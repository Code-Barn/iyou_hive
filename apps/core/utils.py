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
