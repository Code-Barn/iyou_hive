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

app_name = 'ai_assistant'

urlpatterns = [
    path('', views.ai_chat_view, name='chat'),
    path('analyze/', views.analyze_document, name='analyze'),
    path('query-timeline/', views.query_timeline, name='query_timeline'),
    path('suggest-events/', views.suggest_events, name='suggest_events'),
    path('analyze-event/<uuid:event_id>/', views.analyze_timeline_event, name='analyze_event'),
    path('save-api-key/', views.save_api_key, name='save_api_key'),
]
