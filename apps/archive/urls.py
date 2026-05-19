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

from django.urls import path
from . import views
from .api_views import DocumentUploadView

app_name = 'archive'

urlpatterns = [
    path('', views.archive_view, name='archive'),
    path('upload/', views.upload_document, name='upload'),
    path('document/<int:pk>/', views.document_detail, name='document_detail'),
    path('document/<int:pk>/file/', views.document_file, name='document_file'),
    path('document/<int:pk>/thumbnail/', views.document_thumbnail, name='document_thumbnail'),
    
    # Bulk operations
    path('api/bulk-upload/', views.bulk_upload, name='bulk_upload'),
    path('api/download/', views.download_archive, name='download_archive'),
    
    # Sync operations
    path('api/sync/create/', views.create_sync_config, name='create_sync'),
    path('api/sync/<int:sync_id>/', views.sync_archive, name='sync_archive'),
    
    # Document operations
    path('api/document/<int:pk>/save/', views.save_document, name='save_document'),
    
    # Existing API endpoints
    path('api/documents/', views.api_document_list, name='api_document_list'),
    path('api/search/', views.api_document_search, name='api_document_search'),
    path('api/map/', views.generate_archive_map, name='api_generate_map'),
    path('api/link/<int:document_id>/to-event/<int:event_id>/', 
         views.link_to_timeline, 
         name='api_link_to_timeline'),
    path('api/file-tree/', views.api_file_tree, name='api_file_tree'),
    path('api/preview/<int:pk>/', views.api_file_preview, name='api_file_preview'),
    path('api/get-content/<int:pk>/', views.api_get_content, name='api_get_content'),
    path('api/save-canvas/', views.api_save_canvas, name='api_save_canvas'),
    
    # Photo upload and cloud import endpoints
    path('photos/upload/', views.upload_photo, name='upload_photo'),
    path('cloud/connect/', views.cloud_connect, name='cloud_connect'),
    path('cloud/folders/', views.cloud_folders, name='cloud_folders'),
    path('cloud/import/', views.cloud_import, name='cloud_import'),
]
