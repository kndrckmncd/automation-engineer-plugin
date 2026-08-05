---
name: client-profile-change-logger
version: 1.0.0
description: >
  Adds a new row to the Summary of Changes table in a GB Client Profile .doc
  file. Date is always today, Updated By is always "GB0074 Bot", and the
  description is provided as input. Use when the user wants to log a change,
  update the change history, or add an entry to the Summary of Changes.
author: kndrckmncd
tools:
  - powershell
---

# Client Profile Change Logger

## Purpose

Appends a new row to the **Summary of Changes** table inside a GB Client
Profile `.doc` file:

| Column | Value |
|---|---|
| Date updated | Today's date (e.g. `August 5, 2026`) |
| Updated By | `GB0074 Bot` |
| Brief Description of Change | Provided by user |

## Prerequisites

- Microsoft Word installed (`win32com` is used to write to the `.doc`)
- `pywin32` installed: `pip install pywin32`

## Instructions

### Run the script

```powershell
python skills\client-profile-change-logger\scripts\add-change-log.py `
  --file "C:\path\to\ClientProfile.doc" `
  --description "Your change description here"
```

### Example output

```json
{
  "status": "success",
  "date": "August 5, 2026",
  "updated_by": "GB0074 Bot",
  "description": "Posted policy 83143 and booklets 100, 200, 300",
  "row_number": 80
}
```

## Constraints

- The Summary of Changes table is auto-detected by its 3-column structure
  and "Date" header — no hardcoded table index
- The document is saved automatically after the row is added
- Only `.doc` format is supported (not `.docx`)
- Date format matches existing entries: `Month D, YYYY` (no leading zero on day)
