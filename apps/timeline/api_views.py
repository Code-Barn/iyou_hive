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
        try:
            original_event = TimelineEvent.objects.get(
                pk=pk, case__id=case_id, case__user=request.user
            )
        except TimelineEvent.DoesNotExist:
            raise NotFound("Event not found")
        
        # User's party for the counter-claim
        user_party = request.data.get('source_party')
        if not user_party:
            # Determine user's party - for now, assume they're the opposing party
            # In a real system, this would come from user profile
            user_party = 'OPPOSING' if original_event.source_party == 'CLIENT' else 'CLIENT'
        
        # Create counter-claim
        counter_claim = TimelineEvent.objects.create(
            case=original_event.case,
            date=original_event.date,
            event=original_event.event,
            category=original_event.category,
            notes=request.data.get('notes', original_event.notes),
            citation=request.data.get('citation', ''),
            source_party=user_party,
            status='CONTESTED',
            source_type='MANUAL',
            created_by=request.user,
            replaces_event=original_event
        )
        
        # Link evidence if provided
        evidence_ids = request.data.get('evidence_ids', [])
        if evidence_ids:
            docs = ArchiveDocument.objects.filter(
                id__in=evidence_ids, case=original_event.case
            )
            counter_claim.evidence.set(docs)
        
        return Response(
            TimelineEventSerializer(counter_claim).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None, case_id=None):
        """Resolve a conflict by creating a stipulated version."""
        try:
            # Get the contested event
            contested_event = TimelineEvent.objects.get(
                pk=pk, case__id=case_id, case__user=request.user
            )
        except TimelineEvent.DoesNotExist:
            raise NotFound("Contested event not found")
        
        resolution = request.data.get('resolution', 'STIPULATED')
        
        # Get the original event (the one being replaced)
        original_event = contested_event.replaces_event
        
        # Create new stipulated event
        new_event = TimelineEvent.objects.create(
            case=contested_event.case,
            date=request.data.get('date', contested_event.date),
            event=request.data.get('event', contested_event.event),
            category=request.data.get('category', contested_event.category),
            notes=request.data.get('notes', contested_event.notes),
            citation=request.data.get('citation', contested_event.citation),
            source_party='NEUTRAL',
            status='STIPULATED',
            source_type='MANUAL',
            created_by=request.user
        )
        
        # Link evidence
        evidence_ids = request.data.get('evidence_ids', [])
        if evidence_ids:
            docs = ArchiveDocument.objects.filter(
                id__in=evidence_ids, case=contested_event.case
            )
            new_event.evidence.set(docs)
        
        # Both contested events now point to the stipulated version
        contested_event.replaces_event = new_event
        contested_event.save()
        
        if original_event:
            original_event.replaces_event = new_event
            original_event.save()
        
        return Response(
            TimelineEventSerializer(new_event).data,
            status=status.HTTP_201_CREATED
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
