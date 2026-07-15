---
name: work-tracking-operations
description: "Use when updating project progress in Jira and logging delivery hours in Planview. Do NOT use for technical design or bot debugging."
allowed-tools:
  - shell
---

# Work Tracking Operations

## When to Use

- You need to move a Jira ticket to any swimlane/status.
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

## Instructions

### Jira Ticket Updates

You need only two things from the user:
1. **What ticket** — either an exact key (e.g. `CTFSLBEB-752`) or a keyword (e.g. "database table")
2. **Target swimlane** — e.g. `Done`, `Dev - In Progress`, `Code Review`, `Ready for QA`

**By ticket key:**
```
python ./scripts/jira-update.py --domain "manulife-cdn.atlassian.net" --email "manisea@mfcgd.com" --ticket "CTFSLBEB-752" --status "Done"
```

**By keyword search** (script finds the ticket automatically):
```
python ./scripts/jira-update.py --domain "manulife-cdn.atlassian.net" --email "manisea@mfcgd.com" --search "database table" --project "CTFSLBEB" --status "Done"
```

**List available swimlanes for a ticket:**
```
python ./scripts/jira-update.py --domain "manulife-cdn.atlassian.net" --email "manisea@mfcgd.com" --ticket "CTFSLBEB-752" --list-transitions
```

If a keyword search returns multiple matches, the script will list them — ask the user to clarify which one.

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

### Planview Time Tagging

- Use the correct Planview code for the work item.
- Log the number of hours actually worked.
- Confirm Planview reflects the time spent after logging.

## Output

- Jira transition summary (ticket, previous status, new status)
- Planview hour logging confirmation

## Error Handling

- If the target status is not a valid transition, the script will list available swimlanes — use `--list-transitions` to show them, then ask the user which one to use.
- If authentication fails (HTTP 401), ask the user to verify their API token.
- If the ticket is not found (HTTP 404), confirm the ticket key and domain.
- If a keyword search returns no results, try a shorter keyword or ask for the exact ticket key.

## Changelog

- 2026-07-15: Added Jira API integration via `scripts/jira-update.py`
- 2026-07-15: Added keyword search, any-swimlane support, and Story Points float validation workaround
