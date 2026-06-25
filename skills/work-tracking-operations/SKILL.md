---
name: work-tracking-operations
description: "Use when updating project progress in Jira and logging delivery hours in Planview. Do NOT use for technical design or bot debugging."
---

# Work Tracking Operations

## When to Use

- You need to reflect delivery progress in Jira.
- You must log worked hours against the correct Planview code.
- You want ticket status and time tracking to stay aligned.

## Procedure

1. Jira updates:
   - Pull the item from backlog when work starts.
   - Move it to in progress during development.
   - Assign it to testing when development is done.
   - Move it through code review and then to done once approved.
2. Planview time tagging:
   - Use the correct Planview code.
   - Log the number of hours actually worked on that code.
3. Closure check:
   - Confirm Jira reflects the current delivery stage.
   - Confirm Planview reflects the time spent.

## Output

- Jira progress update summary
- Planview hour logging confirmation
