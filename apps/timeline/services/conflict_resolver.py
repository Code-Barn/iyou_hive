"""
Conflict Resolver Service

Manages the Git-style conflict resolution workflow for TimelineEvents.
When a user contests an event, creates a counter-claim linked via replaces_event.
Provides resolution paths: KEEP_ORIGINAL, KEEP_COUNTER, MERGE.
"""

import uuid
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from typing import Optional, List, Dict, Any

from apps.timeline.models import TimelineEvent
from apps.archive.models import ArchiveDocument


class ConflictResolverService:
    """
    Service for managing conflicts between TimelineEvents.
    
    Conflict Flow:
    1. User contests an event → creates counter-claim with replaces_event = original
    2. Counter-claim has same case, different source_party (user's perspective)
    3. Original event's status can be updated, or kept as-is
    4. Conflict resolved via one of three paths:
       - KEEP_ORIGINAL: Discard counter-claim, keep original
       - KEEP_COUNTER: Discard original, keep counter-claim  
       - MERGE: Create new STIPULATED event combining both
    """

    RESOLUTION_KEEP_ORIGINAL = "KEEP_ORIGINAL"
    RESOLUTION_KEEP_COUNTER = "KEEP_COUNTER"
    RESOLUTION_MERGE = "MERGE"
    
    RESOLUTION_CHOICES = [
        (RESOLUTION_KEEP_ORIGINAL, "Keep Original Claim"),
        (RESOLUTION_KEEP_COUNTER, "Keep Counter Claim"),
        (RESOLUTION_MERGE, "Merge into Stipulated"),
    ]

    @transaction.atomic
    def contest_event(
        self,
        original_event: TimelineEvent,
        user,
        event_data: Dict[str, Any],
        evidence_ids: Optional[List[int]] = None,
        evidence_objects: Optional[List[ArchiveDocument]] = None
    ) -> TimelineEvent:
        """
        Create a counter-claim contesting an existing event.
        
        Args:
            original_event: The TimelineEvent being contested
            user: The User creating the counter-claim
            event_data: Dictionary containing event fields:
                       - date: Date of the counter-claim
                       - event: Title/name
                       - category: Event category
                       - notes: Detailed notes
                       - status: CONTESTED or REFUTED (default: CONTESTED)
                       - citation: Optional citation
            evidence_ids: List of ArchiveDocument primary keys to link
            evidence_objects: Alternative - list of ArchiveDocument objects
            
        Returns:
            The newly created counter-claim TimelineEvent
            
        Raises:
            PermissionDenied: If user is the same as original event's source_party
            ValidationError: If CONTESTED/REFUTED status without evidence
        """
        # Validate: User cannot contest their own event if same source_party
        # (They can create a correction instead)
        if original_event.source_party == user.party:
            raise PermissionDenied(
                f"Cannot contest your own event. "
                f"User party: {user.party}, Event source_party: {original_event.source_party}"
            )
        
        # Determine status
        status = event_data.get('status', 'CONTESTED')
        
        # Validate: CONTESTED/REFUTED requires evidence
        if status in ['CONTESTED', 'REFUTED']:
            has_evidence = (evidence_ids and len(evidence_ids) > 0) or \
                          (evidence_objects and len(evidence_objects) > 0)
            if not has_evidence:
                raise ValidationError(
                    f"{status} events require evidence. Provide evidence_ids or evidence_objects."
                )
        
        # Create the counter-claim
        counter_claim = TimelineEvent.objects.create(
            uuid=uuid.uuid4(),
            date=event_data.get('date', original_event.date),
            event=event_data.get('event', f"Counter: {original_event.event}"),
            category=event_data.get('category', original_event.category),
            notes=event_data.get('notes', ''),
            source_party=user.party,
            source_type=event_data.get('source_type', 'MANUAL'),
            status=status,
            # System source fields - counter-claims are user-generated
            is_system_source=False,
            trust_level=2,  # Medium - User Verified
            version=original_event.version + 1,
            citation=event_data.get('citation', ''),
            replaces_event=original_event,  # Link to original
            case=original_event.case,
            created_by=user,
        )
        
        # Link evidence if provided
        if evidence_ids:
            documents = ArchiveDocument.objects.filter(id__in=evidence_ids)
            counter_claim.evidence.set(documents)
        
        if evidence_objects:
            counter_claim.evidence.set(evidence_objects)
        
        # Re-validate after linking evidence
        counter_claim.full_clean()
        
        return counter_claim

    @transaction.atomic
    def resolve_conflict(
        self,
        event: TimelineEvent,
        resolution: str,
        user,
        notes: str = ""
    ) -> TimelineEvent:
        """
        Resolve a conflict for an event.
        
        Args:
            event: The TimelineEvent to resolve (typically the original or a counter-claim)
            resolution: One of KEEP_ORIGINAL, KEEP_COUNTER, MERGE
            user: The User resolving the conflict
            notes: Optional resolution notes for audit trail
            
        Returns:
            The resolved TimelineEvent
            
        Raises:
            ValidationError: If resolution is invalid or no conflict exists
            PermissionDenied: If user lacks permission
        """
        # Validate resolution type
        if resolution not in [self.RESOLUTION_KEEP_ORIGINAL, 
                              self.RESOLUTION_KEEP_COUNTER,
                              self.RESOLUTION_MERGE]:
            raise ValidationError(
                f"Invalid resolution: {resolution}. "
                f"Must be one of: {', '.join([r[0] for r in self.RESOLUTION_CHOICES])}"
            )
        
        # Check if there's actually a conflict to resolve
        has_counter_claims = TimelineEvent.objects.filter(
            replaces_event=event
        ).exists()
        
        is_counter_claim = event.replaces_event is not None
        
        if not has_counter_claims and not is_counter_claim:
            raise ValidationError(
                f"No conflict to resolve for event {event.uuid}. "
                f"Event has no counter-claims and is not itself a counter-claim."
            )
        
        # Determine the original and counter-claim events
        if is_counter_claim:
            # This event is a counter-claim, resolve based on that
            original_event = event.replaces_event
            counter_claim = event
        else:
            # This event is the original, find its counter-claims
            counter_claims = list(TimelineEvent.objects.filter(
                replaces_event=event
            ).order_by('-created_at'))
            
            if not counter_claims:
                raise ValidationError(
                    f"No counter-claims found for event {event.uuid}"
                )
            
            original_event = event
            counter_claim = counter_claims[0]  # Use most recent counter-claim
        
        # Execute resolution
        if resolution == self.RESOLUTION_KEEP_ORIGINAL:
            return self._resolve_keep_original(original_event, counter_claim, user, notes)
        
        elif resolution == self.RESOLUTION_KEEP_COUNTER:
            return self._resolve_keep_counter(original_event, counter_claim, user, notes)
        
        elif resolution == self.RESOLUTION_MERGE:
            return self._resolve_merge(original_event, counter_claim, user, notes)

    def _resolve_keep_original(
        self,
        original_event: TimelineEvent,
        counter_claim: TimelineEvent,
        user,
        notes: str
    ) -> TimelineEvent:
        """
        Keep the original event and mark counter-claim as SUPERSEDED.
        """
        # Mark counter-claim as superseded
        counter_claim.status = 'SUPERSEDED'
        counter_claim.notes = (
            f"{counter_claim.notes}\n\n"
            f"[RESOLVED: {timezone.now().isoformat()}Z]\n"
            f"Resolution: KEEP_ORIGINAL\n"
            f"Resolved by: {user.email or str(str(user.id))}\n"
            f"Notes: {notes}"
        )
        counter_claim.save()
        
        return original_event

    def _resolve_keep_counter(
        self,
        original_event: TimelineEvent,
        counter_claim: TimelineEvent,
        user,
        notes: str
    ) -> TimelineEvent:
        """
        Keep the counter-claim and mark original as SUPERSEDED.
        """
        # Mark original as superseded
        original_event.status = 'SUPERSEDED'
        original_event.notes = (
            f"{original_event.notes}\n\n"
            f"[RESOLVED: {timezone.now().isoformat()}Z]\n"
            f"Resolution: KEEP_COUNTER\n"
            f"Resolved by: {user.email or str(str(user.id))}\n"
            f"Notes: {notes}"
        )
        original_event.save()
        
        return counter_claim

    def _resolve_merge(
        self,
        original_event: TimelineEvent,
        counter_claim: TimelineEvent,
        user,
        notes: str
    ) -> TimelineEvent:
        """
        Merge both events into a new STIPULATED event.
        Combines evidence from both and creates a neutral perspective.
        """
        # Create new merged event
        merged = TimelineEvent.objects.create(
            uuid=uuid.uuid4(),
            date=original_event.date,  # Use original date by default
            event=f"[STIPULATED] {original_event.event}",
            category=original_event.category,
            notes=(
                f"=== ORIGINAL ===\n"
                f"Party: {original_event.source_party}\n"
                f"Status: {original_event.status}\n"
                f"Date: {original_event.date}\n"
                f"Notes: {original_event.notes}\n\n"
                f"=== COUNTER-CLAIM ===\n"
                f"Party: {counter_claim.source_party}\n"
                f"Status: {counter_claim.status}\n"
                f"Date: {counter_claim.date}\n"
                f"Notes: {counter_claim.notes}\n\n"
                f"=== RESOLUTION ===\n"
                f"Merged by: {user.email or str(str(user.id))}\n"
                f"Resolution notes: {notes}"
            ),
            source_party='NEUTRAL',  # Neutral authority for stipulated facts
            source_type='MANUAL',
            status='STIPULATED',
            is_system_source=True,  # Merged facts are system-level truth
            trust_level=5,  # Maximum trust
            version=max(original_event.version, counter_claim.version) + 1,
            replaces_event=original_event,  # Links to original for audit trail
            case=original_event.case,
            created_by=user,
        )
        
        # Merge evidence from both events
        original_evidence = list(original_event.evidence.all())
        counter_evidence = list(counter_claim.evidence.all())
        # Deduplicate by UUID
        all_evidence = []
        seen_uuids = set()
        for doc in original_evidence + counter_evidence:
            if doc.uuid not in seen_uuids:
                all_evidence.append(doc)
                seen_uuids.add(doc.uuid)
        
        if all_evidence:
            merged.evidence.set(all_evidence)
        
        # Mark both original and counter-claim as superseded
        original_event.status = 'SUPERSEDED'
        original_event.notes = (
            f"{original_event.notes}\n\n"
            f"[RESOLVED: {timezone.now().isoformat()}Z]\n"
            f"Resolution: MERGE\n"
            f"Superseded by: {merged.uuid}"
        )
        original_event.save()
        
        counter_claim.status = 'SUPERSEDED'
        counter_claim.notes = (
            f"{counter_claim.notes}\n\n"
            f"[RESOLVED: {timezone.now().isoformat()}Z]\n"
            f"Resolution: MERGE\n"
            f"Superseded by: {merged.uuid}"
        )
        counter_claim.save()
        
        return merged

    def get_conflict_chain(self, event: TimelineEvent) -> List[TimelineEvent]:
        """
        Get the full chain of an event and all events that replace it.
        
        Returns a list of TimelineEvents in chronological order (oldest first).
        """
        chain = [event]
        
        # Find all counter-claims (events that replace this one)
        counter_claims = list(TimelineEvent.objects.filter(
            replaces_event=event
        ).order_by('created_at'))
        
        for cc in counter_claims:
            chain.append(cc)
            # Recursively get chain for counter-claim
            chain.extend(self.get_conflict_chain(cc)[1:])
        
        return chain

    def get_conflict_graph(self, case) -> Dict[str, Any]:
        """
        Get a complete conflict graph for a case.
        
        Returns a dictionary mapping event UUIDs to their conflict information.
        """
        from apps.timeline.models import TimelineEvent
        
        events = TimelineEvent.objects.filter(case=case)
        
        graph = {}
        for event in events:
            # Get counter-claims
            counter_claims = list(TimelineEvent.objects.filter(
                replaces_event=event
            ))
            
            # Get replaced event (if this is a counter-claim)
            replaced_event = event.replaces_event
            
            graph[str(event.uuid)] = {
                'event': event,
                'is_counter_claim': replaced_event is not None,
                'replaces_uuid': str(replaced_event.uuid) if replaced_event else None,
                'counter_claim_uuids': [str(cc.uuid) for cc in counter_claims],
                'has_conflict': len(counter_claims) > 0 or replaced_event is not None,
                'status': event.status,
                'source_party': event.source_party,
                'trust_level': event.trust_level,
                'has_gold_seal': event.has_gold_seal,
            }
        
        return graph

    def get_resolvable_conflicts(self, case, user) -> List[Dict[str, Any]]:
        """
        Get a list of conflicts that the user can resolve.
        
        Returns list of conflict dictionaries with both original and counter-claim info.
        """
        conflicts = []
        
        # Find all events that have counter-claims
        events_with_counter_claims = TimelineEvent.objects.filter(
            case=case,
            counter_claims__isnull=False
        ).distinct()
        
        for event in events_with_counter_claims:
            counter_claims = list(event.counter_claims.all())
            
            for cc in counter_claims:
                # Check if user can resolve this conflict
                # User can resolve if they're involved in either event
                user_can_resolve = (
                    event.created_by == user or
                    cc.created_by == user or
                    user.is_staff or
                    user.is_superuser
                )
                
                if user_can_resolve:
                    conflicts.append({
                        'original': event,
                        'counter_claim': cc,
                        'original_uuid': str(event.uuid),
                        'counter_claim_uuid': str(cc.uuid),
                    })
        
        return conflicts
