---
description: "Use when creating or editing agent files (.agent.md). Enforces standard agent structure including frontmatter, routing table, shared constraints, auth references, and file paths."
applyTo: ".github/agents/*.agent.md"
---

# Agent File Conventions

## Structure

Every agent file must follow this structure:

1. **YAML frontmatter** — `name`, `description`, `tools`, `user-invocable`, `argument-hint`
2. **Role statement** — one sentence declaring what the agent is and what it orchestrates
3. **`## Routing`** — table mapping user intent to skill and key reference
4. **`## Shared Constraints`** — rules that apply across all skills
5. **Auth and connection sections** — one section per external system (ADX, Jira, etc.)
6. **`## File Paths`** — table of all runtime paths the agent uses

---

## Frontmatter Rules

```yaml
---
name: AgentName
description: "One sentence covering: what the agent does, which domains it covers, and trigger phrases."
tools: [execute, read, search, agent, todo]
user-invocable: true
argument-hint: "Concrete example invocations — e.g. 'errors in AlertsNotf last 1h'"
---
```

- `description` must include trigger phrases so VS Code can route `@AgentName` invocations correctly
- `tools` must be the minimal set needed — do not add tools the agent does not use
- `argument-hint` must show 2–3 concrete real-world examples, not abstract descriptions

---

## Routing Table Rules

The routing table is the agent's core dispatch mechanism. Every row must have:

| Column | Rule |
|--------|------|
| User Intent | Plain-language description of what the user is asking; use the same words a user would type |
| Skill | Skill name and procedure name where applicable (e.g., `jira → Bug Builder`) |
| Key Reference | File path to load for this route, if any — leave blank if the skill SKILL.md is sufficient |

- Every skill domain the agent covers must have at least one routing row
- If a route requires loading a specific reference file, put the path in Key Reference — do not scatter load instructions elsewhere in the file
- Add a catch-all note after the table for multi-domain requests (e.g., "execute sequentially")

---

## Shared Constraints Rules

- List only constraints that apply **across all skills** — skill-specific rules belong in SKILL.md
- Each constraint must be a single actionable bullet
- Always include: timestamp format, write-confirmation gates, and data-safety rules
- Do not duplicate constraints that are already enforced in SKILL.md

---

## Auth and Connection Sections

- One section per external system
- Reference env vars by name (e.g., `$JIRA_API_TOKEN`) — never hard-code credentials or URLs
- For error handling, link to the skill's `references/setup.md` — do not inline error tables in the agent file

---

## File Paths Table

Every script, client, and I/O directory the agent references at runtime must appear in the File Paths table. This is the single source of truth for paths — do not scatter paths throughout the file body.

---

## Size and Duplication Rules

- Keep the agent file under **80 lines** of content (excluding frontmatter)
- Do not copy content from SKILL.md into the agent file — use a one-line pointer instead
- Do not inline query patterns, error tables, or field schemas — those belong in skill reference files

---

## Adding a New Agent Checklist

- [ ] Frontmatter includes `name`, `description` with trigger phrases, `tools`, `user-invocable`, `argument-hint`
- [ ] Routing table covers every skill domain the agent orchestrates
- [ ] Shared Constraints section contains only cross-skill rules
- [ ] Each external system has its own auth/connection section referencing env vars only
- [ ] File Paths table lists every runtime path
- [ ] Agent file is under 80 lines of content
- [ ] Agent is registered in the VS Code `<agents>` block in the workspace instructions

---

## Personal Workflow Checklist

Before finalizing an agent file in this personal workspace:

- Verify frontmatter includes all required keys: `name`, `description`, `tools`, `user-invocable`, `argument-hint`
- Verify the required sections exist: `## Routing`, `## Shared Constraints`, `## File Paths`
- Ensure routing entries are clear, user-phrased, and mapped to exactly one skill/procedure each
- Keep shared constraints cross-skill only; move skill-specific detail back into the corresponding SKILL.md
- Prefer references over duplication so the agent file remains compact and maintainable
