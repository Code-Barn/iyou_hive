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

app_name = 'timeline'

urlpatterns = [
    path('', views.timeline_view, name='timeline'),
    path('upload/', views.upload_markdown, name='upload'),
    path('event/<uuid:pk>/', views.event_detail, name='detail'),
    path('api/event/<uuid:pk>/', views.event_api, name='api_event'),
    path('create-event/', views.create_event, name='create_event'),
    # Timeline file APIs
    path('api/load-timeline/', views.load_timeline_file, name='load_timeline_file'),
    path('api/timeline-headings/', views.api_timeline_headings, name='api_timeline_headings'),
    path('select-timeline/', views.select_timeline, name='select_timeline'),
    path('api/create-timeline-file/', views.create_timeline_file, name='create_timeline_file'),
    path('api/sync-timeline/<uuid:timeline_file_id>/', views.sync_timeline_api, name='sync_timeline'),
    
    # Export endpoints for competing timelines
    path('export/<uuid:case_id>/<str:party>/', views.export_party_timeline, name='export_party_timeline'),
    path('export/<uuid:case_id>/', views.export_case_timeline, name='export_case_timeline'),
    
    # Potential matches API for duplicate detection
    path('api/potential-matches/', views.get_potential_matches, name='potential_matches'),
]