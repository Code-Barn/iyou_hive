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
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import pdfplumber

# Load .env from project root (parent of scripts/)
load_dotenv(Path(__file__).parent.parent / '.env')

import pdfplumber

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


def extract_content_smart(pdf_path, state_code="IL"):
    """
    Tiered extraction:
    1. Form Fields (using state rules)
    2. Digital Text (pdfplumber)
    3. OCR (pytesseract)

    For fillable forms, strictly extract ONLY from narrative fields (txtMotion,
    txtAdditionalExplanation) and ignore all other form fields.
    """
    rules = StateRuleRegistry.get_rules(state_code)
    narrative_text = ""
    form_data = {}
    is_fillable_form = False

    # Step1: Try Form Field Metadata
    try:
        with pdfplumber.open(pdf_path) as pdf:
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

    # HYBRID EXTRACTION: Priority First, then Adaptive Fallback
    if form_data:
        # 1. Try high-priority narrative fields first
        priority_patterns = [
            re.compile(r'txtMotion', re.I),
            re.compile(r'txtAdditionalExplanation', re.I),
            re.compile(r'topmostSubform.*txtMotion', re.I),
            re.compile(r'topmostSubform.*txtAdditionalExplanation', re.I),
        ]

        found_priority = False
        for name, val in form_data.items():
            for pat in priority_patterns:
                if pat.search(name) and val.strip():
                    narrative_text += f"\n{val}"
                    found_priority = True
                    break

        # 2. IF PRIORITY FIELDS ARE EMPTY: Grab anything substantial (>50 chars)
        # This prevents the "0 claims" error on non-standard forms
        if not found_priority:
            for name, val in form_data.items():
                if len(str(val)) > 50 and not any(term in name for term in ["Header", "Court", "Name"]):
                    narrative_text += f"\n{val}"

    # FINAL FALLBACK: If still no narrative, grab ALL form fields with content
    if not narrative_text.strip():
        print("  -> No priority fields found, grabbing all form fields...")
        for name, val in form_data.items():
            if val and str(val).strip():
                narrative_text += f"\n{val}"

    # Step 2: If no narrative from fields, check if scanned or digital
    if not narrative_text.strip():
        if is_scanned_pdf(pdf_path):
            print(f"  -> {state_code}: Scanned PDF detected. Running Tesseract...")
            narrative_text = ocr_pdf_images(pdf_path)
        else:
            print(f"  -> {state_code}: Digital PDF detected. Extracting raw text...")
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    narrative_text = "\n".join([p.extract_text() or "" for p in pdf.pages])
            except Exception:
                pass

    # Clean legal artifacts (e.g., underscores from fill-in blanks)
    narrative_text = clean_legal_artifacts(narrative_text)

    return narrative_text, form_data


def chunk_claims_smart(narrative_text):
    """
    Smart chunking logic that handles Roman numerals (I, II, III), Capital letters (A, B, C),
    and Numbers (1, 2, 3) as legal markers. Identifies labels and body text for each claim.
    Filters out boilerplate sections common in Illinois forms.
    Includes section header detection and sentence splitting for robustness.
    """
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
            # Filter boilerplate
            if any(pat.search(chunk) for pat in BLOCKLIST_PATTERNS):
                continue
            # Check if first line is a label
            lines = chunk.split('\n', 1)
            if len(lines) > 1 and len(lines[0]) < 50:
                processed_claims.append({"label": lines[0].strip(), "body": lines[1].strip()})
            else:
                processed_claims.append({"label": "", "body": chunk})

    # Approach 2: If no markers found, try section headers
    if not processed_claims:
        has_section = any(pat.search(narrative_text) for pat in SECTION_PATTERNS)
        if has_section:
            section_splits = re.split(r'\n(?=(?:BACKGROUND|ALLEGATIONS|FACTS|ARGUMENT|RELIEF|COUNT|First|Second|Third|Fourth|Fifth|Sixth))', narrative_text, flags=re.I)
            for sect in section_splits:
                sect = sect.strip()
                if len(sect) > 50:
                    if any(pat.search(sect) for pat in BLOCKLIST_PATTERNS):
                        continue
                    sect_lines = sect.split('\n', 1)
                    if len(sect_lines) > 1 and len(sect_lines[0]) < 50:
                        processed_claims.append({"label": sect_lines[0].strip(), "body": sect_lines[1].strip()})
                    else:
                        processed_claims.append({"label": "", "body": sect})

    # Approach 3: For long text without markers, split by sentences (Option 1)
    if not processed_claims and len(narrative_text) > 500:
        # Split by sentence endings (period + space + capital letter)
        sentences = re.split(r'(?<!\d)\.\s+(?=[A-Z])', narrative_text)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 30:
                if not sent.endswith('.'):
                    sent += '.'
                processed_claims.append({"label": "", "body": sent})

    # Approach 4: Double-newline splitting
    if not processed_claims:
        print("  -> No markers found, splitting by double newlines...")
        blocks = re.split(r'\n\s*\n', narrative_text)
        processed_claims = [{"label": "", "body": b.strip()} for b in blocks if len(b.strip()) > 30]

    # FINAL FALLBACK: Use entire text as one claim (Option 3)
    if not processed_claims and narrative_text.strip():
        print("  -> No chunks created, using entire text as single claim...")
        processed_claims = [{"label": "", "body": narrative_text.strip()}]

    return processed_claims


import requests
import os
import re

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
            "You are a legal document analyst. Your goal is to extract 'Atomic Factual Allegations'.\n"
            "1. IGNORE all standard form instructions, page numbers, and court headers.\n"
            "2. IDENTIFY every distinct factual claim, event, or legal request.\n"
            "3. PRESERVE all dates, names, and specific statutory citations.\n"
            "4. ATOMICITY: Each point must be a single fact. If a paragraph contains multiple reasons, split them.\n"
            "5. OUTPUT: Return ONLY a numbered list. No intro or outro text.\n\n"
        )
        # Available models: gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=system_prompt + f"EXTRACT ATOMIC CLAIMS FROM THIS TEXT:\n\n{narrative_text}"
        )
        
        raw = response.text
        claims = []
        for line in raw.splitlines():
            line = line.strip()
            match = re.match(r'^(\d+[\.\)\-]|[IVXLC]+[\.\)]|[A-Z][\.\)]|[\-\*\+])\s*(.*)', line, re.DOTALL)
            if match:
                label = match.group(1).strip()
                body = match.group(2).strip()
                if body:
                    claims.append({"label": label, "body": body})
            elif line:
                claims.append({"label": "-", "body": line})
        
        return claims if claims else chunk_claims_smart(narrative_text)
        
    except Exception as e:
        print(f"  -> Gemini API failed: {e}, using local chunker.")
        return chunk_claims_smart(narrative_text)


def build_response_sheet_html(case_number, motion_title, claims):
    """
    Generates a printable HTML response sheet with proper print CSS.
    Separates JSON metadata from printable output.
    """
    html = f"""
<html>
<head>
    <meta charset="utf-8">
    <style>
        @media print {{
            @page {{ margin: 0.5in; }}
            body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        }}
        body {{ font-family: sans-serif; margin: 40px; }}
        table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
        td {{
            border: 1px solid #000;
            padding: 12px;
            vertical-align: top;
            width: 50%;
            overflow: hidden;
        }}
        .line-column {{
            background-image: linear-gradient(#ccc 1px, transparent 1px);
            background-size: 100% 2.5em;
            line-height: 2.5em;
        }}
        .label {{
            font-size: 0.8em;
            font-weight: bold;
            color: #666;
            margin-bottom: 4px;
        }}
    </style>
</head>
<body>
    <h1>Response Sheet: {motion_title}</h1>
    <p><strong>Case Number:</strong> {case_number or 'N/A'}</p>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    <hr>
    <table>
"""

    for claim in claims:
        label = claim.get("label", "")
        body = claim.get("body", "")
        html += f"""
        <tr>
            <td>
                <div class="label">{label}</div>
                <div>{body}</div>
            </td>
            <td class="line-column">
                &nbsp;<br>&nbsp;<br>&nbsp;<br>&nbsp;<br>&nbsp;<br>&nbsp;<br>
            </td>
        </tr>
"""

    html += """
    </table>
</body>
</html>
"""
    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_response_sheet(pdf_path, output_path=None, state_code="IL"):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Get state-specific rules
    rules = StateRuleRegistry.get_rules(state_code)

    # 1. Tiered extraction using StateRuleRegistry
    print(f"Extracting content from {pdf_path} (State: {state_code}) ...")
    narrative_text, form_data = extract_content_smart(pdf_path, state_code)

    if not narrative_text or not narrative_text.strip():
        raise ValueError("Could not extract any narrative text from the PDF.")

    print(f"  -> Narrative length: {len(narrative_text)} chars")

    # 2. Extract case number and motion title using state-specific patterns
    case_number = ""
    motion_title = ""
    for key, value in form_data.items():
        if rules["case_pattern"].search(key):
            case_number = str(value).strip()
        if rules["title_pattern"].search(key):
            motion_title = str(value).strip()
    if not motion_title:
        motion_title = Path(pdf_path).stem.replace("_", " ").title()

    # Last Resort Regex for Scanned/Flattened PDFs (Illinois case numbers)
    if not case_number:
        # Pattern for IL: 4-digit year + 2 letters + 6-12 digits (e.g., 2025FA000152)
        # or 2-digit year + 2 letters + digits (e.g., 25FA152)
        case_match = re.search(r'\b(\d{2,4}[A-Z]{2}\d{5,12})\b', narrative_text)
        if case_match:
            case_number = case_match.group(1)

    # 3. Chunk claims with LLM
    claims = []
    if os.environ.get("GEMINI_API_KEY"):
        try:
            client = get_llm_client()
            print("  -> Chunking claims with LLM ...")
            claims = chunk_claims_with_llm(client, narrative_text)
        except Exception as e:
            print(f"  -> LLM unavailable ({e}), using local splitter.")
            claims = chunk_claims_with_llm(None, narrative_text)
    else:
        print("  -> No GEMINI_API_KEY, using local sentence-splitter.")
        claims = chunk_claims_with_llm(None, narrative_text)

    print(f"  -> Extracted {len(claims)} claim(s)")

    # 4. Build JSON metadata for timeline readiness (machine-readable)
    json_metadata = {
        "source_pdf": str(pdf_path),
        "case_number": case_number,
        "motion_title": motion_title,
        "state_code": state_code,
        "claims": []
    }
    for claim_dict in claims:
        # Pass just the text body to the date extractor, not the whole dict
        body_text = claim_dict.get("body", "")
        # Combine label and body for the text field
        label = claim_dict.get("label", "")
        text = f"{label} {body_text}".strip() if label else body_text
        dates = extract_dates(body_text)

        json_metadata["claims"].append({
            "text": text,
            "dates": dates,
        })

    # 5. Generate HTML response sheet (printable)
    html = build_response_sheet_html(case_number, motion_title, claims)

    # 6. Write SEPARATE outputs (JSON for machine, HTML for human)
    base_path = Path(output_path).with_suffix("") if output_path else Path(pdf_path).with_suffix("")

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
        print("Usage: uv run scripts/generate_response_sheet.py <input_pdf> [output_md] [state_code]")
        print("\nConverts a legal PDF into a printable two-column Response Sheet.")
        print("Or mark executable and run directly: ./scripts/generate_response_sheet.py <input_pdf>")
        print("\nSupported states: IL (Illinois), CA (California), or DEFAULT (universal)")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].isalpha() else None
    state_code = sys.argv[3] if len(sys.argv) > 3 else (sys.argv[2] if len(sys.argv) > 2 and sys.argv[2].isalpha() else "IL")

    try:
        out = generate_response_sheet(pdf_path, output_path, state_code)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
