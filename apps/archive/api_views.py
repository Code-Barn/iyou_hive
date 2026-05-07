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

from .models import ArchiveDocument
from apps.core.models import Case
from apps.core.services.hive_directory import HiveDirectoryService


class ArchiveDocumentViewSet(viewsets.ModelViewSet):
    """
    API for ArchiveDocument CRUD operations with Gate Logic support.
    
    Provides:
    - Standard CRUD operations
    - promote/ action: Move document from private workspace to formal evidence vault
    - demote/ action: Move document from formal evidence vault back to private workspace
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter documents by current case and user."""
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
    
    @action(detail=True, methods=['post'])
    def promote(self, request, pk=None):
        """
        Gate Logic: Promote a document from private workspace to formal evidence vault.
        
        This is the ONLY mechanism for moving files from Private to Formal.
        
        Request body: None (document ID in URL)
        
        Returns: Updated document data with is_promoted=True
        
        Raises:
            PermissionDenied: If user doesn't own the document
            NotFound: If document not found
        """
        try:
            document = ArchiveDocument.objects.get(pk=pk)
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
        
        Request body: None (document ID in URL)
        
        Returns: Updated document data with is_promoted=False
        
        Raises:
            PermissionDenied: If user doesn't own the document
            NotFound: If document not found
            ValidationError: If document is not promoted
        """
        try:
            document = ArchiveDocument.objects.get(pk=pk)
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
