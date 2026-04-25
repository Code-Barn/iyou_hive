from django.urls import path
from . import views

app_name = 'archive'

urlpatterns = [
    path('', views.archive_view, name='archive'),
    path('upload/', views.upload_document, name='upload'),
    path('document/<int:pk>/', views.document_detail, name='detail'),
]