"""
Archive API Views

Provides RESTful API endpoints for archive operations including:
- Document promotion/demotion (Gate Logic)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView # Import APIView

from .models import ArchiveDocument
from apps.core.models import Case
from apps.core.services.hive_directory import HiveDirectoryService
from .serializers import RecursiveFolderSerializer # Import RecursiveFolderSerializer

class ArchiveDocumentViewSet(viewsets.ModelViewSet):
    """
    API for ArchiveDocument CRUD operations with Gate Logic support.
    
    Provides:
    - Standard CRUD operations
    - promote/ action: Move document from private workspace to formal evidence vault
    - demote/ action: Move document from formal evidence vault back to private workspace
    - move_file/ action: Move document to a specified folder
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter documents by current case and user.
        """
        case_id = self.request.session.get('selected_case_id')
        if not case_id:
            return ArchiveDocument.objects.none()
        
        try:
            case = Case.objects.get(id=case_id, user=self.request.user)
        except Case.DoesNotExist:
            return ArchiveDocument.objects.none()
        
        # Return documents for this case that the user has access to
        return ArchiveDocument.objects.filter(
            case=case
        ).select_related('case', 'uploader', 'user').order_by('-upload_date')
    
    @action(detail=False, methods=['post'])
    def move_file(self, request):
        """
        Move a file to a new folder within the archive.
        
        Request body:
        - source_file_uuid: UUID of the file to move
        - destination_folder_uuid: UUID of the target folder
        
        Returns: Updated document data.
        
        Raises:
            PermissionDenied: If user doesn't own the document or case access is denied.
            NotFound: If source file or destination folder not found.
            ValidationError: If destination is not a folder.
        """
        source_file_uuid = request.data.get('source_file_uuid')
        destination_folder_uuid = request.data.get('destination_folder_uuid')

        if not source_file_uuid or not destination_folder_uuid:
            return Response({'status': 'error', 'message': 'Missing source_file_uuid or destination_folder_uuid'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        # Get the current case
        case_id = request.session.get('selected_case_id')
        if not case_id:
            raise PermissionDenied("No case selected")
        
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            raise PermissionDenied("Case not found or access denied")

        try:
            source_document = ArchiveDocument.objects.get(uuid=source_file_uuid, case=case)
            destination_folder_document = ArchiveDocument.objects.get(uuid=destination_folder_uuid, case=case)
        except ArchiveDocument.DoesNotExist:
            raise NotFound("Source file or destination folder not found")
        
        # Call the HiveDirectoryService to move the document
        try:
            moved_doc = HiveDirectoryService.move_document(
                document=source_document,
                destination_folder_document=destination_folder_document,
                user=request.user
            )
            return Response({
                'status': 'success',
                'message': 'Document moved successfully',
                'document': {
                    'uuid': str(moved_doc.uuid),
                    'title': moved_doc.title,
                    'path': moved_doc.path,
                    'is_promoted': moved_doc.is_promoted,
                    'promoted_at': moved_doc.promoted_at.isoformat() if moved_doc.promoted_at else None,
                }
            }, status=status.HTTP_200_OK)
        except PermissionDenied as e:
            raise PermissionDenied(str(e))
        except ValidationError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except FileNotFoundError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to move document: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def promote(self, request, pk=None):
        """
        Gate Logic: Promote a document from private workspace to formal evidence vault.
        
        This is the ONLY mechanism for moving files from Private to Formal.
        
        Request body: None (document UUID in URL)
        
        Returns: Updated document data with is_promoted=True
        
        Raises:
            PermissionDenied: If user doesn't own the document
            NotFound: If document not found
        """
        try:
            document = ArchiveDocument.objects.get(uuid=pk)
        except ArchiveDocument.DoesNotExist:
            raise NotFound("Document not found")
        
        # Get the current case
        case_id = request.session.get('selected_case_id')
        if not case_id:
            raise PermissionDenied("No case selected")
        
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            raise PermissionDenied("Case not found or access denied")
        
        # Validate document belongs to this case
        if document.case != case:
            raise PermissionDenied("Document does not belong to the current case")
        
        # Call the Gate Logic service
        try:
            promoted_doc = HiveDirectoryService.promote_to_evidence(
                document=document,
                case=case,
                user=request.user
            )
            
            # Return the updated document
            return Response({
                'status': 'success',
                'message': 'Document promoted to formal evidence',
                'document': {
                    'id': promoted_doc.id,
                    'uuid': str(promoted_doc.uuid),
                    'title': promoted_doc.title,
                    'is_promoted': promoted_doc.is_promoted,
                    'promoted_at': promoted_doc.promoted_at.isoformat() if promoted_doc.promoted_at else None,
                }
            }, status=status.HTTP_200_OK)
            
        except PermissionDenied as e:
            raise PermissionDenied(str(e))
        except FileNotFoundError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to promote document: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def demote(self, request, pk=None):
        """
        Gate Logic: Demote a document from formal evidence vault back to private workspace.
        
        Reverse of promote_to_evidence.
        
        Request body: None (document UUID in URL)
        
        Returns: Updated document data with is_promoted=False
        
        Raises:
            PermissionDenied: If user doesn't own the document
            NotFound: If document not found
            ValidationError: If document is not promoted
        """
        try:
            document = ArchiveDocument.objects.get(uuid=pk)
        except ArchiveDocument.DoesNotExist:
            raise NotFound("Document not found")
        
        # Call the Gate Logic service
        try:
            demoted_doc = HiveDirectoryService.demote_from_evidence(
                document=document,
                user=request.user
            )
            
            # Return the updated document
            return Response({
                'status': 'success',
                'message': 'Document demoted from formal evidence',
                'document': {
                    'id': demoted_doc.id,
                    'uuid': str(demoted_doc.uuid),
                    'title': demoted_doc.title,
                    'is_promoted': demoted_doc.is_promoted,
                    'promoted_at': demoted_doc.promoted_at.isoformat() if demoted_doc.promoted_at else None,
                }
            }, status=status.HTTP_200_OK)
            
        except PermissionDenied as e:
            raise PermissionDenied(str(e))
        except FileNotFoundError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to demote document: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileMetadataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_uuid, *args, **kwargs):
        case_id = request.session.get('selected_case_id')
        if not case_id:
            raise PermissionDenied("No case selected")

        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            raise PermissionDenied("Case not found or access denied")

        try:
            document = ArchiveDocument.objects.select_related('timeline_event').get(uuid=file_uuid, case=case)
        except ArchiveDocument.DoesNotExist:
            raise NotFound("Document not found")

        serializer = ArchiveDocumentSerializer(document)
        return Response(serializer.data)


class ArchiveDirectoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Get case_id from query parameter first, then fall back to session
        case_id = request.query_params.get('case_id') or request.session.get('selected_case_id')
        if not case_id:
            raise PermissionDenied("No case selected")
        
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            raise PermissionDenied("Case not found or access denied")

        case_uuid = str(case.uuid)
        user_uuid = str(request.user.uuid) if request.user.is_authenticated else None

        if not user_uuid:
            raise PermissionDenied("User not authenticated")

        tree_data = RecursiveFolderSerializer.build_tree(case_uuid, user_uuid)
        serializer = RecursiveFolderSerializer(tree_data, many=True, context={'request': request, 'case_uuid': case_uuid, 'user_uuid': user_uuid})
        return Response(serializer.data)
