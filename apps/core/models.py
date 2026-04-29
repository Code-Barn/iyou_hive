from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


def raw_document_upload_path(instance, filename):
    """Generate upload path for RawDocument based on case."""
    return f"raw/{instance.case.id}/{filename}"


class Case(models.Model):
    """
    Model for legal case compartmentalization.

    Each case acts as a container for timeline events, archive documents,
    and AI assistant context. Users can switch between cases to isolate
    their work on different legal matters.

    Attributes:
        id: UUID primary key
        name: Human-readable name of the case
        description: Detailed description of the case
        color: Color code for UI identification (e.g., '#FF8C00' for honey-orange)
        is_active: Whether this is the user's currently active case
        created_at: When the case was created
        updated_at: When the case was last modified
        user: The user who owns this case
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID primary key"
    )

    name = models.CharField(
        max_length=200,
        help_text="Name of the legal case"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the case"
    )
    
    color = models.CharField(
        max_length=7,
        default='#FF8C00',
        help_text="Color code for UI identification (hex format)"
    )
    
    is_active = models.BooleanField(
        default=False,
        help_text="Whether this is the currently active case"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the case was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the case was last modified"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cases',
        db_index=True,
        help_text="User who owns this case"
    )
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Case'
        verbose_name_plural = 'Cases'
        unique_together = ['name', 'user']
    
    def __str__(self):
        return f"{self.name} (User: {self.user.username})"
    
    def get_absolute_url(self):
        """Get URL to view this case."""
        from django.urls import reverse
        return reverse('core:case_detail', args=[str(self.id)])
    
    @property
    def event_count(self):
        """Count of timeline events in this case."""
        return self.events.count()
    
    @property
    def document_count(self):
        """Count of archive documents in this case."""
        return self.documents.count()
    
    @classmethod
    def get_user_case(cls, user):
        """
        Get the first case for a user (or None if no cases exist).
        Returns the most recently updated case if user has multiple.
        """
        if not user or not user.is_authenticated:
            return None
        
        return cls.objects.filter(user=user).order_by('-updated_at').first()
    
    @classmethod
    def get_default_case(cls, user):
        """
        DEPRECATED: Use get_user_case() instead.
        This method now simply returns the user's first/most recent case.
        """
        return cls.get_user_case(user)
    
    def can_access(self, user):
        """
        Check if a user can access this case.
        
        Args:
            user: Django User object
            
        Returns:
            bool: True if user can access this case
        """
        return user.is_authenticated and user.id == self.user_id
    
    def can_edit(self, user):
        """
        Check if a user can edit this case.
        
        Args:
            user: Django User object
            
        Returns:
            bool: True if user can edit this case
        """
        return self.can_access(user)
    
    def can_delete(self, user):
        """
        Check if a user can delete this case.
        
        Args:
            user: Django User object
            
        Returns:
            bool: True if user can delete this case
        """
        return self.can_access(user)


class TimelineFile(models.Model):
    """
    Model for storing Markdown-based timeline files.
    
    Each TimelineFile represents a Markdown document that contains
    timeline events. These files can be parsed to extract headings and
    create dynamic timeline structures.
    
    Attributes:
        name: Human-readable name of the timeline
        file_path: Path to the Markdown file
        case: The case this timeline belongs to
        description: Description of what this timeline covers
        created_at: When the timeline file was created
        updated_at: When the timeline file was last modified
        user: The user who owns this timeline
    """
    
    name = models.CharField(
        max_length=255,
        help_text="Name of the timeline"
    )
    
    file_path = models.CharField(
        max_length=512,
        help_text="Path to the Markdown file"
    )
    
    case = models.ForeignKey(
        'Case',
        on_delete=models.CASCADE,
        related_name='timeline_files',
        null=True,
        blank=True,
        help_text="Case this timeline belongs to"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of what this timeline covers"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the timeline file was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the timeline file was last modified"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='timeline_files',
        help_text="User who owns this timeline"
    )
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Timeline File'
        verbose_name_plural = 'Timeline Files'
    
    def __str__(self):
        return f"{self.name} ({self.file_path})"
    
    def get_absolute_url(self):
        """Get URL to view this timeline."""
        from django.urls import reverse
        return reverse('timeline:view_timeline_file', args=[str(self.id)])
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'file_path': self.file_path,
            'case_id': self.case.id if self.case else None,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class RawDocument(models.Model):
    """
    Layer 1: Raw Document storage (Immutable).

    Stores original uploaded documents (PDFs, Markdown, JSON) with metadata.
    Once created, these documents cannot be modified if is_immutable is True.

    Attributes:
        id: UUID primary key
        case: ForeignKey to Case
        file: Uploaded file path
        file_type: Type of file (pdf, md, json)
        source_party: Who provided the document (CLIENT, OPPOSING, NEUTRAL)
        document_type: Type of document (e.g., "Motion to Dismiss", "Contract")
        reliability_note: Optional notes about reliability
        uploaded_at: When the document was uploaded
        is_immutable: Whether the document can be modified (default: True)
    """

    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('md', 'Markdown'),
        ('json', 'JSON'),
    ]

    SOURCE_PARTY_CHOICES = [
        ('CLIENT', 'Client'),
        ('OPPOSING', 'Opposing Party'),
        ('NEUTRAL', 'Neutral'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID primary key"
    )

    case = models.ForeignKey(
        'Case',
        on_delete=models.CASCADE,
        related_name='raw_documents',
        null=False,
        blank=False,
        help_text="Case this document belongs to"
    )

    file = models.FileField(
        upload_to=raw_document_upload_path,
        help_text="Uploaded document file"
    )

    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPE_CHOICES,
        help_text="Type of file (pdf, md, json)"
    )

    source_party = models.CharField(
        max_length=50,
        choices=SOURCE_PARTY_CHOICES,
        help_text="Who provided the document"
    )

    document_type = models.CharField(
        max_length=100,
        help_text="Type of document (e.g., Motion to Dismiss, Contract)"
    )

    reliability_note = models.TextField(
        blank=True,
        null=True,
        help_text="Optional notes about document reliability"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the document was uploaded"
    )

    is_immutable = models.BooleanField(
        default=True,
        help_text="Whether the document can be modified after creation"
    )

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Raw Document'
        verbose_name_plural = 'Raw Documents'

    def __str__(self):
        return f"{self.document_type} ({self.file_type}) - {self.case.name if self.case else 'No Case'}"

    def save(self, *args, **kwargs):
        """Override save to enforce immutability."""
        if self.is_immutable and self.pk is not None:
            raise ValueError("Cannot update an immutable RawDocument. Create a new document instead.")
        super().save(*args, **kwargs)


class WikiPage(models.Model):
    """
    Layer 2: Wiki Page with version history.

    Stores processed/normalized content derived from RawDocuments.
    Maintains version history and citation references.

    Attributes:
        id: UUID primary key
        case: ForeignKey to Case
        title: Page title (e.g., "timeline", "witness_list")
        content: Page content (Markdown)
        last_updated: When the page was last updated
        version_history: List of previous versions with content and timestamp
        citation_references: List of claim IDs and their sources
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID primary key"
    )

    case = models.ForeignKey(
        'Case',
        on_delete=models.CASCADE,
        related_name='wiki_pages',
        null=False,
        blank=False,
        help_text="Case this wiki page belongs to"
    )

    title = models.CharField(
        max_length=200,
        help_text="Page title (e.g., timeline, witness_list)"
    )

    content = models.TextField(
        help_text="Page content in Markdown"
    )

    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="When the page was last updated"
    )

    version_history = models.JSONField(
        default=list,
        help_text="List of previous versions with content and timestamp"
    )

    citation_references = models.JSONField(
        default=list,
        help_text="List of claim IDs and their sources"
    )

    CATEGORY_CHOICES = [
        ('VERIFIED', 'Stipulated/Verified'),
        ('CONTESTED', 'Contested Allegation'),
    ]

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='CONTESTED',
        help_text="Whether the content is Stipulated/Verified or Contested"
    )

    class Meta:
        ordering = ['-last_updated']
        verbose_name = 'Wiki Page'
        verbose_name_plural = 'Wiki Pages'
        unique_together = ['case', 'title']

    def __str__(self):
        return f"{self.title} - {self.case.name if self.case else 'No Case'}"

    def save(self, *args, **kwargs):
        """Override save to maintain version history."""
        if self.pk is not None:
            try:
                old_instance = WikiPage.objects.get(pk=self.pk)
                if old_instance.content != self.content:
                    self.version_history.append({
                        'content': old_instance.content,
                        'updated_at': old_instance.last_updated.isoformat() if old_instance.last_updated else None
                    })
            except WikiPage.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class SchemaRule(models.Model):
    """
    Layer 3: Schema Rules for LLM formatting.

    Stores rules that define how content should be formatted or structured
    when processing documents through LLMs.

    Attributes:
        id: UUID primary key
        case: ForeignKey to Case
        rule_name: Name of the rule (e.g., "timeline_formatting")
        rule_description: Description of what the rule does
        rule_content: Markdown or JSON rules for LLM formatting
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID primary key"
    )

    case = models.ForeignKey(
        'Case',
        on_delete=models.CASCADE,
        related_name='schema_rules',
        null=False,
        blank=False,
        help_text="Case this rule belongs to"
    )

    rule_name = models.CharField(
        max_length=200,
        help_text="Name of the rule (e.g., timeline_formatting)"
    )

    rule_description = models.TextField(
        help_text="Description of what the rule does"
    )

    rule_content = models.TextField(
        help_text="Markdown or JSON rules for LLM formatting"
    )

    class Meta:
        ordering = ['rule_name']
        verbose_name = 'Schema Rule'
        verbose_name_plural = 'Schema Rules'
        unique_together = ['case', 'rule_name']

    def __str__(self):
        return f"{self.rule_name} - {self.case.name if self.case else 'No Case'}"
