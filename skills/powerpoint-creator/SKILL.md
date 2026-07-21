---
name: powerpoint-creator
description: >
  Generates a PowerPoint (.pptx) presentation using the standard Manulife template.
  Use this when asked to create a presentation, build slides, make a deck,
  or generate a PowerPoint for a topic or project.
allowed-tools:
  - shell
---

## Purpose

Generate a professional `.pptx` PowerPoint presentation from a structured
outline using the standard Manulife template. Saves to the PPT Creation folder
by default.

## Prerequisites

- Python 3.8+
- `python-pptx` installed (`pip install python-pptx`)
- Template file at: `C:\Users\manisea\OneDrive - Manulife\Documents\COPILOT_TEST\PPT Creation\Template.pptx`

## Bundled Resources

- `./scripts/create-presentation.py` — builds the .pptx using the Manulife template
- `./scripts/confluence-search.py` — searches Confluence space `CDTPACS` for page content to use as slide context

## Instructions

### Step 0 — Search Confluence for context (automatic)

Before generating the outline, search Confluence space `CDTPACS` for pages related to the topic:

```
python ./scripts/confluence-search.py --keyword "<topic>" --space CDTPACS --max-results 3
```

Use the returned page text to make slides accurate and specific — real bot names, process steps, system names, exceptions, and business rules found in the documentation. Do **not** use generic placeholder bullets when Confluence content is available.

If no Confluence results are found, fall back to a sensible generic outline.

Ask the user for the following if not already provided:

1. **Presentation title** — the main title shown on the cover slide
2. **Slide outline** — a list of slides, each with:
   - Slide title
   - Bullet points (3–6 per slide)
   - Optional speaker notes
3. **Output path** — where to save the file
   - Default: `C:\Users\manisea\OneDrive - Manulife\Documents\COPILOT_TEST\PPT Creation\<title>.pptx`
4. **Author name** — shown on the cover slide (optional)

If the user provides only a topic (e.g., "make a presentation about RPA"), generate
a sensible outline from the topic before proceeding. Show the proposed outline and
confirm before generating.

### Step 2 — Build the slides JSON

Construct a `slides.json` config:

```json
{
  "title": "Presentation Title",
  "subtitle": "Optional subtitle",
  "author": "Author Name",
  "slides": [
    {
      "title": "Slide Title",
      "content": ["Bullet point 1", "Bullet point 2", "Bullet point 3"],
      "notes": "Optional speaker notes"
    }
  ]
}
```

Save it to a temp file (e.g., session temp dir or `C:\Temp\slides.json`).

### Step 3 — Run the script

```
python ./scripts/create-presentation.py \
  --slides-json <temp_slides_json> \
  --output "<output_path>"
```

The `--template` argument defaults to the Manulife template. Only pass it
explicitly if the user requests a different template.

### Step 4 — Report to user

Tell the user:
- The full path where the file was saved
- Number of slides generated
- How to open it (double-click or open with PowerPoint)

### Step 5 — Clean up

Delete the temp `slides.json` after the .pptx is saved.

## Examples

### Example 1 — Topic only

**User says:** "Create a presentation about the DSS Advisor Termination bot"

**Skill does:**
1. Generates a 6-slide outline: Introduction, Process Overview, As-Is Steps,
   Bot Design, Exception Handling, Next Steps
2. Confirms outline with user
3. Builds `slides.json` and runs `create-presentation.py`

**Result:**
```
✅ Saved: C:\Users\manisea\OneDrive - Manulife\Documents\COPILOT_TEST\PPT Creation\DSS_Advisor_Termination_Bot.pptx  (6 slides)
```

### Example 2 — Full outline provided

**User says:** "Make a deck with: Slide 1 = Project Background, Slide 2 = Solution,
Slide 3 = Timeline"

**Skill does:** Builds the JSON directly from the provided outline, runs the
script, reports the output path.

## Error Handling

- If `python-pptx` is not installed: run `pip install python-pptx` then retry
- If the template file is missing: warn the user and check the path
- If the outline is empty or has no bullets: prompt the user to add content before generating

## Constraints

- **Always use the Manulife template** — never generate a plain/blank presentation
- **Always save to the PPT Creation folder** unless user explicitly specifies another path
- Always confirm a generated outline with the user before running the script
- Never overwrite an existing file without asking
- Keep slide content concise — max 6 bullets per slide; suggest splitting if more

## Changelog

- 2026-07-15: Initial version — custom blue theme
- 2026-07-15: Updated to use Manulife Template.pptx and save to PPT Creation folder
- 2026-07-16: Added Confluence search (CDTPACS) to enrich slide outlines with real project context

