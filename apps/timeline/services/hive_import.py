"""
Hive Import Service

Ingests a .hive (tar.gz) bundle onto a new server instance, recreating
all database records using the original UUIDs for portability.

Key Features:
- UUID Stability: Records are recreated with their original UUIDs
- Collision Handling: Halts if UUID collision detected (not part of this Case)
- Atomic Ingestion: Entire import is wrapped in a transaction
- Relational Mapping: Correctly maps UUID references to recreate the Truth Graph
"""

import json
import os
import shutil
import tarfile
import tempfile
import logging
from typing import Optional, Dict, List, Any, Tuple

from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model

from apps.core.models import Case
from apps.core.services.hive_directory import HiveDirectoryService

logger = logging.getLogger(__name__)

User = get_user_model()


class HiveImportService:
    """
    Service for importing a .hive bundle onto a server.
    
    The import process:
    1. Extracts the .hive bundle to a temp directory
    2. Loads the manifest (hive.json)
    3. Validates the manifest structure and version
    4. Creates the Case (or updates if it exists with same UUID)
    5. Creates all ArchiveDocuments with original UUIDs
    6. Creates all TimelineEvents with original UUIDs, preserving relationships
    7. Creates all TimelineCollections with original UUIDs
    8. Copies all files to their proper locations
    9. All within an atomic transaction
    """

    SUPPORTED_MANIFEST_VERSIONS = ["1.0"]
    
    def __init__(
        self,
        hive_path: str,
        target_case: Optional[Case] = None,
        user: Optional[User] = None
    ):
        """
        Initialize the import service.
        
        Args:
            hive_path: Path to the .hive file to import
            target_case: Optional - if provided, import into this existing case.
                       If None, create a new case from the manifest.
            user: The user performing the import (for ownership/permissions)
        """
        self.hive_path = hive_path
        self.target_case = target_case
        self.user = user
        self.temp_dir = None
        self.manifest: Dict[str, Any] = {}
        self.uuid_map: Dict[str, str] = {}  # For tracking any UUID remappings (though we use originals)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, int] = {
            "cases_created": 0,
            "cases_updated": 0,
            "documents_created": 0,
            "documents_updated": 0,
            "events_created": 0,
            "events_updated": 0,
            "collections_created": 0,
            "collections_updated": 0,
            "files_copied": 0,
        }

    def import_bundle(self) -> Tuple[Case, List[str], List[str]]:
        """
        Import a .hive bundle.
        
        Returns:
            Tuple of (imported_case, errors, warnings)
            
        Raises:
            ValidationError: If manifest is invalid or version unsupported
            IntegrityError: If UUID collision detected
        """
        self.temp_dir = tempfile.mkdtemp(prefix="hive_import_")
        
        try:
            # Extract bundle
            self._extract_bundle()
            
            # Load and validate manifest
            self._load_manifest()
            self._validate_manifest()
            
            # Atomic import
            with transaction.atomic():
                case = self._import_all()
            
            return case, self.errors, self.warnings
            
        except Exception as e:
            # Log error and re-raise
            logger.exception(f"Hive import failed: {e}")
            self.errors.append(f"Import failed: {str(e)}")
            raise
        finally:
            # Clean up temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

    def _extract_bundle(self):
        """Extract the .hive tar.gz to temp directory."""
        with tarfile.open(self.hive_path, "r:gz") as tar:
            tar.extractall(self.temp_dir)

    def _load_manifest(self):
        """Load the hive.json manifest from the temp directory."""
        manifest_path = os.path.join(self.temp_dir, "hive.json")
        
        if not os.path.exists(manifest_path):
            raise ValidationError("hive.json manifest not found in bundle")
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            self.manifest = json.load(f)

    def _validate_manifest(self):
        """Validate the manifest structure and version."""
        # Check version
        version = self.manifest.get("version")
        if version not in self.SUPPORTED_MANIFEST_VERSIONS:
            raise ValidationError(
                f"Unsupported manifest version: {version}. "
                f"Supported: {', '.join(self.SUPPORTED_MANIFEST_VERSIONS)}"
            )
        
        # Check required top-level keys
        required_keys = ["case", "timeline_events", "archive_documents", "timeline_collections"]
        for key in required_keys:
            if key not in self.manifest:
                raise ValidationError(f"Missing required manifest key: {key}")
        
        # Validate case data
        case_data = self.manifest.get("case", {})
        if not case_data.get("uuid"):
            raise ValidationError("Case UUID is required in manifest")
        if not case_data.get("name"):
            self.warnings.append("Case name is missing in manifest")

    def _import_all(self) -> Case:
        """
        Import all data from the manifest.
        
        This is the core import logic, called within an atomic transaction.
        
        Returns:
            The imported/updated Case instance
        """
        # Create or update the Case
        case = self._import_case()
        
        # Ensure hive directory structure exists
        HiveDirectoryService.ensure_hive_structure(case.id)
        
        # Import in dependency order:
        # 1. ArchiveDocuments (needed for evidence M2M)
        self._import_archive_documents(case)
        
        # 2. TimelineEvents (needed for replaces_event and collections)
        self._import_timeline_events(case)
        
        # 3. TimelineCollections (references events)
        self._import_timeline_collections(case)
        
        # 4. Copy files
        self._copy_files(case)
        
        return case

    def _import_case(self) -> Case:
        """Import or update the Case from the manifest."""
        from apps.core.models import Case
        
        case_data = self.manifest["case"]
        case_uuid = case_data["uuid"]
        
        # Check for collision: existing case with different UUID
        if self.target_case:
            # Using provided target case
            case = self.target_case
            self.stats["cases_updated"] += 1
            return case
        
        # Check if case with this UUID already exists
        # Use id since Case.uuid is a property that returns id
        existing_case = Case.objects.filter(id=case_uuid).first()
        
        if existing_case:
            # Update existing case
            existing_case.name = case_data.get("name", existing_case.name)
            existing_case.description = case_data.get("description", existing_case.description)
            existing_case.save()
            self.stats["cases_updated"] += 1
            self.warnings.append(f"Updated existing case: {case_uuid}")
            return existing_case
        
        # Create new case
        # Use id since Case's primary key is UUID (stored in id field)
        case = Case.objects.create(
            id=case_uuid,
            name=case_data.get("name", "Unnamed Case"),
            description=case_data.get("description", ""),
            user=self.user,
        )
        self.stats["cases_created"] += 1
        return case

    def _import_archive_documents(self, case: Case):
        """
        Import ArchiveDocuments from the manifest.
        
        Uses original UUIDs for UUID stability.
        Checks for collisions (document with same UUID but different case).
        """
        from apps.archive.models import ArchiveDocument
        
        doc_data_list = self.manifest.get("archive_documents", [])
        
        for doc_data in doc_data_list:
            doc_uuid = doc_data["uuid"]
            
            # Check for collision: existing document with same UUID but different case
            existing_doc = ArchiveDocument.objects.filter(uuid=doc_uuid).first()
            if existing_doc:
                if existing_doc.case != case:
                    # Collision with document from another case
                    error_msg = (
                        f"UUID collision: ArchiveDocument {doc_uuid} already exists "
                        f"in case {existing_doc.case.uuid}, but manifest assigns it to "
                        f"case {case.uuid}. Import halted to prevent data corruption."
                    )
                    self.errors.append(error_msg)
                    logger.error(error_msg)
                    raise IntegrityError(error_msg)
                else:
                    # Document already exists in this case - skip or update?
                    # For now, we'll update it
                    self._update_archive_document(existing_doc, doc_data, case)
                    self.stats["documents_updated"] += 1
                    continue
            
            # Create new document with original UUID
            doc = self._create_archive_document(doc_data, case)
            self.stats["documents_created"] += 1

    def _create_archive_document(self, doc_data: Dict, case: Case) -> 'ArchiveDocument':
        """Create an ArchiveDocument from manifest data."""
        from apps.archive.models import ArchiveDocument
        
        doc = ArchiveDocument.objects.create(
            uuid=doc_data["uuid"],
            title=doc_data.get("title", "Untitled"),
            file_type=doc_data.get("file_type", "other"),
            category=doc_data.get("category", ""),
            description=doc_data.get("description", ""),
            path=doc_data.get("file_path", ""),
            is_promoted=doc_data.get("is_promoted", False),
            promoted_at=self._parse_datetime(doc_data.get("promoted_at")),
            case=case,
            uploader=self._get_user(doc_data.get("uploader_uuid")),
            user=self._get_user(doc_data.get("user_uuid")),
            is_draft=doc_data.get("is_draft", False),
            is_immutable=doc_data.get("is_immutable", True),
            tags=doc_data.get("tags", []),
            metadata=doc_data.get("metadata", {}),
            conversion_status=doc_data.get("conversion_status", "PENDING"),
            markdown_path=doc_data.get("markdown_path", ""),
            conversion_error=doc_data.get("conversion_error", ""),
            extracted_text=doc_data.get("extracted_text", ""),
            text_extraction_status=doc_data.get("text_extraction_status", "PENDING"),
        )
        
        return doc

    def _update_archive_document(
        self,
        doc: 'ArchiveDocument',
        doc_data: Dict,
        case: Case
    ):
        """Update an existing ArchiveDocument with data from the manifest."""
        # Only update fields that are safe to change
        doc.title = doc_data.get("title", doc.title)
        doc.file_type = doc_data.get("file_type", doc.file_type)
        doc.category = doc_data.get("category", doc.category)
        doc.description = doc_data.get("description", doc.description)
        doc.is_promoted = doc_data.get("is_promoted", doc.is_promoted)
        doc.promoted_at = self._parse_datetime(doc_data.get("promoted_at")) or doc.promoted_at
        doc.is_draft = doc_data.get("is_draft", doc.is_draft)
        doc.tags = doc_data.get("tags", doc.tags)
        doc.metadata = doc_data.get("metadata", doc.metadata)
        doc.save()

    def _import_timeline_events(self, case: Case):
        """
        Import TimelineEvents from the manifest.
        
        Uses original UUIDs for UUID stability.
        Checks for collisions (event with same UUID but different case).
        Preserves replaces_event relationships using UUID mapping.
        """
        from apps.timeline.models import TimelineEvent
        
        event_data_list = self.manifest.get("timeline_events", [])
        
        # First pass: Create all events (without M2M relationships)
        for event_data in event_data_list:
            event_uuid = event_data["uuid"]
            
            # Check for collision
            existing_event = TimelineEvent.objects.filter(id=event_uuid).first()
            if existing_event:
                if existing_event.case != case:
                    error_msg = (
                        f"UUID collision: TimelineEvent {event_uuid} already exists "
                        f"in case {existing_event.case.uuid}, but manifest assigns it to "
                        f"case {case.uuid}. Import halted to prevent data corruption."
                    )
                    self.errors.append(error_msg)
                    logger.error(error_msg)
                    raise IntegrityError(error_msg)
                else:
                    # Update existing event
                    self._update_timeline_event(existing_event, event_data, case)
                    self.stats["events_updated"] += 1
                    continue
            
            # Create new event with original UUID
            event = self._create_timeline_event(event_data, case)
            self.stats["events_created"] += 1
        
        # Second pass: Set up replaces_event relationships
        self._setup_replaces_event_relationships(event_data_list, case)
        
        # Third pass: Set up evidence M2M relationships
        self._setup_evidence_relationships(event_data_list, case)

    def _create_timeline_event(self, event_data: Dict, case: Case) -> 'TimelineEvent':
        """Create a TimelineEvent from manifest data."""
        from apps.timeline.models import TimelineEvent
        
        event = TimelineEvent.objects.create(
            id=event_data["uuid"],
            date=self._parse_date(event_data.get("date")),
            event=event_data.get("event", "Untitled Event"),
            category=event_data.get("category", "other"),
            notes=event_data.get("notes", ""),
            source_party=event_data.get("source_party", "CLIENT"),
            source_type=event_data.get("source_type", "MANUAL"),
            status=event_data.get("status", "UNDISPUTED"),
            is_system_source=event_data.get("is_system_source", False),
            trust_level=event_data.get("trust_level", 3),
            version=event_data.get("version", 1),
            citation=event_data.get("citation", ""),
            case=case,
            created_by=self._get_user(event_data.get("created_by_uuid")),
        )
        
        return event

    def _update_timeline_event(
        self,
        event: 'TimelineEvent',
        event_data: Dict,
        case: Case
    ):
        """Update an existing TimelineEvent with data from the manifest."""
        event.date = self._parse_date(event_data.get("date")) or event.date
        event.event = event_data.get("event", event.event)
        event.category = event_data.get("category", event.category)
        event.notes = event_data.get("notes", event.notes)
        event.source_party = event_data.get("source_party", event.source_party)
        event.source_type = event_data.get("source_type", event.source_type)
        event.status = event_data.get("status", event.status)
        event.is_system_source = event_data.get("is_system_source", event.is_system_source)
        event.trust_level = event_data.get("trust_level", event.trust_level)
        event.version = event_data.get("version", event.version)
        event.citation = event_data.get("citation", event.citation)
        event.save()

    def _setup_replaces_event_relationships(self, event_data_list: List[Dict], case: Case):
        """
        Set up replaces_event relationships after all events are created.
        
        This must be done in a separate pass because we need all events to exist
        before we can set up the self-referencing foreign keys.
        """
        from apps.timeline.models import TimelineEvent
        
        # Build a map of event UUIDs to their database instances
        event_uuid_map = {}
        for event_data in event_data_list:
            event = TimelineEvent.objects.filter(
                id=event_data["uuid"],
                case=case
            ).first()
            if event:
                event_uuid_map[event_data["uuid"]] = event
        
        # Now set up replaces_event relationships
        for event_data in event_data_list:
            event = event_uuid_map.get(event_data["uuid"])
            if not event:
                continue
            
            replaces_uuid = event_data.get("replaces_event_uuid")
            if replaces_uuid and replaces_uuid in event_uuid_map:
                event.replaces_event = event_uuid_map[replaces_uuid]
                event.save()

    def _setup_evidence_relationships(self, event_data_list: List[Dict], case: Case):
        """
        Set up evidence M2M relationships after all events and documents are created.
        
        This maps the evidence_uuids from the manifest back to the actual
        ArchiveDocument instances.
        """
        from apps.timeline.models import TimelineEvent
        from apps.archive.models import ArchiveDocument
        
        # Build a map of document UUIDs to their database instances
        doc_uuid_map = {}
        for doc_data in self.manifest.get("archive_documents", []):
            doc = ArchiveDocument.objects.filter(
                uuid=doc_data["uuid"],
                case=case
            ).first()
            if doc:
                doc_uuid_map[doc_data["uuid"]] = doc
        
        # Set up evidence for each event
        for event_data in event_data_list:
            event = TimelineEvent.objects.filter(
                id=event_data["uuid"],
                case=case
            ).first()
            
            if not event:
                continue
            
            evidence_uuids = event_data.get("evidence_uuids", [])
            evidence_docs = [
                doc_uuid_map[doc_uuid] 
                for doc_uuid in evidence_uuids 
                if doc_uuid in doc_uuid_map
            ]
            
            if evidence_docs:
                event.evidence.set(evidence_docs)

    def _import_timeline_collections(self, case: Case):
        """
        Import TimelineCollections from the manifest.
        
        Uses original UUIDs for UUID stability.
        Checks for collisions (collection with same UUID but different case).
        """
        from apps.timeline.models import TimelineCollection, TimelineEvent
        
        collection_data_list = self.manifest.get("timeline_collections", [])
        
        # Build event UUID map for setting up M2M
        event_uuid_map = {}
        for event_data in self.manifest.get("timeline_events", []):
            event = TimelineEvent.objects.filter(
                id=event_data["uuid"],
                case=case
            ).first()
            if event:
                event_uuid_map[event_data["uuid"]] = event
        
        for collection_data in collection_data_list:
            collection_uuid = collection_data["uuid"]
            
            # Check for collision
            existing_collection = TimelineCollection.objects.filter(
                id=collection_uuid
            ).first()
            if existing_collection:
                if existing_collection.case != case:
                    error_msg = (
                        f"UUID collision: TimelineCollection {collection_uuid} already exists "
                        f"in case {existing_collection.case.uuid}, but manifest assigns it to "
                        f"case {case.uuid}. Import halted to prevent data corruption."
                    )
                    self.errors.append(error_msg)
                    logger.error(error_msg)
                    raise IntegrityError(error_msg)
                else:
                    # Update existing collection
                    self._update_timeline_collection(
                        existing_collection, collection_data, event_uuid_map
                    )
                    self.stats["collections_updated"] += 1
                    continue
            
            # Create new collection with original UUID
            collection = self._create_timeline_collection(
                collection_data, case, event_uuid_map
            )
            self.stats["collections_created"] += 1

    def _create_timeline_collection(
        self,
        collection_data: Dict,
        case: Case,
        event_uuid_map: Dict
    ) -> 'TimelineCollection':
        """Create a TimelineCollection from manifest data."""
        from apps.timeline.models import TimelineCollection
        
        collection = TimelineCollection.objects.create(
            uuid=collection_data["uuid"],
            name=collection_data.get("name", "Unnamed Collection"),
            description=collection_data.get("description", ""),
            case=case,
            created_by=self._get_user(collection_data.get("created_by_uuid")),
            is_public=collection_data.get("is_public", False),
        )
        
        # Set up event M2M relationships
        event_uuids = collection_data.get("event_uuids", [])
        events = [
            event_uuid_map[event_uuid]
            for event_uuid in event_uuids
            if event_uuid in event_uuid_map
        ]
        if events:
            collection.events.set(events)
        
        return collection

    def _update_timeline_collection(
        self,
        collection: 'TimelineCollection',
        collection_data: Dict,
        event_uuid_map: Dict
    ):
        """Update an existing TimelineCollection with data from the manifest."""
        collection.name = collection_data.get("name", collection.name)
        collection.description = collection_data.get("description", collection.description)
        collection.is_public = collection_data.get("is_public", collection.is_public)
        collection.save()
        
        # Update event M2M relationships
        event_uuids = collection_data.get("event_uuids", [])
        events = [
            event_uuid_map[event_uuid]
            for event_uuid in event_uuids
            if event_uuid in event_uuid_map
        ]
        if events:
            collection.events.set(events)

    def _copy_files(self, case: Case):
        """
        Copy all files from the temp directory to their proper Hive locations.
        """
        # Copy formal files
        temp_formal = os.path.join(self.temp_dir, "formal")
        if os.path.exists(temp_formal):
            self._copy_directory_to_hive(
                temp_formal,
                HiveDirectoryService.get_formal_root(case.id)
            )
        
        # Copy private files (if present)
        temp_private = os.path.join(self.temp_dir, "private")
        if os.path.exists(temp_private):
            for user_uuid in os.listdir(temp_private):
                user_private_src = os.path.join(temp_private, user_uuid)
                user_private_dst = HiveDirectoryService.get_private_root(
                    case.uuid, user_uuid
                )
                self._copy_directory_to_hive(user_private_src, user_private_dst)

    def _copy_directory_to_hive(self, src_dir: str, dst_dir: str):
        """Copy a directory from temp to Hive location, preserving structure."""
        os.makedirs(dst_dir, exist_ok=True)
        
        for item in os.listdir(src_dir):
            src_path = os.path.join(src_dir, item)
            dst_path = os.path.join(dst_dir, item)
            
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
                # Count files in subdirectories
                for root, dirs, files in os.walk(src_path):
                    self.stats["files_copied"] += len(files)
            else:
                shutil.copy2(src_path, dst_path)
                self.stats["files_copied"] += 1

    def _get_user(self, user_uuid: Optional[str]) -> Optional[User]:
        """
        Get a User by UUID or ID.
        
        Tries uuid field first (if User model has it), falls back to id.
        Uses importing user as fallback if neither works.
        """
        if not user_uuid:
            return None
        try:
            # Try UUID lookup first (for custom User models with UUID)
            return User.objects.get(uuid=user_uuid)
        except User.DoesNotExist:
            pass
        except AttributeError:
            # User model doesn't have uuid field - try by id (integer primary key)
            try:
                return User.objects.get(id=user_uuid)
            except (User.DoesNotExist, ValueError):
                # ValueError if user_uuid is not a valid integer
                pass
        
        # Log warning but don't fail - use importing user as fallback
        self.warnings.append(f"User {user_uuid} not found, using importer as fallback")
        return self.user

    @staticmethod
    def _parse_date(date_str: Optional[str]):
        """Parse a date string from the manifest."""
        from django.utils.dateparse import parse_date
        if not date_str:
            return None
        return parse_date(date_str)

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]):
        """Parse a datetime string from the manifest."""
        from django.utils.dateparse import parse_datetime
        if not dt_str:
            return None
        return parse_datetime(dt_str)
