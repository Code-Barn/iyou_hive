# Hive Developer Guide

**Architectural Source of Truth - React + Vite + Tailwind + Django REST API (GPLv3)**

*Last Updated: 2026-05-30* | *Build: `index-CNqL40E6.js` / `index-Cyu1mE_y.css`*

---

## Table of Contents

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
11. [Licensing & Attribution](#-licensing--attribution)

---

## Architecture Overview

Hive implements a **React + Vite + Tailwind frontend** with a **Django REST API backend**, following a strict **3-Layer Wiki Architecture** for document processing.

### High-Level Architecture

```
 PRESENTATION LAYER
 React 18 + Vite 5 + Tailwind CSS 3 + TypeScript
 ---------------------------------------------------------------
 frontend/
   src/
     App.tsx              - Root component with Layout
     main.tsx             - Entry point (QueryClientProvider wrapper)
     components/          - All UI components
       Layout.tsx         - 3-panel dashboard (LEFT/CENTER/RIGHT)
       ForensicTimeline.tsx - Main timeline view
       FileTree.tsx       - Archive directory tree
       AIAssistantChat.tsx - AI chat interface
       CaseDetailModal.tsx - Case cockpit / forensic vault
       CaseSelector.tsx   - Case switching dropdown
       CanvasEditor.tsx   - Document canvas area
       DiffView.tsx       - Side-by-side timeline comparison
       SimplifiedView.tsx - Reduced-density timeline view
       SovereignHeader.tsx - App branding header
       ConflictResolverModal.tsx - Competing timeline resolution
       EventCard.tsx      - Individual event card with trust badges
       TimelineToolbar.tsx - Event creation, markdown upload
       FileActions.tsx    - Upload to workspace actions
       DocumentPreviewModal.tsx - Document preview with metadata
       TimelineEventModal.tsx - Event creation/edit modal
       InspectorPanel.tsx - AI inspector panel
       CaseSettingsModal.tsx - Case configuration modal
       CaseInitializationModal.tsx - First-run case creation
       index.ts           - Barrel exports
     api/                 - Axios API client modules
       archive.ts         - Archive document endpoints
       timeline.ts        - Timeline event endpoints
       ai.ts              - AI assistant endpoints
     types/               - TypeScript type definitions
       timeline.ts        - TimelineEvent, SourceParty, Status types
       shared.ts          - Shared type definitions
       global.d.ts        - React ambient type extensions
     views/               - Full-page views
       ArchivePane.tsx    - Archive browser view
     index.css            - Tailwind entry + global styles
   static/frontend/
     assets/
       index-CNqL40E6.js  Current Build
       index-Cyu1mE_y.css Current Build
     .vite/manifest.json
     index.html
                             REST API
 ---------------------------------------------------------------
 API LAYER (Django REST Framework)
 Django 5.2 + DRF + SimpleJWT + CORS
 ---------------------------------------------------------------
 config/
   urls.py                - Root URL routing
   settings.py            - Django configuration
   asgi.py / wsgi.py      - ASGI/WSGI entry points
   celery.py              - Celery async task config

 apps/
   accounts/              - DID + standard authentication
     urls.py              - login, logout, register, did/login
     backends.py          - Custom auth backends (DID)
     views.py             - Auth views

   core/                  - Case, 3-Layer Wiki, portability models
     models.py            - Case, TimelineFile, RawDocument, WikiPage,
                            SchemaRule, EvidenceSignature, ResponseSheet
     views.py             - react_app_view (SPA root), case API views
     urls.py              - Core URL routing
     services/
       hive_directory.py  - HiveDirectoryService (Gate Logic)
       shredder.py        - ShredderService (secure deletion)
     document_processing.py - PDF/markdown processing pipeline
     llm_clients.py       - LLM client abstraction
     parsers.py           - Markdown/JSON parsers
     prompts.py           - Schema rules for LLM formatting
     tasks.py             - Celery async tasks
     context_processors.py - Django template context
     middleware.py         - Custom middleware
     templatetags/        - Django template tags
       assets.py          - Asset loading tags
       timeline_tags.py   - Timeline rendering tags
     migrations/          - 7 migration files

   timeline/              - Timeline events, competing timelines
     models.py            - TimelineEvent, TimelineCollection,
                            PhotoEventLink
     api_views.py         - DRF ViewSets + action endpoints
     api_urls.py          - API router URL config
     views.py             - Template-based timeline views
     urls.py              - Legacy URL routing
     utils.py             - Markdown parsing and export logic
     serializers.py       - DRF serializers
     services/
       hive_export.py     - HiveExportService (.hive bundle export)
       hive_import.py     - HiveImportService (.hive bundle import)
       conflict_resolver.py - Competing timeline resolution
     migrations/          - 12 migration files

   archive/               - Document storage & management
     models.py            - ArchiveDocument, Photo, CloudImport,
                            CustodyLog, SyncedArchive
     api_views.py         - DRF ViewSets + action endpoints
     api_urls.py          - API URL routing
     views.py             - Template-based archive views
     urls.py              - Legacy archive URLs
     forms.py             - Upload forms
     tasks.py             - Async document processing tasks
     utils.py             - Archive utilities
     vector_service.py    - LanceDB vector search service
     serializers.py       - DRF serializers
     migrations/          - 10 migration files

   ai_assistant/          - AI integration
     models.py            - AIConversation, UserSettings
     views.py             - AI chat, analyze, query views
     urls.py              - AI API URL routing
     services.py          - Business logic for AI operations
     api_client.py        - External AI API clients
     migrations/          - 3 migration files

   conversation_logs/     - AI conversation audit logging
     models.py            - ConversationLog, ConversationAnalytics
     views.py             - Conversation log views
     urls.py              - Conversation log API routing
     utils.py             - Logging utilities
     migrations/          - 1 migration file
                             
---------------------------------------------------------------
 DATA LAYER
 SQLite (Default) / PostgreSQL (Production)
 ---------------------------------------------------------------
 Hive Directory Structure:
 media/hives/[case_uuid]/
   formal/                    - Vault (Shared Evidence)
     evidence/                - Promoted documents
     timeline/                - Markdown timeline exports
     hive.json                - Export manifest
   private/                   - Workspace (User-Isolated)
     [user_uuid]/
       drafts/                - Unpromoted documents
       wiki/                  - LLM Wiki pages
       research/              - AI analysis outputs
       temp/                  - Upload staging
```

### Request Flow

1. **Frontend Request** React component calls API via `axios` (CSRF token attached via interceptor)
2. **Django URL Dispatcher** Routes to appropriate API view via `config/urls.py`
3. **API View** Processes request, queries models via ORM, enforces user isolation
4. **JSON Response** Returns structured data to frontend
5. **React State Update** Updates UI via `@tanstack/react-query` (cache invalidation via `invalidateQueries`)

### Data Compartmentalization

All models enforce strict multi-tenant isolation:
- **Model-Level**: All data models reference `user` or `case` via ForeignKey
- **Query-Level**: All queries filter by `request.user`
- **View-Level**: Permission methods (`can_access`, `can_edit`, `can_delete`) enforced
- **API-Level**: All JSON endpoints filter by authenticated user

---

## Sovereign UI Rules

### Anchor Layout (IMMUTABLE)

**Panel Order: Left  Center  Right**

```
 LEFT PANEL: Timeline
   ForensicTimeline
     - Event cards with trust level badges
     - Gold Seal indicator for COURT/NEUTRAL sources
     - Source party coloring (CLIENT/OPPOSING/NEUTRAL/COURT)
     - Significance filtering (is_trivial toggle)

                       DRAGGABLE DIVIDER

 CENTER PANEL: Archive & Canvas (ELASTIC ANCHOR)
   FileTree (Top ~40% height)
     - Vault (Shared) and Workspace (Private) folders
     - 01_Raw, 02_Wiki, 03_Drafts, 04_Strategy, 05_Exports
   Horizontal Divider (Draggable)
   Canvas / DocumentPreview (Bottom ~60% height)
     - Document preview with metadata
     - CanvasEditor for document analysis
   VERTICAL SPLIT: Proportional expansion on collapse

                       DRAGGABLE DIVIDER

 RIGHT PANEL: AI Assistant
   AIAssistantChat
     - Conversation history
     - Document analysis
     - Timeline queries
   InspectorPanel
     - AI inspection results
     - Perspective mode (Client/Opposing/Neutral/Court)
```

### Aesthetic: STRICT WHITE THEME

- **Background**: `bg-white`
- **Text**: `text-gray-900` (primary), `text-gray-600` (secondary)
- **Borders**: `border-gray-200`
- **Hover States**: `hover:bg-blue-50` or `hover:bg-gray-100`
- **Primary Accent**: `bg-primary` (honey-orange `#FF8C00`)
- **Shadows**: `shadow-sm` on headers

**Theme Enforcement**: No dark mode. White background with gray text for maximum legal document readability.

### Elasticity Rules

1. **Proportional Expansion on Collapse**: Center panel expands proportionally when a side panel collapses
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
  - `panel-sizes-{caseId}`: JSON of `{left, center, right}` percentages
  - `panel-horizontal-{caseId}`: Horizontal split ratio (0.01.0)

---

## Data Standards

### Shared Magnet Logic (Gate Logic)

The **Shared Magnet** ensures all case participants see the same Formal Vault evidence while maintaining isolated Private Workspaces.

**Magnetic Attraction Rules:**
1. **Formal Vault** (`/formal/evidence/`): Shared across ALL users in a case
2. **Private Workspace** (`/private/[user_uuid]/`): User-isolated, never visible to others
3. **Promotion** (Magnet Activation): `HiveDirectoryService.promote_to_evidence(document, case, user)`
4. **Demotion** (Magnet Release): `HiveDirectoryService.demote_from_evidence(document, user)`

```python
# apps/core/services/hive_directory.py
HiveDirectoryService.promote_to_evidence(document, case, user)
HiveDirectoryService.demote_from_evidence(document, user)
HiveDirectoryService.move_document(document, destination_folder_document, user)
```

### 5-Column Markdown Requirement

All timeline markdown files MUST follow the **5-column format**:

```markdown
| Date | Event | Description | Category | Documents |
|------|-------|-------------|----------|-----------|
| 2024-01-15 | Contract Signed | Initial agreement executed | contract | contract.pdf |
```

**Column Definitions:**
| Column | Type | Required | Purpose |
|--------|------|----------|---------|
| Date | `YYYY-MM-DD` | Yes | Event date |
| Event | String | Yes | Event title |
| Description | String | Yes | Event details |
| Category | String | Yes | Event category (lowercase) |
| Documents | CSV | Yes | Comma-separated document names |

**Categories Supported:**
`contract`, `email`, `court_filing`, `communication`, `meeting`,
`deadline`, `personal`, `legal`, `medical`, `financial`,
`education`, `verified`, `contested`, `other`

### Trust Level Scale

| Level | Value | Description | Badge |
|-------|-------|-------------|-------|
| 1 | Low - Unverified | User claim without evidence | None |
| 2 | Medium - User Verified | User claim with evidence | Blue |
| 3 | High - Documented | Documented claim (default) | Green |
| 4 | Very High - Official Record | Official documents | Purple |
| 5 | Maximum - Court Stipulated | COURT/NEUTRAL sources | Gold Seal |

**Gold Seal Properties:**
- `is_system_source = True`
- `status = STIPULATED`
- `source_party {COURT, NEUTRAL}`
- Visual: Gold badge with yellow background

---

## Tech Stack

### Frontend
| Technology | Version (range) | Purpose |
|------------|-----------------|---------|
| React | ^18.2.0 | UI Framework |
| Vite | ^5.0.0 | Build Tool & Dev Server |
| Tailwind CSS | ^3.3.6 | Utility-First CSS |
| TypeScript | ^5.3.0 | Type Safety |
| @tanstack/react-query | ^5.0.0 | Server State Management |
| axios | ^1.6.0 | HTTP Client |
| react-router-dom | ^6.20.0 | Client-Side Routing |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | ^3.10 | Runtime |
| Django | >=5.2.13 | Web Framework |
| Django REST Framework | latest | API Layer |
| Celery | latest | Async Task Queue |
| Redis | latest | Message Broker / Cache |
| SQLite | built-in | Default Database |
| PostgreSQL | 15+ | Production Database |
| uv | latest | Python Package Manager |

### Key Python Dependencies (pyproject.toml)
| Package | Version | Purpose |
|---------|---------|---------|
| djangorestframework | any | REST API layer |
| django-cors-headers | any | CORS support |
| mozilla-django-oidc | >=5.0.2 | OIDC / DID authentication |
| lancedb | >=0.25,<0.26 | Vector database for semantic search |
| sentence-transformers | >=2.7,<3 | Text embeddings |
| torch | >=2.2.0,<2.3.0 | PyTorch for ML inference |
| pymupdf | >=1.23.5 | PDF processing |
| pdfplumber | >=0.11.9 | PDF data extraction |
| pytesseract | >=0.3.13 | OCR |
| beautifulsoup4 | >=4.14.3 | HTML parsing |
| markitdown | >=0.1.5 | Markdown conversion |
| google-genai | >=1.74.0 | Google Gemini AI SDK |
| celery | any | Async task processing |
| redis | any | Cache / broker |
| python-dotenv | >=1.2.2 | Environment management |
| requests | >=2.33.1 | HTTP client |

### External Systems
| System | Integration | Purpose |
|--------|-------------|---------|
| Mistral AI | REST API | Cloud LLM (preferred provider) |
| Google Gemini | google-genai SDK | Cloud LLM (fallback provider) |
| Ollama | REST API (optional) | Local LLM Inference |
| Rust-DID | FFI via ctypes | Decentralized Identity |

---

## Backend Architecture

### 3-Layer Wiki Architecture

```
 Layer 1: RawDocument (IMMUTABLE)
   Original uploaded documents (PDF, Markdown, JSON)
   Immutable once created (is_immutable=True)
   Source party tracking (CLIENT/OPPOSING/NEUTRAL)
   Stored in: media/raw/<case_id>/
   Model: apps/core/models.py:RawDocument

                             Sync Pipeline (apps/core/tasks.py)

 Layer 2: WikiPage (PROCESSED)
   Normalized content derived from RawDocuments
   Version history maintained automatically
   Citation references track claims to sources
   Category: VERIFIED vs CONTESTED
   Unique per case+title combination
   Model: apps/core/models.py:WikiPage

                             Schema Rules (apps/core/prompts.py)

 Layer 3: SchemaRule (LLM FORMATTING)
   Defines how LLM should format/structure content
   Applied during document sync and query processing
   Unique per case+rule_name combination
   Model: apps/core/models.py:SchemaRule
```

### Directory Service

`HiveDirectoryService` (apps/core/services/hive_directory.py) manages all file operations:

```python
# Create standard folder structure for new cases
ArchiveDocument.create_standard_folder_structure(case, user)
# Creates: 01_Raw, 02_Wiki, 03_Drafts, 04_Strategy, 05_Exports

# Gate Logic
HiveDirectoryService.promote_to_evidence(document, case, user)
HiveDirectoryService.demote_from_evidence(document, user)

# File Operations
HiveDirectoryService.move_document(document, destination_folder, user)

# Path Queries
get_hive_root(), get_case_root(case_uuid)
get_formal_evidence_path(case_uuid), get_private_drafts_path(case_uuid, user_uuid)
ensure_hive_structure(case_uuid, user_uuid)
```

---

## Frontend Architecture

### Component Hierarchy

```
main.tsx
 QueryClientProvider (TanStack React Query)
   App.tsx
     Router (react-router-dom)
       CaseSelector (top-right, case switching)
       Layout.tsx (3-Panel Dashboard)
         LEFT: Timeline Panel
           Panel Header (Timeline + Full Screen + Collapse)
           ForensicTimeline.tsx
             EventCard.tsx (trust badges, gold seal)
           TimelineToolbar.tsx (Add Event, Upload Markdown)
           SimplifiedView.tsx (reduced-density alternative)

         CENTER: Archive & Canvas Panel (ELASTIC ANCHOR)
           Panel Header (Archive + Ingest + Full Screen + Collapse)
           FileTree.tsx (Top ~40%)
             FileActions.tsx (Upload to Workspace / Vault)
           Horizontal Divider (Draggable)
           Canvas Area (Bottom ~60%)
             CanvasEditor.tsx
             DocumentPreviewModal.tsx (overlay)

         RIGHT: AI Assistant Panel
           Panel Header (AI + Settings + Full Screen + Collapse)
           AIAssistantChat.tsx
           InspectorPanel.tsx (analysis results)

# Modals (overlaid on Layout)
- CaseSelector (top-right dropdown)
- CaseInitializationModal (first-run guided setup)
- CaseDetailModal (Forensic Cockpit with Vault badges)
- CaseSettingsModal
- TimelineEventModal (create/edit events)
- DocumentPreviewModal (document viewer)
- ConflictResolverModal (competing timeline resolution)
- DiffView (side-by-side comparison)
- SovereignHeader (branding header)

# Views (full page)
- ArchivePane.tsx (standalone archive browser)
```

### React Query Integration

All API calls use `@tanstack/react-query` v5 for caching and state management:

```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ['directory-tree', caseId],
  queryFn: () => archiveApi.getDirectoryTree(caseId),
});
```

**Query Keys:**
- `['events', caseId]` Timeline events
- `['event', caseId, eventId]` Single event
- `['collections', caseId]` Timeline collections
- `['directory-tree', caseId]` Archive directory tree
- `['documents']` Archive documents
- `['document-metadata', uuid]` Document details

### API Client Modules

All clients are in `frontend/src/api/` and use a shared pattern:
- Axios instance with base URL, credentials, and CSRF interceptor
- CSRF token read from `hiver_csrftoken` cookie
- All requests automatically attach `X-CSRFToken` header

**archive.ts:**
```typescript
archiveApi.createCase(name, description, clientLegalName?, opposingLegalName?)
archiveApi.getDirectoryTree(caseId?)
archiveApi.getDocumentMetadata(fileUuid)
archiveApi.getDocumentContent(fileUuid)
archiveApi.moveFile(sourceFileUuid, destinationFolderUuid)
archiveApi.promoteDocument(docUuid)
archiveApi.demoteDocument(docUuid)
archiveApi.uploadDocuments(caseId, formData)
archiveApi.uploadToVault(caseId, formData)  // Smart Ingestion
```

**timeline.ts:**
```typescript
// Events CRUD
timelineApi.getEvents(caseId, filters?)
timelineApi.getEvent(caseId, eventId)
timelineApi.createEvent(caseId, data)
timelineApi.updateEvent(caseId, eventId, data)
timelineApi.deleteEvent(caseId, eventId)

// Actions
timelineApi.contestEvent(caseId, eventId, data)
timelineApi.resolveConflict(caseId, eventId, data)
timelineApi.uploadTimeline(caseId, formData)
timelineApi.materializeEvent(caseId, payload)
timelineApi.generatePdf(caseId)
timelineApi.exportHive(caseId, includePrivate)
timelineApi.importHive(caseId, formData)

// Collections
collectionApi.getCollections(caseId)
collectionApi.getCollection(caseId, collectionId)
collectionApi.createCollection(caseId, data)
collectionApi.deleteCollection(caseId, collectionId)
collectionApi.addEventToCollection(caseId, collectionId, eventId)
collectionApi.removeEventFromCollection(caseId, collectionId, eventId)

// Diff View
diffApi.getDiffView(caseId, leftParty?, rightParty?)
```

**ai.ts:**
```typescript
aiApi.saveApiKey(settings)
aiApi.queryTimeline(query, caseId?, documentContent?, perspectiveMode?)
aiApi.analyzeDocument(documentId, text?)
aiApi.suggestEvents(caseId?)
aiApi.analyzeTimelineEvent(eventId)
```

---

## API Endpoints

All endpoints are served under the base URL at `config/urls.py`.

### Authentication (`/accounts/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/accounts/login/` | Standard login |
| POST | `/accounts/did/login/` | DID authentication login |
| POST | `/accounts/did/logout/` | DID logout |
| POST | `/accounts/logout/` | Logout |
| POST | `/accounts/challenge/` | DID challenge generation |
| POST | `/accounts/register/` | User registration |

### OIDC (`/oidc/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| ANY | `/oidc/*` | mozilla-django-oidc routes |

### Core API (`/core/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/core/api/cases/` | List / Create cases |
| GET | `/core/api/cases/{id}/` | Case detail |

### Timeline API (`/api/timeline/`)
**Base:** `config/urls.py` mounts `apps.timeline.api_urls` at `/api/timeline/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/timeline/cases/{case_id}/events/` | List events (with filters) |
| POST | `/api/timeline/cases/{case_id}/events/` | Create event |
| GET | `/api/timeline/cases/{case_id}/events/{id}/` | Get single event |
| PATCH | `/api/timeline/cases/{case_id}/events/{id}/` | Update event |
| DELETE | `/api/timeline/cases/{case_id}/events/{id}/` | Delete event |
| POST | `/api/timeline/cases/{case_id}/events/{id}/contest/` | Contest event |
| POST | `/api/timeline/cases/{case_id}/events/{id}/resolve/` | Resolve conflict |
| POST | `/api/timeline/cases/{case_id}/upload-markdown/` | Upload 5-column markdown |
| GET | `/api/timeline/cases/{case_id}/diff/` | Get diff view |
| POST | `/api/timeline/cases/{case_id}/materialize/` | AI event materialization |

**Collections:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/timeline/cases/{case_id}/collections/` | List collections |
| POST | `/api/timeline/cases/{case_id}/collections/` | Create collection |
| GET | `/api/timeline/cases/{case_id}/collections/{id}/` | Get collection |
| DELETE | `/api/timeline/cases/{case_id}/collections/{id}/` | Delete collection |
| POST | `/api/timeline/cases/{case_id}/collections/{id}/add-event/` | Add event |
| POST | `/api/timeline/cases/{case_id}/collections/{id}/remove-event/` | Remove event |

**Hive Portability:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/timeline/cases/{case_id}/export-hive/` | Export .hive bundle |
| POST | `/api/timeline/cases/{case_id}/import-hive/` | Import .hive bundle |

**Legacy (apps/timeline/urls.py mounted at /timeline/api/):**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/timeline/api/api/load-timeline/` | Load timeline file |
| GET | `/timeline/api/api/timeline-headings/` | List timeline headings |

### Archive API (`/api/archive/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/archive/directory/` | Recursive directory tree |
| GET | `/api/archive/documents/metadata/{uuid}/` | Document metadata |
| GET | `/api/archive/documents/content/{uuid}/` | Document raw content |
| POST | `/api/archive/documents/upload/` | Upload document |
| POST | `/api/archive/documents/{uuid}/promote/` | Promote to Formal Vault |
| POST | `/api/archive/documents/{uuid}/demote/` | Demote to Private Workspace |
| POST | `/api/archive/documents/move_file/` | Move between folders |

### AI API (`/ai/api/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ai/api/analyze/` | Analyze document with LLM |
| POST | `/ai/api/query-timeline/` | Query timeline with LLM |
| POST | `/ai/api/suggest-events/` | Suggest events from documents |
| POST | `/ai/api/analyze-event/{event_id}/` | Analyze specific timeline event |
| POST | `/ai/api/save-api-key/` | Save AI provider API keys |

---

## Models Reference

### Core Models (apps/core/models.py)

#### Case
```python
class Case(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    client_legal_name = models.CharField(max_length=255, blank=True)
    opposing_legal_name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#FF8C00')
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cases')
    # Meta: unique_together = ['name', 'user']
    # Properties: uuid (alias), event_count, document_count
```

#### TimelineFile
```python
class TimelineFile(models.Model):
    name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=512)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
```

#### RawDocument (Layer 1)
```python
class RawDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    file = models.FileField(upload_to=raw_document_upload_path)
    file_type = models.CharField(max_length=10, choices=[('pdf','PDF'), ('md','Markdown'), ('json','JSON')])
    source_party = models.CharField(max_length=50, choices=[('CLIENT','Client'), ('OPPOSING','Opposing'), ('NEUTRAL','Neutral')])
    document_type = models.CharField(max_length=100)
    reliability_note = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_immutable = models.BooleanField(default=True)
    synced_at = models.DateTimeField(null=True, blank=True)
```

#### WikiPage (Layer 2)
```python
class WikiPage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='wiki_pages')
    title = models.CharField(max_length=200)
    content = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)
    version_history = models.JSONField(default=list)
    citation_references = models.JSONField(default=list)
    category = models.CharField(max_length=20, choices=[('VERIFIED','Stipulated/Verified'), ('CONTESTED','Contested Allegation')], default='CONTESTED')
    # Meta: unique_together = ['case', 'title']
```

#### SchemaRule (Layer 3)
```python
class SchemaRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='schema_rules')
    rule_name = models.CharField(max_length=200)
    rule_description = models.TextField()
    rule_content = models.TextField()
    # Meta: unique_together = ['case', 'rule_name']
```

#### EvidenceSignature
```python
class EvidenceSignature(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(RawDocument, on_delete=models.CASCADE, related_name='signatures')
    signer_did = models.CharField(max_length=512)
    signature = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
```

#### ResponseSheet
```python
class ResponseSheet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    source_pdf = models.CharField(max_length=512, blank=True)
    case_number = models.CharField(max_length=100, blank=True)
    state_code = models.CharField(max_length=5, default='IL')
    data = models.JSONField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Timeline Models (apps/timeline/models.py)

#### TimelineEvent
```python
class TimelineEvent(models.Model):
    SOURCE_TYPE_CHOICES = [
        ('MANUAL', 'Manual Entry'),
        ('MARKDOWN', 'Markdown Import'),
        ('AI_GENERATED', 'AI Generated'),
    ]
    STATUS_CHOICES = [
        ('UNDISPUTED', 'Undisputed'),
        ('CONTESTED', 'Contested'),
        ('REFUTED', 'Refuted'),
        ('STIPULATED', 'Stipulated'),
        ('PENDING', 'Pending Review'),
    ]
    SOURCE_PARTY_CHOICES = [
        ('CLIENT', 'Client/Plaintiff'),
        ('OPPOSING', 'Opposing Party/Defendant'),
        ('NEUTRAL', 'Neutral Third Party'),
        ('COURT', 'Court'),
        ('WITNESS', 'Witness'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(db_index=True)
    event = models.CharField(max_length=255)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='other')
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default='MANUAL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNDISPUTED')
    source_party = models.CharField(max_length=20, choices=SOURCE_PARTY_CHOICES)
    section_header = models.CharField(max_length=500, blank=True, null=True)
    is_system_source = models.BooleanField(default=False)
    trust_level = models.PositiveSmallIntegerField(default=3, choices=[(1,'Low')...(5,'Maximum')])
    is_trivial = models.BooleanField(default=False)
    significance = models.PositiveSmallIntegerField(default=3, choices=[(1,'Minimal')...(5,'Critical')])
    citation = models.CharField(max_length=500, blank=True)
    last_printed_citation = models.JSONField(null=True, blank=True)
    notes = models.TextField(blank=True)
    evidence = models.ManyToManyField(ArchiveDocument, blank=True)
    replaces_event = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    timeline_file = models.ForeignKey(TimelineFile, on_delete=models.SET_NULL, null=True, blank=True)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='events')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    # Meta: unique_together = ['case', 'date', 'event', 'source_party']

    @property
    def has_gold_seal(self) -> bool:
        return self.is_system_source and self.status == 'STIPULATED'
```

#### TimelineCollection
```python
class TimelineCollection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    events = models.ManyToManyField(TimelineEvent, blank=True)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='collections')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=False)
    # Meta: unique_together = ['name', 'case']
```

#### PhotoEventLink
```python
class PhotoEventLink(models.Model):
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name='event_links')
    event = models.ForeignKey(TimelineEvent, on_delete=models.CASCADE, related_name='photo_links')
    confidence = models.FloatField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Archive Models (apps/archive/models.py)

#### ArchiveDocument
```python
class ArchiveDocument(models.Model):
    DOCUMENT_TYPES = [
        ('pdf', 'PDF'), ('image', 'Image'), ('text', 'Text'),
        ('word', 'Word Document'), ('email', 'Email'), ('folder', 'Folder'), ('other', 'Other'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='archive/documents/')
    file_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='pdf')
    path = models.CharField(max_length=512, blank=True)
    is_draft = models.BooleanField(default=False)
    is_immutable = models.BooleanField(default=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    promoted_at = models.DateTimeField(null=True, blank=True)
    is_promoted = models.BooleanField(default=False)
    category = models.CharField(max_length=100, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    conversion_status = models.CharField(max_length=20, default='PENDING')
    markdown_path = models.CharField(max_length=512, blank=True)
    conversion_error = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)
    text_extraction_status = models.CharField(max_length=20, default='PENDING')
    case = models.ForeignKey(Case, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    timeline_event = models.ForeignKey(TimelineEvent, on_delete=models.SET_NULL, null=True, blank=True)
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    @staticmethod
    def create_standard_folder_structure(case, user):
        # Creates: 01_Raw, 02_Wiki, 03_Drafts, 04_Strategy, 05_Exports
```

#### Photo
```python
class Photo(models.Model):
    file = models.ImageField(upload_to='archive/photos/')
    timestamp = models.DateTimeField(null=True, blank=True)
    gps_latitude = models.FloatField(null=True, blank=True)
    gps_longitude = models.FloatField(null=True, blank=True)
    device = models.CharField(max_length=255, blank=True)
    sha256_hash = models.CharField(max_length=64, blank=True)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, null=True, blank=True)
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
```

#### CloudImport
```python
class CloudImport(models.Model):
    CLOUD_PROVIDERS = [('dropbox', 'Dropbox'), ('google_drive', 'Google Drive'), ('onedrive', 'OneDrive')]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, null=True, blank=True)
    provider = models.CharField(max_length=50, choices=CLOUD_PROVIDERS)
    access_token = models.CharField(max_length=512, blank=True)
    refresh_token = models.CharField(max_length=512, blank=True)
    token_expires = models.DateTimeField(null=True, blank=True)
    folder_path = models.CharField(max_length=512, blank=True)
    last_imported = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### CustodyLog
```python
class CustodyLog(models.Model):
    ACTION_TYPES = [('UPLOAD','Upload'), ('VIEW','View'), ('EDIT','Edit'),
                    ('DELETE','Delete'), ('EXPORT','Export'), ('ANALYZE','Analyze'),
                    ('LINK','Link to Event'), ('UNLINK','Unlink from Event')]
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name='custody_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    details = models.JSONField(default=dict, blank=True)
```

#### SyncedArchive
```python
class SyncedArchive(models.Model):
    PROVIDERS = [('github', 'GitHub'), ('google_drive', 'Google Drive'), ('local', 'Local Folder')]
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='sync_configs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sync_configs')
    provider = models.CharField(max_length=50, choices=PROVIDERS)
    external_path = models.CharField(max_length=512)
    access_token = models.CharField(max_length=512, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Methods: sync() -> pulls files from external storage
```

### AI Assistant Models (apps/ai_assistant/models.py)

#### AIConversation
```python
class AIConversation(models.Model):
    title = models.CharField(max_length=255, default="New Conversation")
    case = models.ForeignKey(Case, on_delete=models.CASCADE, null=True, blank=True)
    messages = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
```

#### UserSettings
```python
class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    mistral_api_key = models.CharField(max_length=255, blank=True, null=True)
    gemini_api_key = models.CharField(max_length=255, blank=True, null=True)
    preferred_ai_provider = models.CharField(max_length=20, choices=[('mistral','Mistral AI'), ('gemini','Google Gemini')], default='mistral')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Conversation Log Models (apps/conversation_logs/models.py)

#### ConversationLog
```python
class ConversationLog(models.Model):
    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name='logs')
    message = models.TextField()
    sender = models.CharField(max_length=20, choices=[('user','User'), ('ai','AI Assistant'), ('system','System')])
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    # Meta: indexed on conversation, timestamp, sender
```

#### ConversationAnalytics
```python
class ConversationAnalytics(models.Model):
    conversation = models.OneToOneField(AIConversation, on_delete=models.CASCADE, related_name='analytics')
    message_count = models.IntegerField(default=0)
    user_message_count = models.IntegerField(default=0)
    ai_message_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    total_characters = models.IntegerField(default=0)
    user_characters = models.IntegerField(default=0)
    ai_characters = models.IntegerField(default=0)
    user_rating = models.FloatField(null=True, blank=True)
    user_feedback = models.TextField(blank=True)
```

---

## Portability Protocols

### .hive Bundle Specification

A `.hive` file is a **tar.gz archive** containing a complete case with all relationships preserved via UUID references:

```
hive.tar.gz
  hive.json              # Manifest (UTF-8 JSON)
  formal/                # Vault files (shared evidence)
    evidence/            # All promoted documents
      [uuid].[ext]
    timeline/            # Markdown timeline exports
  private/               # Workspace files (optional)
    [user_uuid]/         # Per-user private data
      drafts/
      wiki/
      research/
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

## Security Protocols

### Secure Deletion (ShredderService)

Every file MUST be overwritten with cryptographically secure random data before deletion:

```python
# apps/core/services/shredder.py
def _secure_wipe_file(file_path: str):
    file_size = os.path.getsize(file_path)
    with open(file_path, 'wb') as f:
        remaining = file_size
        while remaining > 0:
            chunk_size = min(4096, remaining)
            random_data = os.urandom(chunk_size)
            f.write(random_data)
            remaining -= chunk_size
        f.flush()
        os.fsync(f.fileno())
    os.unlink(file_path)
```

### M-of-N Shredder Logic (FUTURE)

For multi-owner cases, deletion requires M-of-N authorization. Once a Hive has two verified opposing owners, the shredder requires both parties to sign off, preventing one side from "burning the evidence."

### Evidence Signing (DID)

The `EvidenceSignature` model anchors cryptographic proof to evidence documents via the Desktop Vault (Tauri bridge on :9001). Supports multi-sig (multiple DIDs signing a single RawDocument for joint agreements).

---

## Licensing & Attribution

This project is **Free Software** licensed under the **GNU General Public License v3.0**.

```
Copyright (C) 2026 Byers Brands, LLC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
```

See the `LICENSE` file in the project root for the full license text.

### Completion Status

**COMPLETED**
- React + Vite + Tailwind frontend migration (SPA)
- Django REST API backend with DRF ViewSets
- 3-panel Anchor Layout with Elasticity
- Strict White Theme enforcement
- 5-column Markdown parsing pipeline
- Shared Magnet (Gate Logic) with promote/demote
- Smart Ingestion (Formal/Private automatic routing)
- Trust Level system (1-5) with Gold Seal
- Competing Timelines with contest/resolve workflows
- Timeline Collections (user-curated event subsets)
- .hive portability protocol (export/import)
- Secure deletion with cryptographic wipe
- DID Authentication (challenge/response signing)
- OIDC integration (mozilla-django-oidc)
- Evidence signing with multi-sig support
- Photo forensic metadata (EXIF, GPS, SHA-256)
- Cloud storage import tracking (Dropbox/Google Drive/OneDrive)
- AI conversation logging and analytics
- LanceDB vector search for semantic document retrieval
- GPLv3 license branding on all source files

**IN PROGRESS**
- M-of-N Shredder Logic for multi-owner cases
- Public/Private Toggle for third-party access
- Whistleblower staging area
- Polling app integration
- Court-Linked API for automatic stipulated facts

---

**Build Hashes (Current):**
- Frontend JS: `index-CNqL40E6.js`
- Frontend CSS: `index-Cyu1mE_y.css`
- Vite Manifest: `static/frontend/.vite/manifest.json`

**Last Updated**: 2026-05-30
**License**: GNU GPL v3.0
