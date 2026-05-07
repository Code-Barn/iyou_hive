HIVER ARCHITECTURE GAP REPORT**
*Deep Diagnostic vs Source of Truth*

---

---

## **✅ PRESENT & VERIFIED**

### **1. Truth Graph Model** (`apps/timeline/models.py`)
All required fields and validations **EXIST**:

| Field/Method | Status | Details |
|-------------|--------|---------|
| `status` | ✅ | Includes STIPULATED in STATUS_CHOICES |
| `is_system_source` | ✅ | BooleanField, default=False |
| `trust_level` | ✅ | PositiveSmallIntegerField (1-5) |
| `evidence` | ✅ | ManyToManyField → ArchiveDocument |
| `replaces_event` | ✅ | Self-referencing FK, SET_NULL |
| `has_gold_seal` | ✅ | Property: `is_system_source and status == 'STIPULATED'` |
| `clean()` | ✅ | **Source Requirement**: CONTESTED/REFUTED → requires evidence |
| `clean()` | ✅ | **Hardened Validation**: System sources can't be CONTESTED without replaces_event chain OR Correction doc |
| `clean()` | ✅ | COURT/NEUTRAL → auto-sets `is_system_source=True`, `status=STIPULATED`, `trust_level=5` |

### **2. Backend Services**

| Service | Status | Key Features |
|---------|--------|--------------|
| **ConflictResolverService** | ✅ | KEEP_ORIGINAL, KEEP_COUNTER, MERGE paths |
| **HiveExportService** | ✅ | UUID-based manifest, atomic, file copying |
| **HiveImportService** | ✅ | **UUID Stability**, collision detection, atomic transactions |
| **ShredderService** | ✅ | **`os.urandom` secure wipe** + `os.unlink`, recursive, atomic |
| **HiveDirectoryService** | ✅ | Formal/private structure, **Gate Logic** methods exist |

### **3. Directory Compartmentalization**
| Path | Status |
|------|--------|
| `/media/hives/[case_uuid]/formal/evidence/` | ✅ |
| `/media/hives/[case_uuid]/private/[user_uuid]/` | ✅ |
| Subdirs: drafts/, wiki/, research/, temp/ | ✅ |

### **4. API Endpoints** (`apps/timeline/api_urls.py`)
All **REGISTERED**:
- `/contest/` ✅
- `/resolve/` ✅
- `/export/` ✅
- `/import/` ✅
- `/shred/` ✅

### **5. Frontend Integration**
- **Gold Seal badge** in `frontend/src/components/EventCard.tsx` ✅
- **TypeScript types** include `has_gold_seal: boolean` ✅

### **6. Database Migrations**
- TimelineEvent: status, evidence, replaces_event, is_system_source, trust_level ✅
- ArchiveDocument: is_promoted, promoted_at ✅

---

---

## **❌ CRITICAL GAPS**

---

### **🔴 P0 - BLOCKING: ArchiveDocument Missing UUID Field**

**Issue**: `ArchiveDocument` uses default AutoField (integer PK), but **all services reference `document.uuid`**

**Evidence**:
```python
# hive_directory.py:230
filename = f"{document.uuid}.{ext}"

# hive_export.py:177-179
"uuid": str(doc.uuid),
"file_path": file_path,
"case_uuid": str(doc.case.uuid),
```

**Impact**: Hive export/import **WILL FAIL** when serializing ArchiveDocument

**Fix Required**:
- Add `uuid = models.UUIDField(default=uuid.uuid4, editable=False)` to ArchiveDocument
- Create migration
- Update all serialization to use the new UUID field

---

### **🔴 P0 - BLOCKING: Gate Logic API Not Connected**

**Issue**: `HiveDirectoryService.promote_to_evidence()` and `demote_from_evidence()` exist but have **NO API endpoints**

**Evidence**: No `/promote/` or `/demote/` routes in any `urls.py`

**Impact**: Frontend cannot trigger document promotion from private → formal

**Fix Required**:
- Add `ArchiveDocumentViewSet` with `@action(detail=True, methods=['post'])`
- `promote/` endpoint
- `demote/` endpoint

---

### **🟡 P1 - HIGH: Case UUID Reference Inconsistency**

**Issue**: Services use `case.uuid` but Case model's UUID is stored in `case.id`

**Evidence**:
```python
# Case model (core/models.py:33)
id = models.UUIDField(primary_key=True, default=uuid.uuid4, ...)

# hive_directory.py:159
cls.ensure_hive_structure(case.uuid)  # ← Uses .uuid, but field is .id
```

**Impact**: May work if `uuid` is a property, but inconsistent naming causes confusion

**Fix Required**: Add `@property def uuid(self): return self.id` to Case model OR update all references to `case.id`

---

### **🟡 P1 - MEDIUM: User UUID Unverified**

**Issue**: Services reference `user.uuid` but User model was not checked for UUID field

**Evidence**:
```python
# hive_import.py:440
def _get_user(self, user_uuid: Optional[str]) -> Optional[User]:
    try:
        return User.objects.get(uuid=user_uuid)  # ← Assumes uuid field exists
```

**Impact**: Hive import may fail if User doesn't have UUID field

**Fix Required**: Verify User model has UUID field, add if missing

---

---

## **📊 SUMMARY TABLE**

| Component | Status | Severity | Action |
|-----------|--------|----------|--------|
| TimelineEvent Model | ✅ Complete | - | None |
| has_gold_seal | ✅ Complete | - | None |
| clean() Validation | ✅ Complete | - | None |
| ConflictResolverService | ✅ Complete | - | None |
| HiveExport/Import | ✅ Complete | - | None |
| ShredderService | ✅ Complete | - | None |
| HiveDirectoryService | ✅ Complete | - | None |
| API Endpoints | ✅ Complete | - | None |
| Frontend Gold Seal | ✅ Complete | - | None |
| **ArchiveDocument UUID** | ❌ **MISSING** | **🔴 P0-BLOCKING** | Add field + migration |
| **Gate Logic API** | ❌ **MISSING** | **🔴 P0-BLOCKING** | Add promote/demote endpoints |
| Case.uuid Reference | ⚠️ Inconsistent | 🟡 P1-HIGH | Add property or update refs |
| User.uuid Reference | ⚠️ Unverified | 🟡 P1-MEDIUM | Verify User model |

---

**Awaiting your approval to proceed with fixes. Which gaps should I address first?
