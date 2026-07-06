---
name: gliffy-flowchart-creator
description: >
  Creates a Gliffy swim-lane flowchart (.gliffy) for AA360 bot solution design diagrams.
  Saves the file to ~/Downloads for import into Confluence Gliffy. Use this when asked
  to create a flowchart, generate a solution design diagram, build a swim-lane process
  diagram, or visualise an as-is process from Confluence.
allowed-tools:
  - shell
---

## Purpose

Generate a **Gliffy swim-lane flowchart** following the standard AA360 bot solution
design template. The `.gliffy` file is saved to `~/Downloads` for manual import into
Confluence.

## Standard Template (always)

Every diagram has this fixed structure:

| Lane | Role | Auto-generated content |
|------|------|----------------------|
| **Lane 1 — Master** | Orchestrator | START → Check [system] availability → Inserter (subprocess) → [subprocess lanes] → More work? → No: Create audit report → END. Dashed loop-back: Yes → Inserter |
| **Lane 2 — Inserter** | Work intake | Entry circle → Get work from [source] → Insert record to DB → Return to Master |
| **Lane 3+ — As-Is** | Business process | Entry circle → as-is steps from Confluence → Return to Master |

Master and Inserter lanes are always auto-generated. Only Lane 3+ steps are
provided by the user (from Confluence or described directly).

## Prerequisites

- Python 3.10+ available
- Environment variables (to fetch from Confluence):
  - `CONFLUENCE_TOKEN` — API token
  - `CONFLUENCE_EMAIL` — user email

## Bundled Resources

- `./scripts/fetch-steps.py` — reads a Confluence page and extracts process steps
- `./scripts/create-diagram.py` — generates Gliffy JSON from a `config.json`

## Instructions

### Step 1 — Ask for diagram name and system name first

> "What would you like to name this diagram?"
> "What system does Master check availability for? (e.g. MLM DSS, Salesforce)"

Do not proceed until both are provided.

### Step 2 — Ask about the Inserter lane

> "Where does the Inserter bot get its work? (e.g. Shared Folder, ADF food table, API)"

### Step 3 — Ask about subprocess lanes (Lane 3+)

> "What are the subprocess lane names for this solution? (Lane 3 onwards — these
> are the as-is process lanes, e.g. Termination, Processing, Approval)"

For each subprocess lane, ask:
> "Do you have a Confluence URL for the [lane name] steps, or would you like to
> describe the steps manually?"

- If Confluence URL provided: fetch steps (Step 4)
- If manual: ask the user to describe the steps and generate appropriate step text

### Step 4 — Check environment and fetch Confluence steps

Confirm `CONFLUENCE_TOKEN` is set. Then for each lane with a Confluence URL:

```
python ./scripts/fetch-steps.py --page-url "<url>" > steps_<lane>.json
```

Show the extracted steps and confirm:
> "I found N steps for [lane name]. Here they are: [list]. Are these correct?"

### Step 5 — Build config.json

```json
{
  "system_name": "MLM DSS",
  "inserter_source": "Shared Folder (advisor termination files)",
  "subprocess_lanes": [
    {
      "name": "Termination",
      "steps": ["step1", "step2", "..."]
    }
  ]
}
```

For multiple subprocess lanes, add each as an entry in `subprocess_lanes`.
For Confluence-fetched steps, inject them from the steps JSON.

### Step 6 — Generate the diagram

Single subprocess lane (steps from Confluence):
```
python ./scripts/create-diagram.py \
  --diagram-name "<name>" \
  --config-json config.json \
  --confluence-steps-json steps_Termination.json \
  --confluence-lane-name "Termination"
```

All steps already in config.json:
```
python ./scripts/create-diagram.py \
  --diagram-name "<name>" \
  --config-json config.json
```

### Step 7 — Report to the user

```
Saved to ~/Downloads/<diagram-name>.gliffy

To import into Confluence:
1. Edit the target Confluence page.
2. Place cursor under the target heading.
3. Insert a Gliffy Diagram macro.
4. File → Import → Open '<diagram-name>.gliffy' from your Downloads.
5. Save and publish.
```

### Step 8 — Clean up

Delete `config.json` and any `steps_*.json` files after the diagram is saved.

## Examples

### Example: MLM Termination solution design

**User provides:**
- Diagram name: `MLM Terminate`
- System: `MLM DSS`
- Inserter source: `Shared Folder (advisor termination files)`
- Subprocess lanes: `Termination` (from Confluence)
- Confluence URL: `https://manulife-cdn.atlassian.net/wiki/spaces/.../Advisor+Termination`

**config.json:**
```json
{
  "system_name": "MLM DSS",
  "inserter_source": "Shared Folder (advisor termination files)",
  "subprocess_lanes": [
    {"name": "Termination", "confluence_lane": true}
  ]
}
```

**Command:**
```
python ./scripts/fetch-steps.py --page-url "<url>" > steps_Termination.json
python ./scripts/create-diagram.py \
  --diagram-name "MLM Terminate" \
  --config-json config.json \
  --confluence-steps-json steps_Termination.json \
  --confluence-lane-name "Termination"
```

**Result:**
```json
{
  "diagram_name": "MLM Terminate",
  "system_name": "MLM DSS",
  "inserter_source": "Shared Folder (advisor termination files)",
  "subprocess_lanes": [{"name": "Termination", "steps": 12}],
  "status": "saved"
}
```

## Error Handling

- If source page has no list items, ask the user to confirm the URL or paste steps directly.
- If auth fails (401/403), ask the user to check `CONFLUENCE_TOKEN` and `CONFLUENCE_EMAIL`.
- If a lane has no steps, prompt the user to describe that lane's steps.

## Constraints

- **Always ask for diagram name and system name first** — required every time.
- Always confirm Confluence steps with the user before generating.
- Never assume fixed lane names — always ask for subprocess lane names.
- Never store or log `CONFLUENCE_TOKEN` or `CONFLUENCE_EMAIL`.
- Master and Inserter lanes are always auto-generated — do not ask user for their steps.
- Lane 3+ are always the as-is process lanes from Confluence or user description.
- Clean up `config.json` and `steps_*.json` after the task completes.

## Changelog

- 2026-07-06: Initial version (draw.io + Confluence upload)
- 2026-07-06: Switched to Gliffy format, saved to Downloads, no Confluence upload
- 2026-07-06: Fully dynamic swim lanes; source URL and diagram name always asked first
- 2026-07-06: Fixed Gliffy shape UIDs/TIDs; subprocess circles; lane-start circles
- 2026-07-06: Standard AA360 template hardcoded — Master and Inserter auto-generated;
              loop-back arrow; subprocess lanes end with Return to Master

