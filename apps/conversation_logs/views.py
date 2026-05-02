"""
Views for conversation logging and analytics.
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from apps.ai_assistant.models import AIConversation
from .models import ConversationLog, ConversationAnalytics
from .utils import (
    log_conversation_message, get_conversation_history,
    get_conversation_stats, add_conversation_feedback
)
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_log_message(request):
    """
    API endpoint to log a message to a conversation.
    
    Expects JSON:
    {
        'conversation_id': 'uuid',
        'message': 'message text',
        'sender': 'user|ai|system',  # optional, default 'user'
        'metadata': {}  # optional
    }
    """
    try:
        data = request.POST if request.content_type == 'application/x-www-form-urlencoded' else request.json()
        
        conversation_id = data.get('conversation_id')
        message = data.get('message', '')
        sender = data.get('sender', 'user')
        metadata = data.get('metadata', {})
        
        if not conversation_id or not message:
            return JsonResponse({'error': 'conversation_id and message are required'}, status=400)
        
        # Verify conversation exists and belongs to user
        conversation = get_object_or_404(AIConversation, id=conversation_id, user=request.user)
        
        # Log the message
        log_entry = log_conversation_message(conversation_id, message, sender, metadata)
        
        if log_entry:
            return JsonResponse({
                'status': 'success',
                'log_id': str(log_entry.id),
                'timestamp': log_entry.timestamp.isoformat()
            })
        else:
            return JsonResponse({'error': 'Failed to log message'}, status=500)
            
    except AIConversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found or access denied'}, status=404)
    except Exception as e:
        logger.error(f"API log message error: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["GET"])
def api_conversation_history(request, conversation_id):
    """
    API endpoint to get conversation history.
    
    Args:
        conversation_id: UUID of the conversation
        limit: Maximum number of messages (optional, default 50)
    """
    try:
        # Verify conversation exists and belongs to user
        conversation = get_object_or_404(AIConversation, id=conversation_id, user=request.user)
        
        limit = int(request.GET.get('limit', 50))
        
        history = get_conversation_history(conversation_id, limit)
        
        return JsonResponse({
            'status': 'success',
            'conversation_id': str(conversation_id),
            'history': history
        })
        
    except AIConversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found or access denied'}, status=404)
    except Exception as e:
        logger.error(f"API conversation history error: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["GET"])
def api_conversation_stats(request, conversation_id):
    """
    API endpoint to get conversation statistics.
    
    Args:
        conversation_id: UUID of the conversation
    """
    try:
        # Verify conversation exists and belongs to user
        conversation = get_object_or_404(AIConversation, id=conversation_id, user=request.user)
        
        stats = get_conversation_stats(conversation_id)
        
        if stats:
            return JsonResponse({
                'status': 'success',
                'conversation_id': str(conversation_id),
                'stats': stats
            })
        else:
            return JsonResponse({
                'status': 'success',
                'conversation_id': str(conversation_id),
                'stats': {}
            })
            
    except AIConversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found or access denied'}, status=404)
    except Exception as e:
        logger.error(f"API conversation stats error: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_add_feedback(request, conversation_id):
    """
    API endpoint to add feedback to a conversation.
    
    Expects JSON:
    {
        'rating': 1-5,  # optional
        'feedback': 'text'  # optional
    }
    """
    try:
        # Verify conversation exists and belongs to user
        conversation = get_object_or_404(AIConversation, id=conversation_id, user=request.user)
        
        data = request.POST if request.content_type == 'application/x-www-form-urlencoded' else request.json()
        
        rating = data.get('rating')
        feedback = data.get('feedback', '')
        
        if rating:
            try:
                rating = float(rating)
                if not (1.0 <= rating <= 5.0):
                    return JsonResponse({'error': 'Rating must be between 1 and 5'}, status=400)
            except ValueError:
                return JsonResponse({'error': 'Rating must be a number'}, status=400)
        
        success = add_conversation_feedback(conversation_id, rating, feedback)
        
        if success:
            return JsonResponse({
                'status': 'success',
                'conversation_id': str(conversation_id),
                'message': 'Feedback added successfully'
            })
        else:
            return JsonResponse({'error': 'Failed to add feedback'}, status=500)
            
    except AIConversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found or access denied'}, status=404)
    except Exception as e:
        logger.error(f"API add feedback error: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
def conversation_analytics_dashboard(request):
    """
    Dashboard view showing conversation analytics.
    """
    # Get all conversations for this user
    conversations = AIConversation.objects.filter(user=request.user).order_by('-updated_at')
    
    # Get analytics for each conversation
    conversation_data = []
    for conv in conversations:
        stats = get_conversation_stats(conv.id)
        if stats:
            conversation_data.append({
                'conversation': conv,
                'stats': stats
            })
    
    context = {
        'conversations': conversation_data,
        'total_conversations': len(conversations),
        'active_conversations': len([c for c in conversations if not c.analytics.ended_at])
    }
    
    return render(request, 'conversation_logs/analytics_dashboard.html', context)


@login_required
def conversation_history_view(request, conversation_id):
    """
    View to display the full history of a conversation.
    """
    # Get the conversation
    conversation = get_object_or_404(AIConversation, id=conversation_id, user=request.user)
    
    # Get full history
    history = get_conversation_history(conversation_id)
    
    # Get stats
    stats = get_conversation_stats(conversation_id)
    
    context = {
        'conversation': conversation,
        'history': history,
        'stats': stats
    }
    
    return render(request, 'conversation_logs/conversation_history.html', context)