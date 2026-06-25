---
name: rpa-bot-troubleshooting
description: "Use when an RPA bot fails and you need to reproduce the issue, find the failing line, and isolate the flaw step by step. Do NOT use for initial solution design or project administration."
---

# RPA Bot Troubleshooting

## When to Use

- A bot run has failed and the cause is not yet clear.
- You need to confirm where the flaw actually is before changing the bot.
- You want a repeatable debugging path instead of guessing.

## Procedure

1. Capture the failure context:
   - Bot name
   - Automation tool in use
   - Exact error or failing behavior
   - Relevant step, transaction, or data point involved
2. Reproduce the issue:
   - Run the bot again if it is safe to do so.
   - Confirm the failure is repeatable instead of assuming the first symptom was enough.
3. Locate the failing point:
   - Find which line or step failed.
   - Backtrack from that point to understand what led into it.
4. Debug step by step:
   - Run the bot in a controlled, stepwise way.
   - Check where the actual flaw appears instead of where the visible failure ended.
5. Recommend the correction:
   - Fix the flaw that caused the failure.
   - Re-run the affected path to confirm the issue no longer appears.
   - Note anything that should be handled in future runs to make the bot more adaptable.

## Output

- Troubleshooting summary
- Identified failing point and likely cause
- Recommended fix and re-test result
