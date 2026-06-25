# Automation Engineer Plugin

> Automation Engineer for RPA solution design, bot development, troubleshooting, and disciplined work tracking.

## What This Plugin Does

This plugin captures an RPA Developer workflow from the moment a PDD arrives through solution design, development, testing support, and deployment readiness. It also covers the repeatable day-to-day work of troubleshooting bot failures and keeping delivery traceable through Jira and Planview.

## Persona

The **Automation Engineer** agent brings the perspective of an RPA developer who checks the tools first, reuses proven scripts when practical, and debugs by reproducing issues instead of guessing. It stays direct, detailed, and grounded in real delivery constraints like templates, approvals, SIT, UAT, and time pressure.

## Included Agent

- `automation-engineer` in `agents/automation-engineer.agent.md`

## Skills

| Skill | Description |
|-------|-------------|
| `pdd-to-sdd-design` | Reviews a PDD, chooses the automation approach, and prepares SDD-ready design notes. |
| `rpa-bot-troubleshooting` | Reproduces a failure, finds the failing line, and isolates the flaw step by step. |
| `work-tracking-operations` | Keeps Jira progress and Planview hour logging aligned with delivery work. |
| `jira-search` | Reusable external Jira search support. |
| `jira-get` | Reusable external Jira issue retrieval support. |
| `jira-create` | Reusable external Jira issue creation support. |
| `jira-comment` | Reusable external Jira commenting support. |
| `jira-update` | Reusable external Jira update support. |
| `jira-transition` | Reusable external Jira workflow transition support. |

## Included Reusable External Skills

Configured via `.plugin/sources.json`:

- `jira-search`
- `jira-get`
- `jira-create`
- `jira-comment`
- `jira-update`
- `jira-transition`

## Usage

Invoke the **Automation Engineer** agent when you need:
- A PDD turned into a practical RPA solution direction
- A bot issue reproduced and traced back to the real flaw
- Jira progress and Planview hours kept in sync with delivery work

## Examples

```
@automation-engineer Review this PDD and give me the SDD direction. Tell me whether we should reuse an existing script or use a new approach.
```

```
@automation-engineer The bot failed in AA360. Help me reproduce it, find the failing line, and identify the likely fix.
```

## Working Rules Captured

- Check the tools involved before choosing the automation approach.
- Reuse old scripts where practical before introducing new technology.
- Let time constraints influence the path without dropping core quality.
- Reproduce issues and backtrack from the failing line before fixing.
- Build automations that can adapt to real situations as much as possible.

## Communication Style Captured

- Direct, detailed, and balanced.

## Contributing

To update this plugin's persona or skills, use **The Diskillery**:

```
/agent diskillery
update the automation-engineer plugin
```

Or edit the files directly:
- Persona: `agents/automation-engineer.agent.md`
- Skills: `skills/<skill-name>/SKILL.md`
- Metadata: `.plugin/plugin.json`

## Author

- sean manicad
- sean_kendrick_manicad@manulife.ca
