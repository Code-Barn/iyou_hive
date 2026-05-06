HIVE PORTABILITY & CONFLICT RESOLUTION - ARCHITECTURE PLAN**

---

## **1. DIRECTORY STRUCTURE (Data Compartmentalization)**

```
media/
└── hives/
    └── [case_uuid]/                    # Case-root directory
        ├── formal/                     # VAULT: Shared evidence + Master Timeline
        │   ├── evidence/               # ArchiveDocument files (shared)
        │   │   └── [doc_uuid].[ext]
        │   ├── timeline/               # Export/import staging
        │   │   └── timeline.md
        │   └── hive.json               # Export manifest (optional cache)
        │
        └── private/                    # WORKSPACE: User-isolated
            └── [user_uuid]/            # Per-user compartment
                ├── drafts/            # Unpromoted timeline events
                ├── wiki/               # LLM Wiki pages (markdown)
                ├── research/           # AI analysis outputs
                └── temp/               # Upload staging (auto-cleaned)
```

---

## **2. HIVE EXPORT SERVICE**

### **2.1 Schema: `hive.json` Manifest**

```json
{
  "version": "1.0",
  "case": {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Smith v. Jones",
    "description": "...",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-05-20T14:30:00Z"
  },
  "timeline_events": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440001",
      "date": "2023-11-05",
      "event": "Contract Signed",
      "category": "contract",
      "notes": "Signed with...",
      "source_party": "CLIENT",
      "status": "UNDISPUTED",
      "version": 1,
      "replaces_event": null,
      "evidence_uuids": ["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"],
      "case_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "created_by_uuid": "ffffffff-eeee-dddd-cccc-bbbb-aaaaaaaaaaaa"
    }
  ],
  "archive_documents": [
    {
      "uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      "title": "Contract.pdf",
      "file_type": "pdf",
      "category": "contract",
      "original_filename": "contract_final.pdf",
      "checksum": "sha256:abc123...",
      "file_path": "formal/evidence/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.pdf",
      "uploader_uuid": "ffffffff-eeee-dddd-cccc-bbbb-aaaaaaaaaaaa",
      "case_uuid": "550e8400-e29b-41d4-a716-446655440000"
    }
  ],
  "timeline_collections": [
    {
      "uuid": "11111111-2222-3333-4444-555555555555",
      "name": "Plaintiff Timeline",
      "description": "...",
      "case_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "created_by_uuid": "ffffffff-eeee-dddd-cccc-bbbb-aaaaaaaaaaaa",
      "event_uuids": ["550e8400-e29b-41d4-a716-446655440001"]
    }
  ]
}
```

### **2.2 `HiveExportService` Class Design**

```python
# apps/timeline/services/hive_export.py

class HiveExportService:
    """
    Exports a Case and all related data to a .hive tar.gz bundle.
    """

    def __init__(self, case: Case):
        self.case = case
        self.temp_dir = tempfile.mkdtemp(prefix=f"hive_export_{case.uuid}_")
        self.manifest = {
            "version": "1.0",
            "case": None,
            "timeline_events": [],
            "archive_documents": [],
            "timeline_collections": []
        }

    def export(self) -> str:
        """Main entry point. Returns path to .hive file."""
        self._build_manifest()
        self._copy_files()
        return self._package_bundle()

    def _build_manifest(self):
        """Serialize all DB records to manifest JSON."""
        # Case
        self.manifest["case"] = self._serialize_case()

        # TimelineEvents (with evidence relationships preserved via UUID)
        self.manifest["timeline_events"] = [
            self._serialize_event(e) for e in
            TimelineEvent.objects.filter(case=self.case)
        ]

        # ArchiveDocuments
        self.manifest["archive_documents"] = [
            self._serialize_document(d) for d in
            ArchiveDocument.objects.filter(case=self.case)
        ]

        # TimelineCollections
        self.manifest["timeline_collections"] = [
            self._serialize_collection(c) for c in
            TimelineCollection.objects.filter(case=self.case)
        ]

        # Write manifest to temp dir
        with open(os.path.join(self.temp_dir, "hive.json"), "w") as f:
            json.dump(self.manifest, f, indent=2, default=str)

    def _copy_files(self):
        """Copy all files from formal/ and private/ to temp dir."""
        hive_base = os.path.join(settings.MEDIA_ROOT, "hives", str(self.case.uuid))

        # Copy formal evidence
        formal_src = os.path.join(hive_base, "formal", "evidence")
        formal_dst = os.path.join(self.temp_dir, "formal", "evidence")
        if os.path.exists(formal_src):
            shutil.copytree(formal_src, formal_dst)

        # Copy wiki/research (optional: user can choose to include private data)
        # For now, only formal is exported by default

    def _package_bundle(self) -> str:
        """Create tar.gz from temp dir, return file path."""
        output_path = os.path.join(
            settings.MEDIA_ROOT, "exports",
            f"{self.case.uuid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.hive"
        )
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(self.temp_dir, arcname=".")
        shutil.rmtree(self.temp_dir)
        return output_path

    def _serialize_case(self) -> dict:
        return {
            "uuid": str(self.case.uuid),
            "name": self.case.name,
            "description": self.case.description,
            "created_at": self.case.created_at.isoformat(),
            "updated_at": self.case.updated_at.isoformat()
        }

    def _serialize_event(self, event: TimelineEvent) -> dict:
        return {
            "uuid": str(event.uuid),
            "date": event.date.isoformat(),
            "event": event.event,
            "category": event.category,
            "notes": event.notes,
            "source_party": event.source_party,
            "status": event.status,
            "version": event.version,
            "replaces_event": str(event.replaces_event.uuid) if event.replaces_event else None,
            "evidence_uuids": [str(d.uuid) for d in event.evidence.all()],
            "case_uuid": str(event.case.uuid),
            "created_by_uuid": str(event.created_by.uuid)
        }

    def _serialize_document(self, doc: ArchiveDocument) -> dict:
        return {
            "uuid": str(doc.uuid),
            "title": doc.title,
            "file_type": doc.file_type,
            "category": doc.category,
            "original_filename": doc.original_filename,
            "checksum": doc.checksum,
            "file_path": f"formal/evidence/{doc.uuid}.{doc.file_type}",
            "uploader_uuid": str(doc.uploader.uuid),
            "case_uuid": str(doc.case.uuid)
        }

    def _serialize_collection(self, collection: TimelineCollection) -> dict:
        return {
            "uuid": str(collection.uuid),
            "name": collection.name,
            "description": collection.description,
            "case_uuid": str(collection.case.uuid),
            "created_by_uuid": str(collection.created_by.uuid),
            "event_uuids": [str(e.uuid) for e in collection.events.all()]
        }
```

---

## **3. HIVE IMPORT SERVICE**

### **3.1 `HiveImportService` Class Design**

```python
# apps/timeline/services/hive_import.py

class HiveImportService:
    """
    Imports a .hive bundle, recreating all records with new UUIDs
    to prevent collisions while preserving relationships.
    """

    def __init__(self, hive_path: str, target_case: Case = None, user: User = None):
        self.hive_path = hive_path
        self.target_case = target_case  # If None, create new case
        self.user = user  # Required for ownership
        self.temp_dir = tempfile.mkdtemp(prefix="hive_import_")
        self.uuid_map = {}  # old_uuid -> new_uuid for all entity types
        self.errors = []

    def import_bundle(self) -> Case:
        """Main entry point. Returns the imported/created Case."""
        self._extract_bundle()
        manifest = self._load_manifest()

        # Create or use target case
        case = self._create_case(manifest["case"])

        # Import in dependency order: Documents -> Events -> Collections
        self._import_documents(manifest["archive_documents"], case)
        self._import_events(manifest["timeline_events"], case)
        self._import_collections(manifest["timeline_collections"], case)

        self._copy_files(case)
        self._cleanup()
        return case

    def _extract_bundle(self):
        """Extract .hive tar.gz to temp dir."""
        with tarfile.open(self.hive_path, "r:gz") as tar:
            tar.extractall(self.temp_dir)

    def _load_manifest(self) -> dict:
        """Load and validate hive.json from temp dir."""
        manifest_path = os.path.join(self.temp_dir, "hive.json")
        with open(manifest_path) as f:
            return json.load(f)

    def _create_case(self, case_data: dict) -> Case:
        """Create or update the target Case."""
        if self.target_case:
            return self.target_case
        return Case.objects.create(
            uuid=case_data["uuid"],  # Preserve case UUID for identity
            name=case_data["name"],
            description=case_data["description"],
            user=self.user
        )

    def _import_documents(self, docs: list, case: Case):
        """Import ArchiveDocuments with new UUIDs."""
        for doc_data in docs:
            new_uuid = uuid.uuid4()
            self.uuid_map[doc_data["uuid"]] = str(new_uuid)

            # Create document record (file copied later)
            ArchiveDocument.objects.create(
                uuid=new_uuid,
                title=doc_data["title"],
                file_type=doc_data["file_type"],
                category=doc_data["category"],
                original_filename=doc_data["original_filename"],
                checksum=doc_data["checksum"],
                uploader=self.user,
                case=case,
                # timeline_event left null (use evidence M2M only)
            )

    def _import_events(self, events: list, case: Case):
        """Import TimelineEvents with new UUIDs, preserving relationships."""
        for event_data in events:
            new_uuid = uuid.uuid4()
            self.uuid_map[event_data["uuid"]] = str(new_uuid)

            # Resolve replaces_event (may reference another imported event)
            replaces_uuid = event_data.get("replaces_event")
            replaces_event = None
            if replaces_uuid and replaces_uuid in self.uuid_map:
                replaces_event = TimelineEvent.objects.get(uuid=self.uuid_map[replaces_uuid])

            # Create event
            event = TimelineEvent.objects.create(
                uuid=new_uuid,
                date=event_data["date"],
                event=event_data["event"],
                category=event_data["category"],
                notes=event_data["notes"],
                source_party=event_data["source_party"],
                status=event_data["status"],
                version=event_data.get("version", 1),
                replaces_event=replaces_event,
                case=case,
                created_by=self.user
            )

            # Store for M2M linking (done after all events created)
            self._pending_evidence[new_uuid] = event_data.get("evidence_uuids", [])

        # Second pass: link evidence M2M
        for new_uuid, evidence_uuids in self._pending_evidence.items():
            event = TimelineEvent.objects.get(uuid=new_uuid)
            docs = ArchiveDocument.objects.filter(
                uuid__in=[self.uuid_map[old_uuid] for old_uuid in evidence_uuids
                          if old_uuid in self.uuid_map]
            )
            event.evidence.set(docs)

    def _import_collections(self, collections: list, case: Case):
        """Import TimelineCollections with new UUIDs."""
        for coll_data in collections:
            new_uuid = uuid.uuid4()
            self.uuid_map[coll_data["uuid"]] = str(new_uuid)

            collection = TimelineCollection.objects.create(
                uuid=new_uuid,
                name=coll_data["name"],
                description=coll_data["description"],
                case=case,
                created_by=self.user,
                is_public=False  # Default: imported collections are private
            )

            # Link events
            event_uuids = [
                self.uuid_map[old_uuid]
                for old_uuid in coll_data.get("event_uuids", [])
                if old_uuid in self.uuid_map
            ]
            collection.events.set(
                TimelineEvent.objects.filter(uuid__in=event_uuids)
            )

    def _copy_files(self, case: Case):
        """Copy files from temp dir to hive directory."""
        hive_base = os.path.join(
            settings.MEDIA_ROOT, "hives", str(case.uuid)
        )
        os.makedirs(os.path.join(hive_base, "formal", "evidence"), exist_ok=True)

        formal_src = os.path.join(self.temp_dir, "formal", "evidence")
        if os.path.exists(formal_src):
            for filename in os.listdir(formal_src):
                # Rename file to match new document UUID
                old_uuid = filename.split(".")[0]
                if old_uuid in self.uuid_map:
                    new_uuid = self.uuid_map[old_uuid]
                    ext = filename.rsplit(".", 1)[1]
                    new_filename = f"{new_uuid}.{ext}"
                    src = os.path.join(formal_src, filename)
                    dst = os.path.join(hive_base, "formal", "evidence", new_filename)
                    shutil.copy2(src, dst)

    def _cleanup(self):
        """Remove temp dir."""
        shutil.rmtree(self.temp_dir)
```

---

## **4. GATE LOGIC (Vault ↔ Workspace)**

### **4.1 Directory Service**

```python
# apps/core/services/hive_directory.py

class HiveDirectoryService:
    """
    Manages the isolated directory structure for Hive compartments.
    """

    @staticmethod
    def get_formal_path(case: Case) -> str:
        """Path to shared evidence vault."""
        return os.path.join(settings.MEDIA_ROOT, "hives", str(case.uuid), "formal")

    @staticmethod
    def get_private_path(case: Case, user: User) -> str:
        """Path to user's private workspace."""
        return os.path.join(
            settings.MEDIA_ROOT, "hives", str(case.uuid),
            "private", str(user.uuid)
        )

    @staticmethod
    def ensure_directories(case: Case, user: User = None):
        """Create all necessary directories for a case."""
        os.makedirs(HiveDirectoryService.get_formal_path(case), exist_ok=True)
        if user:
            os.makedirs(
                os.path.join(HiveDirectoryService.get_private_path(case, user), "drafts"),
                exist_ok=True
            )
            os.makedirs(
                os.path.join(HiveDirectoryService.get_private_path(case, user), "wiki"),
                exist_ok=True
            )
            os.makedirs(
                os.path.join(HiveDirectoryService.get_private_path(case, user), "research"),
                exist_ok=True
            )
            os.makedirs(
                os.path.join(HiveDirectoryService.get_private_path(case, user), "temp"),
                exist_ok=True
            )

    @staticmethod
    def promote_to_evidence(document: ArchiveDocument, case: Case, user: User) -> ArchiveDocument:
        """
        Gate Logic: Move a file from private to formal.

        This is a user-triggered action that:
        1. Validates the user owns the document
        2. Copies the file from private to formal
        3. Updates the document record
        4. Optionally links to timeline events
        """
        from apps.timeline.models import ArchiveDocument

        # Validate ownership
        if document.uploader != user or document.case != case:
            raise PermissionDenied("Cannot promote another user's document")

        # Get current file path (private)
        old_path = document.file.path
        if not os.path.exists(old_path):
            raise FileNotFoundError(f"Document file not found: {old_path}")

        # Create new path in formal
        ext = os.path.splitext(old_path)[1][1:]  # Remove leading dot
        new_filename = f"{document.uuid}.{ext}"
        new_path = os.path.join(
            HiveDirectoryService.get_formal_path(case),
            "evidence", new_filename
        )
        os.makedirs(os.path.dirname(new_path), exist_ok=True)

        # Copy file
        shutil.copy2(old_path, new_path)

        # Update document record
        document.file.name = os.path.relpath(new_path, settings.MEDIA_ROOT)
        document.is_promoted = True
        document.promoted_at = timezone.now()
        document.save()

        return document
```

---

## **5. CONFLICT RESOLVER**

### **5.1 Backend: Contest Service**

```python
# apps/timeline/services/conflict_resolver.py

class ConflictResolverService:
    """
    Manages the Git-style conflict resolution workflow.
    """

    def contest_event(self, original_event: TimelineEvent, user: User,
                      event_data: dict, evidence_ids: list) -> TimelineEvent:
        """
        Create a counter-claim that contests an existing event.

        Args:
            original_event: The event being contested
            user: The user creating the counter-claim
            event_data: dict with date, event, category, notes
            evidence_ids: List of ArchiveDocument IDs to link as evidence

        Returns:
            The new counter-claim TimelineEvent
        """
        from apps.timeline.models import TimelineEvent
        from django.utils import timezone

        # Validate: Contested/Refuted requires evidence
        status = event_data.get("status", "CONTESTED")
        if status in ["CONTESTED", "REFUTED"] and not evidence_ids:
            raise ValidationError("CONTESTED and REFUTED events require evidence")

        # Create counter-claim
        counter_claim = TimelineEvent.objects.create(
            uuid=uuid.uuid4(),
            date=event_data["date"],
            event=event_data["event"],
            category=event_data["category"],
            notes=event_data.get("notes", ""),
            source_party=user.party,  # User's perspective
            status=status,
            version=original_event.version + 1,
            replaces_event=original_event,  # Link to original
            case=original_event.case,
            created_by=user,
            created_at=timezone.now()
        )

        # Link evidence
        if evidence_ids:
            counter_claim.evidence.set(evidence_ids)

        return counter_claim

    def resolve_conflict(self, original_event: TimelineEvent, resolution: str,
                         user: User, notes: str = "") -> TimelineEvent:
        """
        Resolve a conflict between events.

        Args:
            original_event: The original event (or the one to keep)
            resolution: One of "KEEP_ORIGINAL", "KEEP_COUNTER", "MERGE"
            user: The user resolving the conflict
            notes: Optional resolution notes

        Returns:
            The resolved TimelineEvent
        """
        if not original_event.replaces_event and not TimelineEvent.objects.filter(
            replaces_event=original_event
        ).exists():
            raise ValidationError("No conflict to resolve for this event")

        if resolution == "KEEP_ORIGINAL":
            # Mark counter-claims as superseded
            counter_claims = TimelineEvent.objects.filter(replaces_event=original_event)
            counter_claims.update(
                status="SUPERSEDED",
                notes=f"{notes}\n\n[Resolved by {user.email}: Kept original]"
            )
            return original_event

        elif resolution == "KEEP_COUNTER":
            counter_claim = TimelineEvent.objects.filter(
                replaces_event=original_event
            ).order_by("-created_at").first()
            if not counter_claim:
                raise ValidationError("No counter-claim found")

            # Mark original as superseded
            original_event.status = "SUPERSEDED"
            original_event.notes = f"{original_event.notes}\n\n[Resolved by {user.email}: Replaced by counter-claim]"
            original_event.save()

            return counter_claim

        elif resolution == "MERGE":
            counter_claim = TimelineEvent.objects.filter(
                replaces_event=original_event
            ).order_by("-created_at").first()

            # Create new STIPULATED event
            merged = TimelineEvent.objects.create(
                uuid=uuid.uuid4(),
                date=original_event.date,  # Or allow customization
                event=f"[STIPULATED] {original_event.event}",
                category=original_event.category,
                notes=f"Original: {original_event.notes}\n\nCounter: {counter_claim.notes}\n\n{notes}",
                source_party="COURT",  # Neutral authority
                status="STIPULATED",
                version=max(original_event.version, counter_claim.version) + 1,
                replaces_event=original_event,  # Links to original
                case=original_event.case,
                created_by=user,
                created_at=timezone.now()
            )

            # Merge evidence from both
            all_evidence = list(original_event.evidence.all()) + list(counter_claim.evidence.all())
            merged.evidence.set(all_evidence)

            # Mark both as superseded
            original_event.status = "SUPERSEDED"
            original_event.save()
            counter_claim.status = "SUPERSEDED"
            counter_claim.save()

            return merged

    def get_conflict_chain(self, event: TimelineEvent) -> list:
        """
        Get the full chain of an event and all its replacements.

        Returns list of TimelineEvents in chronological order.
        """
        chain = []
        current = event

        while current:
            chain.append(current)
            # Find the event that this one replaces (go backwards)
            # Actually, we want to follow replaces_event forward
            # Let's get all events that replace this one
            replacements = list(TimelineEvent.objects.filter(replaces_event=current))
            if replacements:
                # Get the latest replacement
                current = replacements[0]
            else:
                current = None

        return chain
```

### **5.2 API Endpoints**

```python
# apps/timeline/api_views.py - Additions

from rest_framework.decorators import action
from rest_framework.response import Response

class TimelineEventViewSet(viewsets.ModelViewSet):
    # ... existing code ...

    @action(detail=True, methods=['POST'])
    def contest(self, request, pk=None, case_pk=None):
        """Create a counter-claim contesting this event."""
        event = self.get_object()
        user = request.user

        # User cannot contest their own event if same source_party
        if event.source_party == user.party:
            return Response(
                {"error": "Cannot contest your own event"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TimelineEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        evidence_ids = request.data.get('evidence_ids', [])
        if event.status in ["CONTESTED", "REFUTED"] and not evidence_ids:
            return Response(
                {"error": "Evidence required for CONTESTED/REFUTED events"},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = ConflictResolverService()
        counter_claim = service.contest_event(
            event, user,
            serializer.validated_data,
            evidence_ids
        )

        return Response(
            TimelineEventSerializer(counter_claim).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['POST'])
    def resolve(self, request, pk=None, case_pk=None):
        """Resolve a conflict for this event."""
        event = self.get_object()
        resolution = request.data.get('resolution')  # KEEP_ORIGINAL, KEEP_COUNTER, MERGE
        notes = request.data.get('notes', '')

        if not resolution:
            return Response(
                {"error": "resolution is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = ConflictResolverService()
        resolved = service.resolve_conflict(event, resolution, request.user, notes)

        return Response(
            TimelineEventSerializer(resolved).data,
            status=status.HTTP_200_OK
        )

class ConflictViewSet(viewsets.ViewSet):
    """Endpoint for conflict-specific operations."""

    def retrieve(self, request, pk=None, case_pk=None):
        """Get conflict details for an event (original + counter-claims)."""
        event = get_object_or_404(TimelineEvent, pk=pk, case__uuid=case_pk)

        service = ConflictResolverService()
        chain = service.get_conflict_chain(event)

        # Find all counter-claims to this event
        counter_claims = TimelineEvent.objects.filter(replaces_event=event)

        data = {
            "original": TimelineEventSerializer(event).data,
            "counter_claims": TimelineEventSerializer(counter_claims, many=True).data,
            "full_chain": TimelineEventSerializer(chain, many=True).data
        }

        return Response(data)
```

---

## **6. CONFLICT RESOLVER MODAL (React Component)**

```tsx
// src/components/ConflictResolverModal.tsx

import { useState } from 'react';
import { TimelineEvent } from '../types/timeline';
import { resolveConflict } from '../api/timeline';

interface ConflictResolverModalProps {
  originalEvent: TimelineEvent;
  counterClaim: TimelineEvent;
  onClose: () => void;
  onResolved: (resolvedEvent: TimelineEvent) => void;
}

type ResolutionType = 'KEEP_ORIGINAL' | 'KEEP_COUNTER' | 'MERGE';

export function ConflictResolverModal({
  originalEvent,
  counterClaim,
  onClose,
  onResolved
}: ConflictResolverModalProps) {
  const [resolution, setResolution] = useState<ResolutionType | null>(null);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleResolve = async () => {
    if (!resolution) {
      setError('Please select a resolution');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const resolvedEvent = await resolveConflict(
        counterClaim.id,  // Resolve via the counter-claim
        resolution,
        notes
      );
      onResolved(resolvedEvent);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Color mapping for status
  const statusColors = {
    UNDISPUTED: 'bg-gray-100 border-gray-300',
    CONTESTED: 'bg-yellow-100 border-yellow-300',
    REFUTED: 'bg-red-100 border-red-300',
    STIPULATED: 'bg-green-100 border-green-300',
  };

  const partyColors = {
    CLIENT: 'bg-blue-500',
    OPPOSING: 'bg-red-500',
    COURT: 'bg-purple-500',
    WITNESS: 'bg-green-500',
    NEUTRAL: 'bg-gray-500',
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-xl font-bold text-gray-800">Resolve Conflict</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X size={20} />
          </button>
        </div>

        {/* Conflict Display */}
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Original Claim */}
            <div className={`border rounded-lg p-4 ${statusColors[originalEvent.status]}`}>
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-3 h-3 rounded-full ${partyColors[originalEvent.source_party]}`} />
                <h3 className="font-semibold text-gray-800">Original Claim</h3>
                <span className="px-2 py-1 text-xs rounded-full bg-white">
                  {originalEvent.source_party}
                </span>
              </div>

              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-gray-600">Date:</span>
                  <span className="ml-2">{originalEvent.date}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-600">Event:</span>
                  <span className="ml-2">{originalEvent.event}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-600">Category:</span>
                  <span className="ml-2">{originalEvent.category}</span>
                </div>
                <div className="pt-2">
                  <span className="font-medium text-gray-600">Notes:</span>
                  <p className="ml-2 text-gray-700 whitespace-pre-wrap">{originalEvent.notes}</p>
                </div>
                <div className="pt-2">
                  <span className="font-medium text-gray-600">Evidence:</span>
                  <div className="ml-2 flex flex-wrap gap-1">
                    {originalEvent.evidence?.map(doc => (
                      <span key={doc.uuid} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                        {doc.title}
                      </span>
                    )) || <span className="text-gray-500">None</span>}
                  </div>
                </div>
              </div>
            </div>

            {/* Counter Claim */}
            <div className={`border rounded-lg p-4 ${statusColors[counterClaim.status]}`}>
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-3 h-3 rounded-full ${partyColors[counterClaim.source_party]}`} />
                <h3 className="font-semibold text-gray-800">Counter Claim</h3>
                <span className="px-2 py-1 text-xs rounded-full bg-white">
                  {counterClaim.source_party}
                </span>
                <span className="px-2 py-1 text-xs rounded-full bg-yellow-200 text-yellow-800">
                  Replaces: {originalEvent.event.slice(0, 20)}...
                </span>
              </div>

              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium text-gray-600">Date:</span>
                  <span className="ml-2">{counterClaim.date}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-600">Event:</span>
                  <span className="ml-2">{counterClaim.event}</span>
                </div>
                <div>
                  <span className="font-medium text-gray-600">Category:</span>
                  <span className="ml-2">{counterClaim.category}</span>
                </div>
                <div className="pt-2">
                  <span className="font-medium text-gray-600">Notes:</span>
                  <p className="ml-2 text-gray-700 whitespace-pre-wrap">{counterClaim.notes}</p>
                </div>
                <div className="pt-2">
                  <span className="font-medium text-gray-600">Evidence:</span>
                  <div className="ml-2 flex flex-wrap gap-1">
                    {counterClaim.evidence?.map(doc => (
                      <span key={doc.uuid} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                        {doc.title}
                      </span>
                    )) || <span className="text-gray-500">None</span>}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Resolution Options */}
        <div className="p-4 border-t">
          <h3 className="font-semibold text-gray-800 mb-3">Select Resolution</h3>

          {error && (
            <div className="bg-red-50 text-red-600 p-2 rounded mb-3">{error}</div>
          )}

          <div className="space-y-3">
            <label className="flex items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
              <input
                type="radio"
                name="resolution"
                checked={resolution === 'KEEP_ORIGINAL'}
                onChange={() => setResolution('KEEP_ORIGINAL')}
                className="mr-3"
              />
              <div>
                <div className="font-medium">Keep Original Claim</div>
                <div className="text-sm text-gray-600">
                  Discard the counter-claim and retain the original event as truth.
                </div>
              </div>
            </label>

            <label className="flex items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
              <input
                type="radio"
                name="resolution"
                checked={resolution === 'KEEP_COUNTER'}
                onChange={() => setResolution('KEEP_COUNTER')}
                className="mr-3"
              />
              <div>
                <div className="font-medium">Keep Counter Claim</div>
                <div className="text-sm text-gray-600">
                  Replace the original with the counter-claim as the new truth.
                </div>
              </div>
            </label>

            <label className="flex items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
              <input
                type="radio"
                name="resolution"
                checked={resolution === 'MERGE'}
                onChange={() => setResolution('MERGE')}
                className="mr-3"
              />
              <div>
                <div className="font-medium">Merge into Stipulated</div>
                <div className="text-sm text-gray-600">
                  Combine both perspectives into a single STIPULATED event with merged evidence.
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Notes */}
        <div className="p-4 border-t">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Resolution Notes (optional)
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Explain the resolution for audit purposes..."
            className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            rows={3}
          />
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 p-4 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
          >
            Cancel
          </button>
          <button
            onClick={handleResolve}
            disabled={!resolution || isSubmitting}
            className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-blue-300"
          >
            {isSubmitting ? 'Resolving...' : 'Resolve Conflict'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## **7. SHREDDER SERVICE (Secure Erase)**

### **7.1 Backend Service**

```python
# apps/core/services/shredder.py

import os
import shutil
from django.conf import settings
from django.db import transaction
from apps.timeline.models import TimelineEvent, TimelineCollection
from apps.archive.models import ArchiveDocument
from apps.core.models import Case

class ShredderService:
    """
    Securely and recursively deletes all files in a Hive directory
    and purges all related database rows.
    """

    def __init__(self, case: Case):
        self.case = case

    def shred_case(self, user: User = None) -> dict:
        """
        Completely erase a case and all its data.

        Args:
            user: Optional - if provided, only shred user's private data.
                  If None, shred entire case (admin only).

        Returns:
            dict with counts of deleted items
        """
        if user:
            return self._shred_user_data(user)
        else:
            return self._shred_entire_case()

    def _shred_entire_case(self) -> dict:
        """
        Shred ALL data for a case (files + DB records).
        Requires admin privileges.
        """
        counts = {
            'archive_documents': 0,
            'timeline_events': 0,
            'timeline_collections': 0,
            'files': 0
        }

        with transaction.atomic():
            # 1. Delete all files first (to free up DB references)
            hive_path = os.path.join(settings.MEDIA_ROOT, "hives", str(self.case.uuid))
            if os.path.exists(hive_path):
                counts['files'] = self._delete_directory_recursive(hive_path)

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

        return counts

    def _shred_user_data(self, user: User) -> dict:
        """
        Shred only the specified user's private data for this case.
        """
        counts = {
            'archive_documents': 0,
            'timeline_events': 0,
            'timeline_collections': 0,
            'files': 0
        }

        with transaction.atomic():
            # 1. Delete user's private files
            private_path = os.path.join(
                settings.MEDIA_ROOT, "hives", str(self.case.uuid),
                "private", str(user.uuid)
            )
            if os.path.exists(private_path):
                counts['files'] = self._delete_directory_recursive(private_path)

            # 2. Delete user's private TimelineCollections
            collections = TimelineCollection.objects.filter(
                case=self.case,
                created_by=user
            )
            counts['timeline_collections'] = collections.count()
            collections.delete()

            # 3. Delete user's TimelineEvents (only those created by user)
            events = TimelineEvent.objects.filter(
                case=self.case,
                created_by=user
            )
            counts['timeline_events'] = events.count()
            events.delete()

            # 4. Delete user's ArchiveDocuments (only those uploaded by user)
            documents = ArchiveDocument.objects.filter(
                case=self.case,
                uploader=user
            )
            counts['archive_documents'] = documents.count()
            documents.delete()

        return counts

    def _delete_directory_recursive(self, path: str) -> int:
        """
        Recursively delete a directory and all its contents.
        Returns count of files deleted.
        """
        count = 0
        if not os.path.exists(path):
            return 0

        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    os.unlink(file_path)
                    count += 1
                except Exception as e:
                    # Log but continue
                    pass

            for name in dirs:
                dir_path = os.path.join(root, name)
                try:
                    os.rmdir(dir_path)
                except Exception as e:
                    # Log but continue
                    pass

        # Remove the top-level directory
        try:
            os.rmdir(path)
        except Exception as e:
            pass

        return count

    @classmethod
    def secure_wipe(cls, file_path: str):
        """
        Securely wipe a single file (overwrite before delete).
        For highly sensitive data.
        """
        if not os.path.exists(file_path):
            return

        # Overwrite file with random data
        file_size = os.path.getsize(file_path)
        with open(file_path, 'ba+') as f:
            f.seek(0)
            f.write(os.urandom(file_size))

        # Delete the file
        os.unlink(file_path)
```

### **7.2 API Endpoint**

```python
# apps/core/api_views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from .services.shredder import ShredderService
from apps.core.models import Case
from django.shortcuts import get_object_or_404

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_shred_user_data(request, case_uuid):
    """
    Shred the current user's private data for a specific case.
    """
    case = get_object_or_404(Case, uuid=case_uuid, user=request.user)
    service = ShredderService(case)
    counts = service.shred_case(user=request.user)

    return Response({
        'status': 'success',
        'message': 'User data shredded successfully',
        'deleted': counts
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def api_shred_entire_case(request, case_uuid):
    """
    Shred ALL data for a case (admin only).
    """
    case = get_object_or_404(Case, uuid=case_uuid)
    service = ShredderService(case)
    counts = service.shred_case()

    return Response({
        'status': 'success',
        'message': 'Case and all data shredded successfully',
        'deleted': counts
    })
```

---

## **8. FILE STRUCTURE SUMMARY**

```
apps/
├── core/
│   ├── services/
│   │   ├── hive_directory.py      # Vault/Workspace directory management
│   │   └── shredder.py             # Secure erase service
│   └── api_views.py                # Shred API endpoints
│
├── timeline/
│   ├── services/
│   │   ├── hive_export.py          # HiveExportService
│   │   ├── hive_import.py          # HiveImportService
│   │   └── conflict_resolver.py    # ConflictResolverService
│   └── api_views.py                # Conflict API endpoints
│
frontend/
└── src/
    └── components/
        └── ConflictResolverModal.tsx  # React conflict resolver UI
```

---

## **9. IMPLEMENTATION CHECKLIST**

- [ ] `HiveExportService` class
- [ ] `HiveImportService` class with UUID remapping
- [ ] `HiveDirectoryService` for vault/workspace isolation
- [ ] `ConflictResolverService` with contest/resolve/merge logic
- [ ] `ShredderService` with recursive file + DB deletion
- [ ] API endpoints: `/api/cases/{case_uuid}/export/`, `/api/cases/{case_uuid}/import/`
- [ ] API endpoints: `/api/cases/{case_uuid}/events/{pk}/contest/`, `/api/cases/{case_uuid}/events/{pk}/resolve/`
- [ ] API endpoints: `/api/cases/{case_uuid}/shred-user/`, `/api/cases/{case_uuid}/shred-all/` (admin)
- [ ] React `ConflictResolverModal` component
- [ ] Directory structure migration script (if existing data needs to move)
