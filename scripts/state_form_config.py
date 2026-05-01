"""
State Form Configuration for All 50 US States
Maps state codes to their blank form PDFs and title extraction patterns.
"""

# State form configuration: {state_code: {"form_path": str, "title_patterns": [regex]}}
STATE_FORMS = {
    "IL": {
        "form_path": "blank_forms/US/IL/MOT_Motion.pdf",
        "additional_form_path": "blank_forms/US/IL/MOT_Additional_Motion.pdf",
        "title_patterns": [
            r"MOTION TO [A-Z ]+",
            r"NOTICE OF [A-Z ]+",
            r"PETITION FOR [A-Z ]+",
        ],
        "form_fields": [
            "txtMotion",
            "txtAdditionalExplanation",
            "txtTitle",
        ]
    },
    "CA": {
        "form_path": "blank_forms/US/CA/MC-030.pdf",  # Civil Case Cover Sheet
        "title_patterns": [
            r"NOTICE OF [A-Z ]+",
            r"MOTION FOR [A-Z ]+",
        ],
        "form_fields": [
            "MC-030",
            "form_description",
        ]
    },
    # Add more states as blank forms are collected
    # "NY": {"form_path": "blank_forms/US/NY/...pdf", ...},
    # "TX": {"form_path": "blank_forms/US/TX/...pdf", ...},
}

def get_state_config(state_code):
    """Get form configuration for a state."""
    return STATE_FORMS.get(state_code.upper(), STATE_FORMS.get("IL"))  # Default to IL

def get_blank_form_path(state_code):
    """Get the blank form PDF path for a state."""
    config = get_state_config(state_code)
    if config:
        return config.get("form_path")
    return None

def get_title_patterns(state_code):
    """Get title extraction patterns for a state."""
    config = get_state_config(state_code)
    if config:
        return config.get("title_patterns", [])
    return []
