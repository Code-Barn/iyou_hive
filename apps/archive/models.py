from django.db import models
from django.conf import settings


class ArchiveDocument(models.Model):
    """
    Model for storing legal documents in the archive.
    
    Attributes:
        title: Human-readable title of the document
        file: The actual document file (PDF, image, etc.)
        file_type: Type of document (pdf, image, text, etc.)
        upload_date: When the document was uploaded
        category: Optional category for grouping documents
        tags: JSON array of tags for easier filtering
        metadata: Additional metadata extracted from the document
        timeline_event: Foreign key to linked TimelineEvent (if applicable)
        uploader: User who uploaded the document
    """
    
    DOCUMENT_TYPES = [
        ('pdf', 'PDF'),
        ('image', 'Image'),
        ('text', 'Text'),
        ('word', 'Word Document'),
        ('email', 'Email'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=255, help_text="Title of the document")
    file = models.FileField(upload_to='archive/documents/', help_text="Document file")
    file_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='pdf')
    upload_date = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=100, blank=True, null=True, 
                               help_text="Document category (e.g., Contract, Email, Court Filing)")
    tags = models.JSONField(default=list, blank=True, help_text="List of tags for filtering")
    metadata = models.JSONField(default=dict, blank=True, help_text="Extracted metadata (author, date, etc.)")
    description = models.TextField(blank=True, help_text="Description of document contents")
    
    # Relationships
    timeline_event = models.ForeignKey(
        'timeline.TimelineEvent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archive_documents',
        help_text="Linked timeline event (if any)"
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents'
    )
    
    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'Archive Document'
        verbose_name_plural = 'Archive Documents'
    
    def __str__(self):
        return f"{self.title} ({self.file_type})"
    
    def get_absolute_url(self):
        """Get URL to view this document."""
        from django.urls import reverse
        return reverse('archive:document_detail', args=[str(self.id)])
    
    def get_file_url(self):
        """Get URL to the document file."""
        if self.file:
            return self.file.url
        return ""
    
    def get_file_extension(self):
        """Get the file extension."""
        if self.file:
            return self.file.name.split('.')[-1].lower()
        return ""
    
    def is_pdf(self):
        """Check if document is a PDF."""
        return self.get_file_extension() == 'pdf' or self.file_type == 'pdf'
    
    def is_image(self):
        """Check if document is an image."""
        return self.get_file_extension() in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'] or self.file_type == 'image'
    
    def get_thumbnail_url(self):
        """Get URL to thumbnail (for images)."""
        if self.is_image():
            # In production, this would use a thumbnail service
            # For now, return the original image
            return self.get_file_url()
        return None
