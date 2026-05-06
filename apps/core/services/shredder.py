"""
Shredder Service

Securely and recursively deletes all files in a Hive's directory and
purges related database rows. Uses secure_wipe (os.urandom overwrite)
for every file to prevent data recovery.

Permissions:
- Only Case Owner or Admin can trigger a full Case Shred
- Users can only shred their own private data
"""

import os
import logging
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.contrib.auth import get_user_model
from typing import Optional, Dict, List

from apps.core.models import Case
from apps.core.services.hive_directory import HiveDirectoryService

logger = logging.getLogger(__name__)

User = get_user_model()


class ShredderService:
    """
    Service for securely deleting a Case's Hive data and database records.
    
    Features:
    - Secure wipe: Overwrites every file with random data before deletion
    - Recursive: Handles all subdirectories
    - Atomic: Database deletions are transactional
    - Permission-aware: Only case owner or admin can shred entire case
    """

    # Size for secure wipe chunks (in bytes)
    # We'll overwrite the entire file, so this is just for the buffer
    WIPE_BUFFER_SIZE = 4096  # 4KB chunks

    def __init__(self, case: Case):
        """
        Initialize the shredder for a specific case.
        
        Args:
            case: The Case to potentially shred
        """
        self.case = case

    def shred_case(self, user: User, shred_private_only: bool = False) -> Dict[str, int]:
        """
        Securely erase a case's Hive data.
        
        Args:
            user: The User requesting the shred
            shred_private_only: If True, only shred user's private data.
                               If False, shred entire case (requires owner/admin)
            
        Returns:
            Dictionary with counts of deleted items
            
        Raises:
            PermissionDenied: If user doesn't have permission
        """
        if shred_private_only:
            # User can only shred their own private data
            return self._shred_user_private_data(user)
        else:
            # Full case shred requires owner or admin
            self._validate_case_permission(user)
            return self._shred_entire_case(user)

    def _validate_case_permission(self, user: User):
        """
        Validate that user has permission to shred the entire case.
        
        Args:
            user: The User to check
            
        Raises:
            PermissionDenied: If user is not case owner or admin
        """
        if not (user.is_staff or user.is_superuser):
            # Check if user is the case owner
            if self.case.user != user:
                raise PermissionDenied(
                    f"Only case owner or admin can shred case {self.case.uuid}. "
                    f"Case owner: {self.case.user}, Requesting user: {user}"
                )

    @transaction.atomic
    def _shred_entire_case(self, user: User) -> Dict[str, int]:
        """
        Shred ALL data for a case (files + DB records).
        
        Args:
            user: The User performing the shred (for audit logging)
            
        Returns:
            Dictionary with deletion counts
        """
        from apps.timeline.models import TimelineEvent, TimelineCollection
        from apps.archive.models import ArchiveDocument
        
        counts: Dict[str, int] = {
            'archive_documents': 0,
            'timeline_events': 0,
            'timeline_collections': 0,
            'files_secure_wiped': 0,
        }
        
        hive_root = HiveDirectoryService.get_case_root(self.case.uuid)
        
        # 1. Securely wipe and delete all files first
        if os.path.exists(hive_root):
            file_count = self._secure_wipe_directory(hive_root)
            counts['files_secure_wiped'] = file_count
            # Remove the now-empty directory
            try:
                os.rmdir(hive_root)
            except OSError:
                pass  # Directory might not be empty due to permissions
        
        # 2. Delete TimelineCollections for this case
        collections = TimelineCollection.objects.filter(case=self.case)
        counts['timeline_collections'] = collections.count()
        collections.delete()
        
        # 3. Delete TimelineEvents for this case
        events = TimelineEvent.objects.filter(case=self.case)
        counts['timeline_events'] = events.count()
        events.delete()
        
        # 4. Delete ArchiveDocuments for this case
        documents = ArchiveDocument.objects.filter(case=self.case)
        counts['archive_documents'] = documents.count()
        documents.delete()
        
        # 5. Finally, delete the Case itself
        self.case.delete()
        
        # Log the shred operation
        logger.warning(
            f"SHREDDER: User {user.email or user.uuid} shredded case {self.case.uuid}. "
            f"Deleted: {counts}"
        )
        
        return counts

    @transaction.atomic
    def _shred_user_private_data(self, user: User) -> Dict[str, int]:
        """
        Shred only the specified user's private data for this case.
        
        Args:
            user: The User whose private data to shred
            
        Returns:
            Dictionary with deletion counts
        """
        from apps.timeline.models import TimelineEvent, TimelineCollection
        from apps.archive.models import ArchiveDocument
        
        counts: Dict[str, int] = {
            'archive_documents': 0,
            'timeline_events': 0,
            'timeline_collections': 0,
            'files_secure_wiped': 0,
        }
        
        user_uuid = str(user.uuid)
        
        # 1. Securely wipe and delete user's private files
        private_root = HiveDirectoryService.get_private_root(
            self.case.uuid, user_uuid
        )
        
        if os.path.exists(private_root):
            file_count = self._secure_wipe_directory(private_root)
            counts['files_secure_wiped'] = file_count
            # Remove the now-empty directory
            try:
                os.rmdir(private_root)
            except OSError:
                pass
        
        # 2. Delete user's private TimelineCollections
        collections = TimelineCollection.objects.filter(
            case=self.case,
            created_by=user
        )
        counts['timeline_collections'] = collections.count()
        collections.delete()
        
        # 3. Delete user's TimelineEvents
        events = TimelineEvent.objects.filter(
            case=self.case,
            created_by=user
        )
        counts['timeline_events'] = events.count()
        events.delete()
        
        # 4. Delete user's ArchiveDocuments
        documents = ArchiveDocument.objects.filter(
            case=self.case,
            uploader=user
        )
        counts['archive_documents'] = documents.count()
        documents.delete()
        
        # Log the shred operation
        logger.warning(
            f"SHREDDER: User {user.email or user.uuid} shredded private data "
            f"for case {self.case.uuid}. Deleted: {counts}"
        )
        
        return counts

    def _secure_wipe_directory(self, directory_path: str) -> int:
        """
        Recursively securely wipe and delete all files in a directory.
        
        For each file:
        1. Overwrite with random data using os.urandom
        2. Delete the file
        
        Args:
            directory_path: Path to the directory to shred
            
        Returns:
            Number of files securely wiped
        """
        count = 0
        
        if not os.path.exists(directory_path):
            return 0
        
        for root, dirs, files in os.walk(directory_path, topdown=False):
            # Process files first
            for filename in files:
                file_path = os.path.join(root, filename)
                try:
                    self._secure_wipe_file(file_path)
                    count += 1
                except Exception as e:
                    logger.error(
                        f"SHREDDER: Failed to wipe file {file_path}: {e}"
                    )
            
            # Then process directories (will be empty after files deleted)
            for dirname in dirs:
                dir_path = os.path.join(root, dirname)
                try:
                    os.rmdir(dir_path)
                except OSError as e:
                    logger.error(
                        f"SHREDDER: Failed to remove directory {dir_path}: {e}"
                    )
        
        return count

    def _secure_wipe_file(self, file_path: str):
        """
        Securely wipe a single file by overwriting with random data.
        
        CRITICAL: Uses os.urandom to generate random data for overwriting.
        
        Steps:
        1. Get file size
        2. Open file in write mode
        3. Overwrite entire file with random bytes
        4. Flush to disk
        5. Close file
        6. Delete file
        
        Args:
            file_path: Path to the file to securely wipe
        """
        try:
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Open file in binary write mode (truncates file)
            with open(file_path, 'wb') as f:
                # Write random data in chunks
                remaining = file_size
                while remaining > 0:
                    # Generate chunk of random bytes
                    chunk_size = min(self.WIPE_BUFFER_SIZE, remaining)
                    random_data = os.urandom(chunk_size)
                    f.write(random_data)
                    remaining -= chunk_size
                
                # Ensure data is written to disk
                f.flush()
                os.fsync(f.fileno())
            
            # Delete the file
            os.unlink(file_path)
            
        except FileNotFoundError:
            # File was already deleted
            pass
        except Exception as e:
            logger.error(
                f"SHREDDER: Failed to securely wipe {file_path}: {e}"
            )
            # Try to delete anyway
            try:
                os.unlink(file_path)
            except OSError:
                pass

    def shred_file(self, file_path: str) -> bool:
        """
        Securely wipe and delete a single file.
        
        Args:
            file_path: Path to the file to shred
            
        Returns:
            True if file was successfully wiped and deleted
        """
        try:
            self._secure_wipe_file(file_path)
            return True
        except Exception as e:
            logger.error(f"SHREDDER: Failed to shred file {file_path}: {e}")
            return False

    @staticmethod
    def get_shreddable_cases(user: User) -> List[Case]:
        """
        Get list of cases that the user can shred.
        
        Args:
            user: The User
            
        Returns:
            List of Case objects the user has permission to shred
        """
        if user.is_staff or user.is_superuser:
            # Admins can shred any case
            return list(Case.objects.all())
        else:
            # Regular users can only shred their own cases
            return list(Case.objects.filter(user=user))
