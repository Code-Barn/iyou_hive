from django.db import models
from django.conf import settings
from django.utils import timezone


class Case(models.Model):
    """
    Model for legal case compartmentalization.
    
    Each case acts as a container for timeline events, archive documents,
    and AI assistant context. Users can switch between cases to isolate
    their work on different legal matters.
    
    Attributes:
        name: Human-readable name of the case
        description: Detailed description of the case
        color: Color code for UI identification (e.g., '#FF8C00' for honey-orange)
        is_active: Whether this is the user's currently active case
        created_at: When the case was created
        updated_at: When the case was last modified
        user: The user who owns this case
    """
    
    name = models.CharField(
        max_length=255,
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
    def get_default_case(cls, user):
        """
        Get or create a default case for a user.
        
        Creates a 'Default Case' if none exists.
        """
        if not user or not user.is_authenticated:
            return None
        
        default_case, created = cls.objects.get_or_create(
            user=user,
            name='Default Case',
            defaults={
                'description': 'Your default legal case',
                'color': '#FF8C00',
                'is_active': True
            }
        )
        
        # Ensure it's marked as active
        if not default_case.is_active:
            # Deactivate other cases for this user
            cls.objects.filter(user=user).update(is_active=False)
            default_case.is_active = True
            default_case.save()
        
        return default_case
    
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
