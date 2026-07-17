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
from django.conf import settings
from django.conf.urls.static import static
from apps.core.views import react_app_view
from apps.core.auth_pkce import (
    PKCEAuthorizationRequestView,
    PKCEAuthenticationCallbackView,
)
from mozilla_django_oidc.views import OIDCLogoutView

urlpatterns = [
    path('admin/', admin.site.urls),

    # PKCE-enhanced OIDC routes (replaces include('mozilla_django_oidc.urls'))
    path('oidc/login/', PKCEAuthorizationRequestView.as_view(), name='oidc_authentication_init'),
    path('oidc/callback/', PKCEAuthenticationCallbackView.as_view(), name='oidc_authentication_callback'),
    path('oidc/logout/', OIDCLogoutView.as_view(), name='oidc_logout'),

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
