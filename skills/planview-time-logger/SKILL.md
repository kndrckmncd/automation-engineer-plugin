---
name: planview-time-logger
version: 1.0.0
description: >
  Logs hours to the Planview timesheet by navigating the UI with Selenium Edge.
  Accepts work items with GL codes (matched from Jira epics via customfield_25042),
  hours per day, and optional out-of-office days. Use this when the user asks to
  log time, fill in their timesheet, submit hours, or track time in Planview.
author: kndrckmncd
tools:
  - powershell
  - view
---

# Planview Time Logger

## Purpose

Automate logging of hours into the Planview timesheet at:
`https://mlcdndiv.pvcloud.com/planview/Track/Time`

Supports:
- Multiple work items per period
- GL code lookup from Jira Epic `Related GL Code` field
- Per-day hour entry with OOO day skipping
- Optional Sign and Submit

## Prerequisites

- Microsoft Edge installed at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
- Selenium 4: `pip install selenium`
- Edge profile at `C:\Temp\edge_tmp` (first-run SSO login required once)
- `.env` with `JIRA_API_TOKEN` and `email` for GL code lookups

## Instructions

### Step 1 — Gather Inputs

Ask the user for:
1. **Period date** — the period start date as shown on the Select Period page (e.g., `7/4/2026`)
2. **Work items** — for each:
   - GL code (or ask to look it up from Jira epics)
   - Assignment/phase name (e.g., `(CapEx) Analysis`)
   - Hours per day (Mon–Fri)
3. **OOO days** (optional) — day names to skip (e.g., `["Mon"]`)
4. **Sign and submit?** — whether to click Sign and Submit after logging

### Step 2 — Look Up GL Codes (if needed)

If the user doesn't know the GL code, run the lookup script:

```powershell
python skills\planview-time-logger\scripts\lookup-gl-codes.py
```

This fetches the user's Jira epics and shows `Key | GL Code | Summary`.
Match the GL code to the Planview project name (e.g., `EC10010145` → `Ops GB Enhancements • EC10010145`).

### Step 3 — Build Config File

Create a JSON config at a temp path (e.g., `C:\Temp\planview_config.json`):

```json
{
  "period": "7/4/2026",
  "resource_code": "128447",
  "default_work": {
    "gl_code": "EC10010145",
    "assignment": "(CapEx) Analysis"
  },
  "works": [
    {
      "gl_code": "EC10010145",
      "assignment": "(CapEx) Analysis",
      "hours": { "Mon": 7.5, "Tue": 7.5, "Wed": 7.5, "Thu": 7.5, "Fri": 7.5 }
    }
  ],
  "out_of_office": [],
  "sign_and_submit": false
}
```

**Rules:**
- `hours` keys must be `Mon`, `Tue`, `Wed`, `Thu`, `Fri`, `Sat`, `Sun`
- OOO days are excluded from all work items automatically
- `resource_code` is always `128447` for Sean
- Multiple works: split total hours across GL codes per day

### Step 4 — Dry Run First

```powershell
python skills\planview-time-logger\scripts\log-hours.py --config C:\Temp\planview_config.json --dry-run
```

Review the plan. If correct, run without `--dry-run`.

### Step 5 — Log Hours

```powershell
python skills\planview-time-logger\scripts\log-hours.py --config C:\Temp\planview_config.json
```

A browser window will open. The script will:
1. Navigate to the Select Period page and click the matching period
2. Check if work rows already exist; add missing ones via Select Work
3. Click each day cell and enter hours
4. Sign and Submit if configured

## Examples

**Example 1 — Standard work week**

> "Log my hours for the week of July 4: 7.5h/day on GB Enhancements Analysis"

```json
{
  "period": "7/4/2026",
  "resource_code": "128447",
  "works": [{
    "gl_code": "EC10010145",
    "assignment": "(CapEx) Analysis",
    "hours": { "Mon": 7.5, "Tue": 7.5, "Wed": 7.5, "Thu": 7.5, "Fri": 7.5 }
  }],
  "out_of_office": [],
  "sign_and_submit": false
}
```

**Example 2 — Multiple works + OOO**

> "Log 4h on DS0019 and 3.5h on DS0020 each day, I'm off Friday"

```json
{
  "period": "7/4/2026",
  "resource_code": "128447",
  "works": [
    {
      "gl_code": "EC10010143",
      "assignment": "(CapEx) Analysis",
      "hours": { "Mon": 4, "Tue": 4, "Wed": 4, "Thu": 4 }
    },
    {
      "gl_code": "EC10010144",
      "assignment": "(CapEx) Analysis",
      "hours": { "Mon": 3.5, "Tue": 3.5, "Wed": 3.5, "Thu": 3.5 }
    }
  ],
  "out_of_office": ["Fri"],
  "sign_and_submit": false
}
```

## Constraints

- Browser must be Edge; Chrome alternative is available by changing `make_driver()` in the script
- Cell click → input field interaction depends on Planview JS; if it fails, the script falls back to JS injection
- `sign_and_submit: true` is irreversible — confirm with user before enabling
- The script will not delete existing hours, only overwrite specified cells
- OOO as a specific Planview work type (e.g., payroll category) is not yet automated — log 0h for those days

## Reference Files

- `references/planview-dom-notes.md` — DOM structure, cell ID patterns, API endpoints
