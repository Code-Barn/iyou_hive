# Sync Pipeline Implementation

## Overview
This implementation provides a 3-Layer Architecture (Raw → Wiki → Schema) sync pipeline for the Hiver Django application, with Rust-powered document processing.

## Architecture Layers

### Layer 1: Raw (RawDocument)
- **Django Model**: `RawDocument` in `apps/core/models.py`
- **Fields**: UUID, case FK, FileField, file_type, source_party, document_type, reliability_note, uploaded_at, is_immutable
- **Immutability**: Overrides save() to prevent updates if `is_immutable=True`
- **File Storage**: `/media/raw/{case_id}/`

### Layer 2: Wiki (WikiPage)
- **Django Model**: `WikiPage` in `apps/core/models.py`
- **Fields**: UUID, case FK, title, content, last_updated, version_history (JSON), citation_references (JSON)
- **Version History**: Automatically maintains history in save()
- **File Storage**: `/media/wiki/{case_id}/`

### Layer 3: Schema (SchemaRule)
- **Django Model**: `SchemaRule` in `apps/core/models.py`
- **Fields**: UUID, case FK, rule_name, rule_description, rule_content
- **Purpose**: Stores rules for LLM formatting

## Rust Implementation

### Modules
1. **`src/lib.rs`**: Main library with RawDocument/WikiPage structs and `extract_to_markdown()`
2. **`src/sync.rs`**: Sync pipeline - extraction, saving to wiki layer
3. **`src/llm.rs`**: LLM integration for wiki synthesis (trait + implementations)
4. **`src/lint.rs`**: Contradiction detection in wiki files

### Key Functions
- `extract_raw_to_markdown()`: Convert PDF/MD/JSON to normalized Markdown
- `save_to_wiki_layer()`: Save extracted content to wiki directory
- `synthesize_wiki_update()`: Use LLM to update wiki with citations
- `lint_wiki_for_contradictions()`: Detect conflicting claims
- `sync_raw_document()`: Full pipeline orchestrator

## Usage

### Running the Sync Pipeline

#### Option 1: Via Celery Task (Recommended)
```python
from apps.core.tasks import task_sync_raw_document

# Queue a document for sync
task_sync_raw_document.delay(str(raw_doc.id))
```

#### Option 2: Via Rust Binary
```bash
cd rust_did
cargo build --release

# Run sync
./target/release/sync_binary '{"id":"...", "case_id":"...", "file_path":"...", ...}'
```

### LLM Client Configuration

In `config/settings.py`:
```python
LLM_BACKEND = 'ollama'  # or 'gemini', 'mock'
OLLAMA_ENDPOINT = 'http://localhost:11434'
OLLAMA_MODEL = 'llama2'
# OR
GEMINI_API_KEY = 'your-api-key'
GEMINI_MODEL = 'gemini-2.5-flash'
```

## File Structure
```
/media/
  /raw/
    /{case_id}/
      (original PDFs, .md, .json)
  /wiki/
    /{case_id}/
      (timeline.md, witness_list.md, etc.)
      contradictions.md
```

## Testing

### Run Tests
```bash
# Rust tests
cd rust_did && cargo test

# Python/Django tests
uv run python test_sync_pipeline.py
```

## Dependencies

### Rust (`rust_did/Cargo.toml`)
- `serde`, `serde_json`: Serialization
- `regex`: Contradiction detection
- `chrono`: Timestamps
- `tokio`: Async LLM calls
- `log`: Logging

### Python
- `celery`: Async task processing
- `requests`: HTTP calls to LLM APIs
- `django`: Web framework

## Future Enhancements
1. Implement actual PDF extraction (using `pdf-extract` crate)
2. Add PyO3 bindings for direct Python-Rust FFI
3. Implement real LLM clients (Ollama, Gemini, Mistral)
4. Add more sophisticated contradiction detection
5. Add sync status tracking to RawDocument model
6. Implement rollback functionality for failed syncs

## Notes
- The `/media` directory needs to be created and writable by the application
- Ensure Rust is compiled before running Python integration
- Configure Celery broker (Redis/RabbitMQ) for async tasks
