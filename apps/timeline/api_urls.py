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

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'cases/(?P<case_id>[^/]+)/events', api_views.TimelineEventViewSet, basename='timeline-event')
router.register(r'cases/(?P<case_id>[^/]+)/collections', api_views.TimelineCollectionViewSet, basename='timeline-collection')

urlpatterns = [
    path('', include(router.urls)),
    
    # Diff view endpoint
    path('cases/<uuid:case_id>/diff/', api_views.DiffViewAPI.as_view({'get': 'retrieve'}), name='timeline-diff'),
    
    # AI Materialize endpoint: bridge from AI suggestion to Timeline reality
    path('cases/<uuid:case_id>/materialize/', api_views.MaterializeEventView.as_view(), name='timeline-materialize'),

    # Action endpoints for events
    path('cases/<uuid:case_id>/upload-markdown/', api_views.TimelineEventViewSet.as_view({'post': 'upload_markdown'}), name='timeline-upload-markdown'),
    path('cases/<uuid:case_id>/events/<uuid:pk>/contest/', api_views.TimelineEventViewSet.as_view({'post': 'contest'}), name='timeline-event-contest'),
    path('cases/<uuid:case_id>/events/<uuid:pk>/resolve/', api_views.TimelineEventViewSet.as_view({'post': 'resolve'}), name='timeline-event-resolve'),
    
    # Action endpoints for collections
    path('cases/<uuid:case_id>/collections/<uuid:pk>/add-event/', api_views.TimelineCollectionViewSet.as_view({'post': 'add_event'}), name='timeline-collection-add-event'),
    path('cases/<uuid:case_id>/collections/<uuid:pk>/remove-event/', api_views.TimelineCollectionViewSet.as_view({'post': 'remove_event'}), name='timeline-collection-remove-event'),
    
    # Hive portability endpoints
    # path('cases/<uuid:case_id>/export/', api_views.HiveExportViewSet.as_view({'post': 'create'}), name='hive-export'),
    # path('cases/<uuid:case_id>/import/', api_views.HiveImportViewSet.as_view({'post': 'create'}), name='hive-import'),
    
    # Shredder endpoint
    # path('cases/<uuid:case_id>/shred/', api_views.ShredderViewSet.as_view({'post': 'create'}), name='case-shred'),
]
