"""
URL patterns for conversation logging and analytics.
"""

from django.urls import path
from . import views

app_name = 'conversation_logs'

urlpatterns = [
    # API Endpoints
    path('api/log-message/', views.api_log_message, name='api_log_message'),
    path('api/conversation/<uuid:conversation_id>/history/', views.api_conversation_history, name='api_conversation_history'),
    path('api/conversation/<uuid:conversation_id>/stats/', views.api_conversation_stats, name='api_conversation_stats'),
    path('api/conversation/<uuid:conversation_id>/feedback/', views.api_add_feedback, name='api_add_feedback'),
    
    # Web Views
    path('analytics/', views.conversation_analytics_dashboard, name='analytics_dashboard'),
    path('conversation/<uuid:conversation_id>/history/', views.conversation_history_view, name='conversation_history'),
]