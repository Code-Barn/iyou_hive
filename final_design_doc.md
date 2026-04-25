Hiver: Final Design Document
Codename: Hiver

Purpose: A self-hosted, federated app for interactive legal timelines, document archiving, and AI-assisted research.

1. Core Features (Refined)
A. Vertical Scrolling Timeline

Schema:

Required Fields: Date, Event/Incident, Category, Supporting Document(s), Notes
Markdown Example:
markdown
Copy

---
title: "Legal Case Timeline"
---
# 2023-01-15
**Event:** Contract Signed
**Category:** Contracts
**Supporting Docs:** [Link to PDF]
**Notes:** Signed with X Corp. Review by 2023-02-01.





Design:

Dark Mode (Default): Charcoal background (#1A1A1A), honey-orange accents (#FF8C00), white text.
Light Mode: Off-white background (#F5F5F5), dark text, honey-orange highlights.
Timeline Line: #FF8C00 (honey-orange).
Event Dots: #0064AA (Byers blue).

B. Legal Document Archive

Storage: PostgreSQL (default) or IPFS.
Processing:

PDF → Markdown (using your script).
Auto-tagging for categories (e.g., “Contracts,” “Emails”).

C. Message/Conversation Integration

Features:

Upload iMessage/email logs → chronological JSON/PDF.
Alias support for contacts (e.g., “John Doe” = “JD,” “Johnny”).

D. AI Research Assistant (Placeholder)

Default Model: Mistral (API key placeholder in settings).
Interface:

Sidebar chat for queries (e.g., “Summarize this contract”).
Output: Suggested timeline events or notes.

E. Polly Compatibility

Future Use Case:

Collaborators can upvote/downvote/comment on timeline entries.
Scope: Limited to shared “hives” (user-invited groups).

Integration:

Embeddable Polly widgets for timeline entries.
Credential-based access (via Rust-DID).


2. Technical Stack (Updated)


  
    
      Component
      Technology
      Notes
    
  
  
    
      Backend
      Django 4.0+
      Follow namechart-style-guide.md.
    
    
      Database
      PostgreSQL/IPFS
      User choice.
    
    
      Frontend
      Django Templates + JS
      Tailwind CSS (honey-orange palette).
    
    
      Auth
      Rust-DID (FFI)
      Shared with Polly/Namechart.
    
    
      AI Integration
      Mistral API (placeholder)
      Configurable for other models.
    
    
      Polly
      Embeddable widgets
      Future: Protocol-based federation.
    
  



3. App Structure
text
Copy

hiver/
├── apps/
│   ├── core/          # Shared templates/static (honey-orange theme)
│   ├── timeline/      # Timeline models/views
│   ├── archive/       # Document processing
│   ├── messages/      # Conversation logs
│   └── ai_assistant/  # Mistral API integration
├── rust_did/          # Pre-built module
├── static/            # CSS/JS (Tailwind)
└── templates/         # Base templates (light/dark mode)




4. Workflow (Visual)

Upload Timeline MD → Rendered as interactive vertical line.
Upload Docs/Messages → Processed into timeline events.
AI Assistant → Suggests additions or analyzes docs.
Export → Printable PDF or federated link.

5. Open Questions (Revisited)

Timeline Schema: Standardized as above (printable + machine-readable).
AI: Mistral placeholder; API key config in settings.py.
Polly: Compatible by design; widgets for future collaboration.
Federation: Protocol-ready architecture (future phase).

6. Next Steps

Finalize README.md for Senior Dev (setup, DID workflows, color codes).
Draft API Specs for:

Timeline MD parsing.
AI assistant prompts.
Polly widget embedding.

Build Prototype of timeline + AI sidebar (honey-orange theme).

7. Logo & Color Palette

Primary: Honey-Orange (#FF8C00)
Accent: Byers Blue (#0064AA)
Dark Mode: Charcoal (#1A1A1A) + White
Light Mode: Off-White (#F5F5F5) + Dark Text
