#!/usr/bin/env -S uv run --script

# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pdfplumber",
#     "python-dotenv",
#     "PyMuPDF",
#     "PaddleOCR",
# ]
# ///

"""
Batch convert blank form PDFs to Markdown files.
Uses the same techniques as sync_legal_docs.py for consistency.

Run from project root: uv run scripts/batch_convert_blank_forms.py
"""

import os
import re
import subprocess
from pathlib import Path
import pdfplumber
from dotenv import load_dotenv
from markitdown import MarkItDown
import fitz
from paddleocr import PaddleOCR

load_dotenv()

def is_readable(text):
    cleaned = re.sub(r'[☑☒✓Xx_\n\r\t]+', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    if len(cleaned.strip()) < 50:
        return False
    words = re.findall(r'\b[a-zA-Z]{3,}\b', cleaned.lower())
    if len(words) < 25:
        return False
    return True

_local_ocr = None
def get_local_ocr():
    global _local_ocr
    if _local_ocr is None:
        _local_ocr = PaddleOCR(lang='en')
    return _local_ocr

def ocr_pdf_images(pdf_path):
    text_parts = []
    try:
        ocr = get_local_ocr()
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_path = f"/tmp/ocr_page_{page_num}.png"
            pix.save(img_path)
            
            result = ocr.ocr(img_path)
            if result and result[0]:
                r = result[0]
                texts = r.get('rec_texts', [])
                text_parts.extend(texts)
        doc.close()
    except Exception as e:
        print(f"  -> Local OCR error: {e}")
    return "\n".join(text_parts)

def convert_pdf_to_md(pdf_path, md_path=None):
    """Convert a single PDF to Markdown using sync_legal_docs techniques."""
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        return False
    
    if md_path is None:
        md_path = pdf_path.with_suffix(".md")
    
    print(f"Converting: {pdf_path} -> {md_path}...")
    
    text = ""
    form_data = {}
    
    try:
        # Use pdftotext - best text extraction
        try:
            result = subprocess.run(
                ['pdftotext', '-layout', str(pdf_path), '-'],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                text = result.stdout
        except Exception:
            pass
        
        # Fallback to pdfplumber
        if not text:
            try:
                with pdfplumber.open(str(pdf_path)) as pdf:
                    text_parts = [p.extract_text_simple() for p in pdf.pages]
                    text = "\n\n---\n\n".join(text_parts)
            except Exception:
                pass
        
        # Try form extraction (for blank forms, this captures field names)
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page in pdf.pages:
                    fields = page.get_form_fields()
                    if fields:
                        for field in fields:
                            key = field.get("name", "")
                            value = field.get("export_value", "")
                            if value:
                                form_data[key] = value
        except Exception:
            pass
        
        combined = build_markdown_with_form(text, form_data)
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(combined)
        
        if form_data:
            print(f"  -> Extracted: {len(form_data)} fields")
        
        print(f"  -> Saved to {md_path}")
        return True
        
    except Exception as e:
        print(f"  -> Error: {e}")
        return False

def build_markdown_with_form(text, form_data):
    lines = []
    if text:
        lines.append(text.strip())
    if form_data:
        lines.append("\n## Form Fields\n")
        for key, value in form_data.items():
            lines.append(f"- **{key}**: {value}")
    return "\n".join(lines)

def main():
    base_dir = Path("blank_forms/US")
    
    if not base_dir.exists():
        print(f"Error: {base_dir} not found")
        return
    
    converted = 0
    skipped = 0
    failed = 0
    
    for state_dir in base_dir.iterdir():
        if not state_dir.is_dir():
            continue
        
        print(f"\nProcessing state: {state_dir.name}")
        
        for pdf_path in state_dir.glob("*.pdf"):
            md_path = pdf_path.with_suffix(".md")
            
            # Skip if MD exists and is newer
            if md_path.exists():
                pdf_mtime = pdf_path.stat().st_mtime
                md_mtime = md_path.stat().st_mtime
                if md_mtime > pdf_mtime:
                    print(f"  -> Skipping {pdf_path.name} (MD up-to-date)")
                    skipped += 1
                    continue
            
            success = convert_pdf_to_md(pdf_path, md_path)
            if success:
                converted += 1
            else:
                failed += 1
    
    print(f"\n--- Batch Convert Complete ---")
    print(f"Converted: {converted}")
    print(f"Skipped (up-to-date): {skipped}")
    print(f"Failed: {failed}")

if __name__ == "__main__":
    main()
