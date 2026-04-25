# Hiver: Legal Timeline & Document Archive

**Codename:** Hiver
**Purpose:** A self-hosted, federated app for interactive legal timelines, document archiving, and AI-assisted research.

## Overview
Hiver is designed to merge a vertical scrolling interactive timeline with a legal file archive. It integrates with the Byers Brands ecosystem, using Rust-DID for authentication and Polly for collaborative features. The app supports self-hosting, federation, and decentralized logins.

## Core Features
1. **Vertical Scrolling Timeline**
   - Upload and parse Timeline Markdown files.
   - Render events as clickable points on a vertical line.
   - Standardized schema: `Date`, `Event/Incident`, `Category`, `Supporting Document(s)`, `Notes`.

2. **Legal Document Archive**
   - Upload and store legal documents (PDFs, emails, messages).
   - Automated processing: PDF to Markdown, message logs to JSON/PDF.

3. **AI Research Assistant**
   - Default integration with Mistral AI.
   - Configurable for other AI models via API keys.
   - Chat interface for document analysis and timeline suggestions.

4. **Polly Compatibility**
   - Embeddable widgets for collaborative feedback on timeline entries.
   - Future use case: Collaborators can upvote/downvote/comment on entries.

5. **Federation-Ready Architecture**
   - Protocol-based federation for future compatibility.

## Technical Stack
- **Backend:** Django 4.0+
- **Database:** PostgreSQL (default), IPFS
- **Frontend:** Django Templates, JavaScript, Tailwind CSS
- **Authentication:** Rust-DID (shared module)
- **AI Integration:** Mistral API (configurable)
- **Collaboration:** Polly embeddable widgets

## App Structure
```
hiver/
├── apps/
│   ├── core/          # Shared templates and static files
│   ├── timeline/      # Timeline models and views
│   ├── archive/       # Document processing logic
│   ├── messages/      # Conversation log processing
│   └── ai_assistant/  # AI integration logic
├── rust_did/          # Rust-DID authentication module
├── static/            # CSS and JavaScript files
└── templates/         # Base templates for light/dark mode
```

## Workflow
1. Upload a Timeline Markdown file.
2. Hiver renders an interactive vertical timeline.
3. Upload legal documents or message logs.
4. Hiver processes and integrates them into the timeline.
5. Use the AI assistant for analysis and suggestions.
6. Export or share the timeline and documents.

## Design
- **Color Palette:**
  - Primary: Honey-Orange (`#FF8C00`)
  - Accent: Byers Blue (`#0064AA`)
  - Dark Mode: Charcoal (`#1A1A1A`) background with white text
  - Light Mode: Off-white (`#F5F5F5`) background with dark text

## Next Steps
1. Set up the Django project structure.
2. Implement the Rust-DID authentication module.
3. Develop the timeline rendering logic.
4. Integrate the AI assistant placeholder.
5. Ensure compatibility with Polly widgets.

## License
This project is part of the Byers Brands ecosystem and follows the same licensing terms.