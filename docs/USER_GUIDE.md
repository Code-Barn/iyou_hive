# Hiver User Guide

A comprehensive guide to using Hiver for legal timelines, document archiving, and AI-assisted research.

## 📖 Table of Contents

1. [Getting Started](#-getting-started)
2. [Timeline Management](#-timeline-management)
3. [Case Compartmentalization](#-case-compartmentalization)
4. [Document Archive](#-document-archive)
5. [AI Assistant](#-ai-assistant)
6. [Authentication](#-authentication)
7. [Workspace Layout](#-workspace-layout)
8. [Markdown Tutorial](#-markdown-tutorial)
9. [Keyboard Shortcuts](#-keyboard-shortcuts)
10. [Troubleshooting](#-troubleshooting)

---

## 🚀 Getting Started

### Installation

1. Clone the repository and install dependencies (see README.md)
2. Run migrations: `python manage.py migrate`
3. Start the server: `python manage.py runserver`
4. Open `http://localhost:8000` in your browser

### First Login

1. Visit `/accounts/login/`
2. **Option A - Standard Login**: Enter username/password
3. **Option B - DID Login**: Click "Sign In with DID" and use your Decentralized Identifier
4. After login, you'll be redirected to the timeline view

### Initial Setup

1. **Create a Case**: Go to `/core/cases/` and click "Create New Case"
2. **Upload Timeline**: Click "Upload Timeline" and select your Markdown file
3. **Upload Documents**: Click "Upload Document" to add supporting files

---

## 📅 Timeline Management

### Viewing Your Timeline

The timeline displays events in a vertical, scrollable format with:
- **Sticky year headers** that stay visible as you scroll
- **Date badges** showing month and day
- **Event cards** with title, category, and notes
- **Document indicators** showing attached files

### Creating Timeline Events

#### Method 1: Upload Markdown File

1. Click "Upload Timeline" button
2. Select a Markdown file from your computer
3. The system will automatically parse the file and create events

#### Method 2: Manual Entry (via Markdown)

Create a Markdown file with the following format:

```markdown
# My Case Name

This is a description of the case.

## Event 1: Contract Signed
**Date:** 2024-01-15
**Event:** Contract Execution
**Category:** contract
**Notes:** Initial agreement signed by both parties

## Event 2: First Amendment
**Date:** 2024-03-20
**Category:** contract
**Notes:** Payment terms modified
**Description:** 
The payment schedule was updated to reflect new terms. This amendment
was agreed upon by both parties.

Supporting documents: [Contract.pdf](contracts/contract1.pdf), [Amendment.pdf](contracts/amendment1.pdf)

## Event 3: Court Filing
**Date:** 2024-04-05
**Category:** court_filing
**Notes:** Initial complaint filed
```

### Timeline Selection

If you have multiple timeline files:
1. Use the **Timeline Selector dropdown** to choose which timeline to view
2. The main heading from the selected file becomes the page title
3. All headings (H1-H6) appear as navigation links below the title

### Timeline Navigation

- **Click on heading links** to scroll to sections
- **Use browser search** (Ctrl+F) to find specific text
- **Sticky year markers** help you track your position as you scroll

### Filtering and Sorting

- Timeline events are **sorted by date** (oldest first)
- Use the **case selector** to view only events for a specific case
- Click on **category tags** to filter by category

---

## 📁 Case Compartmentalization

Cases help you organize your legal work into isolated workspaces. Each case has its own:
- Timeline events
- Archive documents
- Timeline files
- AI assistant context

### Creating a Case

1. Go to `/core/cases/` or click "Cases" in the header
2. Click "Create New Case"
3. Fill in the form:
   - **Name**: Descriptive name (e.g., "Smith vs. Jones Lawsuit")
   - **Description**: Optional details about the case
   - **Color**: Color code for visual identification
   - **Make Active**: Check to make this your current case

4. Click "Create Case"

### Switching Cases

1. Use the **case selector dropdown** in the header
2. Click "Cases" in the header to see all cases
3. Click "Switch to Case" on a case detail page
4. The selected case is saved in your session

### Viewing Case Details

1. Go to `/core/cases/`
2. Click on a case name
3. View:
   - Basic information (name, description, color)
   - Statistics (event count, document count)
   - Recent events
   - Recent documents
   - Timeline files
   - Quick actions

### Deleting a Case

⚠️ **Warning**: This permanently deletes all data in the case!

1. Go to the case detail page
2. Scroll to the "Danger Zone" section
3. Click "Delete This Case"
4. Confirm the deletion (must check the box)
5. All events, documents, and timeline files for this case will be deleted

### Active Case

- Only one case can be **active** at a time
- The active case is highlighted in the case list
- Switching to a new case automatically deactivates the previous one
- Your session remembers which case you're viewing

---

## 📂 Document Archive

### Uploading Documents

1. Click "Upload Document" in the header
2. Select a file from your computer
3. Fill in the metadata:
   - **Title**: Name of the document
   - **Category**: Type of document (contract, email, etc.)
   - **Description**: Optional description
   - **Tags**: Comma-separated keywords
4. Click "Upload"

### Supported File Types

- **PDF files**: Automatically converted to Markdown (if pdfplumber is installed)
- **Images**: JPG, PNG, GIF, WebP, SVG
- **Microsoft Office**: DOC, DOCX, XLS, XLSX (view only)
- **Other**: Any file type can be uploaded and stored

### Document Features

- **Thumbnail previews** for images
- **File type icons** for quick identification
- **Search and filter** by title, category, or tags
- **Link to timeline events** for context
- **Download or view** original files

### Archive Map

Hiver automatically generates an `archive_map.md` file that shows:
- Complete directory structure
- File counts
- Statistics for your archive

---

## 🤖 AI Assistant

### Overview

The AI Assistant uses Mistral AI to provide:
- **Timeline Analysis**: Query your timeline events in natural language
- **Document Analysis**: Analyze uploaded documents
- **Event Suggestions**: Get suggestions for new events based on existing data
- **Context-Aware Responses**: Answers based on your selected case and timeline

### Using the AI Assistant

1. Open the AI Assistant pane (right side of workspace)
2. Type your question or request in the input box
3. Click "Ask AI" or press Enter
4. View the formatted response with:
   - Summary
   - Key points
   - Recommendations
   - Follow-up actions

### AI Features

#### Query Timeline
Ask questions like:
- "What contracts were signed in January?"
- "Show me all court filings"
- "What deadlines are coming up?"

#### Analyze Event
Click "Ask AI About This" in an event popup to:
- Get a summary of the event
- Understand its legal significance
- Identify related documents
- Suggest follow-up actions

#### Analyze Document
Upload a document and ask the AI to:
- Summarize the content
- Extract key terms
- Identify important clauses
- Suggest related actions

#### Suggestions
Get AI-powered suggestions for:
- Missing events in your timeline
- Connections between existing events
- Important dates to track
- Missing documentation

### AI Configuration

1. Set `MISTRAL_API_KEY` in your environment variables
2. The AI will use this key for all requests
3. Without a key, the AI will show simulated responses

---

## 🔐 Authentication

### Standard Login (Username/Password)

1. Visit `/accounts/login/`
2. Enter your username and password
3. Click "Sign In"
4. You'll be redirected to the timeline view

### DID Login (Decentralized Identifier)

1. Visit `/accounts/login/`
2. Click "Sign In with DID"
3. Enter your DID (e.g., `did:example:abc123`)
4. Copy the **challenge code**
5. Sign the challenge with your DID manager
6. Paste the **signature**
7. Click "Sign In with DID"
8. You'll be authenticated and redirected

### DID Authentication Flow

```
User → Hiver (Generate Challenge)
         ↓
User ← Hiver (Challenge Code)
         ↓
User → DID Manager (Sign Challenge)
         ↓
User ← DID Manager (Signature)
         ↓
User → Hiver (DID + Signature + Challenge)
         ↓
Hiver → Rust-DID (Verify Signature)
         ↓
Hiver ← Rust-DID (Valid/Invalid)
         ↓
User ← Hiver (Authenticated/Error)
```

### Session Management

- **Session Timeout**: 2 weeks (configurable)
- **Remember Me**: Check the box to extend session
- **Logout**: Click "Logout" in the header
- **Multiple Devices**: Your session works across devices

### Security

- **HTTPS Required**: Always use HTTPS in production
- **Secure Cookies**: Session cookies are secure and HttpOnly
- **CSRF Protection**: All forms include CSRF tokens
- **Password Hashing**: Uses Django's PBKDF2 hashing

---

## 🏗️ Workspace Layout

Hiver uses a **three-pane workspace** design:

### Main Pane (Timeline) - 2/3 width
- Timeline events in vertical scrollable format
- Sticky date headers
- Event cards with hover effects
- Primary focus area

### Left Pane (Archive) - 1/3 width, Collapsible
- Document list
- Search and filter
- Document previews
- Can be collapsed to save space

### Right Pane (AI Assistant) - 1/3 width, Collapsible
- AI chat interface
- Context selection
- Response display
- Can be collapsed to save space

### Responsive Design

| Breakpoint | Layout |
|------------|--------|
| Desktop (≥1200px) | Three panes: 2fr 1fr 1fr |
| Tablet (≥900px, <1200px) | Two panes: 2fr 1fr (AI hidden) |
| Mobile (<900px) | Single column, stacked |

---

## 📝 Markdown Tutorial

Hiver uses Markdown for timeline files. Here's a guide to creating effective timelines:

### Basic Markdown Syntax

#### Headings
```markdown
# Main Heading (H1)
## Section Heading (H2)
### Subsection (H3)
#### Sub-subsection (H4)
```

#### Text Formatting
```markdown
*Italic text* or _Italic text_
**Bold text** or __Bold text__
~~Strikethrough~~
`code`
```

#### Lists
```markdown
- Bullet list item
- Another item
  - Nested item

1. Numbered list item
2. Another item
```

#### Links
```markdown
[Link text](https://example.com)
[Document](relative/path/to/document.pdf)
```

#### Images
```markdown
![Alt text](path/to/image.png)
```

### Timeline-Specific Markdown

Hiver recognizes special formats for timeline events:

#### Format 1: Simple Event
```markdown
## Contract Signed

**Date:** 2024-01-15
**Event:** Contract Execution
**Category:** contract
**Notes:** Both parties signed the agreement
```

#### Format 2: Full Event
```markdown
## Discovery Phase Begins

**Date:** 2024-02-01
**Event:** Discovery Commences
**Category:** court_filing
**Notes:** Initial discovery requests sent
**Description:** 
This marks the beginning of the discovery phase. Requests for
production of documents were sent to the opposing party.

**Supporting Docs:** [Complaint.pdf](documents/complaint.pdf), [Request for Production](documents/rfp.docx)
```

#### Format 3: Multiple Events in One File
```markdown
# Case: Smith vs. Jones

## Initial Filing
**Date:** 2024-01-15
**Category:** court_filing
**Notes:** Complaint filed

---

## First Response
**Date:** 2024-01-30
**Category:** court_filing
**Notes:** Defendant's answer filed

---

## Discovery Phase
**Date:** 2024-02-15
**Category:** deadline
**Notes:** Discovery cutoff date
```

### Tips for Effective Timelines

1. **Use Clear Names**: Give each timeline a descriptive name
2. **Start with H1**: The first H1 heading becomes the timeline title
3. **Use H2 for Events**: Each event should be an H2 heading
4. **Include Dates**: Always include a **Date:** field for proper sorting
5. **Use Categories**: Categories help filter and organize events
6. **Add Descriptions**: Use the description field for detailed information
7. **Link Documents**: Use markdown links to reference supporting documents
8. **Separate Events**: Use `---` (horizontal rule) between events for clarity

### Example: Complete Timeline File

```markdown
# Smith vs. Jones Contract Dispute

**Description:** Breach of contract lawsuit regarding software development services

---

## Contract Signed
**Date:** 2023-06-15
**Category:** contract
**Notes:** Both parties executed the agreement
**Description:** 
The original contract for custom software development was signed.
Scope: E-commerce platform with inventory management.

**Supporting Docs:** [Contract.pdf](documents/smith-jones-contract.pdf)

---

## Project Kickoff
**Date:** 2023-06-20
**Category:** meeting
**Notes:** Initial planning meeting
**Description:**
First meeting to discuss project requirements and timeline.
Attendees: Smith, Jones, development team.

---

## First Deliverable
**Date:** 2023-07-15
**Category:** deadline
**Notes:** UI wireframes due
**Description:**
Initial wireframes for the e-commerce platform were delivered.
Feedback requested by July 20.

**Supporting Docs:** [Wireframes.pdf](documents/wireframes.pdf)

---

## Mid-Project Review
**Date:** 2023-08-30
**Category:** meeting
**Notes:** Progress review meeting
**Description:**
Mid-point review of project progress. Some delays noted
in backend development.

---

## Dispute Arises
**Date:** 2023-09-15
**Category:** communication
**Notes:** Email regarding missed deadline
**Description:**
Jones sent email noting that the September 1 deadline for
backend API completion was missed.

**Supporting Docs:** [Email_2023-09-15.pdf](documents/emails/2023-09-15.pdf)

---

## Contract Termination
**Date:** 2023-10-01
**Category:** contract
**Notes:** Agreement terminated
**Description:**
Jones terminated the contract due to repeated missed deadlines.
Final payment of $10,000 withheld.

**Supporting Docs:** [Termination_Notice.pdf](documents/termination-notice.pdf)

---

## Lawsuit Filed
**Date:** 2023-11-15
**Category:** court_filing
**Notes:** Complaint filed in circuit court
**Description:**
Smith filed lawsuit against Jones for breach of contract,
seeking $50,000 in damages.

**Supporting Docs:** [Complaint.pdf](documents/complaint.pdf)
```

### Markdown Tables

```markdown
| Date | Party | Amount | Status |
|------|-------|--------|--------|
| 2024-01-15 | Smith | $10,000 | Paid |
| 2024-01-20 | Jones | $15,000 | Pending |
| 2024-02-01 | Smith | $5,000 | Overdue |
```

### Markdown Footnotes

```markdown
Here's a statement[^1] and another[^2].

[^1]: First footnote
[^2]: Second footnote
```

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `ESC` | Close popup modal |
| `Tab` | Navigate between form fields |
| `Enter` | Submit form / Send AI query |
| `/` | Focus search box (when implemented) |
| `Ctrl+F` | Browser search |
| `Ctrl+S` | Save (in forms) |

---

## 🐛 Troubleshooting

### Common Issues

#### Login Problems
- **Issue**: Can't login with username/password
- **Solution**: Create a superuser with `python manage.py createsuperuser`

#### DID Authentication Not Available
- **Issue**: "Rust-DID Not Available" message
- **Solution**: 
  1. Build the Rust-DID library: `cd rust_did && cargo build --release`
  2. Set `RUST_DID_LIB_PATH` in settings.py
  3. Set `DID_BACKEND='rust'` in settings.py
  4. Restart the server

#### Markdown Not Parsing
- **Issue**: Uploaded markdown file doesn't parse
- **Solution**: 
  1. Check file encoding (must be UTF-8)
  2. Ensure file has at least one heading
  3. Check for syntax errors
  4. Verify python-markdown is installed: `pip install markdown`

#### Documents Not Showing
- **Issue**: Uploaded documents don't appear
- **Solution**:
  1. Check if the upload completed (look for success message)
  2. Verify the file size is within limits
  3. Check if the file type is supported
  4. Restart the server

#### Case Data Not Isolated
- **Issue**: Seeing events/documents from other cases
- **Solution**:
  1. Verify you're logged in as the correct user
  2. Check that events have the correct case assigned
  3. Clear your browser cache

### Error Messages

| Message | Cause | Solution |
|---------|-------|----------|
| "Invalid or expired challenge" | DID challenge timed out | Refresh page and try again |
| "Rust-DID library not found" | Library not built | Build Rust library |
| "No file_path provided" | Missing parameter | Check API call |
| "File not found" | Incorrect path | Verify file exists |
| "NoneType has no attribute 'event'" | Event data missing | Check timeline file format |

### Browser Issues

- **Clear Cache**: If UI looks broken, clear browser cache
- **Disable Extensions**: Some extensions interfere with Hiver
- **Try Another Browser**: Test in Chrome, Firefox, Safari
- **Console Errors**: Open DevTools (F12) and check Console tab

---

## 📚 Additional Resources

- [README.md](../README.md) - Installation and setup guide
- [STYLE_GUIDE.md](../STYLE_GUIDE.md) - Design and styling specifications
- [TIMELINE_SCHEMA.md](TIMELINE_SCHEMA.md) - Timeline data structure
- [Changelog](CHANGELOG.md) - Version history and updates

---

**Last Updated**: {{ date }}
**Version**: 1.0

Need help? Check the [issues](https://github.com/byersbrands/hiver/issues) or contact support.
