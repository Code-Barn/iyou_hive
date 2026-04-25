from django.urls import path
from . import views

app_name = 'archive'

urlpatterns = [
    path('', views.archive_view, name='archive'),
    path('upload/', views.upload_document, name='upload'),
    path('document/<int:pk>/', views.document_detail, name='document_detail'),
    path('document/<int:pk>/file/', views.document_file, name='document_file'),
    path('document/<int:pk>/thumbnail/', views.document_thumbnail, name='document_thumbnail'),
    
    # API endpoints
    path('api/documents/', views.api_document_list, name='api_document_list'),
    path('api/search/', views.api_document_search, name='api_document_search'),
    path('api/map/', views.generate_archive_map, name='api_generate_map'),
    path('api/link/<int:document_id>/to-event/<int:event_id>/', 
         views.link_to_timeline, 
         name='api_link_to_timeline'),
]
