from django.shortcuts import render
from django.http import HttpResponse


def archive_view(request):
    return render(request, 'archive/archive.html')


def upload_document(request):
    if request.method == 'POST':
        return HttpResponse("Document uploaded successfully")
    return render(request, 'archive/upload.html')


def document_detail(request, pk):
    return render(request, 'archive/document_detail.html')