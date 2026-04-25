"""
Core app URLs for case management and API endpoints.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Case management
    path('cases/', views.case_list, name='case_list'),
    path('cases/create/', views.create_case, name='create_case'),
    path('cases/<int:case_id>/', views.case_detail, name='case_detail'),
    path('cases/<int:case_id>/delete/', views.delete_case, name='delete_case'),
    path('cases/<int:case_id>/switch/', views.switch_case, name='switch_case'),
    
    # APIs
    path('api/cases/', views.api_case_list, name='api_case_list'),
    path('api/cases/<int:case_id>/', views.api_case_detail, name='api_case_detail'),
]
