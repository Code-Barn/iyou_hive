#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pdfplumber",
#     "python-dotenv",
#     "PyMuPDF",
#     "markitdown",
#     "google-genai>=1.74.0",
# ]
# ///

"""
Sync Legal Docs: Converts PDFs in the repository to Markdown.
Preserves form fields and uses OCR fallback for scanned documents.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from markitdown import MarkItDown

# Load .env from project root
load_dotenv()

# Import shared utilities
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
        lines.append("\n## Form Fields\n")
        # Sort keys for consistency
        for key in sorted(form_data.keys()):
            value = form_data[key]
            lines.append(f"- **{key}**: {value}")
            
    return "\n".join(lines)

def get_llm_converter():
    """Initialize Gemini client if API key is present."""
    import google.genai as genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def convert_single_pdf(pdf_path, llm_client=None):
    """Convert a single PDF file to markdown with tiered extraction."""
    pdf_path = Path(pdf_path)
    print(f"  -> Processing: {pdf_path.name}")
    
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
            
        has_form = bool(form_data)
        if has_form:
            print(f"     [Fields] Extracted {len(form_data)} fields")
        
        # Determine if OCR was likely used (if text wasn't readable initially)
        # Note: extract_text_from_pdf handles the logic internally
        ocr_used = not is_readable(text) if text else False
        
        return True, has_form, ocr_used
    except Exception as e:
        print(f"  -> Error converting {pdf_path.name}: {e}")
        return False, False, False

def sync_pdfs_to_markdown(single_file=None):
    """Main sync loop: finds PDFs and converts them if MD is missing or older."""
    llm_client = None
    if os.environ.get("GEMINI_API_KEY"):
        try:
            llm_client = get_llm_converter()
            print("--- Vision OCR mode available ---")
        except Exception as e:
            print(f"Warning: Could not initialize Gemini client: {e}")

    root_dir = Path(".")
    converted_count = 0
    skipped_count = 0
    ocr_count = 0
    form_count = 0

    if single_file:
        pdf_path = Path(single_file)
        if not pdf_path.exists():
            print(f"Error: File not found: {single_file}")
            return

        success, has_form, ocr_used = convert_single_pdf(pdf_path, llm_client)
        if success:
            converted_count = 1
            if has_form: form_count = 1
            if ocr_used: ocr_count = 1
    else:
        print(f"--- Scanning repository for PDFs ---")
        # Walk through directory, excluding common folders
        for pdf_path in root_dir.rglob("*.pdf"):
            if ".venv" in str(pdf_path) or ".git" in str(pdf_path):
                continue
                
            md_path = pdf_path.with_suffix(".md")

            # Check if sync is needed
            if md_path.exists():
                if os.path.getmtime(md_path) > os.path.getmtime(pdf_path):
                    skipped_count += 1
                    continue

            success, has_form, ocr_used = convert_single_pdf(pdf_path, llm_client)
            if success:
                converted_count += 1
                if has_form: form_count += 1
                if ocr_used: ocr_count += 1

    print(f"\n--- Sync Complete ---")
    print(f"Converted: {converted_count}")
    if not single_file:
        print(f"Up-to-date: {skipped_count}")
    print(f"With form fields: {form_count}")
    if ocr_count > 0:
        print(f"OCR/Vision used: {ocr_count}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sync_pdfs_to_markdown(single_file=sys.argv[1])
    else:
        sync_pdfs_to_markdown()
