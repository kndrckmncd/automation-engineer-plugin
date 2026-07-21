---
name: performance-review
description: >-
  Generates a Manulife-compliant Performance Review document (.docx) split into
  "The What" (SMART objectives + results) and "The How" (Values & Risk). Use this
  when the user asks to create, write, or update a performance review, self-assessment,
  or year-end review document.
argument-hint: "Employee name and review period, or 'use my Jira tickets'"
user-invocable: true
---

# Performance Review Creator

Generates a formatted Performance Review (.docx) following Manulife's Global Performance
Ratings framework. The document is split into two rated sections:

- **Part 1 — The "What"**: SMART objectives tied to actual achievements and business impact
- **Part 2 — The "How"**: Demonstration of Manulife's 6 Values with proof points and risk management

## Use When

- User asks to "create a performance review", "write my self-assessment", or "generate my year-end review"
- User wants to update or improve an existing performance review
- User says "use my Jira tickets for my review"

## Prerequisites

- `python-docx` installed (`pip install python-docx`)
- Employee details: name, position, manager, review period
- Jira tickets (fetched automatically) or user-provided achievements

## Workflow Steps

### Step 1 — Fetch Achievements from Jira

Fetch all Jira tickets assigned to the user in the review year:
```
JQL: project = CTFSLBEB AND assignee = "<email>" AND created >= "<year>-01-01" ORDER BY updated DESC
```
Use `POST https://<domain>/rest/api/3/search/jql` with credentials from `.env`.

Group tickets by project area (e.g., Booklets, MLM Terminations, BC/NS Enhancements).
Include status: Done ✅, In Progress 🔄, Blocked ⚠️.

### Step 2 — Build "The What" — SMART Objectives

For each project area, write one SMART objective statement:
- **Specific**: Name the project and deliverable
- **Measurable**: Number of tickets, deployments, scripts, components completed
- **Attainable**: Reflect realistic scope given team size
- **Results-oriented**: State impact on business/team (efficiency, reliability, delivery)
- **Time-bound**: Reference quarters or dates

Include in each objective:
- Objective statement
- Key results/achievements (bullet list from Jira tickets)
- Business impact
- Self-rating (Developing / Effective / Highly Effective / Exceptional)

See `references/rating-guide.md` for rating definitions.

### Step 3 — Build "The How" — Values & Risk

For each of the 6 Manulife Values, write 1–2 proof point sentences from actual work:

| Value | Key Question |
|-------|-------------|
| Obsess about Customers | Did you consider stakeholder/end-user needs in your work? |
| Do the Right Thing | Did you act with integrity, speak up, follow standards? |
| Think Big | Did you learn, innovate, or try new approaches? |
| Get it Done Together | Did you collaborate, share, keep things transparent? |
| Own It | Did you take initiative, make decisions, solve problems? |
| Share Your Humanity | Did you support teammates, embrace diversity, be kind? |

Include risk management proof point: Did you demonstrate risk awareness, escalate issues proactively, or improve risk controls?

Assign overall "How" self-rating.

### Step 4 — Build Config JSON and Generate

Write a config JSON to a temp file and run:
```
python skills/performance-review/scripts/generate-review.py --config-json C:\Temp\review_config.json --output "path/to/Output.docx"
```

### Step 5 — Clean Up and Confirm

- Delete temp JSON
- Confirm output path to user
- Remind user: the lower of What/How ratings determines compensation rating

## Output Format

- `.docx` file with:
  - Header (employee info)
  - Part 1: The "What" table (objectives, results, impact, self-rating)
  - Part 2: The "How" table (values, proof points, risk, self-rating)
  - Rating Summary block
  - Manager Comments section (blank)
  - Signature block
- Console JSON: `{ "output": "...", "objectives": N, "status": "saved" }`

## Completion Checklist

- [ ] All objectives are SMART — no vague statements
- [ ] Each objective has measurable results from Jira
- [ ] Each of the 6 Values has at least one proof point
- [ ] Risk management is addressed
- [ ] Self-ratings assigned for both What and How
- [ ] Output file saved and confirmed

## Bundled Resources

- `references/rating-guide.md` — Full Manulife rating definitions (What + How)
- `scripts/generate-review.py` — Python script generating the formatted .docx
