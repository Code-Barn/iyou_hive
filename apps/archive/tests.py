"""
Tests for Archive app.

This module tests:
- ArchiveDocument model functionality
- Document upload
- Document retrieval
- Document linking to timeline
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import ArchiveDocument
from apps.timeline.models import TimelineEvent
from datetime import date
import json

User = get_user_model()


class ArchiveDocumentModelTest(TestCase):
    """Test ArchiveDocument model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a test file
        self.test_file = SimpleUploadedFile(
            'test_document.pdf',
            b'Test PDF content',
            content_type='application/pdf'
        )
    
    def test_document_creation(self):
        """Test creating an archive document."""
        doc = ArchiveDocument.objects.create(
            title='Test Document',
            file=self.test_file,
            file_type='pdf',
            category='contract',
            description='Test description',
            tags=['test', 'contract'],
            metadata={'author': 'Test Author'},
            uploader=self.user
        )
        
        self.assertEqual(doc.title, 'Test Document')
        self.assertEqual(doc.file_type, 'pdf')
        self.assertEqual(str(doc), 'Test Document (pdf)')
    
    def test_document_file_methods(self):
        """Test document file helper methods."""
        doc = ArchiveDocument.objects.create(
            title='Contract.pdf',
            file=self.test_file,
            file_type='pdf',
            uploader=self.user
        )
        
        self.assertTrue(doc.is_pdf())
        self.assertFalse(doc.is_image())
        self.assertEqual(doc.get_file_extension(), 'pdf')
    
    def test_image_document(self):
        """Test image document type."""
        image_file = SimpleUploadedFile(
            'test_image.png',
            b'Test image content',
            content_type='image/png'
        )
        
        doc = ArchiveDocument.objects.create(
            title='Test Image',
            file=image_file,
            file_type='image',
            uploader=self.user
        )
        
        self.assertTrue(doc.is_image())
        self.assertFalse(doc.is_pdf())
        self.assertEqual(doc.get_file_extension(), 'png')
    
    def test_document_ordering(self):
        """Test that documents are ordered by upload date desc."""
        doc1 = ArchiveDocument.objects.create(
            title='Doc 1',
            file=self.test_file,
            file_type='pdf',
            uploader=self.user
        )
        doc2 = ArchiveDocument.objects.create(
            title='Doc 2',
            file=self.test_file,
            file_type='pdf',
            uploader=self.user
        )
        
        docs = ArchiveDocument.objects.all()
        self.assertEqual(docs[0].title, 'Doc 2')  # Most recent first
        self.assertEqual(docs[1].title, 'Doc 1')


class DocumentUploadTest(TestCase):
    """Test document upload functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_upload_view_requires_login(self):
        """Test that upload view requires login."""
        # Log out first
        self.client.logout()
        response = self.client.get(reverse('archive:upload'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_archive_view_requires_login(self):
        """Test that archive view requires login."""
        # Log out first
        self.client.logout()
        response = self.client.get(reverse('archive:archive'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)


class DocumentLinkingTest(TestCase):
    """Test linking documents to timeline events."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create documents
        self.doc1 = ArchiveDocument.objects.create(
            title='Contract',
            file=SimpleUploadedFile('contract.pdf', b'content'),
            file_type='pdf',
            category='contract',
            uploader=self.user
        )
        
        self.doc2 = ArchiveDocument.objects.create(
            title='Email',
            file=SimpleUploadedFile('email.pdf', b'content'),
            file_type='pdf',
            category='email',
            uploader=self.user
        )
        
        # Create event
        self.event = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Event with Documents',
            category='contract',
            supporting_docs=json.dumps([self.doc1.id, self.doc2.id])
        )
    
    def test_document_to_event_linking(self):
        """Test linking documents to timeline events."""
        # Link documents via foreign key
        self.doc1.timeline_event = self.event
        self.doc1.save()
        self.doc2.timeline_event = self.event
        self.doc2.save()
        
        # Verify linking
        docs = ArchiveDocument.objects.filter(timeline_event=self.event)
        self.assertEqual(docs.count(), 2)
        
        # Verify event can access documents
        linked_docs = self.event.get_archive_documents()
        self.assertEqual(len(linked_docs), 2)


class DocumentFileTypesTest(TestCase):
    """Test document file type detection."""
    
    def test_all_file_types(self):
        """Test all supported file types."""
        file_types = [
            ('pdf', 'application/pdf', True, False),
            ('jpg', 'image/jpeg', False, True),
            ('png', 'image/png', False, True),
            ('gif', 'image/gif', False, True),
            ('doc', 'application/msword', False, False),
            ('docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', False, False),
            ('txt', 'text/plain', False, False),
        ]
        
        for ext, content_type, is_pdf_expected, is_image_expected in file_types:
            filename = f'test.{ext}'
            file = SimpleUploadedFile(filename, b'content', content_type=content_type)
            
            doc = ArchiveDocument.objects.create(
                title=f'Test {ext.upper()}',
                file=file,
                file_type=ext if ext in ['pdf', 'image', 'text', 'word'] else 'other'
            )
            
            self.assertEqual(doc.is_pdf(), is_pdf_expected, f'Failed for {ext}')
            self.assertEqual(doc.is_image(), is_image_expected, f'Failed for {ext}')
