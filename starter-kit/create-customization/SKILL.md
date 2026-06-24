---
name: create-customization
description: 'Classify a request as agent, skill, prompt, or instruction file, then create it. Triggers on: "should this be an agent or a skill", "create a customization for", "make this reusable", "classify this request". Do NOT use for editing existing customization files.'
argument-hint: 'Describe the capability or workflow you want to automate'
---

# Create Copilot Customization

Classify a user request, determine the right primitive(s) — **custom agent**, **skill**, **reusable prompt**, or **instruction file** — then create after approval.

## When to Use

- You're asked "should this be an agent or a skill" or "what kind of customization should I create"
- You want to "make this reusable" and need to pick and create the right primitive
- You need to decompose a complex request into multiple customization artifacts

## Setup

See [references/setup.md](./references/setup.md) for scope paths and prerequisites.

## Reference Data

- [Decision Tree](./references/decision-tree.md) — Classification logic for choosing the right primitive
- [Templates](./references/templates.md) — Boilerplate for each primitive type
- [Audit Checklist](./references/audit-checklist.md) — Validation checks for generated artifacts
- [Style & Scope](./references/style-and-scope.md) — Writing style rules, decomposition signals, scope/reusability guidelines

## Procedures

### Step 1 — Gather the Request

Ask the user (or extract from conversation history):
1. **What does it do?** — The outcome or behavior being automated.
2. **When is it used?** — Always-on, on-demand, or triggered by a specific task?
3. **What does it need?** — Tools, scripts, templates, external resources?
4. **Who uses it?** — Personal or team-shared?

### Step 2 — Decompose Composite Requests

Check whether the request contains multiple distinct capabilities. See [style-and-scope.md](./references/style-and-scope.md) for decomposition signals. For each capability identified, classify independently in Step 3.

### Step 3 — Classify Using the Decision Tree

Walk through the [Classification Decision Tree](./references/decision-tree.md). Stop at the first match.

### Step 4 — Present Classification and Ask for Approval

Present: **Type**, **Name**, **Location**, **Reasoning**, **What it will do** (bullets). Use `vscode_askQuestions` for approval before creating any file.

### Step 5 — Determine Scope

Evaluate reusability per [style-and-scope.md](./references/style-and-scope.md). Ask user via `vscode_askQuestions`: Workspace (recommended) or User profile.

### Step 6 — Create the Artifact(s)

Create in dependency order (skills before agents). Follow [Primitive Templates](./references/templates.md) and [Style & Scope](./references/style-and-scope.md) writing rules.

**Content must be generic unless the user explicitly requested project-specific content.** Do not reference project-specific paths (`src-temp/`, `src/modules/`), framework APIs (`context.log`, `Schema.safeParse()`), config constants (`config.DB_CONTAINERS.*`), or library-specific patterns. Instead, use universal descriptions (e.g., "parameterized queries" not "`@param` syntax") and instruct the agent/skill to read project instruction files at runtime for specifics.

#### Step 6a — Identify and Create Bundled Scripts (Skills only)

Determine if the skill needs scripts (API wrappers or helpers). See [templates.md](./references/templates.md) for script language selection, API wrapper template, and skill helper template. After creating scripts, update SKILL.md procedure steps to reference them.

### Step 7 — Validate

After creating the file:

1. Confirm the file is in the correct location for the chosen scope
2. Verify YAML frontmatter syntax (no unescaped colons, no tabs, quoted descriptions with special characters)
3. For skills: confirm `name` matches the parent folder name
4. For agents: confirm `tools` list follows least-privilege principle
5. For instructions: confirm `applyTo` is appropriately scoped (not overly broad)
6. Check that `description` contains keyword-rich trigger phrases for discovery
7. For skills with scripts: confirm scripts exist, are referenced in the procedure, and follow the correct template pattern (API wrapper or skill helper)

### Step 8 — Audit and Fix

After validation, run the [Audit Checklist](./references/audit-checklist.md) on each created file. **Lazy-load** the checklist via `read_file` only at this step — do not embed it in earlier context. For each check that fails, fix it immediately before reporting results. Present results using the report format in the checklist.

## Common Pitfalls

- **Description is the discovery surface.** Include explicit trigger phrases or the agent will never find the customization.
- **YAML frontmatter silent failures.** Quote descriptions with colons; use spaces not tabs; skill `name` must match folder.
- **Wrong primitive choice.** Re-classify if the first attempt feels wrong.
- **Missing scripts.** Skills accessing external systems need wrapper scripts — don't construct raw HTTP requests.
- **Project-specific content baked in.** Default to universal patterns; discover project specifics at runtime.
