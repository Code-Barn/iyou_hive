# 25FA152: Contribution Guide

For **case context, key players, and current priorities**, see:
- [CASE_CONTEXT.md](CASE_CONTEXT.md) *(Updated regularly by the lead agent.)*

---

## **How to Contribute**
### **1. Updating the Timeline**
- **Comprehensive Timeline** (`TIMELINE.md`): Add **all events** (legal, personal, systemic) since 2012.
- **Legal Defense Timeline** (`LEGAL_TIMELINE.md`): Focus on **court evidence** (e.g., OPs, motions, therapy obstruction).
- **Recent Timeline** (`RECENT_TIMELINE.md`): Zoom in on **2021–2026** (escalations, school records, therapy).

#### **Adding an Event**
1. **Format**:
   ```markdown
   | Date       | Event/Incident               | Category   | Supporting Document(s) | Notes          |
   |------------|-------------------------------|------------|-----------------------|----------------|
   | 2019-12-08 | Cory Neill murdered (Zadyn’s father). | Criminal   | (FOIA pending)        | No confirmed links to Pauletta. |
   ```
2. **Link Documents**: Use relative paths (e.g., `[17CM2499](LEGAL_FILE/17CM2499.pdf)`).

---

### **2. GitHub Workflow**
- **Branches**: Create a new branch for edits (e.g., `add-cory-neill-event`).
- **Pull Requests (PRs)**: Submit a PR for review/merge.
- **Issues**: Track tasks (e.g., "Upload 15OP512," "Add Zadyn’s school records").

#### **Example Workflow**
1. **Clone the Repo**:
   ```bash
   git clone https://github.com/dcbyers13/25FA152.git
   cd 25FA152
   ```
2. **Create a Branch**:
   ```bash
   git checkout -b add-cory-neill-event
   ```
3. **Edit Files** (e.g., `TIMELINE.md`).
4. **Commit and Push**:
   ```bash
   git add TIMELINE.md
   git commit -m "Add Cory Neill murder (12/08/2019)"
   git push origin add-cory-neill-event
   ```
5. **Open a PR**: Go to GitHub and submit a pull request.

---

### **3. Document Standards**
- **Facts Over Narrative**: Stick to dates, quotes, and citations.
- **Neutral Language**: Avoid emotional phrasing (e.g., "Pauletta lied" → "Pauletta’s claims lack evidence").
- **Cross-Reference**: Link to supporting files (e.g., `[17CM2499](LEGAL_FILE/17CM2499.pdf)`).

---

## **Repository/Library Navigation**
- **`filemap.md`**: A **master inventory** of all files, organized by category. Use this to:
  - Quickly locate documents (e.g., "Where is the 2024 OP filing?").
  - Identify gaps (e.g., "We’re missing Zadyn’s 2023 school records").

**Example**:
```markdown
# Filemap: 25FA152 Documents
## Legal Files
- `LEGAL_FILE/17CM2499_BATTERY_2017.pdf`: Pauletta’s battery conviction.
- `LEGAL_FILE/24OP613_COURT_FILE.pdf`: 2024 Order of Protection.
```

---

## **Example Workflow for New Agents**
1. **Review the Case**:
   - Start with [CASE_CONTEXT.md](CASE_CONTEXT.md).
   - Then read `TIMELINE.md` and `LEGAL_TIMELINE.md`.

2. **Add an Event**:
   - Find a gap (e.g., missing 15OP512).
   - Draft an entry in the correct table.
   - Submit a PR for review.

3. **Flag Missing Docs**:
   - Open an issue: "Need 15OP512 docket sheet."

---

## **Key Documents**
- **Timelines**:
  - [Comprehensive](TIMELINE.md)
  - [Legal Defense](LEGAL_TIMELINE.md)
- **Supporting Files**:
  - `LEGAL_FILE/`: Court orders, OPs, motions.
  - `COMMS/`: TalkingParents logs, emails.
  - `MEDICAL/`: Therapy records, DCFS reports.
- **Navigation**:
  - [Filemap](filemap.md): Master inventory of all files.

---

## **FAQ**
- **Q: How do I cite a document?**
  - Use markdown links: `[17CM2499](LEGAL_FILE/17CM2499.pdf)`.

- **Q: What if I’m unsure about a date/event?**
  - Open an issue or ask in the PR comments.

- **Q: Can I edit directly?**
  - Yes! For small fixes (typos), edit directly. For larger changes, use a PR.