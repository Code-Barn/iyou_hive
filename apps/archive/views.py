from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, FileResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import ArchiveDocument
from .forms import ArchiveDocumentForm
import os
import sys
import subprocess
from django.db import models
from django.conf import settings
from pathlib import Path


def get_user_archive_dir(user):
    """Get the archive directory path for a user."""
    if user and user.is_authenticated:
        archive_base = Path(settings.MEDIA_ROOT) / 'archive'
        user_dir = archive_base / str(user.id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return str(user_dir)
    return None


def get_archive_base_dir():
    """Get the base archive directory."""
    archive_base = Path(settings.MEDIA_ROOT) / 'archive'
    archive_base.mkdir(parents=True, exist_ok=True)
    return str(archive_base)


def run_pdf_conversion(pdf_path):
    """
    Run the PDF to Markdown conversion script.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        str: Path to the converted Markdown file, or None if failed
    """
    try:
        scripts_dir = Path(settings.BASE_DIR) / 'scripts'
        script_path = str(scripts_dir / 'pdf_to_md_conversion.py')
        
        # Run the conversion script
        result = subprocess.run(
            [sys.executable, script_path, pdf_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # Get the output file path (script replaces .pdf with .md)
            md_path = pdf_path.replace('.pdf', '.md')
            if os.path.exists(md_path):
                return md_path
        else:
            print(f"PDF conversion error: {result.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"PDF conversion failed: {e}", file=sys.stderr)
    
    return None


def run_filemapper(directory):
    """
    Run the filemapper script to generate archive_map.md.
    
    Args:
        directory: Path to the user's archive directory
        
    Returns:
        str: Path to the generated map file, or None if failed
    """
    try:
        scripts_dir = Path(settings.BASE_DIR) / 'scripts'
        script_path = str(scripts_dir / 'filemapper.py')
        
        # Determine output path
        map_path = os.path.join(directory, 'archive_map.md')
        
        # Run the filemapper script
        result = subprocess.run(
            [sys.executable, script_path, directory, map_path, '6'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and os.path.exists(map_path):
            return map_path
        else:
            print(f"Filemapper error: {result.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"Filemapper failed: {e}", file=sys.stderr)
    
    return None


@login_required
def archive_view(request):
    """Display all archived documents."""
    documents = ArchiveDocument.objects.all().order_by('-upload_date')
    
    # Get archive map if it exists
    archive_map = None
    if request.user and request.user.is_authenticated:
        user_archive_dir = get_user_archive_dir(request.user)
        map_path = os.path.join(user_archive_dir, 'archive_map.md')
        if os.path.exists(map_path):
            with open(map_path, 'r', encoding='utf-8') as f:
                archive_map = f.read()
    
    return render(request, 'archive/archive.html', {
        'documents': documents,
        'archive_map': archive_map
    })


@login_required
def upload_document(request):
    """
    Upload a document to the archive.
    
    For PDF files, automatically:
    1. Save the PDF
    2. Convert to Markdown using pdf_to_md_conversion.py
    3. Save the Markdown file
    4. Update the archive map using filemapper.py
    """
    if request.method == 'POST':
        form = ArchiveDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploader = request.user
            
            # Get user's archive directory
            user_archive_dir = get_user_archive_dir(request.user)
            
            # Save the document
            document.save()
            
            # Get the saved file path
            file_path = document.file.path
            
            # For PDFs, auto-convert to Markdown
            if file_path.lower().endswith('.pdf'):
                md_path = run_pdf_conversion(file_path)
                if md_path:
                    # Create a linked Markdown document in the archive
                    from apps.timeline.models import TimelineEvent
                    from .models import ArchiveDocument as ArchiveDoc
                    import re
                    
                    # Parse the markdown to extract event data
                    with open(md_path, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                    
                    # Extract metadata from markdown frontmatter
                    date_match = re.search(r'date:\s*(\S+)', md_content)
                    title_match = re.search(r'title:\s*(.+)', md_content)
                    category_match = re.search(r'category:\s*(\S+)', md_content)
                    
                    if date_match or title_match:
                        # Create a timeline event from the markdown
                        try:
                            # Parse date if found, otherwise use upload date
                            event_date = None
                            if date_match:
                                try:
                                    from datetime import datetime
                                    event_date = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
                                except (ValueError, TypeError):
                                    event_date = document.upload_date
                            if event_date is None:
                                event_date = document.upload_date
                            
                            event = TimelineEvent.objects.create(
                                date=event_date,
                                event=title_match.group(1) if title_match else 'Imported Document',
                                category=category_match.group(1).lower() if category_match else 'other',
                                notes=f"Converted from PDF: {document.title}",
                                supporting_docs=str(document.id),
                                created_by=request.user
                            )
                            
                            # Link the document to the event
                            document.timeline_event = event
                            document.save()
                        except Exception as e:
                            print(f"Failed to create timeline event: {e}", file=sys.stderr)
            
            # Update the archive map after any file changes
            if user_archive_dir:
                run_filemapper(user_archive_dir)
            
            messages.success(request, 'Document uploaded successfully!')
            return redirect('archive:archive')
        else:
            messages.error(request, 'Error uploading document. Please check the form.')
    else:
        form = ArchiveDocumentForm()
    
    return render(request, 'archive/upload.html', {'form': form})


@login_required
def document_detail(request, pk):
    """Display a single document with metadata."""
    document = get_object_or_404(ArchiveDocument, pk=pk)
    
    # Get related timeline events
    related_events = []
    if document.timeline_event:
        related_events = [document.timeline_event]
    
    # Get converted markdown file if it exists
    markdown_content = None
    if document.file and document.file.name.lower().endswith('.pdf'):
        md_path = document.file.path.replace('.pdf', '.md')
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
    
    return render(request, 'archive/document_detail.html', {
        'document': document,
        'related_events': related_events,
        'markdown_content': markdown_content
    })


@login_required
def document_file(request, pk):
    """Serve the actual document file."""
    document = get_object_or_404(ArchiveDocument, pk=pk)
    
    if not document.file:
        return HttpResponse('Document file not found', status=404)
    
    # For PDFs, set content type
    if document.is_pdf():
        response = FileResponse(document.file.open('rb'))
        response['Content-Type'] = 'application/pdf'
        response['Content-Disposition'] = f'inline; filename="{document.title}.pdf"'
        return response
    
    # For images
    if document.is_image():
        response = FileResponse(document.file.open('rb'))
        response['Content-Type'] = f'image/{document.get_file_extension()}'
        response['Content-Disposition'] = f'inline; filename="{document.title}"'
        return response
    
    # For other file types
    response = FileResponse(document.file.open('rb'))
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(document.file.name)}"'
    return response


@login_required
def document_thumbnail(request, pk):
    """Generate or serve a thumbnail for an image document."""
    document = get_object_or_404(ArchiveDocument, pk=pk)
    
    if not document.is_image():
        return HttpResponse('Not an image', status=400)
    
    # For now, just serve the original image
    # In production, this would generate a thumbnail
    return document_file(request, pk)


# API Endpoints

@login_required
def api_document_list(request):
    """API endpoint to list all documents."""
    documents = ArchiveDocument.objects.all().values(
        'id', 'title', 'file_type', 'upload_date', 'category', 'description'
    )
    return JsonResponse(list(documents), safe=False)


@login_required
def api_document_search(request):
    """API endpoint to search documents."""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    
    documents = ArchiveDocument.objects.all()
    
    if query:
        documents = documents.filter(
            models.Q(title__icontains=query) | 
            models.Q(description__icontains=query) |
            models.Q(tags__contains=[query])
        )
    
    if category:
        documents = documents.filter(category__iexact=category)
    
    results = documents.values(
        'id', 'title', 'file_type', 'upload_date', 'category', 'description'
    )
    
    return JsonResponse(list(results), safe=False)


@login_required
def generate_archive_map(request):
    """API endpoint to regenerate the archive map."""
    if request.user and request.user.is_authenticated:
        user_archive_dir = get_user_archive_dir(request.user)
        if user_archive_dir:
            map_path = run_filemapper(user_archive_dir)
            if map_path:
                with open(map_path, 'r', encoding='utf-8') as f:
                    map_content = f.read()
                return JsonResponse({
                    'status': 'success',
                    'map_content': map_content
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Failed to generate archive map'
                }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Unauthorized'
    }, status=401)


@login_required  
def link_to_timeline(request, document_id, event_id):
    """Link an archive document to a timeline event."""
    from apps.timeline.models import TimelineEvent
    
    document = get_object_or_404(ArchiveDocument, pk=document_id)
    event = get_object_or_404(TimelineEvent, pk=event_id)
    
    # Add document ID to event's supporting_docs
    current_docs = event.supporting_docs or []
    if isinstance(current_docs, str):
        # Parse existing string
        try:
            import json
            current_docs = json.loads(current_docs)
        except:
            current_docs = []
    
    if not isinstance(current_docs, list):
        current_docs = [current_docs]
    
    if document_id not in current_docs:
        current_docs.append(document_id)
        event.supporting_docs = current_docs
        event.save()
    
    document.timeline_event = event
    document.save()
    
    return JsonResponse({
        'status': 'success',
        'event_id': event_id,
        'document_id': document_id
    })
