#!/usr/bin/env python
"""
Hive Roundtrip Test

Tests that the "Truth Graph" (Events <-> Documents) is fully preserved
through export and import cycles.
"""

import os
import sys
import django
import tempfile
import shutil

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from apps.core.models import Case
from apps.timeline.models import TimelineEvent
from apps.archive.models import ArchiveDocument
from apps.timeline.services.hive_export import HiveExportService
from apps.timeline.services.hive_import import HiveImportService

User = get_user_model()


def get_unique_event_params(base_date, base_event):
    """Generate unique event parameters to avoid conflicts."""
    import random
    import datetime
    offset = random.randint(0, 1000)
    date = datetime.date(2024, 1, 1) + datetime.timedelta(days=offset)
    event_name = f"{base_event}_{offset}"
    return date, event_name


def create_test_data():
    """Create a test case with events and documents."""
    print("=" * 60)
    print("CREATING TEST DATA")
    print("=" * 60)
    
    # Create or get a test user
    user, created = User.objects.get_or_create(
        username='test_user_roundtrip',
        defaults={'email': 'test_roundtrip@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
    print(f"✓ User: {user.username} (ID: {user.id})")
    
    # Create a test case with unique name
    import random
    case_name = f'Test Case Roundtrip {random.randint(1000, 9999)}'
    case = Case.objects.create(
        name=case_name,
        user=user,
        description='Test case for hive export/import'
    )
    print(f"✓ Case: {case.name} (UUID: {case.uuid})")
    
    # Create test documents
    doc1 = ArchiveDocument.objects.create(
        title=f'Document 1 {case.id}',
        file_type='pdf',
        case=case,
        user=user,
        uploader=user,
        is_draft=False,
        is_immutable=True
    )
    doc2 = ArchiveDocument.objects.create(
        title=f'Document 2 {case.id}',
        file_type='pdf',
        case=case,
        user=user,
        uploader=user,
        is_draft=False,
        is_immutable=True
    )
    print(f"✓ Document 1: {doc1.title} (UUID: {doc1.uuid})")
    print(f"✓ Document 2: {doc2.title} (UUID: {doc2.uuid})")
    
    # Create test events with unique names
    date1, event1_name = get_unique_event_params('2024-01-01', 'Event 1')
    event1 = TimelineEvent.objects.create(
        date=date1,
        event=event1_name,
        category='legal',
        source_party='CLIENT',
        source_type='MANUAL',
        status='UNDISPUTED',
        is_system_source=False,
        trust_level=3,
        case=case,
        created_by=user
    )
    event1.evidence.set([doc1, doc2])
    
    date2, event2_name = get_unique_event_params('2024-01-02', 'Event 2')
    event2 = TimelineEvent.objects.create(
        date=date2,
        event=event2_name,
        category='court_filing',
        source_party='COURT',
        source_type='MANUAL',
        status='STIPULATED',
        is_system_source=True,
        trust_level=5,
        case=case,
        created_by=user
    )
    event2.evidence.set([doc1])
    
    print(f"✓ Event 1: {event1.event} (ID: {event1.id})")
    print(f"  - Evidence: {list(event1.evidence.values_list('title', flat=True))}")
    print(f"✓ Event 2: {event2.event} (ID: {event2.id})")
    print(f"  - Evidence: {list(event2.evidence.values_list('title', flat=True))}")
    
    return case, user, [doc1, doc2], [event1, event2]


def test_export_import():
    """Test export and import cycle."""
    print("\n" + "=" * 60)
    print("TESTING EXPORT/IMPORT ROUNDTRIP")
    print("=" * 60)
    
    # Create test data
    case, user, docs, events = create_test_data()
    
    # Verify pre-export state
    print(f"\n--- Pre-Export State ---")
    print(f"Events: {TimelineEvent.objects.filter(case=case).count()}")
    print(f"Documents: {ArchiveDocument.objects.filter(case=case).count()}")
    
    for event in events:
        print(f"  Event '{event.event}': {event.evidence.count()} evidence docs")
    
    # Export the case
    print(f"\n--- Exporting Case ---")
    export_service = HiveExportService(
        case=case,
        include_private=False
    )
    
    try:
        hive_path = export_service.export()
        print(f"✓ Export created: {hive_path}")
        print(f"  File size: {os.path.getsize(hive_path)} bytes")
    except Exception as e:
        print(f"✗ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Import the case
    print(f"\n--- Importing Case ---")
    import_service = HiveImportService(
        hive_path=hive_path,
        user=user
    )
    
    try:
        with transaction.atomic():
            imported_case, errors, warnings = import_service.import_bundle()
        print(f"✓ Import completed")
        print(f"  Case: {imported_case.name} (UUID: {imported_case.uuid})")
        print(f"  Errors: {len(errors)}")
        print(f"  Warnings: {len(warnings)}")
        if errors:
            for err in errors:
                print(f"    - {err}")
        if warnings:
            for warn in warnings:
                print(f"    ! {warn}")
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify post-import state
    print(f"\n--- Post-Import State ---")
    imported_events = TimelineEvent.objects.filter(case=imported_case)
    imported_docs = ArchiveDocument.objects.filter(case=imported_case)
    print(f"Events: {imported_events.count()}")
    print(f"Documents: {imported_docs.count()}")
    
    # Verify UUIDs are preserved
    print(f"\n--- UUID Preservation Check ---")
    for orig_doc, orig_event in zip(docs, events):
        imported_doc = ArchiveDocument.objects.filter(
            case=imported_case,
            uuid=orig_doc.uuid
        ).first()
        imported_event = TimelineEvent.objects.filter(
            case=imported_case,
            id=orig_event.id  # TimelineEvent uses id as UUID
        ).first()
        
        if imported_doc:
            print(f"✓ Document '{orig_doc.title}' UUID preserved: {orig_doc.uuid}")
        else:
            print(f"✗ Document '{orig_doc.title}' UUID NOT preserved")
            return False
            
        if imported_event:
            print(f"✓ Event '{orig_event.event}' ID preserved: {orig_event.id}")
        else:
            print(f"✗ Event '{orig_event.event}' ID NOT preserved")
            return False
    
    # Verify evidence relationships
    print(f"\n--- Evidence Relationship Check ---")
    for orig_event in events:
        imported_event = TimelineEvent.objects.filter(
            case=imported_case,
            id=orig_event.id
        ).first()
        
        if imported_event:
            orig_evidence_uuids = set(orig_event.evidence.values_list('uuid', flat=True))
            imported_evidence_uuids = set(imported_event.evidence.values_list('uuid', flat=True))
            
            if orig_evidence_uuids == imported_evidence_uuids:
                print(f"✓ Event '{orig_event.event}': Evidence relationships preserved")
            else:
                print(f"✗ Event '{orig_event.event}': Evidence relationships NOT preserved")
                print(f"  Original: {orig_evidence_uuids}")
                print(f"  Imported: {imported_evidence_uuids}")
                return False
    
    # Cleanup
    print(f"\n--- Cleanup ---")
    try:
        os.unlink(hive_path)
        print(f"✓ Temporary export file removed")
    except Exception as e:
        print(f"! Could not remove temp file: {e}")
    
    return True


if __name__ == '__main__':
    try:
        success = test_export_import()
        
        print("\n" + "=" * 60)
        if success:
            print("✓ ALL TESTS PASSED - Truth Graph preserved!")
        else:
            print("✗ TESTS FAILED - Truth Graph NOT preserved")
        print("=" * 60)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n✗ TEST CRASHED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
