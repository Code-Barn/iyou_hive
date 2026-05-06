import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class TimelineEvent(models.Model):
    """
    Model for timeline events in legal cases.
    Supports Competing Timelines: multiple versions of the "truth" for a single case.

    Attributes:
        id: UUID primary key for shareable URLs
        date: Date of the event
        event: Title/name of the event (Event/Incident)
        category: Category of the event
        source_type: How the event was created
        status: Status for competing timelines (UNDISPUTED, CONTESTED, REFUTED, STIPULATED, PENDING)
        source_party: Who created/asserts this event (CLIENT, OPPOSING, NEUTRAL, COURT, WITNESS)
        evidence: ManyToMany to ArchiveDocument - documents supporting this event
        replaces_event: Self-referencing FK for counter-claims
        citation: Citation or reference for this event
        notes: Detailed notes about the event
        version: Version number for audit trail
        created_at: Timestamp when created
        updated_at: Timestamp when last updated
        timeline_file: Source TimelineFile (optional)
        case: Case this event belongs to
        created_by: User who created this event
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    CATEGORY_CHOICES = [
        ('contract', 'Contract'),
        ('email', 'Email'),
        ('court_filing', 'Court Filing'),
        ('communication', 'Communication'),
        ('meeting', 'Meeting'),
        ('deadline', 'Deadline'),
        ('verified', 'Verified'),
        ('contested', 'Contested'),
        ('personal', 'Personal'),
        ('legal', 'Legal'),
        ('medical', 'Medical'),
        ('financial', 'Financial'),
        ('education', 'Education'),
        ('other', 'Other'),
    ]

    SOURCE_TYPE_CHOICES = [
        ('MANUAL', 'Manual Entry'),
        ('MARKDOWN', 'Markdown Import'),
        ('AI_GENERATED', 'AI Generated'),
    ]

    STATUS_CHOICES = [
        ('UNDISPUTED', 'Undisputed'),
        ('CONTESTED', 'Contested'),
        ('REFUTED', 'Refuted'),
        ('STIPULATED', 'Stipulated'),
        ('PENDING', 'Pending Review'),
    ]

    SOURCE_PARTY_CHOICES = [
        ('CLIENT', 'Client/Plaintiff'),
        ('OPPOSING', 'Opposing Party/Defendant'),
        ('NEUTRAL', 'Neutral Third Party'),
        ('COURT', 'Court'),
        ('WITNESS', 'Witness'),
    ]

    date = models.DateField(help_text="Date of the event", db_index=True)
    event = models.CharField(max_length=255, help_text="Title or name of the event (Event/Incident)")
    category = models.CharField(
        max_length=100,
        choices=CATEGORY_CHOICES,
        default='other',
        help_text="Category of the event"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default='MANUAL',
        help_text="How this event was created"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='UNDISPUTED',
        help_text="Status of this event in the competing timeline context"
    )
    source_party = models.CharField(
        max_length=20,
        choices=SOURCE_PARTY_CHOICES,
        help_text="Party that created or asserts this event"
    )

    # System source tracking
    is_system_source = models.BooleanField(
        default=False,
        help_text="Whether this event comes from an authoritative system source (COURT, NEUTRAL)"
    )
    trust_level = models.PositiveSmallIntegerField(
        default=3,
        choices=[
            (1, 'Low - Unverified'),
            (2, 'Medium - User Verified'),
            (3, 'High - Documented'),
            (4, 'Very High - Official Record'),
            (5, 'Maximum - Court Stipulated'),
        ],
        help_text="Trust level from 1 (low) to 5 (maximum)"
    )
    citation = models.CharField(
        max_length=500,
        blank=True,
        help_text="Citation or reference for this event"
    )
    notes = models.TextField(blank=True, help_text="Detailed notes about the event")

    # Evidence: sole mechanism for document linking
    evidence = models.ManyToManyField(
        'archive.ArchiveDocument',
        related_name='timeline_events',
        blank=True,
        help_text="Documents that support or evidence this event"
    )

    # Counter-claim support
    replaces_event = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='counter_claims',
        help_text="Event this is a counter-claim to"
    )

    version = models.PositiveIntegerField(
        default=1,
        help_text="Version number for this event"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this event was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this event was last updated"
    )

    timeline_file = models.ForeignKey(
        'core.TimelineFile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timeline_events',
        help_text="Source TimelineFile this event was parsed from"
    )

    case = models.ForeignKey(
        'core.Case',
        on_delete=models.CASCADE,
        related_name='events',
        db_index=True,
        help_text="Case this event belongs to"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timeline_events_created',
        help_text="User who created this event"
    )

    class Meta:
        ordering = ['date']
        verbose_name = 'Timeline Event'
        verbose_name_plural = 'Timeline Events'
        unique_together = ['case', 'date', 'event', 'source_party']

    def __str__(self):
        return f"{self.date}: {self.event} ({self.get_status_display()})"

    @property
    def has_gold_seal(self) -> bool:
        """
        UI Hint: Returns True if this event has the "Gold Seal" - 
        meaning it's from a system source (COURT/NEUTRAL) and has STIPULATED status.
        Used by frontend to render the Gold Seal icon.
        """
        return self.is_system_source and self.status == 'STIPULATED'

    def clean(self):
        """
        Gatekeeper validation.
        - CONTESTED/REFUTED events MUST have evidence
        - replaces_event must be same case
        - No circular references in replaces_event chain
        - System source validation: COURT/NEUTRAL → is_system_source=True, status=STIPULATED
        - Hardened: System sources cannot be CONTESTED without replaces_event or Correction doc
        """
        super().clean()

        # Defaulting Rules: COURT/NEUTRAL must be system source with STIPULATED status
        if self.source_party in ['COURT', 'NEUTRAL']:
            if not self.is_system_source:
                self.is_system_source = True
            if self.status != 'STIPULATED':
                self.status = 'STIPULATED'
            self.trust_level = 5

        # Inverse: Non-system sources cannot have COURT/NEUTRAL as source_party
        if self.is_system_source and self.source_party not in ['COURT', 'NEUTRAL']:
            raise ValidationError({
                'source_party': 'System sources must have COURT or NEUTRAL as source_party'
            })

        # Source Requirement: CONTESTED/REFUTED MUST have evidence
        if self.status in ['CONTESTED', 'REFUTED']:
            if self.pk is None:
                # New instance: check _evidence_cache
                if not hasattr(self, '_evidence_cache') or not self._evidence_cache:
                    raise ValidationError({
                        'evidence': 'Evidence is required when status is CONTESTED or REFUTED'
                    })
            else:
                # Existing instance: check database
                if not self.evidence.exists():
                    raise ValidationError({
                        'evidence': 'Evidence is required when status is CONTESTED or REFUTED'
                    })

        # replaces_event must be same case
        if self.replaces_event and self.replaces_event.case != self.case:
            raise ValidationError({
                'replaces_event': 'Replaced event must belong to the same case'
            })

        # Detect circular references
        if self.replaces_event:
            chain = []
            current = self
            while current:
                if current.pk:
                    if current.pk in chain:
                        raise ValidationError({
                            'replaces_event': 'Circular reference in replaces_event chain'
                        })
                    chain.append(current.pk)
                current = current.replaces_event
                if len(chain) > 100:
                    raise ValidationError({
                        'replaces_event': 'Chain too deep - possible circular reference'
                    })

        # Hardened Validation: System sources cannot be CONTESTED without conditions
        if self.is_system_source and self.status == 'CONTESTED':
            # Check if there's a replaces_event (counter-claim chain)
            has_replaces = self.replaces_event is not None
            
            # Check if any evidence document has "Correction" in title
            has_correction_doc = False
            if self.pk:
                has_correction_doc = self.evidence.filter(
                    title__icontains='Correction'
                ).exists()
            else:
                # For new instances, check _evidence_cache
                if hasattr(self, '_evidence_cache') and self._evidence_cache:
                    from apps.archive.models import ArchiveDocument
                    doc_ids = [d.id if hasattr(d, 'id') else d for d in self._evidence_cache]
                    has_correction_doc = ArchiveDocument.objects.filter(
                        id__in=doc_ids,
                        title__icontains='Correction'
                    ).exists()
            
            if not has_replaces and not has_correction_doc:
                raise ValidationError({
                    'status': 'System source events cannot be CONTESTED without a replaces_event chain or Correction document'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.pk is not None:
            self.version += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('timeline:detail', args=[str(self.id)])

    def get_category_display(self):
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category)

    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def get_source_party_display(self):
        return dict(self.SOURCE_PARTY_CHOICES).get(self.source_party, self.source_party)


class TimelineCollection(models.Model):
    """
    Curated collection of timeline events.
    Supports "Saved Timelines" - user-created subsets of events for specific purposes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Name of this collection")
    description = models.TextField(blank=True, help_text="Description of the collection's purpose")
    events = models.ManyToManyField(
        TimelineEvent,
        related_name='collections',
        blank=True,
        help_text="Timeline events in this collection"
    )
    case = models.ForeignKey(
        'core.Case',
        on_delete=models.CASCADE,
        related_name='collections',
        help_text="Case this collection belongs to"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='timeline_collections',
        help_text="User who created this collection"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this collection is visible to other users of the case"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Timeline Collection'
        verbose_name_plural = 'Timeline Collections'
        unique_together = ['name', 'case']

    def __str__(self):
        return f"{self.name} ({self.case.name})"
