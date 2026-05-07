"""
Hive Directory Service

Manages the isolated directory structure for Hive compartments:
- /media/hives/[case_uuid]/formal/ - Shared evidence vault (VAULT)
- /media/hives/[case_uuid]/private/[user_uuid]/ - User workspace (WORKSPACE)

The "Gate" logic (promote_to_evidence) moves files from private to formal.
"""

import os
import shutil
import time
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from apps.archive.models import ArchiveDocument


class HiveDirectoryService:
    """
    Service for managing the isolated Hive directory structure.
    
    Directory Layout:
    media/
    └── hives/
        └── [case_uuid]/
            ├── formal/
            │   ├── evidence/           # Shared ArchiveDocument files
            │   │   └── [doc_uuid].[ext]
            │   ├── timeline/          # Markdown exports
            │   │   └── timeline.md
            │   └── hive.json           # Export manifest cache
            │
            └── private/
                └── [user_uuid]/
                    ├── drafts/       # Unpromoted timeline events
                    ├── wiki/          # LLM Wiki pages (markdown)
                    ├── research/      # AI analysis outputs
                    └── temp/          # Upload staging (auto-cleaned)
    """

    # Subdirectory names
    FORMAL_EVIDENCE_DIR = "evidence"
    FORMAL_TIMELINE_DIR = "timeline"
    PRIVATE_DRAFTS_DIR = "drafts"
    PRIVATE_WIKI_DIR = "wiki"
    PRIVATE_RESEARCH_DIR = "research"
    PRIVATE_TEMP_DIR = "temp"

    @classmethod
    def get_hive_root(cls) -> str:
        """Get the root directory for all Hives."""
        return os.path.join(settings.MEDIA_ROOT, "hives")

    @classmethod
    def get_case_root(cls, case_uuid: str) -> str:
        """Get the root directory for a specific case."""
        return os.path.join(cls.get_hive_root(), str(case_uuid))

    @classmethod
    def get_formal_root(cls, case_uuid: str) -> str:
        """Get the formal (shared) root for a case."""
        return os.path.join(cls.get_case_root(case_uuid), "formal")

    @classmethod
    def get_formal_evidence_path(cls, case_uuid: str) -> str:
        """Get the path to the formal evidence directory."""
        return os.path.join(cls.get_formal_root(case_uuid), cls.FORMAL_EVIDENCE_DIR)

    @classmethod
    def get_formal_timeline_path(cls, case_uuid: str) -> str:
        """Get the path to the formal timeline directory."""
        return os.path.join(cls.get_formal_root(case_uuid), cls.FORMAL_TIMELINE_DIR)

    @classmethod
    def get_private_root(cls, case_uuid: str, user_uuid: str) -> str:
        """Get the private workspace root for a user in a case."""
        return os.path.join(
            cls.get_case_root(case_uuid),
            "private",
            str(user_uuid)
        )

    @classmethod
    def get_private_drafts_path(cls, case_uuid: str, user_uuid: str) -> str:
        """Get the path to the user's drafts directory."""
        return os.path.join(
            cls.get_private_root(case_uuid, user_uuid),
            cls.PRIVATE_DRAFTS_DIR
        )

    @classmethod
    def get_private_wiki_path(cls, case_uuid: str, user_uuid: str) -> str:
        """Get the path to the user's wiki directory."""
        return os.path.join(
            cls.get_private_root(case_uuid, user_uuid),
            cls.PRIVATE_WIKI_DIR
        )

    @classmethod
    def get_private_research_path(cls, case_uuid: str, user_uuid: str) -> str:
        """Get the path to the user's research directory."""
        return os.path.join(
            cls.get_private_root(case_uuid, user_uuid),
            cls.PRIVATE_RESEARCH_DIR
        )

    @classmethod
    def get_private_temp_path(cls, case_uuid: str, user_uuid: str) -> str:
        """Get the path to the user's temp directory."""
        return os.path.join(
            cls.get_private_root(case_uuid, user_uuid),
            cls.PRIVATE_TEMP_DIR
        )

    @classmethod
    def ensure_hive_structure(cls, case_uuid: str, user_uuid: str = None):
        """
        Create all necessary directories for a case.
        
        Args:
            case_uuid: The UUID of the case
            user_uuid: Optional - if provided, also create user's private directories
        """
        # Ensure hive root exists
        os.makedirs(cls.get_hive_root(), exist_ok=True)
        
        # Ensure case root exists
        case_root = cls.get_case_root(case_uuid)
        os.makedirs(case_root, exist_ok=True)
        
        # Create formal directories
        os.makedirs(cls.get_formal_evidence_path(case_uuid), exist_ok=True)
        os.makedirs(cls.get_formal_timeline_path(case_uuid), exist_ok=True)
        
        # Create user's private directories if user_uuid provided
        if user_uuid:
            private_root = cls.get_private_root(case_uuid, user_uuid)
            os.makedirs(private_root, exist_ok=True)
            os.makedirs(cls.get_private_drafts_path(case_uuid, user_uuid), exist_ok=True)
            os.makedirs(cls.get_private_wiki_path(case_uuid, user_uuid), exist_ok=True)
            os.makedirs(cls.get_private_research_path(case_uuid, user_uuid), exist_ok=True)
            os.makedirs(cls.get_private_temp_path(case_uuid, user_uuid), exist_ok=True)

    @classmethod
    def ensure_all_case_structures(cls, case):
        """
        Ensure hive structure exists for a case and all its users.
        
        Args:
            case: The Case model instance
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Ensure case-level directories
        cls.ensure_hive_structure(case.uuid)
        
        # Ensure private directories for all case users
        # Note: This may be expensive for cases with many users
        # In production, consider creating on-demand instead
        for user in User.objects.filter(cases=case):
            cls.ensure_hive_structure(case.uuid, str(user.id))

    @classmethod
    def get_relative_path(cls, absolute_path: str) -> str:
        """
        Convert an absolute server path to a relative path from the Hive root.
        
        Args:
            absolute_path: Absolute path on the server
            
        Returns:
            Relative path from the Hive root (e.g., "case_uuid/formal/evidence/doc_uuid.pdf")
        """
        hive_root = cls.get_hive_root()
        if not absolute_path.startswith(hive_root):
            raise ValidationError(
                f"Path {absolute_path} is not within the Hive root {hive_root}"
            )
        return os.path.relpath(absolute_path, hive_root)

    @classmethod
    def get_absolute_path(cls, relative_path: str) -> str:
        """
        Convert a relative Hive path to an absolute server path.
        
        Args:
            relative_path: Path relative to Hive root
            
        Returns:
            Absolute path on the server
        """
        return os.path.join(cls.get_hive_root(), relative_path)

    @classmethod
    def is_in_formal(cls, path: str, case_uuid: str) -> bool:
        """Check if a path is within the formal directory for a case."""
        formal_root = cls.get_formal_root(case_uuid)
        return path.startswith(formal_root)

    @classmethod
    def is_in_private(cls, path: str, case_uuid: str, user_uuid: str) -> bool:
        """Check if a path is within the private directory for a user in a case."""
        private_root = cls.get_private_root(case_uuid, user_uuid)
        return path.startswith(private_root)

    @classmethod
    def get_document_hive_path(
        cls,
        document: ArchiveDocument,
        is_promoted: bool = False
    ) -> str:
        """
        Get the Hive-relative path for a document.
        
        Args:
            document: The ArchiveDocument instance
            is_promoted: If True, use formal path; if False, use private path
            
        Returns:
            Relative path from Hive root
        """
        if is_promoted or document.is_promoted:
            # Formal path: hives/[case_uuid]/formal/evidence/[doc_uuid].[ext]
            ext = document.get_file_extension()
            if ext:
                filename = f"{document.uuid}.{ext}"
            else:
                filename = f"{document.uuid}"
            return os.path.join(
                str(document.case.uuid),
                "formal",
                "evidence",
                filename
            )
        else:
            # Private path: hives/[case_uuid]/private/[user_uuid]/drafts/[doc_uuid].[ext]
            ext = document.get_file_extension()
            if ext:
                filename = f"{document.uuid}.{ext}"
            else:
                filename = f"{document.uuid}"
            return os.path.join(
                str(document.case.uuid),
                "private",
                str(document.uploader.uuid) if document.uploader else "unknown",
                "drafts",
                filename
            )

    @classmethod
    @transaction.atomic
    def promote_to_evidence(
        cls,
        document: ArchiveDocument,
        case,
        user
    ) -> ArchiveDocument:
        """
        Gate Logic: Move a file from a user's private workspace to the formal vault.
        
        This is a user-triggered action that:
        1. Validates the user owns the document
        2. Copies the file from private to formal
        3. Updates the document record
        4. Marks the document as promoted
        
        Args:
            document: The ArchiveDocument to promote
            case: The Case instance (for validation)
            user: The User requesting the promotion
            
        Returns:
            The updated ArchiveDocument instance
            
        Raises:
            PermissionDenied: If user doesn't own the document or case
            FileNotFoundError: If the source file doesn't exist
        """
        # Validate ownership
        if document.uploader != user:
            raise PermissionDenied(
                f"User {str(user.id)} does not own document {document.uuid}"
            )
        
        if document.case != case:
            raise PermissionDenied(
                f"Document {document.uuid} does not belong to case {case.uuid}"
            )
        
        # Get current file path
        if not document.file:
            raise FileNotFoundError(
                f"Document {document.uuid} has no associated file"
            )
        
        old_path = document.file.path
        if not os.path.exists(old_path):
            raise FileNotFoundError(
                f"Document file not found: {old_path}"
            )
        
        # Determine extension
        ext = document.get_file_extension()
        if ext:
            new_filename = f"{document.uuid}.{ext}"
        else:
            new_filename = f"{document.uuid}"
        
        # Create new path in formal evidence directory
        new_dir = cls.get_formal_evidence_path(case.uuid)
        os.makedirs(new_dir, exist_ok=True)
        new_path = os.path.join(new_dir, new_filename)
        
        # Copy file (use copy2 to preserve metadata)
        shutil.copy2(old_path, new_path)
        
        # Update document record
        # Store relative path from MEDIA_ROOT (Django convention)
        relative_path = os.path.relpath(new_path, settings.MEDIA_ROOT)
        
        document.file.name = relative_path
        document.is_promoted = True
        document.promoted_at = timezone.now()
        document.save()
        
        return document

    @classmethod
    @transaction.atomic
    def demote_from_evidence(
        cls,
        document: ArchiveDocument,
        user
    ) -> ArchiveDocument:
        """
        Move a document back from formal to user's private workspace.
        
        Args:
            document: The ArchiveDocument to demote
            user: The User requesting the demotion (must be the uploader)
            
        Returns:
            The updated ArchiveDocument instance
        """
        if document.uploader != user:
            raise PermissionDenied(
                f"Only the uploader can demote a document"
            )
        
        if not document.is_promoted:
            raise ValidationError("Document is not promoted")
        
        old_path = document.file.path
        if not os.path.exists(old_path):
            raise FileNotFoundError(f"File not found: {old_path}")
        
        # Move to private/drafts
        private_drafts = cls.get_private_drafts_path(
            document.case.uuid, str(user.id)
        )
        os.makedirs(private_drafts, exist_ok=True)
        
        ext = document.get_file_extension()
        new_filename = f"{document.uuid}.{ext}" if ext else f"{document.uuid}"
        new_path = os.path.join(private_drafts, new_filename)
        
        shutil.move(old_path, new_path)
        
        # Update document record
        relative_path = os.path.relpath(new_path, settings.MEDIA_ROOT)
        document.file.name = relative_path
        document.is_promoted = False
        document.save()
        
        return document

    @classmethod
    def cleanup_temp_directory(cls, case_uuid: str, user_uuid: str, max_age_days: int = 7):
        """
        Clean up old files from the user's temp directory.
        
        Args:
            case_uuid: The case UUID
            user_uuid: The user UUID
            max_age_days: Delete files older than this many days
        """
        from django.utils import timezone
        import time
        
        temp_path = cls.get_private_temp_path(case_uuid, user_uuid)
        if not os.path.exists(temp_path):
            return 0
        
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        deleted_count = 0
        
        for filename in os.listdir(temp_path):
            file_path = os.path.join(temp_path, filename)
            if os.path.isfile(file_path):
                file_mtime = os.path.getmtime(file_path)
                if file_mtime < cutoff_time:
                    try:
                        os.unlink(file_path)
                        deleted_count += 1
                    except OSError:
                        pass
        
        return deleted_count
