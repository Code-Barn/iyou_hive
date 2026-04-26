from django.db import models
from django.conf import settings


class AIConversation(models.Model):
    """
    Model for storing AI assistant conversations.
    
    Each conversation is linked to a case for compartmentalization.
    """

    title = models.CharField(
        max_length=255,
        default="New Conversation",
        help_text="Title of the conversation"
    )

    case = models.ForeignKey(
        'core.Case',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ai_conversations',
        db_index=True,
        help_text="Case this conversation belongs to"
    )

    messages = models.JSONField(
        default=list,
        blank=True,
        help_text="List of message objects in the conversation"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the conversation was created"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the conversation was last updated"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_conversations',
        db_index=True,
        help_text="User who owns this conversation"
    )

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'AI Conversation'
        verbose_name_plural = 'AI Conversations'

    def __str__(self):
        return f"{self.title} (User: {self.user.username})"