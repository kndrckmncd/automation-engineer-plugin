# Audit Checklist

Run this checklist after creating any customization file. For each check that fails, **fix it immediately** before reporting results.

## All Primitives

| # | Check | Passing Criteria | Auto-fix |
|---|-------|-------------------|----------|
| 1 | **YAML frontmatter parses cleanly** | No unescaped colons in values, no tabs, all special chars quoted | Quote the value or escape the character |
| 2 | **`description` is keyword-rich** | Contains at least 3 explicit trigger phrases AND at least 1 "Do NOT use" clause | Add missing trigger phrases or disambiguation clauses |
| 3 | **`description` ≤ 1024 chars** | Character count within limit | Trim to most essential triggers and exclusions |
| 4 | **No secrets or credentials** | No API keys, tokens, passwords, or hardcoded URLs in the file | Remove and replace with environment variable references |

## Skills Only

| # | Check | Passing Criteria | Auto-fix |
|---|-------|-------------------|----------|
| 5 | **`name` matches folder** | `name` field equals the parent directory name exactly | Rename `name` field to match folder |
| 6 | **Has "When to Use" section** | Body contains a `## When to Use` heading with bullet triggers | Add section with triggers extracted from description |
| 7 | **Has step-by-step procedure** | Body contains numbered steps or a `## Procedure` heading | Add procedure section |
| 8 | **Line count ≤ target** | Skills ≤300, agents ≤80, prompts ≤40, instructions ≤50 | Extract large sections into `./references/` or trim filler |
| 8a | **Token budget** | SKILL.md ≤12KB (~3K tokens). Total with all references ≤28KB (~7K tokens). If over budget, move verbose content (templates, examples, tables) into `./references/` for lazy-loading. | Split large sections into reference files and link with `read_file` instructions |
| 8b | **References are lazy-loaded** | Large reference files (templates, checklists) are linked via relative Markdown links and loaded via `read_file` in the procedure step that needs them — not embedded inline in the SKILL.md body. | Move inline content to `./references/` and add `read_file` instruction at the relevant procedure step |
| 9 | **`argument-hint` present** | Frontmatter includes `argument-hint` | Add a hint based on the skill's purpose |
| 10 | **Bundled scripts created** | If the skill's procedure references executing scripts or calling external APIs, the corresponding scripts exist in `.github/scripts/` (API wrappers) or `.github/skills/<name>/scripts/` (helpers) | Create the missing script(s) using the templates in [templates.md](./templates.md) |
| 11 | **Scripts referenced in procedure** | Each bundled script is linked from the SKILL.md procedure via relative Markdown link | Add `[script_name.py](./scripts/script_name.py)` reference to the relevant procedure step |
| 11a | **No hardcoded project specifics** | Scripts and procedures use auto-detection, CLI args, or env vars instead of hardcoded project names, paths, or conventions. Project-specific notes are isolated in a dedicated section. | Replace hardcoded values with auto-detection or parameterized inputs |
| 11b | **Cross-platform compatible** | Scripts use a cross-platform language (Python or Node.js) unless explicitly unix-only. No hardcoded path separators (`/` or `\\`), no shell-specific syntax, no platform-specific tool paths (e.g., `/usr/local/bin/`). Uses `path.join()` / `os.path.join()` for paths and language-native APIs for file operations. | Convert bash scripts to Python/Node.js, or replace platform-specific calls with portable equivalents |
| 12 | **API wrapper registered** | If a new `.github/scripts/call_*.py` was created, it is listed in `copilot-instructions.md` under Approved API Entry Points | Add the entry to `copilot-instructions.md` |
| 12a | **`.env` auto-sourcing** | If the script requires env vars, it auto-sources from `.env` when vars are not already exported. Never fails silently when `.env` is missing — falls through to the `MISSING_ENV` error. | Add the `.env` sourcing pattern from [templates.md](./templates.md) before the env var validation block |

## Agents Only

| # | Check | Passing Criteria | Auto-fix |
|---|-------|-------------------|----------|
| 13 | **Single role / persona** | Body defines exactly one role, not multiple personas | Split into separate agents or narrow the role |
| 14 | **Minimal tools** | `tools` list contains only what the role needs — no unnecessary aliases | Remove unused tool aliases |
| 15 | **Has constraints section** | Body includes explicit "Do NOT" constraints | Add constraints from description's "Do NOT use" clauses |
| 16 | **Has output format** | Body specifies expected output structure | Add output format section |

## Prompts Only

| # | Check | Passing Criteria | Auto-fix |
|---|-------|-------------------|----------|
| 17 | **Single task focus** | Prompt addresses one well-defined task, not multiple | Split into separate prompts |
| 18 | **Output format specified** | Body includes expected output examples if structure matters | Add output format example |

## Instructions Only

| # | Check | Passing Criteria | Auto-fix |
|---|-------|-------------------|----------|
| 19 | **`applyTo` is appropriately scoped** | Uses specific globs, not `"**"` unless truly universal | Narrow the glob to relevant file types/folders |
| 20 | **One concern per file** | File addresses a single topic (not testing + styling + API design) | Split into separate instruction files |

## Report Format

Present results as a table:

```
## Audit Results — `<file-name>`

| # | Check | Result | Action Taken |
|---|-------|--------|--------------|
| 1 | YAML frontmatter | ✅ Pass | — |
| 2 | Keyword-rich description | ❌ Fail | Added 2 trigger phrases and 1 "Do NOT use" clause |
| 3 | Description length | ✅ Pass | — |
| ... | ... | ... | ... |

**All checks passing.** / **N issues found and fixed.**
```

If the audit produces fixes, show a summary of what changed so the user can review.
