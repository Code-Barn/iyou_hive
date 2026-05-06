# Timeline services package
# Combines new Phase 2/3 services with legacy ingestion/export services

# New services (Phase 2: Portability, Phase 3: Conflict)
from .hive_export import HiveExportService
from .hive_import import HiveImportService
from .conflict_resolver import ConflictResolverService

# Legacy services (renamed from services.py to avoid package conflict)
from ..legacy_services import (
    MarkdownIngestionService,
    MarkdownExportService,
    sync_timeline_file,
    PotentialMatchException,
    IngestionValidationError,
)

__all__ = [
    # New services
    'HiveExportService',
    'HiveImportService',
    'ConflictResolverService',
    # Legacy services
    'MarkdownIngestionService',
    'MarkdownExportService',
    'sync_timeline_file',
    'PotentialMatchException',
    'IngestionValidationError',
]
