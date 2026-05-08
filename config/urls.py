"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from apps.core.views import react_app_view

urlpatterns = [
    path('admin/', admin.site.urls),
    # API endpoints (must be before catch-all)
    path('api/timeline/', include('apps.timeline.api_urls')),
    path('api/archive/', include('apps.archive.api_urls')),
    # Serve React app for all frontend routes
    path('', react_app_view, name='home'),
    path('timeline/', react_app_view, name='timeline'),  # Full-screen timeline view
    # Include other URL configs
    path('accounts/', include('apps.accounts.urls')),
    path('core/', include('apps.core.urls')),
    path('timeline/api/', include('apps.timeline.urls')),
    path('archive/api/', include('apps.archive.urls')),
    path('ai/api/', include('apps.ai_assistant.urls')),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
