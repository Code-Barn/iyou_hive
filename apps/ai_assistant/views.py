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
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from apps.timeline.models import TimelineEvent
from apps.archive.models import ArchiveDocument, Photo
from apps.core.models import Case, WikiPage, RawDocument
from apps.ai_assistant.models import AIConversation
from apps.ai_assistant.api_client import call_ai_api
from apps.core.prompts import CROSS_EXAMINATION_PROMPT
from apps.core.utils import validate_adversarial_disclaimers
from apps.archive.vector_service import VectorIndexService
from typing import Any, Optional
import json


def _build_semantic_context(case_id: str, query: str) -> str:
    """
    Retrieve semantically relevant document chunks from the case-isolated
    LanceDB vector store and format them for LLM context injection.

    Queries the case's ``document_chunks`` table with the raw user message
    and formats the top-5 results into a clean markdown block that maps each
    fragment back to its original folder path via the ``virtual_path``
    column.

    Args:
        case_id: The UUID string of the active case.
        query: The raw user message used as the vector search query.

    Returns:
        A formatted string of evidence blocks prefixed with
        ``[Source Exhibit Path: ...]`` markers, or an empty string if the
        vector store is unreachable or contains no matching chunks.
    """
    try:
        svc: VectorIndexService = VectorIndexService(case_id)
        results: list[dict[str, Any]] = svc.search(query, top_k=5)
    except (ValueError, FileNotFoundError, Exception):
        return ""

    if not results:
        return ""

    blocks: list[str] = [
        "--- Case Document Evidence (Semantic Search) ---"
    ]
    for row in results:
        vpath: str = row.get("virtual_path", "unknown")
        text: str = row.get("text_content", "")
        blocks.append(f"[Source Exhibit Path: {vpath}]\nText: {text}")

    return "\n\n".join(blocks)


def get_ai_response(user_query: str, case_id: str, user=None) -> str:
    """
    Generates a response from the AI Assistant for a user query.
    Applies cross-examination rules and citations.
    """
    # 1. Fetch relevant WikiPages and RawDocuments for the case
    wiki_pages = WikiPage.objects.filter(case_id=case_id)
    raw_docs = RawDocument.objects.filter(case_id=case_id)

    # 2. Build context for the LLM (include content + metadata)
    context = []
    cited_doc_ids = []
    for page in wiki_pages:
        context.append(f"--- WikiPage: {page.title} (Category: {page.category}) ---\n{page.content}")
    for doc in raw_docs:
        from apps.core.tasks import load_document_text
        context.append(f"--- RawDocument: {doc.document_type} (Source: {doc.source_party}) ---\n{load_document_text(doc)}")
        cited_doc_ids.append(str(doc.id))

    # 3. Construct the full prompt
    context_text = "\n".join(context)
    full_prompt = f"""
{CROSS_EXAMINATION_PROMPT}

---
### **User Query**
{user_query}

---
### **Context**
{context_text}
"""

    # 4. Call the LLM
    llm_response = call_ai_api(full_prompt, user=user)

    # 5. Validate adversarial disclaimers
    cited_sources = [doc.source_party for doc in raw_docs if str(doc.id) in cited_doc_ids]
    if not validate_adversarial_disclaimers(llm_response, cited_sources):
        # Fallback: Prepend a generic disclaimer if validation fails
        llm_response = f"Note: Some claims may be contested. {llm_response}"

    return llm_response


@csrf_exempt
@login_required
def save_api_key(request):
    """Save user's AI API key and provider preference to their profile."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        mistral_api_key = data.get('mistral_api_key', '').strip()
        gemini_api_key = data.get('gemini_api_key', '').strip()
        preferred_provider = data.get('preferred_provider', 'mistral').strip()
        
        # Require at least one API key
        if not mistral_api_key and not gemini_api_key:
            return JsonResponse(
                {'error': 'API key is required'},
                status=400,
            )
        
        # Save the API key to user settings
        from .models import UserSettings
        
        try:
            # Try to get existing settings
            user_settings = UserSettings.objects.get(user=request.user)
        except UserSettings.DoesNotExist:
            # Create new settings if none exist
            user_settings = UserSettings(user=request.user)
        
        changed = False
        
        if mistral_api_key and user_settings.mistral_api_key != mistral_api_key:
            user_settings.mistral_api_key = mistral_api_key
            changed = True
            
        if gemini_api_key and user_settings.gemini_api_key != gemini_api_key:
            user_settings.gemini_api_key = gemini_api_key
            changed = True
            
        if preferred_provider in ['mistral', 'gemini'] and user_settings.preferred_ai_provider != preferred_provider:
            user_settings.preferred_ai_provider = preferred_provider
            changed = True
            
        if changed:
            user_settings.save()
            print(f"API settings updated for user: {request.user.username}")
            return JsonResponse({
                'success': True,
                'message': 'API settings saved successfully. Page will reload to apply changes.'
            })
        else:
            return JsonResponse({
                'success': True,
                'message': 'API settings are already set. No changes needed.'
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        import traceback
        print(f"Error saving API key: {str(e)}")
        print("Full traceback:", traceback.format_exc())
        return JsonResponse({
            'error': f'Failed to save API key: {str(e)}',
            'debug': traceback.format_exc().split('\n')
        }, status=500)


@login_required
def ai_chat_view(request):
    """Render the AI assistant chat interface for the current case."""
    # Check user's API key first, then fall back to settings
    from .models import UserSettings
    
    user_api_key = None
    try:
        user_settings = UserSettings.objects.get(user=request.user)
        user_api_key = user_settings.mistral_api_key
        print(f"User API key retrieved for {request.user.username}: {bool(user_api_key)}")
    except UserSettings.DoesNotExist:
        print(f"No UserSettings found for {request.user.username}")
        pass
    
    # Use user's API key if available, otherwise use settings
    api_key = user_api_key or settings.MISTRAL_API_KEY
    print(f"Final API key status for {request.user.username}: {bool(api_key)}")
    
    # Get case from session - required
    case_id = request.session.get('selected_case_id')
    if not case_id:
        return redirect('core:case_list')
    
    try:
        case = Case.objects.get(id=case_id, user=request.user)
    except Case.DoesNotExist:
        request.session.pop('selected_case_id', None)
        return redirect('core:case_list')
    
    # Get data scoped to case
    recent_events = TimelineEvent.objects.filter(case=case, created_by=request.user)
    recent_docs = ArchiveDocument.objects.filter(case=case, user=request.user)
    
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


def _get_case_or_404(request, case_id):
    """Helper to get case or return 404. Accepts case_id from POST body or session."""
    if not case_id:
        case_id = request.session.get('selected_case_id')
    if not case_id:
        return None, JsonResponse({'error': 'case_id is required'}, status=400)
    try:
        case = Case.objects.get(id=case_id, user=request.user)
        return case, None
    except Case.DoesNotExist:
        return None, JsonResponse({'error': 'Case not found or not accessible'}, status=404)


@login_required
def analyze_document(request):
    """Analyze a document using AI. Requires case_id for scoping."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    document_id = request.POST.get('document_id')
    text = request.POST.get('text', '')
    case_id = request.POST.get('case_id')
    
    case, error_response = _get_case_or_404(request, case_id)
    if error_response:
        return error_response
    
    if document_id:
        # Analyze archive document - ensure user owns it and it belongs to case
        document = get_object_or_404(
            ArchiveDocument,
            pk=document_id,
            user=request.user,
            case=case
        )
        # For now, we can't extract text from PDFs without additional libraries
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
    
    response_text = call_ai_api(prompt, user=request.user)
    
    return JsonResponse({
        'status': 'success',
        'analysis': response_text,
        'document_id': document_id
    })


@login_required
def query_timeline(request):
    """Query timeline events using AI. Requires case_id for scoping."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    # Support both JSON and form-encoded POST bodies
    if request.content_type and 'application/json' in request.content_type:
        import json
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            body = {}
        query = body.get('query', '')
        event_id = body.get('event_id', '')
        case_id = body.get('case_id', '')
        document_content = body.get('document_content', '')
        perspective_mode = body.get('perspective_mode', 'NEUTRAL')
    else:
        query = request.POST.get('query', '')
        event_id = request.POST.get('event_id', '')
        case_id = request.POST.get('case_id', '')
        document_content = request.POST.get('document_content', '')
        perspective_mode = request.POST.get('perspective_mode', 'NEUTRAL')
    
    case, error_response = _get_case_or_404(request, case_id)
    if error_response:
        return error_response

    perspective_instructions: dict[str, str] = {
        'NEUTRAL': (
            "You are an absolute objective legal analyst operating in "
            "NEUTRAL PERSPECTIVE. Your sole duty is to strictly evaluate "
            "the retrieved LanceDB evidence blocks. Outline undisputed facts "
            "with clarity, flag evidential contradictions across directory "
            "paths, and identify gaps in the documentary record. You must "
            "not take a side or advocate for any party. Maintain clinical "
            "impartiality at all times."
        ),
        'CLIENT': (
            "You are a defensive legal advocate operating in CLIENT "
            "PERSPECTIVE. Your task is to synthesise the LanceDB evidence "
            "blocks to build core corroborating factual elements that "
            "protect the client's position. Proactively identify supporting "
            "evidence, frame timelines favourably, and construct a coherent "
            "narrative aligned with the client's case strategy."
        ),
        'OPPOSING': (
            "You are a hostile cross-examiner operating in OPPOSING "
            "PERSPECTIVE. Your mandate is to scrutinise the extracted "
            "snippets for notice violations, chronological holes, or "
            "failures to meet evidentiary baselines. Apply the strictest "
            "adversarial lens: challenge assumptions, flag inconsistencies, "
            "identify missing corroboration, and probe for weaknesses in "
            "the documentary chain of custody."
        ),
    }
    perspective_prompt: str = perspective_instructions.get(
        perspective_mode,
        perspective_instructions['NEUTRAL'],
    )

    # --- Operational persona: inject client / opposing party names ---
    client_name: str = case.client_legal_name or "Client"
    opposing_name: str = case.opposing_legal_name or "Opposing Party"
    persona_clause: str = (
        "Operational Persona Context: You are evaluating evidence records "
        "for an active lawsuit. Your client/user is "
        f"{client_name}. "
        "The adversarial/opposing party is "
        f"{opposing_name}. "
        "Synthesize all timeline data and extracted fields using these "
        "explicitly assigned positioning anchors."
    )
    perspective_prompt = f"{persona_clause}\n\n{perspective_prompt}"

    # --- Semantic retrieval from case-isolated LanceDB ---
    semantic_context: str = _build_semantic_context(str(case.id), query)

    if event_id:
        # Query about specific event - ensure user owns it and it belongs to case
        event = get_object_or_404(
            TimelineEvent,
            pk=event_id,
            created_by=request.user,
            case=case
        )
        # Build evidence list from M2M
        evidence_list = [doc.title for doc in event.evidence.all()]
        evidence_str = ', '.join(evidence_list) if evidence_list else 'None'
        context = f"""{perspective_prompt}

{semantic_context}

Timeline Event Context (Case: {case_id}):
Date: {event.date}
Event: {event.event}
Category: {event.category}
Notes: {event.notes}
Evidence: {evidence_str}

User Query: {query}

Please provide a comprehensive answer based on this event and suggest any relevant connections or follow-up actions.
"""
    else:
        # Query about all timeline events for this case - filter by user AND case
        events = TimelineEvent.objects.filter(
            created_by=request.user,
            case=case
        ).order_by('date')
        event_items = []
        for e in events:
            event_items.append(f"Date: {e.date}\nEvent: {e.event}\nCategory: {e.category}\nNotes: {e.notes}")
        context_str = "\n\n".join(event_items)

        doc_sight = ""
        if document_content:
            doc_sight = f"""
--- Current Document Context ---
You are currently looking at the following document:
{document_content}
--- End Document Context ---
"""
        context = f"""{perspective_prompt}

{semantic_context}

Legal Timeline Events (Case: {case_id}):
{context_str}
{doc_sight}
User Query: {query}

Please analyze the timeline and provide insights, connections, and recommendations.
"""
    
    response_text = call_ai_api(context, user=request.user)
    
    return JsonResponse({
        'status': 'success',
        'response': response_text,
        'event_id': event_id,
        'case_id': case_id
    })


@login_required
def suggest_events(request):
    """Generate AI suggestions for new timeline events based on existing data. Requires case_id for scoping."""
    if request.method == 'POST':
        case_id = request.POST.get('case_id')
        
        case, error_response = _get_case_or_404(request, case_id)
        if error_response:
            return error_response
        
        # Get last N events for context - filter by user AND case
        events = TimelineEvent.objects.filter(
            created_by=request.user,
            case=case
        ).order_by('-date')[:10]
        
        # Get documents for context - filter by user AND case
        documents = ArchiveDocument.objects.filter(
            user=request.user,
            case=case
        ).order_by('-upload_date')[:10]
        
        event_items = []
        for e in events:
            event_items.append(f"- {e.date}: {e.event} ({e.category})\n  {e.notes}")
        
        doc_items = []
        for d in documents:
            doc_items.append(f"- {d.title} ({d.category}): {d.description}")
        
        events_text = "\n\n".join(event_items)
        docs_text = "\n".join(doc_items)
        
        context = f"""Analyze the following legal timeline events and documents for Case {case_id}:

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
        
        response_text = call_ai_api(context, user=request.user)
        
        return JsonResponse({
            'status': 'success',
            'suggestions': response_text
        })
    
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def analyze_timeline_event(request, event_id):
    """Analyze a specific timeline event with AI and return structured data. Requires case_id for scoping."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    case_id = request.POST.get('case_id')
    
    case, error_response = _get_case_or_404(request, case_id)
    if error_response:
        return error_response
    
    # Get event - ensure user owns it and it belongs to case
    event = get_object_or_404(
        TimelineEvent,
        pk=event_id,
        created_by=request.user,
        case=case
    )
    
    # Get linked documents via evidence M2M
    documents = event.evidence.all()
    docs_text = []
    for d in documents:
        docs_text.append(f"- {d.title}: {d.description}")
    docs_str = "\n".join(docs_text)
    
    prompt = f"""Analyze this legal timeline event and its supporting documents for Case {case_id}:

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
    
    response_text = call_ai_api(prompt, user=request.user)
    
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


@login_required
def analyze_photo(request):
    """Analyze a single photo using AI."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    photo_id = request.POST.get('photo_id')
    if not photo_id:
        return JsonResponse({'error': 'photo_id is required'}, status=400)
    
    result = analyze_photo(photo_id)
    
    if result['success']:
        return JsonResponse({
            'status': 'success',
            'photo_id': photo_id,
            'analysis': result['analysis']
        })
    else:
        return JsonResponse({'error': result['error']}, status=500)


@login_required
def match_photos_to_events_view(request):
    """Match photos to timeline events for a case."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    case_id = request.POST.get('case_id')
    if not case_id:
        return JsonResponse({'error': 'case_id is required'}, status=400)
    
    try:
        case = Case.objects.get(id=case_id, user=request.user)
        links = match_photos_to_events(case, request.user)
        
        return JsonResponse({
            'status': 'success',
            'case_id': case_id,
            'matched_links': len(links),
            'links': [
                {
                    'photo_id': link.photo.id,
                    'event_id': link.event.id,
                    'confidence': link.confidence,
                    'notes': link.notes
                }
                for link in links
            ]
        })
    except Case.DoesNotExist:
        return JsonResponse({'error': 'Case not found or not accessible'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Failed to match photos: {str(e)}'}, status=500)
