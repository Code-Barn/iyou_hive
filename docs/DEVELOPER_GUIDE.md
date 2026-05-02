# Hiver Developer Guide

This guide covers the architecture, APIs, and customization options for Hiver developers.

## 📖 Table of Contents

1. [Architecture Overview](#-architecture-overview)
2. [Models Reference](#-models-reference)
3. [API Endpoints](#-api-endpoints)
4. [Markdown Parsing Logic](#-markdown-parsing-logic)
5. [Authentication System](#-authentication-system)
6. [Case Compartmentalization](#-case-compartmentalization)
7. [Extending Hiver](#-extending-hiver)
8. [Customization Guide](#-customization-guide)
9. [Performance Considerations](#-performance-considerations)
10. [Security Guide](#-security-guide)

---

## 🏗️ Architecture Overview

Hiver follows Django's MVC pattern with a **3-Layer LLM Wiki Architecture** for document processing:

```
┌─────────────────────────────────────────────────────────────┐
│                        Presentation Layer                        │
├─────────────────────────────────────────────────────────────┤
│  templates/              static/                              │
│    ├── base.html          ├── css/                               │
│    ├── timeline/          │    └── style.css                     │
│    │   └── timeline.html  │    └── style.min.css                │
│    ├── archive/          └── js/                                │
│    │   └── archive.html    └── theme.js                         │
│    ├── ai_assistant/       └── theme.min.js                     │
│    │   └── chat.html                                       │
│    └── accounts/                                           │
│        ├── login.html                                      │
│        └── did_login.html                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        3-Layer Wiki Architecture                │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: RawDocument     - Immutable original uploads         │
│  Layer 2: WikiPage        - Processed/normalized content       │
│  Layer 3: SchemaRule       - LLM formatting rules              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        Application Layer                        │
├─────────────────────────────────────────────────────────────┤
│  apps/                                                           │
│    ├── core/                 - Case, Layer 1-3 models, LLM    │
│    │   ├── models.py        - Case, RawDocument, WikiPage,     │
│    │   │                     SchemaRule, TimelineFile           │
│    │   ├── views.py         - Case CRUD, APIs                  │
│    │   ├── llm_clients.py   - LLM client implementations      │
│    │   ├── prompts.py       - LLM prompt templates             │
│    │   ├── tasks.py         - Sync pipeline tasks              │
│    │   ├── urls.py          - Core URL routing                 │
│    │   └── middleware.py    - Auth middleware                   │
│    │                                                    │
│    ├── timeline/            - Timeline events, parsing          │
│    │   ├── models.py        - TimelineEvent                     │
│    │   ├── views.py         - Timeline views                   │
│    │   ├── utils.py         - Markdown parsing                 │
│    │   └── urls.py          - Timeline URL routing             │
│    │                                                    │
│    ├── archive/             - Document storage                  │
│    │   ├── models.py        - ArchiveDocument                   │
│    │   ├── views.py         - Archive views                    │
│    │   └── urls.py          - Archive URL routing              │
│    │                                                    │
│    ├── ai_assistant/        - AI integration & conversations    │
│    │   ├── models.py        - AIConversation                   │
│    │   ├── views.py         - AI chat, LLM queries             │
│    │   └── urls.py          - AI URL routing                   │
│    │                                                    │
│    ├── conversation_logs/   - Conversation logging (placeholder)│
│    │                                                    │
│    └── accounts/            - Authentication                     │
│        ├── models.py        - (Uses Django User)               │
│        ├── views.py         - DID & standard auth               │
│        └── urls.py          - Accounts URL routing              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                         Data Layer                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │   PostgreSQL    │    │    SQLite       │                 │
│  │  (Production)   │    │   (Default)      │                 │
│  └────────┬────────┘    └────────┬────────┘                 │
│           │                      │                            │
│           └──────────┬───────────┘                            │
│                      │                                        │
│                ┌─────┴─────┐                                 │
│                │ Django ORM │                                 │
│                └───────────┘                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        External Systems                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │ Rust-DID Library │    │ LLM APIs         │                 │
│  │ (FFI via ctypes) │    │ (Ollama/Gemini)  │                 │
│  └─────────────────┘    └─────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Request Flow

1. **Request** → middleware (auth check, security headers)
2. **URL Dispatcher** → routes to appropriate view
3. **View** → processes request, queries models
4. **Template** → renders HTML with context
5. **Response** → returns to user

### Key Design Patterns

- **MVT (Model-View-Template)**: Django's pattern for web apps
- **Faceted Navigation**: Filter by case, category, date
- **Lazy Loading**: Markdown files parsed on-demand
- **Event Sourcing**: Timeline events stored as immutable records
- **CQRS-like**: Separate read/write operations for performance

---

## 🗄️ Models Reference

### Core Models (apps/core/models.py)

#### Case
```python
class Case(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#FF8C00')
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
 
    # Properties
    event_count: Count of timeline events
    document_count: Count of archive documents
 
    # Methods
    get_absolute_url(): Reverse URL for case detail
    can_access(user): Check if user can access this case
    can_edit(user): Check if user can edit this case
    can_delete(user): Check if user can delete this case
 
    # Class Methods
    get_user_case(user): Get most recent case for user (replaces get_default_case)
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
 
    # Methods
    get_absolute_url(): Reverse URL for timeline file
    to_dict(): Convert to dictionary for API responses
```

#### RawDocument (Layer 1: Immutable Raw Documents)
```python
class RawDocument(models.Model):
    """Immutable raw document storage with metadata."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    file = models.FileField(upload_to=raw_document_upload_path)
    file_type = models.CharField(max_length=10, choices=[('pdf','PDF'), ('md','Markdown'), ('json','JSON')])
    source_party = models.CharField(max_length=50, choices=[('CLIENT','Client'), ('OPPOSING','Opposing'), ('NEUTRAL','Neutral')])
    document_type = models.CharField(max_length=100)  # e.g., "Motion to Dismiss"
    reliability_note = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_immutable = models.BooleanField(default=True)  # Prevents modification after creation
```

#### WikiPage (Layer 2: Processed Content)
```python
class WikiPage(models.Model):
    """Processed/normalized content derived from RawDocuments with version history."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)  # e.g., "timeline", "witness_list"
    content = models.TextField()  # Markdown content
    last_updated = models.DateTimeField(auto_now=True)
    version_history = models.JSONField(default=list)  # Previous versions with timestamps
    citation_references = models.JSONField(default=list)  # Claim IDs and sources
    category = models.CharField(max_length=20, choices=[('VERIFIED','Stipulated/Verified'), ('CONTESTED','Contested Allegation')])
    # Unique together: case + title
```

#### SchemaRule (Layer 3: LLM Formatting Rules)
```python
class SchemaRule(models.Model):
    """Rules for LLM formatting and content structure."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE)
    rule_name = models.CharField(max_length=200)  # e.g., "timeline_formatting"
    rule_description = models.TextField()
    rule_content = models.TextField()  # Markdown or JSON rules for LLM
    # Unique together: case + rule_name
```

### Timeline Models (apps/timeline/models.py)

#### TimelineEvent
```python
class TimelineEvent(models.Model):
    date = models.DateField()
    event = models.CharField(max_length=255)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    supporting_docs = models.JSONField(blank=True, null=True)
    notes = models.TextField(blank=True)
    timeline_file = models.CharField(max_length=512, blank=True, null=True)
    case = models.ForeignKey(Case, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
 
    # Category Choices
    CATEGORY_CHOICES = [
        ('verified', 'Verified'),      # NEW: Added for manual event creation
        ('contested', 'Contested'),    # NEW: Added for manual event creation
        ('contract', 'Contract'),
        ('email', 'Email'),
        ('court_filing', 'Court Filing'),
        ('communication', 'Communication'),
        ('meeting', 'Meeting'),
        ('deadline', 'Deadline'),
        ('personal', 'Personal'),      # NEW: Added for manual event creation
        ('legal', 'Legal'),            # NEW: Added for manual event creation
        ('medical', 'Medical'),        # NEW: Added for manual event creation
        ('financial', 'Financial'),    # NEW: Added for manual event creation
        ('education', 'Education'),    # NEW: Added for manual event creation
        ('other', 'Other'),
    ]
 
    # Methods
    get_absolute_url(): Reverse URL for event detail
    get_category_display(): Human-readable category
    get_archive_documents(): Get linked ArchiveDocument objects
    get_document_urls(): Extract all document URLs from supporting_docs
```

**NEW: Manual Event Creation**
- Added `create_event` view for AJAX event creation
- Supports dynamic document linking from archive
- Uses standard 5-column format: Date, Event/Incident, Category, Supporting Documents, Notes

### Archive Models (apps/archive/models.py)

#### ArchiveDocument
```python
class ArchiveDocument(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='archive/')
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL)
    case = models.ForeignKey(Case, on_delete=models.SET_NULL, null=True, blank=True)
    timeline_event = models.ForeignKey(TimelineEvent, on_delete=models.SET_NULL, null=True, blank=True)
 
    # Methods
    get_absolute_url(): Reverse URL for document detail
    is_pdf(): Check if file is PDF
    is_image(): Check if file is image
    get_file_extension(): Get file extension
```

---

## 🧠 3-Layer Wiki Architecture

Hiver uses a 3-layer architecture for document processing and LLM integration:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: RawDocument (Immutable)                             │
├─────────────────────────────────────────────────────────────┤
│  • Original uploaded documents (PDF, Markdown, JSON)        │
│  • Immutable once created (is_immutable=True)               │
│  • Metadata: source_party (CLIENT/OPPOSING/NEUTRAL)        │
│  • Stored in media/raw/<case_id>/                          │
└─────────────────────────────────────────────────────────────┘
                            ↓ Sync Pipeline
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: WikiPage (Processed)                              │
├─────────────────────────────────────────────────────────────┤
│  • Normalized content derived from RawDocuments             │
│  • Version history maintained automatically                │
│  • Citation references track claims to sources             │
│  • Category: VERIFIED vs CONTESTED                         │
│  • Unique per case+title combination                       │
└─────────────────────────────────────────────────────────────┘
                            ↓ Schema Rules
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: SchemaRule (LLM Formatting)                       │
├─────────────────────────────────────────────────────────────┤
│  • Defines how LLM should format/structure content         │
│  • Applied during document sync and query processing        │
│  • Unique per case+rule_name combination                   │
└─────────────────────────────────────────────────────────────┘
```

### Sync Pipeline (apps/core/tasks.py)

The sync pipeline processes RawDocuments into WikiPages using LLM:

1. **Load Document**: Extract text from PDF/Markdown/JSON
2. **LLM Analysis**: Use prompts from `prompts.py` to categorize events
3. **Conflict Detection**: Cross-reference with existing Wiki content
4. **Wiki Update**: Create/update WikiPage with citations
5. **Log Contradictions**: Track disputes in `contradictions.md`

### LLM Clients (apps/core/llm_clients.py)

```python
# Supported backends (configured in settings.py):
LLM_BACKEND = 'mock'    # MockLLMClient - for testing
LLM_BACKEND = 'ollama'  # OllamaClient - local LLM (http://localhost:11434)
LLM_BACKEND = 'gemini'  # GeminiClient - Google Gemini API
```

### Prompt Templates (apps/core/prompts.py)

- `SYNC_PROMPT_TEMPLATE`: For processing documents into Wiki format
- Categorizes events as "Stipulated/Verified" or "Contested Allegation"
- Extracts source party, date, and citation information

---

## 🔌 API Endpoints

### Authentication APIs (accounts/)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/accounts/login/` | Standard login page | No |
| POST | `/accounts/login/` | Login with username/password | No |
| GET | `/accounts/did/login/` | DID login page | No |
| POST | `/accounts/did/login/` | Login with DID | No |
| GET/POST | `/accounts/logout/` | Logout | Yes |
| GET | `/accounts/challenge/` | Generate DID challenge | No |

### Case APIs (core/)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/core/cases/` | List all user cases | Yes |
| GET | `/core/cases/create/` | Show create case form | Yes |
| POST | `/core/cases/create/` | Create new case | Yes |
| GET | `/core/cases/<id>/` | Case detail page | Yes |
| POST | `/core/cases/<id>/delete/` | Delete case | Yes |
| GET | `/core/cases/<id>/switch/` | Switch to case | Yes |
| GET | `/core/api/cases/` | API: List cases (JSON) | Yes |
| GET | `/core/api/cases/<id>/` | API: Case details (JSON) | Yes |

### Timeline APIs (timeline/)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/timeline/` | Timeline view | Yes |
| GET | `/timeline/upload/` | Upload form | Yes |
| POST | `/timeline/upload/` | Upload markdown | Yes |
| GET | `/timeline/event/<id>/` | Event detail | Yes |
| GET | `/timeline/api/load-timeline/` | Load timeline file | Yes |
| GET | `/timeline/api/timeline-headings/` | List timeline headings | Yes |
| GET | `/timeline/select-timeline/` | Select timeline | Yes |
| POST | `/timeline/api/create-timeline-file/` | Create timeline file | Yes |

### Archive APIs (archive/)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/archive/` | Archive view | Yes |
| GET | `/archive/upload/` | Upload form | Yes |
| POST | `/archive/upload/` | Upload document | Yes |
| GET | `/archive/document/<id>/` | Document detail | Yes |
| GET | `/archive/file/<id>/` | Serve file | Yes |
| GET | `/archive/api/documents/` | List documents (JSON) | Yes |
| GET | `/archive/api/search/` | Search documents (JSON) | Yes |

### AI APIs (ai/)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/ai/` | AI chat interface | Yes |
| POST | `/ai/analyze-document/` | Analyze document | Yes |
| POST | `/ai/query-timeline/` | Query timeline with LLM | Yes |
| POST | `/ai/suggest-events/` | Suggest events from docs | Yes |
| POST | `/ai/analyze-event/<id>/` | Analyze specific event | Yes |
| GET/POST | `/ai/conversations/` | List/create conversations | Yes |
| GET | `/ai/conversation/<id>/` | View conversation history | Yes |

#### AIConversation Model (apps/ai_assistant/models.py)
```python
class AIConversation(models.Model):
    title = models.CharField(max_length=255, default="New Conversation")
    case = models.ForeignKey(Case, on_delete=models.CASCADE, null=True, blank=True)
    messages = models.JSONField(default=list)  # List of message objects
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Meta: ordering = ['-updated_at']
```

---

## 📄 Markdown Parsing Logic

### Parsing Pipeline

```
Markdown File
      ↓
[1] File Reading (parse_markdown_file)
      ↓
[2] Validation (validate_markdown_content)
      ↓
[3] HTML Conversion (markdown.markdown with extensions)
      ↓
[4] Heading Extraction (regex for # headings) → headings list
      ↓
[5] Section Parsing (split by headings) → sections list
      ↓
[6] Table Event Extraction (parse_timeline_events_from_table) → table-based events
      ↓
[7] Section Event Extraction (parse_section_events) → section-based events (fallback)
      ↓
[8] Event Validation (validate_timeline_events) → validated events or error
      ↓
[9] Image Extraction (BeautifulSoup find_all 'img') → images list
      ↓
[10] Table Data Extraction (for display) → tables list
      ↓
Parsed Content { headings, sections, events, images, tables, warnings }
```

**Priority:** Table-based events (step 6) take precedence over section-based events (step 7).

### Key Functions (apps/timeline/utils.py)

#### parse_markdown_file(file_path)

Parses a markdown file and returns structured data.

**Parameters:**
- `file_path` (str): Absolute path to markdown file

**Returns:**
```python
{
    'headings': [
        {
            'level': 1,      # Integer 1-6 (H1-H6)
            'text': 'Main Heading',
            'anchor': 'main-heading'  # URL-friendly anchor
        },
        ...
    ],
    'first_heading': 'Main Heading',
    'sections': [
        {
            'heading': 'Section Title',
            'content': 'Section content...',
            'level': 2
        },
        ...
    ],
    'events': [
        # Table-based format (preferred):
        {
            'section': 'Contract Phase',  # Parent heading
            'date': '2024-01-15',         # YYYY-MM-DD format
            'event': 'Contract Signed',   # Event title
            'description': 'Initial agreement',  # Description
            'category': 'contract',        # Lowercase category
            'documents': ['doc1.pdf', 'doc2.pdf']  # List of document names/URLs
        },
        # OR Section-based format (legacy, fallback):
        {
            'title': 'Event Title',
            'date': '2024-01-15',
            'category': 'contract',
            'notes': 'Event notes',
            'description': 'Full description',
            'documents': [{'title': 'Doc', 'url': 'path'}],
            'section_level': 2
        },
        ...
    ],
    'raw_content': 'Raw markdown text...',
    'html': '<html>...</html>',
    'images': [{'url': 'path', 'alt': 'text'}],
    'tables': [[['row1cell1', 'row1cell2'], ['row2cell1', 'row2cell2']]],
    'warnings': ['Validation warning...'],
    'timelines': {
        'Housing Timeline': [
            {'date': '2024-01-15', 'event': 'Contract Signed', ...},
            ...
        ],
        'Education Timeline': [...],
        'Master Timeline': [...]  # Added by view, combines all events sorted by date
    }
}
```

**Note:** Event format depends on source. Table-based parsing produces standardized 5-column format. Events are now grouped by their parent heading in the `timelines` dictionary.

**Supported Formats:**
- **Format A**: Simple headings with content
- **Format B**: H2 headings as events with **Date:**, **Event:**, etc.
- **Format C**: Mixed content with embedded markdown
- **Format D**: Multiple tables under different headings → Each heading becomes a separate timeline

#### parse_timeline_events_from_markdown(markdown_content)

Alternative parser for legacy format.

**Parameters:**
- `markdown_content` (str): Raw markdown text

**Returns:** List of event dicts

**Format:**
```markdown
# Date
**Event:** Event Title
**Category:** category_name
**Notes:** Event notes
**Supporting Docs:** doc1, doc2
```

#### parse_section_events(section)

Parses events from a section of markdown.

**Parameters:**
- `section` (dict): Section with 'heading', 'content', 'level' keys

**Returns:** List of event dicts

**Format:**
```markdown
## Event Title
**Date:** 2024-01-15
**Category:** contract
Notes: Some notes here
Description: More details
Supporting Docs: [Doc1](url1), [Doc2](url2)
```

#### parse_timeline_events_from_table(html_content, current_section=None)

Parses timeline events from HTML tables (5-column format). This is the **preferred** format for structured timeline data.

**Parameters:**
- `html_content` (str): HTML content from markdown conversion
- `current_section` (str, optional): Section heading for grouping events

**Returns:** List of event dicts with standardized structure:
```python
[{
    'section': 'Contract Phase',
    'date': '2024-01-15',
    'event': 'Contract Signed',
    'description': 'Initial agreement executed',
    'category': 'contract',
    'documents': ['contract1.pdf', 'contract2.pdf']
}, ...]
```

**Format:**
```markdown
| Date | Event | Description | Category | Documents |
|------|-------|-------------|----------|-----------|
| 2024-01-15 | Contract Signed | Initial agreement | contract | doc1.pdf, doc2.pdf |
| 2024-03-20 | Amendment | Payment terms | contract | amendment.pdf |
```

**Parsing Rules:**
- Row 1 is treated as header and skipped
- Each data row must have at least 5 cells
- Documents field is split by comma and stripped
- Category is converted to lowercase
- Section is associated from the parent heading

#### validate_timeline_events(events)

Validates timeline events for required fields and date format.

**Parameters:**
- `events` (list): List of event dicts to validate

**Returns:** True if all events are valid

**Raises:** `ValueError` if validation fails

**Validation Rules:**
1. Required fields: `date`, `event`, `description`, `category`, `documents`
2. Date format: `YYYY-MM-DD` (strict validation)
3. All fields must be non-empty

**Usage:**
```python
from apps.timeline.utils import parse_markdown_file, validate_timeline_events

parsed = parse_markdown_file('timeline.md')
try:
    validate_timeline_events(parsed['events'])
    # Events are valid, proceed with display
    return render(request, 'timeline.html', {'events': parsed['events']})
except ValueError as e:
    # Handle validation error
    messages.error(request, str(e))
    return redirect('timeline:upload')
```

#### validate_timeline_events(timelines)

Validates timeline events for required fields and date format when events are grouped by timeline.

**Parameters:**
- `timelines` (dict): Dictionary of timeline_name -> list of event dicts

**Returns:** True if all events are valid

**Raises:** `ValueError` if validation fails

**Usage:**
```python
from apps.timeline.utils import parse_markdown_file, validate_timeline_events

parsed = parse_markdown_file('timeline.md')
try:
    validate_timeline_events(parsed['timelines'])
except ValueError as e:
    messages.error(request, str(e))
```

### Error Handling

#### MarkdownParseError
Raised when file operations fail:
- File not found
- Permission denied
- IO errors

#### MarkdownValidationError
Raised when content is invalid:
- Empty file
- No headings found

#### Graceful Degradation
If python-markdown or BeautifulSoup not available:
- Uses regex-only parsing
- Returns warnings in response
- Still parses headings and basic structure

---

## 🔐 Authentication System

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Authentication Flow                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Standard Flow:                                                   │
│  User → Login Form → Django Auth → Session → Timeline          │
│                                                              │
│  DID Flow:                                                       │
│  User → DID Form → Challenge → DID Manager → Signature →        │
│  Rust-DID Verify → Session → Timeline                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Components

#### Rust-DID Wrapper (apps/core/did_rust_wrapper.py)

-handles FFI with Rust library:
- Lazy loading of library (only when needed)
- Wrapper methods for DID operations
- Graceful fallback when library not available

**Key Functions:**
- `get_did_wrapper()`: Lazy initialization
- `generate_user_did(user_id)`: Generate DID for user
- `verify_credential(credential)`: Verify signed credential

#### Authentication Middleware (apps/core/middleware.py)

- `RustDIDAuthenticationMiddleware`: Main auth middleware
- Checks `DID_BACKEND` setting (rust/python)
- Verifies VC tokens from headers/cookies
- Falls back to session authentication

**Key Methods:**
- `rust_did_available()`: Check if Rust-DID is configured
- `process_request()`: Main middleware logic
- `verify_vc_token()`: Verify credential token
- `get_user_from_vc()`: Extract user from credential

#### DID Views (apps/accounts/views.py)

- `did_login(request)`: DID login view
- `generate_challenge(request)`: Generate challenge API
- `did_logout(request)`: Logout with DID cleanup
- `auth_status(request)`: Check auth status API

### Session Management

```python
# Settings (config/settings.py)
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection

# Login/Logout URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/timeline/'
LOGOUT_REDIRECT_URL = '/timeline/'
```

---

## 📊 Case Compartmentalization

### How It Works

1. **User-Specific Queries**: All queries filter by `user_id`
2. **Session Storage**: Selected case stored in session
3. **Model Methods**: `can_access()`, `can_edit()`, `can_delete()`
4. **View Filtering**: Automatic filtering in views

### Example Query

```python
# Get cases for current user only
cases = Case.objects.filter(user=request.user).order_by('-updated_at')

# Get events for current case or user
if case_id:
    case = Case.objects.get(id=case_id, user=request.user)
    events = TimelineEvent.objects.filter(case=case)
else:
    events = TimelineEvent.objects.filter(created_by=request.user)
```

### Session Management

```python
# Store selected case
request.session['selected_case_id'] = case.id

# Retrieve selected case
case_id = request.session.get('selected_case_id')

# Clear selection
request.session.pop('selected_case_id', None)
```

### Default Case

```python
# Automatically create default case for new users
case = Case.get_default_case(request.user)
if case:
    request.session['selected_case_id'] = case.id
```

### Standard Folder Structure

**NEW: Each case automatically gets a standardized folder structure**

```python
# Called automatically when creating a new case
ArchiveDocument.create_standard_folder_structure(case, user)
```

Creates these folders:
- `01_Raw/` - Original uploaded documents and source materials
- `02_Wiki/` - Processed and cleaned documents for reference
- `03_Drafts/` - Working drafts and editable documents
- `04_Strategy/` - Strategy documents and case planning materials
- `05_Exports/` - Export outputs, reports, and final deliverables

**Implementation Details:**
- Uses `.folder` files as folder markers
- Stores folder metadata in JSON format
- Folders appear with 📁 icon and special styling
- Supports future nested folder expansion

---

## 🛠️ Extending Hiver

### Adding a New Model

1. Add model to appropriate app's `models.py`
2. Create migration: `uv run python manage.py makemigrations`
3. Apply migration: `uv run python manage.py migrate`
4. Add views for CRUD operations
5. Create templates for display
6. Add URLs to app's `urls.py`

### Adding a New API Endpoint

```python
# apps/myapp/views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def my_api_endpoint(request):
    data = {'message': 'Hello', 'results': []}
    return JsonResponse(data)
```

### Adding Custom Authentication

```python
# apps/core/middleware.py
from django.contrib.auth import authenticate

class CustomAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Check for custom auth header
        token = request.headers.get('X-Custom-Token')
        if token:
            user = authenticate(token=token)
            if user:
                request.user = user
                return None
        return None
```

### Adding Markdown Extensions

```python
# apps/timeline/utils.py
import markdown

def parse_markdown_file(file_path):
    # ... existing code ...
    
    # Add custom extensions
    extensions = [
        'tables',
        'fenced_code',
        'codehilite',
        'footnotes',
        'md_in_html',
        'your_custom_extension',  # Add custom extension here
    ]
    
    html = markdown.markdown(content, extensions=extensions)
```

---

## 🎨 Customization Guide

### Custom Themes

1. **CSS Variables**: Override in your custom CSS
```css
:root {
    --primary: #FF8C00;   /* Change honey-orange */
    --accent: #0064AA;    /* Change Byers blue */
    --bg: #000000;        /* Change dark background */
    /* Add more overrides */
}
```

2. **Create Custom Theme File**:
```
static/css/custom.css
```

3. **Load in Template**:
```html
{% extends 'base.html' %}
{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/custom.css' %}">
{% endblock %}
```

### Custom Logos

Replace logo files in:
```
static/core/images/logos/
    ├── DARK_mode_LOGO.png    # Dark mode logo
    └── light_mode_LOGO.png   # Light mode logo
```

### Custom Colors

Define in `config/settings.py`:
```python
HIVER_THEME = {
    'PRIMARY_COLOR': '#FF8C00',      # Honey-Orange
    'ACCENT_COLOR': '#0064AA',        # Byers Blue
    'DARK_BG': '#1A1A1A',           # Charcoal
    'DARK_TEXT': '#FFFFFF',          # White
    'LIGHT_BG': '#F5F5F5',           # Off-white
    'LIGHT_TEXT': '#333333',         # Dark Gray
}
```

---

## ⚡ Performance Considerations

### Database Optimization

1. **Add Indexes**: For frequently queried fields
```python
class TimelineEvent(models.Model):
    date = models.DateField(db_index=True)
    case = models.ForeignKey(Case, on_delete=models.SET_NULL, db_index=True)
```

2. **Select Related**: Reduce queries with `select_related`
```python
events = TimelineEvent.objects.filter(case=case).select_related('case', 'created_by')
```

3. **Prefetch Related**: For many-to-many relationships
```python
cases = Case.objects.filter(user=request.user).prefetch_related('events', 'documents')
```

### Caching

1. **Template Fragment Caching**:
```html
{% load cache %}
{% cache 500 timeline_header %}
    <div class="timeline-header">
        <!-- Expensive content -->
    </div>
{% endcache %}
```

2. **View Caching**:
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15 minutes
@login_required
def timeline_view(request):
    # ...
```

3. **Low-Level Caching**:
```python
from django.core.cache import cache

def parse_markdown_file(file_path):
    cache_key = f'parsed_markdown_{file_path}'
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    result = do_expensive_parsing(file_path)
    cache.set(cache_key, result, 3600)  # 1 hour
    return result
```

### Running Commands with uv

All Django management commands should be run using `uv run`:
```bash
# Check project health
uv run python manage.py check

# Create and apply migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# Start development server
uv run python manage.py runserver

# Collect static files
uv run python manage.py collectstatic
```

### Project Dependencies (pyproject.toml)

```toml
[project]
name = "hiver-django"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "beautifulsoup4>=4.14.3",
    "django>=5.2.13",
    "markdown>=3.10.2",
    "pdfplumber>=0.11.9",
    "pytesseract>=0.3.13",
    "python-dotenv>=1.2.2",
]
```

Install dependencies:
```bash
uv sync
```

### Lazy Loading

1. **Images**: Use `loading="lazy"` attribute
2. **Documents**: Load on-demand when pane is opened
3. **Timeline Events**: Paginate or use infinite scroll

---

## 🔒 Security Guide

### Authentication Security

1. **Always Use HTTPS**: Required for all authentication
2. **Secure Cookies**: Settings configured for security
3. **CSRF Protection**: Built into Django forms
4. **Session Security**: HttpOnly, Secure, SameSite flags

### Authorization

1. **User Ownership Checks**: Always verify user owns the resource
```python
case = get_object_or_404(Case, id=case_id, user=request.user)
```

2. **Permission Methods**: Use model's `can_access()` methods
```python
if case.can_access(request.user):
    # Allow access
else:
    raise PermissionDenied()
```

3. **Login Required**: Protect all user data views
```python
from django.contrib.auth.decorators import login_required

@login_required
def protected_view(request):
    # Only logged-in users can access
    pass
```

### Input Validation

1. **Form Validation**: Use Django forms
2. **File Uploads**: Validate file types and sizes
```python
from django.core.exceptions import ValidationError

def clean_file(self):
    file = self.cleaned_data['file']
    if file.size > 10 * 1024 * 1024:  # 10MB
        raise ValidationError("File too large")
    return file
```

3. **Sanitize Input**: Use Django's template escaping
```html
{{ user_input|escape }}  <!-- Escapes HTML -->
```

### Security Headers

Configured in `apps/core/middleware.py`:
- `Strict-Transport-Security`: Enforce HTTPS
- `X-Content-Type-Options`: Prevent MIME sniffing
- `X-Frame-Options`: Prevent clickjacking
- `X-XSS-Protection`: Enable XSS filter
- `Content-Security-Policy`: Restrict resource loading

### Data Compartmentalization

Hiver implements **strict multi-tenant data isolation** at every layer:

#### 1. Model-Level Security

All models enforce user ownership:

```python
# apps/core/models.py
class Case(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # Cascade delete for data cleanup
        related_name='cases'
    )
    # Each user has their own isolated cases

class TimelineFile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='timeline_files'
    )
    case = models.ForeignKey(
        'Case',
        on_delete=models.CASCADE,
        related_name='timeline_files'
    )
    # Files belong to both user AND case

# apps/timeline/models.py
class TimelineEvent(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='timeline_events_created'
    )
    case = models.ForeignKey(
        'core.Case',
        on_delete=models.SET_NULL,
        related_name='events'
    )
    # Events tracked by creator and case

# apps/archive/models.py  
class ArchiveDocument(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='archive_documents'
    )
    case = models.ForeignKey(
        'core.Case',
        on_delete=models.SET_NULL,
        related_name='archive_documents'
    )
    # Documents owned by user, optionally linked to case
```

**Key Design Decisions:**
- `CASCADE` for user deletion: Removes all user data
- `SET_NULL` for case deletion on TimelineEvent/TimelineFile: Prevents accidental mass deletion
- `CASCADE` for case deletion on ArchiveDocument: Documents are case-specific

#### 2. Query-Level Security

**ALL queries MUST filter by user**. Never use `.all()` on user-owned models:

```python
# ❌ WRONG - Security vulnerability!
documents = ArchiveDocument.objects.all()
events = TimelineEvent.objects.all()

# ✅ CORRECT - Always filter by user
documents = ArchiveDocument.objects.filter(user=request.user)
events = TimelineEvent.objects.filter(created_by=request.user)

# ✅ CORRECT - Filter by case with user ownership check
case = get_object_or_404(Case, id=case_id, user=request.user)
events = TimelineEvent.objects.filter(
    case=case,
    created_by=request.user
)
```

#### 3. Permission Methods

Models include object-level permission checks:

```python
# apps/core/models.py
class Case(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    def can_access(self, user):
        """Check if user can access this case."""
        return user.is_authenticated and user.id == self.user_id
    
    def can_edit(self, user):
        """Check if user can edit this case."""
        return self.can_access(user)
    
    def can_delete(self, user):
        """Check if user can delete this case."""
        return self.can_access(user)
    
    @classmethod
    def get_user_case(cls, user):
        """Get the most recent case for a user."""
        return cls.objects.filter(user=user).order_by('-updated_at').first()
```

**Usage in Views:**
```python
@login_required
def case_detail(request, case_id):
    case = get_object_or_404(Case, id=case_id, user=request.user)
    if not case.can_access(request.user):
        raise PermissionDenied()
    return render(request, 'case_detail.html', {'case': case})
```

#### 4. View-Level Enforcement

All views enforce user isolation (Case model now uses UUIDField for primary key):

```python
# apps/timeline/views.py
def timeline_view(request):
    # ALWAYS filter by user first
    events = TimelineEvent.objects.filter(created_by=request.user)
    
    # Then filter by case if specified (case_id is now UUID string)
    if case_id:
        case = get_object_or_404(Case, id=case_id, user=request.user)
        events = events.filter(case=case)

# apps/archive/views.py
def archive_view(request):
    # ONLY user's documents
    documents = ArchiveDocument.objects.filter(user=request.user)

# apps/ai_assistant/views.py
def query_timeline(request):
    # User-specific context with LLM integration
    events = TimelineEvent.objects.filter(
        created_by=request.user
    )
    if event_id:
        event = get_object_or_404(
            TimelineEvent,
            pk=event_id,
            created_by=request.user  # Double-check ownership
        )
    
    # LLM integration via prompts.py and llm_clients.py
    from apps.core.prompts import SYNC_PROMPT_TEMPLATE
    from apps.core.tasks import initialize_llm_client
```

#### 5. API Endpoint Security

All JSON API endpoints filter by user:

```python
# apps/archive/views.py
@login_required
def api_document_list(request):
    """API: List ONLY user's documents."""
    documents = ArchiveDocument.objects.filter(
        user=request.user
    ).values('id', 'title', 'file_type', 'upload_date', 'category')
    return JsonResponse(list(documents), safe=False)

@login_required  
def api_document_search(request):
    """API: Search ONLY user's documents."""
    documents = ArchiveDocument.objects.filter(user=request.user)
    # ... apply search filters
    return JsonResponse(list(results), safe=False)
```

#### 6. Security Testing Checklist

✅ All views have `@login_required` decorator   
✅ All queries filter by `request.user`   
✅ All `get_object_or_404` calls check user ownership   
✅ No `.all()` on user-owned models in production views   
✅ API endpoints return only user's data   
✅ Uploaded files are stored in user-specific directories   
✅ Session data is user-scoped   

#### 7. Common Security Pitfalls (and Fixes)

| Pitfall | Example | Fix |
|---------|---------|-----|
| `.all()` on user models | `ArchiveDocument.objects.all()` | `.filter(user=request.user)` |
| Missing login check | No `@login_required` | Add decorator |
| Case-only filter | `.filter(case=case)` | Add `.filter(created_by=request.user)` |
| No user check in get() | `get_object_or_404(Case, id=id)` | Add `, user=request.user` |
| Insecure file access | `open(path)` | Use `get_user_archive_dir(user)` |

---

## 📞 Support

- **Documentation**: This guide, USER_GUIDE.md, TESTING_CHECKLIST.md
- **Django Documentation**: https://docs.djangoproject.com/
- **Python Markdown**: https://python-markdown.github.io/
- **BeautifulSoup**: https://www.crummy.com/software/BeautifulSoup/
- **uv Package Manager**: https://docs.astral.sh/uv/
- **LLM Integration**: See `apps/core/llm_clients.py`, `apps/core/prompts.py`
- **3-Layer Wiki**: See `ADVERSARIAL_HANDLING.md`, `SYNC_PIPELINE_README.md`

---

## 🚧 Unfinished Features & Roadmap

### Current State

The project is approximately 85% complete with core functionality implemented but several key features requiring completion:

### 🚧 Unfinished Features

#### 1. LLM Integration (High Priority)
**Status**: Partially implemented with mock responses

**Files Affected:**
- `apps/core/tasks.py` - `call_llm()` function returns mock responses
- `apps/core/tasks.py` - `initialize_llm_client()` needs integration with actual sync pipeline
- `apps/core/tasks.py` - `sync_document_to_wiki()` uses placeholder LLM calls

**What's Missing:**
- Actual LLM API integration in the sync pipeline
- Real implementation of `call_llm()` function
- Integration with Ollama/Gemini clients in document processing

**Implementation Plan:**
```python
# Replace mock call_llm() with actual LLM integration
def call_llm(prompt, document_text):
    """Call LLM with the sync prompt."""
    llm_client = initialize_llm_client()
    return llm_client.generate(prompt)
```

#### 2. Sync Pipeline Tracking (High Priority)
**Status**: Basic implementation without status tracking

**Files Affected:**
- `apps/core/models.py` - RawDocument model missing `synced_at` field
- `apps/core/tasks.py` - `task_sync_all_pending()` can't filter unsynced docs

**What's Missing:**
- `synced_at` field on RawDocument model
- Query filtering for unsynced documents
- Progress tracking for sync operations

**Implementation Plan:**
```python
# Add to RawDocument model
synced_at = models.DateTimeField(
    null=True,
    blank=True,
    help_text="When the document was synced to Wiki layer"
)

# Update sync task
pending_docs = RawDocument.objects.filter(synced_at__isnull=True)
```

#### 3. Conversation Logs (Medium Priority)
**Status**: Placeholder app with no functionality

**Files Affected:**
- `apps/conversation_logs/` - Entire app is placeholder
- `apps/conversation_logs/models.py` - Empty model
- `apps/conversation_logs/views.py` - Basic views without logic

**What's Missing:**
- Actual conversation logging model
- Integration with AI assistant
- Message storage and retrieval

**Implementation Plan:**
```python
# Implement proper conversation logging model
class ConversationLog(models.Model):
    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE)
    message = models.TextField()
    sender = models.CharField(max_length=20)  # 'user' or 'ai'
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)
```

#### 4. Document Processing (Medium Priority)
**Status**: Placeholder PDF extraction

**Files Affected:**
- `apps/core/tasks.py` - `load_document_text()` has placeholder PDF handling
- `scripts/pdf_to_md_conversion.py` - Needs integration

**What's Missing:**
- Actual PDF text extraction
- Integration with existing PDF processing scripts
- Support for different document types

**Implementation Plan:**
```python
# Integrate actual PDF extraction
def load_document_text(raw_doc):
    if raw_doc.file_type == 'pdf':
        from scripts.pdf_to_md_conversion import extract_pdf_text
        return extract_pdf_text(raw_doc.file.path)
```

#### 5. Adversarial Labeling (Medium Priority)
**Status**: Function referenced but not implemented

**Files Affected:**
- `apps/core/utils.py` - Missing `apply_adversarial_labeling()` function
- `apps/ai_assistant/views.py` - Missing `validate_adversarial_disclaimers()`

**What's Missing:**
- Implementation of adversarial labeling logic
- Validation for AI response disclaimers
- Integration with CROSS_EXAMINATION_PROMPT

**Implementation Plan:**
```python
# Implement adversarial labeling
def apply_adversarial_labeling(text, source_party):
    if source_party == 'OPPOSING':
        return f"The opposing party alleges: {text}"
    elif source_party == 'CLIENT':
        return text
    else:
        return f"According to the document: {text}"
```

### 🗑️ Redundant Code

#### 1. Duplicate Markdown Parsing
**Issue**: Multiple functions with overlapping functionality

**Files Affected:**
- `apps/timeline/utils.py` - `parse_timeline_events_from_markdown()` vs `parse_section_events()`
- `apps/timeline/utils.py` - Multiple event extraction methods

**Recommendation:**
```python
# Consolidate into single unified parsing function
def parse_timeline_events_unified(content, format='auto'):
    # Auto-detect table vs section format
    # Return standardized event format
```

#### 2. Unused Imports
**Issue**: Various imports that aren't used

**Files Affected:**
- Multiple files throughout the codebase

**Recommendation:**
- Run `uv run python -m py_compile` to identify unused imports
- Remove unused imports to clean up code

#### 3. Placeholder Functions
**Issue**: Functions that just return mock data

**Files Affected:**
- `apps/core/tasks.py` - Mock LLM functions
- `apps/conversation_logs/` - Entire placeholder app

**Recommendation:**
- Either implement fully or remove placeholder code
- Add TODO comments for incomplete features

### 📈 Areas for Improvement

#### 1. Error Handling
**Current State**: Basic error handling in most places

**Improvements Needed:**
- More robust error handling in LLM integration
- Better validation for document processing
- Comprehensive error logging

**Example:**
```python
# Add comprehensive error handling for LLM calls
try:
    response = llm_client.generate(prompt)
    return json.loads(response)
except json.JSONDecodeError as e:
    logger.error(f"LLM JSON parse error: {e}")
    return {"error": "Invalid LLM response format"}
except Exception as e:
    logger.error(f"LLM call failed: {e}")
    return {"error": "LLM processing failed"}
```

#### 2. Performance Optimization
**Current State**: Basic queries without optimization

**Improvements Needed:**
- Add caching for parsed markdown files
- Implement query optimization
- Add database indexing

**Example:**
```python
# Add caching for markdown parsing
from django.core.cache import cache

def parse_markdown_file(file_path):
    cache_key = f"parsed_markdown_{file_path}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    result = do_expensive_parsing(file_path)
    cache.set(cache_key, result, 3600)  # Cache for 1 hour
    return result
```

#### 3. Documentation Updates
**Current State**: DEVELOPER_GUIDE.md needs updates

**Improvements Needed:**
- Add section for unfinished features
- Update with current implementation status
- Add roadmap for completion

**Example:**
```markdown
## 🚧 Unfinished Features & Roadmap

### Current State
The project is approximately 85% complete with these features remaining:

1. **LLM Integration** (High Priority)
   - Status: Mock implementation
   - Files: `apps/core/tasks.py`
   - Next Steps: Integrate actual LLM API calls

2. **Sync Pipeline Tracking** (High Priority)
   - Status: Basic implementation
   - Files: `apps/core/models.py`, `apps/core/tasks.py`
   - Next Steps: Add `synced_at` field and tracking
```

#### 4. Testing Coverage
**Current State**: Basic test coverage

**Improvements Needed:**
- More comprehensive test cases
- Edge case testing
- Integration testing

**Example:**
```python
# Add edge case tests
class TestMarkdownParsing(TestCase):
    def test_empty_file(self):
        with self.assertRaises(MarkdownValidationError):
            parse_markdown_file('empty.md')
    
    def test_invalid_format(self):
        result = parse_markdown_file('invalid.md')
        self.assertIn('warnings', result)
```

#### 5. Code Organization
**Current State**: Some duplicate logic

**Improvements Needed:**
- Consolidate duplicate parsing functions
- Better separation of concerns
- More modular design

**Example:**
```python
# Create unified parsing module
# apps/timeline/parsing/
#   ├── __init__.py
#   ├── table_parser.py
#   ├── section_parser.py
#   └── unified_parser.py
```

---

## 🚀 Completion Roadmap

### Phase 1: Core Completion (2-3 weeks)
1. ✅ Complete LLM integration in sync pipeline
2. ✅ Add sync status tracking to RawDocument model
3. ✅ Implement basic conversation logging
4. ✅ Integrate PDF extraction from scripts

### Phase 2: Quality Improvement (1-2 weeks)
1. ✅ Consolidate duplicate parsing code
2. ✅ Add comprehensive error handling
3. ✅ Implement caching for performance
4. ✅ Update documentation

### Phase 3: Testing & Polish (1 week)
1. ✅ Add comprehensive test coverage
2. ✅ Performance optimization
3. ✅ Code cleanup and organization
4. ✅ Final documentation review

---

## 📞 Support

- **Documentation**: This guide, USER_GUIDE.md, TESTING_CHECKLIST.md
- **Django Documentation**: https://docs.djangoproject.com/
- **Python Markdown**: https://python-markdown.github.io/
- **BeautifulSoup**: https://www.crummy.com/software/BeautifulSoup/
- **uv Package Manager**: https://docs.astral.sh/uv/
- **LLM Integration**: See `apps/core/llm_clients.py`, `apps/core/prompts.py`
- **3-Layer Wiki**: See `ADVERSARIAL_HANDLING.md`, `SYNC_PIPELINE_README.md`

---

**Last Updated**: 2026-04-30
**Version**: 1.1

## 📝 Changelog

### Version 1.1 (2026-04-30)
- Updated to reflect 3-Layer Wiki Architecture (RawDocument → WikiPage → SchemaRule)
- Added UUIDField primary keys for Case model
- Documented LLM integration (llm_clients.py, prompts.py, tasks.py)
- Added AIConversation model documentation
- Updated all management commands to use `uv run`
- Added conversation_logs app (placeholder)
- Fixed Case.get_default_case() → Case.get_user_case()
- Documented sync pipeline for document processing
- **Added Unfinished Features & Roadmap section**
- **Added Redundant Code identification**
- **Added Areas for Improvement section**
