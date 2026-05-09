from rest_framework import serializers
from django.conf import settings
from apps.archive.models import ArchiveDocument
from apps.timeline.models import TimelineEvent
from apps.core.services.hive_directory import HiveDirectoryService
import os
import uuid

class TimelineEventUuidSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimelineEvent
        fields = ['uuid', 'trust_level']

class ArchiveDocumentSerializer(serializers.ModelSerializer):
    timeline_event_uuids = serializers.SerializerMethodField()
    trust_level = serializers.SerializerMethodField()
    has_md_twin = serializers.SerializerMethodField()

    class Meta:
        model = ArchiveDocument
        fields = ['uuid', 'title', 'file_type', 'path', 'is_promoted', 'promoted_at', 'timeline_event_uuids', 'trust_level', 'conversion_status', 'markdown_path', 'has_md_twin']

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
        case_uuid_str = str(case_uuid)
        user_uuid_str = str(user_uuid)

        documents = ArchiveDocument.objects.filter(case__id=case_uuid_str).select_related('timeline_event', 'uploader').order_by('path')

        tree = [
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

        formal_root_node = tree[0]
        private_root_node = tree[1]

        def insert_node(current_children, path_parts, node_data, is_file_node=False):
            if not path_parts:
                return

            part = path_parts[0]
            existing_node = next((c for c in current_children if c['name'] == part and c['is_folder']), None) # Only match folders

            if len(path_parts) == 1: # This is the final part of the path
                if is_file_node:
                    if node_data['name'] != '.folder': # Avoid adding the .folder file itself
                        current_children.append(node_data)
                else: # It's a folder node represented by a .folder file or an implied folder
                    if existing_node:
                        existing_node.update(node_data) # Update existing placeholder folder node if more details are available
                    else:
                        current_children.append(node_data)
            else: # It's an intermediate folder
                if not existing_node:
                    # Create intermediate folder node
                    # Generate UUID based on the full path segment up to this point
                    # The full_path_segment needs to be relative to the case_uuid, not including it
                    full_path_segment_for_uuid = os.path.join(
                        (case_uuid_str if current_children == formal_root_node['children'] else
                         os.path.join(case_uuid_str, 'private', user_uuid_str)),
                        *path_parts[:len(path_parts)]
                    )
                    folder_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, full_path_segment_for_uuid))
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
            # TASK 2 FIX: Use doc.path (logical path with vault structure) instead of doc.file.name (storage path)
            # doc.path contains the vault structure like "formal/01_Raw/filename.pdf" or "private/uuid/03_Drafts/filename.pdf"
            # doc.file.name is the actual storage path like "archive/documents/filename.pdf"
            
            if not doc.path:
                continue
            
            # Parse the logical path to determine vault location
            path_parts = doc.path.split('/')
            
            if not path_parts:
                continue

            # TASK 2 FIX: Store the model instance, not pre-serialized data
            # This allows the serializer to properly handle the file_details field
            node_data = {
                'uuid': str(doc.uuid),
                'name': doc.title if doc.file_type != 'folder' else doc.title.replace('[FOLDER] ', ''),
                'type': doc.file_type,
                'is_folder': doc.file_type == 'folder',
                'file_details': doc  # Pass the model instance, not serialized data
            }

            # Route to correct vault based on path
            if len(path_parts) >= 1:
                if path_parts[0] == 'formal':
                    # Path: formal/01_Raw/filename.pdf or formal/04_Strategy/filename.pdf
                    insert_node(formal_root_node['children'], path_parts[1:], node_data, is_file_node=(doc.file_type != 'folder'))
                elif path_parts[0] == 'private':
                    # Path: private/[user_uuid]/03_Drafts/filename.pdf
                    if len(path_parts) > 1 and path_parts[1] == user_uuid_str:
                        insert_node(private_root_node['children'], path_parts[2:], node_data, is_file_node=(doc.file_type != 'folder'))
                    else:
                        # Fallback for different user_uuid or missing user part
                        insert_node(private_root_node['children'], path_parts[1:], node_data, is_file_node=(doc.file_type != 'folder'))
                else:
                    # Legacy documents without vault prefix
                    # Try to infer from is_promoted flag
                    if doc.is_promoted:
                        insert_node(formal_root_node['children'], path_parts, node_data, is_file_node=(doc.file_type != 'folder'))
                    else:
                        insert_node(private_root_node['children'], path_parts, node_data, is_file_node=(doc.file_type != 'folder'))
            
        return tree
