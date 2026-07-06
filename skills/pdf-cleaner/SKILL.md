---
name: pdf-cleaner
description: >
  Removes blank pages and "DELETE NOTES PAGE BEFORE PUBLICATION" notes pages
  from PDF files and saves a clean copy. Use this when asked to clean up a PDF,
  strip blank pages, remove notes pages, or prepare a PDF for publication.
allowed-tools:
  - shell
---

## Purpose

Clean a PDF file by removing two categories of unwanted pages:

1. **Blank pages** — pages with no extractable text content.
2. **Notes pages** — pages containing the marker phrase
   `DELETE NOTES PAGE BEFORE PUBLICATION` (case-insensitive).

The cleaned PDF is saved alongside the original with a `_clean` suffix, or
overwrites the original when `--overwrite` is passed.

## Prerequisites

- Python 3.8+ available (`python --version` or `python3 --version`)
- `pypdf` package — install with `pip install pypdf` if missing

## Bundled Resources

- `./scripts/clean-pdf.py` — performs the cleaning; run directly via Python

## Instructions

1. **Before doing anything else**, require the user to provide both:
   - The **full file path** to the PDF (e.g. `C:\Users\name\Documents\report.pdf`)
   - The **file name** (confirm it matches the path)

   If either is missing, stop and ask:
   > "Please provide the full file path and file name of the PDF you'd like to clean up."

   Do not proceed until both are explicitly given.

2. Check that `python` (or `python3`) is available. If not, inform the user and stop.
3. Check that `pypdf` is installed:
   ```
   python -c "import pypdf" 2>&1
   ```
   If missing, run `pip install pypdf` before proceeding.
4. Run the cleaning script using the provided path. Always overwrite the original by default:
   ```
   python ./scripts/clean-pdf.py --input "<full-path-to-pdf>" --overwrite
   ```
   Only create a separate `_clean` copy if the user explicitly asks to keep the original:
   ```
   python ./scripts/clean-pdf.py --input "<full-path-to-pdf>"
   ```
5. Report the result to the user: how many pages were removed, which categories
   (blank / notes), and the path to the saved output file.
6. If zero pages were removed, tell the user the PDF was already clean and no
   output file was written.

## Examples

### Example 1: Happy path — clean a single PDF

**User says:** "Clean up my PDF."

**Skill asks:** "Please provide the full file path and file name of the PDF you'd like to clean up."

**User provides:** `C:\Users\name\reports\Q2_deck.pdf`

**Skill does:**
1. Confirms file path and name: `Q2_deck.pdf` at `C:\Users\name\reports\`.
2. Verifies Python and `pypdf` are available.
3. Runs `python ./scripts/clean-pdf.py --input "C:\Users\name\reports\Q2_deck.pdf"`.
3. Script removes 2 blank pages and 1 notes page (3 of 18 total).

**Result:**
```
✅ PDF cleaned: ./reports/Q2_deck_clean.pdf
   - Removed 2 blank page(s)
   - Removed 1 notes page(s)
   - 15 pages remaining
```

### Example 2: Overwrite the original

**User says:** "Clean `draft.pdf` and save it in place."

**Skill does:** Runs the script with `--overwrite`; original file is replaced.

**Result:**
```
✅ PDF cleaned (overwritten): draft.pdf
   - Removed 1 blank page(s)
   - Removed 1 notes page(s)
   - 12 pages remaining
```

### Example 3: Already clean PDF

**User says:** "Clean `final.pdf`."

**Skill does:** Runs the script; no qualifying pages found.

**Result:**
```
ℹ️ No changes needed — final.pdf has no blank or notes pages.
```

## Error Handling

- If the file does not exist, print a clear error and stop — do not proceed.
- If the file is not a valid PDF, report the parse error and stop.
- If `pypdf` is missing, offer to install it (`pip install pypdf`) before retrying.
- If the cleaned PDF would have zero pages, abort and warn the user rather than
  writing an empty PDF.

## Constraints

- Never overwrite the original unless `--overwrite` is explicitly passed.
+ Always overwrite the original file by default. Only create a `_clean` copy if the user explicitly asks to keep the original.
- Never commit secrets or credentials — this skill needs no auth.
- Always report page counts (removed and remaining) so the user can verify.
- Do not alter page content — only remove entire pages.

## Changelog

- 2026-07-01: Initial version
- 2026-07-01: Require user to provide full file path and file name before any action is taken
- 2026-07-01: Overwrite original file by default; only create _clean copy when user requests it
