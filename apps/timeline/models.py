import uuid
from django.db import models
from django.conf import settings


class TimelineEvent(models.Model):
    """
    Model for timeline events in legal cases.
    
    Each event represents a significant occurrence in a legal case,
    with supporting documents and notes.
    
    Attributes:
        id: UUID primary key for shareable URLs
        date: Date of the event
        event: Title/name of the event
        category: Category (e.g., Verified, Contested, Contract, Email)
        source_type: How the event was created (Manual, Markdown, AI)
        supporting_docs: JSON field or list of ArchiveDocument IDs/URLs
        notes: Detailed notes about the event
        created_by: User who created this event
        timeline_file: ForeignKey to TimelineFile (source document)
        case: Case this event belongs to (for compartmentalization)
    """
    
    # Use UUID as primary key for shareable URLs
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    CATEGORY_CHOICES = [
        ('verified', 'Verified'),
        ('contested', 'Contested'),
        ('contract', 'Contract'),
        ('email', 'Email'),
        ('court_filing', 'Court Filing'),
        ('communication', 'Communication'),
        ('meeting', 'Meeting'),
        ('deadline', 'Deadline'),
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
    
    SOURCE_PARTY_CHOICES = [
        ('CLIENT', 'Client'),
        ('OPPOSING', 'Opposing Party'),
        ('NEUTRAL', 'Neutral'),
    ]
    
    date = models.DateField(help_text="Date of the event", db_index=True)
    event = models.CharField(max_length=255, help_text="Title or name of the event")
    category = models.CharField(
        max_length=100, 
        choices=CATEGORY_CHOICES,
        default='other',
        help_text="Category of the event (Verified/Contested/Other)"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default='MANUAL',
        help_text="How this event was created"
    )
    source_party = models.CharField(
        max_length=20,
        choices=SOURCE_PARTY_CHOICES,
        blank=True,
        null=True,
        help_text="Party associated with this event (Client/Opposing/Neutral)"
    )
    citation = models.CharField(
        max_length=500,
        blank=True,
        help_text="Citation or reference for this event"
    )
    
    # Supporting documents can be:
    # 1. JSON array of ArchiveDocument IDs: [1, 2, 3]
    # 2. JSON array of URLs: ["http://...", "..."]
    # 3. JSON object with description and URL: {"doc1": {"url": "...", "title": "..."}}
    # 4. Markdown-style links: "[Contract.pdf](url) [Email.pdf](url)"
    supporting_docs = models.JSONField(
        blank=True, 
        null=True,
        help_text="List of document references (IDs, URLs, or markdown links)"
    )
    
    notes = models.TextField(blank=True, help_text="Detailed notes about the event")
    
    # Link to TimelineFile (source document) - ForeignKey as requested
    timeline_file = models.ForeignKey(
        'core.TimelineFile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timeline_events',
        help_text="Source TimelineFile this event was parsed from"
    )
    
    # Case compartmentalization (required for data isolation)
    case = models.ForeignKey(
        'core.Case',
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
        blank=True,
        db_index=True,
        help_text="Case this event belongs to"
    )
    
    # User who created this event
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timeline_events_created'
    )
    
    class Meta:
        ordering = ['date']
        verbose_name = 'Timeline Event'
        verbose_name_plural = 'Timeline Events'
        # Deduplication constraint for sync
        unique_together = ['case', 'date', 'event']
    
    def __str__(self):
        return f"{self.date}: {self.event}"
    
    def get_absolute_url(self):
        """Get URL to view this event (shareable UUID-based URL)."""
        from django.urls import reverse
        return reverse('timeline:detail', args=[str(self.id)])
    
    def get_category_display(self):
        """Get human-readable category display."""
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category)
    
    def get_archive_documents(self):
        """
        Get linked ArchiveDocument objects.
        
        Supports multiple formats:
        - List of ArchiveDocument IDs: [1, 2, 3]
        - List of URLs: ["http://...", ...]
        - Markdown links: "[Contract.pdf](url)"
        """
        from apps.archive.models import ArchiveDocument
        
        if not self.supporting_docs:
            return ArchiveDocument.objects.none()
        
        documents = []
        
        # Case1: List of ArchiveDocument IDs or mixed
        if isinstance(self.supporting_docs, list):
            for item in self.supporting_docs:
                if isinstance(item, int):
                    doc = ArchiveDocument.objects.filter(id=item).first()
                    if doc:
                        documents.append(doc)
                elif isinstance(item, str):
                    # Could be a URL or ArchiveDocument ID as string
                    try:
                        doc_id = int(item)
                        doc = ArchiveDocument.objects.filter(id=doc_id).first()
                        if doc:
                            documents.append(doc)
                    except ValueError:
                        # It's a URL, skip (handled in template)
                        pass
                elif isinstance(item, dict):
                    # Could be {"id": 1} or {"url": "...", "title": "..."}
                    doc_id = item.get('id')
                    if doc_id:
                        try:
                            doc = ArchiveDocument.objects.filter(id=int(doc_id)).first()
                            if doc:
                                documents.append(doc)
                        except (ValueError, TypeError):
                            pass
        
        # Case2: String (markdown links or comma-separated IDs)
        elif isinstance(self.supporting_docs, str):
            # Try to parse as markdown links
            import re
            link_pattern = r'\[(.*?)\]\((.*?)\)'
            for match in re.finditer(link_pattern, self.supporting_docs):
                title, url = match.groups()
                # Try to find ArchiveDocument with this URL
                doc = ArchiveDocument.objects.filter(file=url).first()
                if doc:
                    documents.append(doc)
            
            # Try comma-separated IDs
            try:
                parts = self.supporting_docs.split(',')
                for doc_id in parts:
                    doc_id = doc_id.strip().strip('[]')
                    try:
                        doc = ArchiveDocument.objects.filter(id=int(doc_id)).first()
                        if doc:
                            documents.append(doc)
                    except ValueError:
                        pass
            except AttributeError:
                pass
        
        return documents
    
    def get_document_urls(self):
        """
        Extract all document URLs from supporting_docs field.
        
        Returns list of dicts with 'title' and 'url' keys.
        """
        import re
        
        if not self.supporting_docs:
            return []
        
        urls = []
        
        # If it's a list
        if isinstance(self.supporting_docs, list):
            for item in self.supporting_docs:
                if isinstance(item, dict):
                    urls.append({
                        'title': item.get('title', 'Document'),
                        'url': item.get('url', '')
                    })
                elif isinstance(item, str):
                    urls.append({'title': 'Document', 'url': item})
        
        # If it's a string, parse markdown links
        elif isinstance(self.supporting_docs, str):
            link_pattern = r'\[(.*?)\]\((.*?)\)'
            for match in re.finditer(link_pattern, self.supporting_docs):
                title, url = match.groups()
                urls.append({'title': title, 'url': url})
            
            # If no markdown links, try newline/comma separated
            if not urls:
                for line in self.supporting_docs.split('\n'):
                    line = line.strip()
                    if line:
                        urls.append({'title': line, 'url': line})
        
        return urls
