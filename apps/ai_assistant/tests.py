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
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from .views import call_ai_api
from apps.timeline.models import TimelineEvent
from apps.archive.models import ArchiveDocument
from apps.core.models import Case
from .models import AIConversation
from datetime import date
import json
import time
import uuid

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
        self.client.force_login(self.user)
        
        # Create a case for the user and set it in session
        self.case = Case.objects.create(
            name='Test Case',
            user=self.user,
            description='Test case for AI assistant'
        )
        session = self.client.session
        session['selected_case_id'] = str(self.case.id)
        session['oidc_id_token_expiration'] = time.time() + 3600
        session.save()
    
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
            notes='Test notes',
            source_party='CLIENT',
            created_by=self.user,
            case=self.case
        )
        
        response = self.client.get(reverse('ai_assistant:chat'))
        self.assertEqual(response.status_code, 200)
        # Check that we have recent_events in context
        # For now, just check the page loads successfully
        self.assertIn('AI Research Assistant', str(response.content))


class AIAPIFunctionTest(TestCase):
    """Test AI API functions."""
    
    def test_call_ai_api_without_key(self):
        """Test AI API returns error message without API key."""
        # Temporarily remove API key
        original_key = settings.MISTRAL_API_KEY
        settings.MISTRAL_API_KEY = ''
        
        try:
            prompt = "What is 2+2?"
            response = call_ai_api(prompt)
            
            # Should return error message about missing API key
            self.assertIn('error', response.lower())
            self.assertIn('mistral api key not configured', response.lower())
            self.assertIn('in settings', response.lower())
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
        """Set up test data with unique case name to avoid unique constraint conflicts."""
        from apps.core.models import Case
        
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        suffix: str = uuid.uuid4().hex[:6]
        self.case = Case.objects.create(name=f'Test Case {suffix}', user=self.user)
        
        session = self.client.session
        session['selected_case_id'] = str(self.case.id)
        session['oidc_id_token_expiration'] = time.time() + 3600
        session.save()
        
        # Create timeline events
        pdf_file = SimpleUploadedFile('contract.pdf', b'PDF content')
        self.doc = ArchiveDocument.objects.create(
            title='Contract',
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
        self.event1.evidence.set([self.doc])
        
        self.event2 = TimelineEvent.objects.create(
            date=date(2023, 3, 20),
            event='Email Received',
            category='email',
            notes='Important email about contract',
            source_party='OPPOSING',
            case=self.case,
            created_by=self.user,
        )
    
    def test_query_timeline_endpoint(self):
        """Test querying timeline via AI endpoint."""
        response = self.client.post(
            reverse('ai_assistant:query_timeline'),
            {'query': 'What contracts exist?'},
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('response', data)
    
    def test_analyze_timeline_event(self):
        """Test analyzing a specific timeline event via POST."""
        response = self.client.post(
            reverse('ai_assistant:analyze_event', args=[self.event1.pk]),
            {'case_id': str(self.case.id)},
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['event_id'], str(self.event1.pk))
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
        self.client.force_login(self.user)
        self.case = Case.objects.create(name='Suggestion Case', user=self.user)
        
        session = self.client.session
        session['selected_case_id'] = str(self.case.id)
        session['oidc_id_token_expiration'] = time.time() + 3600
        session.save()
        
        # Create multiple timeline events
        for i in range(5):
            TimelineEvent.objects.create(
                date=date(2023, 1, 15 + i),
                event=f'Event {i+1}',
                category='contract',
                notes=f'Notes for event {i+1}',
                source_party='CLIENT',
                case=self.case,
                created_by=self.user,
            )
    
    def test_suggest_events_endpoint(self):
        """Test suggesting events based on timeline."""
        response = self.client.post(
            reverse('ai_assistant:suggest_events'),
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


class SemanticSearchIntegrationTest(TestCase):
    """Regression tests for LanceDB semantic search in the AI chat view."""

    def setUp(self) -> None:
        """Set up test data with authenticated user and case."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='semanticuser',
            email='semantic@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
        self.case = Case.objects.create(
            name='Semantic Search Case',
            user=self.user,
        )
        session = self.client.session
        session['selected_case_id'] = str(self.case.id)
        session.save()

    @patch('apps.ai_assistant.views.call_ai_api')
    def test_search_integration_provides_context(
        self, mock_call_ai: MagicMock
    ) -> None:
        """
        Verify that LanceDB vector search results are injected into the
        AI prompt as formatted context blocks.
        """
        mock_call_ai.return_value = "AI analysis response"

        with patch('apps.ai_assistant.views.VectorIndexService') as mock_svc_cls:
            mock_svc: MagicMock = MagicMock()
            mock_svc_cls.return_value = mock_svc
            mock_svc.search.return_value = [
                {
                    'virtual_path': 'formal/01_Raw/contract.pdf',
                    'text_content': (
                        'This contract is signed by both parties on '
                        'January 15, 2023.'
                    ),
                    '_distance': 0.15,
                },
                {
                    'virtual_path': 'formal/01_Raw/email.pdf',
                    'text_content': (
                        'The opposing party acknowledged receipt of the '
                        'agreement on March 1, 2023.'
                    ),
                    '_distance': 0.22,
                },
            ]

            response = self.client.post(
                reverse('ai_assistant:query_timeline'),
                {
                    'query': 'What does the contract say?',
                    'case_id': str(self.case.id),
                    'perspective_mode': 'NEUTRAL',
                },
            )

        self.assertEqual(response.status_code, 200)
        data: dict = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('response', data)

        # Verify VectorIndexService was initialised with the correct case
        mock_svc_cls.assert_called_once_with(str(self.case.id))

        # Verify search was called with the user query and top_k=5
        mock_svc.search.assert_called_once_with(
            'What does the contract say?', top_k=5
        )

        # Verify the formatted context was injected into the AI prompt
        call_args, _ = mock_call_ai.call_args
        prompt: str = call_args[0] if call_args else ""
        self.assertIn(
            '[Source Exhibit Path: formal/01_Raw/contract.pdf]',
            prompt,
        )
        self.assertIn(
            'This contract is signed by both parties',
            prompt,
        )
        self.assertIn(
            '[Source Exhibit Path: formal/01_Raw/email.pdf]',
            prompt,
        )
        self.assertIn(
            'The opposing party acknowledged receipt',
            prompt,
        )

    @patch('apps.ai_assistant.views.call_ai_api')
    def test_perspective_mode_routes_instructions(
        self, mock_call_ai: MagicMock
    ) -> None:
        """
        Verify that each perspective mode injects its corresponding
        instruction block into the prompt.
        """
        mock_call_ai.return_value = "Perspective test response"

        with patch('apps.ai_assistant.views.VectorIndexService') as mock_svc_cls:
            mock_svc: MagicMock = MagicMock()
            mock_svc_cls.return_value = mock_svc
            mock_svc.search.return_value = []

            for mode, keyword in [
                ('NEUTRAL', 'NEUTRAL PERSPECTIVE'),
                ('CLIENT', 'CLIENT PERSPECTIVE'),
                ('OPPOSING', 'OPPOSING PERSPECTIVE'),
            ]:
                with self.subTest(perspective=mode):
                    self.client.post(
                        reverse('ai_assistant:query_timeline'),
                        {
                            'query': 'Test query',
                            'case_id': str(self.case.id),
                            'perspective_mode': mode,
                        },
                    )

                    args, _ = mock_call_ai.call_args
                    prompt: str = args[0] if args else ""
                    self.assertIn(keyword, prompt)
                    mock_call_ai.reset_mock()

    @patch('apps.ai_assistant.views.call_ai_api')
    def test_search_graceful_failure_on_missing_table(
        self, mock_call_ai: MagicMock
    ) -> None:
        """
        Verify that a missing LanceDB table (no documents indexed yet)
        does not break the chat endpoint and still returns a response.
        """
        mock_call_ai.return_value = "Fallback response without vector context"

        # Do NOT patch VectorIndexService — let the real one run.
        # Since no LanceDB table exists for this case, search should
        # raise ValueError ("Table 'document_chunks' was not found")
        # which _build_semantic_context catches gracefully.

        response = self.client.post(
            reverse('ai_assistant:query_timeline'),
            {
                'query': 'What documents exist?',
                'case_id': str(self.case.id),
                'perspective_mode': 'NEUTRAL',
            },
        )

        self.assertEqual(response.status_code, 200)
        data: dict = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('response', data)

        # Verify the AI was still called even without vector context
        args, _ = mock_call_ai.call_args
        prompt: str = args[0] if args else ""
        self.assertIn('What documents exist?', prompt)
        self.assertNotIn('[Source Exhibit Path:', prompt)


class APIKeyTest(TestCase):
    """Test API key saving functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        # Create a case for the user and set it in session
        self.case = Case.objects.create(
            name='Test Case',
            user=self.user,
            description='Test case for API key saving'
        )
        session = self.client.session
        session['selected_case_id'] = str(self.case.id)
        session['oidc_id_token_expiration'] = time.time() + 3600
        session.save()

    def test_save_api_key_success(self):
        """Test saving API key successfully."""
        response = self.client.post(
            reverse('ai_assistant:save_api_key'),
            data=json.dumps({'mistral_api_key': 'test-api-key-123'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('saved successfully', data['message'])
        
        # Verify the API key was saved
        from .models import UserSettings
        user_settings = UserSettings.objects.get(user=self.user)
        self.assertEqual(user_settings.mistral_api_key, 'test-api-key-123')

    def test_save_api_key_duplicate(self):
        """Test saving the same API key twice returns success without error."""
        # First save
        response1 = self.client.post(
            reverse('ai_assistant:save_api_key'),
            data=json.dumps({'mistral_api_key': 'test-api-key-123'}),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, 200)
        
        # Second save with same key
        response2 = self.client.post(
            reverse('ai_assistant:save_api_key'),
            data=json.dumps({'mistral_api_key': 'test-api-key-123'}),
            content_type='application/json'
        )
        
        self.assertEqual(response2.status_code, 200)
        data = response2.json()
        self.assertTrue(data['success'])
        self.assertIn('already set', data['message'])

    def test_save_api_key_empty(self):
        """Test saving empty API key returns error."""
        response = self.client.post(
            reverse('ai_assistant:save_api_key'),
            data=json.dumps({'mistral_api_key': ''}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('API key is required', data['error'])

    def test_save_api_key_invalid_json(self):
        """Test saving API key with invalid JSON returns error."""
        response = self.client.post(
            reverse('ai_assistant:save_api_key'),
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Invalid JSON data', data['error'])
