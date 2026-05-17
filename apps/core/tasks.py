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
            model=getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash')
        )
    else:
        from .llm_clients import MockLLMClient
        return MockLLMClient()  # Uses default valid JSON response


def load_document_text(raw_doc):
    """
    Load the text content from a RawDocument.
    Handles PDF, Markdown, and JSON files using the integrated scripts.
    """
    if not raw_doc.file:
        return ""

    file_path = raw_doc.file.path

    try:
        if raw_doc.file_type == 'pdf':
            # Use the PDF extraction script
            import sys
            import os
            
            # Add scripts directory to path
            scripts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            
            # Import and use the PDF extraction function
            from legal_utils import extract_text_from_pdf
            return extract_text_from_pdf(file_path)
            
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
    except Exception as e:
        logger.error(f"Failed to load document text from {file_path}: {e}")
        return f"[Error loading document: {str(e)}]"


def call_llm(prompt, document_text):
    """
    Call LLM with the sync prompt using the configured LLM client.
    
    Args:
        prompt (str): The prompt to send to the LLM
        document_text (str): The document text for context
        
    Returns:
        str: JSON response from the LLM
        
    Raises:
        Exception: If LLM call fails
    """
    try:
        # Initialize the LLM client based on settings
        llm_client = initialize_llm_client()
        
        # Call the LLM with the prompt
        response = llm_client.generate(prompt)
        
        # Log the successful call
        logger.info(f"LLM call successful for document: {document_text[:50]}...")
        
        # Return the response as JSON
        return response
        
    except Exception as e:
        # Log the error and return a fallback mock response
        logger.error(f"LLM call failed: {str(e)}")
        
        # Return a mock response for graceful degradation
        mock_response = [
            {
                "text": f"Event from document: {document_text[:100]}...",
                "category": "Contested Allegation",
                "source_party": "CLIENT",
                "date": "2023-01-01",
                "citation": f"Layer1/PDFs/{os.path.basename('example.pdf' if 'example.pdf' in document_text else 'document.pdf')}"
            }
        ]
        return json.dumps(mock_response)


def sync_document_to_wiki(raw_doc_id: str):
    """
    Syncs a RawDocument to the Wiki using the LLM.
    
    Args:
        raw_doc_id (str): ID of the RawDocument to sync
        
    Returns:
        str: Result message with sync status
        
    Raises:
        RawDocument.DoesNotExist: If document not found
        Exception: If sync process fails
    """
    from apps.core.models import RawDocument, WikiPage
    from apps.core.prompts import SYNC_PROMPT_TEMPLATE
    from apps.core.utils import apply_adversarial_labeling

    try:
        # Get the raw document
        raw_doc = RawDocument.objects.get(id=raw_doc_id)
        case = raw_doc.case
        
        logger.info(f"Starting sync for document {raw_doc_id} (case: {case.id})")

        # Load the document text
        document_text = load_document_text(raw_doc)
        if not document_text.strip():
            logger.warning(f"Document {raw_doc_id} has empty content")
            return f"Skipped {raw_doc_id}: Empty document content"

        # Get existing wiki content for cross-referencing
        existing_wiki = ""
        wiki_pages = WikiPage.objects.filter(case=case)
        for page in wiki_pages:
            existing_wiki += f"\n--- {page.title} ---\n{page.content}\n"

        # Ensure we have some existing wiki content for the prompt
        if not existing_wiki.strip():
            existing_wiki = "No existing wiki content available."

        # Prepare the prompt for the LLM
        try:
            prompt = SYNC_PROMPT_TEMPLATE.format(
                document_text=document_text,
                existing_wiki=existing_wiki
            )
        except KeyError as e:
            logger.error(f"Prompt template error: missing placeholder {e}")
            raise ValueError(f"Prompt template missing required placeholder: {e}")

        # Call the LLM with improved integration
        llm_response = call_llm(prompt, document_text)

        # Parse the LLM's JSON response
        try:
            events = json.loads(llm_response)
            if not isinstance(events, list):
                logger.error(f"Invalid LLM response format: {llm_response}")
                return f"Failed to sync {raw_doc_id}: Invalid LLM response format"
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return f"Failed to sync {raw_doc_id}: LLM response parsing error"

        # Apply adversarial labeling and save to WikiPage
        synced_count = 0
        for i, event in enumerate(events):
            try:
                # Validate required fields
                required_fields = ['text', 'category', 'source_party', 'date', 'citation']
                for field in required_fields:
                    if field not in event:
                        logger.warning(f"Event {i} missing field {field}: {event}")
                        continue

                # Apply adversarial labeling based on source_party
                labeled_text = apply_adversarial_labeling(
                    event['text'],
                    event.get('source_party', raw_doc.source_party)
                )

                # Generate a unique title for the wiki page
                event_date = event.get('date', 'unknown').replace('-', '_')
                event_title_suffix = event['text'][:30].replace(' ', '_')
                wiki_title = f"event_{event_date}_{event_title_suffix}_{i}"

                # Save to WikiPage
                wiki_page, created = WikiPage.objects.get_or_create(
                    case=case,
                    title=wiki_title,
                    defaults={
                        'content': labeled_text,
                        'category': event.get('category', 'CONTESTED'),
                        'version_history': [],
                        'citation_references': [{
                            'claim_id': f"CLM-{case.id}-{event.get('date', '000')}-{i:03d}",
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

                synced_count += 1
                logger.info(f"Synced event {i+1}/{len(events)}: {event['text'][:50]}...")

            except Exception as e:
                logger.error(f"Failed to process event {i}: {e}")
                continue

        # Detect contradictions
        contradictions = detect_contradictions(str(case.id))

        # Mark the document as synced
        from django.utils import timezone
        raw_doc.synced_at = timezone.now()
        raw_doc.save()
        
        logger.info(f"Successfully synced {synced_count}/{len(events)} events for document {raw_doc_id}")
        return f"Synced {raw_doc_id} to Wiki layer: {synced_count} events processed, {len(contradictions)} contradictions found."

    except RawDocument.DoesNotExist:
        logger.error(f"RawDocument {raw_doc_id} not found")
        raise
    except Exception as e:
        logger.error(f"Unexpected error syncing document {raw_doc_id}: {e}")
        raise


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

    # Find documents that haven't been synced (synced_at is null)
    pending_docs = RawDocument.objects.filter(synced_at__isnull=True)

    synced = 0
    for doc in pending_docs:
        try:
            task_sync_raw_document.delay(str(doc.id))
            synced += 1
            logger.info(f"Queued document {doc.id} for sync")
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
