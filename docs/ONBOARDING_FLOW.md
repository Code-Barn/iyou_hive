🐝 HIVER: Project Sovereign Onboarding Brief
1. Project Identity
Hiver is a Legal Digital Twin platform designed for forensic case management. It is built to bridge the gap between structured database intelligence and the 2026 courtroom standard (5-column printed PDFs).

2. The Sovereign UI Dictate (The "Anchor")
The app strictly adheres to a 3-panel workspace that must remain in focus at all times. All secondary workflows must occur in Modals (Popups) to prevent context switching.

Left Panel (20-25%): Timeline. A high-density, chronological pulse of the case.

Center Panel (50-60%): The Archive/Canvas. This is the powerhouse. It contains the File Tree, the Document Preview (PDF/MD), and the Drafting Canvas.

Right Panel (20-25%): AI Assistant. The forensic co-pilot for research and classification.

Key Feature: Every panel must have Expand/Collapse toggles.

3. Technical Stack
Backend: Django (Python 3.10+) utilizing a PostgreSQL database.

Frontend: React (TypeScript) powered by Vite.

Data Standard: Strictly uses 5-Column Markdown (| Date | Event | Category | Evidence | Notes |) for all imports/exports and PDF generation.

Forensic Layer: Relational Truth Graph using UUIDs for all cases, documents, and events.

4. Recent Victories (Already Implemented)
The Identity Bridge: Monkey-patched the Django User model to support forensic UUID properties.

The Asset Manifest: Implemented a dynamic Vite manifest loader in Django to prevent 404/MIME errors.

The State-Switch Parser: A sophisticated Markdown parser that treats ## headers as logical "chapters" without polluting the event text.

AI Smart Attribution: A classification service that detects names (e.g., "David" vs "Pauletta") to automatically attribute events to CLIENT, OPPOSING, or NEUTRAL.

5. Immediate Roadmap for the Next Agent
[ ] Finalize the "Anchor" Layout: Ensure Layout.tsx perfectly renders the 3 panels with the Archive in the center.

[ ] Resolve Circular Dependencies: Maintain strict isolation between FileTree.tsx and Layout.tsx using a shared types/shared.ts file.

[ ] Implementation of Citation Maps: Update legal_formatter.py to generate JSON manifests mapping Event UUIDs to PDF Page/Row numbers.

[ ] k3s Hardening: Prepare Kubernetes Secrets for sensitive keys and Persistent Volume Claims (PVCs) for the /formal/ and /private/ vaults.

6. Critical Warnings for the Machine
Never Assume Layout: The user’s design is sovereign. Timeline=Left, Archive=Center, AI=Right.

No String Prepending: Do not smash metadata into event titles. Metadata belongs in model fields, not the text strings.

Strict Scoping: Every API call must be filtered by case_uuid and user_id. There is no "Global" view in Hiver.
