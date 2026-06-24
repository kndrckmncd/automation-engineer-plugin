# Classification Decision Tree

Walk through in order. **Stop at the first match.**

## Q1: Is this an always-on guideline or coding standard?

- It applies to **most or all** work in the project (or to specific file types)
- It defines **rules, conventions, or standards** — not a task to perform
- Examples: "always use camelCase", "follow this API pattern for all controllers", "add error handling to all Python files"

**→ Instruction file** (`.instructions.md`)

## Q2: Does this need a persistent persona, tool restrictions, or role-based handoffs?

- It requires **restricting available tools** (e.g., read-only for a reviewer)
- It defines a **role or persona** the AI should adopt (e.g., security reviewer, architect)
- It uses **handoffs** to chain into another agent
- It needs **context isolation** — a subagent that returns a single focused output
- It requires a **specific model** different from the default

**→ Custom agent** (`.agent.md`)

## Q3: Does this involve a multi-step workflow with bundled resources?

- It has a **step-by-step procedure** with decision points or branching logic
- It needs **scripts, templates, reference docs, or examples** alongside the instructions
- It is a **repeatable capability** that benefits from progressive loading
- It works across VS Code, Copilot CLI, and Copilot coding agent (portability matters)

**→ Skill** (`SKILL.md` in a skill folder)

## Q4: Is this a single focused task with parameterized inputs?

- It performs **one well-defined task** (e.g., generate test cases, create a README, scaffold a component)
- It may accept **user arguments** but doesn't need scripts or multi-step procedures
- It's **lightweight** — instructions only, no bundled assets

**→ Reusable prompt** (`.prompt.md`)

## Ambiguity Tiebreakers

| Ambiguity | Resolution |
|-----------|------------|
| Could be instruction OR skill | Does it apply to *most* work? → Instruction. Only *specific tasks*? → Skill. |
| Could be skill OR prompt | Multi-step workflow with bundled assets? → Skill. Single task? → Prompt. |
| Could be skill OR agent | Same capabilities for all steps? → Skill. Different tool restrictions per stage or context isolation needed? → Agent. |
| Could be prompt OR agent | Need tool restrictions or a persistent persona? → Agent. Just a task template? → Prompt. |
