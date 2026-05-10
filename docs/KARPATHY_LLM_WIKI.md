Karpathy's LLM Wiki is a design pattern for a self-organizing, personal knowledge base that Andrej Karpathy first described in a viral GitHub Gist in April 2026. 
Instead of traditional Retrieval-Augmented Generation (RAG), which searches through chunks of raw documents only when you ask a question, the LLM Wiki pattern treats the AI as a "compiler". It takes raw source materials—like PDFs, research papers, and notes—and proactively "compiles" them once into a structured, interlinked collection of Markdown files. 
Core Architecture
The system is typically structured into three layers: 

    Raw Sources: A read-only folder containing your original PDFs, articles, and meeting notes.
    The Wiki: A folder of AI-generated Markdown files (the "executable") where the LLM maintains concept pages, entity summaries, and an index.
    Schema (Maintenance): A set of rules (often a CLAUDE.md file) that instructs the AI agent on how to structure the wiki, link concepts, and handle new information. 

Key Benefits over RAG

    Compounding Knowledge: In traditional systems, the AI "forgets" the hard work of synthesizing data after every prompt. In the wiki pattern, knowledge accumulates as new sources update existing pages.
    Networked Thought: Because the LLM cross-references and links related ideas with Obsidian-style [[wikilinks]], it can identify connections across different documents that a simple search might miss.
    Self-Healing: The pattern includes a "linting" operation where the AI checks for contradictions, stale claims, or missing references to keep the knowledge base current.
    Human-Readable: Unlike a vector database, the final product is a folder of plain text files you can browse manually in tools like Obsidian. 

Operations
A functional LLM Wiki typically runs three main operations: 

    Ingest: Drop a new source in; the AI updates related wiki pages and adds new ones.
    Query: Ask the AI a question; it reads the wiki and files the answer back into the system so it "remembers" the answer for next time.
    Lint: Automated checks to clean up doubtful information or fix broken links. 

Community implementations have already emerged, such as the open-source llm_wiki desktop app, which turns these principles into a concrete tool.
