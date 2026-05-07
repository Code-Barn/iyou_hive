"""
Hive Export Service

Exports a Case and all related data to a .hive (tar.gz) bundle.
The manifest (hive.json) captures the complete "Truth Graph" with UUID-based
relationships for portability across server instances.
"""

import json
import os
import shutil
import tarfile
import tempfile
from datetime import datetime
from typing import Optional, Dict, List, Any

from django.conf import settings
from django.core.files.base import ContentFile

from apps.core.models import Case
from apps.core.services.hive_directory import HiveDirectoryService


class HiveExportService:
    """
    Service for exporting a Case to a portable .hive bundle.
    
    The .hive file is a tar.gz archive containing:
    - hive.json: Manifest with all database state (Case, TimelineEvents, 
                 ArchiveDocuments, TimelineCollections) with UUID references
    - formal/: All files from the formal evidence vault
    - private/: (Optional) User's private workspace files
    """

    MANIFEST_VERSION = "1.0"
    HIVE_EXTENSION = ".hive"

    def __init__(
        self,
        case: Case,
        include_private: bool = False,
        user_uuid: Optional[str] = None
    ):
        """
        Initialize the export service.
        
        Args:
            case: The Case to export
            include_private: If True, include files from user's private workspace
            user_uuid: If include_private is True, the UUID of the user whose
                      private files should be included. If None and include_private
                      is True, includes ALL users' private files for the case.
        """
        self.case = case
        self.include_private = include_private
        self.user_uuid = user_uuid
        self.temp_dir = None
        self.manifest: Dict[str, Any] = {}

    def export(self) -> str:
        """
        Export the case to a .hive bundle.
        
        Returns:
            Absolute path to the generated .hive file
        """
        self.temp_dir = tempfile.mkdtemp(
            prefix=f"hive_export_{self.case.uuid}_"
        )
        
        try:
            # Build manifest with all data
            self._build_manifest()
            
            # Copy files (formal + optionally private)
            self._copy_formal_files()
            if self.include_private:
                self._copy_private_files()
            
            # Package into tar.gz
            output_path = self._package_bundle()
            return output_path
        finally:
            # Clean up temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

    def _build_manifest(self):
        """Build the hive.json manifest with all case data."""
        from apps.timeline.models import TimelineEvent, TimelineCollection
        from apps.archive.models import ArchiveDocument
        
        self.manifest = {
            "version": self.MANIFEST_VERSION,
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "case": self._serialize_case(),
            "timeline_events": [],
            "archive_documents": [],
            "timeline_collections": []
        }
        
        # Serialize TimelineEvents
        events = TimelineEvent.objects.filter(case=self.case).prefetch_related(
            'evidence', 'replaces_event', 'created_by'
        )
        for event in events:
            self.manifest["timeline_events"].append(
                self._serialize_timeline_event(event)
            )
        
        # Serialize ArchiveDocuments
        documents = ArchiveDocument.objects.filter(case=self.case).select_related(
            'uploader', 'case'
        )
        for doc in documents:
            self.manifest["archive_documents"].append(
                self._serialize_archive_document(doc)
            )
        
        # Serialize TimelineCollections
        collections = TimelineCollection.objects.filter(case=self.case).prefetch_related(
            'events', 'created_by'
        )
        for collection in collections:
            self.manifest["timeline_collections"].append(
                self._serialize_timeline_collection(collection)
            )
        
        # Write manifest to temp directory
        manifest_path = os.path.join(self.temp_dir, "hive.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False, default=str)

    def _serialize_case(self) -> Dict[str, Any]:
        """Serialize Case to manifest format."""
        return {
            "uuid": str(self.case.id),
            "name": self.case.name,
            "description": self.case.description or "",
            "created_at": self.case.created_at.isoformat() + "Z" if self.case.created_at else None,
            "updated_at": self.case.updated_at.isoformat() + "Z" if self.case.updated_at else None,
            "user_uuid": str(self.case.user.id) if self.case.user else None,
        }

    def _serialize_timeline_event(self, event) -> Dict[str, Any]:
        """
        Serialize TimelineEvent to manifest format.
        
        Captures all fields including the new system source fields,
        and preserves relationships via UUID references.
        """
        return {
            "uuid": str(event.id),
            "date": event.date.isoformat() if event.date else None,
            "event": event.event,
            "category": event.category,
            "notes": event.notes or "",
            "source_party": event.source_party,
            "source_type": event.source_type,
            "status": event.status,
            # New Phase 2 fields
            "is_system_source": event.is_system_source,
            "trust_level": event.trust_level,
            "version": event.version,
            # Relationships via UUID
            "replaces_event_uuid": str(event.replaces_event.id) if event.replaces_event else None,
            "evidence_uuids": [str(doc.id) for doc in event.evidence.all()],
            "case_uuid": str(event.case.id),
            "created_by_uuid": str(event.created_by.id) if event.created_by else None,
            "created_at": event.created_at.isoformat() + "Z" if event.created_at else None,
            "updated_at": event.updated_at.isoformat() + "Z" if event.updated_at else None,
            "citation": event.citation or "",
        }

    def _serialize_archive_document(self, doc) -> Dict[str, Any]:
        """
        Serialize ArchiveDocument to manifest format.
        
        File paths are stored as relative paths from the Hive root,
        not absolute server paths.
        """
        # Get relative path from Hive root
        if doc.file:
            file_path = self._get_file_relative_path(doc.file.path)
        else:
            file_path = ""
        
        return {
            "uuid": str(doc.uuid),
            "title": doc.title,
            "file_type": doc.file_type,
            "category": doc.category or "",
            "description": doc.description or "",
            # Hive-relative file path
            "file_path": file_path,
            # Promotion state
            "is_promoted": doc.is_promoted,
            "promoted_at": doc.promoted_at.isoformat() + "Z" if doc.promoted_at else None,
            # Relationships via UUID
            "case_uuid": str(doc.case.uuid) if doc.case else None,
            "uploader_uuid": str(doc.uploader.id) if doc.uploader else None,
            # Legacy fields (for backward compat if needed, though we're strict no-legacy)
            "user_uuid": str(doc.user.id) if doc.user else None,
            "timeline_event_uuid": str(doc.timeline_event.id) if doc.timeline_event else None,
            # Metadata
            "tags": doc.tags or [],
            "metadata": doc.metadata or {},
            "upload_date": doc.upload_date.isoformat() + "Z" if doc.upload_date else None,
            # Conversion fields
            "conversion_status": doc.conversion_status,
            "markdown_path": doc.markdown_path or "",
            "conversion_error": doc.conversion_error or "",
            "extracted_text": doc.extracted_text or "",
            "text_extraction_status": doc.text_extraction_status,
            # Flags
            "is_draft": doc.is_draft,
            "is_immutable": doc.is_immutable,
        }

    def _serialize_timeline_collection(self, collection) -> Dict[str, Any]:
        """Serialize TimelineCollection to manifest format."""
        return {
            "uuid": str(collection.id),
            "name": collection.name,
            "description": collection.description or "",
            "case_uuid": str(collection.case.id),
            "created_by_uuid": str(collection.created_by.id) if collection.created_by else None,
            "is_public": collection.is_public,
            "created_at": collection.created_at.isoformat() + "Z" if collection.created_at else None,
            "updated_at": collection.updated_at.isoformat() + "Z" if collection.updated_at else None,
            "event_uuids": [str(event.id) for event in collection.events.all()],
        }

    def _get_file_relative_path(self, absolute_path: str) -> str:
        """
        Convert an absolute file path to a relative path from the Hive root.
        
        This ensures all file references in the manifest are relative,
        making the bundle portable across servers.
        """
        hive_root = HiveDirectoryService.get_hive_root()
        
        # Normalize paths for comparison
        abs_path = os.path.normpath(absolute_path)
        hive_root_norm = os.path.normpath(hive_root)
        
        if not abs_path.startswith(hive_root_norm):
            # File is outside Hive root - store relative to MEDIA_ROOT
            # This shouldn't happen for properly stored files
            media_root = os.path.normpath(settings.MEDIA_ROOT)
            if abs_path.startswith(media_root):
                return os.path.relpath(abs_path, media_root)
            return absolute_path
        
        return os.path.relpath(abs_path, hive_root_norm)

    def _copy_formal_files(self):
        """Copy all files from the formal directory to the temp export directory."""
        formal_root = HiveDirectoryService.get_formal_root(self.case.id)
        
        if not os.path.exists(formal_root):
            return
        
        # Create formal directory in temp
        temp_formal = os.path.join(self.temp_dir, "formal")
        os.makedirs(temp_formal, exist_ok=True)
        
        # Copy entire formal directory structure
        for item in os.listdir(formal_root):
            src_path = os.path.join(formal_root, item)
            dst_path = os.path.join(temp_formal, item)
            
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)

    def _copy_private_files(self):
        """Copy files from user's private workspace to the temp export directory."""
        if self.user_uuid:
            # Copy specific user's private files
            users_to_copy = [self.user_uuid]
        else:
            # Copy all users' private files for this case
            from django.contrib.auth import get_user_model
            User = get_user_model()
            users_to_copy = [
                str(u.id) 
                for u in User.objects.filter(cases=self.case)
            ]
        
        for user_uuid in users_to_copy:
            private_root = HiveDirectoryService.get_private_root(
                self.case.uuid, user_uuid
            )
            
            if not os.path.exists(private_root):
                continue
            
            # Create private/[user_uuid] in temp
            temp_private_user = os.path.join(
                self.temp_dir, "private", user_uuid
            )
            os.makedirs(temp_private_user, exist_ok=True)
            
            # Copy all subdirectories (drafts, wiki, research, temp)
            for item in os.listdir(private_root):
                src_path = os.path.join(private_root, item)
                dst_path = os.path.join(temp_private_user, item)
                
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)

    def _package_bundle(self) -> str:
        """
        Package the temp directory into a tar.gz .hive file.
        
        Returns:
            Absolute path to the created .hive file
        """
        # Determine output path
        export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{self.case.uuid}_{timestamp}{self.HIVE_EXTENSION}"
        output_path = os.path.join(export_dir, output_filename)
        
        # Create tar.gz
        with tarfile.open(output_path, "w:gz") as tar:
            # Add all files from temp_dir to archive
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Calculate archive name (relative to temp_dir)
                    arcname = os.path.relpath(file_path, self.temp_dir)
                    tar.add(file_path, arcname=arcname)
        
        return output_path

    @staticmethod
    def generate_export_filename(case: Case) -> str:
        """Generate a standardized export filename for a case."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{case.uuid}_{timestamp}{HiveExportService.HIVE_EXTENSION}"
