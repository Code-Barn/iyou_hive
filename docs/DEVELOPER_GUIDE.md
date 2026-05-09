# Hiver Developer Guide

**Architectural Source of Truth - React + Vite + Tailwind + Django API**

*Last Updated: 2026-05-08* | *Build: index-BfomkJw1.js / index-JNzbSqsV.css*

---

## 📖 Table of Contents

1. [Architecture Overview](#-architecture-overview)
2. [Sovereign UI Rules](#-sovereign-ui-rules)
3. [Data Standards](#-data-standards)
4. [Tech Stack](#-tech-stack)
5. [Backend Architecture](#-backend-architecture)
6. [Frontend Architecture](#-frontend-architecture)
7. [API Endpoints](#-api-endpoints)
8. [Models Reference](#-models-reference)
9. [Portability Protocols](#-portability-protocols)
10. [Security Protocols](#-security-protocols)

---

## 🏗️ Architecture Overview

Hiver implements a **React + Vite + Tailwind frontend** with a **Django REST API backend**, following a strict **3-Layer Wiki Architecture** for document processing.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                          │
│  React 18 + Vite 5 + Tailwind CSS 3 + TypeScript                    │
├─────────────────────────────────────────────────────────────────┤
│  frontend/                                                          │
│    ├── src/                                                         │
│    │   ├── App.tsx              - Root component with Layout    │
│    │   ├── components/          - All UI components              │
│    │   │   ├── Layout.tsx       - 3-panel dashboard              │
│    │   │   ├── FileTree.tsx     - Archive file tree              │
│    │   │   ├── ForensicTimeline.tsx - Timeline view           │
│    │   │   ├── AIAssistantChat.tsx - AI chat interface         │
│    │   │   ├── CaseDetailModal.tsx - Case cockpit             │
│    │   │   ├── TimelineEventModal.tsx - Event creation         │
│    │   │   └── ...                                        │
│    │   ├── api/                 - API client functions           │
│    │   └── types/               - TypeScript type definitions    │
│    ├── static/frontend/          - Built assets                    │
│    │   └── assets/              - JS/CSS with hash suffixes       │
│    │       ├── index-BfomkJw1.js  ✅ Current Build              │
│    │       └── index-JNzbSqsV.css  ✅ Current Build              │
└─────────────────────────────────────────────────────────────────┘
                            ↓ REST API
┌─────────────────────────────────────────────────────────────────┐
│                       API LAYER (Django REST)                       │
│  Django 5.2 + Django REST Framework + SimpleJWT                   │
├─────────────────────────────────────────────────────────────────┤
│  config/                                                          │
│    ├── urls.py                 - Root URL routing               │
│    └── settings.py             - Django configuration           │
│                                                                  │
│  apps/                                                             │
│    ├── core/                   - Case, 3-Layer Wiki models      │
│    │   ├── models.py           - Case, RawDocument, WikiPage    │
│    │   ├── views.py            - react_app_view for SPA        │
│    │   ├── api_views.py        - Case API endpoints             │
│    │   └── urls.py             - Core URL routing               │
│    │                                                         │
│    ├── timeline/               - Timeline events & parsing       │
│    │   ├── models.py           - TimelineEvent, TimelineFile    │
│    │   ├── api_views.py        - Timeline API endpoints        │
│    │   └── utils.py            - Markdown parsing logic         │
│    │                                                         │
│    ├── archive/                - Document storage & management  │
│    │   ├── models.py           - ArchiveDocument, Photo         │
│    │   ├── api_views.py        - Archive API endpoints          │
│    │   ├── api_urls.py         - Archive API URL routing        │
│    │   └── urls.py             - Legacy archive URLs            │
│    │                                                         │
│    └── ai_assistant/           - AI integration                  │
│        ├── models.py           - AIConversation                  │
│        ├── views.py            - AI views                       │
│        └── api_views.py        - AI API endpoints               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                  │
├─────────────────────────────────────────────────────────────────┤
│  SQLite (Default) / PostgreSQL (Production)                       │
│  └── Hive Directory Structure (media/hives/[case_uuid]/)          │
│      ├── formal/                    - Vault (Shared Evidence)     │
│      │   ├── evidence/              - Promoted documents         │
│      │   ├── timeline/              - Markdown exports           │
│      │   └── hive.json              - Export manifest            │
│      └── private/                   - Workspace (User-Isolated)  │
│          └── [user_uuid]/           - Per-user private data      │
│              ├── drafts/            - Unpromoted documents        │
│              ├── wiki/               - LLM Wiki pages             │
│              ├── research/           - AI analysis outputs         │
│              └── temp/               - Upload staging              │
└─────────────────────────────────────────────────────────────────┘
```

### Request Flow

1. **Frontend Request** → React component calls API via `axios`
2. **Django URL Dispatcher** → Routes to appropriate API view
3. **API View** → Processes request, queries models via ORM
4. **JSON Response** → Returns structured data to frontend
5. **React State Update** → Updates UI via React Query (TanStack)

---

## 🎨 Sovereign UI Rules

### Anchor Layout (IMMUTABLE)

**Panel Order: Left → Center → Right**

```
┌─────────────────────────────────────────────────────────────────┐
│  LEFT PANEL: Timeline                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 🕰️  ForensicTimeline                                           │ │
│  │     - Event cards with trust level badges                     │ │
│  │     - Gold Seal indicator for system sources                  │ │
│  │     - Source party coloring (CLIENT/OPPOSING/NEUTRAL)         │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

                    ✂️ DRAGGABLE DIVIDER

┌─────────────────────────────────────────────────────────────────┐
│  CENTER PANEL: Archive & Canvas (ELASTIC ANCHOR)                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 📁 FileTree (Top - ~40% height)                                │ │
│  │     - Vault (Shared) and Workspace (Private) folders            │ │
│  │     - 01_Raw, 02_Wiki, 03_Drafts, 04_Strategy, 05_Exports      │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │ 🖼️  DocumentPreviewModal / Canvas (Bottom - ~60% height)        │ │
│  │     - Document preview with metadata                           │ │
│  │     - Canvas for document analysis                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  VERTICAL SPLIT: Proportional expansion on collapse              │
└─────────────────────────────────────────────────────────────────┘

                    ✂️ DRAGGABLE DIVIDER

┌─────────────────────────────────────────────────────────────────┐
│  RIGHT PANEL: AI Assistant                                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ ✨ AIAssistantChat                                              │ │
│  │     - Conversation history                                      │ │
│  │     - Document analysis                                         │ │
│  │     - Timeline queries                                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Aesthetic: STRICT WHITE THEME

- **Background**: `bg-white`
- **Text**: `text-gray-900` (primary), `text-gray-600` (secondary)
- **Borders**: `border-gray-200`
- **Hover States**: `hover:bg-blue-50` or `hover:bg-gray-100`
- **Primary Accent**: `bg-primary` (defined in Tailwind config)
- **Shadows**: `shadow-sm` on headers

**Theme Enforcement**: No dark mode. All panels use white background with gray text for maximum readability of legal documents.

### Elasticity Rules

1. **Proportional Expansion on Collapse**: When a side panel collapses, the center panel expands proportionally
   - Left + Center: Center takes `center / (left + center)` of remaining space
   - Center + Right: Center takes `center / (center + right)` of remaining space
   - Only Center: Center takes 100% width

2. **Minimum Panel Width**: 10% of container width (`MIN_PANEL_PERCENT = 10`)

3. **Horizontal Split Elasticity**: Center panel has vertical split (FileTree top / Canvas bottom) with drag handle
   - Default ratio: 40% / 60%
   - Clamped between 10% and 90%
   - Persists per-case in localStorage

### Panel State Persistence

- Panel sizes stored in `localStorage` with keys:
  - `panel-sizes-{caseId}`: JSON string of {left, center, right} percentages
  - `panel-horizontal-{caseId}`: Horizontal split ratio (0.0-1.0)

---

## 📊 Data Standards

### Shared Magnet Logic

The **Shared Magnet** is the mechanism that ensures all case participants see the same Formal Vault evidence, while maintaining isolated Private Workspaces.

**Magnetic Attraction Rules:**
1. **Formal Vault** (`/formal/evidence/`): Shared across ALL users in a case
2. **Private Workspace** (`/private/[user_uuid]/`): User-isolated, never visible to others
3. **Promotion** (Magnet Activation): Moving a file from Private → Formal via `promote_to_evidence()`
4. **Demotion** (Magnet Release): Moving a file from Formal → Private via `demote_from_evidence()`

**Gate Logic Implementation:**
```python
# apps/core/services/hive_directory.py
HiveDirectoryService.promote_to_evidence(document, case, user)
HiveDirectoryService.demote_from_evidence(document, user)
```

### 5-Column Markdown Requirement

All timeline markdown files MUST follow the **5-column format** for proper parsing:

```markdown
| Date | Event | Description | Category | Documents |
|------|-------|-------------|----------|-----------|
| 2024-01-15 | Contract Signed | Initial agreement executed | contract | contract.pdf, amendment.pdf |
| 2024-03-20 | Payment Received | $10,000 deposit | financial | receipt.pdf |
```

**Column Definitions:**
| Column | Type | Required | Purpose |
|--------|------|----------|---------|
| Date | `YYYY-MM-DD` | ✅ Yes | Event date |
| Event | String | ✅ Yes | Event title |
| Description | String | ✅ Yes | Event details |
| Category | String | ✅ Yes | Event category (lowercase) |
| Documents | CSV | ✅ Yes | Comma-separated document names |

**Parsing Pipeline:**
1. `parse_markdown_file()` - Extracts headings, sections, tables
2. `parse_timeline_events_from_table()` - Parses 5-column tables
3. `validate_timeline_events()` - Validates required fields and date format
4. Events grouped by parent heading in `timelines` dictionary

**Categories Supported:**
- `contract`, `email`, `court_filing`, `communication`, `meeting`
- `deadline`, `personal`, `legal`, `medical`, `financial`
- `education`, `verified`, `contested`, `other`

### Trust Level Scale

| Level | Value | Description | Source | Badge |
|-------|-------|-------------|--------|-------|
| ⭐ | 1 | Low - Unverified | User claim without evidence | None |
| ⭐⭐ | 2 | Medium - User Verified | User claim with evidence | Blue |
| ⭐⭐⭐ | 3 | High - Documented | Documented claim (default) | Green |
| ⭐⭐⭐⭐ | 4 | Very High - Official Record | Official documents | Purple |
| ⭐⭐⭐⭐⭐ | 5 | Maximum - Court Stipulated | COURT/NEUTRAL sources | 🏆 Gold Seal |

**Gold Seal Properties:**
- `is_system_source = True`
- `status = STIPULATED`
- `source_party ∈ {COURT, NEUTRAL}`
- Visual: `🏆 Gold Seal` badge with yellow background

---

## 🛠️ Tech Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2.0 | UI Framework |
| Vite | 5.0.0 | Build Tool & Dev Server |
| Tailwind CSS | 3.3.6 | Utility-First CSS |
| TypeScript | 5.3.0 | Type Safety |
| @tanstack/react-query | 5.0.0 | Server State Management |
| axios | 1.6.0 | HTTP Client |
| react-router-dom | 6.20.0 | Client-Side Routing |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Django | 5.2.13+ | Web Framework |
| Django REST Framework | Latest | API Layer |
| SQLite | Built-in | Default Database |
| PostgreSQL | 15+ | Production Database |
| uv | Latest | Python Package Manager |

### External Systems
| System | Integration | Purpose |
|--------|-------------|---------|
| Ollama | LLM Client | Local LLM Inference |
| Google Gemini | LLM Client | Cloud LLM Access |
| Rust-DID | FFI via ctypes | Decentralized Identity |

---

## 🏛️ Backend Architecture

### 3-Layer Wiki Architecture

Hiver's document processing pipeline transforms raw uploads into structured, queryable knowledge.

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: RawDocument (IMMUTABLE)                                    │
├─────────────────────────────────────────────────────────────────┤
│  • Original uploaded documents (PDF, Markdown, JSON)               │
│  • Immutable once created (is_immutable=True)                      │
│  • Metadata: source_party (CLIENT/OPPOSING/NEUTRAL)               │
│  • Stored in: media/raw/<case_id>/                                  │
│  • Model: apps/core/models.py:RawDocument                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓ Sync Pipeline
                            (apps/core/tasks.py)
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: WikiPage (PROCESSED)                                      │
├─────────────────────────────────────────────────────────────────┤
│  • Normalized content derived from RawDocuments                   │
│  • Version history maintained automatically                       │
│  • Citation references track claims to sources                    │
│  • Category: VERIFIED vs CONTESTED                                  │
│  • Unique per case+title combination                                │
│  • Model: apps/core/models.py:WikiPage                            │
└─────────────────────────────────────────────────────────────────┘
                            ↓ Schema Rules
                            (apps/core/prompts.py)
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: SchemaRule (LLM FORMATTING)                              │
├─────────────────────────────────────────────────────────────────┤
│  • Defines how LLM should format/structure content                 │
│  • Applied during document sync and query processing              │
│  • Unique per case+rule_name combination                           │
│  • Model: apps/core/models.py:SchemaRule                           │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Service

The `HiveDirectoryService` (apps/core/services/hive_directory.py) manages all file operations:

```python
# Create standard folder structure for new cases
ArchiveDocument.create_standard_folder_structure(case, user)
# Creates: 01_Raw, 02_Wiki, 03_Drafts, 04_Strategy, 05_Exports

# Gate Logic
HiveDirectoryService.promote_to_evidence(document, case, user)
HiveDirectoryService.demote_from_evidence(document, user)

# File Operations
HiveDirectoryService.move_document(source, destination, user)
```

---

## 🎨 Frontend Architecture

### Component Hierarchy

```
App.tsx
└── QueryClientProvider (TanStack React Query)
    └── Layout.tsx (3-Panel Dashboard)
        ├── LEFT: Timeline Panel
        │   ├── Panel Header (Timeline + Full Screen + Collapse)
        │   └── ForensicTimeline.tsx
        │       ├── EventCard.tsx (with trust level badges)
        │       └── TimelineToolbar.tsx (Add Event, Upload Markdown)
        │
        ├── CENTER: Archive & Canvas Panel (ELASTIC ANCHOR)
        │   ├── Panel Header (Archive + Ingest + Full Screen + Collapse)
        │   ├── FileTree.tsx (Top - ~40%)
        │   │   └── FileActions.tsx (Upload to Workspace)
        │   ├── Horizontal Divider (Draggable)
        │   └── Canvas Area (Bottom - ~60%)
        │       └── DocumentPreviewModal.tsx
        │
        └── RIGHT: AI Assistant Panel
            ├── Panel Header (AI + Settings + Full Screen + Collapse)
            └── AIAssistantChat.tsx
                └── InspectorPanel.tsx

# Modals (Overlaid on Layout)
- CaseSelector (Top-right, case picker)
- CaseDetailModal (Forensic Cockpit with Vault Badges)
- CaseSettingsModal
- ConflictResolverModal
- TimelineEventModal
- DocumentPreviewModal
```

### React Query Integration

All API calls use `@tanstack/react-query` for caching and state management:

```typescript
// Example: Fetching directory tree
const { data: treeData, isLoading, error } = useQuery({
  queryKey: ['directory-tree', caseId],
  queryFn: () => archiveApi.getDirectoryTree(caseId),
});
```

**Query Keys:**
- `['events']` - Timeline events
- `['collections']` - Timeline collections
- `['directory-tree', caseId]` - Archive directory tree
- `['documents']` - Archive documents

### API Client (frontend/src/api/)

**archive.ts:**
- `getDirectoryTree(caseId)` - GET /api/archive/directory/
- `getDocumentMetadata(fileUuid)` - GET /api/archive/documents/metadata/{uuid}/
- `uploadDocuments(caseId, formData)` - POST /api/archive/documents/upload/
- `uploadToVault(formData)` - POST /api/archive/documents/upload/ (Smart Ingestion)
- `promoteDocument(docUuid)` - POST /api/archive/documents/{uuid}/promote/
- `demoteDocument(docUuid)` - POST /api/archive/documents/{uuid}/demote/
- `moveFile(sourceUuid, destUuid)` - POST /api/archive/documents/move_file/

**timeline.ts:**
- `getEvents(caseId)` - GET /api/timeline/events/
- `createEvent(eventData)` - POST /api/timeline/events/
- `uploadTimeline(caseId, formData)` - POST /api/timeline/cases/{caseId}/upload-markdown/

---

## 🔌 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/accounts/login/` | Standard login |
| POST | `/accounts/did/login/` | DID login |
| POST | `/accounts/logout/` | Logout (POST required - Fix 405) |

### Core API
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cases/` | List user cases |
| POST | `/api/cases/` | Create new case |
| GET | `/api/cases/{id}/` | Get case details |

### Timeline API
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/timeline/events/` | List timeline events |
| POST | `/api/timeline/events/` | Create timeline event |
| POST | `/api/timeline/cases/{case_id}/upload-markdown/` | Upload 5-column markdown |
| GET | `/api/timeline/api/load-timeline/` | Load timeline file (legacy) |
| GET | `/api/timeline/api/timeline-headings/` | List timeline headings |

### Archive API
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/archive/directory/` | Get recursive directory tree |
| GET | `/api/archive/documents/metadata/{uuid}/` | Get document metadata |
| **POST** | **`/api/archive/documents/upload/`** | **Upload document (FIXED 405)** |
| POST | `/api/archive/documents/{uuid}/promote/` | Promote to Formal Vault |
| POST | `/api/archive/documents/{uuid}/demote/` | Demote to Private Workspace |
| POST | `/api/archive/documents/move_file/` | Move file between folders |

### AI API
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ai/api/analyze-document/` | Analyze document with LLM |
| POST | `/ai/api/query-timeline/` | Query timeline with LLM |
| POST | `/ai/api/suggest-events/` | Suggest events from documents |

---

## 🗄️ Models Reference

### Core Models (apps/core/models.py)

#### Case
```python
class Case(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#FF8C00')
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
```

#### RawDocument (Layer 1)
```python
class RawDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    file = models.FileField(upload_to=raw_document_upload_path)
    file_type = models.CharField(max_length=10, choices=[('pdf','PDF'), ('md','Markdown'), ('json','JSON')])
    source_party = models.CharField(max_length=50, choices=[('CLIENT','Client'), ('OPPOSING','Opposing'), ('NEUTRAL','Neutral')])
    document_type = models.CharField(max_length=100)
    reliability_note = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_immutable = models.BooleanField(default=True)
```

#### WikiPage (Layer 2)
```python
class WikiPage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()  # Markdown content
    last_updated = models.DateTimeField(auto_now=True)
    version_history = models.JSONField(default=list)
    citation_references = models.JSONField(default=list)
    category = models.CharField(max_length=20, choices=[('VERIFIED','Stipulated/Verified'), ('CONTESTED','Contested Allegation')])
```

#### SchemaRule (Layer 3)
```python
class SchemaRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    rule_name = models.CharField(max_length=200)
    rule_description = models.TextField()
    rule_content = models.TextField()  # Markdown or JSON rules for LLM
```

### Timeline Models (apps/timeline/models.py)

#### TimelineEvent
```python
class TimelineEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    date = models.DateField()
    event = models.CharField(max_length=255)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    evidence = models.ManyToManyField(ArchiveDocument)
    notes = models.TextField(blank=True)
    timeline_file = models.ForeignKey(TimelineFile, on_delete=models.SET_NULL, null=True, blank=True)
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Trust Model
    is_system_source = models.BooleanField(default=False)
    source_party = models.CharField(max_length=50, choices=[('CLIENT','Client'), ('OPPOSING','Opposing'), ('NEUTRAL','Neutral'), ('COURT','Court')])
    source_type = models.CharField(max_length=50, choices=[('MANUAL','Manual'), ('SYSTEM','System')])
    trust_level = models.PositiveSmallIntegerField(default=3, choices=[(1,'Low'), (2,'Medium'), (3,'High'), (4,'Very High'), (5,'Maximum')])
    status = models.CharField(max_length=50, choices=[('UNDISPUTED','Undisputed'), ('CONTESTED','Contested'), ('STIPULATED','Stipulated'), ('REFUTED','Refuted')])
    
    # Versioning
    version = models.PositiveIntegerField(default=1)
    replaces_event = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    @property
    def has_gold_seal(self) -> bool:
        return self.is_system_source and self.status == 'STIPULATED'
```

### Archive Models (apps/archive/models.py)

#### ArchiveDocument
```python
class ArchiveDocument(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='archive/documents/')
    path = models.CharField(max_length=512)  # Full path including folder structure
    file_type = models.CharField(max_length=50, choices=[('pdf','PDF'), ('image','Image'), ('word','Word'), ('text','Text'), ('email','Email'), ('other','Other'), ('folder','Folder')])
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    timeline_event = models.ForeignKey(TimelineEvent, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Gate Logic fields
    is_promoted = models.BooleanField(default=False)
    promoted_at = models.DateTimeField(null=True, blank=True)
    is_draft = models.BooleanField(default=False)
    is_immutable = models.BooleanField(default=False)
```

#### Standard Folder Structure
```python
FOLDER_CHOICES = [
    ('01_Raw', 'Original uploaded documents and source materials'),
    ('02_Wiki', 'Processed and cleaned documents for reference'),
    ('03_Drafts', 'Working drafts and editable documents'),
    ('04_Strategy', 'Strategy documents and case planning materials'),
    ('05_Exports', 'Export outputs, reports, and final deliverables'),
]
```

---

## 📦 Portability Protocols

### .hive Bundle Specification

A `.hive` file is a **tar.gz archive** containing a complete case with all relationships preserved via UUID references.

```
hive.tar.gz
├── hive.json              # Manifest (UTF-8 JSON)
├── formal/                # Vault files (shared evidence)
│   └── evidence/          # All promoted documents
│       └── [uuid].[ext]
└── private/               # Workspace files (optional)
    └── [user_uuid]/       # Per-user private data
        ├── drafts/
        ├── wiki/
        └── research/
```

### Key Design Principles

1. **UUID Stability**: All records retain their original UUIDs across export/import
2. **Relative Paths Only**: All file paths are relative to the Hive root
3. **Relationships via UUID**: All foreign keys stored as UUID references
4. **Truth Graph Preservation**: Complete conflict history maintained

### Export/Import Services

```python
# Export
from apps.timeline.services import HiveExportService
service = HiveExportService(case=case, include_private=True, user_uuid=str(user.uuid))
hive_path = service.export()

# Import
from apps.timeline.services import HiveImportService
service = HiveImportService(hive_path=hive_path, target_case=case, user=request.user)
case, errors, warnings = service.import_bundle()
```

---

## 🔒 Security Protocols

### Secure Deletion (ShredderService)

Every file MUST be overwritten with cryptographically secure random data before deletion:

```python
import os

def _secure_wipe_file(file_path: str):
    file_size = os.path.getsize(file_path)
    with open(file_path, 'wb') as f:
        remaining = file_size
        while remaining > 0:
            chunk_size = min(4096, remaining)
            random_data = os.urandom(chunk_size)  # CRITICAL: os.urandom
            f.write(random_data)
            remaining -= chunk_size
        f.flush()
        os.fsync(f.fileno())
    os.unlink(file_path)
```

### M-of-N Shredder Logic (FUTURE)

For multi-owner cases, deletion requires M-of-N authorization:
- Once a Hive has two verified opposing owners, shredder undergoes state change
- Deletion of shared `/formal/` vault requires both parties to sign off
- Prevents one side from "burning the evidence" to spite the other

### Data Compartmentalization

**Strict multi-tenant isolation at every layer:**

1. **Model-Level**: All models enforce user ownership via ForeignKey
2. **Query-Level**: ALL queries MUST filter by `request.user`
3. **Permission Methods**: Models include `can_access()`, `can_edit()`, `can_delete()`
4. **View-Level**: All views enforce user isolation
5. **API-Level**: All JSON endpoints filter by user

---

## 🚀 Completion Status

### ✅ COMPLETED
- React + Vite + Tailwind frontend migration
- Django REST API backend
- 3-panel Anchor Layout with Elasticity
- Strict White Theme enforcement
- 5-column Markdown parsing
- Shared Magnet (Gate Logic)
- Smart Ingestion (Formal/Private routing)
- Trust Level system with Gold Seal
- .hive portability protocol
- Secure deletion with cryptographic wipe

### 🚧 IN PROGRESS
- M-of-N Shredder Logic for multi-owner cases
- Identity Verification Service (DID integration)
- Public/Private Toggle for third-party access
- Whistleblower staging area
- Polling app integration
- Court-Linked API for automatic stipulated facts

### 📋 ROADMAP
See `ROADMAP_2026.md` for detailed 2026 goals.

---

## 📞 Support

- **Primary Docs**: DEVELOPER_GUIDE.md, PROJECT_STATE.md, ROADMAP_2026.md
- **Django**: https://docs.djangoproject.com/
- **React**: https://react.dev/
- **Vite**: https://vitejs.dev/
- **Tailwind**: https://tailwindcss.com/
- **TanStack Query**: https://tanstack.com/query
- **uv Package Manager**: https://docs.astral.sh/uv/

---

**Build Hashes (Current):**
- Frontend JS: `index-BfomkJw1.js`
- Frontend CSS: `index-JNzbSqsV.css`
- Vite Manifest: `static/frontend/.vite/manifest.json`

**Last Updated**: 2026-05-08
**Version**: 2.0 (React Migration Complete)
