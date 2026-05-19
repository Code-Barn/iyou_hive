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

from rest_framework import serializers
from django.conf import settings
from apps.archive.models import ArchiveDocument
from apps.timeline.models import TimelineEvent
from apps.core.services.hive_directory import HiveDirectoryService
import os
import uuid
from typing import Any

class TimelineEventUuidSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimelineEvent
        fields = ['uuid', 'trust_level']

class ArchiveDocumentSerializer(serializers.ModelSerializer):
    timeline_event_uuids = serializers.SerializerMethodField()
    trust_level = serializers.SerializerMethodField()
    has_md_twin = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    virtual_path = serializers.SerializerMethodField()

    class Meta:
        model = ArchiveDocument
        fields = ['uuid', 'title', 'file_type', 'path', 'is_promoted', 'promoted_at',
                  'timeline_event_uuids', 'trust_level', 'conversion_status',
                  'markdown_path', 'has_md_twin', 'file_url', 'virtual_path']

    def get_file_url(self, obj: ArchiveDocument) -> str:
        """Return the absolute URL for the stored file."""
        if obj.file:
            return obj.file.url
        return ""

    def get_virtual_path(self, obj: ArchiveDocument) -> str:
        """Return the virtual path from metadata, falling back to the logical path."""
        return obj.metadata.get('virtual_path', obj.path) if isinstance(obj.metadata, dict) else obj.path

    def get_timeline_event_uuids(self, obj):
        if obj.timeline_event:
            return [str(obj.timeline_event.uuid)]
        return []

    def get_trust_level(self, obj):
        # The trust_level for a document is derived from its linked TimelineEvent.
        # If no event is linked, or the event has no trust_level, return a default.
        if obj.timeline_event and obj.timeline_event.trust_level:
            return obj.timeline_event.trust_level
        return "Unverified" # Default trust level

    def get_has_md_twin(self, obj):
        # TASK 2: Check if document has a markdown twin
        # Either from conversion_status or by checking if markdown_path exists
        if obj.conversion_status == 'SUCCESS' and obj.markdown_path:
            return True
        # Also check if a corresponding .md file exists on filesystem
        if obj.file_type == 'pdf' and obj.file:
            md_path = obj.file.name.replace('.pdf', '.md')
            full_md_path = os.path.join(settings.MEDIA_ROOT, md_path)
            if os.path.exists(full_md_path):
                return True
        return False

class RecursiveFolderSerializer(serializers.Serializer):
    uuid = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField() # 'folder' or 'file'
    is_folder = serializers.BooleanField()
    children = serializers.SerializerMethodField()
    file_details = ArchiveDocumentSerializer(required=False)

    def get_children(self, obj):
        if obj['is_folder'] and 'children' in obj:
            # Pass the current case_uuid and user_uuid from context to children
            return RecursiveFolderSerializer(obj['children'], many=True, context=self.context).data
        return []

    def to_representation(self, instance):
        # Override to_representation to handle the recursive nature
        data = super().to_representation(instance)
        
        # Remove children if not a folder or no children
        if not data['is_folder'] or not data['children']:
            data.pop('children', None)
        return data

    @classmethod
    def build_tree(cls, case_uuid: str, user_uuid: str):
        case_uuid_str: str = str(case_uuid)
        user_uuid_str: str = str(user_uuid)

        documents = ArchiveDocument.objects.filter(case__id=case_uuid_str).select_related('timeline_event', 'uploader').order_by('path')

        tree: list[dict[str, Any]] = [
            {
                'uuid': str(uuid.uuid5(uuid.NAMESPACE_DNS, f'{case_uuid_str}/formal')),
                'name': 'Vault (Shared)',
                'type': 'folder',
                'is_folder': True,
                'children': []
            },
            {
                'uuid': str(uuid.uuid5(uuid.NAMESPACE_DNS, f'{case_uuid_str}/private/{user_uuid_str}')),
                'name': 'Workspace (Private)',
                'type': 'folder',
                'is_folder': True,
                'children': []
            }
        ]

        formal_root_node: dict[str, Any] = tree[0]
        private_root_node: dict[str, Any] = tree[1]

        def insert_node(current_children: list[dict[str, Any]], path_parts: list[str], node_data: dict[str, Any], is_file_node: bool = False) -> None:
            if not path_parts:
                return

            part: str = path_parts[0]
            existing_node: dict[str, Any] | None = next(
                (c for c in current_children if c['name'] == part and c['is_folder']),
                None
            )

            if len(path_parts) == 1:
                if is_file_node:
                    current_children.append(node_data)
                else:
                    if existing_node:
                        existing_node.update(node_data)
                    else:
                        current_children.append(node_data)
            else:
                if not existing_node:
                    full_path_segment: str = os.path.join(
                        (case_uuid_str if current_children is formal_root_node['children'] else
                         os.path.join(case_uuid_str, 'private', user_uuid_str)),
                        *path_parts[:len(path_parts)]
                    )
                    folder_uuid: str = str(uuid.uuid5(uuid.NAMESPACE_DNS, full_path_segment))
                    existing_node = {
                        'uuid': folder_uuid,
                        'name': part,
                        'type': 'folder',
                        'is_folder': True,
                        'children': []
                    }
                    current_children.append(existing_node)
                insert_node(existing_node['children'], path_parts[1:], node_data, is_file_node)

        for doc in documents:
            if not doc.path:
                continue

            # --- Vault routing from doc.path ---
            root_path_parts: list[str] = doc.path.split('/')
            if not root_path_parts:
                continue

            # --- Sub-tree path from metadata.virtual_path ---
            raw_virtual: str = doc.metadata.get('virtual_path', '') if isinstance(doc.metadata, dict) else ''
            sub_path_parts: list[str] = raw_virtual.split('/') if raw_virtual else root_path_parts[2:]

            node_data: dict[str, Any] = {
                'uuid': str(doc.uuid),
                'name': doc.title if doc.file_type != 'folder' else doc.title.replace('[FOLDER] ', ''),
                'type': doc.file_type,
                'is_folder': doc.file_type == 'folder',
                'file_details': doc,
                'path': doc.path,
            }

            if root_path_parts[0] == 'formal':
                insert_node(formal_root_node['children'], sub_path_parts, node_data, is_file_node=(doc.file_type != 'folder'))
            elif root_path_parts[0] == 'private':
                if len(root_path_parts) > 1 and root_path_parts[1] == user_uuid_str:
                    insert_node(private_root_node['children'], sub_path_parts, node_data, is_file_node=(doc.file_type != 'folder'))
                else:
                    insert_node(private_root_node['children'], root_path_parts[1:], node_data, is_file_node=(doc.file_type != 'folder'))
            else:
                if doc.is_promoted:
                    insert_node(formal_root_node['children'], sub_path_parts, node_data, is_file_node=(doc.file_type != 'folder'))
                else:
                    insert_node(private_root_node['children'], sub_path_parts, node_data, is_file_node=(doc.file_type != 'folder'))

        return tree
