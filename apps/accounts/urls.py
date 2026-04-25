from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.did_login, name='did_login'),
    path('logout/', views.did_logout, name='did_logout'),
    path('challenge/', views.generate_challenge, name='generate_challenge'),
]
