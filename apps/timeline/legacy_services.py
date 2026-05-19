# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Timeline Services for Competing Timelines.

Provides:
- MarkdownIngestionService: Parses 5-column markdown into TimelineEvent + evidence M2M
- MarkdownExportService: Exports TimelineEvent to 5-column markdown
- sync_timeline_file: Re-parse and sync timeline files
"""

import logging
from django.db import transaction, models
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError

from .models import TimelineEvent
from apps.core.models import TimelineFile, Case
from apps.archive.models import ArchiveDocument

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class PotentialMatchException(Exception):
    """Raised when ingestion finds potential duplicate events."""
    def __init__(self, message: str, matches: models.QuerySet):
        super().__init__(message)
        self.matches = matches


class IngestionValidationError(Exception):
    """Raised when markdown content fails validation."""
    pass


# ============================================================================
# MarkdownIngestionService
# ============================================================================

class MarkdownIngestionService:
    """
    Service for ingesting 5-column markdown timeline files.
    Parses directly into TimelineEvent with evidence M2M relationships.
    """

    @classmethod
    def find_potential_matches(cls, event_data: dict, case: Case) -> models.QuerySet:
        """
        Find existing events that might match this new event.
        Match on: case + date + event title (exact and fuzzy).
        """
        date_str = event_data.get('date', '')
        event_title = event_data.get('event', '').strip()

        if not date_str or not event_title:
            return TimelineEvent.objects.none()

        # Parse date
        date_obj = cls._parse_date(date_str)
        if not date_obj:
            return TimelineEvent.objects.none()

        # Exact match
        exact_matches = TimelineEvent.objects.filter(
            case=case,
            date=date_obj,
            event__iexact=event_title
        )

        if exact_matches.exists():
            return exact_matches

        # Fuzzy match: same date, title contains keywords
        words = [w for w in event_title.split() if len(w) > 3]
        if words:
            fuzzy_matches = TimelineEvent.objects.filter(
                case=case,
                date=date_obj
            )
            for word in words:
                fuzzy_matches = fuzzy_matches.filter(event__icontains=word)
            return fuzzy_matches

        # Date range match: +/- 1 day
        return TimelineEvent.objects.filter(
            case=case,
            date__range=[date_obj - timedelta(days=1), date_obj + timedelta(days=1)]
        ).filter(event__icontains=event_title)

    @classmethod
    def _parse_date(cls, date_str: str):
        """Parse date string into date object."""
        if not date_str:
            return None
        for fmt in ['%Y-%m-%d', '%Y-%m', '%Y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        try:
            year = int(date_str[:4])
            return datetime(year, 1, 1).date()
        except (ValueError, IndexError):
            return None

    @classmethod
    def ingest_markdown_file(cls, file_path: str, case: Case, user, 
                            timeline_file: TimelineFile = None,
                            source_party: str = 'CLIENT') -> dict:
        """
        Ingest a 5-column markdown file.
        Returns: {created, updated, skipped, matches, warnings}
        """
        from .utils import parse_markdown_file
        import os

        if not os.path.exists(file_path):
            return {
                'error': f'File not found: {file_path}',
                'created': 0, 'updated': 0, 'skipped': 0,
                'matches': [], 'warnings': [f'File not found: {file_path}']
            }

        try:
            parsed = parse_markdown_file(file_path)
        except Exception as e:
            return {
                'error': f'Parse failed: {e}',
                'created': 0, 'updated': 0, 'skipped': 0,
                'matches': [], 'warnings': [f'Parse error: {e}']
            }

        # Collect all events from parsed data
        all_events = list(parsed.get('events', []))
        for timeline_events in parsed.get('timelines', {}).values():
            all_events.extend(timeline_events)

        created_count = 0
        updated_count = 0
        skipped_count = 0
        matches_found = []
        warnings = []

        for event_data in all_events:
            try:
                # Find potential duplicates
                potential_matches = cls.find_potential_matches(event_data, case)
                
                if potential_matches.exists():
                    matches_found.append({
                        'event_data': event_data,
                        'matches': list(potential_matches.values(
                            'id', 'date', 'event', 'source_party', 'status'
                        ))
                    })
                    skipped_count += 1
                    warnings.append(
                        f"Potential duplicate: {event_data.get('date')} / {event_data.get('event')}"
                    )
                    continue
                
                # Smart attribution: use section header context
                section_header = event_data.get('section_header')
                if section_header:
                    # Determine source_party based on section context
                    if 'pauletta' in section_header.lower():
                        source_party = 'OPPOSING'
                    elif 'david' in section_header.lower():
                        source_party = 'CLIENT'
                    # else: keep provided source_party parameter
                
                # Create the event
                event, was_created = cls.create_timeline_event(
                    event_data=event_data,
                    case=case,
                    user=user,
                    timeline_file=timeline_file,
                    source_party=source_party
                )

                if was_created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                logger.error(f"Ingest failed for {event_data.get('event', '?')}: {e}")
                skipped_count += 1
                warnings.append(f"Ingest failed: {event_data.get('event', '?')}: {e}")

        return {
            'created': created_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'matches': matches_found,
            'warnings': warnings
        }

    @classmethod
    def create_timeline_event(cls, event_data: dict, case: Case, user,
                             timeline_file: TimelineFile = None,
                             source_party: str = 'CLIENT') -> tuple:
        """
        Create TimelineEvent from parsed 5-column data.
        Links evidence via M2M.
        Implements smart attribution logic based on event text.
        Returns: (TimelineEvent, bool_created)
        """
        date_obj = cls._parse_date(event_data.get('date', ''))
        if not date_obj:
            date_obj = timezone.now().date()
        
        event_title = (event_data.get('event') or event_data.get('title') or '').strip()
        if not event_title:
            raise ValueError("Event title required")
        
        # Truncate event title to 255 characters (model max_length)
        if len(event_title) > 255:
            event_title = event_title[:252] + '...'
        
        # Validate category against model choices
        valid_categories = [choice[0] for choice in TimelineEvent.CATEGORY_CHOICES]
        category = (event_data.get('category') or 'other').lower()
        if category not in valid_categories:
            category = 'other'
        
        notes = event_data.get('notes') or event_data.get('description') or ''
        citation = event_data.get('citation') or ''
        evidence_data = event_data.get('evidence') or event_data.get('documents') or ''
        
        # Get section header from parsed data
        section_header = event_data.get('section_header') or None
        
        # SMART ATTRIBUTION LOGIC
        # Determine source_party based on event text content
        event_text = (event_title + ' ' + notes).lower()
        
        # First try the existing keyword matching
        has_david = 'david' in event_text
        has_pauletta = 'pauletta' in event_text or 'pauletta' in event_text
        
        if has_pauletta and not has_david:
            source_party = 'OPPOSING'  # Pauletta mentioned without David -> Opposing
        elif has_david and not has_pauletta:
            source_party = 'CLIENT'     # David mentioned without Pauletta -> Client
        elif has_david and has_pauletta:
            # Both mentioned - use section context or default to NEUTRAL
            if section_header:
                if 'pauletta' in section_header.lower():
                    source_party = 'OPPOSING'
                elif 'david' in section_header.lower():
                    source_party = 'CLIENT'
                else:
                    source_party = 'NEUTRAL'
            else:
                source_party = 'NEUTRAL'  # Both mentioned, no clear context
        else:
            # No clear keywords - try AI classification
            try:
                from apps.ai_assistant.services import AIService
                source_party = AIService.classify_party(event_text, section_header)
            except ImportError:
                source_party = 'NEUTRAL'  # Default fallback
        
        # Determine status from category if not specified
        status = event_data.get('status', 'UNDISPUTED')
        if status == 'UNDISPUTED' and category in ['contested', 'refuted']:
            status = category.upper()
        
        defaults = {
            'category': category,
            'notes': notes,
            'citation': citation,
            'source_type': 'MARKDOWN',
            'status': status,
            'source_party': source_party,
            'section_header': section_header,  # Store section header
            'created_by': user,
            'timeline_file': timeline_file,
        }
        
        with transaction.atomic():
            event, created = TimelineEvent.objects.update_or_create(
                case=case,
                date=date_obj,
                event=event_title,
                source_party=source_party,
                defaults=defaults
            )
            
            # Link evidence documents
            if evidence_data:
                cls._link_evidence(event, evidence_data, case)
        
        return event, created

    @classmethod
    def _link_evidence(cls, event: TimelineEvent, docs_data, case: Case):
        """Link ArchiveDocument objects to event.evidence M2M."""
        doc_ids = []

        if isinstance(docs_data, str):
            docs_data = [docs_data]

        for item in docs_data:
            if isinstance(item, int):
                doc_ids.append(item)
            elif isinstance(item, dict):
                doc_id = item.get('id')
                if doc_id:
                    doc_ids.append(doc_id)
            elif isinstance(item, str):
                # Try to parse as ArchiveDocument ID
                try:
                    doc_ids.append(int(item))
                except ValueError:
                    # Try to find by title
                    doc = ArchiveDocument.objects.filter(
                        title__iexact=item.strip(),
                        case=case
                    ).first()
                    if doc:
                        doc_ids.append(doc.id)

        if doc_ids:
            try:
                docs = ArchiveDocument.objects.filter(id__in=doc_ids, case=case)
                event.evidence.set(docs)
            except Exception as e:
                logger.warning(f"Failed to link evidence to event {event.id}: {e}")


# ============================================================================
# MarkdownExportService
# ============================================================================

class MarkdownExportService:
    """
    Export TimelineEvent to 5-column markdown.
    Only uses relational fields - no fallback logic.
    """

    @classmethod
    def export_party_timeline(cls, case: Case, party: str = None) -> str:
        """Export timeline as 5-column markdown for specified party."""
        if party:
            events = TimelineEvent.objects.filter(
                case=case, source_party=party
            ).select_related('replaces_event').prefetch_related('evidence').order_by('date')
            title = f"{case.name} - {party} Perspective"
        else:
            events = TimelineEvent.objects.filter(
                case=case
            ).select_related('replaces_event').prefetch_related('evidence').order_by('date')
            title = f"{case.name} - Full Timeline"

        lines = []
        lines.append("---")
        lines.append(f'title: "{title}"')
        lines.append(f"case_id: {case.id}")
        if party:
            lines.append(f"party: {party}")
        lines.append(f"exported: {timezone.now().isoformat()}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {title}")
        lines.append("")
        lines.append("| Date | Event/Incident | Category | Supporting Docs | Notes |")
        lines.append("|------|---------------|----------|----------------|-------|")

        for event in events:
            lines.append(cls._format_event_row(event))

        # Append contested/refuted section
        contested = [e for e in events if e.status in ['CONTESTED', 'REFUTED']]
        if contested:
            lines.append("")
            lines.append("## Contested and Refuted Events")
            lines.append("")
            for event in contested:
                lines.append(f"### {event.event} ({event.date})")
                lines.append(f"- **Status:** {event.get_status_display()}")
                lines.append(f"- **Party:** {event.get_source_party_display()}")
                if event.replaces_event:
                    lines.append(f"- **Replaces:** {event.replaces_event.event} ({event.replaces_event.date})")
                if event.evidence.exists():
                    lines.append("- **Evidence:**")
                    for doc in event.evidence.all():
                        lines.append(f"  - [{doc.title}]({doc.get_file_url()})")
                if event.notes:
                    lines.append(f"- **Notes:** {event.notes}")
                lines.append("")

        return '\n'.join(lines)

    @classmethod
    def _format_event_row(cls, event: TimelineEvent) -> str:
        """Format single event as 5-column table row."""
        date = event.date.strftime('%Y-%m-%d')
        event_title = event.event.replace('|', '\\|')
        category = event.get_category_display()

        # Format evidence as markdown links
        doc_links = []
        for doc in event.evidence.all():
            title = doc.title.replace('|', '\\|')
            doc_links.append(f"[{title}]({doc.get_file_url()})")
        evidence_column = ', '.join(doc_links) if doc_links else ''

        notes = event.notes.replace('|', '\\|') if event.notes else ''

        return f"| {date} | {event_title} | {category} | {evidence_column} | {notes} |"

    @classmethod
    def export_full_case_timeline(cls, case: Case) -> str:
        """Export all parties' timelines grouped by source_party."""
        from django.db.models import Count

        lines = []
        lines.append("---")
        lines.append(f'title: "{case.name} - Complete Timeline"')
        lines.append(f"case_id: {case.id}")
        lines.append(f"exported: {timezone.now().isoformat()}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {case.name} - Complete Timeline")
        lines.append("")

        # Group by source_party
        parties = TimelineEvent.objects.filter(case=case).values('source_party')\
            .annotate(count=Count('id')).order_by('source_party')

        for p in parties:
            party = p['source_party']
            if party:
                party_display = dict(TimelineEvent.SOURCE_PARTY_CHOICES).get(party, party)
                lines.append(f"## {party_display}")
                lines.append("")
                party_events = TimelineEvent.objects.filter(
                    case=case, source_party=party
                ).prefetch_related('evidence').order_by('date')
                lines.append("| Date | Event/Incident | Category | Supporting Docs | Notes |")
                lines.append("|------|---------------|----------|----------------|-------|")
                for event in party_events:
                    lines.append(cls._format_event_row(event))
                lines.append("")

        # Contested events summary
        contested = TimelineEvent.objects.filter(
            case=case, status__in=['CONTESTED', 'REFUTED']
        ).prefetch_related('evidence', 'replaces_event').order_by('date')

        if contested.exists():
            lines.append("## Disputed Events")
            lines.append("")
            for event in contested:
                lines.append(f"### {event.event} ({event.date})")
                lines.append(f"- **Status:** {event.get_status_display()}")
                lines.append(f"- **Party:** {event.get_source_party_display()}")
                if event.replaces_event:
                    lines.append(f"- **Replaces:** {event.replaces_event.event} ({event.replaces_event.date})")
                if event.evidence.exists():
                    lines.append("- **Evidence:**")
                    for doc in event.evidence.all():
                        lines.append(f"  - [{doc.title}]({doc.get_file_url()})")
                lines.append("")

        return '\n'.join(lines)


# ============================================================================
# Legacy sync function (updated to use new service)
# ============================================================================

def sync_timeline_file(timeline_file_id, user):
    """Sync a TimelineFile: re-parse and update all events."""
    try:
        timeline_file = TimelineFile.objects.get(id=timeline_file_id)
    except TimelineFile.DoesNotExist:
        return {'error': 'Timeline file not found'}

    from .utils import parse_markdown_file
    try:
        parsed = parse_markdown_file(timeline_file.file_path)
    except Exception as e:
        return {'error': f'Parse failed: {e}'}

    results = MarkdownIngestionService.ingest_markdown_file(
        file_path=timeline_file.file_path,
        case=timeline_file.case,
        user=user,
        timeline_file=timeline_file
    )

    timeline_file.state = 'SYNCED'
    timeline_file.save(update_fields=['state', 'updated_at'])

    return {'status': 'success', 'timeline_file': timeline_file.name, **results}
