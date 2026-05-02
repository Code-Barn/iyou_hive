"""
Timeline Event Ingestion Service

Provides unified ingestion of timeline events from various sources:
- Manual entry via UI
- Markdown file parsing
- AI-generated events

Handles deduplication and syncing to TimelineEvent model (UUID-based).
"""

import logging
from django.db import transaction
from django.utils import timezone
from .models import TimelineEvent
from apps.core.models import TimelineFile, Case

logger = logging.getLogger(__name__)


def ingest_event(event_data, case, user, timeline_file=None, source_type='MANUAL'):
    """
    Ingest a single timeline event with update-or-create logic.
    
    Deduplication is based on: case, date, and event title.
    If an existing event matches, it will be updated with new data.
    
    Args:
        event_data (dict): Event data with keys:
            - date: date string (YYYY-MM-DD) or date object
            - event: event title (str)
            - category: category string (default: 'other')
            - notes: notes text (default: '')
            - supporting_docs: JSON data (default: None)
            - citation: citation text (default: '')
            - source_party: CLIENT/OPPOSING/NEUTRAL (default: None)
        case (Case): The Case object this event belongs to
        user (User): The User creating/updating the event
        timeline_file (TimelineFile, optional): Source TimelineFile object
        source_type (str): Source type (MANUAL, MARKDOWN, AI_GENERATED)
    
    Returns:
        TimelineEvent: The created or updated event
        bool: True if created, False if updated
    """
    from datetime import datetime
    
    # Normalize date
    date = event_data.get('date')
    if isinstance(date, str):
        for fmt in ['%Y-%m-%d', '%Y-%m', '%Y']:
            try:
                date = datetime.strptime(date, fmt).date()
                break
            except ValueError:
                continue
        else:
            logger.warning(f"Could not parse date: {event_data.get('date')}")
            date = timezone.now().date()
    
    event_title = event_data.get('event', '').strip()
    if not event_title:
        raise ValueError("Event title is required")
    
    # Prepare event data
    defaults = {
        'category': event_data.get('category', 'other').lower(),
        'notes': event_data.get('notes', event_data.get('description', '')),
        'supporting_docs': event_data.get('supporting_docs') or event_data.get('documents'),
        'source_type': source_type,
        'created_by': user,
        'timeline_file': timeline_file,
    }
    
    # Add optional fields if present
    if 'citation' in event_data:
        defaults['citation'] = event_data['citation']
    if 'source_party' in event_data:
        defaults['source_party'] = event_data['source_party']
    
    # Deduplication: lookup by case + date + event title
    with transaction.atomic():
        event, created = TimelineEvent.objects.update_or_create(
            case=case,
            date=date,
            event=event_title,
            defaults=defaults
        )
        
        # If updating and source_type is different, keep the original source_type
        # (manual edits should preserve their source type)
        if not created and source_type == 'MARKDOWN':
            event.source_type = source_type
            event.timeline_file = timeline_file
            event.save(update_fields=['source_type', 'timeline_file'])
    
    logger.info(f"{'Created' if created else 'Updated'} event: {event.event} ({event.id})")
    return event, created


def ingest_markdown_events(parsed_data, case, user, timeline_file_obj=None):
    """
    Ingest multiple events from parsed markdown data.
    
    Args:
        parsed_data (dict): Output from parse_markdown_file() with 'events' key
        case (Case): The Case object
        user (User): The User
        timeline_file_obj (TimelineFile, optional): Source TimelineFile
    
    Returns:
        dict: {'created': count, 'updated': count, 'skipped': count, 'events': list}
    """
    events_data = parsed_data.get('events', [])
    timelines_data = parsed_data.get('timelines', {})
    
    # Collect all events from all timelines
    all_events = list(events_data)
    for timeline_name, timeline_events in timelines_data.items():
        all_events.extend(timeline_events)
    
    created_count = 0
    updated_count = 0
    skipped_count = 0
    ingested_events = []
    
    for event_data in all_events:
        try:
            event, was_created = ingest_event(
                event_data,
                case,
                user,
                timeline_file=timeline_file_obj,
                source_type='MARKDOWN'
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1
            ingested_events.append(event)
        except Exception as e:
            logger.error(f"Failed to ingest event {event_data.get('event', 'Unknown')}: {e}")
            skipped_count += 1
    
    return {
        'created': created_count,
        'updated': updated_count,
        'skipped': skipped_count,
        'events': ingested_events,
        'total': len(all_events)
    }


def sync_timeline_file(timeline_file_id, user):
    """
    Sync a TimelineFile: re-parse and update all events.
    
    Args:
        timeline_file_id: UUID of the TimelineFile
        user: The User performing the sync
    
    Returns:
        dict: Sync results
    """
    try:
        timeline_file = TimelineFile.objects.get(id=timeline_file_id)
    except TimelineFile.DoesNotExist:
        return {'error': 'Timeline file not found'}
    
    # Parse the markdown file
    from .utils import parse_markdown_file
    try:
        parsed = parse_markdown_file(timeline_file.file_path)
    except Exception as e:
        return {'error': f'Failed to parse file: {e}'}
    
    # Ingest all events
    results = ingest_markdown_events(
        parsed,
        timeline_file.case,
        user,
        timeline_file_obj=timeline_file
    )
    
    # Update timeline_file state
    timeline_file.state = 'SYNCED'
    timeline_file.save(update_fields=['state', 'updated_at'])
    
    return {
        'status': 'success',
        'timeline_file': timeline_file.name,
        **results
    }
