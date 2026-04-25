from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    path('', views.ai_chat_view, name='chat'),
    path('analyze/', views.analyze_document, name='analyze'),
]