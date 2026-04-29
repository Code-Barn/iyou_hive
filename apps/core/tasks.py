"""
Tasks for syncing RawDocuments to Wiki layer using Rust.
"""
from celery import shared_task
from django.conf import settings
import os
import logging
import json

logger = logging.getLogger(__name__)


def initialize_llm_client():
    """
    Initialize LLM client based on settings.
    Returns a client object that matches the LLMClient trait in Rust.
    """
    llm_backend = getattr(settings, 'LLM_BACKEND', 'mock')

    if llm_backend == 'ollama':
        from .llm_clients import OllamaClient
        return OllamaClient(
            endpoint=getattr(settings, 'OLLAMA_ENDPOINT', 'http://localhost:11434'),
            model=getattr(settings, 'OLLAMA_MODEL', 'llama2')
        )
    elif llm_backend == 'gemini':
        from .llm_clients import GeminiClient
        return GeminiClient(
            api_key=getattr(settings, 'GEMINI_API_KEY', ''),
            model=getattr(settings, 'GEMINI_MODEL', 'gemini-pro')
        )
    else:
        from .llm_clients import MockLLMClient
        return MockLLMClient(response="Mock response")


def load_document_text(raw_doc):
    """
    Load the text content from a RawDocument.
    Handles PDF, Markdown, and JSON files.
    """
    if not raw_doc.file:
        return ""

    file_path = raw_doc.file.path

    if raw_doc.file_type == 'pdf':
        # Placeholder: use pdf-extract or similar
        return f"[PDF content from {file_path}]"
    elif raw_doc.file_type == 'md':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    elif raw_doc.file_type == 'json':
        with open(file_path, 'r', encoding='utf-8') as f:
            import json
            data = json.load(f)
            return json.dumps(data, indent=2)
    else:
        return ""


def call_llm(prompt, document_text):
    """
    Call LLM with the sync prompt.
    Placeholder for actual LLM integration.
    """
    # This is where you'd call your LLM API
    # For now, return a mock response
    mock_response = [
        {
            "text": f"Event from document: {document_text[:100]}...",
            "category": "Contested Allegation",
            "source_party": "CLIENT",
            "date": "2023-01-01",
            "citation": f"Layer1/PDFs/{os.path.basename('example.pdf')}"
        }
    ]
    return json.dumps(mock_response)


def sync_document_to_wiki(raw_doc_id: str):
    """
    Syncs a RawDocument to the Wiki using the LLM.
    """
    from apps.core.models import RawDocument, WikiPage
    from apps.core.prompts import SYNC_PROMPT_TEMPLATE
    from apps.core.utils import apply_adversarial_labeling

    raw_doc = RawDocument.objects.get(id=raw_doc_id)
    case = raw_doc.case

    # Load the document text
    document_text = load_document_text(raw_doc)

    # Get existing wiki content for cross-referencing
    existing_wiki = ""
    wiki_pages = WikiPage.objects.filter(case=case)
    for page in wiki_pages:
        existing_wiki += f"\n--- {page.title} ---\n{page.content}\n"

    # Prepare the prompt for the LLM
    prompt = SYNC_PROMPT_TEMPLATE.format(
        document_text=document_text,
        existing_wiki=existing_wiki
    )

    # Call the LLM
    llm_response = call_llm(prompt, document_text)

    # Parse the LLM's JSON response
    events = json.loads(llm_response)

    # Apply adversarial labeling and save to WikiPage
    for event in events:
        # Apply adversarial labeling based on source_party
        labeled_text = apply_adversarial_labeling(
            event['text'],
            event.get('source_party', raw_doc.source_party)
        )

        # Save to WikiPage
        wiki_page, created = WikiPage.objects.get_or_create(
            case=case,
            title=f"event_{event.get('date', 'unknown')}_{event['text'][:20]}",
            defaults={
                'content': labeled_text,
                'category': event.get('category', 'CONTESTED'),
                'version_history': [],
                'citation_references': [{
                    'claim_id': f"CLM-{case.id}-{event.get('date', '000')}-001",
                    'source': event.get('citation', '')
                }]
            }
        )

        if not created:
            # Append to version history
            wiki_page.version_history.append({
                'content': wiki_page.content,
                'updated_at': str(wiki_page.last_updated)
            })
            wiki_page.content = labeled_text
            wiki_page.category = event.get('category', 'CONTESTED')
            wiki_page.save()

    # Detect contradictions
    contradictions = detect_contradictions(str(case.id))

    return f"Synced {raw_doc_id} to Wiki layer. Found {len(contradictions)} contradictions."


@shared_task
def task_sync_raw_document(raw_doc_id: str):
    """
    Celery task to sync a RawDocument to the Wiki layer.
    """
    try:
        result = sync_document_to_wiki(raw_doc_id)
        logger.info(f"Successfully synced {raw_doc_id} to Wiki layer")
        return result
    except RawDocument.DoesNotExist:
        logger.error(f"RawDocument {raw_doc_id} not found")
        return f"RawDocument {raw_doc_id} not found"
    except Exception as e:
        logger.error(f"Error syncing {raw_doc_id}: {str(e)}")
        raise


@shared_task
def task_sync_all_pending():
    """
    Sync all pending RawDocuments that haven't been synced yet.
    """
    from apps.core.models import RawDocument

    # Find documents that haven't been synced
    # This requires tracking sync status - add a `synced_at` field to RawDocument
    pending_docs = RawDocument.objects.filter(
        # synced_at__isnull=True  # Uncomment when field is added
    )

    synced = 0
    for doc in pending_docs:
        try:
            task_sync_raw_document.delay(str(doc.id))
            synced += 1
        except Exception as e:
            logger.error(f"Failed to queue sync for {doc.id}: {e}")

    return f"Queued {synced} documents for sync"


def detect_contradictions(case_id: str):
    """
    Detects contradictions between WikiPages and logs them in contradictions.md.

    Args:
        case_id: The UUID of the case to check.

    Returns:
        list: Contradictions found.
    """
    from apps.core.models import WikiPage
    from pathlib import Path

    wiki_pages = WikiPage.objects.filter(case_id=case_id)
    contradictions = []

    # Compare all pairs of WikiPages for the same case
    wiki_list = list(wiki_pages)
    for i, page1 in enumerate(wiki_list):
        for page2 in wiki_list[i+1:]:
            # Simple contradiction detection (e.g., conflicting dates or statements)
            # This is a placeholder; you may need a more sophisticated NLP approach.
            if "2023-10-15" in page1.content and "2023-11-20" in page2.content and \
               "contract signed" in page1.content.lower() and "contract signed" in page2.content.lower():
                contradictions.append({
                    "contradiction": "Conflicting contract signing dates",
                    "source1": f"Wiki/{page1.title} (Last updated: {page1.last_updated})",
                    "source2": f"Wiki/{page2.title} (Last updated: {page2.last_updated})",
                    "status": "Unresolved"
                })

    # Log contradictions to contradictions.md
    if contradictions:
        contradictions_path = Path(f"media/wiki/{case_id}/contradictions.md")
        contradictions_path.parent.mkdir(parents=True, exist_ok=True)

        with open(contradictions_path, 'w', encoding='utf-8') as f:
            f.write("# Contradictions\n\n")
            for contradiction in contradictions:
                f.write(f"- **Contradiction**: {contradiction['contradiction']}\n")
                f.write(f"  - **Source 1**: {contradiction['source1']}\n")
                f.write(f"  - **Source 2**: {contradiction['source2']}\n")
                f.write(f"  - **Status**: {contradiction['status']}\n\n")

    return contradictions


@shared_task
def task_lint_wiki_for_contradictions(case_id: str):
    """
    Lint Wiki files for contradictions.
    """
    contradictions = detect_contradictions(case_id)
    return f"Found {len(contradictions)} contradictions for case {case_id}"
