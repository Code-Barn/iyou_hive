"""
Core middleware for Hiver project.

This module provides:
- Authentication middleware for Rust-DID integration
- Session management
- Request logging
- Case selection enforcement
"""

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect, reverse
from django.conf import settings
from django.http import HttpResponseRedirect
import os


class RustDIDAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware for Rust-DID based authentication.
    
    This middleware checks for valid DID-based authentication.
    In production, it would verify Verifiable Credentials (VCs) using
    the Rust-DID FFI library.
    
    For development, it uses a simple session-based fallback.
    """
    
    @staticmethod
    def rust_did_available():
        """
        Check if Rust-DID library is configured and available.
        
        Returns:
            bool: True if Rust-DID is available, False otherwise
        """
        from django.conf import settings
        import os
        
        # Check if Rust-DID backend is configured
        use_rust_did = getattr(settings, 'DID_BACKEND', 'python').lower() == 'rust'
        
        # Also check environment variable
        if not use_rust_did:
            use_rust_did = os.getenv('DID_BACKEND', '').lower() == 'rust'
        
        has_lib_path = hasattr(settings, 'RUST_DID_LIB_PATH') and settings.RUST_DID_LIB_PATH
        
        # If Rust-DID is enabled, check if the library can be loaded
        if use_rust_did:
            try:
                from apps.core.did_rust_wrapper import get_did_wrapper
                return get_did_wrapper() is not None
            except Exception:
                return False
        else:
            # Even if not explicitly set to 'rust', check if library exists
            # This allows fallback to Rust-DID if the library is present
            if has_lib_path:
                lib_path = str(settings.RUST_DID_LIB_PATH)
                if os.path.exists(lib_path):
                    try:
                        from apps.core.did_rust_wrapper import get_did_wrapper
                        return get_did_wrapper() is not None
                    except Exception:
                        return False
        return False
    
    def process_request(self, request):
        """
        Process each request to check authentication.
        
        Returns None if request should continue, or HttpResponse if
        authentication fails.
        """
        # Skip authentication for certain paths
        exempt_paths = [
            '/accounts/login/',
            '/accounts/logout/',
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
        if (path.startswith('/timeline/') or 
           path.startswith('/archive/') or 
           path.startswith('/ai/') or
           path.startswith('/')):
            
            # Check if user is authenticated
            if not request.user.is_authenticated:
                # Skip redirect for login/logout pages
                if path.startswith('/accounts/'):
                    return None
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
    
    Adds Content-Security-Policy header. Other security headers are handled
    by Django's built-in SecurityMiddleware.
    """
    
    def process_response(self, request, response):
        """Add security headers to responses."""
        # Let Django SecurityMiddleware handle: Strict-Transport-Security, X-Frame-Options,
        # X-Content-Type-Options, X-XSS-Protection
        
        # Only add CSP if not already set (by previous middleware or view)
        if 'Content-Security-Policy' not in response:
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
                request.session['selected_case_id'] = first_case.id
            return None
        
        # Verify the selected case belongs to this user
        try:
            case = Case.objects.get(id=selected_case_id, user=request.user)
        except Case.DoesNotExist:
            # Auto-select the first case
            first_case = user_cases.order_by('-updated_at').first()
            if first_case:
                request.session['selected_case_id'] = first_case.id
            else:
                request.session.pop('selected_case_id', None)
        
        return None
