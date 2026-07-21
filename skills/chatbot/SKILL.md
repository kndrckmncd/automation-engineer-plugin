---
name: chatbot
description: >
  Terminal chatbot that routes natural language requests to plugin skills.
  Use this when the user wants to launch the interactive bot, trigger skills
  conversationally, or says "open the bot", "start the chatbot", "run the bot".
allowed-tools:
  - shell
---

## Purpose

A mini terminal chatbot that lets users trigger plugin skills using plain
English, without needing to remember script arguments or file paths.

## Prerequisites

- Python 3.8+
- `python-pptx` installed for PowerPoint creation (`pip install python-pptx`)
- `rich` recommended for a better UI (`pip install rich`)
- `JIRA_API_TOKEN` environment variable set for Jira operations

## Bundled Resources

- `./scripts/chatbot.py` — the interactive chatbot

## Instructions

### Launch the bot

```
python ./scripts/chatbot.py
```

The bot starts an interactive loop. No arguments needed.

### What the bot can do

| Skill | Example phrases |
|-------|----------------|
| PowerPoint | "create a ppt about RPA", "make a deck for the MLM project" |
| Jira Move  | "move ticket CTFSLBEB-809 to Done", "transition issue to Dev In Progress", "move my booklets ticket to done" |
| Jira Find  | "find ticket database table", "search for ticket accesses" |
| Jira List  | "list my tickets", "show all mlm tickets" |
| Team Tickets | "show joshua ilunio's tickets", "what is shara faelga working on" |
| Sprint Points | "how many story points are left", "sprint progress for joshua" |
| Gliffy     | "create a diagram for advisor termination", "make a flowchart of the process" |

> **Confluence context**: When creating a presentation, the bot automatically searches Confluence space `CDTPACS` for relevant pages and uses that content to generate accurate, project-specific slides.

Type `help` inside the bot to see all commands.
Type `quit` or press Ctrl+C to exit.

## Examples

### Example 1 — Start the bot directly

**User says:** "run the bot" or "open the chatbot"

**Skill does:** Runs `python ./scripts/chatbot.py` in the terminal.

### Example 2 — Invoke from the CLI

```bash
python skills/chatbot/scripts/chatbot.py
```

## Constraints

- The bot runs interactively — it cannot be used non-interactively
- Jira operations require `JIRA_API_TOKEN` to be set
- All PPTs are saved to `C:\Users\manisea\OneDrive - Manulife\Documents\COPILOT_TEST\PPT Creation\`
- Gliffy diagrams are saved to the Downloads folder

## Changelog

- 2026-07-15: Initial version — PPT, Jira, Gliffy skill routing
- 2026-07-16: Added team member ticket lookup, sprint story points, help command fix, task status indicators
- 2026-07-16: Added Confluence context enrichment for PPT generation (space CDTPACS)
