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
Core middleware for Hiver project.

This module provides:
- Session management
- Request logging
- Case selection enforcement
"""

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.conf import settings


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to enhance session security.
    
    Adds Content-Security-Policy header. Other security headers are handled
    by Django's built-in SecurityMiddleware.
    """
    
    def process_response(self, request, response):
        """Add security headers to responses."""
        # Let Django SecurityMiddleware handle: Strict-Transport-Security, X-Frame-Options,
        # X-Content-Type-Options, X-XSS-Protection
        
        # Only add CSP if not already set (by previous middleware or view)
        if 'Content-Security-Policy' not in response:
            connect_src = getattr(settings, 'CONNECT_SRC', "'self' wss://home.iyou.me:9001 https://iyou.me")
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                f"connect-src {connect_src}; "
                "frame-src 'none'; "
                "object-src 'none'"
            )
            response['Content-Security-Policy'] = csp
        
        if 'Referrer-Policy' not in response:
            response['Referrer-Policy'] = 'same-origin'
        
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log requests for debugging.
    
    Only logs in DEBUG mode.
    """
    
    def process_request(self, request):
        """Log request details in debug mode."""
        if settings.DEBUG:
            from django.utils.log import getLogger
            logger = getLogger('hiver.request')
            logger.debug(f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}")
        
        return None


class CaseSelectionMiddleware(MiddlewareMixin):
    """
    Middleware to enforce case selection.
    
    If a user is authenticated and has cases but no case is selected,
    redirect to case selection.
    """
    
    EXEMPT_URLS = [
        '/accounts/',
        '/admin/',
        '/static/',
        '/media/',
        '/core/cases/',
        '/core/api/',
    ]
    
    def process_request(self, request):
        """Check if case selection is required."""
        path = request.path_info
        
        # Skip for exempt URLs
        for exempt in self.EXEMPT_URLS:
            if path.startswith(exempt):
                return None
        
        # Skip if user not authenticated
        if not request.user or not request.user.is_authenticated:
            return None
        
        # Skip if user has no cases
        from apps.core.models import Case
        user_cases = Case.objects.filter(user=request.user)
        if not user_cases.exists():
            return None
        
        # Check if case is selected in session
        selected_case_id = request.session.get('selected_case_id')
        if not selected_case_id:
            # Auto-select the first case
            first_case = user_cases.order_by('-updated_at').first()
            if first_case:
                request.session['selected_case_id'] = str(first_case.id)
            return None
        
        # Verify the selected case belongs to this user
        try:
            case = Case.objects.get(id=selected_case_id, user=request.user)
        except Case.DoesNotExist:
            # Auto-select the first case
            first_case = user_cases.order_by('-updated_at').first()
            if first_case:
                request.session['selected_case_id'] = str(first_case.id)
            else:
                request.session.pop('selected_case_id', None)
        
        return None
