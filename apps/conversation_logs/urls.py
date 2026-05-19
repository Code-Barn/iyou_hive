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

"""
URL patterns for conversation logging and analytics.
"""

from django.urls import path
from . import views

app_name = 'conversation_logs'

urlpatterns = [
    # API Endpoints
    path('api/log-message/', views.api_log_message, name='api_log_message'),
    path('api/conversation/<uuid:conversation_id>/history/', views.api_conversation_history, name='api_conversation_history'),
    path('api/conversation/<uuid:conversation_id>/stats/', views.api_conversation_stats, name='api_conversation_stats'),
    path('api/conversation/<uuid:conversation_id>/feedback/', views.api_add_feedback, name='api_add_feedback'),
    
    # Web Views
    path('analytics/', views.conversation_analytics_dashboard, name='analytics_dashboard'),
    path('conversation/<uuid:conversation_id>/history/', views.conversation_history_view, name='conversation_history'),
]