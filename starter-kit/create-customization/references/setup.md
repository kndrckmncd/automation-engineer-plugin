# Setup — Create Customization Skill

## Dependencies

- No external dependencies. This skill creates local files only.

## Prerequisites

- Workspace must have the standard `.github/` folder structure
- Instruction convention files must exist in `.github/instructions/` for validation

## Scope Paths

| Scope | Location |
|-------|----------|
| Workspace agents | `.github/agents/` |
| Workspace skills | `.github/skills/<name>/` |
| Workspace prompts | `.github/prompts/` |
| Workspace instructions | `.github/instructions/` |
| User profile prompts | `{{VSCODE_USER_PROMPTS_FOLDER}}` |
