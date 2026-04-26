"""
Timeline utilities for parsing Markdown files and extracting headings.

This module provides:
- Markdown file parsing with python-markdown
- Heading extraction for dynamic timeline display
- Timeline event parsing with support for tables, lists, images
- Helper functions for timeline rendering
- Robust error handling for malformed files
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


class MarkdownParseError(Exception):
    """Exception raised when Markdown parsing fails."""
    pass


class MarkdownValidationError(Exception):
    """Exception raised when Markdown content is invalid."""
    pass


def validate_markdown_content(content):
    """
    Validate Markdown content for required fields.
    
    Args:
        content (str): Markdown content to validate
        
    Raises:
        MarkdownValidationError: If content is invalid
        
    Returns:
        bool: True if valid
    """
    if not content or not content.strip():
        raise MarkdownValidationError("Markdown file is empty")
    
    # Check for at least one heading
    if '#' not in content:
        raise MarkdownValidationError("No headings found in Markdown file")
    
    return True


def parse_markdown_file(file_path):
    """
    Parse a Markdown file and extract headings, events, and structure.
    
    Supports:
    - Headings (H1-H6) for document structure
    - Timeline events with **Date:**, **Event:**, **Category:**, **Notes:**
    - Tables, lists, images (when python-markdown is available)
    - Inline HTML for advanced formatting
    
    Args:
        file_path (str): Absolute path to the Markdown file
        
    Returns:
        dict: Parsed content with headings, sections, events, and metadata
            {
                'headings': [{'level': int, 'text': str, 'anchor': str}, ...],
                'first_heading': str or None,
                'sections': [{'heading': str, 'content': str, 'level': int}, ...],
                'events': [{'title': str, 'date': str, 'category': str, 'notes': str, 
                          'description': str, 'documents': list}, ...],
                'raw_content': str,
                'html': str or None,
                'images': [{'url': str, 'alt': str}, ...],
                'tables': [dict, ...],
                'warnings': [str, ...]
            }
        
    Raises:
        MarkdownParseError: If file cannot be read
        MarkdownValidationError: If content is invalid
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise MarkdownParseError(f"Markdown file not found: {file_path}")
    
    # Try to read file
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            raw_content = file.read()
    except IOError as e:
        raise MarkdownParseError(f"Failed to read file {file_path}: {e}")
    except UnicodeDecodeError as e:
        raise MarkdownParseError(f"Failed to decode file {file_path} as UTF-8: {e}")
    
    # Validate content
    warnings = []
    try:
        validate_markdown_content(raw_content)
    except MarkdownValidationError as e:
        warnings.append(f"Validation warning: {e}")
    
    result = {
        'headings': [],
        'first_heading': None,
        'sections': [],
        'events': [],
        'raw_content': raw_content,
        'html': None,
        'images': [],
        'tables': [],
        'warnings': warnings
    }
    
    # Parse with markdown if available (with extensions for tables, etc.)
    if MARKDOWN_AVAILABLE:
        try:
            result['html'] = markdown.markdown(
                raw_content,
                extensions=[
                    'tables',
                    'fenced_code',
                    'codehilite',
                    'footnotes',
                    'md_in_html',
                ]
            )
        except Exception as e:
            result['warnings'].append(f"Markdown parsing error: {e}")
            result['html'] = None
    
    # Extract headings using regex
    heading_pattern = r'^(#{1,6})\s+(.+?)\s*$'
    headings = []
    
    for line in raw_content.split('\n'):
        match = re.match(heading_pattern, line)
        if match:
            level_hashes, text = match.groups()
            level = int(level_hashes[1:])  # Convert # to integer (h1 -> 1)
            anchor = re.sub(r'[^\w\-]+', '-', text.lower()).strip('-')
            headings.append({
                'level': level,
                'text': text.strip(),
                'anchor': anchor
            })
    
    result['headings'] = headings
    result['first_heading'] = headings[0]['text'] if headings else "Legal Timeline"
    
    # Extract sections (content between headings)
    sections = []
    lines = raw_content.split('\n')
    current_section = {'heading': None, 'contentlines': [], 'level': 0}
    
    for line in lines:
        heading_match = re.match(heading_pattern, line)
        if heading_match:
            # Save previous section
            if current_section['heading'] is not None:
                sections.append({
                    'heading': current_section['heading'],
                    'content': '\n'.join(current_section['contentlines']),
                    'level': current_section['level']
                })
            # Start new section
            level = int(heading_match.group(1)[1:])
            current_section = {
                'heading': heading_match.group(2).strip(),
                'contentlines': [],
                'level': level
            }
        else:
            current_section['contentlines'].append(line)
    
    # Save last section
    if current_section['heading'] is not None:
        sections.append({
            'heading': current_section['heading'],
            'content': '\n'.join(current_section['contentlines']),
            'level': current_section['level']
        })
    
    result['sections'] = sections
    
    # Parse events from tables (5-column format) - takes precedence
    table_events = []
    if result['html']:
        # Associate tables with their section headings
        for section in sections:
            section_heading = section.get('heading', '')
            section_content = section.get('content', '')
            
            # Parse table events from this section's HTML
            section_events = parse_timeline_events_from_table(result['html'], section_heading)
            table_events.extend(section_events)
    
    # Parse events from sections (backward compatibility)
    section_events = []
    for section in sections:
        # Check if this section looks like an event (has Date, Event, etc.)
        sec_events = parse_section_events(section)
        section_events.extend(sec_events)
    
    # If no table events found, try parsing the whole content
    if not table_events:
        # Try to find tables in the raw markdown
        if result['html']:
            table_events = parse_timeline_events_from_table(result['html'])
    
    # Combine events: prefer table events, fallback to section events
    result['events'] = table_events if table_events else section_events
    
    # Extract images if HTML is available
    if result['html'] and BEAUTIFULSOUP_AVAILABLE:
        try:
            soup = BeautifulSoup(result['html'], 'html.parser')
            for img in soup.find_all('img'):
                result['images'].append({
                    'url': img.get('src', ''),
                    'alt': img.get('alt', '')
                })
        except Exception as e:
            result['warnings'].append(f"Image extraction error: {e}")
    
    # Extract tables for display (not for events)
    if result['html'] and BEAUTIFULSOUP_AVAILABLE:
        try:
            soup = BeautifulSoup(result['html'], 'html.parser')
            for table in soup.find_all('table'):
                table_data = []
                for row in table.find_all('tr'):
                    cells = [cell.get_text(strip=True) for cell in row.find_all(['th', 'td'])]
                    table_data.append(cells)
                result['tables'].append(table_data)
        except Exception as e:
            result['warnings'].append(f"Table extraction error: {e}")
    
    return result


def parse_section_events(section):
    """
    Parse timeline events from a section of Markdown content.
    
    Expected format within a section:
    ## Event Title
    **Date:** 2024-01-15
    **Category:** contract
    **Notes:** Some notes here
    
    Or with description:
    ## Event Title
    Date: 2024-01-15
    Category: contract
    Notes: Some notes
    Description: More details here
    
    Args:
        section (dict): Section dict with 'heading', 'content', 'level' keys
        
    Returns:
        list: List of event dicts
    """
    events = []
    content = section.get('content', '')
    heading = section.get('heading', '')
    
    # If this is an H2 section, treat heading as event title
    if section.get('level', 0) == 2:
        event = {
            'title': heading,
            'date': None,
            'category': 'other',
            'notes': '',
            'description': content.strip(),
            'documents': [],
            'section_level': section.get('level', 0)
        }
        
        # Parse content for event fields
        for line in content.split('\n'):
            line = line.strip()
            
            # Try both **Field:** and Field: formats
            if line.lower().startswith('**date:**'):
                event['date'] = line[8:].strip()
            elif line.lower().startswith('date:'):
                event['date'] = line[5:].strip()
            elif line.lower().startswith('**category:**'):
                event['category'] = line[12:].strip().lower()
            elif line.lower().startswith('category:'):
                event['category'] = line[9:].strip().lower()
            elif line.lower().startswith('**notes:**'):
                event['notes'] = line[8:].strip()
            elif line.lower().startswith('notes:'):
                event['notes'] = line[6:].strip()
            elif line.lower().startswith('**description:**'):
                event['description'] = line[14:].strip()
            elif line.lower().startswith('description:'):
                event['description'] = line[11:].strip()
            elif line.lower().startswith('**documents:**') or line.lower().startswith('**supporting docs:**'):
                # Try to parse documents
                docs_part = line.split(':', 1)[1].strip()
                if '[' in docs_part and ']' in docs_part:
                    # Try to parse as markdown links
                    event['documents'] = extract_documents_from_text(docs_part)
                elif ',' in docs_part:
                    event['documents'] = [d.strip() for d in docs_part.split(',')]
                else:
                    event['documents'] = [docs_part]
            elif line.lower().startswith('documents:') or line.lower().startswith('supporting docs:'):
                docs_part = line.split(':', 1)[1].strip()
                if '[' in docs_part and ']' in docs_part:
                    event['documents'] = extract_documents_from_text(docs_part)
                elif ',' in docs_part:
                    event['documents'] = [d.strip() for d in docs_part.split(',')]
                else:
                    event['documents'] = [docs_part]
        
        events.append(event)
    
    return events


def extract_documents_from_text(text):
    """
    Extract document references from text.
    
    Supports formats:
    - [Document 1](url1), [Document 2](url2)
    - Document 1, Document 2
    - url1, url2
    
    Args:
        text (str): Text containing document references
        
    Returns:
        list: List of document dicts or strings
    """
    documents = []
    
    # Try to parse as markdown links
    link_pattern = r'\[(.*?)\]\((.*?)\)'
    matches = re.findall(link_pattern, text)
    for title, url in matches:
        documents.append({'title': title.strip(), 'url': url.strip()})
    
    # If no links found, try comma-separated
    if not documents and text.strip():
        parts = [p.strip() for p in text.split(',')]
        for part in parts:
            if part:
                documents.append(part)
    
    return documents


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
        try:
            parsed = parse_markdown_file(file_path)
            return parsed.get('first_heading', 'Legal Timeline')
        except (MarkdownParseError, MarkdownValidationError):
            return "Legal Timeline"
    
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


def parse_timeline_events_from_table(html_content, current_section=None):
    """
    Parse timeline events from HTML table rows (5 columns).
    
    Expected table format:
    | Date | Event | Description | Category | Documents |
    |------|-------|-------------|----------|-----------|
    | 2024-01-15 | Contract Signed | Signed with client | contract | doc1.pdf, doc2.pdf |
    
    Args:
        html_content (str): HTML content to parse
        current_section (str, optional): Current section heading for grouping
        
    Returns:
        list: List of event dicts with keys: section, date, event, description, category, documents
    """
    if not BEAUTIFULSOUP_AVAILABLE:
        return []
    
    events = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            
            # Skip tables with fewer than 2 rows (header + at least one data row)
            if len(rows) < 2:
                continue
            
            # Process each data row
            for row in rows[1:]:  # Skip header row
                cells = row.find_all(['td', 'th'])
                
                # Need at least 5 cells for the standard format
                if len(cells) < 5:
                    continue
                
                # Extract text from each cell
                date = cells[0].get_text().strip()
                event = cells[1].get_text().strip()
                description = cells[2].get_text().strip()
                category = cells[3].get_text().strip().lower()
                documents_raw = cells[4].get_text().strip()
                
                # Parse documents - split by comma, strip whitespace
                documents = [d.strip() for d in documents_raw.split(',') if d.strip()]
                
                events.append({
                    'section': current_section,
                    'date': date,
                    'event': event,
                    'description': description,
                    'category': category,
                    'documents': documents
                })
    except Exception as e:
        # Log error but don't fail
        pass
    
    return events


def validate_timeline_events(events):
    """
    Validate timeline events for required fields and date format.
    
    Expected format: Each event should have date, event, description, category, documents.
    Date should be in YYYY-MM-DD format.
    
    Args:
        events (list): List of event dicts to validate
        
    Raises:
        ValueError: If events are missing required fields or have invalid dates
        
    Returns:
        bool: True if all events are valid
    """
    from datetime import datetime
    
    for i, event in enumerate(events):
        # Check required fields
        required_fields = ['date', 'event', 'description', 'category', 'documents']
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
