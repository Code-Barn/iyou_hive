Technical Proposal: Transitioning to an "LLM Wiki" Architecture
Objective: Replace stateless Retrieval-Augmented Generation (RAG) with a persistent, compounding Knowledge Base for legal case management. 
1. The Core Philosophy: "The Compiler Analogy"
In standard RAG, we treat documents as data to be searched. In the LLM Wiki pattern, we treat raw documents (PDFs, iMessages) as source code and the Wiki as the compiled binary. 
    • Ingestion (Compile Time): When a file is "synced," the LLM reads it and updates a structured set of Markdown files (the Wiki). 
    • Query (Run Time): The AI assistant reads the Wiki first to answer questions, ensuring it has the "big picture" context of the case. 
2. Proposed Architecture (Django + Rust + LLM)
We will maintain the existing 3-pane UI but reorganize the backend data flow into a 3-Layer Architecture. 
Layer	Component	Description
Layer 1: Raw	Rust/Django Storage	Immutable "source of truth" (Original PDFs + Machine-readable .md/.json).
Layer 2: Wiki	LLM-Maintained Markdown	A folder of interlinked .md files (e.g., timeline.md, witness_list.md, evidence_links.md).
Layer 3: Schema	CLAUDE.md / Instructions	The "Rulebook" that tells the LLM how to format the Wiki and what entities to track.
3. The "Sync" Pipeline (Technical Specs)
    1. Extraction (Rust): High-speed OCR and conversion of raw files to normalized Markdown.
    2. Synthesis (LLM Agent): Instead of just indexing, an agent (via Ollama or API) performs an Incremental Update:
        ◦ Reads the new document.
        ◦ Reads relevant existing Wiki pages.
        ◦ Updates summaries, appends to the timeline, and creates new "Entity Pages" for people or organizations. 
        ◦ Crucial: Every update must include a citation back to the Layer 1 source file. 
    3. Linting (Maintenance): Periodically, a "Lint" task runs to check for contradictions between Wiki pages (e.g., "Witness A said X on Tuesday, but Witness B says A was at Y"). 
4. Why This Wins for Legal Tech
    • Contextual Persistence: The AI doesn't "forget" the case details between chat sessions. 
    • Auditability: Senior devs and lawyers can open the wiki/ folder and manually verify or edit the AI's "understanding" of the case.
    • Multi-Tenancy: We scope the Wiki to the case_id. There is zero risk of data leakage because the LLM only ever "sees" the folder belonging to that specific case.
    • Reduced Hallucination: By forcing the LLM to write down its findings in a structured Wiki, we catch logic errors during the "Compile" phase rather than during a live chat with a user.

Suggested First Step for Devs
Before refactoring the whole app, create a single "Case Folder" with a /raw and /wiki sub-directory. Manually run Karpathy's "LLM Wiki" prompt (from his April 2026 Gist) against a set of 5 related case documents using a high-context model.
If the resulting timeline.md and witness_list.md look like something a junior associate would spend 10 hours writing, you know the architecture is solid.
Quick question for your devs: Are we comfortable using pgvector as a hybrid—using the Wiki for reasoning, but keeping the vector index for finding "needle in a haystack" quotes in 1,000+ page transcripts?




Me: haven't passed that on yet but i have one more question about implementation. i'm sure this is solvable but i could use your advice on the best way to do it. so for example in the case i'm working on right now i know that the documents submitted by the other party are full of misrepresentations. in parsing documents and building the legal timeline which is a main feature of this project, how do i tell the agent to treat motions/responses filed by the other side "with a grain of salt"

Agent:
This is a classic "Conflict of Truth" problem in legal data engineering. In a standard RAG system, the AI treats all text as equally true. In the LLM Wiki model, you handle this by introducing Source Metadata and Adversarial Labeling.
Since you are already standardizing your library into machine-readable formats, you have the power to "tag" the data before the AI ever reads it.
1. The "Source Bias" Metadata Tag
When your user uploads a document, your UI should require (or intelligently guess) the Originating Party. In your Django database and your Markdown "Raw" files, you prepend a header that sets the "vibe" for the LLM.
Example Raw Markdown Header:
Markdown
---
document_id: 2026-CV-001
source_party: DEFENDANT (Adversarial)
document_type: Motion to Dismiss
reliability_note: Contains contested allegations.
---
2. The "Dual-Timeline" Strategy
Instead of one single timeline.md, have your "Compiler" agent maintain a Contested Timeline.
Your prompt to the LLM during the "Sync" phase should be:
"Analyze this document. For every event found, categorize it into one of two buckets:
    1. Stipulated/Verified: (e.g., The date a contract was signed, court filing dates).
    2. Contested Allegations: (e.g., 'The Defendant claims the Plaintiff was late').
If the source is 'Adversarial,' cross-reference it against existing 'Verified' events and flag any Discrepancies in the contradictions.md file."
3. "Cross-Examination" Prompts
In your 3rd-pane AI Assistant, you modify the system prompt to reflect the reality of litigation. You give the agent a "skeptical" persona.
System Prompt Instruction:
"When answering questions, prioritize facts from Verified sources. If you cite an Adversarial source, you MUST use phrases like 'The [Party] alleges...' or 'According to the contested filing...'. Do not state adversarial claims as objective facts."

4. Technical Implementation (The "Salt" Filter)
Since you are using Rust, you can bake this logic into your ingestion script.
    1. Party Mapping: Create a simple lookup in Django: Party A = Client, Party B = Opposing.
    2. Visual Indicators: In your Timeline (Pane 1), color-code the events. Green for your docs, Red for theirs.
    3. The "Grain of Salt" Weight: If you use vector search, you can actually "boost" the importance of your own documents in the search results and "bury" the opposing party’s claims unless they are specifically asked for.
Summary for your Senior Devs:
To handle misrepresentations, we aren't just indexing text; we are indexing Claims. By adding a source_party attribute to our document metadata, we allow the LLM Wiki to act as a "Fact Checker." The Wiki doesn't just store what happened; it stores who said it happened, which is the cornerstone of legal reasoning.
