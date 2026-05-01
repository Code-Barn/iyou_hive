#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pdfplumber",
#     "python-dotenv",
#     "PyMuPDF",
#     "google-genai>=1.74.0",
# ]
# ///

"""
Hiver Legal Response Sheet Generator

Converts a filled-out Illinois legal PDF (Motion, Additional Page, etc.) into a
printable two-column "Response Sheet" for factual rebuttal.
"""

import os
import re
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / '.env')

# Import shared utilities
from legal_utils import (
    is_readable, clean_legal_artifacts, extract_form_fields,
    scrub_boilerplate, extract_metadata, extract_dates,
    load_blank_form_text, is_form_instruction, clean_claim_text,
    extract_text_from_pdf, split_text_into_sentences
)

# Import specialized form handling
try:
    import sys
    from pathlib import Path
    scripts_dir = Path(__file__).parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from form_detector import split_combined_form, extract_user_input_from_section
    FORM_TOOLS_AVAILABLE = True
    print("  -> Form tools loaded")
except ImportError as e:
    print(f"  -> Form tools not available: {e}")
    FORM_TOOLS_AVAILABLE = False


# ---------------------------------------------------------------------------
# State-Specific Rule Registry (For Non-IL fallback)
# ---------------------------------------------------------------------------

class StateRuleRegistry:
    @staticmethod
    def get_rules(state_code="IL"):
        registry = {
            "IL": {
                "case_pattern": re.compile(r'case\s*number|case\s*no', re.I),
                "title_pattern": re.compile(r'motion.*title|title.*motion|document\s*title', re.I)
            },
            "DEFAULT": {
                "case_pattern": re.compile(r'case', re.I),
                "title_pattern": re.compile(r'title', re.I)
            }
        }
        return registry.get(state_code.upper(), registry["DEFAULT"])


# ---------------------------------------------------------------------------
# Extraction Logic
# ---------------------------------------------------------------------------

def extract_content_smart(file_path, state_code="IL"):
    """
    Tiered extraction using specialized form tools or raw extraction.
    Returns: (narrative_text, raw_text, form_data)
    """
    file_path = Path(file_path)
    text = ""
    raw_text = ""
    form_data = {}

    # Always get raw text first (for metadata extraction)
    try:
        if file_path.suffix.lower() == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
        else:
            raw_text = extract_text_from_pdf(file_path)
            form_data = extract_form_fields(str(file_path))
    except Exception as e:
        print(f"  -> Error reading file: {e}")
        return "", "", {}

    # Try form tools to extract user input (best for IL forms)
    if FORM_TOOLS_AVAILABLE:
        try:
            sections = split_combined_form(raw_text, state_code)
            user_texts = []
            for section in sections:
                user_text = extract_user_input_from_section(section['text'], section['form_type'], state_code)
                if user_text:
                    user_texts.append(user_text)

            if user_texts:
                text = '\n\n'.join(user_texts)
        except Exception as e:
            print(f"  -> Form tools failed: {e}")

    # Fallback to raw text if form tools didn't extract anything
    if not text.strip():
        text = raw_text

    # Clean and return
    text = scrub_boilerplate(text)
    text = clean_legal_artifacts(text)
    return text, raw_text, form_data


# ---------------------------------------------------------------------------
# Chunker Logic
# ---------------------------------------------------------------------------

def chunk_claims_smart(narrative_text, state_code="IL"):
    """
    Local claim chunker that splits text into atomic claims.
    Fully atomizes text into individual sentences (one fact per claim).
    """
    blank_lines = load_blank_form_text(state_code)

    # Pre-clean the narrative
    narrative_text = clean_claim_text(narrative_text, blank_lines)

    # Split entire narrative into atomic sentences
    sentences = split_text_into_sentences(narrative_text)

    # Convert sentences to claims
    processed_claims = []
    for i, sent in enumerate(sentences):
        if len(sent) < 15 or is_form_instruction(sent, blank_lines):
            continue

        # Categorize
        claim_type = "substantive"
        procedural_keywords = [
            'filed', 'accepted', 'case number', 'served', 'notice',
            'venue', 'jurisdiction', 'summons', 'attached', 'entered',
            'approved', 'granted', 'denied', 'dismissed', 'continued',
            'scheduled', 'postponed', 'heard', 'ruled', 'ordered',
            'court date', 'hearing date', 'trial date', 'appearance',
            'summons', 'subpoena', 'process server', 'proof of service',
            'certificate of service', 'clerk', 'judge', 'magistrate'
        ]
        if any(kw in sent.lower() for kw in procedural_keywords):
            claim_type = "procedural"

        processed_claims.append({
            "id": i + 1,
            "label": f"{i+1}.",
            "text": sent,
            "type": claim_type,
            "body": sent
        })

    # Build result
    procedural_facts = [c["text"] for c in processed_claims if c["type"] == "procedural"]

    return {
        "metadata": extract_metadata(narrative_text, state_code),
        "procedural_facts": list(dict.fromkeys(procedural_facts)),
        "claims": processed_claims
    }


def chunk_claims_with_llm(client, narrative_text, state_code="IL"):
    """
    Use Gemini to extract atomic claims with strict verbatim requirements.
    """
    if not client:
        return chunk_claims_smart(narrative_text, state_code)

    system_prompt = (
        "You are a legal document analyst. Extract ATOMIC claims from legal narratives.\n"
        "STRICT INSTRUCTIONS:\n"
        "1. VERBATIM: Reproduce EXACT wording. NO paraphrasing. NO summarizing.\n"
        "2. ATOMIZE: Each individual factual allegation must be its own object.\n"
        "3. CATEGORIZE: Use 'substantive' for claims or 'procedural' for court context.\n"
        "4. IGNORE: All form instructions, boilerplate, and headers.\n"
        "OUTPUT: Return ONLY a valid JSON object:\n"
        "{\n"
        "  'metadata': { 'case_number': '...', 'parties': ['...'], 'title': '...' },\n"
        "  'procedural_facts': [ 'Fact 1', ... ],\n"
        "  'claims': [ { 'id': 1, 'label': '1.', 'text': '...', 'type': 'substantive' }, ... ]\n"
        "}\n"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", # Use fast model for extraction
            contents=system_prompt + f"\nEXTRACT FROM:\n{narrative_text}"
        )

        raw = response.text
        # Clean markdown fences
        raw = re.sub(r'```json\s*|\s*```', '', raw).strip()
        data = json.loads(raw)

        # Ensure 'text' and 'body' consistency
        for c in data.get("claims", []):
            if "text" in c: c["body"] = c["text"]
            elif "body" in c: c["text"] = c["body"]

        return data
    except Exception as e:
        print(f"  -> LLM failed: {e}. Falling back to local chunker.")
        return chunk_claims_smart(narrative_text, state_code)


# ---------------------------------------------------------------------------
# UI / HTML Generation
# ---------------------------------------------------------------------------

def build_response_sheet_html(data, used_local=False):
    """
    Generates a printable HTML response sheet.
    """
    metadata = data.get("metadata", {})
    claims = data.get("claims", [])
    procedural = data.get("procedural_facts", [])

    title = metadata.get("title", "Legal Document")
    header = metadata.get("case_header", metadata.get("case_number", "Unknown Case"))
    parties = metadata.get("parties", [])

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Response Sheet - {title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.5; color: #333; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
        .header-box {{ background: #f8f9fa; border: 1px solid #dee2e6; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .header-box h1 {{ margin-top: 0; color: #1a73e8; }}
        .claim-card {{ border: 1px solid #000; margin-bottom: 25px; page-break-inside: avoid; }}
        .claim-header {{ background: #eee; padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #000; display: flex; justify-content: space-between; }}
        .claim-body {{ padding: 15px; border-bottom: 1px solid #000; background: #fff; }}
        .response-area {{ padding: 15px; }}
        .response-label {{ font-weight: bold; font-size: 0.9em; margin-bottom: 10px; color: #555; }}
        .response-lines {{ background-image: linear-gradient(#eee 1px, transparent 1px); background-size: 100% 2.5em; line-height: 2.5em; min-height: 10em; }}
        .local-warning {{ background: #fff3cd; border: 1px solid #ffeeba; padding: 10px; margin-bottom: 20px; border-radius: 4px; font-size: 0.9em; }}
        @media print {{
            .no-print, button {{ display: none !important; }}
            body {{ margin: 0; padding: 0; }}
            .header-box {{ border: none; background: none; padding: 0; }}
        }}
    </style>
    <script>
        function removeChunk(el) {{ if(confirm('Remove?')) el.closest('.claim-card').style.display='none'; }}
    </script>
</head>
<body>
    <div class="header-box">
        <h1>Response Sheet: {title}</h1>
        <p><strong>Case:</strong> {header}</p>
"""
    if parties:
        html += f'<p><strong>Parties:</strong> {", ".join(parties)}</p>'
    html += f"""
        <p><strong>Date Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
"""
    if used_local:
        html += '<div class="local-warning"><strong>Note:</strong> Generated using local logic. Please verify chunks for accuracy.</div>'
    if procedural:
        html += "<h3>Procedural Context</h3><ul>" + "".join(f"<li>{f}</li>" for f in procedural) + "</ul><hr>"
    html += """
    <div class="claims-container">
"""
    for i, claim in enumerate(claims, 1):
        label = claim.get("label") or f"{i}."
        text = claim.get("text", "")
        html += f"""
        <div class="claim-card">
            <div class="claim-header">
                <span>Claim {label}</span>
                <button class="no-print" onclick="removeChunk(this)">×</button>
            </div>
            <div class="claim-body">{text}</div>
            <div class="response-area">
                <div class="response-label">Your Rebuttal / Statement:</div>
                <div class="response-lines"></div>
            </div>
        </div>
"""
    html += "</div></body></html>"
    return html


# ---------------------------------------------------------------------------
# Main Orchestration
# ---------------------------------------------------------------------------

def generate_response_sheet(file_path, output_path=None, state_code="IL", force_local=False):
    print(f"--- Generating Response Sheet for: {Path(file_path).name} ---")

    # 1. Extract content
    narrative_text, raw_text, form_data = extract_content_smart(file_path, state_code)
    if not narrative_text.strip():
        print("Error: No narrative content found.")
        return None

    # 2. Chunk claims
    client = None
    if not force_local and os.environ.get("GEMINI_API_KEY"):
        try:
            import google.genai as genai
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        except Exception: pass

    if client:
        print("  -> Using Gemini for chunking...")
        data = chunk_claims_with_llm(client, narrative_text, state_code)
    else:
        print("  -> Using local chunker...")
        data = chunk_claims_smart(narrative_text, state_code)

    # 3. Final clean and metadata enrichment (use raw text for better metadata)
    used_local = not client
    if not data.get("metadata") or not data["metadata"].get("title"):
        # Use raw text for metadata extraction (has form headers with title, parties, case #)
        data["metadata"] = extract_metadata(raw_text or narrative_text, state_code)

    # 4. Save outputs
    base_path = Path(output_path).with_suffix("") if output_path else Path(file_path).with_suffix("")

    # JSON output
    json_path = f"{base_path}.response_sheet.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  -> JSON saved: {json_path}")

    # HTML output
    html = build_response_sheet_html(data, used_local)
    html_path = f"{base_path}.response_sheet.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  -> HTML saved: {html_path}")

    return html_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_response_sheet.py <input_file> [output_path] [state_code] [--local]")
        sys.exit(1)

    file_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    state_code = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "IL"
    force_local = "--local" in sys.argv

    try:
        generate_response_sheet(file_path, output_path, state_code, force_local)
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
