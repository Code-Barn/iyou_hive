"""
Utility functions for the Hiver application.
"""

from typing import Dict, Any, List


def apply_adversarial_labeling(llm_response: str, source_party: str) -> str:
    """
    Modifies the LLM's response to include adversarial disclaimers if the source is 'OPPOSING'.

    Args:
        llm_response: The raw response from the LLM.
        source_party: The party that provided the source (e.g., 'CLIENT', 'OPPOSING').

    Returns:
        str: The labeled response.
    """
    if source_party == 'OPPOSING':
        # Prepend adversarial disclaimer
        return f"The opposing party alleges: {llm_response}"
    elif source_party == 'CLIENT':
        # No disclaimer needed for client sources
        return llm_response
    else:
        # Neutral sources (e.g., court filings)
        return f"According to the document: {llm_response}"


def categorize_event(text: str, source_party: str, existing_verified_events: list = None) -> Dict[str, Any]:
    """
    Categorize an event as 'VERIFIED' or 'CONTESTED'.

    Args:
        text: The event text.
        source_party: Who provided the information.
        existing_verified_events: List of verified events for cross-referencing.

    Returns:
        dict: Event with category and metadata.
    """
    if existing_verified_events is None:
        existing_verified_events = []

    # Simple heuristic: CLIENT sources tend to be verified, OPPOSING are contested
    if source_party == 'OPPOSING':
        category = 'CONTESTED'
    elif source_party == 'CLIENT':
        category = 'VERIFIED'
    else:
        # Neutral sources - check against verified events
        category = 'VERIFIED'  # Default for court filings

    return {
        'text': text,
        'category': category,
        'source_party': source_party,
    }


def check_for_contradictions(new_event: Dict[str, Any], existing_events: list) -> list:
    """
    Check if a new event contradicts existing events.

    Args:
        new_event: The new event to check.
        existing_events: List of existing events.

    Returns:
        list: Contradictions found.
    """
    contradictions = []

    new_text = new_event.get('text', '').lower()

    for existing in existing_events:
        existing_text = existing.get('text', '').lower()

        # Simple contradiction detection: look for same subject with different facts
        # This is a placeholder - in production, use NLP/LLM for better detection
        if are_contradictory(new_text, existing_text):
            contradictions.append({
                'contradiction': f"Conflicting claims about similar subject",
                'event1': new_event.get('text'),
                'event2': existing.get('text'),
                'source1': new_event.get('source_party'),
                'source2': existing.get('source_party'),
                'status': 'Unresolved'
            })

    return contradictions


def are_contradictory(text1: str, text2: str) -> bool:
    """
    Simple check if two texts are contradictory.
    Placeholder for more sophisticated NLP logic.
    """
    # Check for date contradictions
    import re
    dates1 = re.findall(r'\d{4}-\d{2}-\d{2}', text1)
    dates2 = re.findall(r'\d{4}-\d{2}-\d{2}', text2)

    if dates1 and dates2 and dates1[0] != dates2[0]:
        if 'signed' in text1 and 'signed' in text2:
            return True

    # Check for presence/absence contradictions
    presence_words = ['present', 'attended', 'was there']
    absence_words = ['absent', 'did not attend', 'was not there']

    for pw in presence_words:
        if pw in text1:
            for aw in absence_words:
                if aw in text2:
                    # Check if they're talking about the same subject
                    if have_similar_subject(text1, text2):
                        return True

    return False


def have_similar_subject(text1: str, text2: str) -> bool:
    """
    Check if two texts refer to the same subject.
    Simple word overlap check.
    """
    words1 = set(text1.split())
    words2 = set(text2.split())

    # Remove common words
    stop_words = {'the', 'a', 'an', 'is', 'was', 'were', 'on', 'at', 'in'}
    words1 -= stop_words
    words2 -= stop_words

    # Check for overlap
    overlap = words1 & words2
    return len(overlap) > 2  # Arbitrary threshold


def validate_adversarial_disclaimers(response: str, cited_sources: List[str]) -> bool:
    """
    Validates that adversarial claims are properly disclaimed.

    Args:
        response: The LLM's response text.
        cited_sources: List of source_party values for all cited documents.

    Returns:
        bool: True if all adversarial claims are properly disclaimed, False otherwise.
    """
    # Check if any cited source is "OPPOSING"
    has_opposing = any(source == "OPPOSING" for source in cited_sources)

    if not has_opposing:
        return True  # No adversarial sources, no disclaimers needed

    # Define adversarial disclaimers to look for
    disclaimers = [
        "The opposing party alleges",
        "According to the contested filing",
        "The [Party] claims",
        "alleges that",
        "claims that",
    ]

    # Check if any disclaimer is present in the response
    for disclaimer in disclaimers:
        if disclaimer.lower() in response.lower():
            return True

    # If no disclaimer found, log a warning (or raise an error in strict mode)
    print("Warning: Adversarial claim cited without proper disclaimer.")
    return False
