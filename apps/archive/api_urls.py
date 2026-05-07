"""
Archive API URLs

Endpoints for archive operations including Gate Logic (promote/demote).
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'documents', api_views.ArchiveDocumentViewSet, basename='archive-document')

urlpatterns = [
    path('', include(router.urls)),
    # Gate Logic endpoints
    path('documents/<uuid:pk>/promote/', api_views.ArchiveDocumentViewSet.as_view({'post': 'promote'}), name='archive-document-promote'),
    path('documents/<uuid:pk>/demote/', api_views.ArchiveDocumentViewSet.as_view({'post': 'demote'}), name='archive-document-demote'),
    path('documents/move_file/', api_views.ArchiveDocumentViewSet.as_view({'post': 'move_file'}), name='archive-document-move-file'),
    path('documents/metadata/<uuid:file_uuid>/', api_views.FileMetadataView.as_view(), name='archive-document-metadata'),
    path('directory/', api_views.ArchiveDirectoryView.as_view(), name='archive-directory'),
]
