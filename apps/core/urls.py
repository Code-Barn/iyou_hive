"""
Core app URLs for case management and API endpoints.
"""
from django.urls import path
from . import views

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

