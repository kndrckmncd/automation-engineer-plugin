---
description: "Use when creating or editing skill files (SKILL.md, references/, scripts/). Enforces standard skill structure, separates procedures from reference data, and keeps shared queries in named library files."
applyTo: ".github/skills/**"
---

# Skill File Conventions

## Required Folder Structure

Every skill must follow this layout:

```
.github/skills/<skill-name>/
  SKILL.md              ← procedures and routing only
  references/           ← domain knowledge, schemas, stored queries
  scripts/              ← executable code
```

A `references/` folder is required for every skill. At minimum it must contain a setup guide (auth, env vars, dependencies).

---

## SKILL.md Rules

SKILL.md must stay **procedure-focused**. It tells the agent *what to do and when*, not *how queries are written*.

### Must include
- YAML frontmatter: `name`, `description`
- **When to Use** — bullet list of trigger scenarios
- **Procedures** — numbered steps or named sub-procedures with links to reference files
- **Setup** — pointer to `references/setup.md`

### Must NOT include
- Raw KQL, JQL, SQL, or other query blocks — put these in `references/`
- Field schemas or table definitions — put these in `references/tables.md` or equivalent
- Large inline examples that duplicate content already in a reference file

### Size target
Keep SKILL.md under **100 lines**. If it grows beyond that, move the excess into a reference file and replace with a one-line pointer.

---

## Reference File Rules

### Stored query libraries
Any skill that runs queries must have a named query library file:

| Skill | File |
|-------|------|
| `adx` | `references/querying.md` |
| `jira` | `references/common-jql.md` |
| New skills | `references/common-<query-language>.md` |

Query library files must use **named, parameterized templates** — replace runtime values with `<PLACEHOLDER>` tokens. Do not hard-code dates, project keys, or environment values.

### Shared boilerplate
If two or more prompts share the same query shape, output requirements, or execution rules, extract the shared content into a reference file (e.g., `alertsnotf-latency-shared.md`) and have each prompt reference it by path.

---

## Prompt–Skill Integration

When a prompt invokes a skill's shared reference:

```markdown
Load and follow `.github/skills/<skill>/references/<file>.md` for the [KQL template / JQL templates / execution requirements / output format].
```

The prompt then only contains its unique `## Inputs for Analysis` section and any channel- or workflow-specific overrides.

---

## Adding a New Skill Checklist

- [ ] Create `SKILL.md` with frontmatter, When to Use, Procedures, and Setup sections
- [ ] Create `references/setup.md` covering env vars, auth, and dependency installation
- [ ] Create `references/common-<query-language>.md` if the skill runs queries
- [ ] Add the skill to Athena's routing table in `.github/agents/athena.agent.md`
- [ ] Register the skill in the `<skills>` block in the VS Code agent instructions (copilot-instructions or settings)
- [ ] Verify SKILL.md is under 100 lines before committing

---

## Personal Workflow Checklist

Before finalizing a skill in this personal workspace:

- Verify folder structure stays consistent: `SKILL.md`, `references/`, `scripts/`
- Verify SKILL.md includes `## When to Use`, `## Procedures`, and a setup pointer to `references/setup.md`
- Keep SKILL.md procedural; move raw queries, schemas, and bulky examples into `references/`
- Reuse named templates for repeated query patterns instead of hard-coding runtime values
- Keep instructions concise so the skill remains easy to maintain as it grows
