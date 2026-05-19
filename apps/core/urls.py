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
Core app URLs for case management and API endpoints.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Case management
    path('', views.case_list, name='case_list'),
    path('cases/create/', views.create_case, name='create_case'),
    path('cases/<uuid:case_id>/', views.case_detail, name='case_detail'),
    path('cases/<uuid:case_id>/switch/', views.switch_case, name='switch_case'),
    path('cases/<uuid:case_id>/delete/', views.delete_case, name='delete_case'),
    path('api/cases/', views.api_case_list, name='api_case_list'),
    path('api/cases/<uuid:case_id>/', views.api_case_detail, name='api_case_detail'),

    # Response sheets
    path('response-sheets/', views.response_sheet_review, name='response_sheet_list'),
    path('response-sheets/<uuid:sheet_id>/', views.response_sheet_review, name='response_sheet_review'),
    path('response-sheets/<uuid:sheet_id>/generate/', views.response_sheet_generate, name='response_sheet_generate'),
]

