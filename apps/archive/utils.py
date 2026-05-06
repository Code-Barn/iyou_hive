"""
PDF Conversion Utilities for Hiver Archive.

This module provides PyMuPDF-based PDF to Markdown conversion that preserves
legal document formatting style as defined in sync_legal_docs_ORIGINAL.py.
"""

import re
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
from apps.core.document_processing import convert_pdf_to_markdown as core_convert_pdf_to_markdown
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


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
    # Use the centralized document processing logic
    return core_convert_pdf_to_markdown(pdf_path)


def pdf_to_markdown_string(pdf_path):
    """
    Convert PDF to Markdown string (without saving to file).
    
    Args:
        pdf_path (str/Path): Path to PDF file
        
    Returns:
        str: Markdown content, or None if failed
    """
    # Use the centralized document processing logic
    md_path = core_convert_pdf_to_markdown(pdf_path)
    if md_path:
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def extract_exif_metadata(image_path):
    """
    Extract EXIF metadata from an image file.
    
    Args:
        image_path (str/Path): Path to the image file
        
    Returns:
        dict: Extracted metadata including timestamp, GPS, and device info
    """
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        
        if not exif_data:
            return {}
        
        metadata = {}
        
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            
            if tag == 'DateTimeOriginal':
                # Parse EXIF datetime format: 'YYYY:MM:DD HH:MM:SS'
                try:
                    datetime_str = value.replace(':', '-', 2)  # Replace first two colons
                    metadata['timestamp'] = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    pass
            
            elif tag == 'Make':
                metadata['device_make'] = value
            
            elif tag == 'Model':
                metadata['device_model'] = value
            
            elif tag == 'GPSInfo':
                gps_info = {}
                for gps_tag_id in value.keys():
                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag] = value[gps_tag_id]
                
                # Extract latitude and longitude
                if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
                    lat = gps_info['GPSLatitude']
                    lat_ref = gps_info.get('GPSLatitudeRef', 'N')
                    lon = gps_info['GPSLongitude']
                    lon_ref = gps_info.get('GPSLongitudeRef', 'E')
                    
                    # Convert to decimal degrees
                    metadata['gps_latitude'] = convert_to_decimal_degrees(lat, lat_ref)
                    metadata['gps_longitude'] = convert_to_decimal_degrees(lon, lon_ref)
        
        # Combine device make and model
        if 'device_make' in metadata or 'device_model' in metadata:
            device_parts = []
            if 'device_make' in metadata:
                device_parts.append(metadata['device_make'])
            if 'device_model' in metadata:
                device_parts.append(metadata['device_model'])
            metadata['device'] = ' '.join(device_parts)
        
        return metadata
        
    except Exception as e:
        print(f"Error extracting EXIF metadata: {e}")
        return {}


def convert_to_decimal_degrees(coordinate, reference):
    """
    Convert GPS coordinates from EXIF format to decimal degrees.
    
    Args:
        coordinate (tuple): GPS coordinate in degrees, minutes, seconds
        reference (str): Direction (N/S/E/W)
        
    Returns:
        float: Decimal degrees
    """
    try:
        degrees = coordinate[0][0] / coordinate[0][1]
        minutes = coordinate[1][0] / coordinate[1][1]
        seconds = coordinate[2][0] / coordinate[2][1]
        
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        
        if reference in ['S', 'W']:
            decimal = -decimal
        
        return decimal
    except (IndexError, TypeError, ZeroDivisionError):
        return None
