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
Context processors for providing case information throughout the app.
"""
from apps.core.models import Case
from apps.archive.models import ArchiveDocument
from django.conf import settings


def service_urls(request):
    return {
        "POLY_URL": getattr(settings, "POLY_URL", "https://poly.iyou.me"),
        "SOCIALFEED_URL": getattr(settings, "SOCIALFEED_URL", "https://wun.iyou.me"),
        "VAULT_URL": getattr(settings, "VAULT_URL", "wss://home.iyou.me:9001/"),
    }


def cases_processor(request):
    """
    Context processor to provide current case information to all templates.
    Shows new user modal when user has no cases.
    Also provides archive documents and AI config for side panes.
    """
    from apps.core.models import Case
    
    current_case = None
    case_list = []
    show_create_modal = False
    archive_documents = []
    api_configured = bool(getattr(settings, 'MISTRAL_API_KEY', None)) or bool(getattr(settings, 'GEMINI_API_KEY', None))
    user_settings = None
    
    if request.user and request.user.is_authenticated:
        from apps.ai_assistant.models import UserSettings
        try:
            user_settings = UserSettings.objects.get(user=request.user)
            if user_settings.mistral_api_key or user_settings.gemini_api_key:
                api_configured = True
        except UserSettings.DoesNotExist:
            pass
            
        case_list = list(Case.objects.filter(user=request.user).values(
            'id', 'name', 'color', 'is_active'
        ))
        
        # Only show modal if user has no cases AND hasn't just created one
        show_create_modal = len(case_list) == 0 and not request.session.get('case_just_created')
        
        # Clear the flag after checking
        if request.session.get('case_just_created'):
            request.session.pop('case_just_created', None)
        
        selected_case_id = request.session.get('selected_case_id')
        if selected_case_id:
            try:
                current_case = Case.objects.get(id=selected_case_id, user=request.user)
            except Case.DoesNotExist:
                request.session.pop('selected_case_id', None)
        
        if not current_case and case_list:
            current_case = Case.objects.get(id=case_list[0]['id'], user=request.user)
            request.session['selected_case_id'] = str(current_case.id)
        
        # Get documents for this case (for archive pane)
        if current_case:
            archive_documents = list(ArchiveDocument.objects.filter(
                case=current_case, user=request.user
            ).order_by('-upload_date')[:50])
    
    return {
        'current_case': current_case,
        'case_list': case_list,
        'show_create_modal': show_create_modal,
        'archive_documents': archive_documents,
        'api_configured': api_configured,
        'ai_settings': user_settings,
    }