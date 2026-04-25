from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, FileResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import ArchiveDocument
from .forms import ArchiveDocumentForm
import os
from django.db import models


def archive_view(request):
    """Display all archived documents."""
    documents = ArchiveDocument.objects.all().order_by('-upload_date')
    return render(request, 'archive/archive.html', {'documents': documents})


@login_required
def upload_document(request):
    """Upload a document to the archive."""
    if request.method == 'POST':
        form = ArchiveDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploader = request.user
            document.save()
            messages.success(request, 'Document uploaded successfully!')
            return redirect('archive:archive')
        else:
            messages.error(request, 'Error uploading document. Please check the form.')
    else:
        form = ArchiveDocumentForm()
    
    return render(request, 'archive/upload.html', {'form': form})


def document_detail(request, pk):
    """Display a single document with metadata."""
    document = get_object_or_404(ArchiveDocument, pk=pk)
    return render(request, 'archive/document_detail.html', {'document': document})


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
