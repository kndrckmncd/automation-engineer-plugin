---
name: pdd-to-sdd-design
description: "Use when a new PDD arrives and you need to analyze the requirements, choose the automation approach, and turn it into an SDD direction. Do NOT use for bot debugging or routine status updates."
---

# PDD to SDD Design

## When to Use

- A new PDD has arrived for analysis.
- You need to decide how the bot should be designed before development starts.
- You must recommend reuse, tool choice, or new technology based on the requirement.

## Procedure

1. Review the PDD:
   - Read the stated requirements carefully.
   - Identify the business flow, tool dependencies, and any unclear points.
2. Check the implementation options:
   - Confirm which tools are in scope, such as Power Automate, AA360, or MS SQL.
   - Look for reusable scripts or existing components first.
   - Consider new technology only when reuse will not satisfy the requirement.
3. Shape the approach:
   - Factor in the time constraint.
   - Choose the most practical design that still covers likely situations the bot will face.
4. Prepare the SDD direction:
   - Describe the recommended solution flow.
   - Call out dependencies, assumptions, and areas needing approval before build starts.
5. Hand off to development:
   - Proceed once the SDD approach is approved.
   - Carry the design intent into build, SIT, UAT, and deployment preparation.

## Output

- PDD analysis summary
- Recommended automation approach
- SDD-ready design notes and approval points
