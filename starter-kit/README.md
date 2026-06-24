# Agent Starter Kit

Everything your team needs to start building a VS Code Copilot agent.

## Setup (2 steps)

**1. Drop `create-customization/` into your `.github/skills/` folder**

```
your-workspace/
  .github/
    skills/
      create-customization/   ← drop here
```

**2. Drop the 3 files from `instructions/` into your `.github/instructions/` folder**

```
your-workspace/
  .github/
    instructions/
      agent-conventions.instructions.md
      skill-conventions.instructions.md
      prompt-conventions.instructions.md
```

---

## How to Use

Open Copilot Chat and say:

```
Create a customization for [describe what you want your agent to do]
```

The skill will guide you through the rest — classifying the request, presenting a plan, and generating the files with proper structure.

---

## What's Included

| File | Purpose |
|------|---------|
| `create-customization/SKILL.md` | Main skill — guides you through building any agent customization |
| `create-customization/references/decision-tree.md` | Choose between agent, skill, prompt, or instruction |
| `create-customization/references/templates.md` | Boilerplate for every primitive type |
| `create-customization/references/style-and-scope.md` | Writing rules and reusability guidelines |
| `create-customization/references/audit-checklist.md` | Validation checks to run after creating any file |
| `instructions/agent-conventions.instructions.md` | Auto-applied rules when editing `.agent.md` files |
| `instructions/skill-conventions.instructions.md` | Auto-applied rules when editing skill files |
| `instructions/prompt-conventions.instructions.md` | Auto-applied rules when editing `.prompt.md` files |

---

## The Four Primitives

| Type | Use When |
|------|----------|
| **Agent** | Persistent persona, tool restrictions, or multi-skill routing |
| **Skill** | Multi-step workflow with scripts, templates, or reference data |
| **Prompt** | Single focused task with parameterized inputs |
| **Instruction** | Always-on coding standards for specific file types |

Not sure which one fits? The `create-customization` skill will figure it out for you.
