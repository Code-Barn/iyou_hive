"""
Archive API Views

Provides RESTful API endpoints for archive operations including:
- Document promotion/demotion (Gate Logic)
- Smart Ingestion (Formal Vault vs Private Workspace)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import ArchiveDocument
from apps.core.models import Case
from apps.core.services.hive_directory import HiveDirectoryService
from .serializers import RecursiveFolderSerializer
from apps.core.document_processing import convert_pdf_to_markdown
import os
from pathlib import Path
from django.conf import settings

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


@method_decorator(csrf_exempt, name='dispatch')
class DocumentUploadView(APIView):
    """
    Smart Ingestion: Upload documents to either Formal Vault or Private Workspace.
    
    This endpoint implements the Smart Ingestion feature that asks users:
    "Where does this evidence belong?"
    
    Options:
    1. Formal Vault (Read-Only Evidence, destined for the Courtroom PDF)
    2. Private Workspace (Work-in-progress, Drafts, and Wiki)
    
    The vault_type parameter determines the routing:
    - vault_type="formal": Routes to 01_Raw/ or 04_Strategy/ folders
    - vault_type="private": Routes to 02_Wiki/, 03_Drafts/, or 05_Exports/ folders
    
    Request body:
    - files: Array of files to upload
    - vault_type: "formal" or "private" (required for smart ingestion)
    - target_folder: Optional specific folder path (e.g., "01_Raw", "03_Drafts")
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        case_id = request.session.get('selected_case_id')
        if not case_id:
            raise PermissionDenied("No case selected")
        
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            raise PermissionDenied("Case not found or access denied")
        
        # Get vault type from POST data (required for smart ingestion)
        vault_type = request.POST.get('vault_type', None)
        target_folder = request.POST.get('target_folder', None)
        
        # Get uploaded files
        files = request.FILES.getlist('files')
        paths = request.POST.getlist('relative_paths')
        
        if not files:
            return Response({
                'status': 'error',
                'message': 'No files provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not vault_type:
            return Response({
                'status': 'error',
                'message': 'vault_type is required. Must be "formal" or "private"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if vault_type not in ['formal', 'private']:
            return Response({
                'status': 'error',
                'message': 'vault_type must be "formal" or "private"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Determine the base path based on vault type
        # TASK 2 FIX: Include vault prefix in path for proper tree building
        if vault_type == 'formal':
            # Formal Vault: formal/01_Raw/ for raw documents, formal/04_Strategy/ for strategy
            folder = target_folder if target_folder in ['01_Raw', '04_Strategy'] else '01_Raw'
            base_path = f'formal/{folder}/'
            is_promoted = True
            is_draft = False
        else:
            # Private Workspace: private/[user_uuid]/02_Wiki/, private/[user_uuid]/03_Drafts/, etc.
            folder = target_folder if target_folder in ['02_Wiki', '03_Drafts', '05_Exports'] else '03_Drafts'
            base_path = f'private/{str(case.user.uuid)}/{folder}/'
            is_promoted = False
            is_draft = True
        
        uploaded_count = 0
        uploaded_documents = []
        
        try:
            for i, uploaded_file in enumerate(files):
                rel_path = paths[i] if i < len(paths) else uploaded_file.name
                
                file_ext = uploaded_file.name.lower().split('.')[-1] if '.' in uploaded_file.name else ''
                file_type_map = {
                    'pdf': 'pdf', 'png': 'image', 'jpg': 'image', 'jpeg': 'image',
                    'gif': 'image', 'webp': 'image', 'svg': 'image',
                    'doc': 'word', 'docx': 'word',
                    'txt': 'text', 'md': 'text',
                    'eml': 'email', 'msg': 'email',
                }
                file_type = file_type_map.get(file_ext, 'other')
                
                full_path = f"{base_path}{uploaded_file.name}"
                
                doc = ArchiveDocument.objects.create(
                    title=uploaded_file.name,
                    file=uploaded_file,
                    path=full_path,
                    file_type=file_type,
                    is_draft=is_draft,
                    is_immutable=not is_draft,
                    is_promoted=is_promoted,
                    promoted_at=timezone.now() if is_promoted else None,
                    case=case,
                    user=request.user,
                    uploader=request.user,
                    metadata={'virtual_path': rel_path}
                )
                
                try:
                    file_abs_path = os.path.join(settings.MEDIA_ROOT, doc.file.name)
                    original_name = uploaded_file.name
                    virtual_path = rel_path
                    
                    processed_path = convert_pdf_to_markdown(
                        file_abs_path,
                        original_name=original_name,
                        virtual_path=virtual_path
                    )
                    
                    if processed_path != file_abs_path:
                        twin_rel_path = os.path.relpath(processed_path, settings.MEDIA_ROOT)
                        doc.conversion_status = 'SUCCESS'
                        doc.markdown_path = twin_rel_path
                        doc.save()
                        
                except Exception as e:
                    doc.conversion_status = 'FAILED'
                    doc.conversion_error = str(e)
                    doc.save()
                    print(f"Digital Twin conversion failed for {doc.title}: {str(e)}")
                
                uploaded_count += 1
                uploaded_documents.append({
                    'uuid': str(doc.uuid),
                    'title': doc.title,
                    'path': doc.path,
                    'is_promoted': doc.is_promoted,
                    'vault_type': vault_type,
                    'conversion_status': doc.conversion_status,
                    'markdown_path': doc.markdown_path if doc.markdown_path else None
                })
            
            return Response({
                'status': 'success',
                'message': f'Uploaded {uploaded_count} file(s) to {vault_type} vault',
                'uploaded': uploaded_count,
                'vault_type': vault_type,
                'documents': uploaded_documents
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to upload files: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
