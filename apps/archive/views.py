from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, FileResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import ArchiveDocument
from .forms import ArchiveDocumentForm
from apps.core.models import Case
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
    """Display all archived documents for the current case."""
    # Get case from session - required
    case_id = request.session.get('selected_case_id')
    if not case_id:
        return redirect('core:case_list')
    
    try:
        case = Case.objects.get(id=case_id, user=request.user)
    except Case.DoesNotExist:
        request.session.pop('selected_case_id', None)
        return redirect('core:case_list')
    
    # Filter documents by case
    documents = ArchiveDocument.objects.filter(case=case, user=request.user)
    documents = documents.order_by('-upload_date')
    
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
        'archive_map': archive_map,
        'case': case,
        'selected_case_id': case_id or (case.id if case else None),
    })


@login_required
def upload_document(request):
    """
    Upload a document to the archive.
    Requires case to be selected (middleware enforces this).
    """
    # Get case from session - required
    case_id = request.session.get('selected_case_id')
    if not case_id:
        return redirect('core:case_list')
    
    try:
        case = Case.objects.get(id=case_id, user=request.user)
    except Case.DoesNotExist:
        request.session.pop('selected_case_id', None)
        return redirect('core:case_list')
    
    if request.method == 'POST':
        form = ArchiveDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploader = request.user
            document.user = request.user
            document.case = case
            
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
                                created_by=request.user,
                                case=case
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
def bulk_upload(request):
    """
    Bulk upload multiple files or folder structures.
    Accepts multiple files and preserves folder hierarchy via path.
    """
    case_id = request.session.get('selected_case_id')
    case = None
    if case_id:
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            case = Case.get_default_case(request.user)
    else:
        case = Case.get_default_case(request.user)
        if case:
            request.session['selected_case_id'] = case.id
    
    if request.method == 'POST':
        files = request.FILES.getlist('files')
        base_path = request.POST.get('base_path', '')
        
        uploaded_count = 0
        for uploaded_file in files:
            # Determine if this is a draft
            is_draft = 'drafts/' in base_path or uploaded_file.name.startswith('drafts/')
            
            # Auto-detect file type
            file_ext = uploaded_file.name.lower().split('.')[-1] if '.' in uploaded_file.name else ''
            file_type_map = {
                'pdf': 'pdf', 'png': 'image', 'jpg': 'image', 'jpeg': 'image',
                'gif': 'image', 'webp': 'image', 'svg': 'image',
                'doc': 'word', 'docx': 'word',
                'txt': 'text', 'md': 'text',
                'eml': 'email', 'msg': 'email',
            }
            file_type = file_type_map.get(file_ext, 'other')
            
            # Create the document
            doc = ArchiveDocument.objects.create(
                title=uploaded_file.name,
                file=uploaded_file,
                path=base_path + uploaded_file.name if base_path else uploaded_file.name,
                file_type=file_type,
                is_draft=is_draft,
                is_immutable=not is_draft,
                case=case,
                user=request.user,
                uploader=request.user
            )
            uploaded_count += 1
        
        return JsonResponse({
            'status': 'success',
            'uploaded': uploaded_count
        })
    
    return JsonResponse({'error': 'POST required'}, status=405)


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
    """API endpoint to list all documents for current user."""
    documents = ArchiveDocument.objects.filter(user=request.user).values(
        'id', 'title', 'file_type', 'upload_date', 'category', 'description'
    )
    return JsonResponse(list(documents), safe=False)


@login_required
def api_document_search(request):
    """API endpoint to search documents for current user."""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    
    documents = ArchiveDocument.objects.filter(user=request.user)
    
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


@login_required
def api_file_tree(request):
    """API endpoint to get file tree HTML for the archive."""
    from django.template.loader import render_to_string
    
    documents = ArchiveDocument.objects.filter(user=request.user).order_by('-upload_date')
    
    html = render_to_string('archive/file_tree_partial.html', {'documents': documents})
    return HttpResponse(html)


@login_required
def api_file_preview(request, pk):
    """API endpoint to preview a document."""
    document = get_object_or_404(ArchiveDocument, pk=pk, user=request.user)
    
    if document.is_pdf():
        return JsonResponse({
            'type': 'pdf',
            'title': document.title,
            'url': document.get_file_url(),
            'message': 'PDF preview requires a PDF viewer'
        })
    elif document.is_image():
        return JsonResponse({
            'type': 'image',
            'title': document.title,
            'url': document.get_file_url()
        })
    elif document.file_type == 'markdown' or document.file_type == 'text':
        is_md = document.file_type == 'markdown' or (document.file and document.file.name and document.file.name.lower().endswith('.md'))
        if is_md:
            content = ''
            if document.file:
                try:
                    fp = document.file.path
                    if fp and os.path.exists(fp):
                        content = open(fp, 'r', encoding='utf-8', errors='ignore').read()
                except Exception:
                    pass
            return JsonResponse({'type': 'markdown', 'title': document.title, 'content': content})
    
    return JsonResponse({
        'type': 'other',
        'title': document.title,
        'description': document.description,
        'category': document.category,
        'tags': document.tags
    })


@login_required
def api_get_content(request, pk):
    """API endpoint to get document content for canvas editing."""
    document = get_object_or_404(ArchiveDocument, pk=pk, user=request.user)
    
    content = ''
    if document.file:
        file_path = document.file.path
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:
                content = f'# {document.title}\n\n[Content could not be loaded]'
    
    return JsonResponse({
        'title': document.title,
        'content': content
    })


@login_required
def api_save_canvas(request):
    """API endpoint to save canvas content as a document."""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        title = data.get('title', 'Untitled')
        content = data.get('content', '')
        
        from django.core.files.base import ContentFile
        content_file = ContentFile(content.encode('utf-8'))
        
        document = ArchiveDocument.objects.create(
            title=title,
            file=content_file,
            file_type='text',
            user=request.user,
            uploader=request.user
        )
        
        return JsonResponse({'status': 'success', 'document_id': document.pk})
    
    return JsonResponse({'error': 'POST required'}, status=405)


@login_required
def save_document(request, pk):
    """
    Save document, enforcing read-only for immutable files.
    Only draft documents can be edited.
    """
    document = get_object_or_404(ArchiveDocument, pk=pk, user=request.user)
    
    if document.is_immutable:
        return JsonResponse({
            'status': 'error', 
            'message': 'This file is read-only to preserve integrity.'
        }, status=403)
    
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        content = data.get('content', '')
        
        # Save the new content
        from django.core.files.base import ContentFile
        document.file.save(document.title, ContentFile(content.encode('utf-8')), save=True)
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'POST required'}, status=405)


@login_required
def download_archive(request, case_id):
    """
    Download entire archive as a ZIP file.
    """
    import io
    import zipfile
    
    case = get_object_or_404(Case, id=case_id, user=request.user)
    documents = ArchiveDocument.objects.filter(case=case)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for doc in documents:
            if doc.file:
                filename = doc.path or doc.title
                zip_file.writestr(filename, doc.file.read())
    
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{case.name}_archive.zip"'
    return response


@login_required
def create_sync_config(request):
    """Create a sync configuration for external storage."""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        
        case_id = request.session.get('selected_case_id')
        case = Case.get_default_case(request.user)
        
        sync_config = SyncedArchive.objects.create(
            case=case,
            user=request.user,
            provider=data.get('provider'),
            external_path=data.get('external_path'),
            access_token=data.get('access_token', '')
        )
        
        return JsonResponse({
            'status': 'success',
            'sync_id': sync_config.pk
        })
    
    return JsonResponse({'error': 'POST required'}, status=405)


@login_required
def sync_archive(request, sync_id):
    """Trigger sync for a sync configuration."""
    sync_config = get_object_or_404(SyncedArchive, pk=sync_id, user=request.user)
    
    synced_count = sync_config.sync()
    
    return JsonResponse({
        'status': 'success',
        'synced': synced_count
    })
