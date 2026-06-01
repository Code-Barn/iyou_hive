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

from django.shortcuts import redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import CreateView

# Get User model
User = get_user_model()


class CustomLoginView(LoginView):
    """Custom login view that redirects to React root after login."""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return '/'
    
    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().username}!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class CustomLogoutView(LogoutView):
    """Custom logout view that redirects to React root after logout."""
    next_page = '/'
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, 'You have been logged out.')
        return super().dispatch(request, *args, **kwargs)


class RegisterView(CreateView):
    """User registration view with form validation."""
    model = User
    form_class = UserCreationForm
    template_name = 'accounts/register.html'
    success_url = '/'
    
    def get_success_url(self):
        messages.success(self.request, 'Registration successful! You are now logged in.')
        return super().get_success_url()
    
    def form_valid(self, form):
        # Save the user
        response = super().form_valid(form)
        
        # Log the user in after registration
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        user = authenticate(
            username=username,
            password=password
        )
        if user is not None:
            login(self.request, user)
        
        return response
    
class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with additional fields."""
    class Meta:
        model = User
        fields = ('username', 'email')


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
            'login_url': settings.LOGIN_URL,
        })
    else:
        return JsonResponse({
            'authenticated': False,
            'login_url': settings.LOGIN_URL,
        })


@login_required
def dashboard(request):
    """
    User dashboard - redirect to timeline if case is selected, otherwise show case list.
    For first-time users, suggest creating a case.
    """
    case_id = request.session.get("selected_case_id")
    if case_id:
        return redirect("/")
    
    # Check if this is a first-time user (no cases created)
    from apps.core.models import Case
    has_cases = Case.objects.filter(user=request.user).exists()
    if not has_cases:
        # First-time user - suggest creating a case
        messages.info(request, "Welcome! Please create your first case to get started.")
    
    return redirect("core:case_list")
