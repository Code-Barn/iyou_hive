from django.urls import path
from . import views

app_name = 'timeline'

urlpatterns = [
    path('', views.timeline_view, name='timeline'),
    path('upload/', views.upload_markdown, name='upload'),
    path('event/<int:pk>/', views.event_detail, name='detail'),
]