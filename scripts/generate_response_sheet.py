#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pdfplumber",
#     "python-dotenv",
#     "PyMuPDF",
#     "pytesseract",
#     "Pillow",
#     "google-genai>=1.74.0",
# ]
# ///

"""
Hiver Legal Response Sheet Generator

Converts a filled-out Illinois legal PDF (Motion, Additional Page, etc.) into a
printable two-column "Response Sheet" for factual rebuttal.

Usage:
    uv run scripts/generate_response_sheet.py <input_pdf> [output_md_path]

Or mark executable and run directly:
    chmod +x scripts/generate_response_sheet.py
    ./scripts/generate_response_sheet.py <input_pdf>
"""

import os
import re
import sys
import subprocess
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import pdfplumber

# Load .env from project root (parent of scripts/)
load_dotenv(Path(__file__).parent.parent / '.env')

# Import shared utilities
from legal_utils import (
    is_readable, is_scanned_pdf, clean_legal_artifacts,
    extract_form_fields, ocr_pdf_images, scrub_boilerplate,
    extract_dates, extract_metadata, is_form_instruction,
    BOILERPLATE_PATTERNS, BLOCKLIST_PATTERNS
)

# Import form field mapping and detection
try:
    from form_field_mapping import get_form_fields, classify_text, extract_narrative_text, FormFieldType
    from form_detector import detect_form_type, process_form
    FORM_MAPPING_AVAILABLE = True
except ImportError as e:
    FORM_MAPPING_AVAILABLE = False
    print(f"Warning: form_field_mapping.py or form_detector.py not found: {e}")

# ---------------------------------------------------------------------------
# State-Specific Rule Registry
# ---------------------------------------------------------------------------

class StateRuleRegistry:
    """
    A pluggable system for handling different state form structures.
    Add new states here as you expand.
    """

    @staticmethod
    def get_rules(state_code="IL"):
        registry = {
            "IL": {
                "field_patterns": [
                    re.compile(r'topmostSubform.*txtMotion', re.I),
                    re.compile(r'topmostSubform.*txtAdditionalExplanation', re.I),
                    re.compile(r'section\s*3.*motion', re.I),
                    re.compile(r'additional\s*explanation', re.I),
                ],
                "case_pattern": re.compile(r'case\s*number|case\s*no', re.I),
                "title_pattern": re.compile(r'motion.*title|title.*motion|document\s*title', re.I)
            },
            "CA": {
                # California Judicial Council forms often use field names like 'MC-030'
                "field_patterns": [re.compile(r'form.*description|MC-\d+', re.I)],
                "case_pattern": re.compile(r'case\s*number', re.I),
                "title_pattern": re.compile(r'document\s*title', re.I)
            },
            # Default fallback for "Universal" US support
            "DEFAULT": {
                "field_patterns": [re.compile(r'explanation|description|narrative|motion', re.I)],
                "case_pattern": re.compile(r'case', re.I),
                "title_pattern": re.compile(r'title', re.I)
            }
        }
        return registry.get(state_code.upper(), registry["DEFAULT"])

# ---------------------------------------------------------------------------
# Re-use helpers from sync_legal_docs
# ---------------------------------------------------------------------------

def is_readable(text):
    cleaned = re.sub(r'[☑☒✓Xx_\n\r\t]+', '', text)
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
            # Check up to 3 pages for existing digital text
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
    # Match sequences of single letters separated by spaces
    def fix_wide_text(m):
        return ''.join(m.group(0).split())

    text = re.sub(r'\b([A-Za-z])(\s+[A-Za-z])+\b',
                lambda m: fix_wide_text(m), text)

    # 4. Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text

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
    except pytesseract.TesseractNotFoundError:
        print("  -> Tesseract binary not found. Install tesseract-ocr.")
    except Exception as e:
        print(f"  -> OCR Failed: {e}")
    return "\n".join(text_parts)


# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------

def get_llm_client():
    import os
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    # Use v1 API (stable) not v1beta
    return genai.Client(api_key=api_key, http_options={'api_version': 'v1'})


# ---------------------------------------------------------------------------
# Date extraction helper
# ---------------------------------------------------------------------------

DATE_PATTERNS = [
    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
    r'\b\d{4}-\d{2}-\d{2}\b',
    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b',
]


def extract_dates(text):
    dates = []
    for pattern in DATE_PATTERNS:
        dates.extend(re.findall(pattern, text, re.IGNORECASE))
    return dates


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def collect_narrative_text(form_data, state_code="IL"):
    """
    Prioritizes specific form fields to avoid pulling in
    court headers and instruction text.
    Uses StateRuleRegistry for state-specific field patterns.
    """
    rules = StateRuleRegistry.get_rules(state_code)
    narrative_parts = []

    # 1. Try to find fields matching state-specific patterns
    for key, value in form_data.items():
        if not value or len(str(value).strip()) < 5:
            continue

        for pat in rules["field_patterns"]:
            if pat.search(key):
                narrative_parts.append(str(value).strip())
                break

    # 2. If we found specific fields, return them exclusively
    if narrative_parts:
        return "\n\n".join(narrative_parts), True

    # 3. Fallback: If no specific fields found, then and only then
    # look for any large text block that isn't a header
    for key, value in form_data.items():
        val_str = str(value).strip()
        if len(val_str) > 200: # Typical threshold for a narrative block
            narrative_parts.append(val_str)

    return "\n\n".join(narrative_parts), False


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
]


def scrub_boilerplate(text):
    """Remove known form instructions and boilerplate text."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        if any(pat.search(line) for pat in BOILERPLATE_PATTERNS):
            continue
        if re.match(r'^\s*[\._◻□☐]{3,}\s*$', line):  # Skip lines that are just underscores/boxes
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)

def clean_claim_text(text, blank_lines=None):
    """
    Clean individual claim text by removing boilerplate embedded within.
    Removes: checkbox text, clerk footers, form instructions, URLs.
    If blank_lines provided, also removes form labels (keeps user input after labels).
    """
    import unicodedata
    
    # Normalize unicode characters (fix special chars like )
    text = unicodedata.normalize('NFKC', text)
    
    # Remove checkbox attachments (✔ I need more room... or ✓ I have filled out...)
    text = re.sub(r'[✓✔❌☑☒]\s*(I need more room|I have filled out|Additional Page).*?(?=\.|$)', '', text, flags=re.IGNORECASE)
    
    # Remove clerk footers - pattern: "Accepted: 4/29/2026 8:27 AM Reviewed By: EH Env#37816100"
    text = re.sub(r'Accepted:\s*[\d/]+\s*[\d:]+\s*[AP]M\s*Reviewed By:\s*\w+\s*Env#\d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Reviewed By:\s*\w+\s*Env#\d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Env#\d+', '', text)
    text = re.sub(r'Case Number\s*SIGN', 'SIGN', text)
    
    # Remove case numbers like "25FA152" that appear after clerk footers
    text = re.sub(r'\d+FA\d+\s*', '', text)
    
    # Remove "SIGN Under Illinois Supreme Court Rule 137..." text (multi-line)
    text = re.sub(r'SIGN.*?Under Illinois Supreme Court Rule.*?(?=\.|$)', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\S+\.info/\S+', '', text)
    text = re.sub(r'ilcourts\.info\S*', '', text)
    
    # Remove "In some counties, you may get the court date..." boilerplate (multi-line)
    text = re.sub(r'In some counties, you may get the court date.*?(?=\.|$)', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'After you fill out your forms.*?(?=\.|$)', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'Find your Circuit Clerk.*?(?=\.|$)', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove "NEXT STEP FOR PERSON FILLING..." boilerplate
    text = re.sub(r'NEXT STEP FOR.*?(?=\.|$)', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove "You may also find more information..." boilerplate
    text = re.sub(r'You may also find more information.*?(?=\.|$)', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # NEW: Remove form labels (keep user input after the label)
    if blank_lines:
        text_lower = text.lower()
        for blank_line in blank_lines:
            if len(blank_line) > 10:
                # Remove underscores from blank line for matching
                blank_clean = re.sub(r'_+', '', blank_line).strip()
                if blank_clean and blank_clean in text_lower:
                    idx = text_lower.find(blank_clean)
                    if idx >= 0:
                        # Find corresponding position in original text
                        # (try to find case-insensitive match)
                        for i in range(len(text) - len(blank_clean) + 1):
                            if text[i:].lower().startswith(blank_clean):
                                # Remove the blank line, keep text after it
                                text = text[:i] + text[i + len(blank_clean):]
                                text_lower = text.lower()
                                break
    
    # Remove remnant special characters () and fix ". ." artifacts
    text = re.sub(r'[]', '', text)
    text = re.sub(r'\s+\.', '.', text)  # Fix " ." to "."
    text = re.sub(r'\.\s*\.', '.', text)  # Fix ".." to "."
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Final cleanup - remove trailing ". ." or similar
    text = re.sub(r'\.+', '.', text)  # Collapse multiple periods to one
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def strip_blank_form_content(text, state_code="IL"):
    """
    Remove form labels that appear in the blank form BEFORE chunking.
    This prevents form labels from becoming part of chunks.

    Strategy: For each line in the narrative, check if it STARTS WITH or CONTAINS
    a form label from the blank form. If so, remove just the label part.
    """
    blank_lines = load_blank_form_text(state_code)
    if not blank_lines:
        return text

    lines = text.split('\n')
    cleaned_lines = []
    removed_count = 0

    for line in lines:
        original_line = line
        normalized_line = re.sub(r'\s+', ' ', line.strip().lower())

        # Skip empty lines
        if not normalized_line:
            cleaned_lines.append(line)
            continue

        # Check if this line contains a form label
        cleaned_line = line
        for blank_line in blank_lines:
            # If the blank line is a substantial part of our line, remove it
            if len(blank_line) > 10 and blank_line in normalized_line:
                # Remove the form label from the line
                # Try to keep just the user's input (text after the label)
                idx = normalized_line.find(blank_line)
                if idx >= 0:
                    # Keep text after the label
                    remaining = normalized_line[idx + len(blank_line):].strip()
                    if remaining and len(remaining) > 3:
                        # Find where the remaining text starts in the original line
                        # (accounting for case differences)
                        idx_orig = line.lower().find(remaining)
                        if idx_orig >= 0:
                            cleaned_line = line[idx_orig:].strip()
                            removed_count += 1
                            break

        cleaned_lines.append(cleaned_line)

    if removed_count > 0:
        print(f"  -> Removed {removed_count} form label lines before chunking")

    return '\n'.join(cleaned_lines)


def extract_content_smart(file_path, state_code="IL"):
    """
    Tiered extraction:
    1. Detect form type(s) in the document (handles combined Motion + Additional Page)
    2. Split combined forms into sections
    3. Extract user input from each section using its specific blank form
    """
    rules = StateRuleRegistry.get_rules(state_code)
    narrative_text = ""
    form_data = {}
    is_fillable_form = False
    metadata_text = ""  # Separate metadata from claims

    file_path = Path(file_path)

    # Handle Markdown files
    if file_path.suffix.lower() == '.md':
        print(f"  -> Reading Markdown file directly...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                filled_text = f.read()
            
            # Use form detector to split combined forms
            from form_detector import split_combined_form, extract_user_input_from_section
            
            sections = split_combined_form(filled_text, state_code)
            print(f"  -> Detected {len(sections)} form section(s)")
            
            # Extract user input from each section
            user_texts = []
            for section in sections:
                form_type = section['form_type']
                section_text = section['text']
                print(f"     - {form_type}: {len(section_text)} chars")
                
                user_text = extract_user_input_from_section(section_text, form_type, state_code)
                if user_text:
                    user_texts.append(user_text)
            
            narrative_text = '\n\n'.join(user_texts)
            
        except Exception as e:
            print(f"  -> Error reading markdown: {e}")
            narrative_text = ""
    
    # Handle PDF files
    elif file_path.suffix.lower() == '.pdf':
        print(f"  -> Extracting text from PDF: {file_path}")
        try:
            result = subprocess.run(
                ['pdftotext', '-layout', str(file_path), '-'],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                pdf_text = result.stdout
                
                # Use form detector to split combined forms
                from form_detector import split_combined_form, extract_user_input_from_section
                
                sections = split_combined_form(pdf_text, state_code)
                print(f"  -> Detected {len(sections)} form section(s)")
                
                # Extract user input from each section
                user_texts = []
                for section in sections:
                    form_type = section['form_type']
                    section_text = section['text']
                    print(f"     - {form_type}: {len(section_text)} chars")
                    
                    user_text = extract_user_input_from_section(section_text, form_type, state_code)
                    if user_text:
                        user_texts.append(user_text)
                
                narrative_text = '\n\n'.join(user_texts)
            else:
                narrative_text = ""
        except Exception as e:
            print(f"  -> Error extracting PDF: {e}")
            narrative_text = ""
    
    # Final scrub and clean
    narrative_text = scrub_boilerplate(narrative_text)
    narrative_text = clean_legal_artifacts(narrative_text)
    return narrative_text, form_data

    # Handle PDF files (original logic)
    # Step1: Try Form Field Metadata
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                fields = page.get_form_fields()
                if fields:
                    is_fillable_form = True
                    for f in fields:
                        name, val = f.get("name", ""), f.get("export_value", "")
                        if val:
                            form_data[name] = val
    except Exception:
        pass

    # STRICT FIELD TARGETING: Only narrative fields
    if form_data:
        priority_patterns = [
            re.compile(r'txtMotion', re.I),
            re.compile(r'txtAdditionalExplanation', re.I),
            re.compile(r'topmostSubform.*txtMotion', re.I),
            re.compile(r'topmostSubform.*txtAdditionalExplanation', re.I),
            # Additional variations for Illinois forms
            re.compile(r'motion', re.I),
            re.compile(r'additional.*explanation', re.I),
            re.compile(r'narrative', re.I),
        ]

        found_narrative = False
        for name, val in form_data.items():
            for pat in priority_patterns:
                if pat.search(name) and val.strip():
                    # Scrub boilerplate from each field
                    cleaned = scrub_boilerplate(val)
                    if cleaned.strip():
                        narrative_text += f"\n{cleaned}"
                        found_narrative = True
                    break

        # IF NO NARRATIVE FIELDS FOUND: Do NOT fallback to other fields
        # This prevents boilerplate from entering the narrative
        if not found_narrative:
            print("  -> No narrative fields found in form data, trying OCR...")
            # Try OCR instead of falling back to random fields
            narrative_text = ""

    # ONLY use digital text extraction if NO form data existed at all
    # FALLBACK: Only if NO form fields yielded narrative
    if not narrative_text.strip():
        if is_scanned_pdf(file_path):
            print(f"  -> {state_code}: Scanned PDF detected. Running Tesseract...")
            narrative_text = ocr_pdf_images(file_path)
        else:
            print(f"  -> {state_code}: Digital PDF detected. Extracting raw text...")
            try:
                with pdfplumber.open(file_path) as pdf:
                    narrative_text = "\n".join([p.extract_text() or "" for p in pdf.pages])
            except Exception:
                pass

    # Final scrub and clean
    narrative_text = scrub_boilerplate(narrative_text)
    narrative_text = clean_legal_artifacts(narrative_text)

    return narrative_text, form_data


def extract_user_input(filled_text, state_code="IL"):
    """
    Extract ONLY the user's narrative text from the filled form.
    Compares filled MD against blank MD to find what the user actually wrote.
    Uses both the main blank form and additional page blank form for comparison.
    """
    # Load blank form lines (main form)
    blank_lines = load_blank_form_text(state_code)
    
    # Also load additional page blank form if available
    additional_blank_lines = set()
    config = get_state_config(state_code)
    if config:
        additional_path = config.get("additional_form_path")
        if additional_path:
            md_path = Path(additional_path).with_suffix(".md")
            if md_path.exists():
                try:
                    with open(md_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    for line in text.split('\n'):
                        normalized = re.sub(r'\s+', ' ', line.strip().lower())
                        if len(normalized) > 3:
                            additional_blank_lines.add(normalized)
                    print(f"  -> Loaded {len(additional_blank_lines)} lines from additional blank form")
                except Exception as e:
                    print(f"  -> Error reading additional blank form: {e}")
    
    all_blank_lines = blank_lines | additional_blank_lines
    
    if not all_blank_lines:
        print("  -> Warning: No blank form text loaded, returning all text")
        return filled_text
    
    print(f"  -> Total blank form lines for comparison: {len(all_blank_lines)}")
    
    filled_lines = filled_text.split('\n')
    user_lines = []
    
    for line in filled_lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        
        # Normalize the line for comparison
        line_normalized = re.sub(r'\s+', ' ', line_clean.lower())
        
        # Skip if line is entirely from blank form
        is_blank_line = False
        for blank_line in all_blank_lines:
            # Exact match
            if line_normalized == blank_line:
                is_blank_line = True
                break
            # Line is mostly blank form text (>80% word overlap)
            words_line = set(line_normalized.split())
            words_blank = set(blank_line.split())
            if words_line and words_blank:
                overlap = len(words_line & words_blank)
                similarity = overlap / max(len(words_line), 1)
                if similarity > 0.8:  # 80% threshold
                    is_blank_line = True
                    break
        
        if not is_blank_line:
            # This line is not in blank form at all = pure user input
            user_lines.append(line_clean)
    
    result = '\n'.join(user_lines)
    print(f"  -> Extracted {len(user_lines)} lines of user input from {len(filled_lines)} total lines")
    return result
    return result


def split_by_blank_form_labels(text, state_code="IL"):
    """
    Split text by blank form labels BEFORE chunking.
    This prevents form labels from being part of chunks.
    Returns cleaned text with form labels removed.
    """
    blank_lines = load_blank_form_text(state_code)
    if not blank_lines:
        return text
    
    # Build a list of all blank line positions in the text
    text_lower = text.lower()
    split_positions = [0]  # Start of text
    
    for blank_line in blank_lines:
        if len(blank_line) < 10:
            continue
        # Remove underscores for matching
        blank_clean = re.sub(r'_+', '', blank_line).strip()
        if not blank_clean:
            continue
        
        # Find all occurrences of this blank line in text
        start_idx = 0
        while True:
            idx = text_lower.find(blank_clean, start_idx)
            if idx == -1:
                break
            # Add position where blank line starts
            split_positions.append(idx)
            start_idx = idx + len(blank_clean)
    
    # Sort and deduplicate positions
    split_positions = sorted(set(split_positions))
    
    # Extract pieces between split positions
    pieces = []
    for i in range(len(split_positions) - 1):
        piece = text[split_positions[i]:split_positions[i+1]]
        piece = piece.strip()
        if piece and len(piece) > 20:  # Keep only substantial pieces
            pieces.append(piece)
    
    # Add the last piece
    if split_positions[-1] < len(text):
        piece = text[split_positions[-1]:].strip()
        if piece and len(piece) > 20:
            pieces.append(piece)
    
    # Filter out pieces that are mostly form labels (no user content)
    result_pieces = []
    for piece in pieces:
        # Check if piece has substantial user content (not just form labels)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', piece.lower())
        if len(words) > 10:  # Has substantial user content
            result_pieces.append(piece)
    
    result = '\n\n'.join(result_pieces)
    if result != text:
        print(f"  -> Split text by blank form labels: {len(pieces)} pieces kept")
    
    return result


def load_blank_form_text(state_code="IL"):
    """
    Load blank form text for comparison.
    Returns set of lines that are likely form instructions.
    Uses MD file if available, falls back to PDF.
    Now captures ALL lines (not just >3 chars) to catch short form labels.
    Also captures form labels with underscores (like "COUNTY: ___").
    """
    blank_text = set()

    # Try MD file first (faster, already extracted)
    config = get_state_config(state_code)
    if config:
        form_path = config.get("form_path")
        if form_path:
            md_path = Path(form_path).with_suffix(".md")
            if md_path.exists():
                try:
                    with open(md_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    for line in text.split('\n'):
                        normalized = re.sub(r'\s+', ' ', line.strip().lower())
                        # Lower threshold to capture more form text (including labels with underscores)
                        if len(normalized) > 3:
                            blank_text.add(normalized)
                    print(f"  -> Loaded {len(blank_text)} lines from MD: {md_path}")
                    return blank_text
                except Exception as e:
                    print(f"  -> Error reading MD: {e}")

    # Fall back to PDF
    blank_path = get_blank_form_path(state_code)
    if not blank_path or not Path(blank_path).exists():
        return blank_text

    try:
        with pdfplumber.open(blank_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    # Add each line (normalized) to the set
                    for line in text.split('\n'):
                        normalized = re.sub(r'\s+', ' ', line.strip().lower())
                        if len(normalized) > 3:
                            blank_text.add(normalized)
    except Exception as e:
        print(f"  -> Could not load blank form: {e}")

    return blank_text


def is_form_instruction(text, blank_lines, threshold=0.6):
    """
    Check if text is likely a form instruction by comparing against blank form.
    Uses multiple strategies:
    1. Word overlap similarity (>threshold)
    2. Substring match (if >50% of text appears in blank form)
    3. Key phrase matching (common form instructions)
    4. Form label detection (text with underscores, form field patterns)
    5. Short label detection (text that looks like a form field label)
    """
    if not blank_lines or not text:
        return False

    normalized = re.sub(r'\s+', ' ', text.strip().lower())

    # Strategy 1: Word overlap
    words_text = set(normalized.split())
    if words_text:
        for blank_line in blank_lines:
            words_blank = set(blank_line.split())
            if words_blank:
                overlap = len(words_text & words_blank)
                similarity = overlap / max(len(words_text), len(words_blank))
                if similarity > threshold:
                    return True

    # Strategy 2: Substring match - if significant portion appears in blank form
    text_len = len(normalized)
    for blank_line in blank_lines:
        if len(blank_line) > 20:
            # Check if this blank line is a substantial substring of our text
            if blank_line in normalized:
                # If >40% of our text is from blank form, it's likely form text
                if len(blank_line) / text_len > 0.4:
                    return True

    # Strategy 3: Key form phrases that should always be filtered
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

    # Strategy 4: Detect form labels (text with lots of underscores or form fields)
    if '__' in text or '___' in text:
        return True

    # Strategy 5: Detect common form field patterns
    form_patterns = [
        r'^\s*county:?\s*_{2,}',
        r'^\s*case number:?\s*_{2,}',
        r'^\s*plaintiff.*:?\s*_{2,}',
        r'^\s*defendant.*:?\s*_{2,}',
        r'^\s*name:?\s*_{2,}',
        r'^\s*address:?\s*_{2,}',
        r'^\s*phone.*:?\s*_{2,}',
        r'^\s*email.*:?\s*_{2,}',
        r'^\s*signature.*:?\s*_{2,}',
        r'^\s*motion to:?\s*_{2,}',
        r'^\s*explain.*:?\s*_{2,}',
        r'^\s*i am.*:?\s*_{2,}',
        r'^\s*enter the case',
        r'^\s*who started the case',
        r'^\s*who the case was filed against',
    ]
    for pattern in form_patterns:
        if re.search(pattern, normalized, re.IGNORECASE):
            return True

    return False


def chunk_claims_smart(narrative_text, state_code="IL"):
    """
    Smart chunking logic that handles Roman numerals (I, II, III), Capital letters (A, B, C),
    and Numbers (1, 2, 3) as legal markers. Identifies labels and body text for each claim.
    Filters out boilerplate sections common in Illinois forms.
    ATOMIZES: Splits compound paragraphs into individual claims.
    Uses blank form comparison to filter out form instructions.
    """
    # Load blank form for comparison
    print(f"  -> Loading blank form for {state_code}...")
    blank_lines = load_blank_form_text(state_code)
    if blank_lines:
        print(f"  -> Loaded {len(blank_lines)} lines from blank form")

    # Section header patterns for plain text detection (Option 2)
    SECTION_PATTERNS = [
        re.compile(r'^(BACKGROUND|ALLEGATIONS|FACTS|ARGUMENT|RELIEF)', re.I),
        re.compile(r'^(COUNT \d+|COUNT I{1,3})', re.I),
        re.compile(r'^(First|Second|Third|Fourth|Fifth|Sixth)', re.I),
    ]

    # Items to exclude from the final response sheet - use word boundaries for accuracy
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
        re.compile(r'ATJ\s+801\.7', re.I),
    ]

    processed_claims = []

    # Helper: scrub boilerplate from text and skip if empty
    def is_boilerplate(text):
        if any(pat.search(text) for pat in BLOCKLIST_PATTERNS):
            return True
        if any(pat.search(text) for pat in BOILERPLATE_PATTERNS):
            return True
        return False

    # Helper: check if text is form instruction (using blank form comparison)
    def check_form_instruction(text):
        if is_boilerplate(text):
            return True
        if blank_lines and is_form_instruction(text, blank_lines):
            return True
        return False

    # Helper: atomize - split compound paragraphs into individual sentences/claims
    def atomize_text(text):
        """Split text into individual atomic claims."""
        # Split by sentence endings (period + space + capital letter), keeping the period
        parts = re.split(r'(?<=\.)\s+(?=[A-Z])', text)
        claims = []
        for part in parts:
            part = part.strip()
            if len(part) > 20:  # Skip very short fragments
                claims.append(part)
        return claims if claims else [text]  # Fallback to original if no split

    # Approach 1: Try to split by legal markers (Roman numerals, numbers, etc.)
    # Pattern matches: I., II., A., B., 1., 1), etc. at the start of a line
    marker_pattern = r'\n\s*(?=[IXVLC]+[\.\)]|[A-Z][\.\)]|\d+[\.\)])'
    raw_chunks = re.split(marker_pattern, "\n" + narrative_text)

    if len(raw_chunks) > 1:
        # Found legal markers, process each chunk
        for chunk in raw_chunks:
            chunk = chunk.strip()
            if not chunk or len(chunk) < 10:
                continue
            # Filter boilerplate and form instructions
            if is_boilerplate(chunk) or check_form_instruction(chunk):
                continue
            # Scrub boilerplate from chunk text
            chunk = scrub_boilerplate(chunk)
            if not chunk:
                continue
            # Check if first line is a label
            lines = chunk.split('\n', 1)
            if len(lines) > 1 and len(lines[0]) < 50:
                label = lines[0].strip()
                body = lines[1].strip()
                # ATOMIZE: split body into individual claims
                for atomic_claim in atomize_text(body):
                    processed_claims.append({"label": label, "body": atomic_claim})
            else:
                # ATOMIZE: split chunk into individual claims
                for atomic_claim in atomize_text(chunk):
                    processed_claims.append({"label": "", "body": atomic_claim})

    # Approach 2: If no markers found, try section headers
    if not processed_claims:
        has_section = any(pat.search(narrative_text) for pat in SECTION_PATTERNS)
        if has_section:
            section_splits = re.split(r'\n(?=(?:BACKGROUND|ALLEGATIONS|FACTS|ARGUMENT|RELIEF|COUNT|First|Second|Third|Fourth|Fifth|Sixth))', narrative_text, flags=re.I)
            for sect in section_splits:
                sect = sect.strip()
                if len(sect) > 50:
                    if is_boilerplate(sect) or check_form_instruction(sect):
                        continue
                    sect = scrub_boilerplate(sect)
                    if not sect:
                        continue
                    sect_lines = sect.split('\n', 1)
                    if len(sect_lines) > 1 and len(sect_lines[0]) < 50:
                        label = sect_lines[0].strip()
                        body = sect_lines[1].strip()
                        for atomic_claim in atomize_text(body):
                            processed_claims.append({"label": label, "body": atomic_claim})
                    else:
                        for atomic_claim in atomize_text(sect):
                            processed_claims.append({"label": "", "body": atomic_claim})

    # Approach 3: For long text without markers, split by sentences
    if not processed_claims and len(narrative_text) > 500:
        # Split by sentence endings, but keep sentence boundaries intact
        sentences = re.split(r'(?<!\d)\.\s+(?=[A-Z])', narrative_text)
        current_claim = ""
        for sent in sentences:
            sent = sent.strip()
            sent = scrub_boilerplate(sent)
            if not sent or check_form_instruction(sent):
                continue
            # If adding this sentence makes claim too long, start new claim
            if len(current_claim) > 300 and current_claim:
                if not current_claim.endswith('.'):
                    current_claim += '.'
                processed_claims.append({"label": "", "body": current_claim})
                current_claim = sent
            else:
                if current_claim:
                    current_claim += ' ' + sent
                else:
                    current_claim = sent
        # Don't forget the last claim
        if current_claim:
            if not current_claim.endswith('.'):
                current_claim += '.'
            processed_claims.append({"label": "", "body": current_claim})

    # Approach 4: Double-newline splitting
    if not processed_claims:
        print("  -> No markers found, splitting by double newlines...")
        blocks = re.split(r'\n\s*\n', narrative_text)
        for b in blocks:
            b = b.strip()
            b = scrub_boilerplate(b)
            if b and len(b) > 30 and not check_form_instruction(b):
                processed_claims.append({"label": "", "body": b})

    # FINAL FALLBACK: Use entire text as one claim
    if not processed_claims:
        print("  -> No chunks created, using entire text as single claim...")
        processed_claims = [{"label": "", "body": scrub_boilerplate(narrative_text.strip())}]

    # Assign sequential IDs and normalize fields
    for i, claim in enumerate(processed_claims, 1):
        if "id" not in claim:
            claim["id"] = i
        if "text" not in claim and "body" in claim:
            claim["text"] = claim["body"]

    # Categorize claims by type (substantive, procedural)
    procedural_patterns = [
        re.compile(r'filed on|accepted on|case number|case is|entered on|obtained|police report|order of protection', re.I),
        re.compile(r'return date|documents.*sent|phone number|email address|address is', re.I),
    ]

    for claim in processed_claims:
        text = claim.get("text", claim.get("body", ""))
        claim_type = "substantive"  # default

        # Check if procedural
        if any(pat.search(text) for pat in procedural_patterns):
            claim_type = "procedural"

        claim["type"] = claim_type

    # Return in new dict format for consistency
    return {
        "metadata": {},
        "procedural_facts": [c["text"] for c in processed_claims if c.get("type") == "procedural"],
        "claims": processed_claims
    }


import requests
import os
import re
from state_form_config import get_blank_form_path, get_title_patterns, get_state_config

def chunk_claims_with_llm(client, narrative_text):
    """
    Use Gemini client (from get_llm_client) to chunk claims.
    Falls back to local chunking if API fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or client is None:
        print("  -> No Gemini client, using local chunker.")
        return chunk_claims_smart(narrative_text)

    try:
        # Use the client passed in (genai.Client)
        # system_instruction not supported in this SDK version, so include in prompt
        system_prompt = (
            "You are a legal document analyst. Extract ATOMIC claims from pro se legal narratives.\n"
            "STRICT INSTRUCTIONS FOR LEGAL INTEGRITY:\n"
            "1. VERBATIM REQUIREMENT: You MUST reproduce the EXACT wording from the text. NO paraphrasing, NO summarizing, NO rewording.\n"
            "2. If the text says 'I am asking the Court to approve relocation', you MUST output 'I am asking the Court to approve relocation'.\n"
            "3. Preserve ALL original capitalization, punctuation, and formatting. Legal documents require exact reproduction.\n"
            "OUTPUT: Return ONLY a valid JSON object (no markdown fences, no intro/outro) with these keys:\n"
            "  'metadata': { 'case_header': '...', 'parties': ['...'], 'case_number': '...', 'title': '...' }\n"
            "  'procedural_facts': [ 'Fact A', 'Fact B' ]  // Non-rebuttable context (dates filed, venues, etc.)\n"
            "  'claims': [ { 'id': 1, 'label': '1.', 'text': 'Claim text', 'type': 'substantive' }, ... ]\n"
            "RULES:\n"
            "1. IGNORE all form instructions, boilerplate, headers, page numbers, 'Enter the case' text.\n"
            "2. metadata: Extract ONLY court name, county, case number, party names/roles.\n"
            "3. procedural_facts: Filing dates, court locations, case numbers (non-rebuttable).\n"
            "4. claims: EVERY individual factual allegation or legal argument gets its OWN object.\n"
            "5. ATOMIZE: If a paragraph has 3 accusations, create 3 separate claim objects.\n"
            "6. Each claim needs 'id' (sequential int), 'label' (e.g., '1.'), 'text' (string), 'type' ('substantive'/'procedural').\n"
            "7. NEVER combine multiple arguments into one claim. NEVER summarize. If they wrote it, it is a separate claim.\n"
            "8. Exclude metadata/boilerplate from claims list entirely.\n"
            "9. VERBATIM: Output the text EXACTLY as written. Do not change 'I am' to 'Petitioner is'.\n"
        )
        # Available models: gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=system_prompt + f"EXTRACT ATOMIC CLAIMS FROM THIS TEXT:\n\n{narrative_text}"
        )

        raw = response.text
        # Strip markdown code blocks if present
        raw = re.sub(r'```json\s*', '', raw)
        raw = re.sub(r'```\s*$', '', raw)
        raw = raw.strip()

        # Try to parse as JSON (new format); fall back to old line-by-line parsing
        try:
            data = json.loads(raw)
            # Validate expected keys
            if "claims" in data:
                metadata = data.get("metadata", {})
                procedural = data.get("procedural_facts", [])
                claims = data.get("claims", [])
                # Normalize claims to dicts with label/body for downstream compatibility
                for i, c in enumerate(claims, 1):
                    if "id" not in c:
                        c["id"] = i
                    if "text" in c and "body" not in c:
                        c["body"] = c["text"]
                    if "label" not in c:
                        c["label"] = str(c.get("id", i))
                return {
                    "metadata": metadata,
                    "procedural_facts": procedural,
                    "claims": claims
                }
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: old numbered-list parsing
        claims = []
        for line in raw.splitlines():
            line = line.strip()
            match = re.match(r'^(\d+[\.\)\-]|[IVXLC]+[\.\)]|[A-Z][\.\)]|[\-\*\+])\s*(.*)', line, re.DOTALL)
            if match:
                label = match.group(1).strip()
                body = match.group(2).strip()
                if body:
                    claims.append({"id": len(claims)+1, "label": label, "body": body})
            elif line:
                claims.append({"id": len(claims)+1, "label": "-", "body": line})

        return {
            "metadata": {},
            "procedural_facts": [],
            "claims": claims if claims else chunk_claims_smart(narrative_text)
        }

    except Exception as e:
        print(f"  -> Gemini API failed: {e}, using local chunker.")
        return chunk_claims_smart(narrative_text)


def filter_claims(data, excluded_ids=None):
    """
    Filter claims by excluding specific IDs.
    `data` is the parsed dict with 'metadata', 'procedural_facts', 'claims'.
    Returns a new dict with filtered claims (and empty procedural_facts for UI).
    """
    if excluded_ids is None:
        excluded_ids = set()
    else:
        excluded_ids = set(excluded_ids)
    filtered = {
        "metadata": data.get("metadata", {}),
        "procedural_facts": data.get("procedural_facts", []),
        "claims": [c for c in data.get("claims", []) if c.get("id") not in excluded_ids]
    }
    return filtered


def build_response_sheet_html(case_number, motion_title, data, layout="block", used_local=False):
    """
    Generates a printable HTML response sheet with proper print CSS.
    `data` is a dict with 'metadata', 'procedural_facts', and 'claims'.
    `layout`: 'block' = new style with response space (default), 'table' = old style
    Only shows 'substantive' claims by default.
    `used_local`: Boolean indicating if local chunker was used (shows notice if True)
    """
    metadata = data.get("metadata", {})
    procedural = data.get("procedural_facts", [])
    claims = data.get("claims", [])

    # Filter to only substantive claims and re-number sequentially
    # For block layout, show ALL claims (including procedural/contested)
    if layout == "block":
        display_claims = claims  # Show all claims
        filter_note = f"Showing: {len(display_claims)} total claims (all types)"
    else:
        display_claims = [c for c in claims if c.get("type", "substantive") == "substantive"]
        filter_note = f"Showing: {len(display_claims)} substantive claims (filtered from {len(claims)} total)"

    # Re-number claims sequentially for display
    for i, claim in enumerate(display_claims, 1):
        claim["display_id"] = i
        claim["label"] = f"{i}."

    header = metadata.get("case_header", f"{case_number} - {motion_title}" if case_number else motion_title)
    parties = metadata.get("parties", [])
    title = metadata.get("title", motion_title)

    # Use the motion_title passed in (it's already extracted)
    if not title or len(title) < 5:
        title = motion_title

    html = f"""
<html>
<head>
    <meta charset="utf-8">
    <style>
        @media print {{
            @page {{ margin: 0.5in; }}
            body {{-webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .btn-group, .local-notice {{ display: none !important; }}
        }}
        body {{ font-family: sans-serif; margin: 40px; }}
        .header-info {{ background: #f0f0f0; padding: 15px; margin-bottom: 20px; }}
        .procedural {{ margin-bottom: 12px; }}
    </style>
</head>
<body>
    <h1>Response Sheet: {title}</h1>
    <div class="header-info">
        <p><strong>{header}</strong></p>
"""
    if parties:
        html += f"        <p><strong>Parties:</strong> {', '.join(parties)}</p>\n"

    html += f"""        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p><strong>{filter_note}</strong></p>
    </div>
    <hr>
"""

    # Procedural facts as bullets
    if procedural:
        html += """    <h3>Procedural Context</h3>
    <ul class="procedural">
"""
        for fact in procedural:
            # Check if this fact is also a contested claim
            contested_mark = ""
            for claim in claims:
                if claim.get("type") == "contested" and claim.get("text", "") in fact:
                    contested_mark = " (contested)"
                    break
            html += f"        <li>{fact}{contested_mark}</li>\n"
        html += "    </ul>\n    <hr>\n"

    if layout == "table":
        # Add JavaScript for removing rows
        html += """    <script>
        function removeChunk(element) {
            if (confirm('Remove this item?')) {
                element.closest('tr').style.display = 'none';
            }
        }
        </script>
    <style>
        table { width: 100%; border-collapse: collapse; table-layout: fixed; }
        td {
            border: 1px solid #000;
            padding: 12px;
            vertical-align: top;
            width: 50%;
            overflow: hidden;
        }
        .line-column {
            background-image: linear-gradient(#ccc 1px, transparent 1px);
            background-size: 100% 2.5em;
            line-height: 2.5em;
        }
        .label {
            font-size: 0.8em;
            font-weight: bold;
            color: #666;
            margin-bottom: 4px;
        }
        .remove-btn {
            background: #ff4444;
            color: white;
            border: none;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            cursor: pointer;
            font-weight: bold;
            margin-right: 8px;
        }
        .local-notice {
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 10px;
            margin-bottom: 15px;
            border-radius: 4px;
        }
        </style>
    <div class="local-notice">
        <strong>Notice:</strong> This response sheet was generated using the <strong>local script-based chunker</strong> (no LLM used).
        Some items may be form instructions rather than actual claims. Click the <strong>×</strong> button to remove any incorrect entries.
    </div>
    <table>
"""
        # Show ALL claims (including procedural/contested) in table, re-numbered sequentially
        all_claims = claims  # Show all claims, not just substantive

        # Re-number all claims sequentially for display
        for i, claim in enumerate(all_claims, 1):
            claim["display_id"] = i
            claim["label"] = f"{i}."

        for claim in all_claims:
            cid = claim.get("id", "")
            label = claim.get("label", "")
            text = claim.get("text", claim.get("body", ""))
            combined = f"{label} {text}" if label and text else (text or label or "")
            claim_type = claim.get("type", "substantive")

            # Mark contested claims
            contested_mark = " (contested)" if claim_type == "contested" else ""

            html += f"""        <tr data-claim-id="{cid}" data-type="{claim_type}">
            <td>
                <button class="remove-btn" onclick="removeChunk(this)" title="Remove this item">×</button>
                <div class="label">{label}{contested_mark}</div>
                <div>{text}</div>
            </td>
            <td class="line-column">
                &nbsp;<br>&nbsp;<br>&nbsp;<br>&nbsp;<br>&nbsp;<br>&nbsp;<br>
            </td>
        </tr>
"""
        html += "    </table>\n"

    else:
        # BLOCK LAYOUT (new style with response space)
        # Add JavaScript for removing, merging, and splitting chunks
        html += """    <script>
        function removeChunk(element) {
            if (confirm('Remove this item?')) {
                element.closest('.claim-block').style.display = 'none';
            }
        }
        function mergeWithAbove(btn) {
            var block = btn.closest('.claim-block');
            var prev = block.previousElementSibling;
            while (prev && prev.style.display === 'none') prev = prev.previousElementSibling;
            if (!prev || !prev.classList.contains('claim-block')) return alert('No block above to merge with');
            var prevContent = prev.querySelector('.claim-content').innerText;
            var currContent = block.querySelector('.claim-content').innerText;
            prev.querySelector('.claim-content').innerText = prevContent + ' ' + currContent;
            block.style.display = 'none';
            renumberClaims();
        }
        function mergeWithBelow(btn) {
            var block = btn.closest('.claim-block');
            var next = block.nextElementSibling;
            while (next && next.style.display === 'none') next = next.nextElementSibling;
            if (!next || !next.classList.contains('claim-block')) return alert('No block below to merge with');
            var currContent = block.querySelector('.claim-content').innerText;
            var nextContent = next.querySelector('.claim-content').innerText;
            block.querySelector('.claim-content').innerText = currContent + ' ' + nextContent;
            next.style.display = 'none';
            renumberClaims();
        }
        function splitChunk(btn) {
            var block = btn.closest('.claim-block');
            var content = block.querySelector('.claim-content').innerText;
            var splitPoint = prompt('Enter the text to split AFTER (the split point will go to the new second chunk):', content.substring(Math.floor(content.length/2)));
            if (!splitPoint || !content.includes(splitPoint)) return;
            var idx = content.indexOf(splitPoint);
            var part1 = content.substring(0, idx + splitPoint.length).trim();
            var part2 = content.substring(idx + splitPoint.length).trim();
            if (!part1 || !part2) return alert('Cannot split - not enough content');
            block.querySelector('.claim-content').innerText = part1;
            var newBlock = block.cloneNode(true);
            newBlock.querySelector('.claim-content').innerText = part2;
            newBlock.style.display = '';
            block.parentNode.insertBefore(newBlock, block.nextSibling);
            renumberClaims();
        }
        function renumberClaims() {
            var blocks = document.querySelectorAll('.claim-block:not([style*="display: none"])');
            blocks.forEach(function(block, i) {
                var num = i + 1;
                block.querySelector('.claim-header').innerText = 'Claim ' + num + '.';
            });
        }
        function markContested(btn) {
            var block = btn.closest('.claim-block');
            var currentType = block.getAttribute('data-type') || 'substantive';
            var newType = 'contested';
            block.setAttribute('data-type', newType);
            var header = block.querySelector('.claim-header');
            if (!header.innerText.includes('(contested)')) {
                header.innerText = header.innerText + ' (contested)';
            }
        }
        function changeType(btn) {
            var block = btn.closest('.claim-block');
            var currentType = block.getAttribute('data-type') || 'substantive';
            var newType = prompt('Enter new type (substantive, procedural, contested):', currentType);
            if (!newType || !['substantive', 'procedural', 'contested'].includes(newType)) return;
            block.setAttribute('data-type', newType);
            var header = block.querySelector('.claim-header');
            header.innerText = header.innerText.replace(/\(.*\)/, '') + (newType === 'contested' ? ' (contested)' : '');
        }
        </script>
        <style>
        @media print {
            .btn-group, .local-notice { display: none !important; }
        }
        .claim-block {
            border: 1px solid #000;
            margin-bottom: 20px;
            page-break-inside: avoid;
            position: relative;
        }
        .claim-header {
            background: #e0e0e0;
            padding: 8px 12px;
            font-weight: bold;
            border-bottom: 1px solid #000;
        }
        .btn-group {
            position: absolute;
            top: 5px;
            right: 10px;
        }
        .remove-btn, .merge-btn, .split-btn {
            background: #ff4444;
            color: white;
            border: none;
            border-radius: 3px;
            padding: 2px 6px;
            cursor: pointer;
            font-size: 0.8em;
            margin-left: 3px;
        }
        .merge-btn {
            background: #ffa500;
        }
        .split-btn {
            background: #007bff;
        }
        .claim-content {
            padding: 12px;
            border-bottom: 1px solid #000;
        }
        .response-section {
            padding: 12px;
        }
        .response-label {
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
        }
        .response-lines {
            background-image: linear-gradient(#ccc 1px, transparent 1px);
            background-size: 100% 2.5em;
            line-height: 2.5em;
            min-height: 10em;
        }
        .local-notice {
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 10px;
            margin-bottom: 15px;
            border-radius: 4px;
        }
        @media print {
            .local-notice, .btn-group { display: none !important; }
        }
    </style>
"""
        # Add local chunker notice if applicable
        if used_local:
            html += """    <div class="local-notice">
            <strong>Notice:</strong> This response sheet was generated using the <strong>local script-based chunker</strong> (no LLM used).
            Some items may be form instructions rather than actual claims. Click the <strong>×</strong> button to remove any incorrect entries.
        </div>
"""

        for claim in display_claims:
            cid = claim.get("id", "")
            label = claim.get("label", str(claim.get("display_id", "")))
            text = claim.get("text", claim.get("body", ""))
            combined = f"{label} {text}" if label and text else (text or label or "")
            claim_type = claim.get("type", "substantive")
            contested_mark = " (contested)" if claim_type == "contested" else ""

            html += f"""
    <div class="claim-block" data-claim-id="{cid}" data-type="{claim_type}">
        <div class="btn-group">
            <button class="remove-btn" onclick="removeChunk(this)" title="Remove this item">×</button>
            <button class="merge-btn" onclick="mergeWithAbove(this)" title="Merge with above">↑ Merge</button>
            <button class="merge-btn" onclick="mergeWithBelow(this)" title="Merge with below">↓ Merge</button>
            <button class="split-btn" onclick="splitChunk(this)" title="Split this chunk">✂ Split</button>
            <button class="split-btn" onclick="changeType(this)" title="Change claim type" style="background: #28a745;">Type</button>
            <button class="split-btn" onclick="markContested(this)" title="Mark as contested" style="background: #dc3545;">Mark Contested</button>
        </div>
        <div class="claim-header">Claim {label}{contested_mark}</div>
        <div class="claim-content">{combined}</div>
        <div class="response-section">
            <div class="response-label">Your Response / Counter-Statement:</div>
            <div class="response-lines">
                &nbsp;<br>
                &nbsp;<br>
                &nbsp;<br>
                &nbsp;<br>
            </div>
        </div>
    </div>
"""

    html += """</body>
</html>
"""
    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_response_sheet(file_path, output_path=None, state_code="IL", layout="block", force_local=False):
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get state-specific rules
    rules = StateRuleRegistry.get_rules(state_code)

    # 1. Tiered extraction using StateRuleRegistry
    print(f"Extracting content from {file_path} (State: {state_code}) ...")
    narrative_text, form_data = extract_content_smart(file_path, state_code)

    if not narrative_text or not narrative_text.strip():
        raise ValueError("Could not extract any narrative text from the file.")

    print(f"  -> Narrative length: {len(narrative_text)} chars")

    # 2. Extract case number and motion title using state-specific patterns
    case_number = ""
    motion_title = ""

    # For PDFs with form data, extract from form fields
    if form_data:
        for key, value in form_data.items():
            if rules["case_pattern"].search(key):
                case_number = str(value).strip()
            if rules["title_pattern"].search(key):
                motion_title = str(value).strip()

    # For markdown files or PDFs without form data, try regex extraction
    if not case_number:
        # Pattern for IL: 4-digit year + 2 letters + 6-12 digits (e.g., 2025FA000152)
        case_match = re.search(r'\b(\d{2,4}[A-Z]{2}\d{5,12})\b', narrative_text)
        if case_match:
            case_number = case_match.group(1)

    # Extract title from narrative text using state-specific patterns
    if not motion_title:
        # For IL: Look for the actual motion title in the document
        # Known title: "MOTION TO Relocate MINOR CHILD AND MODIFY PARENTING SCHEDULE"

        # Search for the exact title from the IL form
        il_title = re.search(
            r'(?:MOTION\s+TO\s+)?(Relocate\s+MINOR\s+CHILD\s+AND\s+MODIFY\s+PARENTING\s+SCHEDULE)',
            narrative_text,
            re.IGNORECASE
        )
        if il_title:
            motion_title = il_title.group(1).strip().upper()

        # For other states, use config patterns
        if not motion_title:
            title_patterns = get_title_patterns(state_code)
            for pattern in title_patterns:
                match = re.search(pattern, narrative_text, re.IGNORECASE)
                if match:
                    motion_title = match.group(0).strip()
                    break

    # Special: For IL forms, look for "MOTION TO..." in all caps (from form field)
    if not motion_title or len(motion_title) < 10:
        # Search for all-caps title with "MOTION" or "PETITION"
        all_caps_pattern = re.search(
            r'(?:MOTION|PETITION)\s+TO\s+[A-Z][A-Z\s]{10,}(?:AND\s+[A-Z\s]+)?',
            narrative_text
        )
        if all_caps_pattern:
            motion_title = all_caps_pattern.group(0).strip()

    # If still not found, look for the exact pattern from the form
    if not motion_title or len(motion_title) < 10:
        exact_pattern = re.search(
            r'(RELOCATE\s+MINOR\s+CHILD\s+AND\s+MODIFY\s+PARENTING\s+SCHEDULE)',
            narrative_text,
            re.IGNORECASE
        )
        if exact_pattern:
            motion_title = exact_pattern.group(1).strip().upper()

    # Fallback: use filename (remove underscores, title case)
    if not motion_title:
        motion_title = file_path.stem.replace("_", " ").title()

    # Fallback: extract from the first substantive claim or use filename
    if not motion_title:
        # Try to find a title in the first few lines of narrative
        lines = narrative_text.split('\n')[:10]
        for line in lines:
            line = line.strip()
            if len(line) > 10 and not line[0].isdigit() and 'case' not in line.lower():
                motion_title = line
                break

    if not motion_title:
        motion_title = file_path.stem.replace("_", " ").title()

    # 3. Chunk claims with LLM
    llm_result = {"metadata": {}, "procedural_facts": [], "claims": []}
    if force_local:
        print("  -> Forcing local chunker (--local flag)")
        llm_result = chunk_claims_with_llm(None, narrative_text)
    elif os.environ.get("GEMINI_API_KEY"):
        try:
            client = get_llm_client()
            print("  -> Chunking claims with LLM...")
            llm_result = chunk_claims_with_llm(client, narrative_text)
        except Exception as e:
            print(f"  -> LLM unavailable ({e}), using local splitter.")
            llm_result = chunk_claims_with_llm(None, narrative_text)
    else:
        print("  -> No GEMINI_API_KEY, using local sentence-splitter.")
        llm_result = chunk_claims_with_llm(None, narrative_text)

    claims = llm_result.get("claims", [])
    procedural_facts = llm_result.get("procedural_facts", [])
    
    # Load blank form lines ONCE for cleaning
    blank_lines = load_blank_form_text(state_code)
    if blank_lines:
        print(f"  -> Loaded {len(blank_lines)} blank form lines for cleaning")
    
    # Clean each claim text to remove embedded boilerplate
    for claim in claims:
        text = claim.get("text", claim.get("body", ""))
        cleaned = clean_claim_text(text, blank_lines)
        if text != cleaned:
            print(f"  -> Cleaned claim {claim.get('id', '?')}: '{text[:50]}...' -> '{cleaned[:50]}...'")
        if "text" in claim:
            claim["text"] = cleaned
        if "body" in claim:
            claim["body"] = cleaned
    
    # Clean procedural facts too
    cleaned_facts = []
    for fact in procedural_facts:
        cleaned = clean_claim_text(fact, blank_lines)
        if fact != cleaned:
            print(f"  -> Cleaned procedural fact: '{fact[:50]}...'")
        if cleaned:  # Only keep non-empty after cleaning
            cleaned_facts.append(cleaned)
    llm_result["procedural_facts"] = cleaned_facts

    print(f"  -> Extracted {len(claims)} claim(s), {len(cleaned_facts)} procedural facts")

    # Track if local chunker was used
    used_local = False
    if not llm_result.get("metadata", {}).get("source") == "llm":
        used_local = True

    # 4. Build JSON metadata for timeline readiness (machine-readable)
    # Add motion_title to llm_result metadata so it's available in HTML
    if "metadata" not in llm_result:
        llm_result["metadata"] = {}
    llm_result["metadata"]["title"] = motion_title
    llm_result["metadata"]["case_header"] = f"{case_number} - {motion_title}" if case_number else motion_title
    llm_result["metadata"]["used_local"] = used_local

    json_metadata = {
        "source_file": str(file_path),
        "case_number": case_number,
        "motion_title": motion_title,
        "state_code": state_code,
        "metadata": llm_result.get("metadata", {}),
        "procedural_facts": llm_result.get("procedural_facts", []),
        "claims": []
    }
    for claim_dict in claims:
        text = claim_dict.get("text", claim_dict.get("body", ""))
        label = claim_dict.get("label", "")
        if label and text.startswith(label):
            text = text[len(label):].strip()
        dates = extract_dates(text)
        json_metadata["claims"].append({
            "id": claim_dict.get("id"),
            "text": text,
            "type": claim_dict.get("type", "substantive"),
            "dates": dates,
        })

    # 5. Generate HTML response sheet (printable)
    html = build_response_sheet_html(case_number, motion_title, llm_result, layout, used_local=used_local)

    # 6. Write SEPARATE outputs (JSON for machine, HTML for human)
    base_path = Path(output_path).with_suffix("") if output_path else file_path.with_suffix("")

    # JSON file (machine-readable, for timeline tool)
    json_path = f"{base_path}.response_sheet.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_metadata, f, indent=2, ensure_ascii=False)
    print(f"JSON metadata written to: {json_path}")

    # HTML file (printable)
    html_path = f"{base_path}.response_sheet.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML response sheet written to: {html_path}")

    return html_path


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run scripts/generate_response_sheet.py <input_file> [output_md] [state_code] [--layout=block|table] [--local]")
        print("\nConverts a legal PDF or Markdown file into a printable Response Sheet.")
        print("Or mark executable and run directly: ./scripts/generate_response_sheet.py <input_file>")
        print("\nSupported states: IL (Illinois), CA (California), or DEFAULT (universal)")
        print("Supported file types: .pdf, .md")
        print("\nLayout options:")
        print("  --layout=block   : Block style with response writing space (default)")
        print("  --layout=table   : Table style with two columns")
        print("\nChunker options:")
        print("  --local           : Force local chunker (skip LLM API)")
        sys.exit(1)

    file_path = None
    output_path = None
    state_code = "IL"
    layout = "block"
    force_local = False

    # Parse arguments
    for arg in sys.argv[1:]:
        if arg.startswith("--layout="):
            layout = arg.split("=")[1]
        elif arg == "--local":
            force_local = True
        elif arg.startswith("--"):
            print(f"Unknown option: {arg}")
            sys.exit(1)
        elif file_path is None:
            file_path = arg
        elif not arg.isalpha() and output_path is None:
            output_path = arg
        elif state_code == "IL":
            state_code = arg

    if file_path is None:
        print("Error: No input file specified")
        sys.exit(1)

    try:
        out = generate_response_sheet(file_path, output_path, state_code, layout, force_local)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
