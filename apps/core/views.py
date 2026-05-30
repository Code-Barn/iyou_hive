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
Core views for case management, user settings, and workspace configuration.

This module provides:
- Case CRUD operations
- API endpoints for case management
- User preferences and settings
"""

import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction, IntegrityError
from .models import Case, TimelineFile
from apps.timeline.models import TimelineEvent
from apps.archive.models import ArchiveDocument
from django.utils import timezone

logger = logging.getLogger(__name__)

# ============================================================================
# React App View
# ============================================================================

def react_app_view(request):
    """
    Sovereign Entrance Gate: Route to the legacy Django workspace for
    anonymous traffic, or the React SPA for authenticated sessions.
    """
    if not request.user.is_authenticated:
        return render(request, 'core/case_list.html')

    active_case_id = request.session.get('selected_case_id', '')
    if not active_case_id:
        user_case = Case.objects.filter(user=request.user).first()
        if user_case:
            active_case_id = str(user_case.id)
            request.session['selected_case_id'] = active_case_id

    from django.conf import settings

    context = {
        'username': request.user.username,
        'active_case_id': active_case_id if active_case_id else '',
        'POLY_URL': getattr(settings, 'POLY_URL', 'https://poly.iyou.me'),
        'SOCIALFEED_URL': getattr(settings, 'SOCIALFEED_URL', 'https://wun.iyou.me'),
        'VAULT_URL': getattr(settings, 'VAULT_URL', 'ws://127.0.0.1:9001'),
    }

    return render(request, 'frontend/index.html', context)


# ============================================================================
# Case Management Views
# ============================================================================

@login_required
def case_list(request):
    """
    List all cases for the current user.
    
    Supports creating new cases via GET parameter.
    """
    cases = Case.objects.filter(user=request.user).order_by('-updated_at')
    
    # Check for quick create
    if 'create_case' in request.GET:
        name = request.GET.get('name', '').strip()
        if name:
            # Create the case
            try:
                with transaction.atomic():
                    case = Case.objects.create(
                        name=name,
                        user=request.user,
                        description=request.GET.get('description', '')[:500]
                    )
                    messages.success(request, f'Case "{name}" created successfully!')
                    
                    # Automatically select this case for the user
                    request.session['selected_case_id'] = str(case.id)
                    
                    # Redirect to home view instead of case detail
                    return redirect('/')
            except Exception as e:
                messages.error(request, f'Failed to create case: {e}')
    
    context = {
        'cases': cases,
        'has_cases': cases.exists(),
        'default_case': Case.get_default_case(request.user)
    }
    
    return render(request, 'core/case_list.html', context)


@login_required
def case_detail(request, case_id):
    """
    Display details for a specific case.
    """
    case = get_object_or_404(Case, id=case_id, user=request.user)
    
    # Get related data - filter by case AND user for compartmentalization
    events = TimelineEvent.objects.filter(
        case=case,
        created_by=request.user
    ).order_by('-date')[:10]
    documents = ArchiveDocument.objects.filter(
        case=case,
        user=request.user
    ).order_by('-upload_date')[:10]
    timeline_files = TimelineFile.objects.filter(
        case=case,
        user=request.user
    ).order_by('-updated_at')
    
    context = {
        'case': case,
        'events': events,
        'documents': documents,
        'timeline_files': timeline_files,
        'event_count': case.event_count,
        'document_count': case.document_count,
    }
    
    return render(request, 'core/case_detail.html', context)


@login_required
def create_case(request):
    """
    Create a new case.
    
    GET: Show creation form
    POST: Create the case (AJAX support for welcome modal)
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()[:500]
        color = request.POST.get('color', '#FF8C00')
        
        if not name:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Case name is required'}, status=400)
            messages.error(request, 'Case name is required')
            return redirect('core:case_list')
        
        # Gradient color selection options
        color_options = [
            '#FF8C00',  # Honey-Orange (default)
            '#0064AA',  # Byers Blue
            '#4CAF50',  # Green
            '#F44336',  # Red
            '#9C27B0',  # Purple
            '#FF9800',  # Orange
            '#2196F3',  # Blue
            '#E91E63',  # Pink
        ]
        
        if color not in color_options:
            color = '#FF8C00'
        
        try:
            with transaction.atomic():
                # Check if case with this name already exists for this user
                existing = Case.objects.filter(name=name, user=request.user).first()
                if existing:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'error': f'A case with the name "{name}" already exists.'}, status=400)
                    messages.error(request, f'A case with the name "{name}" already exists.')
                    return redirect('core:case_list')
                
                case = Case.objects.create(
                    name=name,
                    description=description,
                    color=color,
                    user=request.user,
                    is_active=True
                )
                
                # Create standard folder structure
                from apps.archive.models import ArchiveDocument
                ArchiveDocument.create_standard_folder_structure(case, request.user)
                
                request.session['selected_case_id'] = str(case.id)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'case_id': str(case.id),
                        'name': case.name
                    })
                
                messages.success(request, f'Case "{case.name}" created successfully!')
                return redirect('core:case_detail', case_id=case.id)
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': f'Failed to create case: {e}'}, status=500)
            messages.error(request, f'Failed to create case: {e}')
            return redirect('core:case_list')
    
    # GET: Show creation form
    return render(request, 'core/create_case.html', {
        'color_options': color_options
    })


@login_required
def api_case_list(request):
    """
    API endpoint to list all cases for the current user.
    POST: Create a new case

    Returns:
        JsonResponse with list of cases or created case
    """
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            client_legal_name = data.get('client_legal_name', '').strip()
            opposing_legal_name = data.get('opposing_legal_name', '').strip()
            description = data.get('description', '').strip()[:500]
            color = data.get('color', '#FF8C00')

            if not name:
                return JsonResponse({'error': 'Case name is required'}, status=400)

            color_options = [
                '#FF8C00', '#0064AA', '#4CAF50', '#F44336',
                '#9C27B0', '#FF9800', '#2196F3', '#E91E63',
            ]

            if color not in color_options:
                color = '#FF8C00'

            with transaction.atomic():
                existing = Case.objects.filter(name=name, user=request.user).first()
                if existing:
                    return JsonResponse({'error': f'A case with the name "{name}" already exists.'}, status=400)

                case = Case.objects.create(
                    name=name,
                    client_legal_name=client_legal_name,
                    opposing_legal_name=opposing_legal_name,
                    description=description,
                    color=color,
                    user=request.user,
                    is_active=True
                )

                from apps.archive.models import ArchiveDocument
                ArchiveDocument.create_standard_folder_structure(case, request.user)

                request.session['selected_case_id'] = str(case.id)

                return JsonResponse({
                    'status': 'success',
                    'case': {
                        'id': str(case.id),
                        'name': case.name,
                        'client_legal_name': case.client_legal_name,
                        'opposing_legal_name': case.opposing_legal_name,
                        'description': case.description,
                        'color': case.color,
                        'is_active': case.is_active,
                        'event_count': 0,
                        'document_count': 0,
                        'created_at': case.created_at.isoformat() if case.created_at else None,
                        'updated_at': case.updated_at.isoformat() if case.updated_at else None,
                    }
                }, status=201)
        except Exception as e:
            return JsonResponse({'error': f'Failed to create case: {e}'}, status=500)

    cases = Case.objects.filter(user=request.user).order_by('-updated_at')

    case_list = []
    for case in cases:
        case_list.append({
            'id': str(case.id),
            'name': case.name,
            'client_legal_name': case.client_legal_name,
            'opposing_legal_name': case.opposing_legal_name,
            'description': case.description,
            'color': case.color,
            'is_active': case.is_active,
            'event_count': case.event_count,
            'document_count': case.document_count,
            'created_at': case.created_at.isoformat() if case.created_at else None,
            'updated_at': case.updated_at.isoformat() if case.updated_at else None,
        })

    return JsonResponse({'cases': case_list})


@login_required
def api_case_detail(request, case_id):
    """
    API endpoint to get details for a specific case.
    
    Returns:
        JsonResponse with case details
    """
    case = get_object_or_404(Case, id=case_id, user=request.user)
    
    # Get related data counts
    events = TimelineEvent.objects.filter(case=case)
    documents = ArchiveDocument.objects.filter(case=case)
    timeline_files = TimelineFile.objects.filter(case=case)
    
    return JsonResponse({
        'id': str(case.id),  # Convert UUID to string for JSON serialization
        'name': case.name,
        'description': case.description,
        'color': case.color,
        'is_active': case.is_active,
        'event_count': events.count(),
        'document_count': documents.count(),
        'timeline_file_count': timeline_files.count(),
        'created_at': case.created_at.isoformat() if case.created_at else None,
        'updated_at': case.updated_at.isoformat() if case.updated_at else None,
    })


@login_required
def get_timeline_data(request, case_id):
    """
    Returns timeline data for a case, including source_party and category for styling.
    """
    from apps.core.models import WikiPage, RawDocument
    import os

    # Get case and verify access
    case = get_object_or_404(Case, id=case_id, user=request.user)

    # Fetch WikiPages for the case
    wiki_pages = WikiPage.objects.filter(case_id=case_id).order_by('last_updated')

    timeline_data = []
    for page in wiki_pages:
        # Get the source_party from the associated RawDocument (if any)
        source_party = "NEUTRAL"  # Default

        # Try to get source_party from citation_references
        if page.citation_references and len(page.citation_references) > 0:
            first_citation = page.citation_references[0]
            try:
                # Assuming citation source is in format "raw/{case_id}/{filename}"
                source_path = first_citation.get('source', '')
                if source_path:
                    # Extract filename from path
                    filename = os.path.basename(source_path)
                    # Try to find the RawDocument
                    raw_doc = RawDocument.objects.filter(
                        case=case,
                        file__endswith=filename
                    ).first()
                    if raw_doc:
                        source_party = raw_doc.source_party
            except Exception:
                pass

        timeline_data.append({
            'id': str(page.id),
            'title': page.title,
            'content': page.content,
            'date': page.last_updated.strftime("%Y-%m-%d"),
            'category': page.category,
            'source_party': source_party,
            'citation': page.citation_references[0].get('source', '') if page.citation_references else '',
        })

    return JsonResponse({'timeline': timeline_data})


# ============================================================================
# Response Sheet Review Views
# ============================================================================

@login_required
def response_sheet_review(request, sheet_id=None):
    """
    Review response sheet claims with checkboxes.
    Checked = keep, Unchecked = exclude.
    """
    from .models import ResponseSheet
    from .utils import filter_claims
    import json
    
    # If no sheet_id, show list of available sheets
    if sheet_id is None:
        sheets = ResponseSheet.objects.filter(
            created_by=request.user
        ).order_by('-created_at')[:20]
        return render(request, 'core/response_sheet_list.html', {
            'sheets': sheets
        })
    
    sheet = get_object_or_404(ResponseSheet, id=sheet_id, created_by=request.user)
    data = sheet.data
    
    if request.method == 'POST':
        # Get excluded IDs from checkboxes
        excluded_ids = request.POST.getlist('exclude_ids', [])
        excluded_ids = [int(x) for x in excluded_ids if x.isdigit()]
        
        # Generate filtered HTML
        filtered = filter_claims(data, excluded_ids)
        html = sheet.get_filtered_html(excluded_ids)
        
        # Save filtered HTML to file
        import tempfile
        output_path = f"temp/{sheet.case_number or 'sheet'}_{sheet.id}_filtered.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        messages.success(request, f"Filtered response sheet saved to {output_path}")
        return redirect('core:response_sheet_review', sheet_id=sheet_id)
    
    # GET request - show review page
    metadata = data.get('metadata', {})
    procedural = data.get('procedural_facts', [])
    claims = data.get('claims', [])
    
    return render(request, 'core/response_sheet_review.html', {
        'sheet': sheet,
        'metadata': metadata,
        'procedural_facts': procedural,
        'claims': claims,
    })


@login_required
def response_sheet_generate(request, sheet_id):
    """
    POST-only view to generate filtered HTML/PDF from review page.
    Expects 'excluded_ids' in POST data.
    """
    from .models import ResponseSheet
    from .utils import filter_claims
    import json
    
    if request.method != 'POST':
        return redirect('core:response_sheet_review', sheet_id=sheet_id)
    
    sheet = get_object_or_404(ResponseSheet, id=sheet_id, created_by=request.user)
    data = sheet.data
    
    # Get excluded IDs from hidden input (set by JavaScript)
    excluded_json = request.POST.get('excluded_ids_json', '[]')
    try:
        excluded_ids = json.loads(excluded_json)
    except json.JSONDecodeError:
        excluded_ids = []
    
    # Generate filtered output
    filtered = filter_claims(data, excluded_ids)
    html = sheet.get_filtered_html(excluded_ids)
    
    # Save outputs
    base_name = f"temp/{sheet.case_number or 'sheet'}_{sheet.id}"
    
    # JSON
    with open(f"{base_name}_filtered.json", 'w', encoding='utf-8') as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)
    
    # HTML
    with open(f"{base_name}_filtered.html", 'w', encoding='utf-8') as f:
        f.write(html)
    
    messages.success(request, f"Filtered response sheet generated!")
    return redirect('core:response_sheet_review', sheet_id=sheet_id)


@login_required
def response_sheet_list(request):
    """List all response sheets for the user."""
    from .models import ResponseSheet
    sheets = ResponseSheet.objects.filter(
        created_by=request.user
    ).order_by('-created_at')[:50]
    return render(request, 'core/response_sheet_list.html', {
        'sheets': sheets
    })


@login_required
def generate_response_sheet_view(request):
    """Upload PDF and generate a new response sheet."""
    from .models import ResponseSheet, Case
    import json
    from pathlib import Path
    
    if request.method == 'POST':
        pdf_file = request.FILES.get('pdf_file')
        state_code = request.POST.get('state_code', 'IL')
        
        if not pdf_file:
            messages.error(request, "Please upload a PDF file.")
            return redirect('core:generate_sheet')
        
        # Save PDF temporarily
        temp_path = f"temp/{pdf_file.name}"
        with open(temp_path, 'wb+') as destination:
            for chunk in pdf_file.chunks():
                destination.write(chunk)
        
        # Run the script
        import sys
        sys.path.insert(0, 'scripts')
        try:
            from generate_response_sheet import generate_response_sheet as gen_sheet
            output_path = gen_sheet(temp_path, state_code=state_code)
            
            # Load the generated JSON
            json_path = str(Path(output_path).with_suffix('.response_sheet.json'))
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create ResponseSheet record
            case_id = request.POST.get('case_id')
            case = None
            if case_id:
                try:
                    case = Case.objects.get(id=case_id, user=request.user)
                except Case.DoesNotExist:
                    pass
            
            sheet = ResponseSheet.objects.create(
                case=case,
                title=data.get('motion_title', 'Untitled'),
                source_pdf=temp_path,
                case_number=data.get('case_number', ''),
                state_code=state_code,
                data=data,
                created_by=request.user,
            )
            
            messages.success(request, f"Response sheet generated! Review claims below.")
            return redirect('core:response_sheet_review', sheet_id=sheet.id)
            
        except Exception as e:
            messages.error(request, f"Error generating sheet: {e}")
            return redirect('core:generate_sheet')
    
    # GET: show upload form
    from .models import Case
    cases = Case.objects.filter(user=request.user).order_by('-updated_at')
    return render(request, 'core/generate_sheet.html', {
        'cases': cases
    })


@login_required
def switch_case(request, case_id):
    """
    Switch the active case for the current user session.

    Sets ``selected_case_id`` in the session and redirects to the case
    timeline view.

    Args:
        case_id: UUID of the target case.

    Returns:
        Redirect to the timeline view for the chosen case.
    """
    case = get_object_or_404(Case, id=case_id, user=request.user)
    Case.objects.filter(user=request.user).update(is_active=False)
    case.is_active = True
    case.save(update_fields=['is_active'])
    request.session['selected_case_id'] = str(case.id)
    return redirect('timeline:timeline')


@login_required
def delete_case(request, case_id):
    """
    Delete a case and all associated data.

    POST-only view that removes the case and its related timeline events,
    documents, and AI conversations.

    Args:
        case_id: UUID of the case to delete.

    Returns:
        Redirect to the case list on success.
    """
    case = get_object_or_404(Case, id=case_id, user=request.user)
    if request.method == 'POST':
        case_name = case.name
        case.delete()
        request.session.pop('selected_case_id', None)
        messages.success(request, f'Case "{case_name}" has been deleted.')
        return redirect('core:case_list')
    return render(request, 'core/confirm_delete.html', {'case': case})


@login_required
def delete_response_sheet(request, sheet_id):
    """Delete a response sheet."""
    from .models import ResponseSheet
    sheet = get_object_or_404(ResponseSheet, id=sheet_id, created_by=request.user)
    
    if request.method == 'POST':
        sheet.delete()
        messages.success(request, "Response sheet deleted.")
        return redirect('core:response_sheet_list')
    
    return render(request, 'core/delete_sheet_confirm.html', {
        'sheet': sheet
    })
