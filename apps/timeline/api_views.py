import os
import tempfile
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from django.db.models import Q
from .models import TimelineEvent, TimelineCollection
from .serializers import (
    TimelineEventSerializer,
    TimelineCollectionSerializer,
    DiffViewSerializer
)
from apps.core.models import Case
from apps.archive.models import ArchiveDocument


class TimelineEventViewSet(viewsets.ModelViewSet):
    """API for TimelineEvent CRUD operations."""
    serializer_class = TimelineEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    
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
    
    def perform_update(self, serializer):
        # Get existing instance
        instance = self.get_object()
        
        # Verify user can edit (case owner)
        if instance.case.user != self.request.user:
            raise PermissionDenied("You can only edit events in your own cases")
        
        # Update evidence
        evidence_ids = self.request.data.get('evidence_ids', [])
        if evidence_ids:
            docs = ArchiveDocument.objects.filter(
                id__in=evidence_ids, case=instance.case
            )
            instance.evidence.set(docs)
        
        # Update replaces_event
        replaces_id = self.request.data.get('replaces_event')
        if replaces_id:
            try:
                replaces_event = TimelineEvent.objects.get(
                    id=replaces_id, case=instance.case
                )
                instance.replaces_event = replaces_event
            except TimelineEvent.DoesNotExist:
                pass
        
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def contest(self, request, pk=None, case_id=None):
        """Create a counter-claim to contest an event."""
        from .services import ConflictResolverService
        
        try:
            original_event = TimelineEvent.objects.get(
                pk=pk, case__id=case_id, case__user=request.user
            )
        except TimelineEvent.DoesNotExist:
            raise NotFound("Event not found")
        
        service = ConflictResolverService()
        
        # Prepare event data
        event_data = {
            'date': request.data.get('date', original_event.date),
            'event': request.data.get('event', original_event.event),
            'category': request.data.get('category', original_event.category),
            'notes': request.data.get('notes', original_event.notes),
            'citation': request.data.get('citation', original_event.citation),
            'status': request.data.get('status', 'CONTESTED'),
            'source_type': request.data.get('source_type', 'MANUAL'),
        }
        
        # Get evidence IDs
        evidence_ids = request.data.get('evidence_ids', [])
        
        try:
            counter_claim = service.contest_event(
                original_event=original_event,
                user=request.user,
                event_data=event_data,
                evidence_ids=evidence_ids
            )
            
            return Response(
                TimelineEventSerializer(counter_claim).data,
                status=status.HTTP_201_CREATED
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None, case_id=None):
        """Resolve a conflict for an event.
        
        Supports three resolution paths:
        - KEEP_ORIGINAL: Keep the original event, mark counter-claim as superseded
        - KEEP_COUNTER: Keep the counter-claim, mark original as superseded
        - MERGE: Create new STIPULATED event combining both
        """
        from .services import ConflictResolverService
        
        try:
            event = TimelineEvent.objects.get(
                pk=pk, case__id=case_id, case__user=request.user
            )
        except TimelineEvent.DoesNotExist:
            raise NotFound("Event not found")
        
        resolution = request.data.get('resolution')
        notes = request.data.get('notes', '')
        
        if not resolution:
            return Response(
                {'error': 'resolution is required. Use KEEP_ORIGINAL, KEEP_COUNTER, or MERGE'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = ConflictResolverService()
        
        try:
            resolved_event = service.resolve_conflict(
                event=event,
                resolution=resolution,
                user=request.user,
                notes=notes
            )
            
            return Response(
                TimelineEventSerializer(resolved_event).data,
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )


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
    
    @action(detail=True, methods=['post'])
    def add_event(self, request, pk=None, case_id=None):
        """Add an event to this collection."""
        try:
            collection = TimelineCollection.objects.get(
                pk=pk, case__id=case_id, case__user=request.user
            )
        except TimelineCollection.DoesNotExist:
            raise NotFound("Collection not found")
        
        event_id = request.data.get('event_id')
        if not event_id:
            return Response(
                {'error': 'event_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            event = TimelineEvent.objects.get(
                id=event_id, case=collection.case
            )
            collection.events.add(event)
            return Response(TimelineCollectionSerializer(collection).data)
        except TimelineEvent.DoesNotExist:
            return Response(
                {'error': 'Event not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_event(self, request, pk=None, case_id=None):
        """Remove an event from this collection."""
        try:
            collection = TimelineCollection.objects.get(
                pk=pk, case__id=case_id, case__user=request.user
            )
        except TimelineCollection.DoesNotExist:
            raise NotFound("Collection not found")
        
        event_id = request.data.get('event_id')
        if not event_id:
            return Response(
                {'error': 'event_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            event = TimelineEvent.objects.get(
                id=event_id, case=collection.case
            )
            collection.events.remove(event)
            return Response(TimelineCollectionSerializer(collection).data)
        except TimelineEvent.DoesNotExist:
            return Response(
                {'error': 'Event not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class DiffViewAPI(viewsets.ViewSet):
    """API endpoint for diff view data."""
    permission_classes = [permissions.IsAuthenticated]
    
    def retrieve(self, request, case_id=None):
        """Get diff view data comparing CLIENT vs OPPOSING parties."""
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            raise NotFound("Case not found")
        
        left_party = request.query_params.get('left', 'CLIENT')
        right_party = request.query_params.get('right', 'OPPOSING')
        
        # Get all events for both parties
        left_events = list(TimelineEvent.objects.filter(
            case=case, source_party=left_party
        ).select_related('replaces_event').prefetch_related('evidence').order_by('date'))
        
        right_events = list(TimelineEvent.objects.filter(
            case=case, source_party=right_party
        ).select_related('replaces_event').prefetch_related('evidence').order_by('date'))
        
        # Get all event keys
        left_keys = {(e.date, e.event, e.source_party): e for e in left_events}
        right_keys = {(e.date, e.event, e.source_party): e for e in right_events}
        
        all_keys = set(left_keys.keys()) | set(right_keys.keys())
        
        shared = []
        left_only = []
        right_only = []
        contested = {}
        
        for key in all_keys:
            left_e = left_keys.get(key)
            right_e = right_keys.get(key)
            
            if left_e and right_e:
                # Both parties have this event
                if self._events_differ(left_e, right_e):
                    # Contested - different versions
                    contested_key = f"{left_e.date}_{left_e.event}"
                    contested[contested_key] = {
                        'left': TimelineEventSerializer(left_e).data,
                        'right': TimelineEventSerializer(right_e).data,
                        'diff': self._get_diff(left_e, right_e)
                    }
                else:
                    # Identical - shared
                    shared.append(TimelineEventSerializer(left_e).data)
            elif left_e:
                # Only in left party
                left_only.append(TimelineEventSerializer(left_e).data)
            else:
                # Only in right party
                right_only.append(TimelineEventSerializer(right_e).data)
        
        return Response({
            'left_party': left_party,
            'right_party': right_party,
            'shared': shared,
            'left_only': left_only,
            'right_only': right_only,
            'contested': contested
        })
    
    def _events_differ(self, e1, e2):
        """Check if two events have any differences."""
        return (
            e1.category != e2.category or
            e1.status != e2.status or
            e1.notes != e2.notes or
            e1.citation != e2.citation or
            set(e1.evidence.values_list('id', flat=True)) != 
            set(e2.evidence.values_list('id', flat=True))
        )
    
    def _get_diff(self, e1, e2):
        """Get field-by-field diff between two events."""
        return {
            'category': e1.category != e2.category,
            'status': e1.status != e2.status,
            'notes': e1.notes != e2.notes,
            'citation': e1.citation != e2.citation,
            'evidence': set(e1.evidence.values_list('id', flat=True)) != 
                      set(e2.evidence.values_list('id', flat=True))
        }


class HiveExportViewSet(viewsets.ViewSet):
    """API for exporting a case to a .hive bundle."""
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, case_id=None):
        """Export a case to a .hive bundle.
        
        POST /api/timeline/cases/{case_id}/export/
        
        Optional query params:
        - include_private=true: Include user's private workspace files
        - user_uuid: Specific user UUID for private files (if include_private)
        """
        from .services import HiveExportService
        from apps.core.models import Case
        from django.http import HttpResponse
        import os
        
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            raise NotFound("Case not found or access denied")
        
        # Get optional parameters
        include_private = request.query_params.get('include_private', 'false').lower() == 'true'
        user_uuid = request.query_params.get('user_uuid')
        
        # Use current user's UUID if include_private but no user_uuid specified
        if include_private and not user_uuid:
            user_uuid = str(request.user.uuid)
        
        service = HiveExportService(
            case=case,
            include_private=include_private,
            user_uuid=user_uuid
        )
        
        try:
            hive_path = service.export()
            
            # Return the file as a downloadable response
            if os.path.exists(hive_path):
                with open(hive_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/gzip')
                    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(hive_path)}"'
                    return response
            else:
                return Response(
                    {'error': 'Export file not created'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HiveImportViewSet(viewsets.ViewSet):
    """API for importing a .hive bundle."""
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, case_id=None):
        """Import a .hive bundle.
        
        POST /api/timeline/cases/{case_id}/import/
        
        Request body: The .hive file as multipart form data
        Query params:
        - target_case: UUID of existing case to import into (optional)
        """
        from .services import HiveImportService
        from apps.core.models import Case
        import tempfile
        
        # Get the uploaded file
        hive_file = request.FILES.get('file')
        if not hive_file:
            return Response(
                {'error': 'No file provided. Use multipart form with field name "file"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save to temp file
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, hive_file.name)
        
        try:
            with open(temp_path, 'wb+') as destination:
                for chunk in hive_file.chunks():
                    destination.write(chunk)
            
            # Get target case if specified
            target_case = None
            target_case_uuid = request.query_params.get('target_case')
            if target_case_uuid:
                try:
                    target_case = Case.objects.get(
                        uuid=target_case_uuid,
                        user=request.user
                    )
                except Case.DoesNotExist:
                    return Response(
                        {'error': 'Target case not found or access denied'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            service = HiveImportService(
                hive_path=temp_path,
                target_case=target_case,
                user=request.user
            )
            
            case, errors, warnings = service.import_bundle()
            
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            
            return Response({
                'status': 'success',
                'case_uuid': str(case.uuid),
                'case_name': case.name,
                'errors': errors,
                'warnings': warnings,
                'stats': service.stats
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Clean up temp directory
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


class ShredderViewSet(viewsets.ViewSet):
    """API for secure data shredding."""
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, case_id=None):
        """Shred a case or user's private data.
        
        POST /api/timeline/cases/{case_id}/shred/
        
        Request body:
        - shred_private_only: true to only shred user's private data (default: false)
        """
        from apps.core.models import Case
        from apps.core.services import ShredderService
        
        try:
            case = Case.objects.get(id=case_id)
        except Case.DoesNotExist:
            raise NotFound("Case not found")
        
        shred_private_only = request.data.get('shred_private_only', False)
        
        service = ShredderService(case)
        
        try:
            counts = service.shred_case(
                user=request.user,
                shred_private_only=shred_private_only
            )
            
            return Response({
                'status': 'success',
                'message': 'Case shredded successfully' if not shred_private_only 
                           else 'Private data shredded successfully',
                'deleted': counts
            }, status=status.HTTP_200_OK)
            
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
