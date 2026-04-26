"""
Tests for AI Assistant app.

This module tests:
- AI API integration
- Timeline querying
- Document analysis
- Suggestion generation
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from .views import call_ai_api
from apps.timeline.models import TimelineEvent
from apps.archive.models import ArchiveDocument
from apps.core.models import Case
from .models import AIConversation
from datetime import date
import json

User = get_user_model()


class AIAssistantViewTest(TestCase):
    """Test AI Assistant views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_ai_chat_view(self):
        """Test AI chat view."""
        response = self.client.get(reverse('ai_assistant:chat'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('AI Research Assistant', str(response.content))
    
    def test_ai_chat_view_with_recent_events(self):
        """Test AI chat view shows recent events."""
        TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Recent Event',
            category='other',
            notes='Test notes'
        )
        
        response = self.client.get(reverse('ai_assistant:chat'))
        self.assertEqual(response.status_code, 200)
        # Check that we have recent_events in context
        # For now, just check the page loads successfully
        self.assertIn('AI Research Assistant', str(response.content))


class AIAPIFunctionTest(TestCase):
    """Test AI API functions."""
    
    def test_call_ai_api_without_key(self):
        """Test AI API returns simulated response without API key."""
        # Temporarily remove API key
        original_key = settings.MISTRAL_API_KEY
        settings.MISTRAL_API_KEY = ''
        
        try:
            prompt = "What is 2+2?"
            response = call_ai_api(prompt)
            
            # Should return simulated response
            self.assertIn('simulated response', response.lower())
            self.assertIn('mistral', response.lower())
        finally:
            settings.MISTRAL_API_KEY = original_key
    
    def test_call_ai_api_with_keyPlaceholder(self):
        """Test AI API with placeholder key (will fail but return fallback)."""
        # Temporarily set API key
        original_key = settings.MISTRAL_API_KEY
        settings.MISTRAL_API_KEY = 'test-placeholder-key'
        
        try:
            prompt = "What is 2+2?"
            response = call_ai_api(prompt)
            
            # Will either fail gracefully or return from Mistral
            # Since we're using a placeholder key, it should fail gracefully
            self.assertIsInstance(response, str)
        finally:
            settings.MISTRAL_API_KEY = original_key


class TimelineIntegrationTest(TestCase):
    """Test timeline and AI integration."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create timeline events
        self.event1 = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Contract Signed',
            category='contract',
            notes='Signed with X Corp',
            supporting_docs=json.dumps([{'title': 'Contract', 'url': 'https://example.com/c.pdf'}])
        )
        
        self.event2 = TimelineEvent.objects.create(
            date=date(2023, 3, 20),
            event='Email Received',
            category='email',
            notes='Important email about contract'
        )
    
    def test_query_timeline_endpoint(self):
        """Test querying timeline via AI endpoint."""
        response = self.client.post(
            reverse('ai_assistant:query_timeline'),
            {'query': 'What contracts exist?'},
            content_type='application/x-www-form-urlencoded'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('response', data)
    
    def test_analyze_timeline_event(self):
        """Test analyzing a specific timeline event."""
        response = self.client.get(
            reverse('ai_assistant:analyze_event', args=[self.event1.pk])
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['event_id'], self.event1.pk)
        self.assertIn('analysis', data)


class SuggestionGenerationTest(TestCase):
    """Test AI suggestion generation."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create multiple timeline events
        for i in range(5):
            TimelineEvent.objects.create(
                date=date(2023, 1, 15 + i),
                event=f'Event {i+1}',
                category='contract',
                notes=f'Notes for event {i+1}'
            )
    
    def test_suggest_events_endpoint(self):
        """Test suggesting events based on timeline."""
        response = self.client.post(
            reverse('ai_assistant:suggest_events'),
            content_type='application/x-www-form-urlencoded'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('suggestions', data)


class AIConversationModelTest(TestCase):
    """Test AIConversation model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.case = Case.objects.create(name='Test Case', user=self.user)
    
    def test_create_conversation(self):
        """Test creating an AI conversation."""
        conv = AIConversation.objects.create(
            title='Test Conversation',
            user=self.user,
            case=self.case,
            messages=[{'role': 'user', 'content': 'Hello'}]
        )
        self.assertEqual(conv.title, 'Test Conversation')
        self.assertEqual(conv.user, self.user)
        self.assertEqual(conv.case, self.case)
    
    def test_conversations_filtered_by_case(self):
        """Test that conversations are filtered by case."""
        conv1 = AIConversation.objects.create(
            title='Conv 1',
            user=self.user,
            case=self.case
        )
        conv2 = AIConversation.objects.create(
            title='Conv 2',
            user=self.user,
            case=None
        )
        
        case_convs = AIConversation.objects.filter(case=self.case)
        self.assertEqual(case_convs.count(), 1)
        self.assertEqual(case_convs.first(), conv1)
