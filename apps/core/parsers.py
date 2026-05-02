"""
Unified Parsing Module for Hiver.

This module consolidates all timeline parsing logic into a single, standardized interface.
It replaces redundant parsing functions from timeline/utils.py and other locations.
"""

import re
import markdown
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def parse_markdown_content(content):
    """
    Unified markdown parser supporting all timeline formats.
    
    Supports:
    - Legacy format: ## Event Title\n**Date:** ...\n**Category:** ...
    - Table format: | Date | Event | Description | Category | Documents |
    - Mixed formats within the same document
    
    Args:
        content (str): Markdown content to parse
        
    Returns:
        dict: {
            'events': List[dict],      # List of parsed events
            'timelines': Dict[str, List[dict]],  # Events grouped by timeline name
            'headings': List[dict],    # Extracted headings with levels
            'metadata': dict           # Document metadata
        }
    """
    result = {
        'events': [],
        'timelines': {},
        'headings': [],
        'metadata': {}
    }
    
    # Parse headings first
    heading_pattern = r'^(#{1,6})\s+(.+?)\s*$'
    for line in content.split('\n'):
        match = re.match(heading_pattern, line)
        if match:
            level_hashes, text = match.groups()
            level = len(level_hashes)
            result['headings'].append({
                'level': level,
                'text': text.strip(),
                'anchor': re.sub(r'[^\w\-]+', '-', text.lower()).strip('-')
            })
    
    # Try table-based parsing first (modern format)
    table_events = _parse_table_events(content)
    if table_events:
        result['events'].extend(table_events)
        # Group events by their section headings
        current_timeline = 'Main Timeline'
        for event in table_events:
            if 'section' in event and event['section']:
                current_timeline = event['section']
            if current_timeline not in result['timelines']:
                result['timelines'][current_timeline] = []
            result['timelines'][current_timeline].append(event)
    
    # Try legacy parsing if no table events found
    if not table_events:
        legacy_events = _parse_legacy_events(content)
        result['events'].extend(legacy_events)
        # Group legacy events by their section headings
        current_timeline = 'Main Timeline'
        for event in legacy_events:
            if 'section' in event and event['section']:
                current_timeline = event['section']
            if current_timeline not in result['timelines']:
                result['timelines'][current_timeline] = []
            result['timelines'][current_timeline].append(event)
    
    # Extract metadata from frontmatter if present
    frontmatter = _extract_frontmatter(content)
    if frontmatter:
        result['metadata'] = frontmatter
    
    return result


def _parse_table_events(content):
    """Parse timeline events from HTML tables (5-column format)."""
    events = []
    
    try:
        html = markdown.markdown(content, extensions=['tables'])
        soup = BeautifulSoup(html, 'html.parser')
        
        current_section = None
        for element in soup.find_all():
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                current_section = element.get_text().strip()
            elif element.name == 'table':
                rows = element.find_all('tr')
                if len(rows) >= 2:  # Has header + data rows
                    for row in rows[1:]:  # Skip header
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 5:
                            date = cells[0].get_text().strip()
                            event_title = cells[1].get_text().strip()
                            description = cells[2].get_text().strip()
                            category = cells[3].get_text().strip().lower()
                            documents_raw = cells[4].get_text().strip()
                            documents = [d.strip() for d in documents_raw.split(',') if d.strip()]
                            
                            events.append({
                                'section': current_section,
                                'date': date,
                                'event': event_title,
                                'description': description,
                                'category': category,
                                'documents': documents
                            })
    except Exception:
        pass
    
    return events


def _parse_legacy_events(content):
    """Parse timeline events from legacy markdown format."""
    events = []
    current_event = None
    current_section = None
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Check for section heading (H2)
        if line.startswith('## '):
            current_section = line[3:].strip()
        
        # Check for event heading (H3)
        elif line.startswith('### '):
            if current_event:
                events.append(current_event)
            current_event = {
                'section': current_section,
                'title': line[4:].strip(),
                'date': None,
                'category': 'other',
                'notes': '',
                'description': '',
                'documents': []
            }
        
        # Parse event fields
        elif current_event:
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
            elif line.lower().startswith('**documents:**') or line.lower().startswith('**supporting docs:**'):
                docs_part = line.split(':', 1)[1].strip()
                current_event['documents'] = _extract_documents_from_text(docs_part)
    
    if current_event:
        events.append(current_event)
    
    return events


def _extract_frontmatter(content):
    """Extract YAML frontmatter from markdown content."""
    frontmatter = {}
    
    # Check for YAML frontmatter (--- ... ---)
    if content.startswith('---'):
        lines = content.split('\n')
        if len(lines) > 2 and lines[1].strip():
            for line in lines[1:]:
                if line.strip() == '---':
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
    
    return frontmatter


def _extract_documents_from_text(text):
    """Extract document references from text."""
    documents = []
    
    # Try markdown links: [title](url)
    link_pattern = r'\[(.*?)\]\((.*?)\)'
    matches = re.findall(link_pattern, text)
    for title, url in matches:
        documents.append({'title': title.strip(), 'url': url.strip()})
    
    # Try comma-separated values
    if not documents:
        parts = [p.strip() for p in text.split(',')]
        for part in parts:
            if part:
                documents.append(part)
    
    return documents


def validate_timeline_events(events):
    """
    Validate timeline events for required fields and date format.
    
    Args:
        events (list): List of event dicts to validate
        
    Raises:
        ValueError: If events are missing required fields or have invalid dates
        
    Returns:
        bool: True if all events are valid
    """
    for i, event in enumerate(events):
        # Check required fields
        required_fields = ['date', 'event']
        for field in required_fields:
            if field not in event or not event[field]:
                raise ValueError(
                    f"Event {i} missing required field '{field}': {event}"
                )
        
        # Validate date format
        try:
            datetime.strptime(event['date'], '%Y-%m-%d')
        except ValueError:
            raise ValueError(
                f"Event {i} has invalid date format '{event['date']}'. "
                f"Expected YYYY-MM-DD."
            )
    
    return True


def parse_timeline_file(file_path):
    """
    Parse a timeline Markdown file and extract structure.
    
    Args:
        file_path (str/Path): Path to Markdown file
        
    Returns:
        dict: Parsed content with events, timelines, headings, and metadata
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return parse_markdown_content(content)


def format_event_for_display(event):
    """
    Format an event dict for display in templates.
    
    Args:
        event (dict): Event data
        
    Returns:
        dict: Formatted event with display-ready fields
    """
    formatted = event.copy()
    
    # Format date for display
    if 'date' in event and event['date']:
        try:
            date_obj = datetime.strptime(event['date'], '%Y-%m-%d')
            formatted['date_display'] = date_obj.strftime('%B %d, %Y')
        except ValueError:
            formatted['date_display'] = event['date']
    
    # Format category
    if 'category' in event:
        formatted['category_display'] = event['category'].capitalize()
    
    # Format documents
    if 'documents' in event:
        formatted['document_urls'] = []
        for doc in event['documents']:
            if isinstance(doc, dict):
                formatted['document_urls'].append({
                    'title': doc.get('title', 'Document'),
                    'url': doc.get('url', '')
                })
            else:
                formatted['document_urls'].append({
                    'title': str(doc),
                    'url': ''
                })
    
    return formatted
