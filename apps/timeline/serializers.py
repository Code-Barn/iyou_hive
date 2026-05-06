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
            'created_by', 'created_by_username', 'timeline_file'
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
