# Writing Style & Scope Guidelines

## Writing Style — Concise and Generic by Default

All generated markdown files (agents, skills, prompts, instructions) MUST be **concise, straightforward, and generic**:

- Use short, direct sentences. Cut filler words.
- Prefer bullet lists over prose paragraphs.
- One idea per bullet. No nested sub-bullets unless essential.
- Omit obvious context — the reader is a developer, not a beginner.
- Procedure steps: imperative verb first, then the essential detail. No preamble.
- Skip sections that add no value (e.g., don't add "Overview" if the description already covers it).
- Target line counts: instructions ≤50 lines, prompts ≤40 lines, agents ≤80 lines, skills ≤300 lines (excluding references).
- **Generic by default.** Never embed project-specific references unless the user explicitly requests it.

## Decomposition Signals

**Split when you see:**
- A **data/system access** concern paired with a **reasoning/analysis** concern
- A **reusable capability** paired with a **persona or workflow** that consumes it
- Multiple **independent actions** joined by "and" that serve different purposes
- A request that names **two or more external systems** each requiring their own procedures

**Keep together when:**
- All parts serve a single coherent task
- Splitting would create artifacts that are never used independently

## Scope & Reusability

Before asking scope, evaluate reusability:

- **Project-specific?** → Workspace scope. Hardcode details in a config section, not throughout.
- **Portable across projects?** → User profile scope. Use auto-detection or CLI args.
- **Could be either?** → Default to generic content in workspace scope.

**Reusability checklist:**
- No hardcoded project names, paths, or team-specific URLs in procedures or scripts
- Use auto-detection from config files for defaults
- Accept CLI args or env vars for values that differ between projects
- Isolate project-specific notes in a dedicated section

**Path mapping:**
- **Workspace** → `.github/agents/`, `.github/skills/<name>/`, `.github/prompts/`, or `.github/instructions/`
- **User profile** → user prompts folder or `~/.copilot/skills/<name>/`
