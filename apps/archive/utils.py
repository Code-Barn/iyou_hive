"""
PDF Conversion Utilities for Hiver Archive.

This module provides PyMuPDF-based PDF to Markdown conversion that preserves
legal document formatting style as defined in sync_legal_docs_ORIGINAL.py.
"""

import re
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime


def extract_text_with_formatting(pdf_path):
    """
    Extract text from PDF while preserving basic formatting.
    
    Args:
        pdf_path (str/Path): Path to PDF file
        
    Returns:
        str: Extracted text with preserved formatting
    """
    doc = fitz.open(pdf_path)
    text_parts = []
    
    for page_num, page in enumerate(doc):
        # Extract text with layout information
        blocks = page.get_text("blocks")
        
        for block in blocks:
            # block[4] contains the text, block[0:4] contains coordinates
            text = block[4].strip()
            if text:
                # Detect headings (larger font sizes)
                if len(text) < 100 and any(word in text.lower() for word in ['case', 'motion', 'affidavit', 'exhibit', 'plaintiff', 'defendant']):
                    # Likely a heading
                    text_parts.append(f"\n## {text}\n")
                else:
                    text_parts.append(f"{text}\n")
        
        if page_num < len(doc) - 1:
            text_parts.append("\n--- Page Break ---\n")
    
    doc.close()
    return "".join(text_parts)


def extract_tables(pdf_path):
    """
    Extract tables from PDF using PyMuPDF.
    
    Args:
        pdf_path (str/Path): Path to PDF file
        
    Returns:
        list: List of extracted tables (each table is list of rows)
    """
    doc = fitz.open(pdf_path)
    tables = []
    
    for page in doc:
        # Extract tables from the page
        page_tables = page.find_tables()
        
        for table in page_tables:
            table_data = table.extract()
            if table_data:
                tables.append(table_data)
    
    doc.close()
    return tables


def extract_metadata(pdf_path):
    """
    Extract metadata from PDF.
    
    Args:
        pdf_path (str/Path): Path to PDF file
        
    Returns:
        dict: Extracted metadata
    """
    doc = fitz.open(pdf_path)
    metadata = {
        'title': doc.metadata.get('title', ''),
        'author': doc.metadata.get('author', ''),
        'subject': doc.metadata.get('subject', ''),
        'creator': doc.metadata.get('creator', ''),
        'creation_date': doc.metadata.get('creationDate', ''),
        'mod_date': doc.metadata.get('modDate', ''),
        'page_count': len(doc)
    }
    doc.close()
    return metadata


def format_table_as_markdown(table_data):
    """
    Format table data as Markdown table.
    
    Args:
        table_data (list): Table data (list of rows)
        
    Returns:
        str: Markdown formatted table
    """
    if not table_data or len(table_data) < 2:
        return ""
    
    # Convert to Markdown table format
    markdown_lines = []
    
    # Header
    header = " | ".join(str(cell) for cell in table_data[0])
    markdown_lines.append(f"| {header} |")
    
    # Separator
    separator = " | ".join("---" for _ in table_data[0])
    markdown_lines.append(f"| {separator} |")
    
    # Data rows
    for row in table_data[1:]:
        row_text = " | ".join(str(cell) for cell in row)
        markdown_lines.append(f"| {row_text} |")
    
    return "\n".join(markdown_lines)


def convert_pdf_to_markdown(pdf_path, output_path=None):
    """
    Convert PDF to Markdown with legal document formatting.
    
    Args:
        pdf_path (str/Path): Path to input PDF file
        output_path (str/Path, optional): Path to output Markdown file
        
    Returns:
        str: Path to generated Markdown file, or None if failed
    """
    pdf_path = Path(pdf_path)
    
    if output_path is None:
        output_path = pdf_path.with_suffix('.md')
    else:
        output_path = Path(output_path)
    
    try:
        # Extract basic text with formatting
        text_content = extract_text_with_formatting(pdf_path)
        
        # Extract tables
        tables = extract_tables(pdf_path)
        
        # Extract metadata
        metadata = extract_metadata(pdf_path)
        
        # Build Markdown content
        markdown_lines = []
        
        # Add metadata header
        if metadata['title']:
            markdown_lines.append(f"# {metadata['title']}")
        else:
            markdown_lines.append(f"# {pdf_path.stem.replace('_', ' ').title()}")
        
        markdown_lines.append(f"\n**Document Metadata:**")
        markdown_lines.append(f"- Author: {metadata['author']}")
        markdown_lines.append(f"- Subject: {metadata['subject']}")
        markdown_lines.append(f"- Pages: {metadata['page_count']}")
        if metadata['creation_date']:
            try:
                creation_date = datetime.strptime(metadata['creation_date'][2:10], '%Y%m%d')
                markdown_lines.append(f"- Created: {creation_date.strftime('%Y-%m-%d')}")
            except:
                pass
        
        # Add main content
        markdown_lines.append("\n## Document Content")
        markdown_lines.append(text_content)
        
        # Add tables
        if tables:
            markdown_lines.append("\n## Tables")
            for i, table in enumerate(tables, 1):
                markdown_lines.append(f"\n### Table {i}")
                markdown_lines.append(format_table_as_markdown(table))
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(markdown_lines))
        
        return str(output_path)
        
    except Exception as e:
        print(f"Error converting PDF to Markdown: {e}")
        return None


def pdf_to_markdown_string(pdf_path):
    """
    Convert PDF to Markdown string (without saving to file).
    
    Args:
        pdf_path (str/Path): Path to PDF file
        
    Returns:
        str: Markdown content, or None if failed
    """
    try:
        # Extract basic text with formatting
        text_content = extract_text_with_formatting(pdf_path)
        
        # Extract tables
        tables = extract_tables(pdf_path)
        
        # Extract metadata
        metadata = extract_metadata(pdf_path)
        
        # Build Markdown content
        markdown_lines = []
        
        # Add metadata header
        if metadata['title']:
            markdown_lines.append(f"# {metadata['title']}")
        else:
            markdown_lines.append(f"# {Path(pdf_path).stem.replace('_', ' ').title()}")
        
        markdown_lines.append(f"\n**Document Metadata:**")
        markdown_lines.append(f"- Author: {metadata['author']}")
        markdown_lines.append(f"- Subject: {metadata['subject']}")
        markdown_lines.append(f"- Pages: {metadata['page_count']}")
        
        # Add main content
        markdown_lines.append("\n## Document Content")
        markdown_lines.append(text_content)
        
        # Add tables
        if tables:
            markdown_lines.append("\n## Tables")
            for i, table in enumerate(tables, 1):
                markdown_lines.append(f"\n### Table {i}")
                markdown_lines.append(format_table_as_markdown(table))
        
        return '\n'.join(markdown_lines)
        
    except Exception as e:
        print(f"Error converting PDF to Markdown: {e}")
        return None
