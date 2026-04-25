from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    path('', views.ai_chat_view, name='chat'),
    path('analyze/', views.analyze_document, name='analyze'),
    path('query-timeline/', views.query_timeline, name='query_timeline'),
    path('suggest-events/', views.suggest_events, name='suggest_events'),
    path('analyze-event/<int:event_id>/', views.analyze_timeline_event, name='analyze_event'),
]
