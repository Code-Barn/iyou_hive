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
from .models import TimelineEvent, TimelineCollection
from apps.archive.models import ArchiveDocument
from apps.core.models import Case


class ArchiveDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ArchiveDocument
        fields = ['id', 'title', 'file_type', 'file_url', 'path', 'category']
    
    def get_file_url(self, obj):
        return obj.get_file_url()


class TimelineEventSerializer(serializers.ModelSerializer):
    evidence = ArchiveDocumentSerializer(many=True, read_only=True)
    replaces_event = serializers.PrimaryKeyRelatedField(read_only=True)
    counter_claims = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    case_id = serializers.UUIDField(source='case.id', read_only=True)
    
    class Meta:
        model = TimelineEvent
        fields = [
            'id', 'date', 'event', 'category', 'source_type',
            'status', 'source_party', 'citation', 'notes', 'version',
            'created_at', 'updated_at', 'evidence',
            'replaces_event', 'counter_claims', 'case', 'case_id',
            'created_by', 'created_by_username', 'timeline_file',
            'is_system_source', 'trust_level', 'has_gold_seal',
            'section_header', 'last_printed_citation',
            'is_trivial', 'significance'
        ]
        read_only_fields = [
            'id', 'version', 'created_at', 'updated_at',
            'created_by', 'counter_claims', 'case', 'case_id'
        ]


class TimelineCollectionSerializer(serializers.ModelSerializer):
    events = TimelineEventSerializer(many=True, read_only=True)
    case_id = serializers.UUIDField(source='case.id', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    event_count = serializers.IntegerField(source='events.count', read_only=True)
    
    class Meta:
        model = TimelineCollection
        fields = [
            'id', 'name', 'description', 'events', 'case', 'case_id',
            'created_by', 'created_by_username', 'created_at', 'updated_at',
            'is_public', 'event_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'created_by_username', 'case_id']


class DiffViewSerializer(serializers.Serializer):
    """Serializer for diff view data."""
    left_party = serializers.CharField()
    right_party = serializers.CharField()
    shared = TimelineEventSerializer(many=True)
    left_only = TimelineEventSerializer(many=True)
    right_only = TimelineEventSerializer(many=True)
    contested = serializers.DictField(child=serializers.DictField())


class ContestedPairSerializer(serializers.Serializer):
    """Serializer for a pair of contested events."""
    left = TimelineEventSerializer()
    right = TimelineEventSerializer()
    diff = serializers.DictField()
