from django.shortcuts import render
from django.http import HttpResponse


def messages_view(request):
    return render(request, 'conversation_logs/messages.html')


def upload_messages(request):
    if request.method == 'POST':
        return HttpResponse("Messages uploaded successfully")
    return render(request, 'conversation_logs/upload.html')


def conversation_detail(request, pk):
    return render(request, 'conversation_logs/conversation_detail.html')