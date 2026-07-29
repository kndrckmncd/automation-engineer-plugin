---
name: planview-time-logger
version: 1.1.0
description: >
  Logs hours to the Planview timesheet by navigating the UI with Selenium Edge.
  Accepts work items with GL codes (matched from Jira epics via customfield_25042),
  hours per day, and OOO days (logged as "Out of Office" work type). Use this when
  the user asks to log time, fill in their timesheet, submit hours, or track time
  in Planview.
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
- Per-day hour entry with OOO days logged as **Out of Office** work type
- User-selected assignment/work type per GL code
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
   - **Assignment/work type** — always ask explicitly; present these choices:
     - `(CapEx) Analysis`
     - `(CapEx) App Programming & Testing`
     - `(CapEx) Development on Existing App`
     - `(CapEx) Architecture`
     - `(CapEx) Implementations`
     - `(CapEx) Project Management`
     - `(CapEx) Code Promotion`
     - `(OpEx) Business Case Requirements and Planning`
   - Hours per day (Mon–Fri)
3. **OOO days** (optional) — day names (e.g., `["Mon", "Wed"]`). **OOO days MUST be logged as the "Out of Office" Planview work type** — do NOT skip them silently.
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
  "works": [
    {
      "gl_code": "EC10010145",
      "assignment": "(CapEx) App Programming & Testing",
      "hours": { "Mon": 7.5, "Tue": 7.5, "Wed": 7.5, "Thu": 7.5, "Fri": 7.5 }
    },
    {
      "gl_code": "OOO",
      "assignment": "Out of Office",
      "hours": { "Mon": 7.5 }
    }
  ],
  "out_of_office": ["Mon"],
  "sign_and_submit": false
}
```

**Rules:**
- `hours` keys must be `Mon`, `Tue`, `Wed`, `Thu`, `Fri`, `Sat`, `Sun`
- **OOO days MUST have a matching work entry** with `"gl_code": "OOO"` and `"assignment": "Out of Office"` — always include this when the user mentions being out. Never silently skip OOO days.
- `resource_code` is always `128447` for Sean
- Multiple works: split total hours across GL codes per day
- The `out_of_office` list only controls which days to skip for non-OOO work items; OOO hours are still entered on those days via the "Out of Office" work entry
- **Checkbox scoping**: when adding work via Select Work, always scope checkbox clicks strictly to the matching GL code's project section. Never check the same assignment across multiple projects.
- **On error / wrong entries**: immediately zero out incorrectly entered cells AND uncheck the wrong rows in Select Work before re-logging

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

> "Log my hours for the week of July 4: 7.5h/day on GB Enhancements App Programming"

```json
{
  "period": "7/4/2026",
  "resource_code": "128447",
  "works": [{
    "gl_code": "EC10010145",
    "assignment": "(CapEx) App Programming & Testing",
    "hours": { "Mon": 7.5, "Tue": 7.5, "Wed": 7.5, "Thu": 7.5, "Fri": 7.5 }
  }],
  "out_of_office": [],
  "sign_and_submit": false
}
```

**Example 2 — With OOO days**

> "Log hours week of July 18, I'm out Monday and Wednesday"

```json
{
  "period": "7/18/2026",
  "resource_code": "128447",
  "works": [
    {
      "gl_code": "EC10010145",
      "assignment": "(CapEx) App Programming & Testing",
      "hours": { "Tue": 7.5, "Thu": 7.5, "Fri": 7.5 }
    },
    {
      "gl_code": "OOO",
      "assignment": "Out of Office",
      "hours": { "Mon": 7.5, "Wed": 7.5 }
    }
  ],
  "out_of_office": ["Mon", "Wed"],
  "sign_and_submit": false
}
```

**Example 3 — Multiple GL codes**

> "Log 4h on DS0019 and 3.5h on DS0020 each day, I'm off Friday"

```json
{
  "period": "7/4/2026",
  "resource_code": "128447",
  "works": [
    {
      "gl_code": "EC10010143",
      "assignment": "(CapEx) App Programming & Testing",
      "hours": { "Mon": 4, "Tue": 4, "Wed": 4, "Thu": 4 }
    },
    {
      "gl_code": "EC10010144",
      "assignment": "(CapEx) App Programming & Testing",
      "hours": { "Mon": 3.5, "Tue": 3.5, "Wed": 3.5, "Thu": 3.5 }
    },
    {
      "gl_code": "OOO",
      "assignment": "Out of Office",
      "hours": { "Fri": 7.5 }
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
- **Checkbox scoping is strict**: `find_and_check_assignment` uses JS to scope checkbox selection to the exact GL code project section. It will NOT check the same assignment under a different project.
- **OOO is never silent**: OOO days must always be logged as the "Out of Office" Planview work type (under "Not Billable"). Skipping them without logging is wrong.
- **Cleanup on error**: if wrong hours are entered, zero out each affected cell AND uncheck the wrong assignment in Select Work before re-logging the correct entry.
- Always ask the user for the assignment/work type — do not assume Analysis; present the full list of choices.

## Reference Files

- `references/planview-dom-notes.md` — DOM structure, cell ID patterns, API endpoints
