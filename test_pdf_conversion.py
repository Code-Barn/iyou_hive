#!/usr/bin/env python
"""
Test script for PDF conversion formatting.
"""

import os
import sys
from pathlib import Path

# Add the project directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.archive.utils import convert_pdf_to_markdown, pdf_to_markdown_string

def test_pdf_conversion():
    """Test PDF conversion with sample files."""
    test_pdfs = [
        'sample_contract.pdf',
        'sample_pleading.pdf',
        'sample_brief.pdf',
    ]
    
    for pdf_file in test_pdfs:
        if not os.path.exists(pdf_file):
            print(f"Sample PDF file not found: {pdf_file}")
            continue
            
        print(f"\nTesting conversion for: {pdf_file}")
        markdown_output = pdf_to_markdown_string(pdf_file)
        
        if markdown_output:
            print(f"Successfully converted {pdf_file} to Markdown.")
            print("Preview:")
            print(markdown_output[:500] + "...")
        else:
            print(f"Failed to convert {pdf_file}")

if __name__ == '__main__':
    test_pdf_conversion()