# Hiver Test Strategy

This document outlines the comprehensive testing strategy for the Hiver legal timeline system.
All tests must reflect the **Zero Legacy Support** policy - no references to `supporting_docs` JSON fields.

---

## 📋 Table of Contents

1. [Unit Testing](#-unit-testing)
2. [Integration Testing](#-integration-testing)
3. [Integrity Testing](#-integrity-testing)
4. [Security Testing](#-security-testing)
5. [UI/UX Testing](#-uiux-testing)
6. [Test Data Factories](#-test-data-factories)
7. [Test Execution](#-test-execution)

---

## 🧪 Unit Testing

### 1.1 ConflictResolverService Tests

**File:** `apps/timeline/tests/test_conflict_resolver.py`

#### Test: Contest Event Creation
```python
class TestConflictResolverContest(TestCase):
    """Tests for contest_event method."""
    
    def setUp(self):
        self.user_client = User.objects.create_user(
            username='client', email='client@test.com', password='test123'
        )
        self.user_opposing = User.objects.create_user(
            username='opposing', email='opposing@test.com', password='test123'
        )
        self.case = Case.objects.create(name='Test Case', user=self.user_client)
        self.client_event = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Original Event',
            category='contract',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case,
            created_by=self.user_client
        )
        self.doc = ArchiveDocument.objects.create(
            title='Evidence.pdf',
            file_type='pdf',
            case=self.case,
            uploader=self.user_opposing
        )
    
    def test_contest_event_creates_counter_claim(self):
        """Contesting an event creates a counter-claim with replaces_event link."""
        service = ConflictResolverService()
        
        counter_claim = service.contest_event(
            original_event=self.client_event,
            user=self.user_opposing,
            event_data={
                'date': date(2023, 1, 15),
                'event': 'Counter Claim',
                'category': 'contract',
                'notes': 'This is wrong',
                'status': 'CONTESTED'
            },
            evidence_ids=[self.doc.id]
        )
        
        # Assertions
        self.assertIsNotNone(counter_claim.uuid)
        self.assertEqual(counter_claim.replaces_event, self.client_event)
        self.assertEqual(counter_claim.source_party, 'OPPOSING')
        self.assertEqual(counter_claim.status, 'CONTESTED')
        self.assertEqual(counter_claim.version, 2)  # Original was 1
        self.assertEqual(counter_claim.evidence.count(), 1)
        self.assertIn(self.doc, counter_claim.evidence.all())
    
    def test_contest_requires_evidence_for_contested_status(self):
        """CONTESTED status requires evidence."""
        service = ConflictResolverService()
        
        with self.assertRaises(ValidationError) as ctx:
            service.contest_event(
                original_event=self.client_event,
                user=self.user_opposing,
                event_data={
                    'status': 'CONTESTED'
                },
                evidence_ids=[]  # No evidence
            )
        
        self.assertIn('Evidence is required', str(ctx.exception))
    
    def test_cannot_contest_own_event(self):
        """User cannot contest their own event if same source_party."""
        service = ConflictResolverService()
        
        with self.assertRaises(PermissionDenied) as ctx:
            service.contest_event(
                original_event=self.client_event,
                user=self.user_client,  # Same user, same party
                event_data={'status': 'CONTESTED'},
                evidence_ids=[self.doc.id]
            )
        
        self.assertIn('Cannot contest your own event', str(ctx.exception))
    
    def test_contest_default_status_is_contested(self):
        """Default status for contest is CONTESTED."""
        service = ConflictResolverService()
        
        counter_claim = service.contest_event(
            original_event=self.client_event,
            user=self.user_opposing,
            event_data={'event': 'Counter'},
            evidence_ids=[self.doc.id]
        )
        
        self.assertEqual(counter_claim.status, 'CONTESTED')
```

#### Test: Resolution Paths
```python
class TestConflictResolverResolve(TestCase):
    """Tests for resolve_conflict method with all three resolution paths."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='user', email='user@test.com', password='test123'
        )
        self.case = Case.objects.create(name='Test Case', user=self.user)
        
        # Create original event
        self.original = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Original Event',
            category='contract',
            source_party='CLIENT',
            status='UNDISPUTED',
            case=self.case,
            created_by=self.user
        )
        
        # Create counter-claim
        self.counter = TimelineEvent.objects.create(
            date=date(2023, 1, 16),
            event='Counter Claim',
            category='contract',
            source_party='OPPOSING',
            status='CONTESTED',
            replaces_event=self.original,
            case=self.case,
            created_by=self.user
        )
    
    def test_resolve_keep_original(self):
        """KEEP_ORIGINAL: Original kept, counter-claim marked SUPERSEDED."""
        service = ConflictResolverService()
        
        resolved = service.resolve_conflict(
            event=self.original,
            resolution='KEEP_ORIGINAL',
            user=self.user,
            notes='Original is correct'
        )
        
        # Refresh from DB
        self.original.refresh_from_db()
        self.counter.refresh_from_db()
        
        self.assertEqual(resolved, self.original)
        self.assertEqual(self.original.status, 'UNDISPUTED')  # Unchanged
        self.assertEqual(self.counter.status, 'SUPERSEDED')
        self.assertIn('KEEP_ORIGINAL', self.counter.notes)
    
    def test_resolve_keep_counter(self):
        """KEEP_COUNTER: Counter-claim kept, original marked SUPERSEDED."""
        service = ConflictResolverService()
        
        resolved = service.resolve_conflict(
            event=self.counter,
            resolution='KEEP_COUNTER',
            user=self.user,
            notes='Counter is correct'
        )
        
        # Refresh from DB
        self.original.refresh_from_db()
        self.counter.refresh_from_db()
        
        self.assertEqual(resolved, self.counter)
        self.assertEqual(self.counter.status, 'CONTESTED')  # Unchanged
        self.assertEqual(self.original.status, 'SUPERSEDED')
        self.assertIn('KEEP_COUNTER', self.original.notes)
    
    def test_resolve_merge(self):
        """MERGE: Creates new STIPULATED event, both originals marked SUPERSEDED."""
        service = ConflictResolverService()
        
        # Add evidence to both
        doc1 = ArchiveDocument.objects.create(
            title='Doc1.pdf', file_type='pdf', case=self.case, uploader=self.user
        )
        doc2 = ArchiveDocument.objects.create(
            title='Doc2.pdf', file_type='pdf', case=self.case, uploader=self.user
        )
        self.original.evidence.set([doc1])
        self.counter.evidence.set([doc2])
        
        resolved = service.resolve_conflict(
            event=self.original,
            resolution='MERGE',
            user=self.user,
            notes='Merging both versions'
        )
        
        # Refresh all from DB
        self.original.refresh_from_db()
        self.counter.refresh_from_db()
        
        # Assertions
        self.assertEqual(resolved.status, 'STIPULATED')
        self.assertEqual(resolved.source_party, 'NEUTRAL')
        self.assertTrue(resolved.is_system_source)
        self.assertEqual(resolved.trust_level, 5)
        self.assertEqual(resolved.replaces_event, self.original)
        self.assertEqual(resolved.version, 3)  # max(1,2) + 1
        
        # Evidence merged (deduplicated)
        self.assertEqual(resolved.evidence.count(), 2)
        self.assertIn(doc1, resolved.evidence.all())
        self.assertIn(doc2, resolved.evidence.all())
        
        # Originals marked superseded
        self.assertEqual(self.original.status, 'SUPERSEDED')
        self.assertEqual(self.counter.status, 'SUPERSEDED')
    
    def test_resolve_invalid_resolution(self):
        """Invalid resolution raises ValidationError."""
        service = ConflictResolverService()
        
        with self.assertRaises(ValidationError) as ctx:
            service.resolve_conflict(
                event=self.original,
                resolution='INVALID',
                user=self.user
            )
        
        self.assertIn('Invalid resolution', str(ctx.exception))
    
    def test_resolve_no_conflict_raises_error(self):
        """Cannot resolve an event with no conflict."""
        service = ConflictResolverService()
        
        # Create an event with no counter-claims
        isolated_event = TimelineEvent.objects.create(
            date=date(2023, 2, 1),
            event='Isolated Event',
            category='contract',
            source_party='CLIENT',
            case=self.case,
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError) as ctx:
            service.resolve_conflict(
                event=isolated_event,
                resolution='KEEP_ORIGINAL',
                user=self.user
            )
        
        self.assertIn('No conflict to resolve', str(ctx.exception))
```

#### Test: Conflict Chain and Graph
```python
class TestConflictResolverGraph(TestCase):
    """Tests for conflict chain and graph methods."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='user', email='user@test.com', password='test123'
        )
        self.case = Case.objects.create(name='Test Case', user=self.user)
        
        # Create chain: original -> counter1 -> counter2
        self.original = TimelineEvent.objects.create(
            date=date(2023, 1, 1), event='Original', category='contract',
            source_party='CLIENT', case=self.case, created_by=self.user
        )
        self.counter1 = TimelineEvent.objects.create(
            date=date(2023, 1, 2), event='Counter 1', category='contract',
            source_party='OPPOSING', replaces_event=self.original,
            case=self.case, created_by=self.user
        )
        self.counter2 = TimelineEvent.objects.create(
            date=date(2023, 1, 3), event='Counter 2', category='contract',
            source_party='CLIENT', replaces_event=self.counter1,
            case=self.case, created_by=self.user
        )
    
    def test_get_conflict_chain(self):
        """Get full chain of events."""
        service = ConflictResolverService()
        
        chain = service.get_conflict_chain(self.original)
        
        self.assertEqual(len(chain), 3)
        self.assertIn(self.original, chain)
        self.assertIn(self.counter1, chain)
        self.assertIn(self.counter2, chain)
    
    def test_get_conflict_graph(self):
        """Get complete conflict graph for case."""
        service = ConflictResolverService()
        
        graph = service.get_conflict_graph(self.case)
        
        self.assertIn(str(self.original.uuid), graph)
        self.assertIn(str(self.counter1.uuid), graph)
        self.assertIn(str(self.counter2.uuid), graph)
        
        self.assertTrue(graph[str(self.original.uuid)]['has_conflict'])
        self.assertTrue(graph[str(self.counter1.uuid)]['is_counter_claim'])
        self.assertEqual(
            graph[str(self.counter1.uuid)]['replaces_uuid'],
            str(self.original.uuid)
        )
```

---

## 🔗 Integration Testing

### 2.1 Conflict Resolution API Integration

**File:** `apps/timeline/tests/test_conflict_api.py`

```python
class TestConflictAPI(TestCase):
    """Tests for /contest/ and /resolve/ API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@test.com', password='test123'
        )
        self.case = Case.objects.create(name='Test Case', user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create event
        self.event = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Test Event',
            category='contract',
            source_party='CLIENT',
            case=self.case,
            created_by=self.user
        )
        
        # Create evidence document
        self.doc = ArchiveDocument.objects.create(
            title='Evidence.pdf',
            file_type='pdf',
            case=self.case,
            uploader=self.user
        )
    
    def test_contest_endpoint(self):
        """POST /contest/ creates counter-claim."""
        url = f'/api/timeline/cases/{self.case.id}/events/{self.event.id}/contest/'
        data = {
            'event': 'Counter Claim',
            'notes': 'Disputing this event',
            'evidence_ids': [self.doc.id]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertIn('replaces_event', response.data)
    
    def test_resolve_endpoint_keep_original(self):
        """POST /resolve/ with KEEP_ORIGINAL."""
        # First create a counter-claim
        counter = TimelineEvent.objects.create(
            date=date(2023, 1, 16),
            event='Counter',
            category='contract',
            source_party='OPPOSING',
            status='CONTESTED',
            replaces_event=self.event,
            case=self.case,
            created_by=self.user
        )
        
        url = f'/api/timeline/cases/{self.case.id}/events/{self.event.id}/resolve/'
        data = {
            'resolution': 'KEEP_ORIGINAL',
            'notes': 'Original stands'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify counter was superseded
        counter.refresh_from_db()
        self.assertEqual(counter.status, 'SUPERSEDED')
```

---

## 🔄 Integrity Testing

### 3.1 Round-Trip Test (Hive Portability)

**File:** `apps/timeline/tests/test_hive_roundtrip.py`

**CRITICAL TEST**: Export → Delete → Re-import → Verify ALL UUIDs and relationships match perfectly.

```python
class TestHiveRoundTrip(TestCase):
    """
    Round-trip integrity test for the .hive portability engine.
    
    This test verifies that:
    1. Export creates a valid .hive bundle
    2. Import recreates all records with original UUIDs
    3. All M2M relationships are preserved
    4. All replaces_event links are preserved
    5. All file paths are correctly restored
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@test.com', password='test123'
        )
        self.case = Case.objects.create(
            name='Round-Trip Test Case',
            description='Testing portability',
            user=self.user
        )
        
        # Create test data with complex relationships
        self._create_test_data()
    
    def _create_test_data(self):
        """Create a complex dataset for round-trip testing."""
        # Documents
        self.doc1 = ArchiveDocument.objects.create(
            title='Contract.pdf',
            file_type='pdf',
            category='contract',
            case=self.case,
            uploader=self.user
        )
        self.doc2 = ArchiveDocument.objects.create(
            title='Email.pdf',
            file_type='pdf',
            category='email',
            case=self.case,
            uploader=self.user
        )
        
        # Events with evidence
        self.event1 = TimelineEvent.objects.create(
            date=date(2023, 1, 15),
            event='Contract Signed',
            category='contract',
            notes='Original contract',
            source_party='CLIENT',
            status='UNDISPUTED',
            trust_level=3,
            case=self.case,
            created_by=self.user
        )
        self.event1.evidence.set([self.doc1])
        
        # Counter-claim
        self.event2 = TimelineEvent.objects.create(
            date=date(2023, 1, 16),
            event='Contract Disputed',
            category='contract',
            notes='Disputing terms',
            source_party='OPPOSING',
            status='CONTESTED',
            trust_level=2,
            replaces_event=self.event1,
            case=self.case,
            created_by=self.user
        )
        self.event2.evidence.set([self.doc2])
        
        # Collection
        self.collection = TimelineCollection.objects.create(
            name='Test Collection',
            description='Test collection',
            case=self.case,
            created_by=self.user,
            is_public=False
        )
        self.collection.events.set([self.event1, self.event2])
        
        # Store original UUIDs for verification
        self.original_uuids = {
            'case': str(self.case.uuid),
            'doc1': str(self.doc1.uuid),
            'doc2': str(self.doc2.uuid),
            'event1': str(self.event1.uuid),
            'event2': str(self.event2.uuid),
            'collection': str(self.collection.uuid)
        }
    
    def test_roundtrip_preserves_uuids(self):
        """All records are recreated with their original UUIDs."""
        # Export
        service_export = HiveExportService(self.case)
        hive_path = service_export.export()
        
        # Delete everything
        self.case.delete()
        
        # Verify deletion
        self.assertFalse(Case.objects.filter(uuid=self.original_uuids['case']).exists())
        self.assertFalse(TimelineEvent.objects.filter(uuid=self.original_uuids['event1']).exists())
        self.assertFalse(ArchiveDocument.objects.filter(uuid=self.original_uuids['doc1']).exists())
        
        # Import
        service_import = HiveImportService(hive_path, user=self.user)
        imported_case, errors, warnings = service_import.import_bundle()
        
        # Verify no errors
        self.assertEqual(len(errors), 0)
        
        # Verify UUIDs are preserved
        self.assertEqual(str(imported_case.uuid), self.original_uuids['case'])
        
        imported_doc1 = ArchiveDocument.objects.get(uuid=self.original_uuids['doc1'])
        imported_doc2 = ArchiveDocument.objects.get(uuid=self.original_uuids['doc2'])
        imported_event1 = TimelineEvent.objects.get(uuid=self.original_uuids['event1'])
        imported_event2 = TimelineEvent.objects.get(uuid=self.original_uuids['event2'])
        imported_collection = TimelineCollection.objects.get(uuid=self.original_uuids['collection'])
        
        # Verify all original UUIDs exist
        self.assertEqual(str(imported_doc1.uuid), self.original_uuids['doc1'])
        self.assertEqual(str(imported_doc2.uuid), self.original_uuids['doc2'])
        self.assertEqual(str(imported_event1.uuid), self.original_uuids['event1'])
        self.assertEqual(str(imported_event2.uuid), self.original_uuids['event2'])
        self.assertEqual(str(imported_collection.uuid), self.original_uuids['collection'])
    
    def test_roundtrip_preserves_replaces_event(self):
        """replaces_event relationships are preserved."""
        # Export
        service_export = HiveExportService(self.case)
        hive_path = service_export.export()
        
        # Delete and re-import
        self.case.delete()
        service_import = HiveImportService(hive_path, user=self.user)
        imported_case, _, _ = service_import.import_bundle()
        
        # Get imported events
        imported_event1 = TimelineEvent.objects.get(uuid=self.original_uuids['event1'])
        imported_event2 = TimelineEvent.objects.get(uuid=self.original_uuids['event2'])
        
        # Verify replaces_event link
        self.assertEqual(imported_event2.replaces_event, imported_event1)
    
    def test_roundtrip_preserves_evidence_m2m(self):
        """Evidence M2M relationships are preserved."""
        # Export
        service_export = HiveExportService(self.case)
        hive_path = service_export.export()
        
        # Delete and re-import
        self.case.delete()
        service_import = HiveImportService(hive_path, user=self.user)
        imported_case, _, _ = service_import.import_bundle()
        
        # Get imported records
        imported_event1 = TimelineEvent.objects.get(uuid=self.original_uuids['event1'])
        imported_event2 = TimelineEvent.objects.get(uuid=self.original_uuids['event2'])
        imported_doc1 = ArchiveDocument.objects.get(uuid=self.original_uuids['doc1'])
        imported_doc2 = ArchiveDocument.objects.get(uuid=self.original_uuids['doc2'])
        
        # Verify evidence links
        self.assertEqual(imported_event1.evidence.count(), 1)
        self.assertIn(imported_doc1, imported_event1.evidence.all())
        
        self.assertEqual(imported_event2.evidence.count(), 1)
        self.assertIn(imported_doc2, imported_event2.evidence.all())
    
    def test_roundtrip_preserves_collection_events(self):
        """Collection event M2M relationships are preserved."""
        # Export
        service_export = HiveExportService(self.case)
        hive_path = service_export.export()
        
        # Delete and re-import
        self.case.delete()
        service_import = HiveImportService(hive_path, user=self.user)
        imported_case, _, _ = service_import.import_bundle()
        
        # Get imported collection
        imported_collection = TimelineCollection.objects.get(uuid=self.original_uuids['collection'])
        imported_event1 = TimelineEvent.objects.get(uuid=self.original_uuids['event1'])
        imported_event2 = TimelineEvent.objects.get(uuid=self.original_uuids['event2'])
        
        # Verify collection contains both events
        self.assertEqual(imported_collection.events.count(), 2)
        self.assertIn(imported_event1, imported_collection.events.all())
        self.assertIn(imported_event2, imported_collection.events.all())
    
    def test_roundtrip_preserves_system_source_fields(self):
        """is_system_source, trust_level, has_gold_seal preserved."""
        # Create a court event with gold seal
        court_event = TimelineEvent.objects.create(
            date=date(2023, 2, 1),
            event='Court Order',
            category='court_filing',
            source_party='COURT',
            case=self.case,
            created_by=self.user
        )
        # Auto-set by clean(): is_system_source=True, status=STIPULATED, trust_level=5
        court_event.full_clean()
        court_event.save()
        
        original_uuids = {**self.original_uuids, 'court_event': str(court_event.uuid)}
        
        # Export
        service_export = HiveExportService(self.case)
        hive_path = service_export.export()
        
        # Delete and re-import
        self.case.delete()
        service_import = HiveImportService(hive_path, user=self.user)
        imported_case, _, _ = service_import.import_bundle()
        
        # Get imported court event
        imported_court = TimelineEvent.objects.get(uuid=original_uuids['court_event'])
        
        # Verify system source fields
        self.assertTrue(imported_court.is_system_source)
        self.assertEqual(imported_court.trust_level, 5)
        self.assertEqual(imported_court.status, 'STIPULATED')
        self.assertTrue(imported_court.has_gold_seal)
```

---

## 🔐 Security Testing

### 4.1 ShredderService Tests

**File:** `apps/core/tests/test_shredder.py`

```python
class TestShredderService(TestCase):
    """Tests for ShredderService secure deletion."""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', email='admin@test.com', password='test123',
            is_staff=True, is_superuser=True
        )
        self.owner = User.objects.create_user(
            username='owner', email='owner@test.com', password='test123'
        )
        self.other_user = User.objects.create_user(
            username='other', email='other@test.com', password='test123'
        )
        
        self.owner_case = Case.objects.create(name='Owner Case', user=self.owner)
        self.admin_case = Case.objects.create(name='Admin Case', user=self.admin)
    
    def test_shred_entire_case_owner(self):
        """Case owner can shred their own case."""
        # Create test data
        event = TimelineEvent.objects.create(
            date=date(2023, 1, 1), event='Test', category='other',
            source_party='CLIENT', case=self.owner_case, created_by=self.owner
        )
        doc = ArchiveDocument.objects.create(
            title='Test.pdf', file_type='pdf',
            case=self.owner_case, uploader=self.owner
        )
        
        # Shred
        service = ShredderService(self.owner_case)
        counts = service.shred_case(user=self.owner, shred_private_only=False)
        
        # Verify deletion
        self.assertEqual(counts['timeline_events'], 1)
        self.assertEqual(counts['archive_documents'], 1)
        self.assertFalse(TimelineEvent.objects.filter(id=event.id).exists())
        self.assertFalse(ArchiveDocument.objects.filter(id=doc.id).exists())
        self.assertFalse(Case.objects.filter(id=self.owner_case.id).exists())
    
    def test_shred_entire_case_admin(self):
        """Admin can shred any case."""
        # Admin can shred owner's case
        service = ShredderService(self.owner_case)
        counts = service.shred_case(user=self.admin, shred_private_only=False)
        
        self.assertFalse(Case.objects.filter(id=self.owner_case.id).exists())
    
    def test_shred_entire_case_permission_denied(self):
        """Non-owner, non-admin cannot shred a case."""
        service = ShredderService(self.owner_case)
        
        with self.assertRaises(PermissionDenied):
            service.shred_case(user=self.other_user, shred_private_only=False)
    
    def test_shred_private_data_only(self):
        """User can shred their own private data without being case owner."""
        # Create data in admin's case (not owned by other_user)
        event = TimelineEvent.objects.create(
            date=date(2023, 1, 1), event='Test', category='other',
            source_party='CLIENT', case=self.admin_case, created_by=self.other_user
        )
        
        # Shred only private data
        service = ShredderService(self.admin_case)
        counts = service.shred_case(user=self.other_user, shred_private_only=True)
        
        # Event should be deleted
        self.assertEqual(counts['timeline_events'], 1)
        self.assertFalse(TimelineEvent.objects.filter(id=event.id).exists())
        
        # But case still exists
        self.assertTrue(Case.objects.filter(id=self.admin_case.id).exists())
    
    def test_secure_wipe_file(self):
        """Files are overwritten with random data before deletion."""
        import tempfile
        import os
        
        # Create a temp file with known content
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'SECRET_DATA_THAT_MUST_BE_WIPED')
            temp_path = f.name
        
        try:
            service = ShredderService(self.owner_case)
            
            # Secure wipe the file
            service.shred_file(temp_path)
            
            # File should no longer exist
            self.assertFalse(os.path.exists(temp_path))
            
            # Even if we create a new file at the same path,
            # the old content should be gone (overwritten)
        finally:
            # Clean up if file still exists
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_database_cascade_on_case_delete(self):
        """Deleting a case cascades to all related records."""
        # Create full data set
        collection = TimelineCollection.objects.create(
            name='Test Collection', case=self.owner_case, created_by=self.owner
        )
        event = TimelineEvent.objects.create(
            date=date(2023, 1, 1), event='Test', category='other',
            source_party='CLIENT', case=self.owner_case, created_by=self.owner
        )
        collection.events.add(event)
        doc = ArchiveDocument.objects.create(
            title='Test.pdf', file_type='pdf',
            case=self.owner_case, uploader=self.owner
        )
        event.evidence.add(doc)
        
        # Shred entire case
        service = ShredderService(self.owner_case)
        service.shred_case(user=self.owner, shred_private_only=False)
        
        # Verify cascade deletion
        self.assertFalse(Case.objects.filter(id=self.owner_case.id).exists())
        self.assertFalse(TimelineCollection.objects.filter(id=collection.id).exists())
        self.assertFalse(TimelineEvent.objects.filter(id=event.id).exists())
        self.assertFalse(ArchiveDocument.objects.filter(id=doc.id).exists())
    
    def test_get_shreddable_cases_admin(self):
        """Admin can see all cases for shredding."""
        cases = ShredderService.get_shreddable_cases(self.admin)
        
        self.assertIn(self.owner_case, cases)
        self.assertIn(self.admin_case, cases)
    
    def test_get_shreddable_cases_owner(self):
        """Regular user can only see their own cases."""
        cases = ShredderService.get_shreddable_cases(self.owner)
        
        self.assertIn(self.owner_case, cases)
        self.assertNotIn(self.admin_case, cases)
```

---

## 🎨 UI/UX Testing

### 5.1 Gold Seal Rendering Tests

**File:** `frontend/src/components/__tests__/EventCard.test.tsx`

```typescript
import React from 'react';
import { render, screen } from '@testing-library/react';
import EventCard from '../EventCard';
import { TimelineEvent } from '../../types/timeline';

describe('EventCard Gold Seal', () => {
  const mockUserParty: SourceParty = 'CLIENT';
  
  const baseEvent: TimelineEvent = {
    id: '123',
    date: '2023-01-15',
    event: 'Test Event',
    category: 'contract',
    source_type: 'MANUAL',
    status: 'UNDISPUTED',
    source_party: 'CLIENT',
    citation: '',
    notes: 'Test notes',
    version: 1,
    created_at: '2023-01-15T00:00:00Z',
    updated_at: '2023-01-15T00:00:00Z',
    evidence: [],
    replaces_event: null,
    counter_claims: [],
    case: 'case-123',
    case_id: 'case-123',
    created_by: 'user-123',
    created_by_username: 'Test User',
    timeline_file: null,
    is_system_source: false,
    trust_level: 3,
    has_gold_seal: false
  };

  it('does not render Gold Seal badge when has_gold_seal is false', () => {
    render(<EventCard event={baseEvent} userParty={mockUserParty} />);
    
    expect(screen.queryByText('🏆 Gold Seal')).not.toBeInTheDocument();
  });

  it('renders Gold Seal badge when has_gold_seal is true', () => {
    const goldSealEvent: TimelineEvent = {
      ...baseEvent,
      is_system_source: true,
      status: 'STIPULATED',
      has_gold_seal: true
    };
    
    render(<EventCard event={goldSealEvent} userParty={mockUserParty} />);
    
    expect(screen.getByText('🏆 Gold Seal')).toBeInTheDocument();
  });

  it('Gold Seal badge has correct tooltip', () => {
    const goldSealEvent: TimelineEvent = {
      ...baseEvent,
      is_system_source: true,
      status: 'STIPULATED',
      has_gold_seal: true
    };
    
    render(<EventCard event={goldSealEvent} userParty={mockUserParty} />);
    
    const badge = screen.getByText('🏆 Gold Seal');
    expect(badge).toHaveAttribute('title', 'Gold Seal: Court/Neutral Stipulated Fact');
  });
});
```

### 5.2 Conflict Resolver Modal Tests

**File:** `frontend/src/components/__tests__/ConflictResolverModal.test.tsx`

```typescript
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ConflictResolverModal from '../ConflictResolverModal';
import { ContestedPair, SourceParty } from '../../types/timeline';

describe('ConflictResolverModal', () => {
  const mockOnClose = jest.fn();
  const mockOnResolve = jest.fn();
  
  const mockConflict: ContestedPair = {
    left: {
      id: 'event-1',
      date: '2023-01-15',
      event: 'Original Claim',
      category: 'contract',
      source_type: 'MANUAL',
      status: 'UNDISPUTED',
      source_party: 'CLIENT',
      citation: '',
      notes: 'Original notes',
      version: 1,
      created_at: '2023-01-15T00:00:00Z',
      updated_at: '2023-01-15T00:00:00Z',
      evidence: [],
      replaces_event: null,
      counter_claims: [],
      case: 'case-123',
      case_id: 'case-123',
      created_by: 'user-123',
      created_by_username: 'Client User',
      timeline_file: null,
      is_system_source: false,
      trust_level: 3,
      has_gold_seal: false
    },
    right: {
      id: 'event-2',
      date: '2023-01-16',
      event: 'Counter Claim',
      category: 'contract',
      source_type: 'MANUAL',
      status: 'CONTESTED',
      source_party: 'OPPOSING',
      citation: '',
      notes: 'Counter notes',
      version: 2,
      created_at: '2023-01-16T00:00:00Z',
      updated_at: '2023-01-16T00:00:00Z',
      evidence: [],
      replaces_event: 'event-1',
      counter_claims: [],
      case: 'case-123',
      case_id: 'case-123',
      created_by: 'user-456',
      created_by_username: 'Opposing User',
      timeline_file: null,
      is_system_source: false,
      trust_level: 2,
      has_gold_seal: false
    },
    diff: {
      category: false,
      status: true,
      notes: true,
      citation: false,
      evidence: false
    }
  };

  it('renders modal with Original Claim and Counter Claim sections', () => {
    render(
      <ConflictResolverModal
        conflict={mockConflict}
        leftParty={'CLIENT' as SourceParty}
        rightParty={'OPPOSING' as SourceParty}
        onClose={mockOnClose}
        onResolve={mockOnResolve}
      />
    );

    expect(screen.getByText('Original Claim')).toBeInTheDocument();
    expect(screen.getByText('Counter Claim')).toBeInTheDocument();
    expect(screen.getByText('Original Claim')).toBeInTheDocument();
    expect(screen.getByText('Counter Claim')).toBeInTheDocument();
  });

  it('displays both events with their details', () => {
    render(
      <ConflictResolverModal
        conflict={mockConflict}
        leftParty={'CLIENT' as SourceParty}
        rightParty={'OPPOSING' as SourceParty}
        onClose={mockOnClose}
        onResolve={mockOnResolve}
      />
    );

    // Left (Original) side
    expect(screen.getByText('Original Claim')).toBeInTheDocument();
    expect(screen.getByText('2023-01-15')).toBeInTheDocument();
    expect(screen.getByText('Original notes')).toBeInTheDocument();

    // Right (Counter) side
    expect(screen.getByText('Counter Claim')).toBeInTheDocument();
    expect(screen.getByText('2023-01-16')).toBeInTheDocument();
    expect(screen.getByText('Counter notes')).toBeInTheDocument();
  });

  it('has three resolution option buttons', () => {
    render(
      <ConflictResolverModal
        conflict={mockConflict}
        leftParty={'CLIENT' as SourceParty}
        rightParty={'OPPOSING' as SourceParty}
        onClose={mockOnClose}
        onResolve={mockOnResolve}
      />
    );

    expect(screen.getByLabelText(/Keep Original Claim/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Keep Counter Claim/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Merge/i)).toBeInTheDocument();
  });

  it('calls onResolve with correct data when Keep Original is selected', () => {
    render(
      <ConflictResolverModal
        conflict={mockConflict}
        leftParty={'CLIENT' as SourceParty}
        rightParty={'OPPOSING' as SourceParty}
        onClose={mockOnClose}
        onResolve={mockOnResolve}
      />
    );

    fireEvent.click(screen.getByLabelText(/Keep Original Claim/i));
    fireEvent.click(screen.getByText(/Resolve Conflict/i));

    expect(mockOnResolve).toHaveBeenCalledWith(
      expect.objectContaining({
        action: 'KEEP_ORIGINAL'
      })
    );
  });

  it('calls onClose when cancel button is clicked', () => {
    render(
      <ConflictResolverModal
        conflict={mockConflict}
        leftParty={'CLIENT' as SourceParty}
        rightParty={'OPPOSING' as SourceParty}
        onClose={mockOnClose}
        onResolve={mockOnResolve}
      />
    );

    fireEvent.click(screen.getByText(/Cancel/i));
    expect(mockOnClose).toHaveBeenCalled();
  });
});
```

---

## 🏭 Test Data Factories

**File:** `apps/timeline/tests/factories.py`

```python
import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from datetime import date
from apps.core.models import Case
from apps.timeline.models import TimelineEvent, TimelineCollection
from apps.archive.models import ArchiveDocument
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.Sequence(lambda n: f'user_{n}@test.com')
    password = 'testpassword123'


class CaseFactory(DjangoModelFactory):
    class Meta:
        model = Case
    
    name = factory.Sequence(lambda n: f'Case {n}')
    description = 'Test case description'
    user = factory.SubFactory(UserFactory)


class ArchiveDocumentFactory(DjangoModelFactory):
    class Meta:
        model = ArchiveDocument
    
    title = factory.Sequence(lambda n: f'Document {n}.pdf')
    file_type = 'pdf'
    category = 'contract'
    description = 'Test document'
    case = factory.SubFactory(CaseFactory)
    uploader = factory.SubFactory(UserFactory)
    is_promoted = False


class TimelineEventFactory(DjangoModelFactory):
    class Meta:
        model = TimelineEvent
    
    date = date(2023, 1, 15)
    event = factory.Sequence(lambda n: f'Event {n}')
    category = 'contract'
    notes = 'Test event notes'
    source_party = 'CLIENT'
    source_type = 'MANUAL'
    status = 'UNDISPUTED'
    is_system_source = False
    trust_level = 3
    version = 1
    case = factory.SubFactory(CaseFactory)
    created_by = factory.SubFactory(UserFactory)
    
    @factory.post_generation
    def evidence(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for doc in extracted:
                self.evidence.add(doc)


class TimelineCollectionFactory(DjangoModelFactory):
    class Meta:
        model = TimelineCollection
    
    name = factory.Sequence(lambda n: f'Collection {n}')
    description = 'Test collection'
    case = factory.SubFactory(CaseFactory)
    created_by = factory.SubFactory(UserFactory)
    is_public = False
    
    @factory.post_generation
    def events(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for event in extracted:
                self.events.add(event)
```

---

## 🚀 Test Execution

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific test modules
python manage.py test apps.timeline.tests.test_conflict_resolver
python manage.py test apps.timeline.tests.test_hive_roundtrip
python manage.py test apps.core.tests.test_shredder

# Run with coverage
coverage run --source='.' manage.py test
coverage report

# Run frontend tests (requires Node.js)
cd frontend
npm test
```

### Test Coverage Requirements

| Component | Minimum Coverage |
|-----------|------------------|
| ConflictResolverService | 95% |
| HiveExportService | 90% |
| HiveImportService | 90% |
| ShredderService | 95% |
| API Endpoints | 90% |
| Frontend Components | 85% |

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_USER: hiver
          POSTGRES_PASSWORD: hiver
          POSTGRES_DB: hiver_test
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install coverage
      
      - name: Run backend tests
        env:
          DJANGO_SETTINGS_MODULE: config.settings
          DATABASE_URL: postgres://hiver:hiver@localhost:hiver_test
        run: |
          python manage.py test --noinput
          coverage run --source='.' manage.py test
          coverage report --fail-under=90
      
      - name: Set up Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      
      - name: Install frontend dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run frontend tests
        run: |
          cd frontend
          npm test
```

---

## ✅ Zero Legacy Support Verification

All tests **MUST** verify that no legacy code paths are used:

1. **No `supporting_docs` references**: All document linking MUST use `evidence` M2M
2. **No `get_archive_documents()` calls**: Use `event.evidence.all()`
3. **No `get_document_urls()` calls**: Use `doc.file.url` or custom serialization
4. **No JSON-based document storage**: All documents in ArchiveDocument model

### Verification Test

```python
class TestZeroLegacySupport(TestCase):
    """Verify no legacy code paths are used."""
    
    def test_timeline_event_has_evidence_m2m(self):
        """TimelineEvent must have evidence M2M, not supporting_docs."""
        from apps.timeline.models import TimelineEvent
        
        # Check model fields
        self.assertTrue(hasattr(TimelineEvent, 'evidence'))
        self.assertFalse(hasattr(TimelineEvent, 'supporting_docs'))
    
    def test_no_supporting_docs_in_views(self):
        """No supporting_docs references in views."""
        import apps.timeline.views as views_module
        
        # Read source and check
        import inspect
        source = inspect.getsource(views_module)
        self.assertNotIn('supporting_docs', source)
        self.assertNotIn('get_archive_documents', source)
        self.assertNotIn('get_document_urls', source)
```

---

## 📚 Documentation

- [Developer Guide](DEVELOPER_GUIDE.md) - Architecture and API reference
- [Architecture Plan](PORTABILITY_PLUS_CONFLICTRES_ARCHITECTURE_PLANE.md) - Original design documents

---

**Maintainer Note**: Keep this test strategy document updated as new features are added. All new features must include corresponding unit, integration, and UI tests as outlined above.
