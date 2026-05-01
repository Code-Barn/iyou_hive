"""
Centralized document processing utilities for Hiver.
This module contains the core logic for converting PDFs to Markdown.
"""
from pathlib import Path
from legal_utils import (
    is_readable, extract_form_fields, extract_text_from_pdf,
    clean_legal_artifacts
)

def build_markdown_with_form(text, form_data):
    """Combine extracted text and form data into a single markdown string."""
    lines = []
    if text:
        # Clean text artifacts before adding
        text = clean_legal_artifacts(text)
        lines.append(text.strip())
    
    if form_data:
        lines.append("
## Form Fields
")
        # Sort keys for consistency
        for key in sorted(form_data.keys()):
            value = form_data[key]
            lines.append(f"- **{key}**: {value}")
            
    return "
".join(lines)


def convert_pdf_to_markdown(pdf_path):
    """
    Convert a single PDF file to markdown with tiered extraction.
    This is the centralized function for all PDF to Markdown conversions.
    """
    pdf_path = Path(pdf_path)
    
    try:
        # 1. Extract text using shared tiered strategy
        text = extract_text_from_pdf(pdf_path)
        
        # 2. Extract form fields
        form_data = extract_form_fields(str(pdf_path))
        
        # 3. Combine and save
        combined = build_markdown_with_form(text, form_data)
        
        md_path = pdf_path.with_suffix(".md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(combined)
            
        return md_path
    except Exception as e:
        # We will let the calling function handle the exception
        raise e
