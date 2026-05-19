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

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q
from django.core.cache import cache
from django.core.paginator import Paginator
from .models import TimelineEvent
from apps.core.models import Case, TimelineFile
from .utils import (
    get_main_heading,
    extract_headings,
    find_markdown_files,
    get_timeline_file_info
)
from apps.core.parsers import (
    parse_markdown_content,
    validate_timeline_events,
    parse_timeline_file
)
from .services import (
    sync_timeline_file,
    MarkdownIngestionService, MarkdownExportService
)
from django.utils import timezone
import tempfile
import os
import json


@login_required
def timeline_view(request):
    """
    Display the timeline view with events.
    
    Requires a case to be selected (enforced by middleware).
    """
    # Get selected case from session - middleware ensures this exists
    case_id = request.session.get('selected_case_id')
    if not case_id:
        return redirect('core:case_list')
    
    # Validate case_id is valid format (UUID or int)
    try:
        # Try to convert to UUID if it's a string
        if isinstance(case_id, str):
            import uuid
            uuid.UUID(case_id)
    except (ValueError, AttributeError):
        # Invalid format, clear session and redirect
        request.session.pop('selected_case_id', None)
        return redirect('core:case_list')
    
    # Get case - verify it belongs to user
    try:
        case = Case.objects.get(id=case_id, user=request.user)
    except Case.DoesNotExist:
        request.session.pop('selected_case_id', None)
        return redirect('core:case_list')
    
    # Cache key for events
    cache_key = f'timeline_events_{case_id}_{request.user.id}'
    events = cache.get(cache_key)
    
    if not events:
        # Get events for this case only
        events = TimelineEvent.objects.filter(case=case, created_by=request.user)
        cache.set(cache_key, events, 3600)  # Cache for 1 hour
    
    # Get timeline file information for this case
    timeline_files = []
    main_heading = "Legal Timeline"
    
    if case:
        # Get all timeline files for this case - ONLY user's files
        timeline_files_qs = TimelineFile.objects.filter(
            user=request.user,
            case=case
        ).order_by('-updated_at')
        
        for tf in timeline_files_qs:
            timeline_files.append(tf.to_dict())
        
        # Get main heading from first timeline file with actual file
        for tf in timeline_files_qs:
            if tf.file_path and os.path.exists(tf.file_path):
                main_heading = get_main_heading(file_path=tf.file_path)
                break
    
    # Get unique timeline files from events
    unique_timeline_files = set()
    for event in events:
        if event.timeline_file:
            unique_timeline_files.add(event.timeline_file)
    
    # Add standalone timeline files (not linked to events)
    timeline_files_from_events = []
    for file_path in unique_timeline_files:
        timeline_files_from_events.append({
            'file_path': file_path,
            'name': os.path.basename(file_path),
            'main_heading': get_main_heading(file_path=file_path)
        })
    
    # Merge timeline files
    all_timeline_files = timeline_files + timeline_files_from_events
    
    # Parse markdown file for headings, events, and timelines
    markdown_timelines = {}
    markdown_headings = []
    markdown_events = []
    db_events_from_markdown = []
    
    if all_timeline_files and all_timeline_files[0].get('file_path'):
        try:
            parsed = parse_timeline_file(all_timeline_files[0]['file_path'])
            markdown_headings = parsed.get('headings', [])
            markdown_events = parsed.get('events', [])
            markdown_timelines = parsed.get('timelines', {})
            
            # Validate events if present
            if markdown_events:
                try:
                    validate_timeline_events(markdown_events)
                except ValueError as e:
                    # Add warning but don't fail
                    pass
            
            # Ingest markdown events into database for UUID-based access
            if markdown_events or markdown_timelines:
                # Get or create TimelineFile object
                tf_path = all_timeline_files[0].get('file_path')
                timeline_file_obj = None
                try:
                    timeline_file_obj = TimelineFile.objects.filter(
                        file_path=tf_path,
                        user=request.user
                    ).first()
                except Exception:
                    pass
                
                # Ingest all events using MarkdownIngestionService
                ingest_result = MarkdownIngestionService.ingest_markdown_file(
                    file_path=timeline_file_obj.file_path if timeline_file_obj else '',
                    case=case,
                    user=request.user,
                    timeline_file=timeline_file_obj
                )
                db_events_from_markdown = []  # Events are created directly by the service
                
        except Exception as e:
            markdown_events = []
            markdown_headings = []
            markdown_timelines = {}
    
    # Create master timeline from all timelines
    if markdown_timelines:
        # Sort all events from all timelines by date
        from datetime import datetime
        def safe_date(event):
            try:
                return datetime.strptime(event['date'], '%Y-%m-%d')
            except (ValueError, TypeError):
                return datetime.min
        
        all_timeline_events = []
        for heading, events in markdown_timelines.items():
            all_timeline_events.extend(events)
        
        # Sort by date
        all_timeline_events.sort(key=safe_date)
        
        # Add master timeline
        markdown_timelines['Master Timeline'] = all_timeline_events
    
    # Get current timeline name from request or default to Master Timeline
    current_timeline_name = request.GET.get('timeline', 'Master Timeline')
    
    # Get events for the current timeline
    current_timeline_events = []
    if markdown_timelines and current_timeline_name in markdown_timelines:
        current_timeline_events = markdown_timelines[current_timeline_name]
    elif markdown_events:
        current_timeline_events = markdown_events
    else:
        current_timeline_events = list(events)
    
    # Use DB events (now including ingested markdown events) for display
    display_events = list(events) + db_events_from_markdown
    
    # Add pagination
    paginator = Paginator(display_events, 20)  # Show 20 events per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'events': page_obj,
        'case': case,
        'main_heading': main_heading,
        'headings': markdown_headings,
        'timeline_files': all_timeline_files,
        'selected_case_id': case_id or (case.id if case else None),
        'timelines': markdown_timelines,
        'current_timeline': current_timeline_name,
        'current_timeline_events': current_timeline_events,
    }
    
    return render(request, 'timeline/timeline.html', context)


@login_required
def home(request):
    """Redirect to timeline view."""
    return redirect('timeline:timeline')


@login_required
def upload_markdown(request):
    """
    Upload or parse markdown content to create timeline events.
    Requires case to be selected (middleware ensures this).
    
    Now uses MarkdownIngestionService for unified parsing and event creation.
    """
    from .services import MarkdownIngestionService
    import tempfile
    import os
    
    # Get case from session - required
    case_id = request.session.get('selected_case_id')
    if not case_id:
        return JsonResponse({'error': 'No case selected'}, status=403)
    
    try:
        case = Case.objects.get(id=case_id, user=request.user)
    except Case.DoesNotExist:
        return JsonResponse({'error': 'Invalid case'}, status=403)
    
    if request.method == 'POST':
        content = request.POST.get('markdown_content', '')
        timeline_file_path = request.POST.get('timeline_file_path', '')
        
        # If no content provided but timeline_file_path exists, read from file
        if not content and timeline_file_path:
            if os.path.exists(timeline_file_path):
                with open(timeline_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
        
        if not content:
            return JsonResponse({'error': 'No content provided'}, status=400)
        
        # Write content to temp file for MarkdownIngestionService
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md', encoding='utf-8') as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Get timeline file if path provided
            timeline_file = None
            if timeline_file_path:
                try:
                    timeline_file = TimelineFile.objects.filter(
                        file=timeline_file_path, 
                        case=case
                    ).first()
                except:
                    pass
            
            # Use MarkdownIngestionService for unified processing
            result = MarkdownIngestionService.ingest_markdown_file(
                file_path=temp_path,
                case=case,
                user=request.user,
                timeline_file=timeline_file,
                source_party='CLIENT'
            )
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return JsonResponse({
                'status': 'success',
                'created': result.get('created', 0),
                'updated': result.get('updated', 0),
                'skipped': result.get('skipped', 0),
                'warnings': result.get('warnings', []),
                'redirect': '/timeline/'
            })
            
        except Exception as e:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)
    
    # GET request - show form
    cases = Case.objects.filter(user=request.user).order_by('-updated_at')
    # Get current case if available
    current_case = None
    current_case_id = request.session.get('selected_case_id')
    if current_case_id:
        try:
            current_case = Case.objects.get(id=current_case_id, user=request.user)
        except Case.DoesNotExist:
            pass
    return render(request, 'timeline/upload.html', {
        'cases': cases,
        'current_case': current_case,
        'timeline_files': TimelineFile.objects.filter(user=request.user)
    })


import uuid

@login_required
def event_detail(request, pk):
    """Display detailed information about a timeline event."""
    # Validate UUID format
    try:
        uuid.UUID(str(pk))
    except (ValueError, AttributeError):
        return JsonResponse({'error': 'Invalid event ID format'}, status=400)
    
    event = get_object_or_404(TimelineEvent, pk=pk)
    return render(request, 'timeline/event_detail.html', {'event': event})


@login_required
def event_api(request, pk):
    """
    API endpoint to get event data by UUID.
    Used by frontend to populate popups dynamically.
    """
    # Validate UUID format
    try:
        uuid.UUID(str(pk))
    except (ValueError, AttributeError):
        return JsonResponse({'error': 'Invalid event ID format'}, status=400)
    
    try:
        event = TimelineEvent.objects.get(pk=pk)
    except (TimelineEvent.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Event not found'}, status=404)
    
    # Check user has access to this event's case
    if event.case and event.case.user != request.user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Build event data
    event_data = {
        'id': str(event.id),
        'date': event.date.isoformat(),
        'date_display': event.date.strftime('%B %d, %Y'),
        'event': event.event,
        'category': event.get_category_display(),
        'category_raw': event.category,
        'source_type': event.get_source_type_display(),
        'notes': event.notes,
        'citation': event.citation,
        'source_party': event.get_source_party_display() if event.source_party else '',
        'status': event.status,
        'evidence': [
            {
                'id': str(doc.id),
                'title': doc.title,
                'file_url': doc.get_file_url(),
                'file_type': doc.file_type
            }
            for doc in event.evidence.all()
        ],
        'replaces_event': str(event.replaces_event.id) if event.replaces_event else None,
        'timeline_file': str(event.timeline_file.id) if event.timeline_file else None,
        'case': str(event.case.id) if event.case else None,
    }
    
    return JsonResponse(event_data)


@login_required
def create_event(request):
    """Create a single timeline event via AJAX."""
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    case_id = request.session.get('selected_case_id')
    if not case_id:
        return JsonResponse({'error': 'No case selected'}, status=400)
    
    try:
        from apps.core.models import Case
        case = Case.objects.get(id=case_id, user=request.user)
    except Case.DoesNotExist:
        return JsonResponse({'error': 'Case not found'}, status=404)
    
    date = request.POST.get('date')
    event = request.POST.get('event', '').strip()
    category = request.POST.get('category', 'other')
    description = request.POST.get('description', '').strip()
    evidence_ids = request.POST.getlist('evidence_ids', [])
    source_party = request.POST.get('source_party', 'CLIENT')
    status = request.POST.get('status', 'UNDISPUTED')
    
    if not date or not event:
        return JsonResponse({'error': 'Date and event are required'}, status=400)
    
    # Link evidence documents via M2M
    evidence_docs = []
    if evidence_ids:
        try:
            from apps.archive.models import ArchiveDocument
            docs = ArchiveDocument.objects.filter(id__in=evidence_ids, case=case)
            evidence_docs = list(docs)
        except (ArchiveDocument.DoesNotExist, ValueError):
            pass
    
    # Create the event
    new_event = TimelineEvent.objects.create(
        date=date,
        event=event,
        category=category,
        notes=description,
        source_party=source_party,
        status=status,
        case=case,
        created_by=request.user,
        source_type='MANUAL'
    )
    
    # Link evidence after creation
    if evidence_docs:
        new_event.evidence.set(evidence_docs)
    
    return JsonResponse({'status': 'success'})


def parse_markdown(content):
    """
    Parse markdown content into timeline events.
    Supports both legacy format and new 5-column table format.
    
    Expected formats:
    
    Legacy format:
    # Date
    **Event:** Event Title
    **Category:** category_name
    **Notes:** Event notes
    **Supporting Docs:** doc1, doc2
    
    OR Table format (5 columns):
    | Date | Event | Description | Category | Documents |
    |------|-------|-------------|----------|-----------|
    | 2024-01-15 | Event Title | Description | category | doc1, doc2 |
    """
    import markdown
    from bs4 import BeautifulSoup
    
    events = []
    
    # Try to parse as table-based format first
    try:
        html = markdown.markdown(content, extensions=['tables'])
        soup = BeautifulSoup(html, 'html.parser')
        
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            # Get header row to determine column mapping
            header_cells = rows[0].find_all(['th', 'td'])
            header_text = [cell.get_text().strip().lower() for cell in header_cells]
            
            # Find column indices by searching for keywords in header text
            col_date = next((i for i, h in enumerate(header_text) if 'date' in h), 0)
            col_event = next((i for i, h in enumerate(header_text) if 'event' in h or 'incident' in h), 1)
            col_category = next((i for i, h in enumerate(header_text) if 'category' in h), 2)
            col_docs = next((i for i, h in enumerate(header_text) if 'doc' in h or 'support' in h), None)
            col_notes = next((i for i, h in enumerate(header_text) if 'note' in h), None)
            col_description = next((i for i, h in enumerate(header_text) if 'description' in h), None)
            
            # Default column positions for standard format
            if col_docs is None:
                col_docs = 4
            if col_notes is None and col_description is None:
                # Try to find the last column that's not already assigned
                all_cols = {col_date, col_event, col_category, col_docs}
                for i in range(len(header_text) - 1, -1, -1):
                    if i not in all_cols:
                        col_notes = i
                        break
            
            # Process data rows
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) < 5:
                    continue
                
                date = cells[col_date].get_text().strip() if col_date < len(cells) else ''
                event = cells[col_event].get_text().strip() if col_event < len(cells) else ''
                category = cells[col_category].get_text().strip().lower() if col_category < len(cells) else 'other'
                
                # Get documents
                if col_docs is not None and col_docs < len(cells):
                    documents = cells[col_docs].get_text().strip()
                else:
                    documents = ''
                
                # Get notes/description
                if col_notes is not None and col_notes < len(cells):
                    notes = cells[col_notes].get_text().strip()
                elif col_description is not None and col_description < len(cells):
                    notes = cells[col_description].get_text().strip()
                elif 2 < len(cells):
                    # Try column 2 as fallback for description
                    notes = cells[2].get_text().strip()
                else:
                    notes = ''
                
                events.append({
                    'date': date,
                    'event': event,
                    'category': category,
                    'notes': notes,
                    'evidence': documents
                })
        
        # If we found table events, return them
        if events:
            return events
    except Exception:
        # Fall back to legacy parsing
        pass
    
    # Legacy format parsing
    lines = content.split('\n')
    current_event = {}

    for line in lines:
        line = line.strip()
        if line.startswith('# '):
            if current_event:
                events.append(current_event)
            try:
                current_event = {'date': line[2:], 'event': '', 'category': '', 'evidence': None, 'notes': ''}
            except ValueError:
                current_event = {}
                continue
        elif line.startswith('**Event:**'):
            current_event['event'] = line[10:].strip()
        elif line.startswith('**Category:**'):
            current_event['category'] = line[13:].strip()
        elif line.startswith('**Notes:**'):
            current_event['notes'] = line[10:].strip()
        elif line.startswith('**Supporting Docs:**') or line.startswith('**Documents:**'):
            current_event['evidence'] = line.split(':', 1)[1].strip()

    if current_event:
        events.append(current_event)

    return events


@login_required
def load_timeline_file(request):
    """
    API endpoint to load and parse a timeline Markdown file.
    
    Returns the main heading and headings from the file.
    """
    file_path = request.GET.get('file_path', '')
    
    if not file_path:
        return JsonResponse({'error': 'No file_path provided'}, status=400)
    
    # Security check - ensure file is within media directory
    if not file_path.startswith(settings.MEDIA_ROOT):
        return JsonResponse({'error': 'Invalid file path'}, status=403)
    
    if not os.path.exists(file_path):
        return JsonResponse({'error': 'File not found'}, status=404)
    
    parsed = parse_timeline_file(file_path)
    
    return JsonResponse({
        'status': 'success',
        'main_heading': parsed.get('headings', [{}])[0].get('text', 'Legal Timeline') if parsed.get('headings') else 'Legal Timeline',
        'headings': parsed.get('headings', []),
        'sections': []  # TODO: Add section parsing to new parser
    })


@login_required
def api_timeline_headings(request):
    """
    API endpoint to get headings from all timeline files.
    
    Returns list of timeline files with their headings.
    """
    case_id = request.GET.get('case_id', '')
    
    if case_id:
        case = get_object_or_404(Case, id=case_id, user=request.user)
        timeline_files = TimelineFile.objects.filter(case=case)
    else:
        timeline_files = TimelineFile.objects.filter(user=request.user)
    
    timelines = []
    for tf in timeline_files:
        if os.path.exists(tf.file_path):
            parsed = parse_timeline_file(tf.file_path)
            timelines.append({
                'id': str(tf.id),  # Convert UUID to string for JSON serialization
                'name': tf.name,
                'file_path': tf.file_path,
                'main_heading': parsed.get('headings', [{}])[0].get('text', 'Legal Timeline') if parsed.get('headings') else 'Legal Timeline',
                'headings': parsed.get('headings', [])
            })
    
    return JsonResponse({'timelines': timelines})


@login_required
def select_timeline(request):
    """
    Select a timeline file to display.
    
    Sets the selected timeline in session and redirects to timeline view.
    """
    timeline_id = request.GET.get('timeline_id')
    file_path = request.GET.get('file_path')
    
    if timeline_id:
        try:
            timeline = TimelineFile.objects.get(id=timeline_id, user=request.user)
            request.session['selected_timeline_id'] = timeline_id
            request.session['selected_timeline_path'] = timeline.file_path
        except TimelineFile.DoesNotExist:
            pass
    elif file_path:
        request.session['selected_timeline_path'] = file_path
    
    return redirect('timeline:timeline')


@login_required
def create_timeline_file(request):
    """
    Create a new TimelineFile entry.
    
    Used when uploading a new Markdown timeline file.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '')
        file_path = request.POST.get('file_path', '')
        case_id = request.POST.get('case_id', '')
        description = request.POST.get('description', '')
        
        case = None
        if case_id:
            try:
                case = Case.objects.get(id=case_id, user=request.user)
            except Case.DoesNotExist:
                pass
        
        timeline_file = TimelineFile.objects.create(
            name=name,
            file_path=file_path,
            case=case,
            description=description,
            user=request.user
        )
        
        return JsonResponse({
            'status': 'success',
            'timeline_file': timeline_file.to_dict()
        })
    
    return JsonResponse({'error': 'POST required'}, status=405)


@login_required
def sync_timeline_api(request, timeline_file_id):
    """
    API endpoint to sync a timeline file.
    Re-parses the file and updates/creates events in the database.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    result = sync_timeline_file(timeline_file_id, request.user)
    
    if 'error' in result:
        return JsonResponse(result, status=404)
    
    return JsonResponse(result)


@login_required
def export_party_timeline(request, case_id, party):
    """
    Export a party's timeline as Markdown file.
    
    This generates a 5-column Markdown table that can be:
    - Viewed in the browser
    - Downloaded as a .md file
    - Processed by the existing PDF generation script
    
    Args:
        case_id: UUID of the case
        party: Source party (CLIENT, OPPOSING, NEUTRAL, COURT, WITNESS)
    
    Returns:
        HttpResponse with markdown content and download headers
    """
    from apps.core.models import Case
    
    case = get_object_or_404(Case, id=case_id, user=request.user)
    
    # Validate party
    valid_parties = [p[0] for p in TimelineEvent.SOURCE_PARTY_CHOICES]
    if party not in valid_parties:
        return HttpResponseBadRequest(f"Invalid party: {party}. Valid parties are: {', '.join(valid_parties)}")
    
    # Generate markdown content
    markdown_content = MarkdownExportService.export_party_timeline(case, party)
    
    # Return as downloadable file
    response = HttpResponse(markdown_content, content_type='text/markdown; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{case.name} - {party} Timeline.md"'
    return response


@login_required
def export_case_timeline(request, case_id):
    """
    Export the complete case timeline with all parties.
    
    Args:
        case_id: UUID of the case
    
    Returns:
        HttpResponse with complete markdown content
    """
    from apps.core.models import Case
    
    case = get_object_or_404(Case, id=case_id, user=request.user)
    
    # Generate complete timeline
    markdown_content = MarkdownExportService.export_full_case_timeline(case)
    
    # Return as downloadable file
    response = HttpResponse(markdown_content, content_type='text/markdown; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{case.name} - Complete Timeline.md"'
    return response


@login_required
def get_potential_matches(request):
    """
    API endpoint to find potential duplicate matches for an event.
    
    Used during markdown ingestion to prevent duplicates.
    
    POST data should include:
        - case_id: UUID of the case
        - date: Event date (YYYY-MM-DD)
        - event: Event title
    
    Returns:
        JsonResponse with list of potential matches
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    from apps.core.models import Case
    
    case_id = request.POST.get('case_id')
    date = request.POST.get('date')
    event_title = request.POST.get('event')
    
    if not case_id or not date or not event_title:
        return JsonResponse({
            'error': 'case_id, date, and event are required'
        }, status=400)
    
    try:
        case = Case.objects.get(id=case_id, user=request.user)
    except Case.DoesNotExist:
        return JsonResponse({'error': 'Case not found'}, status=404)
    
    # Build event data dict
    event_data = {
        'date': date,
        'event': event_title,
        'category': request.POST.get('category', ''),
        'notes': request.POST.get('notes', ''),
    }
    
    # Find potential matches
    matches = MarkdownIngestionService.find_potential_matches(event_data, case)
    
    # Serialize matches for JSON response
    matches_list = list(matches.values(
        'id', 'date', 'event', 'source_party', 'status', 'category'
    ))
    
    return JsonResponse({
        'matches': matches_list,
        'count': len(matches_list)
    })
