from django.urls import path
from . import views

app_name = 'timeline'

urlpatterns = [
    path('', views.timeline_view, name='timeline'),
    path('upload/', views.upload_markdown, name='upload'),
    path('event/<int:pk>/', views.event_detail, name='detail'),
    path('create-event/', views.create_event, name='create_event'),
    # Timeline file APIs
    path('api/load-timeline/', views.load_timeline_file, name='load_timeline_file'),
    path('api/timeline-headings/', views.api_timeline_headings, name='api_timeline_headings'),
    path('select-timeline/', views.select_timeline, name='select_timeline'),
    path('api/create-timeline-file/', views.create_timeline_file, name='create_timeline_file'),
]