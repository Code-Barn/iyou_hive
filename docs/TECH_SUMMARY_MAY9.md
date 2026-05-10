Hiver — Technical Summary for Developers**

Hiver is a forensic case management platform with a **React 18 + Vite 5 + Tailwind CSS 3** frontend (TypeScript) and a **Django 5.2 + DRF** backend, served as a SPA via Django templates.

**Architecture:** 3-panel layout (Timeline | Archive+Canvas | AI Assistant), draggable dividers with elastic proportional expansion. Strict white theme. Panel state persisted in localStorage.

**Data Model — 3-Layer Wiki Architecture:**
- **Layer 1:** `RawDocument` — immutable uploaded evidence (PDF, Markdown, JSON)
- **Layer 2:** `WikiPage` — normalized, versioned content with citation references
- **Layer 3:** `SchemaRule` — LLM formatting rules for structured output

**Key features:** Shared Magnet (Gate Logic for promoting/demoting evidence between Formal Vault and Private Workspace), 5-column Markdown timeline parser, Trust Level system (1-5 with Gold Seal at Level 5), .hive bundle export/import (tar.gz with UUID-stable relationships).

**Backend apps:** `core` (cases, wiki models), `timeline` (events, parsing), `archive` (documents, file tree), `ai_assistant` (LLM chat), `accounts` (auth incl. DID login).

**API highlights:** ~15+ endpoints across cases, timeline events, archive CRUD + promote/demote/move, AI analysis. JWT auth via SimpleJWT.

**LLM integration:** Ollama (local) + Google Gemini via `google-genai` package.

**Build:** `cd frontend && npm run build` outputs to `static/frontend/assets/` with content-hashed filenames. Dev: `npm run dev` (Vite HMR).

**Key docs:** `docs/DEVELOPER_GUIDE.md` (720 lines, full architectural reference), `docs/PROJECT_STATE.md` (current status + verification checklist).
