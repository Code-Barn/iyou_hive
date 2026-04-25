# Timeline Markdown Schema

## Overview
This document defines the standardized schema for Timeline Markdown files used in Hiver. The schema is designed to be both machine-readable and printable for legal settings.

## Schema
Each event in the timeline should follow this format:

```markdown
# YYYY-MM-DD
**Event:** [Event/Incident Name]
**Category:** [Category Name]
**Supporting Docs:** [Link to Document(s)]
**Notes:** [Additional Notes]
```

## Example
```markdown
---
title: "Legal Case Timeline"
---

# 2023-01-15
**Event:** Contract Signed
**Category:** Contracts
**Supporting Docs:** [contract_20230115.pdf](link_to_document)
**Notes:** Signed with X Corp. Review by 2023-02-01.

# 2023-03-20
**Event:** Email from Lawyer
**Category:** Communication
**Supporting Docs:** [email_20230320.pdf](link_to_document)
**Notes:** "Urgent: Review attached draft."
```

## Fields
- **Date (YYYY-MM-DD):** The date of the event.
- **Event/Incident:** A brief description of the event.
- **Category:** The category the event falls under (e.g., Contracts, Communication, Court Filing).
- **Supporting Docs:** Links to relevant documents.
- **Notes:** Any additional information or context.

## Usage
- Use this schema to create Timeline Markdown files for upload to Hiver.
- Ensure the Markdown file is valid and follows the schema for proper rendering in the app.

## License
This schema is part of the Byers Brands ecosystem and follows the same licensing terms.