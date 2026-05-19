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
