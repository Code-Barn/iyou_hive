from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # DID Authentication
    path('did/login/', views.did_login, name='did_login'),
    path('did/logout/', views.did_logout, name='did_logout'),
    path('challenge/', views.generate_challenge, name='generate_challenge'),
    
    # Standard Django authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
]
