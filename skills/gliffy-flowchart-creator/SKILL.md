---
name: gliffy-flowchart-creator
description: >
  Creates a Gliffy flowchart diagram in Confluence based on as-is process steps
  from a source Confluence page. Use this when asked to create a flowchart,
  generate a Gliffy diagram, visualise process steps in Confluence, or turn
  a process list into a flow diagram.
allowed-tools:
  - shell
---

## Purpose

Read as-is process steps from a source Confluence page and automatically
generate a Gliffy flowchart diagram embedded in a target Confluence page
under a specified heading.

The flowchart layout:
- **Start** oval → one **process box** per step → **End** oval
- Steps are connected top-to-bottom with arrows
- Diagram is embedded using the Gliffy macro

## Prerequisites

- Python 3.10+ available
- `requests` package — install with `pip install requests` if missing
- Gliffy for Confluence plugin must be installed on the Confluence instance
- Environment variables set:
  - `CONFLUENCE_TOKEN` — API token (Cloud) or Personal Access Token (Server/DC)
  - `CONFLUENCE_EMAIL` — user email (required for Confluence Cloud only)

## Bundled Resources

- `./scripts/fetch-steps.py` — reads a Confluence page and extracts process steps
- `./scripts/create-gliffy.py` — generates the Gliffy diagram and embeds it in the target page

## Instructions

1. **Before doing anything else**, require the user to provide all of:
   - **Source Confluence URL** — the page containing the as-is process steps
   - **Target Confluence URL** — the page where the diagram will be placed
   - **Heading** — the exact heading on the target page under which to insert the diagram
   - **Diagram name** — what to call the Gliffy diagram

   If any are missing, ask:
   > "Please provide: (1) source page URL, (2) target page URL, (3) heading name, (4) diagram name."

2. Check that `python` and `requests` are available:
   ```
   python -c "import requests"
   ```
   If missing, run `pip install requests` first.

3. Check that `CONFLUENCE_TOKEN` is set. If not, ask the user to set it:
   ```
   set CONFLUENCE_TOKEN=your_token_here
   set CONFLUENCE_EMAIL=your_email@company.com   # Cloud only
   ```

4. Fetch the process steps from the source page:
   ```
   python ./scripts/fetch-steps.py --page-url "<source-url>" > steps.json
   ```

5. Review the extracted steps with the user before proceeding. Show them the list and confirm:
   > "I found N steps: [list]. Shall I create the flowchart?"

6. Create the Gliffy diagram on the target page:
   ```
   python ./scripts/create-gliffy.py \
     --target-url "<target-url>" \
     --heading "<heading>" \
     --diagram-name "<diagram-name>" \
     --steps-json steps.json
   ```

7. Report the result:
   - Diagram name and number of steps
   - Target page title and heading where it was inserted
   - Link to the target Confluence page

8. Clean up the temporary `steps.json` file after success.

## Examples

### Example 1: Happy path

**User provides:**
- Source: `https://site.atlassian.net/wiki/spaces/GB/pages/12345/AS-IS+Process`
- Target: `https://site.atlassian.net/wiki/spaces/GB/pages/67890/Process+Design`
- Heading: `Current State Flowchart`
- Diagram name: `GB0071 AS-IS Flowchart`

**Skill does:**
1. Fetches steps from source page → finds 8 steps.
2. Confirms with user.
3. Creates Gliffy diagram with 8 process boxes.
4. Embeds macro under "Current State Flowchart" heading on target page.

**Result:**
```
✅ Gliffy flowchart created!
   - Diagram: "GB0071 AS-IS Flowchart"
   - Steps: 8
   - Inserted under: "Current State Flowchart"
   - Target page: Process Design
```

### Example 2: Heading not found

If the heading does not exist on the target page, the diagram is appended
at the end of the page and a warning is shown.

## Error Handling

- If the source page has no list items, report it and ask the user to confirm the URL or describe the format of the steps.
- If the Gliffy plugin is not installed, the API will return a 404 — report this clearly.
- If the heading is not found on the target page, append the diagram at the end and warn the user.
- If auth fails (401/403), ask the user to check `CONFLUENCE_TOKEN` and `CONFLUENCE_EMAIL`.

## Constraints

- Always confirm extracted steps with the user before creating the diagram.
- Never store or log `CONFLUENCE_TOKEN` or `CONFLUENCE_EMAIL`.
- Clean up `steps.json` after the task completes.
- Only create the diagram — do not modify the source page.

## Changelog

- 2026-07-06: Initial version
