---
name: rpa-delivery-quality
description: "Use when building or enhancing RPA bots and preparing changes for release with quality gates. Do NOT use for administrative updates like leave filing or time tagging."
---

# RPA Delivery Quality

## When to Use

- A bot feature or bug fix is being implemented.
- You need a release-ready checklist with strong test coverage.
- A rush change must still pass minimum quality requirements.

## Procedure

1. Define scope and acceptance:
   - Clarify expected behavior and transaction outcomes.
   - Confirm dependencies in Power Automate, AA360, and MS SQL.
2. Implement incrementally:
   - Keep changes scoped to the smallest effective unit.
   - Add guardrails for known error conditions.
3. Execute tests:
   - Happy-path test
   - Error-path test
   - Regression checks for impacted transactions
4. Validate data integrity:
   - Confirm SQL transaction state is correct before and after execution.
5. Release recommendation:
   - Approve only if behavior is correct and evidence is documented.
   - Otherwise hold release and list required fixes.

## Output

- Delivery readiness summary
- Test evidence checklist
- Release recommendation with risk note
