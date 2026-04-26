from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from apps.timeline.models import TimelineEvent
from apps.archive.models import ArchiveDocument
from apps.core.models import Case
from apps.ai_assistant.models import AIConversation
import json
import urllib.request
import urllib.parse


@login_required
def ai_chat_view(request):
    """Render the AI assistant chat interface."""
    api_key = settings.MISTRAL_API_KEY
    
    case_id = request.session.get('selected_case_id')
    if 'case_id' in request.GET:
        case_id = request.GET['case_id']
        request.session['selected_case_id'] = case_id
    
    case = None
    recent_events = TimelineEvent.objects.filter(created_by=request.user)
    recent_docs = ArchiveDocument.objects.filter(user=request.user)
    
    if case_id:
        try:
            case = Case.objects.get(id=case_id, user=request.user)
            recent_events = recent_events.filter(case=case)
            recent_docs = recent_docs.filter(case=case)
        except Case.DoesNotExist:
            request.session.pop('selected_case_id', None)
    
    if case is None and case_id is None:
        existing_cases = Case.objects.filter(user=request.user).first()
        if existing_cases:
            case = existing_cases
            request.session['selected_case_id'] = case.id
            recent_events = recent_events.filter(case=case)
            recent_docs = recent_docs.filter(case=case)
    
    recent_events = recent_events.order_by('-date')[:5]
    recent_docs = recent_docs.order_by('-upload_date')[:5]
    
    conversations = []
    if case:
        conversations = AIConversation.objects.filter(
            user=request.user,
            case=case
        ).order_by('-updated_at')[:10]
    
    return render(request, 'ai_assistant/chat.html', {
        'api_configured': bool(api_key),
        'recent_events': recent_events,
        'recent_docs': recent_docs,
        'case': case,
        'selected_case_id': case_id or (case.id if case else None),
        'conversations': conversations,
    })


def analyze_document(request):
    """Analyze a document using AI."""
    if request.method == 'POST':
        document_id = request.POST.get('document_id')
        text = request.POST.get('text', '')
        
        if document_id:
            # Analyze archive document - ensure user owns it
            document = get_object_or_404(
                ArchiveDocument,
                pk=document_id,
                user=request.user if request.user.is_authenticated else None
            )
            # For now, we can't extract text from PDFs without additional libraries
            # This is a placeholder for future implementation
            text = f"Document: {document.title}\nCategory: {document.category}\nTags: {document.tags}"
        
        prompt = f"""Analyze the following legal document and provide:
1. A brief summary
2. Key points or important clauses
3. Any dates mentioned
4. Recommended actions or follow-ups

Document content:
{text}

Please format your response in markdown with clear sections.
"""
        
        response_text = call_ai_api(prompt)
        
        return JsonResponse({
            'status': 'success',
            'analysis': response_text,
            'document_id': document_id
        })
    
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def query_timeline(request):
    """Query timeline events using AI."""
    if request.method == 'POST':
        query = request.POST.get('query', '')
        event_id = request.POST.get('event_id')
        
        if event_id:
            # Query about specific event - ensure user owns it
            event = get_object_or_404(
                TimelineEvent,
                pk=event_id,
                created_by=request.user
            )
            context = f"""Timeline Event Context:
Date: {event.date}
Event: {event.event}
Category: {event.category}
Notes: {event.notes}
Supporting Documents: {event.supporting_docs}

User Query: {query}

Please provide a comprehensive answer based on this event and suggest any relevant connections or follow-up actions.
"""
        else:
            # Query about all timeline events - ONLY USER'S EVENTS
            events = TimelineEvent.objects.filter(
                created_by=request.user
            ).order_by('date')
            event_items = []
            for e in events:
                event_items.append(f"Date: {e.date}\nEvent: {e.event}\nCategory: {e.category}\nNotes: {e.notes}")
            context_str = "\n\n".join(event_items)
            context = f"""Legal Timeline Events:
{context_str}

User Query: {query}

Please analyze the timeline and provide insights, connections, and recommendations.
"""
        
        response_text = call_ai_api(context)
        
        return JsonResponse({
            'status': 'success',
            'response': response_text,
            'event_id': event_id
        })
    
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def suggest_events(request):
    """Generate AI suggestions for new timeline events based on existing data."""
    if request.method == 'POST':
        # Get last N events for context - ONLY USER'S DATA
        events = TimelineEvent.objects.filter(
            created_by=request.user
        ).order_by('-date')[:10]
        documents = ArchiveDocument.objects.filter(
            user=request.user
        ).order_by('-upload_date')[:10]
        
        event_items = []
        for e in events:
            event_items.append(f"- {e.date}: {e.event} ({e.category})\n  {e.notes}")
        
        doc_items = []
        for d in documents:
            doc_items.append(f"- {d.title} ({d.category}): {d.description}")
        
        events_text = "\n\n".join(event_items)
        docs_text = "\n".join(doc_items)
        
        context = f"""Analyze the following legal timeline events and documents:

Timeline Events:
{events_text}

Documents:
{docs_text}

Based on this information, suggest:
1. Missing events that should be added to the timeline
2. Connections between existing events
3. Important dates or deadlines to track
4. Documentation that might be missing

Format your suggestions as markdown with clear sections.
"""
        
        response_text = call_ai_api(context)
        
        return JsonResponse({
            'status': 'success',
            'suggestions': response_text
        })
    
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def analyze_timeline_event(request, event_id):
    """Analyze a specific timeline event with AI and return structured data."""
    event = get_object_or_404(TimelineEvent, pk=event_id)
    
    # Get linked documents
    documents = event.get_archive_documents()
    docs_text = []
    for d in documents:
        docs_text.append(f"- {d.title}: {d.description}")
    docs_str = "\n".join(docs_text)
    
    prompt = f"""Analyze this legal timeline event and its supporting documents:

Event: {event.event}
Date: {event.date}
Category: {event.category}
Notes: {event.notes}

Supporting Documents:
{docs_str if docs_str else "(None)"}

Please provide:
1. A brief summary of this event
2. Its legal significance
3. Any important dates or deadlines mentioned
4. Recommended next steps or follow-up actions
5. Potential connections to other events or documents

Format as markdown with clear headings.
"""
    
    response_text = call_ai_api(prompt)
    
    return JsonResponse({
        'status': 'success',
        'event_id': event_id,
        'event_data': {
            'date': event.date.strftime('%Y-%m-%d'),
            'event': event.event,
            'category': event.category,
            'notes': event.notes,
        },
        'analysis': response_text
    })


def call_ai_api(prompt, model="mistral-tiny", temperature=0.7, max_tokens=2000):
    """
    Call the Mistral AI API to get a response.
    
    This is a placeholder implementation that simulates AI responses
    when no API key is configured.
    """
    api_key = settings.MISTRAL_API_KEY
    
    if not api_key:
        # Return a simulated response for development
        return (
            "Based on the information provided, here's my analysis:\n\n"
            "**Summary:** This is a simulated response since no Mistral API key is configured.\n\n"
            "**Key Points:**\n"
            "- The event requires careful review\n"
            "- Important dates should be tracked\n"
            "- Connections to other documents should be established\n\n"
            "**Recommendations:**\n"
            "1. Review the supporting documents\n"
            "2. Follow up on any deadlines\n"
            "3. Consider linking related events\n\n"
            "For actual AI analysis, please configure your MISTRAL_API_KEY in settings."
        )
    
    try:
        # Make actual API call to Mistral
        return call_mistral_api(prompt, api_key, model, temperature, max_tokens)
    
    except Exception as e:
        # Fallback for API errors
        return f"I encountered an error processing your request: {str(e)}\n\nPlease try again, or check your Mistral API configuration."


def call_mistral_api(prompt, api_key, model="mistral-tiny", temperature=0.7, max_tokens=2000):
    """
    Call the Mistral AI API using urllib.
    
    This is a more reliable implementation that doesn't require the requests library.
    """
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data['choices'][0]['message']['content']
    
    except Exception as e:
        raise Exception(f"API call failed: {str(e)}")
