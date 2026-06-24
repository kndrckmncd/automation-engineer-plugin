# Primitive Templates

Use the template matching the classified primitive type. **Keep all generated files concise** — short sentences, bullet lists over prose, no filler. Every line must be actionable.

## Instruction

```yaml
---
description: "Use when... [keyword-rich trigger phrases]"
applyTo: "<glob pattern or omit for on-demand only>"
---
```

- One concern per file
- Concise, actionable rules — bullets over prose, no preamble
- Use specific `applyTo` globs; avoid `"**"` unless truly universal
- Target ≤50 lines

## Agent

```yaml
---
description: "Use when... [keyword-rich trigger phrases for subagent discovery]"
tools: [<minimal set of tool aliases>]
---
```

- Single role with focused responsibilities
- Minimal tools — only what the role needs
- Clear constraints: define what the agent should NOT do
- Include approach steps and output format
- Target ≤80 lines — cut anything the agent can infer from context

## Skill

```yaml
---
name: <lowercase-hyphenated, must match folder name>
description: '<max 1024 chars, starts with trigger phrases, includes Do NOT use clauses>'
---
```

- "When to Use" section with bullet triggers
- Step-by-step \"Procedure\" section — imperative verbs, no filler
- Keep SKILL.md under 300 lines; use `./references/` for large content
- Reference bundled scripts/templates via relative Markdown links
- Description must include positive triggers AND "Do NOT use" disambiguation

### Script Language Selection — Cross-Platform

Choose the script language based on portability needs:

| Language | When to use | Platform |
|----------|------------|----------|
| **Python** | API wrappers, data processing, complex logic | macOS, Windows, Linux |
| **Node.js** | Projects already using Node, npm-based tooling | macOS, Windows, Linux |
| **Bash** | Simple unix-only orchestration, CI scripts | macOS, Linux only |

**Default to Python or Node.js** for cross-platform skills. Use bash only when the skill is explicitly unix-only (e.g., macOS dev tooling).

**Cross-platform rules for all scripts:**
- Use `path.join()` or `os.path.join()` — never hardcode `/` or `\\` as path separators
- Use `process.env` / `os.environ` — never rely on shell-specific syntax like `$VAR`
- Use `which` / `shutil.which()` / `npx which` to find executables — never assume paths like `/usr/local/bin/`
- For file operations, use language-native APIs (`fs`, `pathlib`) — never shell commands like `cp`, `mv`, `rm`
- Test with both forward-slash and backslash paths if accepting user input

**Node.js skill helper script template:**

```javascript
#!/usr/bin/env node
/**
 * <script_name>.js — <One-line description>.
 *
 * Usage:
 *   node .github/skills/<name>/scripts/<script_name>.js [--workspace <path>]
 *
 * Exits with code 0 and prints result to stdout on success.
 * Exits with code 1 and prints structured error JSON to stderr on failure.
 */

const { randomUUID } = require('crypto');
const path = require('path');
const fs = require('fs');

function fatal(errorCode, message) {
  const error = {
    error_code: errorCode,
    message,
    correlation_id: randomUUID(),
    timestamp: new Date().toISOString(),
  };
  console.error(JSON.stringify(error));
  process.exit(1);
}

function loadEnv(prefix) {
  const envFile = path.join(process.cwd(), '.env');
  if (!fs.existsSync(envFile)) return;
  for (const line of fs.readFileSync(envFile, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (trimmed.startsWith(`${prefix}_`) && trimmed.includes('=')) {
      const [key, ...rest] = trimmed.split('=');
      if (!process.env[key]) {
        process.env[key] = rest.join('=').replace(/^["']|["']$/g, '');
      }
    }
  }
}

// ... script logic ...
```

**Required conventions (Node.js):**
- Structured error JSON to stderr (same format as Python scripts)
- Use `path.join()` for all file paths
- Auto-source from `.env` using `loadEnv()` pattern above
- No shell-exec calls (`child_process.exec('rm ...')`) — use `fs` APIs

### API Wrapper Script

Place in `.github/scripts/call_<system>.py`. Use when the skill accesses an external system via API.

```python
"""
call_<system>.py — Approved <System Name> REST API wrapper.

Operations: <list operations>

Credentials are read exclusively from environment variables:
  <SYSTEM>_BASE_URL  — e.g. https://...
  <SYSTEM>_API_TOKEN — API token or OAuth 2.0 bearer token
"""

import json, os, sys, time, uuid, urllib.request, urllib.error, urllib.parse

_DEFAULT_TIMEOUT = 30
_MAX_RETRIES = 3
_RETRY_TRANSIENT = {"API_UNAVAILABLE", "RATE_LIMITED"}

def _fatal(error_code: str, message: str) -> None:
    error = {
        "error_code": error_code,
        "message": message,
        "correlation_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(error), file=sys.stderr)
    sys.exit(1)

# ... auth from env vars, HTTP helpers with retry, response sanitization ...
# See existing wrappers in .github/scripts/ for the full pattern.
```

**Required conventions:**
- Credentials from environment variables only — never as arguments
- Auto-source from `.env` if vars are not already exported (see pattern below)
- Structured error JSON to stderr: `{"error_code", "message", "correlation_id", "timestamp"}`
- Retry with exponential backoff for transient errors (429, 5xx)
- Sanitize responses — redact sensitive keys recursively
- Idempotency keys for write operations
- Register in `copilot-instructions.md` under **Approved API Entry Points**

**`.env` auto-sourcing pattern (bash):**
```bash
# Source from .env if vars are not already exported
if [[ -z "${REQUIRED_VAR:-}" ]] && [[ -f .env ]]; then
  echo "==> Sourcing <PREFIX>_* vars from .env..."
  export $(grep -E '^<PREFIX>_' .env | xargs)
fi
```

**`.env` auto-sourcing pattern (Python):**
```python
import os
from pathlib import Path

def _load_env(prefix: str) -> None:
    env_file = Path(".env")
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{prefix}_") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key, value.strip('"').strip("'"))
```

### Skill Helper Script

Place in `.github/skills/<name>/scripts/`. Use for skill-specific routines that don't access external APIs (e.g., auto-detection, workspace scanning, data transformation).

```python
"""
<script_name>.py — <One-line description>.

Usage:
    python .github/skills/<name>/scripts/<script_name>.py [--workspace <path>]

Exits with code 0 and prints result to stdout on success.
Exits with code 1 and prints structured error JSON to stderr on failure.
"""

import json, os, sys, uuid
from datetime import datetime, timezone

def _error(error_code: str, message: str) -> None:
    payload = {
        "error_code": error_code,
        "message": message,
        "correlation_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(payload), file=sys.stderr)
    sys.exit(1)

# ... detection / scanning / transformation logic ...
```

**Required conventions:**
- Structured error JSON to stderr (same format as API wrappers)
- No credentials or hardcoded URLs
- Auto-source from `.env` if the script requires env vars (use the pattern from API Wrapper section)
- Accept workspace path as CLI argument with sensible default

## Prompt

```yaml
---
description: "<what this prompt does>"
agent: "agent"
---
```

- Single task focus — one prompt = one well-defined task
- Include output format examples if structure matters
- Use `${input:variableName}` for parameterized inputs
- Reference instruction files instead of duplicating guidelines
- Target ≤40 lines — a prompt should be scannable in seconds
