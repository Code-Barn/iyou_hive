#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pdfplumber",
#     "google-generativeai",
#     "python-dotenv",
#     "PyMuPDF",
#     "pytesseract",
#     "Pillow",
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

load_dotenv()

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
    import google.genai as genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return client


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
        
        # 2. IF PRIORITY FIELDS ARE EMPTY: Grab anything large (>100 chars)
        # This prevents the "0 claims" error on non-standard forms
        if not found_priority:
            for name, val in form_data.items():
                if len(str(val)) > 100 and not any(term in name for term in ["Header", "Court", "Name"]):
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
    """
    # Pattern matches: I., II., A., B., 1., 1), etc. at the start of a line
    pattern = r'\n\s*(?=[IXVLC]+[\.\)]|[A-Z][\.\)]|\d+[\.\)])'
    
    # Split the text into blocks based on these markers (prepend \n to catch first marker)
    raw_chunks = re.split(pattern, "\n" + narrative_text)
    
    # Items to exclude from the final response sheet
    BLOCKLIST = [
        "PROOF OF DELIVERY", "CERTIFICATE OF SERVICE", 
        "Attorney Number", "Law Firm", "EFSP", 
        "Street, Apt. #", "City State Zip Code",
        "Instructions", "icourts.info", "ATJ 801.7"
    ]
    
    processed_claims = []
    for chunk in raw_chunks:
        chunk = chunk.strip()
        if not chunk or len(chunk) < 10:
            continue
            
        # SKIP chunks that look like contact info or service proofs
        # Only skip if the chunk STARTS WITH or IS MAINLY boilerplate
        chunk_upper = chunk.upper()
        if any(term.upper() in chunk_upper for term in BLOCKLIST):
            # Only skip small chunks (<200 chars) that are purely boilerplate
            if len(chunk) < 200:
                continue
            # For larger chunks, just remove the boilerplate lines
            lines = chunk.split('\n')
            filtered_lines = [line for line in lines if not any(term in line for term in BLOCKLIST)]
            chunk = '\n'.join(filtered_lines).strip()
            if len(chunk) < 10:
                continue

        # Check if the first line is a short "Heading" (e.g., "I. BACKGROUND")
        lines = chunk.split('\n', 1)
        if len(lines) > 1 and len(lines[0]) < 50:
            # Separate the label/heading from the body text
            processed_claims.append({"label": lines[0].strip(), "body": lines[1].strip()})
        else:
            processed_claims.append({"label": "", "body": chunk})
    
    # FALLBACK: If all chunks were filtered out, use double-newline splitting
    if not processed_claims:
        print("  -> All chunks filtered, falling back to double-newline split...")
        blocks = re.split(r'\n\s*\n', narrative_text)
        processed_claims = [{"label": "", "body": b.strip()} for b in blocks if len(b.strip()) > 10]
    
    # FINAL FALLBACK: If STILL empty, treat entire text as one claim
    if not processed_claims and narrative_text.strip():
        print("  -> No chunks created, using entire text as single claim...")
        processed_claims = [{"label": "", "body": narrative_text.strip()}]
    
    return processed_claims


def chunk_claims_with_llm(client, narrative_text):
    """
    Refined atomic parser that strips form boilerplates and
    breaks down dense narratives into single factual points.
    Uses LLM if client is available, otherwise falls back to smart chunking.
    Returns a list of dicts with 'label' and 'body' keys.
    """
    # No LLM client - use smart chunking with legal markers
    if client is None:
        print("  -> No LLM client: Using smart chunking.")
        return chunk_claims_smart(narrative_text)

    # LLM available - attempt semantic chunking
    system_instruction = (
        "You are a legal document analyst. Your goal is to extract 'Atomic Factual Allegations'.\n"
        "1. IGNORE all standard form instructions, page numbers, and court headers.\n"
        "2. IDENTIFY every distinct factual claim, event, or legal request.\n"
        "3. PRESERVE all dates, names, and specific statutory citations (e.g., 750 ILCS 5/609.2).\n"
        "4. ATOMICITY: Each point must be a single fact. If a paragraph contains three reasons for a move, create three separate numbered items.\n"
        "5. OUTPUT: Return ONLY a numbered list. No intro or outro text."
    )

    prompt = f"EXTRACT ATOMIC CLAIMS FROM THIS TEXT:\n\n{narrative_text}"

    try:
        # Using the system_instruction parameter ensures the LLM stays on task
        result = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={'system_instruction': system_instruction}
        )

        raw = result.text if hasattr(result, 'text') else str(result)

        # Parse into dict format with label/body
        claims = []
        for line in raw.splitlines():
            line = line.strip()
            # Matches "1.", "1)", "I.", "A.", or "- " at the start of a line
            match = re.match(r'^(\d+[\.\)\-]|[IVXLC]+[\.\)]|[A-Z][\.\)]|[\-\*\+])\s*(.*)', line, re.DOTALL)
            if match:
                label = match.group(1).strip()
                body = match.group(2).strip()
                if body:
                    claims.append({"label": label, "body": body})
                elif label:
                    claims.append({"label": label, "body": ""})
        
        # If no structured claims found, treat entire text as one claim
        if not claims:
            claims.append({"label": "", "body": raw.strip()})
            
        return claims
    except Exception as e:
        print(f"  -> LLM parsing failed: {e}")
        # Fallback to smart chunking
        return chunk_claims_smart(narrative_text)


def build_response_sheet_markdown(case_number, motion_title, claims, json_metadata):
    """
    Generates a high-clearance two-column Markdown table.
    The right column is prepopulated with space for manual entry.
    """
    lines = []

    # Keep JSON metadata for the timeline tool
    lines.append("```json")
    lines.append(json.dumps(json_metadata, indent=2, ensure_ascii=False))
    lines.append("```\n")

    # Header with clear visual separation
    lines.append(f"# Response Sheet: {motion_title}")
    lines.append(f"**Case Number:** {case_number or 'N/A'}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("\n---\n")

    # HTML Table for strict 50/50 split layout with discrete labels
    lines.append('<table style="width: 100%; table-layout: fixed; border-collapse: collapse;">')
    
    for claim in claims:
        # 'claim' is now a dict with 'label' and 'body'
        label = claim.get("label", "")
        body = claim.get("body", "")

        lines.append('  <tr style="border-bottom: 2px solid #444;">')
        
        # LEFT: Allegation with a discrete label
        lines.append('    <td style="width: 50%; vertical-align: top; padding: 10px; border-right: 1px solid #000;">')
        if label:
            lines.append(f'      <div style="font-size: 0.8em; color: #666; margin-bottom: 5px; font-weight: bold;">{label}</div>')
        lines.append(f'      <div style="line-height: 1.4;">{body}</div>')
        lines.append('    </td>')
        
        # RIGHT: Blank Writing Lines
        writing_style = "background-image: linear-gradient(#ccc 1px, transparent 1px); background-size: 100% 2em; line-height: 2em;"
        lines.append(f'    <td style="width: 50%; vertical-align: top; padding: 10px; {writing_style}">')
        # Ensure at least 6 lines of writing space regardless of claim length
        lines.append('&nbsp;<br>' * 6)
        lines.append('    </td>')
        lines.append('  </tr>')
    
    lines.append('</table>')
    return "\n".join(lines)


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

    # 4. Build JSON metadata for timeline readiness
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

    # 5. Generate Markdown
    md = build_response_sheet_markdown(case_number, motion_title, claims, json_metadata)

    # 6. Write output
    if output_path is None:
        output_path = Path(pdf_path).with_suffix(".response_sheet.md")
    os.makedirs(Path(output_path).parent or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Response sheet written to: {output_path}")
    return output_path


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
