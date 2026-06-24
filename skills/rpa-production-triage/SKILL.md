---
name: rpa-production-triage
description: "Use when investigating production RPA bot failures, collecting incident facts, and deciding quick patch versus long-term fix. Do NOT use for greenfield bot design or non-incident brainstorming."
---

# RPA Production Triage

## When to Use

- A production bot run has failed.
- You need structured data before analysis starts.
- You must decide restoration-first patching or durable remediation.

## Procedure

1. Capture required facts:
   - Bot name
   - Automation platform/tool
   - Exact error message
   - SQL transaction ID where failure occurred
2. Verify tracking:
   - Confirm there is a Jira ticket.
   - If missing, continue immediate investigation and require ticket creation within the same day.
3. Measure impact:
   - Number of blocked transactions
   - User or process exposure
   - Deadline or SLA pressure
4. Choose fix strategy:
   - Quick patch if active blockage affects multiple transactions.
   - Long-term fix when impact is controlled and quality improvement is the priority.
5. Validate outcome:
   - Re-run impacted path.
   - Confirm expected transaction state in SQL.
   - Record evidence in the Jira ticket.
6. Communicate status formally:
   - Current state
   - Root cause (known or suspected)
   - Fix type selected
   - Next update time

## Output

- Incident triage summary
- Explicit fix strategy decision
- Validation evidence and next actions
