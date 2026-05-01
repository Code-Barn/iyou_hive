"""
Shared utilities for legal document processing.
Used by both sync_legal_docs.py and generate_response_sheet.py
"""

import os
import re
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import pdfplumber

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / '.env')


# ---------------------------------------------------------------------------
# Shared PDF processing utilities
# ---------------------------------------------------------------------------

def is_readable(text):
    """Check if text contains enough readable content."""
    cleaned = re.sub(r'[\u25c8\u25c6\u2610\u2611\u2612\u2713\u2717\u2714Xx_\n\r\t]+', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    if len(cleaned.strip()) < 50:
        return False
    words = re.findall(r'\b[a-zA-Z]{3,}\b', cleaned.lower())
    if len(words) < 25:
        return False
    return True


def is_scanned_pdf(pdf_path):
    """Detects if a PDF is an image-based scan vs born-digital."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            sample_text = ""
            for page in pdf.pages[:3]:
                sample_text += page.extract_text() or ""
            return len(sample_text.strip()) < 50
    except Exception:
        return True


def clean_legal_artifacts(text):
    """
    Removes common legal form 'noise' like underscores used for
    handwriting lines and excessive whitespace.
    """
    # 1. Remove underscores inside words (e.g., _D_e_K_a_l_b_ -> DeKalb)
    text = re.sub(r'_(?=[a-zA-Z0-9])|(?<=[a-zA-Z0-9])_', '', text)

    # 2. Remove long runs of underscores used for blank lines
    text = re.sub(r'_{2,}', ' ', text)

    # 3. Fix "wide text" from OCR (e.g., "D e K a l b" -> "DeKalb")
    def fix_wide_text(m):
        return ''.join(m.group(0).split())

    text = re.sub(r'\b([A-Za-z])(\s+[A-Za-z])+\b',
                lambda m: fix_wide_text(m), text)

    # 4. Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def extract_form_fields(pdf_path):
    """Extract form field data from a PDF."""
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


def ocr_pdf_images(pdf_path):
    """OCR fallback using pytesseract. Requires 'sudo apt install tesseract-ocr'."""
    text_parts = []
    try:
        import fitz
        import pytesseract
        from PIL import Image
        from io import BytesIO
    except ImportError:
        print("  -> pytesseract or Pillow not installed.")
        return "\n".join(text_parts)

    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.open(BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img)
            if text.strip():
                text_parts.append(text.strip())
        doc.close()
    except Exception as e:
        print(f"  -> OCR Failed: {e}")
    return "\n".join(text_parts)


def get_local_ocr():
    """Get or create PaddleOCR instance for local OCR."""
    global _local_ocr
    if _local_ocr is None:
        try:
            from paddleocr import PaddleOCR
            _local_ocr = PaddleOCR(lang='en')
        except ImportError:
            print("  -> PaddleOCR not installed, falling back to pytesseract")
            _local_ocr = "pytesseract"
    return _local_ocr


_local_ocr = None


def ocr_pdf_with_paddle(pdf_path):
    """OCR using PaddleOCR."""
    text_parts = []
    try:
        import fitz
        ocr = get_local_ocr()
        if ocr == "pytesseract":
            return ocr_pdf_images(pdf_path)
        
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


def extract_text_from_pdf(pdf_path):
    """
    Tiered PDF text extraction:
    1. Try pdftotext (best for born-digital)
    2. Fallback to pdfplumber
    3. Fallback to OCR if scanned
    """
    text = ""
    pdf_path = Path(pdf_path)
    
    # Try pdftotext first
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
    
    # If still no text and it's scanned, try OCR
    if not text.strip() and is_scanned_pdf(pdf_path):
        text = ocr_pdf_with_paddle(pdf_path)
        if not text.strip():
            text = ocr_pdf_images(pdf_path)
    
    return text


# ---------------------------------------------------------------------------
# Boilerplate patterns
# ---------------------------------------------------------------------------

BOILERPLATE_PATTERNS = [
    re.compile(r'Approved by the Conference of Chief Judges', re.I),
    re.compile(r'Forms are free at', re.I),
    re.compile(r'Page \d+ of \d+', re.I),
    re.compile(r'IN THE STATE OF ILLINOIS', re.I),
    re.compile(r'Circuit Court.*County', re.I),
    re.compile(r'Enter the case information as it appears', re.I),
    re.compile(r'Explain in a few words what you are asking', re.I),
    re.compile(r'Where You Are Filing the Case', re.I),
    re.compile(r'Who started the case', re.I),
    re.compile(r'Who the case was filed against', re.I),
    re.compile(r'Check one box', re.I),
    re.compile(r'This should match the title you write', re.I),
    re.compile(r'Approved.*\d{4}\.\d{2}\.\d{2}', re.I),
    re.compile(r'State of Illinois.*Circuit Court', re.I),
    re.compile(r'Placeholder.*case number', re.I),
    re.compile(r'ATJ \d+\.\d+', re.I),
    re.compile(r'ilcourts\.info', re.I),
    re.compile(r'Find your Circuit Clerk', re.I),
    re.compile(r'After you fill out your forms', re.I),
    re.compile(r'file them with the circuit clerk', re.I),
    re.compile(r'send your forms to the other people', re.I),
    re.compile(r'NEXT STEP FOR PERSON', re.I),
    re.compile(r'Learn more about each step', re.I),
    re.compile(r'illinois court help', re.I),
    re.compile(r'illinois legal aid online', re.I),
    re.compile(r'You may also find more information', re.I),
    re.compile(r'location of your local legal self-help center', re.I),
    re.compile(r'If there are any words or terms that you do not understand', re.I),
    re.compile(r'ilcourthelp\.gov', re.I),
    re.compile(r'ilao\.info', re.I),
]

BLOCKLIST_PATTERNS = [
    re.compile(r'PROOF\s+OF\s+DELIVERY', re.I),
    re.compile(r'CERTIFICATE\s+OF\s+SERVICE', re.I),
    re.compile(r'Attorney\s+Number', re.I),
    re.compile(r'Law\s+Firm', re.I),
    re.compile(r'EFSP', re.I),
    re.compile(r'Street.*Apt\.?\s*#', re.I),
    re.compile(r'City\s+State\s+Zip\s+Code', re.I),
    re.compile(r'Instructions', re.I),
    re.compile(r'icourts\.info', re.I),
    re.compile(r'ATJ\s+\d+\.\d+', re.I),
]


def scrub_boilerplate(text):
    """Remove known form instructions and boilerplate text."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        if any(pat.search(line) for pat in BOILERPLATE_PATTERNS):
            continue
        if re.match(r'^\s*[._\u25fb\u25a1\u2610]{3,}\s*$', line):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


# ---------------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------------

DATE_PATTERNS = [
    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
    r'\b\d{4}-\d{2}-\d{2}\b',
    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b',
]


def extract_dates(text):
    """Extract all date patterns from text."""
    dates = []
    for pattern in DATE_PATTERNS:
        dates.extend(re.findall(pattern, text, re.IGNORECASE))
    return dates


# ---------------------------------------------------------------------------
# Metadata extraction patterns
# ---------------------------------------------------------------------------

# Illinois case number pattern: 2-4 digits + 2 letters + 5-12 digits
IL_CASE_PATTERN = re.compile(r'\b(\d{2,4}[A-Z]{2}\d{5,12})\b')

# Party name patterns
PARTY_PATTERNS = [
    re.compile(r'(?:PLAINTIFF|PETITIONER|DEFENDANT|RESPONDENT)[S]*(?:/\w+)*\s*:?\s*(.+?)(?:\n|\r|$)', re.I),
    re.compile(r'(?:IN RE):\s*(.+?)(?:\n|\r|$)', re.I),
    re.compile(r'Who started the case\.\s*(.+?)(?:\n|\r|$)', re.I),
    re.compile(r'Who the case was filed against\.\s*(.+?)(?:\n|\r|$)', re.I),
]

# Title patterns
TITLE_PATTERNS = [
    re.compile(r'MOTION\s+TO\s+(.+?)(?:\n|\r|$)', re.I),
    re.compile(r'NOTICE\s+OF\s+(.+?)(?:\n|\r|$)', re.I),
    re.compile(r'PETITION\s+FOR\s+(.+?)(?:\n|\r|$)', re.I),
    re.compile(r'Motion to:\s*(.+?)(?:\n|\r|$)', re.I),
]


def extract_metadata(text, state_code="IL"):
    """
    Extract metadata (case number, parties, title) from legal text.
    Returns dict with keys: case_number, parties, title
    """
    metadata = {
        'case_number': '',
        'parties': [],
        'title': '',
        'case_header': ''
    }
    
    # Extract case number
    case_match = IL_CASE_PATTERN.search(text)
    if case_match:
        metadata['case_number'] = case_match.group(1)
    
    # Extract parties
    for pattern in PARTY_PATTERNS:
        matches = pattern.findall(text)
        for match in matches:
            name = match.strip()
            if name and len(name) > 2 and name not in metadata['parties']:
                # Clean up names
                name = re.sub(r'[,_;]', '', name)
                name = re.sub(r'\s+', ' ', name).strip()
                if name:
                    metadata['parties'].append(name)
    
    # Extract title
    for pattern in TITLE_PATTERNS:
        match = pattern.search(text)
        if match:
            title = match.group(1).strip()
            if title and len(title) > 5:
                metadata['title'] = title.upper()
                break
    
    # Build case header
    if metadata['case_number'] and metadata['title']:
        metadata['case_header'] = f"{metadata['case_number']} - {metadata['title']}"
    elif metadata['case_number']:
        metadata['case_header'] = metadata['case_number']
    elif metadata['title']:
        metadata['case_header'] = metadata['title']
    
    return metadata


# ---------------------------------------------------------------------------
# Form label detection
# ---------------------------------------------------------------------------

FORM_LABEL_PATTERNS = [
    re.compile(r'^\s*COUNTY:\s*_{2,}', re.I),
    re.compile(r'^\s*CASE\s+NUMBER:\s*_{2,}', re.I),
    re.compile(r'^\s*PLAINTIFF.*:\s*_{2,}', re.I),
    re.compile(r'^\s*DEFENDANT.*:\s*_{2,}', re.I),
    re.compile(r'^\s*NAME:\s*_{2,}', re.I),
    re.compile(r'^\s*ADDRESS:\s*_{2,}', re.I),
    re.compile(r'^\s*PHONE.*:\s*_{2,}', re.I),
    re.compile(r'^\s*EMAIL.*:\s*_{2,}', re.I),
    re.compile(r'^\s*SIGNATURE:\s*_{2,}', re.I),
    re.compile(r'^\s*MOTION\s+TO:\s*_{2,}', re.I),
    re.compile(r'^\s*EXPLAIN.*:\s*_{2,}', re.I),
    re.compile(r'^\s*I\s+AM.*:\s*_{2,}', re.I),
    re.compile(r'^\s*ENTER\s+THE\s+CASE', re.I),
    re.compile(r'^\s*WHO\s+STARTED\s+THE\s+CASE', re.I),
    re.compile(r'^\s*WHO\s+THE\s+CASE\s+WAS\s+FILED\s+AGAINST', re.I),
]


def is_form_label(text):
    """Check if text is a form label (not user content)."""
    for pattern in FORM_LABEL_PATTERNS:
        if pattern.search(text):
            return True
    return False


def is_form_instruction(text, blank_lines=None, threshold=0.6):
    """
    Check if text is likely a form instruction.
    Uses multiple strategies for detection.
    """
    if not text:
        return False
    
    normalized = re.sub(r'\s+', ' ', text.strip().lower())
    
    # Strategy 1: Word overlap with blank form
    if blank_lines:
        words_text = set(normalized.split())
        if words_text:
            for blank_line in blank_lines:
                words_blank = set(blank_line.split())
                if words_blank:
                    overlap = len(words_text & words_blank)
                    similarity = overlap / max(len(words_text), len(words_blank))
                    if similarity > threshold:
                        return True
    
    # Strategy 2: Key form phrases
    form_phrases = [
        'under illinois supreme court rule',
        'my signature means that',
        'i read the document',
        'i have been informed and believe it is true',
        'i am not filing it to cause delay',
        'accepted:',
        'reviewed by:',
        'env#',
        'case number',
        'in some counties, you may get the court date',
        'after you fill out your forms',
        'file them with the circuit clerk',
        'send your forms to the other people',
        'find your circuit clerk',
        'this form is approved by the illinois supreme court',
        'forms are free at',
        'page',
        'of',
        'next step for person',
        'learn more about each step',
        'illinois court help',
        'illinois legal aid online',
        'you may also find more information',
        'location of your local legal self-help center',
    ]
    for phrase in form_phrases:
        if phrase in normalized:
            return True
    
    # Strategy 3: Detect form labels (text with underscores)
    if '__' in text or '___' in text:
        return True
    
    # Strategy 4: Check against blocklist patterns
    for pattern in BLOCKLIST_PATTERNS:
        if pattern.search(text):
            return True
    
    return False
