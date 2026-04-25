from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import os


def ai_chat_view(request):
    api_key = settings.MISTRAL_API_KEY
    return render(request, 'ai_assistant/chat.html', {'api_configured': bool(api_key)})


def analyze_document(request):
    if request.method == 'POST':
        return JsonResponse({'status': 'placeholder', 'message': 'AI analysis coming soon'})
    return JsonResponse({'error': 'POST required'}, status=400)