from django.db import models
from django.conf import settings


class ArchiveDocument(models.Model):
    """
    Model for storing legal documents in the archive.
    
    Attributes:
        title: Human-readable title of the document
        file: The actual document file (PDF, image, etc.)
        file_type: Type of document (pdf, image, text, etc.)
        path: Relative path for folder structure (e.g., "court_documents/subfolder/file.pdf")
        is_draft: Whether this file is a draft (editable)
        is_immutable: Whether this file is read-only (true for all non-drafts)
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
    file_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='pdf', db_index=True)
    path = models.CharField(
        max_length=512, 
        blank=True, 
        help_text="Relative path for folder structure (e.g., 'court_documents/subfolder/file.pdf')"
    )
    is_draft = models.BooleanField(
        default=False,
        help_text="Whether this is a draft document (editable)"
    )
    is_immutable = models.BooleanField(
        default=True,
        help_text="Read-only to preserve integrity (automatically True for non-drafts)"
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=100, blank=True, null=True, 
                               help_text="Document category (e.g., Contract, Email, Court Filing)")
    tags = models.JSONField(default=list, blank=True, help_text="List of tags for filtering")
    metadata = models.JSONField(default=dict, blank=True, help_text="Extracted metadata (author, date, etc.)")
    description = models.TextField(blank=True, help_text="Description of document contents")
    
    # Relationships (case required for data isolation)
    case = models.ForeignKey(
        'core.Case',
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True,
        db_index=True,
        help_text="Case this document belongs to"
    )
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
        related_name='uploaded_documents',
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archive_documents',
        db_index=True,
        help_text="User who owns this document"
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
    
    def save(self, *args, **kwargs):
        """Auto-set is_immutable based on is_draft."""
        if self.is_draft:
            self.is_immutable = False
        else:
            self.is_immutable = True
        super().save(*args, **kwargs)


class SyncedArchive(models.Model):
    """
    Model for tracking external storage sync (GitHub, Google Drive, local folders).
    """
    
    PROVIDERS = [
        ('github', 'GitHub'),
        ('google_drive', 'Google Drive'),
        ('local', 'Local Folder'),
    ]
    
    case = models.ForeignKey(
        'core.Case',
        on_delete=models.CASCADE,
        related_name='sync_configs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sync_configs'
    )
    provider = models.CharField(max_length=50, choices=PROVIDERS)
    external_path = models.CharField(max_length=512, help_text="GitHub repo URL or local path")
    access_token = models.CharField(max_length=512, blank=True, help_text="For cloud providers")
    last_synced = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Synced Archive'
        verbose_name_plural = 'Synced Archives'
    
    def __str__(self):
        return f"{self.provider}: {self.external_path}"
    
    def sync(self):
        """Pull files from external storage into Hiver."""
        if self.provider == 'github':
            return self._sync_github()
        elif self.provider == 'google_drive':
            return self._sync_google_drive()
        elif self.provider == 'local':
            return self._sync_local_folder()
    
    def _sync_github(self):
        """Sync from GitHub repository."""
        try:
            from github import Github
            g = Github(self.access_token)
            repo = g.get_repo(self.external_path)
            contents = repo.get_contents('')
            
            synced_count = 0
            for content in contents:
                if content.type == 'file' and not content.name.startswith('.'):
                    # Download and save file
                    file_content = content.decoded_content
                    from django.core.files.base import ContentFile
                    doc = ArchiveDocument(
                        case=self.case,
                        user=self.user,
                        title=content.name,
                        path=content.path,
                        is_draft=False,
                        is_immutable=True,
                        file=ContentFile(file_content),
                        file_type=self._guess_file_type(content.name)
                    )
                    doc.save()
                    synced_count += 1
            
            self.last_synced = models.functions.Now()
            self.save()
            return synced_count
        except Exception as e:
            return 0
    
    def _sync_google_drive(self):
        """Sync from Google Drive (placeholder)."""
        # Requires Google API client setup
        return 0
    
    def _sync_local_folder(self):
        """Sync from local folder."""
        import os
        synced_count = 0
        
        if not os.path.exists(self.external_path):
            return 0
        
        for root, dirs, files in os.walk(self.external_path):
            for filename in files:
                if filename.startswith('.'):
                    continue
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, self.external_path)
                
                with open(filepath, 'rb') as f:
                    from django.core.files.base import ContentFile
                    doc = ArchiveDocument(
                        case=self.case,
                        user=self.user,
                        title=filename,
                        path=rel_path,
                        is_draft=False,
                        is_immutable=True,
                        file=ContentFile(f.read()),
                        file_type=self._guess_file_type(filename)
                    )
                    doc.save()
                    synced_count += 1
        
        self.last_synced = models.functions.Now()
        self.save()
        return synced_count
    
    def _guess_file_type(self, filename):
        """Guess file type from extension."""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        type_map = {
            'pdf': 'pdf', 'png': 'image', 'jpg': 'image', 'jpeg': 'image',
            'gif': 'image', 'webp': 'image', 'svg': 'image',
            'doc': 'word', 'docx': 'word',
            'txt': 'text', 'md': 'markdown', 'markdown': 'markdown',
            'eml': 'email', 'msg': 'email',
        }
        return type_map.get(ext, 'other')
