from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q
from .models import TimelineEvent
from apps.core.models import Case, TimelineFile
from .utils import (
    parse_markdown_file,
    get_main_heading,
    parse_timeline_events_from_markdown,
    extract_headings,
    find_markdown_files,
    get_timeline_file_info,
    validate_timeline_events
)
import os
import json


@login_required
def timeline_view(request):
    """
    Display the timeline view with events.
    
    Supports:
    - Case filtering via case_id query parameter or session
    - Markdown file based headings
    - Timeline selection
    """
    # Get selected case from session or query param
    case_id = request.session.get('selected_case_id')
    if 'case_id' in request.GET:
        case_id = request.GET['case_id']
        request.session['selected_case_id'] = case_id
    
    # Get case and events
    case = None
    events = TimelineEvent.objects.all()
    
    if case_id:
        try:
            case = Case.objects.get(id=case_id, user=request.user)
            events = events.filter(
                Q(case=case) | Q(case__isnull=True)
            )
        except Case.DoesNotExist:
            pass
    else:
        # Get default case for user
        case = Case.get_default_case(request.user)
        if case:
            request.session['selected_case_id'] = case.id
            events = events.filter(
                Q(case=case) | Q(case__isnull=True)
            )
    
    # Get timeline file information for this case
    timeline_files = []
    main_heading = "Legal Timeline"
    
    if case:
        # Get all timeline files for this case
        timeline_files_qs = TimelineFile.objects.filter(
            Q(case=case) | Q(user=request.user, case__isnull=True)
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
    
    # Parse markdown file for headings and events
    markdown_events = []
    markdown_headings = []
    
    if all_timeline_files and all_timeline_files[0].get('file_path'):
        try:
            parsed = parse_markdown_file(all_timeline_files[0]['file_path'])
            markdown_headings = parsed.get('headings', [])
            markdown_events = parsed.get('events', [])
            
            # Validate events if present
            if markdown_events:
                try:
                    validate_timeline_events(markdown_events)
                except ValueError as e:
                    # Add warning but don't fail
                    pass
        except Exception as e:
            markdown_events = []
            markdown_headings = []
    
    # Use markdown events if available, otherwise fall back to database events
    display_events = markdown_events if markdown_events else list(events)
    
    context = {
        'events': display_events,
        'case': case,
        'main_heading': main_heading,
        'headings': markdown_headings,
        'timeline_files': all_timeline_files,
        'selected_case_id': case_id or (case.id if case else None),
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
    
    Supports both POST with content and GET for form display.
    """
    if request.method == 'POST':
        content = request.POST.get('markdown_content', '')
        timeline_file_path = request.POST.get('timeline_file_path', '')
        case_id = request.POST.get('case_id', '')
        
        # Parse events from markdown
        events = parse_markdown(content)
        
        # Get case if specified
        case = None
        if case_id:
            try:
                case = Case.objects.get(id=case_id, user=request.user)
            except Case.DoesNotExist:
                pass
        
        # Create events
        created_count = 0
        for event_data in events:
            event = TimelineEvent.objects.create(
                date=event_data.get('date'),
                event=event_data.get('event', event_data.get('title', '')),
                category=event_data.get('category', 'other'),
                notes=event_data.get('notes', ''),
                supporting_docs=event_data.get('supporting_docs'),
                timeline_file=timeline_file_path if timeline_file_path else None,
                case=case,
                created_by=request.user
            )
            created_count += 1
        
        return JsonResponse({
            'status': 'success',
            'created': created_count,
            'redirect': '/timeline/'
        })
    
    # GET request - show form
    cases = Case.objects.filter(user=request.user).order_by('-updated_at')
    return render(request, 'timeline/upload.html', {
        'cases': cases,
        'timeline_files': TimelineFile.objects.filter(user=request.user)
    })


@login_required
def event_detail(request, pk):
    """Display detailed information about a timeline event."""
    event = get_object_or_404(TimelineEvent, pk=pk)
    return render(request, 'timeline/event_detail.html', {'event': event})


def parse_markdown(content):
    """
    Legacy function: Parse markdown content into event dicts.
    
    Expected format:
    # Date
    **Event:** Event Title
    **Category:** category_name
    **Notes:** Event notes
    **Supporting Docs:** doc1, doc2
    """
    events = []
    lines = content.split('\n')
    current_event = {}

    for line in lines:
        line = line.strip()
        if line.startswith('# '):
            if current_event:
                events.append(current_event)
            try:
                current_event = {'date': line[2:], 'event': '', 'category': '', 'supporting_docs': None, 'notes': ''}
            except ValueError:
                continue
        elif line.startswith('**Event:**'):
            current_event['event'] = line[10:].strip()
        elif line.startswith('**Category:**'):
            current_event['category'] = line[13:].strip()
        elif line.startswith('**Notes:**'):
            current_event['notes'] = line[10:].strip()
        elif line.startswith('**Supporting Docs:**'):
            current_event['supporting_docs'] = line[18:].strip()

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
    
    parsed = parse_markdown_file(file_path)
    
    return JsonResponse({
        'status': 'success',
        'main_heading': parsed['first_heading'],
        'headings': parsed['headings'],
        'sections': parsed['sections']
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
            parsed = parse_markdown_file(tf.file_path)
            timelines.append({
                'id': tf.id,
                'name': tf.name,
                'file_path': tf.file_path,
                'main_heading': parsed['first_heading'],
                'headings': parsed['headings']
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
