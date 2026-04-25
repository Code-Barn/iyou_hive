from django.urls import path
from . import views

app_name = 'conversation_logs'

urlpatterns = [
    path('', views.messages_view, name='messages'),
    path('upload/', views.upload_messages, name='upload'),
    path('conversation/<int:pk>/', views.conversation_detail, name='detail'),
]