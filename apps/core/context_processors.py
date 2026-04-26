"""
Context processors for providing case information throughout the app.
"""
from apps.core.models import Case
from apps.archive.models import ArchiveDocument
from django.conf import settings


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
    api_configured = bool(getattr(settings, 'MISTRAL_API_KEY', None))
    
    if request.user and request.user.is_authenticated:
        case_list = list(Case.objects.filter(user=request.user).values(
            'id', 'name', 'color', 'is_active'
        ))
        
        show_create_modal = len(case_list) == 0
        
        selected_case_id = request.session.get('selected_case_id')
        if selected_case_id:
            try:
                current_case = Case.objects.get(id=selected_case_id, user=request.user)
            except Case.DoesNotExist:
                request.session.pop('selected_case_id', None)
        
        if not current_case and case_list:
            current_case = Case.objects.get(id=case_list[0]['id'], user=request.user)
            request.session['selected_case_id'] = current_case.id
        
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
    }