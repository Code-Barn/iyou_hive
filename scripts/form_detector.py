"""
Form Type Detection and Section Splitting for Illinois Legal Forms
Identifies what type of form is being submitted and handles combined PDFs.
"""

from pathlib import Path
import re


# Form type patterns (keywords that identify each form type)
FORM_TYPES = {
    "MOTION": {
        "keywords": ["MOTION", "I am asking the judge to:"],
        "section_marker": "I am asking the judge to:",
        "additional_page_marker": "Additional explanation continued from my Motion:",
        "output_suffix": "_motion",
        "blank_form": "MOT_Motion.md",
    },
    "ADDITIONAL_PAGE": {
        "keywords": ["ADDITIONAL PAGE FOR MOTION", "Additional explanation continued from my Motion:"],
        "section_marker": "Additional explanation continued from my Motion:",
        "is_additional": True,
        "output_suffix": "_additional",
        "blank_form": "MOT_Additional_Motion.md",
    },
    "PROOF_DELIVERY": {
        "keywords": ["PROOF OF DELIVERY", "I am sending this Proof of Delivery"],
        "section_marker": "I am sending this Proof of Delivery",
        "output_suffix": "_proof",
        "blank_form": None,
    },
}


def detect_form_type(text: str) -> str:
    """
    Detect what type of form this is.
    Returns: "MOTION", "ADDITIONAL_PAGE", "PROOF_DELIVERY", etc.
    """
    text_upper = text.upper()
    
    # Check each form type
    for form_type, config in FORM_TYPES.items():
        keywords = config.get("keywords", [])
        for keyword in keywords:
            if keyword.upper() in text_upper:
                return form_type
    
    return "UNKNOWN"


def split_combined_form(text: str, state_code: str = "IL") -> list:
    """
    Split a combined PDF text into separate form sections.
    Returns: [{"form_type": str, "text": str}, ...]
    """
    sections = []
    
    # Check if Additional Page is present
    has_additional = "ADDITIONAL PAGE FOR MOTION" in text.upper() or \
                     "Additional explanation continued from my Motion:" in text
    
    if has_additional:
        # Split into Motion section and Additional Page section
        additional_marker = "ADDITIONAL PAGE FOR MOTION"
        additional_idx = text.upper().find(additional_marker)
        
        if additional_idx > 0:
            # Motion section (before Additional Page)
            motion_text = text[:additional_idx].strip()
            sections.append({
                "form_type": "MOTION",
                "text": motion_text
            })
            
            # Additional Page section (from Additional Page onwards)
            additional_text = text[additional_idx:].strip()
            sections.append({
                "form_type": "ADDITIONAL_PAGE",
                "text": additional_text
            })
        else:
            # Couldn't find exact split point, treat as one document
            form_type = detect_form_type(text)
            sections.append({
                "form_type": form_type,
                "text": text
            })
    else:
        # Single form type
        form_type = detect_form_type(text)
        sections.append({
            "form_type": form_type,
            "text": text
        })
    
    return sections


def get_blank_form_path(form_type: str, state_code: str = "IL") -> str:
    """Get the blank form path for a specific form type."""
    config = FORM_TYPES.get(form_type, {})
    blank_form = config.get("blank_form")
    if blank_form:
        return f"blank_forms/US/{state_code}/{blank_form}"
    return None


def load_blank_form_for_type(form_type: str, state_code: str = "IL") -> set:
    """
    Load blank form text for a specific form type.
    Returns set of normalized lines.
    """
    blank_lines = set()
    blank_form_path = get_blank_form_path(form_type, state_code)
    
    if blank_form_path:
        md_path = Path(blank_form_path).with_suffix(".md")
        if md_path.exists():
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                for line in text.split('\n'):
                    normalized = re.sub(r'\s+', ' ', line.strip().lower())
                    if len(normalized) > 3:
                        blank_lines.add(normalized)
            except Exception:
                pass
    
    return blank_lines


def extract_user_input_from_section(section_text: str, form_type: str, state_code: str = "IL") -> str:
    """
    Extract ONLY user narrative input from a form section.
    Step 1: Find narrative start marker ("I am asking the judge to:" or "Additional explanation continued from my Motion:")
    Step 2: Extract only text from that point onwards
    Step 3: Remove form labels by comparing to blank form
    """
    # Find narrative start based on form type
    narrative_markers = {
        "MOTION": ["I am asking the judge to:"],
        "ADDITIONAL_PAGE": ["Additional explanation continued from my Motion:"],
    }
    
    narrative_start = -1
    markers = narrative_markers.get(form_type, [])
    
    for marker in markers:
        idx = section_text.lower().find(marker.lower())
        if idx >= 0:
            # Find the start of this line
            line_start = section_text.rfind('\n', 0, idx) + 1
            narrative_start = line_start if line_start >= 0 else idx
            break
    
    # If no marker found, return empty (this section has no narrative)
    if narrative_start < 0:
        print(f"  -> Warning: No narrative marker found for {form_type}")
        return ""
    
    # Extract only the narrative portion (from marker onwards)
    narrative_text = section_text[narrative_start:].strip()
    
    # Now remove form labels from the narrative by comparing to blank form
    blank_lines = load_blank_form_for_type(form_type, state_code)
    
    if not blank_lines:
        return narrative_text
    
    lines = narrative_text.split('\n')
    user_lines = []
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        
        line_normalized = re.sub(r'\s+', ' ', line_clean.lower())
        
        # Check if line is a form label
        is_form_label = False
        for blank_line in blank_lines:
            # Exact match
            if line_normalized == blank_line:
                is_form_label = True
                break
            # Line contains blank form text (user added after label)
            if len(blank_line) > 10 and blank_line in line_normalized:
                # Extract only the part after the blank form text
                idx = line_normalized.find(blank_line)
                if idx >= 0:
                    remaining = line_clean[idx + len(blank_line):].strip()
                    if remaining and len(remaining) > 2:
                        user_lines.append(remaining)
                is_form_label = True
                break
            # Check word overlap (>80% = form line)
            words_line = set(line_normalized.split())
            words_blank = set(blank_line.split())
            if words_line and words_blank:
                overlap = len(words_line & words_blank)
                similarity = overlap / max(len(words_line), 1)
                if similarity > 0.8:
                    is_form_label = True
                    break
        
        if not is_form_label:
            user_lines.append(line_clean)
    
    result = '\n'.join(user_lines)
    print(f"  -> Extracted {len(user_lines)} narrative lines from {form_type} section")
    return result


if __name__ == "__main__":
    # Test with sample text containing both forms
    sample = """MOTION
IN THE STATE OF ILLINOIS, CIRCUIT COURT
COUNTY: DeKalb
I am asking the judge to:
I am asking the judge to grant me permission to relocate.

ADDITIONAL PAGE FOR MOTION
Additional explanation continued from my Motion:
This is additional text that didn't fit on the first page.
"""
    
    sections = split_combined_form(sample)
    print(f"Detected {len(sections)} sections:")
    for i, sec in enumerate(sections, 1):
        print(f"  Section {i}: {sec['form_type']} ({len(sec['text'])} chars)")
