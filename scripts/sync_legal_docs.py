#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pdfplumber",
#     "python-dotenv",
#     "PyMuPDF",
#     "markitdown",
#     "google-genai>=1.74.0",
#     "django",
# ]
# ///

"""
Sync Legal Docs: Converts PDFs in the repository to Markdown.
This script is a wrapper around the centralized document processing logic.
"""

import os
import sys
import django
from pathlib import Path

# Initialize Django
sys.path.append(Path(__file__).resolve().parent.parent.as_posix())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.document_processing import convert_pdf_to_markdown

def sync_pdfs_to_markdown(single_file=None):
    """Main sync loop: finds PDFs and converts them if MD is missing or older."""
    root_dir = Path(".")
    converted_count = 0
    skipped_count = 0
    failed_count = 0

    if single_file:
        pdf_path = Path(single_file)
        if not pdf_path.exists():
            print(f"Error: File not found: {single_file}")
            return
        
        print(f"  -> Processing: {pdf_path.name}")
        try:
            convert_pdf_to_markdown(pdf_path)
            converted_count = 1
            print(f"     [Success] Converted {pdf_path.name}")
        except Exception as e:
            failed_count = 1
            print(f"     [Failed] Error converting {pdf_path.name}: {e}")

    else:
        print(f"--- Scanning repository for PDFs ---")
        pdf_files = list(root_dir.rglob("*.pdf"))
        for pdf_path in pdf_files:
            if ".venv" in str(pdf_path) or ".git" in str(pdf_path) or "media/archive" in str(pdf_path):
                continue
                
            md_path = pdf_path.with_suffix(".md")

            # Check if sync is needed
            if md_path.exists() and os.path.getmtime(md_path) > os.path.getmtime(pdf_path):
                skipped_count += 1
                continue

            print(f"  -> Processing: {pdf_path.name}")
            try:
                convert_pdf_to_markdown(pdf_path)
                converted_count += 1
                print(f"     [Success] Converted {pdf_path.name}")
            except Exception as e:
                failed_count += 1
                print(f"     [Failed] Error converting {pdf_path.name}: {e}")

    print(f"\n--- Sync Complete ---")
    print(f"Converted: {converted_count}")
    if not single_file:
        print(f"Up-to-date: {skipped_count}")
    if failed_count > 0:
        print(f"Failed: {failed_count}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sync_pdfs_to_markdown(single_file=sys.argv[1])
    else:
        sync_pdfs_to_markdown()
