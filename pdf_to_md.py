import os
import re
import subprocess
import sys
from pathlib import Path
import pdfplumber
from dotenv import load_dotenv
load_dotenv()

from markitdown import MarkItDown
import fitz
from paddleocr import PaddleOCR

def is_readable(text):
    cleaned = re.sub(r'[☑☒✓Xx_\n\r\t]+', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    if len(cleaned.strip()) < 50:
        return False
    words = re.findall(r'\b[a-zA-Z]{3,}\b', cleaned.lower())
    if len(words) < 25:
        return False
    return True

def extract_form_fields(pdf_path):
    form_data = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    fields = page.get_form_fields()
                    if fields:
                        for field in fields:
                            key = field.get("name", f"field_{page_num}")
                            value = field.get("export_value", "")
                            if value:
                                form_data[key] = value
                except Exception:
                    pass
    except Exception:
        pass
    return form_data

def extract_checkboxes(pdf_path):
    checkboxes = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                for obj in page.chars:
                    text = obj.get("text", "")
                    if text.strip().lower() in ["x", "✓"]:
                        try:
                            cx = float(obj.get("x0", 0))
                            cy = float(obj.get("y0", 0))
                        except:
                            continue
                        label_text = f"page {page_num+1}, row {int(cy/50)}"
                        checkboxes[f"checkbox_{len(checkboxes)}"] = {
                            "mark": text,
                            "label": label_text
                        }
    except Exception:
        pass
    return checkboxes

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

def build_markdown_with_form(text, form_data, checkboxes):
    lines = []
    if text:
        lines.append(text.strip())
    if form_data:
        lines.append("\n## Form Fields\n")
        for key, value in form_data.items():
            lines.append(f"- **{key}**: {value}")
    if checkboxes:
        lines.append("\n## Checkboxes Checked\n")
        for key, info in checkboxes.items():
            lines.append(f"- [{info['mark']}] {info.get('label', '')}")
    return "\n".join(lines)

def get_llm_converter():
    import google.genai as genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return client

def convert_single_pdf(pdf_path, llm_client):
    """Convert a single PDF file to markdown."""
    form_data = {}
    checkboxes = {}
    text = ""

    pdf_path = Path(pdf_path)

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

        # Try checkboxes
        try:
            checkboxes = extract_checkboxes(str(pdf_path))
        except Exception:
            pass

        # Try OCR for empty or short text (mixed PDFs need OCR)
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

        # Add note if text is short/empty (image-only or mixed PDFs)
        if len(text.strip()) < 300:
            text = text + "\n\n[Note: This PDF may contain images. Vision OCR quota exhausted. File needs manual OCR processing.]"

        combined = build_markdown_with_form(text, form_data, checkboxes)

        md_path = pdf_path.with_suffix(".md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(combined)

        if form_data or checkboxes:
            print(f"  -> Extracted: {len(form_data)} fields, {len(checkboxes)} checkboxes")

        return True, len(form_data) > 0 or len(checkboxes) > 0
    except Exception as e:
        print(f"  -> Error: {e}")
        return False, False

def sync_pdfs_to_markdown(single_file=None):
    basic_converter = MarkItDown()
    llm_client = None

    if os.environ.get("GEMINI_API_KEY"):
        try:
            llm_client = get_llm_converter()
            print("OCR mode enabled (GEMINI_API_KEY found)")
        except Exception as e:
            print(f"Warning: Could not initialize OCR mode: {e}")

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

        print(f"--- Converting single file: {pdf_path.absolute()} ---")
        success, has_form = convert_single_pdf(pdf_path, llm_client)
        if success:
            converted_count = 1
            if has_form:
                form_count = 1
    else:
        print(f"--- Scanning repository: {root_dir.absolute()} ---")

        for pdf_path in root_dir.rglob("*.pdf"):
            md_path = pdf_path.with_suffix(".md")

            if md_path.exists():
                pdf_mtime = os.path.getmtime(pdf_path)
                md_mtime = os.path.getmtime(md_path)
                if md_mtime > pdf_mtime:
                    skipped_count += 1
                    continue

            print(f"Converting: {pdf_path}...")

            success, has_form = convert_single_pdf(pdf_path, llm_client)
            if success:
                converted_count += 1
                if has_form:
                    form_count += 1

    print(f"\n--- Sync Complete ---")
    print(f"Converted: {converted_count}")
    if not single_file:
        print(f"Up-to-date: {skipped_count}")
    print(f"With forms/checkboxes: {form_count}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run on single file
        sync_pdfs_to_markdown(single_file=sys.argv[1])
    else:
        # Run on whole library
        sync_pdfs_to_markdown()
