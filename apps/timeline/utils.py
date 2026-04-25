"""
Timeline utilities for parsing Markdown files and extracting headings.

This module provides:
- Markdown file parsing with python-markdown
- Heading extraction for dynamic timeline display
- Helper functions for timeline rendering
"""

import os
import re
from pathlib import Path

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False


def parse_markdown_file(file_path):
    """
    Parse a Markdown file and extract headings and structure.
    
    Args:
        file_path (str): Absolute path to the Markdown file
        
    Returns:
        dict: Parsed content with headings, sections, and metadata
            {
                'headings': [{'level': 'h1', 'text': 'Main Heading', 'anchor': 'main-heading'}, ...],
                'first_heading': str or None,
                'sections': [{'heading': str, 'content': str}, ...],
                'raw_content': str,
                'html': str or None
            }
    """
    if not os.path.exists(file_path):
        return {
            'headings': [],
            'first_heading': None,
            'sections': [],
            'raw_content': '',
            'html': None
        }
    
    with open(file_path, 'r', encoding='utf-8') as file:
        raw_content = file.read()
    
    result = {
        'headings': [],
        'first_heading': None,
        'sections': [],
        'raw_content': raw_content,
        'html': None
    }
    
    # Parse with markdown if available
    if MARKDOWN_AVAILABLE:
        result['html'] = markdown.markdown(raw_content)
    
    # Extract headings using regex (works with or without markdown library)
    heading_pattern = r'^(#{1,6})\s+(.+?)\s*$'
    headings = []
    
    for line in raw_content.split('\n'):
        match = re.match(heading_pattern, line)
        if match:
            level_hashes, text = match.groups()
            level = f'h{len(level_hashes)}'
            anchor = re.sub(r'[^\w\-]+', '-', text.lower()).strip('-')
            headings.append({
                'level': level,
                'text': text.strip(),
                'anchor': anchor
            })
    
    result['headings'] = headings
    result['first_heading'] = headings[0]['text'] if headings else None
    
    # Extract sections (content between headings)
    sections = []
    lines = raw_content.split('\n')
    current_section = {'heading': None, 'contentlines': []}
    
    for line in lines:
        heading_match = re.match(heading_pattern, line)
        if heading_match:
            # Save previous section
            if current_section['heading'] is not None:
                sections.append({
                    'heading': current_section['heading'],
                    'content': '\n'.join(current_section['contentlines'])
                })
            # Start new section
            current_section = {
                'heading': heading_match.group(2).strip(),
                'contentlines': []
            }
        else:
            current_section['contentlines'].append(line)
    
    # Save last section
    if current_section['heading'] is not None:
        sections.append({
            'heading': current_section['heading'],
            'content': '\n'.join(current_section['contentlines'])
        })
    
    result['sections'] = sections
    
    return result


def extract_headings(html_content=None, markdown_content=None):
    """
    Extract headings from HTML or Markdown content.
    
    Args:
        html_content (str, optional): HTML content to parse
        markdown_content (str, optional): Markdown content to parse
        
    Returns:
        list: List of heading dicts with level, text, and anchor
    """
    headings = []
    
    if html_content and BEAUTIFULSOUP_AVAILABLE:
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            headings.append({
                'level': heading.name,
                'text': heading.get_text().strip(),
                'anchor': heading.get('id', '')
            })
    elif markdown_content:
        # Parse markdown headings directly
        heading_pattern = r'^(#{1,6})\s+(.+?)\s*$'
        for line in markdown_content.split('\n'):
            match = re.match(heading_pattern, line)
            if match:
                level_hashes, text = match.groups()
                level = f'h{len(level_hashes)}'
                anchor = re.sub(r'[^\w\-]+', '-', text.lower()).strip('-')
                headings.append({
                    'level': level,
                    'text': text.strip(),
                    'anchor': anchor
                })
    
    return headings


def get_main_heading(markdown_content=None, file_path=None):
    """
    Get the main (first H1) heading from Markdown content or file.
    
    Args:
        markdown_content (str, optional): Markdown content
        file_path (str, optional): Path to Markdown file
        
    Returns:
        str: The first H1 heading text, or a default
    """
    if file_path:
        parsed = parse_markdown_file(file_path)
        return parsed['first_heading']
    
    if markdown_content:
        for line in markdown_content.split('\n'):
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
    
    return "Legal Timeline"


def parse_timeline_events_from_markdown(markdown_content):
    """
    Parse timeline events from Markdown content.
    
    Expected format:
    # Timeline Name
    
    ## Event 1
    **Date:** 2024-01-01
    **Event:** Contract Signed
    **Category:** contract
    **Notes:** This is a test event
    
    ## Event 2
    **Date:** 2024-01-15
    ...
    
    Args:
        markdown_content (str): Markdown content with timeline events
        
    Returns:
        list: List of event dicts
    """
    events = []
    current_event = None
    in_event = False
    
    lines = markdown_content.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Check for event heading (##)
        if line.startswith('## '):
            # Save previous event
            if current_event:
                events.append(current_event)
            current_event = {
                'title': line[3:].strip(),
                'date': None,
                'category': 'other',
                'notes': '',
                'description': ''
            }
            in_event = True
        elif in_event and current_event:
            # Parse event fields
            if line.lower().startswith('**date:**'):
                current_event['date'] = line[8:].strip()
            elif line.lower().startswith('**event:**'):
                current_event['title'] = line[8:].strip()
            elif line.lower().startswith('**category:**'):
                current_event['category'] = line[12:].strip().lower()
            elif line.lower().startswith('**notes:**'):
                current_event['notes'] = line[8:].strip()
            elif line.lower().startswith('**description:**'):
                current_event['description'] = line[15:].strip()
            else:
                # Regular content line
                if current_event.get('description'):
                    current_event['description'] += '\n' + line
                else:
                    current_event['description'] = line
    
    # Save last event
    if current_event:
        events.append(current_event)
    
    return events


def find_markdown_files(directory):
    """
    Find all Markdown files in a directory.
    
    Args:
        directory (str): Directory path to search
        
    Returns:
        list: List of file paths
    """
    md_files = []
    directory = Path(directory)
    
    if directory.exists():
        for ext in ['*.md', '*.markdown', '*.MD', '*.MARKDOWN']:
            md_files.extend(directory.glob(ext))
    
    return [str(f) for f in sorted(md_files)]


def get_timeline_file_info(file_path):
    """
    Get information about a timeline Markdown file.
    
    Args:
        file_path (str): Path to the timeline file
        
    Returns:
        dict: File information
    """
    parsed = parse_markdown_file(file_path)
    
    return {
        'file_path': file_path,
        'name': os.path.basename(file_path),
        'main_heading': parsed['first_heading'] or os.path.splitext(os.path.basename(file_path))[0],
        'heading_count': len(parsed['headings']),
        'headings': parsed['headings']
    }
