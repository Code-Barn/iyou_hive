"""
Core middleware for Hiver project.

This module provides:
- Authentication middleware for Rust-DID integration
- Session management
- Request logging
"""

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect, reverse
from django.conf import settings
import os


class RustDIDAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware for Rust-DID based authentication.
    
    This middleware checks for valid DID-based authentication.
    In production, it would verify Verifiable Credentials (VCs) using
    the Rust-DID FFI library.
    
    For development, it uses a simple session-based fallback.
    """
    
    def process_request(self, request):
        """
        Process each request to check authentication.
        
        Returns None if request should continue, or HttpResponse if
        authentication fails.
        """
        # Skip authentication for certain paths
        exempt_paths = [
            reverse('admin:login'),
            reverse('admin:logout'),
            '/static/',
            '/media/',
            '/favicon.ico',
        ]
        
        path = request.path_info
        
        # Skip if path is exempt
        if any(path.startswith(str(p)) for p in exempt_paths):
            return None
        
        # Use Rust-DID if configured
        use_rust_did = os.getenv('DID_BACKEND', '').lower() == 'rust'
        
        if use_rust_did and hasattr(settings, 'RUST_DID_LIB_PATH'):
            # In production, verify VC from request headers
            vc_token = request.headers.get('X-VC-Token') or \
                      request.COOKIES.get('vc_token')
            
            if vc_token:
                # For now, we'll use a simple check
                # In production, this would call the Rust library
                if self.verify_vc_token(vc_token):
                    request.user = self.get_user_from_vc(vc_token)
                    return None
            
            # Fall back to session authentication
            if request.user.is_authenticated:
                return None
        else:
            # Use Django's built-in authentication
            if request.user.is_authenticated:
                return None
        
        # Require authentication for certain apps
        if path.startswith('/timeline/') or \
           path.startswith('/archive/') or \
           path.startswith('/ai/'):
            
            # Check if user is authenticated
            if not request.user.is_authenticated:
                # Redirect to login
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        
        return None
    
    def verify_vc_token(self, token):
        """
        Verify a Verifiable Credential token using Rust-DID.
        
        This is a placeholder that would call the actual Rust FFI.
        """
        try:
            # In production, this would call the Rust library
            # For now, just check if it's a non-empty string
            return bool(token and len(token) > 10)
        except Exception:
            return False
    
    def get_user_from_vc(self, token):
        """
        Extract user information from a Verifiable Credential.
        
        This is a placeholder implementation.
        """
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # In production, decode VC and get DID
        # For now, return the first user or None
        try:
            return User.objects.first()
        except Exception:
            return None


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to enhance session security.
    
    Sets security-related headers and validates sessions.
    """
    
    def process_response(self, request, response):
        """Add security headers to responses."""
        # Secure cookies
        response.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('X-Frame-Options', 'DENY')
        response.setdefault('X-XSS-Protection', '1; mode=block')
        response.setdefault('Referrer-Policy', 'same-origin')
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-src 'none'; "
            "object-src 'none'"
        )
        response.setdefault('Content-Security-Policy', csp)
        
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
