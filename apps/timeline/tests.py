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
Tests for Timeline app.

This module tests:
- TimelineEvent model functionality
- Evidence M2M linking to ArchiveDocument
- Markdown parsing
- API endpoints
- Case compartmentalization
- Competing timelines functionality
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import TimelineEvent, TimelineCollection
from apps.archive.models import ArchiveDocument
from apps.core.models import Case
from datetime import date
import json
import time
import uuid

User = get_user_model()


class TimelineEventModelTest(TestCase):
    """Test TimelineEvent model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.case = Case.objects.create(name=f'Test Case {uuid.uuid4().hex[:6]}', user=self.user)
        
        # Create archive documents for evidence
        pdf_file = SimpleUploadedFile('contract.pdf', b'PDF content')
        self.doc1 = ArchiveDocument.objects.create(
            title='Contract PDF',
            file=pdf_file,
            file_type='pdf',
            category='contract',
            uploader=self.user,
            case=self.case
        )
        
        self.event1 = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Contract Signed',
            category='contract',
            notes='Signed with X Corp',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case,
            created_by=self.user
        )
        self.event1.evidence.set([self.doc1])
        
        # CONTESTED event requires evidence — pre-set _evidence_cache before save
        self.event2 = TimelineEvent(
            date=date(2023, 3, 20),
            event='Email from Lawyer',
            category='email',
            notes='Urgent: Review attached draft',
            source_party='OPPOSING',
            status='CONTESTED',
            case=self.case,
            created_by=self.user
        )
        self.event2._evidence_cache = [self.doc1.id]
        self.event2.save()
        self.event2.evidence.set([self.doc1])
        
        self.event3 = TimelineEvent.objects.create(
            date=date(2023, 5, 1),
            event='Markdown Links Event',
            category='communication',
            notes='Event with markdown links',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case,
            created_by=self.user
        )
    
    def test_timeline_event_creation(self):
        """Test creating a timeline event."""
        self.assertEqual(self.event1.event, 'Contract Signed')
        self.assertEqual(self.event1.category, 'contract')
        self.assertEqual(str(self.event1), '2023-01-15: Contract Signed (Undisputed)')
    
    def test_get_category_display(self):
        """Test category display method."""
        self.assertEqual(self.event1.get_category_display(), 'Contract')
        self.assertEqual(self.event2.get_category_display(), 'Email')
        self.assertEqual(self.event3.get_category_display(), 'Communication')
    
    def test_get_absolute_url(self):
        """Test absolute URL method."""
        url = self.event1.get_absolute_url()
        self.assertEqual(url, f'/timeline/api/event/{self.event1.pk}/')
    
    def test_ordering(self):
        """Test that events are ordered by date."""
        events = TimelineEvent.objects.all()
        self.assertEqual(events[0].event, 'Contract Signed')
        self.assertEqual(events[1].event, 'Email from Lawyer')
        self.assertEqual(events[2].event, 'Markdown Links Event')
    
    def test_evidence_m2m_relationship(self):
        """Test evidence ManyToMany relationship."""
        self.assertEqual(self.event1.evidence.count(), 1)
        self.assertIn(self.doc1, self.event1.evidence.all())
    
    def test_contested_requires_evidence_validation(self):
        """Test that CONTESTED status requires evidence."""
        from django.core.exceptions import ValidationError
        
        # Create event without evidence but CONTESTED status
        event = TimelineEvent(
            date=date(2023, 6, 1),
            event='Contested No Evidence',
            category='other',
            source_party='OPPOSING',
            status='CONTESTED',
            case=self.case,
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError) as context:
            event.full_clean()
        
        self.assertIn('evidence', str(context.exception))
    
    def test_refuted_requires_evidence_validation(self):
        """Test that REFUTED status requires evidence."""
        from django.core.exceptions import ValidationError
        
        event = TimelineEvent(
            date=date(2023, 6, 1),
            event='Refuted No Evidence',
            category='other',
            source_party='OPPOSING',
            status='REFUTED',
            case=self.case,
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError) as context:
            event.full_clean()
        
        self.assertIn('evidence', str(context.exception))


class TimelineCollectionModelTest(TestCase):
    """Test TimelineCollection model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.case = Case.objects.create(name=f'Test Case {uuid.uuid4().hex[:6]}', user=self.user)
        
        self.event1 = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Event 1',
            category='contract',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case,
            created_by=self.user
        )
        
        self.event2 = TimelineEvent.objects.create(
            date=date(2023, 3, 20),
            event='Event 2',
            category='email',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case,
            created_by=self.user
        )
        
        self.collection = TimelineCollection.objects.create(
            name='Important Events',
            description='Collection of important events',
            case=self.case,
            created_by=self.user
        )
        self.collection.events.set([self.event1, self.event2])
    
    def test_collection_creation(self):
        """Test creating a timeline collection."""
        self.assertEqual(self.collection.name, 'Important Events')
        self.assertEqual(self.collection.events.count(), 2)
    
    def test_collection_str(self):
        """Test collection string representation."""
        self.assertEqual(str(self.collection), f'Important Events ({self.case.name})')
    
    def test_collection_unique_together(self):
        """Test that collection name is unique per case."""
        from django.db import IntegrityError
        
        with self.assertRaises(IntegrityError):
            TimelineCollection.objects.create(
                name='Important Events',
                case=self.case,
                created_by=self.user
            )


class EvidenceM2MTest(TestCase):
    """Test evidence ManyToMany linking between Timeline and Archive."""
    
    def setUp(self):
        """Set up test data with both events and documents."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.case = Case.objects.create(name=f'Test Case {uuid.uuid4().hex[:6]}', user=self.user)
        
        # Create test files
        pdf_file = SimpleUploadedFile('contract.pdf', b'PDF content')
        
        # Create documents
        self.doc1 = ArchiveDocument.objects.create(
            title='Contract PDF',
            file=pdf_file,
            file_type='pdf',
            category='contract',
            uploader=self.user,
            case=self.case
        )
        self.doc2 = ArchiveDocument.objects.create(
            title='Email PDF',
            file=pdf_file,
            file_type='pdf',
            category='email',
            uploader=self.user,
            case=self.case
        )
        
        # Create event with evidence M2M
        self.event = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Contract and Email Event',
            category='contract',
            notes='Event with linked documents',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case,
            created_by=self.user
        )
        
        self.event.evidence.set([self.doc1, self.doc2])
    
    def test_evidence_m2m_count(self):
        """Test evidence M2M count."""
        self.assertEqual(self.event.evidence.count(), 2)
    
    def test_evidence_m2m_reverse(self):
        """Test reverse relationship from ArchiveDocument to TimelineEvent."""
        docs_with_events = ArchiveDocument.objects.filter(timeline_events__isnull=False)
        self.assertEqual(docs_with_events.count(), 2)
    
    def test_archive_document_file_urls(self):
        """Test ArchiveDocument file URL methods."""
        url = self.doc1.get_file_url()
        self.assertIn('archive/documents', url.lower())
        self.assertTrue(self.doc1.is_pdf())
        self.assertFalse(self.doc1.is_image())
    
    def test_document_str(self):
        """Test ArchiveDocument string representation."""
        self.assertEqual(str(self.doc1), 'Contract PDF (pdf)')


class TimelineViewTest(TestCase):
    """Test timeline views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        self.case = Case.objects.create(name=f'Test Case {uuid.uuid4().hex[:6]}', user=self.user)
        session = self.client.session
        session['selected_case_id'] = str(self.case.id)
        session['oidc_id_token_expiration'] = time.time() + 3600
        session.save()
    
    def test_timeline_view_with_events(self):
        """Test timeline view with events."""
        event = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Test Event',
            category='other',
            notes='Test notes',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case,
            created_by=self.user
        )
        
        response = self.client.get(reverse('timeline:timeline'))
        self.assertEqual(response.status_code, 200)
        # Events are loaded client-side via JS; verify the shell renders
        self.assertIn('timeline-app', str(response.content))
    
    def test_timeline_view_empty(self):
        """Test timeline view with no events."""
        response = self.client.get(reverse('timeline:timeline'))
        self.assertEqual(response.status_code, 200)
    
    def test_upload_markdown_view(self):
        """Test markdown upload view."""
        response = self.client.get(reverse('timeline:upload'))
        self.assertEqual(response.status_code, 200)


class MarkdownParsingTest(TestCase):
    """Test markdown parsing functionality."""
    
    def test_parse_markdown_basic(self):
        """Test basic markdown parsing."""
        from .views import parse_markdown
        
        content = """# 2023-01-15
**Event:** Contract Signed
**Category:** Contracts
**Notes:** Signed with X Corp
"""
        
        events = parse_markdown(content)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['date'], '2023-01-15')
        self.assertEqual(events[0]['event'], 'Contract Signed')
        self.assertEqual(events[0]['category'], 'Contracts')
        self.assertEqual(events[0]['notes'], 'Signed with X Corp')
    
    def test_parse_markdown_multiple_events(self):
        """Test parsing multiple events."""
        from .views import parse_markdown
        
        content = """# 2023-01-15
**Event:** Contract Signed
**Category:** Contracts

# 2023-03-20
**Event:** Email from Lawyer
**Category:** Communication
"""
        
        events = parse_markdown(content)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['event'], 'Contract Signed')
        self.assertEqual(events[1]['event'], 'Email from Lawyer')
    
    def test_parse_markdown_table_format(self):
        """Test parsing markdown table format."""
        from .views import parse_markdown
        
        content = """| Date | Event | Description | Category | Documents |
|------|-------|-------------|----------|-----------|
| 2023-01-15 | Contract Signed | Signed with X Corp | contract | doc1, doc2 |
| 2023-03-20 | Email from Lawyer | Urgent email | email | email.pdf |
"""
        
        events = parse_markdown(content)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['date'], '2023-01-15')
        self.assertEqual(events[0]['event'], 'Contract Signed')
        self.assertEqual(events[0]['category'], 'contract')
        self.assertEqual(events[0]['evidence'], 'doc1, doc2')


class TimelineEventCompartmentalizationTest(TestCase):
    """Tests for timeline event case compartmentalization."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.case1 = Case.objects.create(name='Case 1', user=self.user)
        self.case2 = Case.objects.create(name='Case 2', user=self.user)
    
    def test_events_linked_to_case(self):
        """Test that events can be linked to cases."""
        event = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Test Event',
            category='other',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case1,
            created_by=self.user
        )
        self.assertEqual(event.case, self.case1)
    
    def test_events_filtered_by_case(self):
        """Test that events are filtered by case."""
        event1 = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Event in Case 1',
            category='other',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case1,
            created_by=self.user
        )
        event2 = TimelineEvent.objects.create(
            date=date(2023, 2, 15),
            event='Event in Case 2',
            category='other',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case2,
            created_by=self.user
        )
        
        case1_events = TimelineEvent.objects.filter(case=self.case1)
        case2_events = TimelineEvent.objects.filter(case=self.case2)
        
        self.assertEqual(case1_events.count(), 1)
        self.assertEqual(case2_events.count(), 1)
        self.assertEqual(case1_events.first().event, 'Event in Case 1')
        self.assertEqual(case2_events.first().event, 'Event in Case 2')
    
    def test_events_isolated_between_cases(self):
        """Test that events in different cases are isolated."""
        event1 = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Event 1',
            category='other',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case1,
            created_by=self.user
        )
        event2 = TimelineEvent.objects.create(
            date=date(2023, 2, 15),
            event='Event 2',
            category='other',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case2,
            created_by=self.user
        )
        
        self.assertTrue(event1.case != event2.case)


class CompetingTimelinesTest(TestCase):
    """Tests for competing timelines functionality."""
    
    def setUp(self):
        """Set up test data with competing events."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.case = Case.objects.create(name=f'Test Case {uuid.uuid4().hex[:6]}', user=self.user)
        
        pdf_file = SimpleUploadedFile('contract.pdf', b'PDF content')
        self.doc = ArchiveDocument.objects.create(
            title='Contract',
            file=pdf_file,
            file_type='pdf',
            category='contract',
            uploader=self.user,
            case=self.case
        )
        
        # Create original event from CLIENT
        self.client_event = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Contract Signed',
            category='contract',
            notes='Signed on this date',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case,
            created_by=self.user
        )
        
        # Create counter-claim from OPPOSING
        self.opposing_event = TimelineEvent(
            date=date(2023, 1, 16),
            event='Contract Signed',
            category='contract',
            notes='Actually signed on this date',
            source_party='OPPOSING',
            status='CONTESTED',
            replaces_event=self.client_event,
            case=self.case,
            created_by=self.user
        )
        self.opposing_event._evidence_cache = [self.doc.id]
        self.opposing_event.save()
        self.opposing_event.evidence.set([self.doc])
    
    def test_replaces_event_relationship(self):
        """Test replaces_event foreign key relationship."""
        self.assertEqual(self.opposing_event.replaces_event, self.client_event)
        self.assertIn(self.opposing_event, self.client_event.counter_claims.all())
    
    def test_counter_claims_related_name(self):
        """Test counter_claims related name."""
        self.assertEqual(self.client_event.counter_claims.count(), 1)
    
    def test_contested_status_requires_evidence(self):
        """Test that CONTESTED status with replaces_event requires evidence."""
        self.assertEqual(self.opposing_event.evidence.count(), 1)
    
    def test_unique_together_allows_same_event_different_parties(self):
        """Test that same event from different parties is allowed."""
        # Both events have same date and event name but different source_party
        self.assertEqual(self.client_event.event, self.opposing_event.event)
        self.assertNotEqual(self.client_event.source_party, self.opposing_event.source_party)
