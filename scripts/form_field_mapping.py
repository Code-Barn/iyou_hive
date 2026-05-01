"""
Form Field Mapping System for Illinois Legal Forms
Classifies form fields into metadata, narrative, labels, and checkboxes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class FormFieldType(Enum):
    METADATA = "metadata"  # Header info: case number, party names, county
    NARRATIVE = "narrative"  # User-written claims/arguments
    LABEL = "label"  # Form instructions/labels (e.g., "I am asking the judge to:")
    CHECKBOX = "checkbox"  # Checkbox fields (irrelevant for filled forms)
    ADDITIONAL = "additional"  # Additional page narrative continuation


@dataclass
class FormField:
    field_type: FormFieldType
    text: str
    page: int = 1
    bbox: Optional[tuple] = None  # (x1, y1, x2, y2) if from PDF


# Predefined field mappings for Illinois form types
ILLINOIS_FORM_FIELDS = {
    "MOTION": [
        # Metadata fields
        FormField(FormFieldType.METADATA, "IN THE STATE OF ILLINOIS, CIRCUIT COURT"),
        FormField(FormFieldType.METADATA, "COUNTY:"),
        FormField(FormFieldType.METADATA, "PLAINTIFF/PETITIONER OR IN RE:"),
        FormField(FormFieldType.METADATA, "DEFENDANTS/RESPONDENTS:"),
        FormField(FormFieldType.METADATA, "Case Number"),
        # Labels
        FormField(FormFieldType.LABEL, "1. MOTION TITLE"),
        FormField(FormFieldType.LABEL, "Explain in a few words what you are asking the judge to do."),
        FormField(FormFieldType.LABEL, "Motion to:"),
        FormField(FormFieldType.LABEL, "2. PERSON FILING THE MOTION"),
        FormField(FormFieldType.LABEL, "Check one box. The Plaintiff/Petitioner is the person who started the case."),
        FormField(FormFieldType.LABEL, "I am filing the Motion. I am the:"),
        FormField(FormFieldType.LABEL, " Plaintiff/Petitioner"),
        FormField(FormFieldType.LABEL, " Defendant/Respondent"),
        FormField(FormFieldType.LABEL, "3. MOTION"),
        FormField(FormFieldType.LABEL, "Explain what you are asking the judge to do and the reasons why the judge should agree with you."),
        FormField(FormFieldType.LABEL, "I am asking the judge to:"),
        FormField(FormFieldType.LABEL, " I need more room to explain, and I have filled out and attached an Additional Page for Motion form."),
        # Narrative field (user input)
        FormField(FormFieldType.NARRATIVE, "I am asking the judge to:"),
        # Signature section labels
        FormField(FormFieldType.LABEL, "SIGN"),
        FormField(FormFieldType.LABEL, "Under Illinois Supreme Court Rule 137, my signature means that:"),
        FormField(FormFieldType.LABEL, "Signature /s/"),
        FormField(FormFieldType.LABEL, "Print Name"),
        FormField(FormFieldType.LABEL, "I am completing this form for myself"),
        FormField(FormFieldType.LABEL, "Phone Number"),
        FormField(FormFieldType.LABEL, "Email (if you have one)"),
        FormField(FormFieldType.LABEL, "Your Address"),
        FormField(FormFieldType.LABEL, "Be sure to check your email every day"),
        FormField(FormFieldType.LABEL, "I am a lawyer completing this form on behalf of a client"),
        FormField(FormFieldType.LABEL, "Lawyer Name"),
        FormField(FormFieldType.LABEL, "Attorney Number"),
        FormField(FormFieldType.LABEL, "Lawyer Phone Number"),
        FormField(FormFieldType.LABEL, "Law Firm"),
        FormField(FormFieldType.LABEL, "Lawyer Email"),
        FormField(FormFieldType.LABEL, "Address"),
        # Proof of Delivery labels
        FormField(FormFieldType.LABEL, "PROOF (EXPLANATION) OF DELIVERY"),
        FormField(FormFieldType.LABEL, "This tells the judge how and when you will send your documents to the other people in the case under Rule 11."),
        FormField(FormFieldType.LABEL, "A. I am sending this Proof of Delivery and the following court documents:"),
        FormField(FormFieldType.LABEL, "Name of Documents"),
        FormField(FormFieldType.LABEL, "To:"),
        FormField(FormFieldType.LABEL, "Full Name or Law Firm Name"),
        FormField(FormFieldType.LABEL, "B. I am sending the documents:"),
        FormField(FormFieldType.LABEL, " By email to this email address:"),
        FormField(FormFieldType.LABEL, " Through an approved e-filing website (EFSP) to this email address:"),
        FormField(FormFieldType.LABEL, " I am sending the documents to this address:"),
        FormField(FormFieldType.LABEL, "C. The documents will be sent on: Date:"),
        FormField(FormFieldType.LABEL, " I am sending the document to more than 1 person"),
        FormField(FormFieldType.LABEL, "SIGN (Proof of Delivery)"),
        FormField(FormFieldType.LABEL, "Under 735 ILCS 5/1-109, my signature means that:"),
        FormField(FormFieldType.LABEL, "NEXT STEP FOR PERSON FILLING OUT THIS FORM:"),
        FormField(FormFieldType.LABEL, "NEXT STEP FOR PERSON RECEIVING THIS DOCUMENT:"),
    ],
    "ADDITIONAL_PAGE": [
        # Metadata fields
        FormField(FormFieldType.METADATA, "IN THE STATE OF ILLINOIS, CIRCUIT COURT"),
        FormField(FormFieldType.METADATA, "COUNTY:"),
        FormField(FormFieldType.METADATA, "PLAINTIFF/PETITIONER OR IN RE:"),
        FormField(FormFieldType.METADATA, "DEFENDANTS/RESPONDENTS:"),
        FormField(FormFieldType.METADATA, "Case Number"),
        # Labels
        FormField(FormFieldType.LABEL, "ADDITIONAL PAGE FOR MOTION"),
        FormField(FormFieldType.LABEL, "Use this only if you run out of space in section 3 on your Motion form."),
        FormField(FormFieldType.LABEL, "This document becomes an additional page of your Motion and should be filed with your Motion."),
        FormField(FormFieldType.LABEL, "Additional explanation continued from my Motion:"),
        # Narrative field (user input)
        FormField(FormFieldType.ADDITIONAL, "Additional explanation continued from my Motion:"),
        # Footer
        FormField(FormFieldType.LABEL, "This form is approved by the Illinois Supreme Court"),
        FormField(FormFieldType.LABEL, "File this form with your Motion."),
    ]
}


def get_form_fields(form_type: str) -> List[FormField]:
    """Return list of form fields for the given form type."""
    return ILLINOIS_FORM_FIELDS.get(form_type, [])


def classify_text(text: str, form_type: str) -> FormFieldType:
    """
    Classify a block of text into a form field type based on the form's structure.
    """
    text_clean = text.strip()
    if not text_clean:
        return FormFieldType.LABEL  # Empty lines are irrelevant
    
    # Check against predefined fields for the form type
    fields = get_form_fields(form_type)
    for field in fields:
        if field.text.lower() in text_clean.lower():
            return field.field_type
    
    # Heuristics for unknown text
    if any(keyword in text_clean.upper() for keyword in ["COUNTY:", "PLAINTIFF:", "DEFENDANT:", "CASE NUMBER"]):
        return FormFieldType.METADATA
    if len(text_clean) > 50 and not any(label.text.lower() in text_clean.lower() for label in fields if label.field_type == FormFieldType.LABEL):
        return FormFieldType.NARRATIVE
    return FormFieldType.LABEL


def extract_narrative_text(text: str, form_type: str) -> str:
    """
    Extract only narrative text (user input) from the form, excluding labels and metadata.
    """
    lines = text.split('\n')
    narrative_lines = []
    in_narrative = False
    narrative_markers = [f.text for f in get_form_fields(form_type) if f.field_type in (FormFieldType.NARRATIVE, FormFieldType.ADDITIONAL)]
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Check if we hit a narrative marker
        hit_marker = False
        for marker in narrative_markers:
            if marker.lower() in line_stripped.lower():
                hit_marker = True
                in_narrative = True
                # Extract text AFTER the marker (user input on same line)
                idx = line_stripped.lower().find(marker.lower())
                if idx >= 0:
                    remaining = line_stripped[idx + len(marker):].strip()
                    if remaining and not any(l.text.lower() in remaining.lower() for l in get_form_fields(form_type) if l.field_type == FormFieldType.LABEL):
                        narrative_lines.append(remaining)
                break
        
        if in_narrative and not hit_marker:
            # Check if we hit a new label (end of narrative)
            is_label = classify_text(line_stripped, form_type) == FormFieldType.LABEL
            if is_label and not any(marker.lower() in line_stripped.lower() for marker in narrative_markers):
                in_narrative = False
                continue
            if in_narrative:
                # Skip lines that are just labels repeated
                if not any(l.text.lower() in line_stripped.lower() for l in get_form_fields(form_type) if l.field_type == FormFieldType.LABEL):
                    narrative_lines.append(line_stripped)
    
    return '\n'.join(narrative_lines)
