# Hiver Roadmap 2026

**The New Vision: From Private Litigation to Public Accountability**

> "Hiver is not just a database; it is a Git-inspired **Version Control for Reality.** Every feature must respect the boundary between Private Strategy and Formal Evidence."

---

## 🎯 2026 Vision Statement

Hiver's ultimate goal: **A portable, uncancelable, and transparent record of truth that can be used by a single individual or an entire community.**

**Core Principle:** The Truth is not a single line; it is a graph of verified claims.

---

## 📋 Strategic Goals from NEW_VISION.md

### 1. The "Interested Third-Party" Framework

**Goal:** Expand Hiver from a tool for named parties (Petitioner/Respondent) to support third parties documenting truth from the outside.

**Implementation Plan:**

#### Q2 2026: Researcher Role
- [ ] Add "Researcher" user type with read-only access to Formal Vault
- [ ] Create third-party workspace isolated from named parties
- [ ] Implement "Shadow Hive" concept for third-party archives

#### Q3 2026: Granular Public Toggles
- [ ] Add "Switch to Public" mode for Formal Vault
- [ ] Implement public/private visibility toggles per document
- [ ] Create public-facing timeline view (no authentication required)

#### Q4 2026: Gift Protocol
- [ ] Mechanism to transfer ownership of third-party Hive to named legal party
- [ ] Export/import with ownership transfer
- [ ] Audit trail for ownership changes

**Current UI Mapping:**
- **CaseDetailModal** - Already has Vault Badges showing Formal/Private distinction
- **FileTree** - Shows Vault (Shared) and Workspace (Private) folders
- **Stipulated Magnet** - Gold Seal indicator for system sources (courts/neutral parties)

---

### 2. Identity Verification & The "Claim" System

**Goal:** Support multi-owner Hives with cryptographic identity verification.

**Implementation Plan:**

#### Q1-Q2 2026: Identity Verification Service
- [ ] Hook for digital ID/signature verification
- [ ] Integrate with existing Rust-DID library
- [ ] Add DID-based authentication flow
- [ ] Store verified identities in user profiles

#### Q3 2026: Verified Counter-Claims
- [ ] "On-Ramp" for opposing party to prove identity
- [ ] Claim their role in existing Hive
- [ ] Multi-party identity verification UI

#### Q4 2026: Joint Ownership Locks
- [ ] **M-of-N Shredder Logic** (CRITICAL)
  - Once Hive has two verified opposing owners
  - Shredder undergoes state change
  - Deletion of shared `/formal/` vault requires M-of-N authorization
  - Both parties must sign off to prevent evidence destruction

#### Q1 2027: Sovereign Ejection
- [ ] Party can "Eject" - export full .hive bundle
- [ ] Revoke shared instance's access to their private workspace
- [ ] Preserve Formal Vault for remaining parties

**Current UI Mapping:**
- **CaseDetailModal** - Shows case ownership information
- **Vault Badges** - Visual distinction between shared and private
- **Stipulated Magnet (Gold Seal)** - Indicates court/neutral authority sources

---

### 3. The "Rashomon" Public Interface

**Goal:** For high-profile cases, enable collaborative discovery with public participation.

**Implementation Plan:**

#### Q3 2026: Crowdsourced Evidence
- [ ] Public staging area for proposed evidence
- [ ] Hive Owner (Researcher or Party) acts as moderator
- [ ] "Promote" mechanism for valid submissions to Formal Vault
- [ ] Public submission form with document upload

#### Q4 2026: Whistleblower On-Ramps
- [ ] Secure, anonymous drop-boxes within a Hive
- [ ] Document upload triggers AI Assistant automatically
- [ ] AI searches for contradictions in existing Master Timeline
- [ ] Protect whistleblower identity (no authentication required)

#### Q1 2027: Public Polling API
- [ ] Integration with polling app
- [ ] Vote on "Probability of Fact" for contested timeline events
- [ ] Weight votes based on user reputation/trust level
- [ ] Display polling results alongside timeline events

**Current UI Mapping:**
- **CaseDetailModal** - Ingestion tab for document upload (foundation for public submission)
- **Vault Badges** - Formal Vault = public-ready, Private = hidden
- **Stipulated Magnet** - System sources cannot be contested without evidence

---

### 4. Generalized Subject Timelines

**Goal:** Transition from strictly "Legal" tool to "Human History" tool.

**Implementation Plan:**

#### Q2 2026: Modular Schema
- [ ] Allow users to swap "Legal" categories for "Historical" or "Investigative"
- [ ] Configurable category taxonomies
- [ ] Per-case schema selection

**Category Mapping:**
```
Legal Categories:
- Motion, Hearing, Discovery, Contract, Email, Court Filing

Historical Categories:
- Sighting, Financial Transaction, Interview, Document, Event

Investigative Categories:
- Lead, Evidence, Interview, Surveillance, Report
```

#### Q3 2026: Community Archiving
- [ ] Empower neighborhoods/groups to create Hives for local events
- [ ] "Conflict Resolver" to manage different memories of same incident
- [ ] Community ownership models

**Current UI Mapping:**
- **ForensicTimeline** - Already supports configurable categories
- **TimelineEventModal** - Category selection dropdown
- **Stipulated Magnet** - Can be extended to community-verified facts

---

### 5. The "Gold Seal" Immutable Ledger

**Goal:** Move Gold Seal from database flag to cryptographic proof.

**Implementation Plan:**

#### Q4 2026: Evidence Hashing
- [ ] Every document promoted to Vault gets hash recorded
- [ ] Hash stored in blockchain-like structure (Merkle tree)
- [ ] Even if file moved between servers via Portability Engine, Gold Seal remains valid
- [ ] Mathematical proof of file integrity

#### Q1 2027: Court-Linked API
- [ ] Hiver pulls data directly from court dockets via API
- [ ] Automatic population of "Stipulated" facts with highest trust_level
- [ ] No human intervention required for court records
- [ ] Periodic sync with court systems

**Current UI Mapping:**
- **Gold Seal Badge** (🏆) - Already displays on EventCard for system sources
- **Trust Level Display** - Shows 1-5 stars with descriptions
- **has_gold_seal property** - Computed from is_system_source + STIPULATED status

---

## 🗺️ Implementation Timeline

### Q1 2026 (Current Quarter)
**Theme: Foundation & Stability**

- [x] Complete React migration (DONE)
- [x] Fix 405 Upload Error (DONE)
- [x] Update documentation (DONE)
- [ ] Add automated test suite for API endpoints
- [ ] Implement Identity Verification Service (DID integration)
- [ ] Add M-of-N Shredder Logic for multi-owner cases

### Q2 2026
**Theme: Third-Party Support**

- [ ] Researcher user type
- [ ] Shadow Hive implementation
- [ ] Modular schema for non-legal use cases
- [ ] Public/Private toggle (basic)

### Q3 2026
**Theme: Collaborative Features**

- [ ] Granular public toggles
- [ ] Crowdsourced evidence staging
- [ ] Whistleblower drop-boxes
- [ ] Community archiving support
- [ ] Verified counter-claims

### Q4 2026
**Theme: Cryptographic Integrity**

- [ ] Evidence hashing for Gold Seal
- [ ] Gift Protocol for ownership transfer
- [ ] Joint Ownership Locks
- [ ] Public Polling API integration

### Q1 2027
**Theme: Version Control for Reality**

- [ ] Court-Linked API
- [ ] Sovereign Ejection
- [ ] Full M-of-N implementation
- [ ] Cross-Hive citation linking

---

## 🏗️ Current Architecture Mapping to Goals

### UI Components → Vision Features

| Current UI Element | Maps To | Vision Feature |
|-------------------|---------|----------------|
| `CaseDetailModal` with Vault Badges | ✅ | Formal/Private distinction |
| `FileTree` with Vault/Workspace | ✅ | Shadow Hive foundation |
| Gold Seal (🏆) on EventCard | ✅ | Cryptographic proof foundation |
| `Stipulated Magnet` (system sources) | ✅ | Court-Linked API foundation |
| `TimelineEventModal` with categories | ✅ | Modular Schema foundation |
| `CaseDetailModal` Ingestion tab | ✅ | Whistleblower on-ramp foundation |
| `ConflictResolverModal` | ✅ | Community conflict resolution |

### Data Models → Vision Features

| Current Model | Maps To | Vision Feature |
|--------------|---------|----------------|
| `ArchiveDocument` with is_promoted | ✅ | Gate Logic / Shadow Hive |
| `TimelineEvent` with trust_level | ✅ | Public Polling / Gold Seal |
| `Case` with user ownership | ✅ | Multi-owner / M-of-N |
| `HiveDirectoryService` | ✅ | Version Control for Reality |
| `.hive bundle format` | ✅ | Portable truth records |

### API Endpoints → Vision Features

| Current Endpoint | Maps To | Vision Feature |
|----------------|---------|----------------|
| `/api/archive/documents/upload/` | ✅ | Whistleblower ingestion |
| `/api/archive/documents/promote/` | ✅ | Crowdsourced evidence promotion |
| `/api/timeline/events/` | ✅ | Community timeline building |
| `/ai/api/analyze-document/` | ✅ | Contradiction detection |

---

## 🎯 2026 Success Metrics

### Quantitative Goals
- **Q2**: 100 third-party Hives created (Researcher role)
- **Q3**: 500 public timeline views per day
- **Q4**: 1000 verified users with DID authentication
- **Q4**: 5 high-profile cases using Rashomon interface

### Qualitative Goals
- [ ] "Journalists can document corruption cases without fear of evidence loss"
- [ ] "Communities can collaboratively build timelines of local events"
- [ ] "Opposing parties can verify each other's identity and collaborate fairly"
- [ ] "Court records automatically populate with cryptographic proof"

---

## 📚 Technical Debt & Cleanup

### High Priority (Blockers)
- [ ] Fix all legacy URL conflicts (405 errors)
- [ ] Remove duplicate markdown parsing code
- [ ] Consolidate authentication flows (DID vs Session)

### Medium Priority
- [ ] Implement proper error handling in API views
- [ ] Add caching for parsed markdown files
- [ ] Optimize database queries with select_related/prefetch_related

### Low Priority
- [ ] Clean up redundant code in conversation_logs app
- [ ] Update all tests to use new React frontend
- [ ] Add TypeScript types for all backend models

---

## 🔒 Sovereign Rules (Non-Negotiable)

1. **No UI Code Changes** - Documentation must match current state
2. **UUID Stability** - All records preserve UUIDs across export/import
3. **Data Compartmentalization** - Strict separation of Formal Vault and Private Workspace
4. **Cryptographic Integrity** - All evidence must have verifiable hashes
5. **Portability** - .hive bundles must be server-agnostic

---

## 📖 References

- **Source**: [NEW_VISION.md](../NEW_VISION.md) - Original vision document
- **Related**: [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Technical architecture
- **Related**: [PROJECT_STATE.md](./PROJECT_STATE.md) - Current implementation status

---

**Document Created**: 2026-05-08  
**Vision Source**: NEW_VISION.md  
**Status**: Active Roadmap  
**Next Review**: 2026-06-01
