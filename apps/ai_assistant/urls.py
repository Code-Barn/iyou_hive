from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    path('', views.ai_chat_view, name='chat'),
    path('analyze/', views.analyze_document, name='analyze'),
    path('query-timeline/', views.query_timeline, name='query_timeline'),
    path('suggest-events/', views.suggest_events, name='suggest_events'),
    path('analyze-event/<uuid:event_id>/', views.analyze_timeline_event, name='analyze_event'),
    path('save-api-key/', views.save_api_key, name='save_api_key'),
]
