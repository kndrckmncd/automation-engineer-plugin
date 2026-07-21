---
name: idp-creator
description: >-
  Generates a well-structured Individual Development Plan (IDP) Word document
  using the SMART goal framework. Use this when the user wants to create, improve,
  or update an IDP, development plan, or career growth plan.
argument-hint: "Employee name and role, or path to existing IDP to improve"
user-invocable: true
---

# IDP Creator

Produces a professionally formatted Individual Development Plan (.docx) using the
SMART goal framework (Specific, Measurable, Achievable, Relevant, Time-bound).
Covers goals, key deliverables, action steps, target dates, status, and support needed.

## Use When

- User asks to "create an IDP", "make a development plan", or "build a career plan"
- User wants to improve or update an existing IDP document
- User provides an existing IDP file to enhance
- User asks to generate a development plan for a specific period

## Prerequisites

- `python-docx` installed (`pip install python-docx`)
- Employee details: name, position, manager, period covered

## Workflow Steps

### Step 1 — Gather Employee Context

If the user provides an existing IDP file path:
- Read it and extract all current goals, employee info, and status values
- Identify gaps: vague goals, missing dates, empty steps, or no support listed

If no existing file:
- Ask the user for: full name, position/title, manager name, and period covered

### Step 2 — Build SMART Goals

For each goal, apply the SMART framework. See `references/idp-framework.md` for
the full framework and Manulife automation engineer competency guide.

Enrich each goal with:
- **Specific**: clear outcome statement, not vague intent
- **Measurable**: concrete deliverable or metric (e.g., "deployed to production", "certification obtained")
- **Achievable**: realistic given role and timeframe
- **Relevant**: tied to team/business objectives or career growth
- **Time-bound**: specific quarter or date, not "TBA"

### Step 3 — Structure the IDP JSON

Build a config JSON matching this schema:
```json
{
  "employee": {
    "name": "...", "employee_number": "...", "date_hired": "...",
    "position": "...", "manager": "...", "period": "..."
  },
  "goals": [
    {
      "goal_statement": "...",
      "key_deliverables": "...",
      "target_steps": ["Step 1", "Step 2"],
      "target_date": "Q3 2026",
      "status": "Not Started | In Progress | Completed",
      "support_needed": "...",
      "category": "Technical | Leadership | Growth | Process"
    }
  ],
  "development_areas": [
    {
      "competency": "...",
      "current_level": "Developing | Proficient | Advanced",
      "target_level": "...",
      "actions": "..."
    }
  ]
}
```

Write the JSON to a temp file (e.g., `C:\Temp\idp_config.json`).

### Step 4 — Generate the Document

Run the generation script:
```
python skills/idp-creator/scripts/generate-idp.py --config-json C:\Temp\idp_config.json --output "path/to/Output Name.docx"
```

The script produces a formatted `.docx` with:
- Header block (employee info)
- SMART Goals table
- Development Areas table
- Signature block

### Step 5 — Clean Up and Confirm

- Delete the temp JSON file
- Confirm the output file path to the user
- Offer to adjust any goals or add more sections

## Output Format

- A `.docx` file at the path specified by `--output`
- Console JSON summary: `{ "output": "...", "goals": N, "status": "saved" }`

## Completion Checklist

- [ ] All goals follow SMART framework (no "TBA" dates without reason)
- [ ] Each goal has at least 2 concrete action steps
- [ ] Each goal has a measurable deliverable
- [ ] Support needed is filled for every goal
- [ ] Development areas section is populated
- [ ] Output file saved and path confirmed to user

## Bundled Resources

- `references/idp-framework.md` — SMART goal guide + Manulife automation engineer competency areas
- `scripts/generate-idp.py` — Python script that produces the formatted .docx
