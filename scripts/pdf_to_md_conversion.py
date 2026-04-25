#!/usr/bin/env python3
"""
PDF to Markdown Conversion Script

This script converts PDF files to Markdown format for integration with Hiver's
timeline system. It extracts text, preserves structure, and formats it as
legal case timeline markdown.

Usage:
    python scripts/pdf_to_md_conversion.py <input_pdf_path> [output_md_path]

Dependencies:
    - pdfplumber (for PDF text extraction)
    - python-dateutil (for date parsing)

Install with:
    pip install pdfplumber python-dateutil
"""

import re
import sys
import os
from datetime import datetime
from pathlib import Path

# Check for pdfplumber, fall back to text extraction without it
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("Warning: pdfplumber not installed. Falling back to basic text extraction.")


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        str: Extracted text content
    """
    if not HAS_PDFPLUMBER:
        # Fallback: Try to read as text (won't work for binary PDFs)
        try:
            with open(pdf_path, 'r', encoding='latin-1') as f:
                return f.read()
        except:
            return ""
    
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
    
    return text


def parse_legal_document(text):
    """
    Parse legal document text and extract structured information.
    
    This function identifies:
    - Dates
    - Parties
    - Document types
    - Key clauses
    - Signatures
    
    Args:
        text: The extracted text from the PDF
        
    Returns:
        dict: Parsed document structure
    """
    result = {
        'title': None,
        'date': None,
        'parties': [],
        'type': None,
        'sections': [],
        'key_terms': [],
        'raw_text': text
    }
    
    # Extract title (first few lines often contain the title)
    lines = text.split('\n')
    for i, line in enumerate(lines[:10]):
        line = line.strip()
        if line and len(line) > 10 and not line[0].isdigit():
            result['title'] = line
            break
    
    # Extract dates (look for date patterns)
    date_patterns = [
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
        r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
        r'\b\d{4}-\d{2}-\d{2}\b',
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        if matches:
            result['date'] = matches[0]
            break
    
    # Extract document type (look for keywords)
    type_keywords = {
        'contract': ['agreement', 'contract', 'terms and conditions', 'between'],
        'complaint': ['complaint', 'plaintiff', 'defendant'],
        'answer': ['answer', 'response'],
        'motion': ['motion', 'to dismiss', 'for summary judgment'],
        'order': ['order', 'court order', 'judgment'],
        'email': ['from:', 'to:', 'subject:', 're:', 'fw:'],
        'letter': ['letter', 'correspondence'],
        'memorandum': ['memorandum', 'memo'],
    }
    
    text_lower = text.lower()
    for doc_type, keywords in type_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                result['type'] = doc_type
                break
        if result['type']:
            break
    
    # If no type found, use first word of title
    if not result['type'] and result['title']:
        first_word = result['title'].split()[0].lower() if result['title'] else ''
        result['type'] = first_word
    
    # Extract parties (names, usually in specific locations)
    # Look for patterns like "Plaintiff:", "Defendant:", "Between:", etc.
    party_patterns = [
        (r'(?:between|plaintiff[s]?|defendant[s]?|party|parties|by):?\s*(.+?)(?:\n|\.|,)', 'party'),
        (r'(?:signed by|signature of):\s*(.+?)(?:\n|\.|,)', 'signer'),
        (r'\b(?:attorney|lawyer|counsel|firm):\s*(.+?)(?:\n|\.|,)', 'attorney'),
    ]
    
    for pattern, party_type in party_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            names = [n.strip() for n in match.split('and')]
            for name in names:
                name = name.strip(' ,;\n')
                if name and len(name) > 2:
                    result['parties'].append({'type': party_type, 'name': name})
    
    # Extract sections (numbered or titled sections)
    section_pattern = r'^(?:\s*[\d\.]+|[A-Z][A-Z\s]+)\s+(.+?)$'
    current_section = None
    for line in lines:
        line = line.strip()
        if re.match(section_pattern, line) and len(line) < 200:
            current_section = line
            result['sections'].append({'title': current_section, 'content': []})
        elif current_section and line:
            result['sections'][-1]['content'].append(line)
    
    # Extract key terms (common legal terms)
    legal_terms = [
        'whereas', 'hereinafter', 'agrees', 'shall', 'may', 'must', 'notwithstanding',
        'indemnify', 'liability', 'breach', 'termination', 'confidential', 'exhibit',
        'witnesseth', 'executed', 'effective date', 'governing law', 'jurisdiction'
    ]
    
    for line in lines:
        for term in legal_terms:
            if term.lower() in line.lower() and term not in result['key_terms']:
                result['key_terms'].append(term)
    
    return result


def format_as_timeline_markdown(document):
    """
    Format parsed document as timeline-compatible markdown.
    
    Args:
        document: Parsed document dict from parse_legal_document()
        
    Returns:
        str: Formatted markdown
    """
    md = []
    
    # Add header with metadata
    md.append("---")
    md.append(f"title: {document['title'] or 'Legal Document'}")
    if document['date']:
        md.append(f"date: {document['date']}")
    md.append(f"category: {document['type'] or 'Document'}")
    md.append("---")
    md.append("")
    
    # Add document date as timeline header
    if document['date']:
        try:
            # Convert date to YYYY-MM-DD format
            date_str = document['date']
            # Try to parse and reformat
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts[2]) == 2:
                    parts[2] = '20' + parts[2]
                date_str = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
            md.append(f"# {date_str}")
        except:
            md.append(f"# {date_str}")
    else:
        md.append("# Untitled Event")
    
    md.append("")
    
    # Add event details
    if document['title']:
        md.append(f"**Event:** {document['title']}")
    
    if document['type']:
        md.append(f"**Category:** {document['type'].title()}")
    
    # Add parties
    if document['parties']:
        party_names = ", ".join([p['name'] for p in document['parties']])
        md.append(f"**Parties:** {party_names}")
    
    # Add supporting docs (reference the original PDF)
    md.append("**Supporting Docs:** Document PDF")
    md.append("")
    
    # Add notes from sections
    if document['sections']:
        md.append("**Notes:**")
        for section in document['sections']:
            if section['title'] != section['content']:
                md.append(f"\n**{section['title']}:**")
                md.append("\n".join(section['content'][:3]))  # First 3 lines
    elif document['key_terms']:
        md.append(f"**Notes:** Key terms: {', '.join(document['key_terms'][:5])}")
    else:
        # Add first few lines of text
        text_lines = document['raw_text'].split('\n')
        notes = [l.strip() for l in text_lines[:5] if l.strip()]
        if notes:
            md.append(f"**Notes:** {' '.join(notes)}")
    
    return "\n".join(md)


def convert_pdf_to_markdown(pdf_path, output_path=None):
    """
    Convert a PDF file to Markdown format.
    
    Args:
        pdf_path: Path to the input PDF file
        output_path: Optional path for output markdown file
        
    Returns:
        str: Path to the created markdown file
    """
    # Validate input
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError(f"File is not a PDF: {pdf_path}")
    
    # Extract text from PDF
    text = extract_text_from_pdf(pdf_path)
    
    if not text or len(text.strip()) < 10:
        raise ValueError(f"Could not extract text from PDF: {pdf_path}")
    
    # Parse the document
    document = parse_legal_document(text)
    
    # Format as markdown
    markdown = format_as_timeline_markdown(document)
    
    # Determine output path
    if output_path is None:
        base_path = Path(pdf_path).with_suffix('')
        output_path = str(base_path) + '.md'
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    # Save markdown
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    return output_path


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_md_conversion.py <input_pdf> [output_md]")
        print("\nConverts a PDF file to Markdown format for legal timeline use.")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        md_path = convert_pdf_to_markdown(pdf_path, output_path)
        print(f"Successfully converted {pdf_path} to {md_path}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
