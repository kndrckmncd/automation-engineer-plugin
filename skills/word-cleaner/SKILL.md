---
name: word-cleaner
description: >
  Updates the notes page of a Word (.docx) document by inserting the accessibility
  line "This document has been made accessible" and updating the Revised Date field
  to today's date (YYYY-MM-DD). Use this when asked to clean up a Word file,
  mark a document as accessible, or update the revised date on a Word document.
allowed-tools:
  - shell
---

## Purpose

Update a Word (.docx) document by making two changes:

1. **Accessibility line** — append `"This document has been made accessible"` to the
   **notes page (first page)** if not already present.
2. **Booklet produced date** — find the `"This booklet produced:"` field on the
   **second page** and update its date to today in `YYYY-MM-DD` format.

The updated document overwrites the original by default, or is saved as
`<name>_clean.docx` when the user asks to keep the original.

## Prerequisites

- Python 3.8+ available (`python --version` or `python3 --version`)
- `python-docx` package — install with `pip install python-docx` if missing

## Bundled Resources

- `./scripts/clean-word.py` — performs the update; run directly via Python

## Instructions

1. **Before doing anything else**, require the user to provide both:
   - The **full file path** to the Word document (e.g. `C:\Users\name\Documents\report.docx`)
   - The **file name** (confirm it matches the path)

   If either is missing, stop and ask:
   > "Please provide the full file path and file name of the Word document you'd like to clean up."

   Do not proceed until both are explicitly given.

2. Check that `python` (or `python3`) is available. If not, inform the user and stop.
3. Check that `python-docx` is installed:
   ```
   python -c "import docx" 2>&1
   ```
   If missing, run `pip install python-docx` before proceeding.
4. Run the cleaning script using the provided path. Always overwrite the original by default:
   ```
   python ./scripts/clean-word.py --input "<full-path-to-docx>" --overwrite
   ```
   Only create a separate `_clean` copy if the user explicitly asks to keep the original:
   ```
   python ./scripts/clean-word.py --input "<full-path-to-docx>"
   ```
5. Report the result to the user:
   - Whether the accessibility line was added to the notes page (or was already present)
   - Whether the "This booklet produced:" date was updated, and what the new value is
   - The path to the saved output file

## Examples

### Example 1: Happy path — clean a Word document

**User says:** "Clean up my Word file."

**Skill asks:** "Please provide the full file path and file name of the Word document you'd like to clean up."

**User provides:** `C:\Users\name\Documents\benefit_booklet.docx`

**Skill does:**
1. Confirms file path and name.
2. Verifies Python and `python-docx` are available.
3. Runs `python ./scripts/clean-word.py --input "C:\Users\name\Documents\benefit_booklet.docx" --overwrite`.

**Result:**
```
✅ Word document updated: benefit_booklet.docx
   - Accessibility line added to notes page (page 1) ✅
   - "This booklet produced" date updated to: 2026-07-06 ✅
```

### Example 2: Accessibility line already present

**Result:**
```
✅ Word document updated: benefit_booklet.docx
   - Accessibility line already present on notes page — skipped
   - "This booklet produced" date updated to: 2026-07-06 ✅
```

### Example 3: Keep original — save as new file

**User says:** "Clean it but keep the original."

**Skill does:** Runs the script without `--overwrite`; saves as `benefit_booklet_clean.docx`.

## Error Handling

- If the file does not exist, print a clear error and stop — do not proceed.
- If the file is not a `.docx`, report the error and stop.
- If `python-docx` is missing, offer to install it (`pip install python-docx`) before retrying.
- If the `"This booklet produced:"` field is not found on the cover page (page 2, between the first and second page breaks), report it clearly — the field may be named differently in this document.

## Constraints

- Always overwrite the original file by default. Only create a `_clean` copy if the user explicitly asks to keep the original.
- Never commit secrets or credentials — this skill needs no auth.
- Always report what changed so the user can verify.
- Do not alter any content outside the notes page.
- Today's date is always formatted as `YYYY-MM-DD`.

## Changelog

- 2026-07-02: Initial version
- 2026-07-03: Accessibility line now appended to notes page (page 1); date update targets "This booklet produced:" field on cover page (page 2, between first and second page breaks)
- 2026-07-06: Accessibility line now matches font name and size of surrounding notes page paragraphs
