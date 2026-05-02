"""
Utility functions for Hiver core app.
Includes legal claim processing helpers.
"""


def filter_claims(data, excluded_ids=None):
    """
    Filter claims by excluding specific IDs.
    
    Args:
        data: Dict with 'metadata', 'procedural_facts', 'claims' keys
        excluded_ids: List of claim IDs to exclude (or None for no filtering)
        
    Returns:
        Dict with filtered claims (metadata and procedural_facts preserved)
    """
    if excluded_ids is None:
        excluded_ids = set()
    else:
        excluded_ids = set(excluded_ids)
    
    return {
        "metadata": data.get("metadata", {}),
        "procedural_facts": data.get("procedural_facts", []),
        "claims": [
            c for c in data.get("claims", [])
            if c.get("id") not in excluded_ids
        ]
    }


def apply_adversarial_labeling(text, source_party):
    """
    Apply adversarial labeling to text based on the source party.
    
    This function implements the adversarial handling logic to ensure
    that claims from opposing parties are properly labeled as contested.
    
    Args:
        text (str): The text to label
        source_party (str): The source party (CLIENT, OPPOSING, NEUTRAL)
        
    Returns:
        str: The labeled text with appropriate disclaimers
    """
    if not text:
        return text
        
    source_party = source_party.upper() if source_party else "NEUTRAL"
    
    if source_party == "OPPOSING":
        # Apply adversarial disclaimer for opposing party claims
        return f"The opposing party alleges: {text}"
    elif source_party == "CLIENT":
        # Client claims are presented as-is
        return text
    else:
        # Neutral sources get a neutral disclaimer
        return f"According to the document: {text}"


def parse_response_sheet_json(json_path):
    """
    Load and validate a response sheet JSON file.
    
    Args:
        json_path: Path to the .response_sheet.json file
        
    Returns:
        Dict with metadata, procedural_facts, claims
    """
    import json
    from pathlib import Path
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Ensure required keys exist
    return {
        "metadata": data.get("metadata", {}),
        "procedural_facts": data.get("procedural_facts", []),
        "claims": data.get("claims", []),
        "source_pdf": data.get("source_pdf", ""),
        "case_number": data.get("case_number", ""),
        "motion_title": data.get("motion_title", ""),
        "state_code": data.get("state_code", "IL"),
    }