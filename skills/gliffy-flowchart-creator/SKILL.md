---
name: gliffy-flowchart-creator
description: >
  Creates a draw.io flowchart diagram in Confluence based on as-is process steps
  from a source Confluence page. Use this when asked to create a flowchart,
  generate a diagram, visualise process steps in Confluence, or turn
  a process list into a flow diagram.
allowed-tools:
  - shell
---

## Purpose

Read as-is process steps from a source Confluence page and generate a
**draw.io-compatible horizontal flowchart** uploaded as an attachment to
the target Confluence page, ready for manual import.

The flowchart style matches the team's standard:
- **Horizontal left-to-right flow**
- **Rectangles** for process steps, **diamonds** for decision points
- **Exception paths** branch downward in red
- **Orange circle connectors** when the flow wraps to a new row
- **Standard steps always included**: Get Work → Audit Report → [as-is steps] → Update Critical Data
- **Detailed navigation**: button clicks, screen names, field values preserved

## Prerequisites

- Python 3.10+ available
- `requests` package — install with `pip install requests` if missing
- Environment variables:
  - `CONFLUENCE_TOKEN` — API token (Cloud) or Personal Access Token (Server/DC)
  - `CONFLUENCE_EMAIL` — user email (Confluence Cloud only)

## Bundled Resources

- `./scripts/fetch-steps.py` — reads a Confluence page and extracts process steps
- `./scripts/create-diagram.py` — generates the draw.io XML and uploads it as a Confluence attachment

## Instructions

1. **Before doing anything else**, ask for all required inputs:
   - **Source Confluence URL** — page with the as-is process steps
   - **Target Confluence URL** — page where the diagram attachment will go
   - **Diagram name** — what to call the diagram file

2. Then ask for **deeper context** to generate a richer, more accurate diagram:
   - **Source of work**: Where does the bot get its work items from? (e.g. audit report, Excel file, email, queue, database)
   - **Development platform**: What RPA/automation tool is being used? (e.g. UiPath, Blue Prism, Power Automate Desktop)
   - **Systems accessed**: What applications or platforms are used during the process? (e.g. DSS, Salesforce, SAP, web portal)
   - **Standard steps**: Are Get Work, Audit Report, and Update Critical Data steps present? If so, what are their details?
   - **Exceptions**: Are there any exception/escalation paths? What triggers them and where do they go?

   Ask these as a group:
   > "Before I generate the diagram, I have a few questions to make it more accurate: (1) Where does the bot get its work from? (2) What platform is this built on? (3) What systems are accessed? (4) Are there Get Work / Audit Report / Update Critical Data steps?"

3. Check that `python` and `requests` are available. If `requests` is missing, run `pip install requests`.

4. Check that `CONFLUENCE_TOKEN` is set. If not, ask the user to set it.

5. Fetch the process steps from the source page:
   ```
   python ./scripts/fetch-steps.py --page-url "<source-url>" > steps.json
   ```

6. Review the extracted steps with the user. Show the full list and confirm:
   > "I found N steps. Here they are: [list]. Are these complete, or should I add/adjust any steps before generating?"

7. Generate the diagram and upload it as an attachment:
   ```
   python ./scripts/create-diagram.py \
     --target-url "<target-url>" \
     --diagram-name "<diagram-name>" \
     --steps-json steps.json
   ```

8. Provide the manual import instructions to the user:
   ```
   1. Open the target Confluence page.
   2. Edit the page and place cursor under the target heading.
   3. Insert a draw.io macro (or Gliffy if available).
   4. Choose "Import" → select "<diagram-name>.drawio" from page attachments.
   5. Save and publish.
   ```

9. Clean up the temporary `steps.json` file after success.

## Examples

### Example 1: Happy path

**User provides:**
- Source: `https://site.atlassian.net/wiki/spaces/GB/pages/12345/AS-IS+Process`
- Target: `https://site.atlassian.net/wiki/spaces/GB/pages/67890/Solution+Design`
- Diagram name: `GB0071 AS-IS Flowchart`

**Skill asks:**
> "Where does the bot get its work from? What platform is this built on? What systems are accessed?"

**User answers:**
> "Work comes from an audit report in Excel. Built on UiPath. Accesses DSS portal."

**Skill does:**
1. Fetches 12 steps from source page.
2. Prepends Get Work (from Excel audit report) and Audit Report steps.
3. Appends Update Critical Data step.
4. Generates horizontal draw.io flowchart with decision diamonds and exception paths.
5. Uploads `GB0071_AS-IS_Flowchart.drawio` as page attachment.
6. Provides import instructions.

**Result:**
```
✅ Diagram uploaded to Confluence!
   - File: GB0071_AS-IS_Flowchart.drawio
   - Steps: 14 (including Get Work, Audit Report, Update Critical Data)
   - Attached to: Solution Design page
   - Import it manually via draw.io macro → Import → select from attachments
```

## Error Handling

- If the source page has no list items, ask the user to confirm the URL or paste the steps directly.
- If auth fails (401/403), ask the user to check `CONFLUENCE_TOKEN` and `CONFLUENCE_EMAIL`.
- If upload fails, save the `.drawio` file locally and provide the path for manual upload.

## Constraints

- Always confirm extracted steps with the user before generating.
- Always ask for deeper context (platform, work source, systems) before generating.
- Never store or log `CONFLUENCE_TOKEN` or `CONFLUENCE_EMAIL`.
- Standard steps (Get Work, Audit Report, Update Critical Data) must always be included.
- Preserve detailed navigation text (button names, screen names, field values) in each step.
- Clean up `steps.json` after the task completes.

## Changelog

- 2026-07-06: Initial version
- 2026-07-06: Switched from Gliffy embed to draw.io attachment upload (manual import workflow)
- 2026-07-06: Updated to horizontal flow style matching team diagrams; added deeper context questions; standard steps always included

