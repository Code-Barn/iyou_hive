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

"""
Utility functions for conversation logging and analytics.
"""

from django.utils import timezone
from .models import ConversationLog, ConversationAnalytics
from apps.ai_assistant.models import AIConversation
import logging

logger = logging.getLogger(__name__)


def log_conversation_message(conversation_id, message, sender='user', metadata=None):
    """
    Log a message to a conversation.
    
    Args:
        conversation_id: ID of the AIConversation
        message: Message content
        sender: 'user', 'ai', or 'system'
        metadata: Additional metadata dict
        
    Returns:
        ConversationLog: The created log entry
    """
    try:
        # Get or create analytics for this conversation
        analytics, created = ConversationAnalytics.objects.get_or_create(
            conversation_id=conversation_id
        )
        
        # Create the log entry
        log_entry = ConversationLog.objects.create(
            conversation_id=conversation_id,
            message=message,
            sender=sender,
            metadata=metadata or {}
        )
        
        # Update analytics
        if sender == 'user':
            analytics.user_message_count += 1
            analytics.user_characters += len(message)
        elif sender == 'ai':
            analytics.ai_message_count += 1
            analytics.ai_characters += len(message)
        
        analytics.message_count += 1
        analytics.total_characters += len(message)
        analytics.save()
        
        logger.info(f"Logged {sender} message to conversation {conversation_id}")
        return log_entry
        
    except AIConversation.DoesNotExist:
        logger.error(f"Conversation {conversation_id} not found for logging")
        return None
    except Exception as e:
        logger.error(f"Failed to log conversation message: {e}")
        return None


def start_conversation_analytics(conversation_id):
    """
    Initialize analytics for a new conversation.
    
    Args:
        conversation_id: ID of the AIConversation
        
    Returns:
        ConversationAnalytics: The created analytics object
    """
    try:
        analytics, created = ConversationAnalytics.objects.get_or_create(
            conversation_id=conversation_id,
            defaults={
                'started_at': timezone.now(),
                'message_count': 0,
                'user_message_count': 0,
                'ai_message_count': 0,
                'total_characters': 0,
                'user_characters': 0,
                'ai_characters': 0,
                'duration_seconds': 0
            }
        )
        
        if created:
            logger.info(f"Initialized analytics for conversation {conversation_id}")
        
        return analytics
    except Exception as e:
        logger.error(f"Failed to initialize conversation analytics: {e}")
        return None


def end_conversation_analytics(conversation_id):
    """
    Mark a conversation as ended and calculate final metrics.
    
    Args:
        conversation_id: ID of the AIConversation
        
    Returns:
        ConversationAnalytics: The updated analytics object
    """
    try:
        analytics = ConversationAnalytics.objects.get(conversation_id=conversation_id)
        
        if not analytics.ended_at:
            analytics.ended_at = timezone.now()
            # Calculate duration
            if analytics.started_at:
                duration = analytics.ended_at - analytics.started_at
                analytics.duration_seconds = int(duration.total_seconds())
            analytics.save()
            logger.info(f"Ended conversation {conversation_id} with {analytics.message_count} messages")
        
        return analytics
    except ConversationAnalytics.DoesNotExist:
        logger.warning(f"No analytics found for conversation {conversation_id}")
        return None
    except Exception as e:
        logger.error(f"Failed to end conversation analytics: {e}")
        return None


def get_conversation_history(conversation_id, limit=50):
    """
    Get the message history for a conversation.
    
    Args:
        conversation_id: ID of the AIConversation
        limit: Maximum number of messages to return
        
    Returns:
        list: List of message dictionaries
    """
    try:
        logs = ConversationLog.objects.filter(
            conversation_id=conversation_id
        ).order_by('timestamp')[:limit]
        
        return [{
            'id': log.id,
            'message': log.message,
            'sender': log.sender,
            'timestamp': log.timestamp.isoformat(),
            'metadata': log.metadata
        } for log in logs]
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        return []


def get_conversation_stats(conversation_id):
    """
    Get statistics for a conversation.
    
    Args:
        conversation_id: ID of the AIConversation
        
    Returns:
        dict: Statistics dictionary
    """
    try:
        analytics = ConversationAnalytics.objects.get(conversation_id=conversation_id)
        
        return {
            'message_count': analytics.message_count,
            'user_message_count': analytics.user_message_count,
            'ai_message_count': analytics.ai_message_count,
            'total_characters': analytics.total_characters,
            'user_characters': analytics.user_characters,
            'ai_characters': analytics.ai_characters,
            'started_at': analytics.started_at.isoformat() if analytics.started_at else None,
            'ended_at': analytics.ended_at.isoformat() if analytics.ended_at else None,
            'duration_seconds': analytics.duration_seconds,
            'user_rating': analytics.user_rating,
            'user_feedback': analytics.user_feedback
        }
    except ConversationAnalytics.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Failed to get conversation stats: {e}")
        return None


def add_conversation_feedback(conversation_id, rating=None, feedback=None):
    """
    Add user feedback to a conversation.
    
    Args:
        conversation_id: ID of the AIConversation
        rating: User rating (1-5)
        feedback: User feedback text
        
    Returns:
        bool: True if successful
    """
    try:
        analytics = ConversationAnalytics.objects.get(conversation_id=conversation_id)
        
        if rating is not None:
            analytics.user_rating = float(rating)
        
        if feedback is not None:
            analytics.user_feedback = feedback
        
        analytics.save()
        logger.info(f"Added feedback to conversation {conversation_id}")
        return True
    except ConversationAnalytics.DoesNotExist:
        logger.warning(f"No analytics found for conversation {conversation_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to add conversation feedback: {e}")
        return False