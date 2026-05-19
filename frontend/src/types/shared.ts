/*
 * Copyright (C) 2026 Byers Brands, LLC
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 */

export interface FileNode {
  uuid: string;
  name: string;
  type: string;
  is_folder: boolean;
  children?: FileNode[];
  file_details?: {
    uuid: string;
    title: string;
    file_type: string;
    path: string;
    is_promoted: boolean;
    promoted_at: string | null;
    timeline_event_uuids: string[];
    trust_level: string;
    conversion_status: string;
    markdown_path: string | null;
    has_md_twin: boolean;
  };
}

export interface LayoutProps {
  caseId: string;
  userParty: string;
  onCaseSelect: (caseId: string) => void;
  onToggleFullTimeline?: () => void;
}
