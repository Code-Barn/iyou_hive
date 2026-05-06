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
    
    # Action endpoints for events
    path('cases/<uuid:case_id>/events/<uuid:pk>/contest/', api_views.TimelineEventViewSet.as_view({'post': 'contest'}), name='timeline-event-contest'),
    path('cases/<uuid:case_id>/events/<uuid:pk>/resolve/', api_views.TimelineEventViewSet.as_view({'post': 'resolve'}), name='timeline-event-resolve'),
    
    # Action endpoints for collections
    path('cases/<uuid:case_id>/collections/<uuid:pk>/add-event/', api_views.TimelineCollectionViewSet.as_view({'post': 'add_event'}), name='timeline-collection-add-event'),
    path('cases/<uuid:case_id>/collections/<uuid:pk>/remove-event/', api_views.TimelineCollectionViewSet.as_view({'post': 'remove_event'}), name='timeline-collection-remove-event'),
    
    # Hive portability endpoints
    path('cases/<uuid:case_id>/export/', api_views.HiveExportViewSet.as_view({'post': 'create'}), name='hive-export'),
    path('cases/<uuid:case_id>/import/', api_views.HiveImportViewSet.as_view({'post': 'create'}), name='hive-import'),
    
    # Shredder endpoint
    path('cases/<uuid:case_id>/shred/', api_views.ShredderViewSet.as_view({'post': 'create'}), name='case-shred'),
]
