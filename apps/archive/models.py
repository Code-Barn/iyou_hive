# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from django.db import models
from django.conf import settings
import os
import hashlib
import uuid


class ArchiveDocument(models.Model):
    """
    Model for storing legal documents in the archive.

    Attributes:
    uuid: Unique identifier for portability across server instances
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
    
    # UUID for portability across server instances (Hive Portability)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Unique identifier for portability across server instances"
    )
    
    DOCUMENT_TYPES = [
        ('pdf', 'PDF'),
        ('image', 'Image'),
        ('text', 'Text'),
        ('word', 'Word Document'),
        ('email', 'Email'),
        ('folder', 'Folder'),
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
    promoted_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this document was promoted to formal evidence"
    )
    is_promoted = models.BooleanField(
        default=False,
        help_text="Whether this document has been promoted to formal evidence"
    )
    category = models.CharField(max_length=100, blank=True, null=True, 
                               help_text="Document category (e.g., Contract, Email, Court Filing)")
    tags = models.JSONField(default=list, blank=True, help_text="List of tags for filtering")
    metadata = models.JSONField(default=dict, blank=True, help_text="Extracted metadata (author, date, etc.)")
    description = models.TextField(blank=True, help_text="Description of document contents")

    # Conversion fields
    conversion_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PROCESSING', 'Processing'),
            ('SUCCESS', 'Success'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING',
        help_text="Status of PDF to Markdown conversion"
    )
    markdown_path = models.CharField(
        max_length=512,
        blank=True,
        help_text="Path to the converted Markdown file"
    )
    conversion_error = models.TextField(
        blank=True,
        help_text="Error message if conversion failed"
    )
    extracted_text = models.TextField(
        blank=True,
        help_text="Extracted text content from the document"
    )
    text_extraction_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PROCESSING', 'Processing'),
            ('SUCCESS', 'Success'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING',
        help_text="Status of text extraction"
    )
    
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
    
    @staticmethod
    def create_standard_folder_structure(case, user):
        """
        Create logical folder placeholder records for a new case archive.

        Creates database-only folder markers — no physical files are written
        to disk. The folders exist purely in the ``virtual_path`` metadata
        that the ``RecursiveFolderSerializer`` uses to build the UI tree.

        Folders:
        01_Raw       — Original uploaded documents and source materials
        02_Wiki      — Processed and cleaned documents for reference
        03_Drafts    — Working drafts and editable documents
        04_Strategy  — Strategy documents and case planning materials
        05_Exports   — Export outputs, reports, and final deliverables
        """
        folder_structure: list[tuple[str, str]] = [
            ('01_Raw', 'Original uploaded documents and source materials'),
            ('02_Wiki', 'Processed and cleaned documents for reference'),
            ('03_Drafts', 'Working drafts and editable documents'),
            ('04_Strategy', 'Strategy documents and case planning materials'),
            ('05_Exports', 'Export outputs, reports, and final deliverables'),
        ]

        created_folders: list[ArchiveDocument] = []

        for folder_name, folder_description in folder_structure:
            try:
                folder_doc: ArchiveDocument = ArchiveDocument.objects.create(
                    title=f"[FOLDER] {folder_name}",
                    file_type='folder',
                    path=f"{folder_name}/",
                    description=folder_description,
                    is_draft=False,
                    is_immutable=True,
                    case=case,
                    user=user,
                    uploader=user,
                    metadata={'virtual_path': f"{folder_name}/"}
                )
                created_folders.append(folder_doc)
            except Exception as e:
                print(f"Warning: Could not create folder {folder_name}: {e}")
                continue

        return created_folders
    
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


class Photo(models.Model):
    """
    Model for storing photos with EXIF metadata for forensic timelines.
    """
    file = models.ImageField(upload_to='archive/photos/', help_text="Photo file")
    timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp from EXIF DateTimeOriginal"
    )
    gps_latitude = models.FloatField(
        null=True,
        blank=True,
        help_text="GPS latitude from EXIF"
    )
    gps_longitude = models.FloatField(
        null=True,
        blank=True,
        help_text="GPS longitude from EXIF"
    )
    device = models.CharField(
        max_length=255,
        blank=True,
        help_text="Device make and model from EXIF"
    )
    sha256_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 hash for tamper detection"
    )
    case = models.ForeignKey(
        'core.Case',
        on_delete=models.CASCADE,
        related_name='photos',
        null=True,
        blank=True,
        db_index=True,
        help_text="Case this photo belongs to"
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_photos',
        db_index=True,
        help_text="User who uploaded this photo"
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'Photo'
        verbose_name_plural = 'Photos'
    
    def __str__(self):
        return f"{self.file.name} ({self.timestamp})"
    
    def get_absolute_url(self):
        """Get URL to view this photo."""
        from django.urls import reverse
        return reverse('archive:photo_detail', args=[str(self.id)])
    
    def get_file_url(self):
        """Get URL to the photo file."""
        if self.file:
            return self.file.url
        return ""
    
    def calculate_sha256(self):
        """Calculate SHA-256 hash of the photo file."""
        if self.file:
            sha256 = hashlib.sha256()
            for chunk in self.file.chunks():
                sha256.update(chunk)
            return sha256.hexdigest()
        return ""
    
    def save(self, *args, **kwargs):
        """Auto-calculate SHA-256 hash on save."""
        if not self.sha256_hash:
            self.sha256_hash = self.calculate_sha256()
        super().save(*args, **kwargs)
    
    def verify_hash(self):
        """Verify the SHA-256 hash of the photo file."""
        current_hash = self.calculate_sha256()
        return current_hash == self.sha256_hash


class CloudImport(models.Model):
    """
    Model for tracking cloud storage imports (Dropbox/Google Drive/OneDrive).
    """
    CLOUD_PROVIDERS = [
        ('dropbox', 'Dropbox'),
        ('google_drive', 'Google Drive'),
        ('onedrive', 'OneDrive'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cloud_imports',
        db_index=True,
        help_text="User who owns this import"
    )
    case = models.ForeignKey(
        'core.Case',
        on_delete=models.CASCADE,
        related_name='cloud_imports',
        null=True,
        blank=True,
        db_index=True,
        help_text="Case this import belongs to"
    )
    provider = models.CharField(
        max_length=50,
        choices=CLOUD_PROVIDERS,
        help_text="Cloud storage provider"
    )
    access_token = models.CharField(
        max_length=512,
        blank=True,
        help_text="OAuth2 access token"
    )
    refresh_token = models.CharField(
        max_length=512,
        blank=True,
        help_text="OAuth2 refresh token"
    )
    token_expires = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the access token expires"
    )
    folder_path = models.CharField(
        max_length=512,
        blank=True,
        help_text="Path to the folder being imported"
    )
    last_imported = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the last import was performed"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this import is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Cloud Import'
        verbose_name_plural = 'Cloud Imports'
    
    def __str__(self):
        return f"{self.provider}: {self.folder_path}"
    
    def is_token_expired(self):
        """Check if the access token is expired."""
        if not self.token_expires:
            return True
        return timezone.now() > self.token_expires
    
    def refresh_access_token(self):
        """Refresh the access token using the refresh token."""
        # Placeholder for OAuth2 token refresh logic
        pass


class CustodyLog(models.Model):
    """
    Model for tracking all actions on photos for forensic integrity.
    """
    ACTION_TYPES = [
        ('UPLOAD', 'Upload'),
        ('VIEW', 'View'),
        ('EDIT', 'Edit'),
        ('DELETE', 'Delete'),
        ('EXPORT', 'Export'),
        ('ANALYZE', 'Analyze'),
        ('LINK', 'Link to Event'),
        ('UNLINK', 'Unlink from Event'),
    ]
    
    photo = models.ForeignKey(
        'Photo',
        on_delete=models.CASCADE,
        related_name='custody_logs',
        db_index=True,
        help_text="Photo this action relates to"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='photo_custody_logs',
        db_index=True,
        help_text="User who performed the action"
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        help_text="Type of action performed"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the user"
    )
    user_agent = models.CharField(
        max_length=512,
        blank=True,
        help_text="User agent string"
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional details about the action"
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Custody Log'
        verbose_name_plural = 'Custody Logs'
    
    def __str__(self):
        return f"{self.action}: {self.photo.file.name} by {self.user}"


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
