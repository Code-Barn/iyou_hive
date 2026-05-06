"""
Centralized document processing utilities for Hiver.
This module contains the core logic for converting PDFs to Markdown.
"""
import os
import re
import subprocess
from pathlib import Path
import pdfplumber
from dotenv import load_dotenv
load_dotenv()

from markitdown import MarkItDown
import fitz

# Add scripts directory to Python path for imports
import sys
import os
scripts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

# It's better to handle the absence of paddleocr gracefully
try:
    from paddleocr import PaddleOCR
    _local_ocr = None
    def get_local_ocr():
        global _local_ocr
        if _local_ocr is None:
            _local_ocr = PaddleOCR(lang='en')
        return _local_ocr
except ImportError:
    _local_ocr = None
    def get_local_ocr():
        return None

from legal_utils import (
    is_readable, extract_form_fields, extract_text_from_pdf
)

def ocr_pdf_images(pdf_path):
    text_parts = []
    ocr = get_local_ocr()
    if not ocr:
        print("  -> PaddleOCR not available. Skipping local OCR.")
        return ""

    try:
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

def build_markdown_with_form(text, form_data):
    lines = []
    if text:
        lines.append(text.strip())
    if form_data:
        lines.append("\n## Form Fields\n")
        for key, value in form_data.items():
            lines.append(f"- **{key}**: {value}")
    return "\n".join(lines)

def get_llm_converter():
    import google.genai as genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        client = genai.Client(api_key=api_key)
        return client
    except Exception as e:
        print(f"Warning: Could not initialize Gemini client: {e}")
        return None

def convert_pdf_to_markdown(pdf_path):
    pdf_path = Path(pdf_path)
    md_path = pdf_path.with_suffix(".md")

    form_data = {}
    text = ""
    llm_client = get_llm_converter()

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
                    text = "\n\n--- Page Break ---\n\n".join(text_parts)
            except Exception:
                pass

        # Try form extraction
        try:
            form_data = extract_form_fields(str(pdf_path))
        except Exception:
            pass

        # Try OCR for empty or short text
        if len(text.strip()) < 300:
            if llm_client:
                try:
                    print(f"  -> Using Vision API...")
                    uploaded = llm_client.files.upload(file=str(pdf_path))
                    result = llm_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[uploaded, "Extract all text from this document."]
                    )
                    text = result.text if hasattr(result, 'text') else str(result)
                except Exception as e:
                    print(f"  -> Vision failed: {e}, trying local OCR...")
                    text = ocr_pdf_images(str(pdf_path))
            else:
                print(f"  -> Using local PaddleOCR...")
                text = ocr_pdf_images(str(pdf_path))

        if len(text.strip()) < 300:
            text = text + "\n\n[Note: This PDF may contain images. OCR processing may be incomplete.]"

        combined = build_markdown_with_form(text, form_data)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(combined)

        return md_path
    except Exception as e:
        raise e
