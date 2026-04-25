from django.test import TestCase
from django.utils import timezone
from .models import TimelineEvent
from .views import parse_markdown


class TimelineEventModelTest(TestCase):
    def test_create_event(self):
        event = TimelineEvent.objects.create(
            date=timezone.now().date(),
            event='Test Event',
            category='Test',
            notes='Test notes'
        )
        self.assertEqual(event.event, 'Test Event')
        self.assertEqual(str(event), f"{event.date}: Test Event")

    def test_ordering(self):
        event1 = TimelineEvent.objects.create(date='2023-01-01', event='First', category='Test')
        event2 = TimelineEvent.objects.create(date='2023-06-01', event='Second', category='Test')
        events = TimelineEvent.objects.all()
        self.assertEqual(events[0].event, 'First')


class ParseMarkdownTest(TestCase):
    def test_parse_basic_event(self):
        content = """# 2023-01-15
**Event:** Contract Signed
**Category:** Contracts
**Notes:** Test note"""
        events = parse_markdown(content)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['event'], 'Contract Signed')

    def test_parse_multiple_events(self):
        content = """# 2023-01-15
**Event:** Event 1
**Category:** Test

# 2023-02-20
**Event:** Event 2
**Category:** Test"""
        events = parse_markdown(content)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['event'], 'Event 1')
        self.assertEqual(events[1]['event'], 'Event 2')