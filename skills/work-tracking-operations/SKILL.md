---
name: work-tracking-operations
description: "Use when updating project progress in Jira, querying team member tickets, checking sprint story points, and logging delivery hours in Planview. Do NOT use for technical design or bot debugging."
allowed-tools:
  - shell
---

# Work Tracking Operations

## When to Use

- You need to move a Jira ticket to any swimlane/status.
- You want to see what tickets are assigned to a team member.
- You want to check how many story points are left in the current sprint.
- You must log worked hours against the correct Planview code.
- You want ticket status and time tracking to stay aligned.

## User Defaults

| Field | Value |
|-------|-------|
| Jira domain | `manulife-cdn.atlassian.net` |
| Email | `manisea@mfcgd.com` |
| Default project | `CTFSLBEB` |

Use these defaults automatically — do not ask the user for domain or email unless they provide a different one.

## Prerequisites

- Python 3.8+ available (`python --version`)
- Jira API token in the `JIRA_API_TOKEN` environment variable

**First-time setup** — if `JIRA_API_TOKEN` is not set:
```powershell
[System.Environment]::SetEnvironmentVariable("JIRA_API_TOKEN", "<your-token>", "User")
```
Then restart the terminal.

## Bundled Resources

- `./scripts/jira-update.py` — transitions a Jira ticket to any target swimlane via the Jira REST API
- `./scripts/jira-query.py` — fetches team member tickets and sprint story point summaries

## Instructions

### Ticket Identification — Extract First, Ask Second

**Never ask the user for a ticket number.** Always try to identify the ticket from what they said.

Follow this order:

1. **Exact key provided** (e.g. `CTFSLBEB-752`) → use `--ticket` directly.
2. **Description or name provided** (e.g. "my create database table ticket", "the accessibility story") → extract the core keywords and use `--search`.
   - Strip filler words ("my", "the", "ticket", "story", "task", "issue") and use the meaningful noun phrase.
   - Example: "my create database table ticket" → `--search "create database table"`
   - Example: "the accessibility story" → `--search "accessibility"`
3. **Multiple results returned** → list them clearly (key, summary, current status) and ask the user which one.
4. **No results returned** → try a shorter or broader keyword. If still nothing, then ask the user for the ticket key.

### Jira Ticket Updates

You need only two things from the user:
1. **What ticket** — exact key or a description (see Ticket Identification above)
2. **Target swimlane** — e.g. `Done`, `Dev - In Progress`, `Code Review`, `Ready for QA`

**By ticket key:**
```
python ./scripts/jira-update.py --ticket "CTFSLBEB-752" --status "Done"
```

**By keyword search** (when no key is given — use this by default):
```
python ./scripts/jira-update.py --search "create database table" --project "CTFSLBEB" --status "Done"
```

**List available swimlanes for a ticket** (when the target status is unclear):
```
python ./scripts/jira-update.py --ticket "CTFSLBEB-752" --list-transitions
```

> Domain and email are read automatically from env vars and defaults — do not pass them explicitly.

### After Running

Report to the user:
- Ticket key and summary
- Previous swimlane → New swimlane

### Swimlane Reference

| Stage | Jira Status |
|---|---|
| Work starts | Dev - In Progress |
| Development complete | Ready for QA |
| QA active | QA - In Progress |
| Testing complete | Code Review |
| Approved | Done |

### Fetching Team Member Tickets

Use `jira-query.py` when the user asks about someone else's stories, tasks, or tickets.

**All tickets for a person:**
```
python ./scripts/jira-query.py --user "Joshua Ilunio"
```

**Filtered by status:**
```
python ./scripts/jira-query.py --user "Shara Faelga" --status "Dev - In Progress"
```

**Scoped to a project (default is CTFSLBEB):**
```
python ./scripts/jira-query.py --user "Joshua Ilunio" --project "CTFSLBEB"
```

> The script resolves the person's Jira account by display name automatically — do not ask the user for an account ID.

After running, report:
- Assignee name
- Tickets grouped by status (key, summary, priority)
- Total ticket count

---

### Checking Sprint Story Points

Use `jira-query.py --sprint-points` when the user asks how many points are left, remaining, or completed in the current sprint.

**All team members in active sprint:**
```
python ./scripts/jira-query.py --sprint-points --project CTFSLBEB
```

**For a specific person in the active sprint:**
```
python ./scripts/jira-query.py --sprint-points --project CTFSLBEB --user "Joshua Ilunio"
```

After running, report:
- Sprint name
- Total story points in sprint
- Completed story points
- **Remaining story points** (highlight this — it's what users care about most)
- Per-ticket breakdown if helpful

---

### Planview Time Tagging

- Use the correct Planview code for the work item.
- Log the number of hours actually worked.
- Confirm Planview reflects the time spent after logging.

## Output

- Jira transition summary (ticket, previous status, new status)
- Team member ticket list grouped by status
- Sprint story point summary (total / completed / remaining)
- Planview hour logging confirmation

## Error Handling

- If the target status is not a valid transition, the script will list available swimlanes — use `--list-transitions` to show them, then ask the user which one to use.
- If authentication fails (HTTP 401), ask the user to verify their API token.
- If the ticket is not found (HTTP 404), confirm the ticket key and domain.
- If a keyword search returns no results, try a shorter keyword before asking the user for the exact key.
- If `--user` resolves multiple people with similar names, the script picks the closest match — confirm the name with the user if the result looks wrong.
- If `--sprint-points` finds no active sprint, ask the user to confirm the project key.

## Changelog

- 2026-07-15: Added Jira API integration via `scripts/jira-update.py`
- 2026-07-16: Strengthened ticket identification instructions — agent now extracts keywords from natural language and always searches before asking for a ticket number
- 2026-07-16: Added `scripts/jira-query.py` — team member ticket lookup and sprint story point summary
