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


class UserSettings(models.Model):
    """
    Model for storing user-specific settings including API keys.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='settings',
        help_text="User who owns these settings"
    )
    
    mistral_api_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Mistral AI API key for this user"
    )

    gemini_api_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Google Gemini API key for this user"
    )

    PROVIDER_CHOICES = [
        ('mistral', 'Mistral AI'),
        ('gemini', 'Google Gemini'),
    ]

    preferred_ai_provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default='mistral',
        help_text="Preferred AI provider for the assistant"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the settings were created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the settings were last updated"
    )
    
    class Meta:
        verbose_name = 'User Setting'
        verbose_name_plural = 'User Settings'
    
    def __str__(self):
        return f"Settings for {self.user.username}"


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