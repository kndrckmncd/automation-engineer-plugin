# Automation Engineer Plugin

This plugin captures an Automation Engineer workflow focused on RPA bot delivery, production incident triage, and strict execution traceability.

## Included Agent

- `automation-engineer` in `agents/automation-engineer.agent.md`

## Included Local Skills

- `rpa-production-triage`
- `rpa-delivery-quality`
- `work-tracking-operations`

## Included Reusable External Skills

Configured via `.plugin/sources.json`:

- `jira-search`
- `jira-get`
- `jira-create`
- `jira-comment`
- `jira-update`
- `jira-transition`

## Working Rules Captured

- Start production investigation immediately when needed.
- Ensure a Jira ticket is created within the same day.
- Choose quick patching for urgent multi-transaction blockage.
- Prefer long-term fixes when urgency is lower.
- Do not ship without proper testing and validation.

## Communication Style Captured

- Formal, direct, and respectful.

## Author

- sean manicad
- sean_kendrick_manicad@manulife.ca
