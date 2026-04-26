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

Hiver follows Django's MVC pattern with these key components:

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
│                        Application Layer                        │
├─────────────────────────────────────────────────────────────┤
│  apps/                                                           │
│    ├── core/                 - Case management, middleware    │
│    │   ├── models.py        - Case, TimelineFile                │
│    │   ├── views.py         - Case CRUD, APIs                  │
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
│    ├── ai_assistant/        - AI integration                    │
│    │   ├── views.py         - AI views, Mistral API             │
│    │   └── urls.py          - AI URL routing                   │
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
│  │ Rust-DID Library │    │ Mistral AI API   │                 │
│  │ (FFI via ctypes) │    │ (Optional)       │                 │
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
    name = models.CharField(max_length=255)
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
    get_default_case(user): Get or create default case
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
        ('contract', 'Contract'),
        ('email', 'Email'),
        ('court_filing', 'Court Filing'),
        ('communication', 'Communication'),
        ('meeting', 'Meeting'),
        ('deadline', 'Deadline'),
        ('other', 'Other'),
    ]
 
    # Methods
    get_absolute_url(): Reverse URL for event detail
    get_category_display(): Human-readable category
    get_archive_documents(): Get linked ArchiveDocument objects
    get_document_urls(): Extract all document URLs from supporting_docs
```

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
| POST | `/ai/query-timeline/` | Query timeline | Yes |
| POST | `/ai/suggest-events/` | Suggest events | Yes |
| POST | `/ai/analyze-event/<id>/` | Analyze specific event | Yes |

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
    'warnings': ['Validation warning...']
}
```

**Note:** Event format depends on source. Table-based parsing produces standardized 5-column format. Section-based parsing maintains backward compatibility.

**Supported Formats:**
- **Format A**: Simple headings with content
- **Format B**: H2 headings as events with **Date:**, **Event:**, etc.
- **Format C**: Mixed content with embedded markdown

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

---

## 🛠️ Extending Hiver

### Adding a New Model

1. Add model to appropriate app's `models.py`
2. Create migration: `python manage.py makemigrations`
3. Apply migration: `python manage.py migrate`
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

---

## 📞 Support

- **Documentation**: This guide, USER_GUIDE.md, TESTING_CHECKLIST.md
- **Django Documentation**: https://docs.djangoproject.com/
- **Python Markdown**: https://python-markdown.github.io/
- **BeautifulSoup**: https://www.crummy.com/software/BeautifulSoup/

---

**Last Updated**: {{ date }}
**Version**: 1.0
