---
description: "Use when creating or editing .prompt.md files. Enforces standard prompt structure including the Inputs for Analysis section with Required and Optional fields."
applyTo: ".github/prompts/*.prompt.md"
---

# Prompt File Conventions

## Structure

Every prompt file must follow this structure:

1. **YAML frontmatter** — `description`, `name`, `argument-hint`, `agent: "Miriam"`
2. **Purpose statement** — one-line summary of what the prompt does
3. **`## Inputs for Analysis`** — user-editable parameters (see format below)
4. **Remaining instructions** — query behavior, output requirements, scope constraints

## Inputs for Analysis Format

Every prompt must include a `## Inputs for Analysis` section near the top, immediately after the purpose statement. This section is the primary place where users update parameters before running the prompt.

```markdown
## Inputs for Analysis

Required:
- Date range (EST): <value>
- channel: <value>

Optional:
- sourceSystem:
- subChannel:
- Generate PDF: no
```

### Rules

- **Required fields** have values filled in — these must be provided for the prompt to work
- **Optional fields** are listed with empty values or defaults — leave blank to skip
- Use `<value>` as placeholder only in templates; real prompts must have concrete values
- Always include `Generate PDF: no` as an optional field when the prompt supports PDF output
- Date ranges must specify the timezone (EST) and exact start/end times
- Group all user-editable inputs in this one section — do not scatter parameters throughout the prompt body

---

## Personal Workflow Checklist

Before finalizing a prompt file in this personal workspace:

- Verify frontmatter includes: `description`, `name`, `argument-hint`, and `agent: "Miriam"`
- Verify `## Inputs for Analysis` appears near the top and includes both `Required:` and `Optional:` labels
- Keep required fields filled with actionable values; keep optional fields blank/defaulted when appropriate
- Remove repeated boilerplate and prefer linking to shared references in skill `references/` files
- Keep instructions unambiguous so future edits remain easy to understand
