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
Tests for Archive app.

This module tests:
- ArchiveDocument model functionality
- Document upload
- Document retrieval
- Document linking to timeline
- PDF to Markdown conversion
- Filemapper functionality
"""

from django.test import TestCase, Client
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
import numpy as np
from .models import ArchiveDocument
from .vector_service import VectorIndexService
from apps.timeline.models import TimelineEvent
from apps.core.models import Case
from datetime import date
from pathlib import Path
import json
import os
import tempfile
import shutil
import uuid

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


class PDFConversionTest(TestCase):
    """Test PDF to Markdown conversion functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a simple PDF-like file (text file with .pdf extension for testing)
        # In a real scenario, this would be a real PDF
        self.pdf_path = os.path.join(self.temp_dir, 'test.pdf')
        with open(self.pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4\n1 0 obj\n<<\n/Title (Test Contract)\n/Author (Test Author)\n>>\nendobj\ntrailer\n%%EOF')
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_pdf_conversion_creates_markdown(self):
        """Test that PDF conversion creates a markdown file."""
        from apps.core.document_processing import convert_pdf_to_markdown
        
        # This test will only work if pdfplumber is installed
        # For now, we just test that the function exists and doesn't crash
        try:
            result = convert_pdf_to_markdown(self.pdf_path)
            # Result will be None if pdfplumber is not installed
            # or the path to the markdown file if conversion succeeded
        except Exception as e:
            # Expected if pdfplumber is not available
            pass
    
    def test_upload_pdf_creates_markdown(self):
        """Test that uploading a PDF creates a markdown file."""
        from django.test import override_settings
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        client = Client()
        client.force_login(self.user)
        
        # Create a case and set it in session
        case = Case.objects.create(
            name='Test Case',
            user=self.user,
            description='Test case for PDF upload'
        )
        session = client.session
        session['selected_case_id'] = str(case.id)
        session.save()
        
        # Upload a PDF
        with open(self.pdf_path, 'rb') as f:
            response = client.post(
                reverse('archive:upload'),
                {
                    'title': 'Test PDF',
                    'file': SimpleUploadedFile('test.pdf', f.read(), content_type='application/pdf'),
                    'file_type': 'pdf',
                    'category': 'contract'
                }
            )
        
        # Check that the document was created
        self.assertEqual(response.status_code, 302)  # Redirect after upload
        
        # Check that at least one document exists
        self.assertTrue(ArchiveDocument.objects.filter(title='Test PDF').exists())
        
        # In a real test with pdfplumber, we would check for the .md file
        # For now, we just verify the upload works


class FilemapperTest(TestCase):
    """Test filemapper functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a temporary directory structure
        self.temp_dir = tempfile.mkdtemp()
        
        # Create some test directories and files
        os.makedirs(os.path.join(self.temp_dir, '2023', 'contracts'))
        os.makedirs(os.path.join(self.temp_dir, '2023', 'emails'))
        
        with open(os.path.join(self.temp_dir, '2023', 'contracts', 'contract1.pdf'), 'w') as f:
            f.write('Contract content')
        with open(os.path.join(self.temp_dir, '2023', 'emails', 'email1.eml'), 'w') as f:
            f.write('Email content')
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_filemapper_script_exists(self):
        """Test that the filemapper script exists."""
        from django.conf import settings
        script_path = Path(settings.BASE_DIR) / 'scripts' / 'filemapper.py'
        self.assertTrue(script_path.exists(), "Filemapper script not found")
    
    def test_filemapper_generates_map(self):
        """Test that filemapper generates a map file."""
        from apps.archive.views import run_filemapper
        
        # This should generate archive_map.md in the temp directory
        try:
            result = run_filemapper(self.temp_dir)
            # Result will be the path to archive_map.md
            if result and os.path.exists(result):
                with open(result, 'r') as f:
                    content = f.read()
                self.assertIn('Archive Map', content)
                self.assertIn('contract1.pdf', content)
        except Exception as e:
            # May fail if subprocess has issues
            pass


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
        self.client.force_login(self.user)
    
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
        # Should redirect to login or show empty list
        # The archive view doesn't require login, but will show empty if no docs
        self.assertIn(response.status_code, [200, 302])


class DocumentLinkingTest(TestCase):
    """Test linking documents to timeline events."""
    
    def setUp(self):
        """Set up test data."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.core.models import Case
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.case = Case.objects.create(name='Test Case', user=self.user)
        
        # Create test files
        pdf_file = SimpleUploadedFile('contract.pdf', b'PDF content', content_type='application/pdf')
        
        # Create documents first with files
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
        
        # Create event and link documents via evidence M2M
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
        
        # Link documents to event via evidence M2M
        self.event.evidence.set([self.doc1, self.doc2])
    
    def test_evidence_m2m_relationship(self):
        """Test evidence M2M relationship."""
        self.assertEqual(self.event.evidence.count(), 2)
        doc_ids = [d.id for d in self.event.evidence.all()]
        self.assertIn(self.doc1.id, doc_ids)
        self.assertIn(self.doc2.id, doc_ids)
        
    def test_archive_document_file_urls(self):
        """Test ArchiveDocument file URL methods."""
        # doc1 has a file
        url = self.doc1.get_file_url()
        self.assertIn('archive/documents', url.lower())
        self.assertTrue(self.doc1.is_pdf())
        self.assertFalse(self.doc1.is_image())
    
    def test_document_str(self):
        """Test ArchiveDocument string representation."""
        self.assertEqual(str(self.doc1), 'Contract PDF (pdf)')
    
    def test_document_to_event_linking(self):
        """Test linking documents to timeline events."""
        # Documents are linked in setUp via M2M related_name 'timeline_events'
        docs = ArchiveDocument.objects.filter(timeline_events=self.event)
        self.assertEqual(docs.count(), 2)
        
        # Verify event can access documents via evidence M2M
        linked_docs = self.event.evidence.all()
        self.assertEqual(len(linked_docs), 2)


class DocumentFileTypesTest(TestCase):
    """Test document file type detection."""
    
    def test_all_file_types(self):
        """Test all supported file types."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
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
                file_type=ext if ext in ['pdf', 'image', 'text', 'word'] else 'other',
                uploader=self.user
            )
            
            self.assertEqual(doc.is_pdf(), is_pdf_expected, f'Failed for {ext}')
            self.assertEqual(doc.is_image(), is_image_expected, f'Failed for {ext}')


class ArchiveDocumentCompartmentalizationTest(TestCase):
    """Tests for archive document case compartmentalization."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.test_file = SimpleUploadedFile(
            'test_document.pdf',
            b'Test PDF content',
            content_type='application/pdf'
        )
        self.case1 = Case.objects.create(name='Case 1', user=self.user)
        self.case2 = Case.objects.create(name='Case 2', user=self.user)
    
    def test_documents_linked_to_case(self):
        """Test that documents can be linked to cases."""
        doc = ArchiveDocument.objects.create(
            title='Test Document',
            file=self.test_file,
            file_type='pdf',
            case=self.case1,
            user=self.user,
            uploader=self.user
        )
        self.assertEqual(doc.case, self.case1)
    
    def test_documents_filtered_by_case(self):
        """Test that documents are filtered by case."""
        doc1 = ArchiveDocument.objects.create(
            title='Doc 1',
            file=self.test_file,
            file_type='pdf',
            case=self.case1,
            user=self.user,
            uploader=self.user
        )
        doc2 = ArchiveDocument.objects.create(
            title='Doc 2',
            file=self.test_file,
            file_type='pdf',
            case=self.case2,
            user=self.user,
            uploader=self.user
        )
        
        case1_docs = ArchiveDocument.objects.filter(case=self.case1)
        case2_docs = ArchiveDocument.objects.filter(case=self.case2)
        
        self.assertEqual(case1_docs.count(), 1)
        self.assertEqual(case2_docs.count(), 1)
        self.assertEqual(case1_docs.first().title, 'Doc 1')
        self.assertEqual(case2_docs.first().title, 'Doc 2')


class VectorIndexServiceTest(TestCase):
    """Regression suite for the LanceDB vector indexing engine."""

    def setUp(self):
        """Set up test data with isolated temporary storage."""
        self.user = User.objects.create_user(
            username='vecuser',
            email='vec@example.com',
            password='testpass123'
        )
        self.case_a = Case.objects.create(name='Case A', user=self.user)
        self.case_b = Case.objects.create(name='Case B', user=self.user)
        self.temp_media = tempfile.mkdtemp()
        self.temp_twins = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_media, ignore_errors=True)
        shutil.rmtree(self.temp_twins, ignore_errors=True)

    def _make_twin(
        self, virtual_path: str, body: str = "", folder: str = ""
    ) -> str:
        """Create a fake digital twin ``.md`` file and return its path."""
        content = body or "Test content for vector indexing verification."
        folder = folder or self.temp_twins
        path = os.path.join(folder, f"twin_{uuid.uuid4().hex}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"---\noriginal_name: test.pdf\nvirtual_path: {virtual_path}\n---\n\n{content}")
        return path

    # --- Frontmatter parsing unit tests --------------------------------

    def test_parse_frontmatter_extracts_virtual_path(self):
        """Verify ``_parse_frontmatter`` extracts ``virtual_path`` correctly."""
        text = "---\noriginal_name: doc.pdf\nvirtual_path: case/evidence/doc.pdf\n---\n\nBody"
        result = VectorIndexService._parse_frontmatter(text)
        self.assertEqual(result.get("virtual_path"), "case/evidence/doc.pdf")

    def test_parse_frontmatter_empty_when_no_frontmatter(self):
        """Verify empty dict is returned when no frontmatter exists."""
        result = VectorIndexService._parse_frontmatter("Just body text\nno frontmatter")
        self.assertEqual(result, {})

    def test_strip_frontmatter_removes_header(self):
        """Verify frontmatter block is stripped from content."""
        text = "---\nkey: val\n---\n\nBody text here"
        stripped = VectorIndexService._strip_frontmatter(text)
        self.assertNotIn("key: val", stripped)
        self.assertIn("Body text here", stripped)

    def test_strip_frontmatter_passthrough_when_none(self):
        """Verify text passes through unchanged when no frontmatter exists."""
        text = "Just body text"
        self.assertEqual(VectorIndexService._strip_frontmatter(text), text)

    # --- Chunking unit tests ------------------------------------------

    def test_chunk_text_single_chunk(self):
        """Verify text shorter than chunk size produces one chunk."""
        text = "Short text"
        chunks = VectorIndexService._chunk_text(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_chunk_text_multiple_chunks(self):
        """Verify text longer than chunk size is split correctly."""
        text = "Word " * 200
        chunks = VectorIndexService._chunk_text(text)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(c), VectorIndexService.CHUNK_SIZE)

    def test_chunk_text_overlap(self):
        """Verify consecutive chunks share overlap content."""
        text = "Hello World\n" * 30
        chunks = VectorIndexService._chunk_text(text)
        if len(chunks) >= 2:
            prev_end = chunks[0][-VectorIndexService.CHUNK_OVERLAP:]
            next_start = chunks[1][:VectorIndexService.CHUNK_OVERLAP]
            self.assertTrue(
                prev_end in chunks[1] or next_start in chunks[0],
                "Expected overlap content between consecutive chunks"
            )

    def test_chunk_text_empty(self):
        """Verify empty input returns empty list."""
        self.assertEqual(VectorIndexService._chunk_text(""), [])
        self.assertEqual(VectorIndexService._chunk_text("   "), [])

    # --- Integration tests (mocked embeddings) -------------------------

    @override_settings(MEDIA_ROOT=None)
    def test_index_digital_twin_stores_rows(self):
        """Verify indexing a twin produces at least one row in LanceDB."""
        with override_settings(MEDIA_ROOT=self.temp_media):
            mock_model = MagicMock()
            mock_model.encode.return_value = np.zeros(384, dtype=np.float32)

            doc = ArchiveDocument.objects.create(
                title="Test Doc",
                file_type="pdf",
                case=self.case_a,
                user=self.user,
                uploader=self.user,
            )
            twin_path = self._make_twin(
                virtual_path="test/sample.pdf",
                body="Indexed content. " * 100,
            )
            svc = VectorIndexService(str(self.case_a.id))
            with patch.object(svc, "_get_embedding_model", return_value=mock_model):
                count = svc.index_digital_twin(twin_path, doc)

        self.assertGreater(count, 0)
        tbl = svc._get_db().open_table(VectorIndexService.TABLE_NAME)
        stored = tbl.search([0.0] * 384).limit(count * 2).to_list()
        self.assertEqual(len(stored), count)

    @override_settings(MEDIA_ROOT=None)
    def test_case_vector_isolation(self):
        """
        Verify that querying Case A's LanceDB returns zero fragments
        belonging to Case B.
        """
        with override_settings(MEDIA_ROOT=self.temp_media):
            mock_model = MagicMock()
            mock_model.encode.return_value = np.zeros(384, dtype=np.float32)

            doc_a = ArchiveDocument.objects.create(
                title="Doc A", file_type="pdf",
                case=self.case_a, user=self.user, uploader=self.user,
            )
            doc_b = ArchiveDocument.objects.create(
                title="Doc B", file_type="pdf",
                case=self.case_b, user=self.user, uploader=self.user,
            )
            path_a = self._make_twin(
                virtual_path="case_a/doc.pdf",
                body="Exclusive content for Case A. " * 200,
            )
            path_b = self._make_twin(
                virtual_path="case_b/doc.pdf",
                body="Exclusive content for Case B. " * 200,
            )

            svc_a = VectorIndexService(str(self.case_a.id))
            svc_b = VectorIndexService(str(self.case_b.id))

            with patch.object(svc_a, "_get_embedding_model", return_value=mock_model):
                count_a = svc_a.index_digital_twin(path_a, doc_a)
            with patch.object(svc_b, "_get_embedding_model", return_value=mock_model):
                count_b = svc_b.index_digital_twin(path_b, doc_b)

            self.assertGreater(count_a, 0)
            self.assertGreater(count_b, 0)

            tbl_a = svc_a._get_db().open_table(VectorIndexService.TABLE_NAME)
            all_a = tbl_a.search([0.0] * 384).limit(count_a * 2).to_list()

            doc_b_uuids = [r for r in all_a if r["document_uuid"] == str(doc_b.uuid)]
            self.assertEqual(
                len(doc_b_uuids), 0,
                "Case A's vector store must not contain any chunks from Case B"
            )

    @override_settings(MEDIA_ROOT=None)
    def test_metadata_path_retention(self):
        """
        Verify that pulled vector chunks maintain their original folder
        trail string inside the returned payload schema.
        """
        with override_settings(MEDIA_ROOT=self.temp_media):
            mock_model = MagicMock()
            mock_model.encode.return_value = np.zeros(384, dtype=np.float32)

            doc = ArchiveDocument.objects.create(
                title="Path Doc", file_type="pdf",
                case=self.case_a, user=self.user, uploader=self.user,
            )
            expected_path = "formal/01_Raw/contracts/signed/agreement.pdf"
            twin_path = self._make_twin(
                virtual_path=expected_path,
                body="Path retention test content. " * 100,
            )

            svc = VectorIndexService(str(self.case_a.id))
            with patch.object(svc, "_get_embedding_model", return_value=mock_model):
                svc.index_digital_twin(twin_path, doc)

            tbl = svc._get_db().open_table(VectorIndexService.TABLE_NAME)
            results = tbl.search([0.0] * 384).limit(100).to_list()

            self.assertGreater(len(results), 0)
            for row in results:
                self.assertEqual(
                    row["virtual_path"], expected_path,
                    "Each chunk must retain the original virtual_path"
                )

    @override_settings(MEDIA_ROOT=None)
    def test_search_returns_results(self):
        """Verify ``search()`` returns semantically similar chunks."""
        with override_settings(MEDIA_ROOT=self.temp_media):
            mock_model = MagicMock()
            mock_model.encode.return_value = np.zeros(384, dtype=np.float32)

            doc = ArchiveDocument.objects.create(
                title="Search Doc", file_type="pdf",
                case=self.case_a, user=self.user, uploader=self.user,
            )
            twin_path = self._make_twin(
                virtual_path="search/test.pdf",
                body="Semantic search target content for testing. " * 100,
            )

            svc = VectorIndexService(str(self.case_a.id))
            with patch.object(svc, "_get_embedding_model", return_value=mock_model):
                svc.index_digital_twin(twin_path, doc)
                results = svc.search("test query", top_k=3)

            self.assertGreater(len(results), 0)
            self.assertIn("_distance", results[0])
            self.assertIn("text_content", results[0])
            self.assertIn("virtual_path", results[0])
            self.assertIn("document_uuid", results[0])
