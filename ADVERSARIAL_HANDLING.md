# Adversarial Source Handling & Event Categorization

## Overview
This update adds support for categorizing events as "Stipulated/Verified" or "Contested Allegations" and handling adversarial sources (OPPOSING party) in the LLM Wiki sync pipeline.

## Changes Made

### 1. Django Model Updates (`apps/core/models.py`)

**RawDocument** (already had these fields):
- `source_party`: CharField with choices CLIENT/OPPOSING/NEUTRAL
- `reliability_note`: TextField (blank=True, null=True)

**WikiPage** (new field added):
- `category`: CharField with choices VERIFIED/CONTESTED (default: CONTESTED)
- Used to track whether content is "Stipulated/Verified" or "Contested Allegation"

### 2. Prompt Templates (`apps/core/prompts.py`)

Created new file with:

**`SYNC_PROMPT_TEMPLATE`**:
- Instructs LLM to categorize events into two buckets
- Extracts: text, category, source_party, date, citation
- Handles adversarial sources (OPPOSING)
- Outputs JSON array of events/claims

**`CROSS_EXAMINATION_PROMPT`**:
- System prompt for AI Assistant (3rd pane)
- Prioritizes Verified sources
- Requires disclaimers for adversarial sources
- Never states contested claims as objective facts

**`ADVERSARIAL_DISCLAIMER_TEMPLATES`**:
- Templates for labeling based on source_party
- OPPOSING: "The opposing party alleges: {text}"
- CLIENT: No disclaimer
- NEUTRAL: "According to the document: {text}"

### 3. Utility Functions (`apps/core/utils.py`)

Created new file with:

**`apply_adversarial_labeling()`**:
- Modifies LLM response based on source_party
- Adds disclaimers for OPPOSING sources
- No changes for CLIENT sources
- Adds "According to document" for NEUTRAL sources

**`categorize_event()`**:
- Categorizes events as VERIFIED or CONTESTED
- Simple heuristic: CLIENT=VERIFIED, OPPOSING=CONTESTED
- Can cross-reference with existing verified events

**`check_for_contradictions()`**:
- Checks if new events contradict existing events
- Placeholder for NLP/LLM-based contradiction detection

### 4. Updated Tasks (`apps/core/tasks.py`)

**`sync_document_to_wiki()`**:
- Now uses `SYNC_PROMPT_TEMPLATE`
- Calls LLM with document text + existing wiki content
- Parses JSON response
- Applies adversarial labeling via `apply_adversarial_labeling()`
- Saves to WikiPage with category field
- Calls `detect_contradictions()` after sync

**`detect_contradictions()`**:
- Compares WikiPages for same case
- Simple contradiction detection (conflicting dates, statements)
- Logs to `media/wiki/{case_id}/contradictions.md`

### 5. Rust Updates (`rust_did/src/lib.rs`)

Updated `WikiPage` struct to include:
```rust
pub category: String,  // "VERIFIED" or "CONTESTED"
```

## Usage

### Syncing a Document
```python
from apps.core.tasks import task_sync_raw_document

# Queue a document for sync
task_sync_raw_document.delay(str(raw_doc.id))
```

### Manual Sync (for testing)
```python
from apps.core.tasks import sync_document_to_wiki

result = sync_document_to_wiki(str(raw_doc.id))
print(result)
```

### Checking Contradictions
```python
from apps.core.tasks import detect_contradictions

contradictions = detect_contradictions(str(case.id))
print(f"Found {len(contradictions)} contradictions")
```

## File Structure
```
apps/core/
├── models.py          # Updated: WikiPage.category field
├── prompts.py        # NEW: Sync & cross-examination prompts
├── utils.py          # NEW: Adversarial labeling utilities
├── tasks.py          # Updated: Sync with categorization
└── migrations/
    └── 0003_add_category_to_wikipage.py  # NEW migration

rust_did/src/
└── lib.rs            # Updated: WikiPage struct with category
```

## Migration
```bash
# Apply the migration for WikiPage.category field
cd /home/user/CODE_BASE/hiver_django
uv run python manage.py migrate core 0003 --fake
```

## Testing
```bash
# Run the test script
uv run python test_sync_pipeline.py

# Check for contradictions manually
cat media/wiki/{case_id}/contradictions.md
```

## Notes
- The `source_party` field already existed in RawDocument with correct choices
- The `reliability_note` field already existed in RawDocument
- New `category` field defaults to CONTESTED for backward compatibility
- Contradiction detection is currently simple (placeholder) - enhance with NLP/LLM in production
- Adversarial labeling helps users distinguish between verified facts and contested claims
