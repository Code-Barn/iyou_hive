"""
DID Authentication Views

Handles Rust-DID based authentication with:
- Challenge/response flow
- DID verification
- Session management
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib.auth import get_user_model
import uuid
import json

# Get User model
User = get_user_model()


def generate_challenge(request):
    """
    Generate a DID authentication challenge.
    
    Returns:
        JsonResponse with challenge and session key
    """
    # Generate a unique challenge
    challenge = str(uuid.uuid4())
    
    # Store challenge in session
    request.session['did_challenge'] = challenge
    request.session['did_challenge_nonce'] = str(uuid.uuid4())
    
    return JsonResponse({
        'challenge': challenge,
        'nonce': request.session['did_challenge_nonce']
    })


@require_http_methods(["GET", "POST"])
def did_login(request):
    """
    DID-based login view.
    
    GET: Generate and display login form with challenge
    POST: Verify DID signature and authenticate user
    
    Uses Rust-DID for verification when available, falls back to session auth.
    """
    if request.method == 'POST':
        # Handle DID authentication
        did = request.POST.get('did')
        signature = request.POST.get('signature')
        challenge = request.POST.get('challenge')
        
        # Verify the challenge matches what we stored
        stored_challenge = request.session.get('did_challenge')
        
        if not stored_challenge or stored_challenge != challenge:
            messages.error(request, 'Invalid or expired challenge. Please try again.')
            return redirect('accounts:did_login')
        
        # Try Rust-DID verification
        from apps.core.did_rust_wrapper import verify_credential
        from apps.core.middleware import RustDIDAuthenticationMiddleware
        
        try:
            # Create a VC (Verification Credential) string for verification
            # Format: {"did": "...", "signature": "...", "challenge": "..."}
            vc_payload = {
                'did': did,
                'signature': signature,
                'challenge': challenge,
                'nonce': request.session.get('did_challenge_nonce')
            }
            vc_string = json.dumps(vc_payload)
            
            # Verify using Rust-DID
            is_valid = verify_credential(vc_string)
            
            if is_valid:
                # Extract username from DID or create new user
                # For now, use DID as username
                username = did
                
                # Get or create user
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={'email': f'{username}@did.example'}
                )
                
                # Log the user in
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                
                # Clear challenge from session
                request.session.pop('did_challenge', None)
                request.session.pop('did_challenge_nonce', None)
                
                return redirect('timeline:timeline')
            else:
                messages.error(request, 'Invalid DID signature. Authentication failed.')
                
        except FileNotFoundError as e:
            # Rust-DID library not available, log warning
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Rust-DID library not found: {e}")
            messages.warning(request, 'Rust-DID not available. Please configure RUST_DID_LIB_PATH.')
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"DID authentication error: {e}")
            messages.error(request, f'Authentication error: {str(e)}')
        
        # If we get here, authentication failed
        return redirect('accounts:did_login')
    
    # GET request - show login form
    challenge = str(uuid.uuid4())
    request.session['did_challenge'] = challenge
    request.session['did_challenge_nonce'] = str(uuid.uuid4())
    
    return render(request, 'accounts/did_login.html', {
        'challenge': challenge,
        'nonce': request.session['did_challenge_nonce'],
        'rust_did_available': RustDIDAuthenticationMiddleware.rust_did_available(),
    })


@login_required
def did_logout(request):
    """
    Logout view with DID session cleanup.
    """
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('timeline:timeline')


def auth_status(request):
    """
    API endpoint to check authentication status.
    
    Returns:
        JsonResponse with user authentication status
    """
    if request.user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'username': request.user.username,
            'did': request.user.username,  # Using username as DID for now
        })
    else:
        return JsonResponse({
            'authenticated': False,
            'challenge_url': '/accounts/challenge/',
            'login_url': '/accounts/login/',
        })
