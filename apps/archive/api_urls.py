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
    path('documents/<int:pk>/promote/', api_views.ArchiveDocumentViewSet.as_view({'post': 'promote'}), name='archive-document-promote'),
    path('documents/<int:pk>/demote/', api_views.ArchiveDocumentViewSet.as_view({'post': 'demote'}), name='archive-document-demote'),
]
