"""
Timeline API Views

Provides RESTful API endpoints for timeline operations including:
- TimelineEvent CRUD operations
- Timeline upload and parsing
- Diff view generation
- Conflict resolution
"""

import os
import tempfile
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import TimelineEvent, TimelineCollection
from .serializers import (
    TimelineEventSerializer,
    TimelineCollectionSerializer,
    DiffViewSerializer
)
from apps.core.models import Case
from apps.archive.models import ArchiveDocument
from .services import MarkdownIngestionService
from .services.hive_export import HiveExportService
from .services.hive_import import HiveImportService
# from apps.core.services.legal_formatter import LegalFormatterService


class TimelineEventViewSet(viewsets.ModelViewSet):
    """API for TimelineEvent CRUD operations."""
    serializer_class = TimelineEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def get_queryset(self):
        case_id = self.kwargs.get('case_id')
        if not case_id:
            return TimelineEvent.objects.none()
        
        # Verify case belongs to user
        try:
            case = Case.objects.get(id=case_id, user=self.request.user)
        except Case.DoesNotExist:
            return TimelineEvent.objects.none()
        
        queryset = TimelineEvent.objects.filter(case=case)
        
        # Filter by query params
        party = self.request.query_params.get('party')
        if party:
            queryset = queryset.filter(source_party=party)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        # Has evidence filter
        has_evidence = self.request.query_params.get('has_evidence')
        if has_evidence == 'true':
            queryset = queryset.filter(evidence__isnull=False).distinct()
        elif has_evidence == 'false':
            queryset = queryset.filter(evidence__isnull=True)
        
        # Contested only
        contested = self.request.query_params.get('contested')
        if contested == 'true':
            queryset = queryset.filter(
                Q(status__in=['CONTESTED', 'REFUTED']) |
                Q(counter_claims__isnull=False)
            ).distinct()
        
        return queryset.select_related('case', 'created_by', 'replaces_event')\
                       .prefetch_related('evidence', 'counter_claims')\
                       .order_by('date')
    
    def perform_create(self, serializer):
        case_id = self.kwargs.get('case_id')
        try:
            case = Case.objects.get(id=case_id, user=self.request.user)
        except Case.DoesNotExist:
            raise PermissionDenied("Case not found or access denied")
        
        # Link evidence documents
        evidence_ids = self.request.data.get('evidence_ids', [])
        event = serializer.save(case=case, created_by=self.request.user)
        
        if evidence_ids:
            docs = ArchiveDocument.objects.filter(
                id__in=evidence_ids, case=case
            )
            event.evidence.set(docs)
        
        # Link replaces_event if provided
        replaces_id = self.request.data.get('replaces_event')
        if replaces_id:
            try:
                replaces_event = TimelineEvent.objects.get(
                    id=replaces_id, case=case
                )
                event.replaces_event = replaces_event
                event.save()
            except TimelineEvent.DoesNotExist:
                pass

    @method_decorator(csrf_exempt, name='dispatch')
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_markdown(self, request, case_id=None):
        """
        Upload and process a 5-column markdown timeline file.
        
        Accepts:
        - file: The markdown file to upload
        - case_uuid: The case UUID (from URL)
        
        Returns:
        - status: success/error
        - created: number of events created
        - updated: number of events updated
        - skipped: number of events skipped
        - warnings: list of warnings
        """
        if not case_id:
            return Response({
                'status': 'error',
                'error': 'Case ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify case exists and belongs to user
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            return Response({
                'status': 'error',
                'error': 'Case not found or access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if file was provided
        if 'file' not in request.FILES:
            return Response({
                'status': 'error',
                'error': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['file']
        
        # Validate file type
        if not uploaded_file.name.endswith(('.md', '.markdown')):
            return Response({
                'status': 'error',
                'error': 'Only Markdown files (.md, .markdown) are accepted'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Save file to temporary location for processing
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.md') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            # Process the markdown file using MarkdownIngestionService
            result = MarkdownIngestionService.ingest_markdown_file(
                file_path=temp_path,
                case=case,
                user=request.user
            )
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            # Clear cache for this case's timeline
            cache_key = f'timeline_events_{case_id}_{request.user.id}'
            cache.delete(cache_key)
            
            return Response({
                'status': 'success',
                'created': result.get('created', 0),
                'updated': result.get('updated', 0),
                'skipped': result.get('skipped', 0),
                'warnings': result.get('warnings', []),
                'message': f'Timeline processed: {result.get("created", 0)} events created, {result.get("updated", 0)} updated'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Clean up temporary file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            return Response({
                'status': 'error',
                'error': f'Failed to process timeline: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def generate_pdf(self, request, case_id=None):
        """
        Generate a legal PDF of the timeline for the specified case.
        Also generates citation_manifest.json mapping events to PDF locations.
        
        Returns:
        - PDF file for download
        - Citation manifest saved alongside PDF
        """
        if not case_id:
            return Response({
                'status': 'error',
                'error': 'Case ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify case exists and belongs to user
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            return Response({
                'status': 'error',
                'error': 'Case not found or access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Get all events for this case
            events = TimelineEvent.objects.filter(case=case).order_by('date')
            
            # Convert events to 5-column markdown format
            import tempfile
            import os
            
            md_content = f"# {case.name}\n\n"
            md_content += "| Date | Event/Incident | Description | Category | Evidence |\n"
            md_content += "|------|-------|-------------|----------|----------|\n"
            
            for event in events:
                date_str = event.date.strftime('%Y-%m-%d') if event.date else 'N/A'
                evidence_titles = ', '.join([doc.title for doc in event.evidence.all()])
                md_content += f"| {date_str} | {event.event} | {event.notes or ''} | {event.category} | {evidence_titles} |\n"
            
            # Write to temp markdown file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md', encoding='utf-8') as tmp:
                tmp.write(md_content)
                temp_md_path = tmp.name
            
            # Generate PDF using the script
            temp_pdf_path = temp_md_path.replace('.md', '.pdf')
            manifest_path = temp_md_path.replace('.md', '_citation_manifest.json')
            
            # Import and run the conversion
            import sys
            sys.path.insert(0, '/home/user/CODE_BASE/hiver_django/scripts')
            from timeline_to_pdf import convert_md_to_pdf
            
            # Modify convert_md_to_pdf to return citation manifest
            # For now, just generate the PDF
            convert_md_to_pdf(temp_md_path, temp_pdf_path)
            
            # Read the generated citation manifest if it exists
            citation_map = {}
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    citation_map = json.load(f)
            
            # Update events with citation data
            for event in events:
                event_key = f"{event.date}: {event.event}"
                if event_key in citation_map:
                    event.last_printed_citation = citation_map[event_key]
                    event.save(update_fields=['last_printed_citation'])
            
            # Return PDF as file download
            from django.http import FileResponse
            response = FileResponse(
                open(temp_pdf_path, 'rb'),
                as_attachment=True,
                filename=f"timeline_{case_id}.pdf"
            )
            
            # Clean up temp files after response
            import atexit
            def cleanup():
                for f in [temp_md_path, temp_pdf_path, manifest_path]:
                    if os.path.exists(f):
                        os.unlink(f)
            atexit.register(cleanup)
            
            return response
            
        except Exception as e:
            return Response({
                'status': 'error',
                'error': f'Failed to generate PDF: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def contest(self, request, pk=None, case_id=None):
        """Contest an event (create counter-claim)."""
        try:
            event = TimelineEvent.objects.get(pk=pk, case__id=case_id)
        except TimelineEvent.DoesNotExist:
            raise NotFound("Event not found")
        
        # Create counter-claim
        counter_claim_data = {
            'date': event.date,
            'event': event.event,
            'category': 'contested',
            'source_party': request.data.get('source_party', 'OPPOSING'),
            'notes': request.data.get('notes', ''),
            'status': 'CONTESTED',
            'replaces_event': event,
            'case': event.case,
            'created_by': request.user
        }
        
        serializer = self.get_serializer(data=counter_claim_data)
        serializer.is_valid(raise_exception=True)
        counter_claim = serializer.save()
        
        # Link same evidence
        counter_claim.evidence.set(event.evidence.all())
        
        return Response({
            'status': 'success',
            'counter_claim': TimelineEventSerializer(counter_claim).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None, case_id=None):
        """Resolve a conflict."""
        try:
            event = TimelineEvent.objects.get(pk=pk, case__id=case_id)
        except TimelineEvent.DoesNotExist:
            raise NotFound("Event not found")
        
        resolution_data = request.data
        
        # Update the event with resolution
        event.status = resolution_data.get('status', 'UNDISPUTED')
        event.notes = resolution_data.get('notes', event.notes)
        event.citation = resolution_data.get('citation', event.citation)
        
        if 'evidence_ids' in resolution_data:
            docs = ArchiveDocument.objects.filter(id__in=resolution_data['evidence_ids'])
            event.evidence.set(docs)
        
        event.save()
        
        return Response({
            'status': 'success',
            'event': TimelineEventSerializer(event).data
        }, status=status.HTTP_200_OK)


class TimelineCollectionViewSet(viewsets.ModelViewSet):
    """API for TimelineCollection CRUD operations."""
    serializer_class = TimelineCollectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        case_id = self.kwargs.get('case_id')
        if not case_id:
            return TimelineCollection.objects.none()
        
        try:
            case = Case.objects.get(id=case_id, user=self.request.user)
        except Case.DoesNotExist:
            return TimelineCollection.objects.none()
        
        return TimelineCollection.objects.filter(case=case)
    
    def perform_create(self, serializer):
        case_id = self.kwargs.get('case_id')
        try:
            case = Case.objects.get(id=case_id, user=self.request.user)
        except Case.DoesNotExist:
            raise PermissionDenied("Case not found or access denied")
        
        serializer.save(case=case, created_by=self.request.user)


class DiffViewAPI(viewsets.ViewSet):
    """API for diff view data."""
    permission_classes = [permissions.IsAuthenticated]
    
    def retrieve(self, request, case_id=None):
        """Get diff view data for a case."""
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            raise PermissionDenied("Case not found or access denied")
        
        left_party = request.query_params.get('left', 'CLIENT')
        right_party = request.query_params.get('right', 'OPPOSING')
        
        # Get ALL events for this case
        all_events = TimelineEvent.objects.filter(case=case).order_by('date')
        
        # Categorize events by source_party and status
        left_only = []
        right_only = []
        shared_events = []
        contested_pairs = {}
        
        # First pass: identify contested pairs
        contested_events = all_events.filter(status__in=['CONTESTED', 'REFUTED'])
        for event in contested_events:
            if event.replaces_event:
                pair_id = f"{event.replaces_event.id}-{event.id}"
                contested_pairs[pair_id] = {
                    'original': event.replaces_event,
                    'counter_claim': event
                }
        
        # Second pass: categorize all events
        for event in all_events:
            # Skip contested events (they'll be handled separately)
            if event.status in ['CONTESTED', 'REFUTED'] and event.replaces_event:
                # This is a counter-claim, skip it (original will be in its party column)
                continue
            
            # Check if this event is the original of a contested pair
            is_original_of_contested = any(
                pair_id.startswith(f"{event.id}-") 
                for pair_id in contested_pairs.keys()
            )
            
            if is_original_of_contested:
                # Original events that have counter-claims go to contested
                # They'll be displayed in the contested section
                continue
            
            # Categorize by source_party
            if event.source_party == left_party:
                if event.status == 'UNDISPUTED':
                    shared_events.append(event)
                else:
                    left_only.append(event)
            elif event.source_party == right_party:
                if event.status == 'UNDISPUTED':
                    shared_events.append(event)
                else:
                    right_only.append(event)
            else:
                # NEUTRAL, COURT, WITNESS - treat as shared
                shared_events.append(event)
        
        data = {
            'left_party': left_party,
            'right_party': right_party,
            'left_only': TimelineEventSerializer(left_only, many=True).data,
            'right_only': TimelineEventSerializer(right_only, many=True).data,
            'shared': TimelineEventSerializer(shared_events, many=True).data,
            'contested': contested_pairs
        }
        
        return Response(data)

    @action(detail=False, methods=['get'])
    def export_hive(self, request, case_id=None):
        """
        Export the case as a .hive bundle (tar.gz with manifest and files).
        
        Query params:
        - include_private: If 'true', include user's private workspace files
        
        Returns:
        - .hive file for download
        """
        if not case_id:
            return Response({
                'status': 'error',
                'error': 'Case ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            return Response({
                'status': 'error',
                'error': 'Case not found or access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            include_private = request.query_params.get('include_private', 'false').lower() == 'true'
            
            exporter = HiveExportService(
                case=case,
                include_private=include_private,
                user_uuid=str(request.user.id)
            )
            hive_path = exporter.export()
            
            # Return file for download
            from django.http import FileResponse
            response = FileResponse(
                open(hive_path, 'rb'),
                as_attachment=True,
                filename=f"{case.name.replace(' ', '_')}.hive"
            )
            
            # Clean up temp file after response (note: FileResponse closes file after sending)
            import atexit
            atexit.register(lambda: os.unlink(hive_path) if os.path.exists(hive_path) else None)
            
            return response
            
        except NotImplementedError as e:
            return Response({
                'status': 'error',
                'error': str(e)
            }, status=status.HTTP_501_NOT_IMPLEMENTED)
        except Exception as e:
            return Response({
                'status': 'error',
                'error': f'Failed to export: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(csrf_exempt, name='dispatch')
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def import_hive(self, request, case_id=None):
        """
        Import a .hive bundle (tar.gz with manifest and files).
        
        Accepts:
        - file: The .hive bundle to import
        
        Returns:
        - status: success/error
        - message: Result message
        - warnings: List of warnings
        """
        if not case_id:
            return Response({
                'status': 'error',
                'error': 'Case ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            return Response({
                'status': 'error',
                'error': 'Case not found or access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if 'file' not in request.FILES:
            return Response({
                'status': 'error',
                'error': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['file']
        
        # Validate file type
        if not uploaded_file.name.endswith('.hive'):
            return Response({
                'status': 'error',
                'error': 'Only .hive files are accepted'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.hive') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name
            
            importer = HiveImportService(
                case=case,
                user=request.user,
                hive_path=temp_path
            )
            imported_case, warnings, errors = importer.import_bundle()
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return Response({
                'status': 'success',
                'message': f'Imported successfully with {len(warnings)} warnings and {len(errors)} errors',
                'warnings': warnings,
                'errors': errors
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            return Response({
                'status': 'error',
                'error': f'Failed to import: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
