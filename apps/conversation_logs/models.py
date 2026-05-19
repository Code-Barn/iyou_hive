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


class ConversationLog(models.Model):
    """
    Model for storing individual messages in AI conversations.
    
    Each log entry represents a single message in a conversation,
    with metadata about the sender, timestamp, and content.
    """
    
    conversation = models.ForeignKey(
        'ai_assistant.AIConversation',
        on_delete=models.CASCADE,
        related_name='logs',
        help_text="The AI conversation this message belongs to"
    )
    
    message = models.TextField(
        help_text="The content of the message"
    )
    
    sender = models.CharField(
        max_length=20,
        choices=[
            ('user', 'User'),
            ('ai', 'AI Assistant'),
            ('system', 'System')
        ],
        default='user',
        help_text="Who sent this message (user, ai, or system)"
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the message was sent"
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (e.g., message type, references)"
    )
    
    # Index for better performance on queries
    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Conversation Log'
        verbose_name_plural = 'Conversation Logs'
        indexes = [
            models.Index(fields=['conversation']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['sender']),
        ]
    
    def __str__(self):
        return f"{self.get_sender_display()} message in {self.conversation.title}"


class ConversationAnalytics(models.Model):
    """
    Model for storing analytics and metrics about conversations.
    
    Tracks usage patterns, response times, and other metrics
    for monitoring and improvement purposes.
    """
    
    conversation = models.OneToOneField(
        'ai_assistant.AIConversation',
        on_delete=models.CASCADE,
        related_name='analytics',
        help_text="The conversation this analytics data belongs to"
    )
    
    # Usage metrics
    message_count = models.IntegerField(
        default=0,
        help_text="Total number of messages in conversation"
    )
    
    user_message_count = models.IntegerField(
        default=0,
        help_text="Number of messages from user"
    )
    
    ai_message_count = models.IntegerField(
        default=0,
        help_text="Number of messages from AI"
    )
    
    # Timing metrics
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the conversation started"
    )
    
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the conversation ended (null if ongoing)"
    )
    
    duration_seconds = models.IntegerField(
        default=0,
        help_text="Duration of conversation in seconds"
    )
    
    # Content metrics
    total_characters = models.IntegerField(
        default=0,
        help_text="Total characters in all messages"
    )
    
    user_characters = models.IntegerField(
        default=0,
        help_text="Characters from user messages"
    )
    
    ai_characters = models.IntegerField(
        default=0,
        help_text="Characters from AI messages"
    )
    
    # Quality metrics (could be populated by feedback or analysis)
    user_rating = models.FloatField(
        null=True,
        blank=True,
        help_text="User rating of conversation quality (1-5)"
    )
    
    user_feedback = models.TextField(
        blank=True,
        help_text="User feedback about the conversation"
    )
    
    class Meta:
        verbose_name = 'Conversation Analytics'
        verbose_name_plural = 'Conversation Analytics'
    
    def __str__(self):
        return f"Analytics for {self.conversation.title}"
