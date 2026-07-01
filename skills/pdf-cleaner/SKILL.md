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

1. Confirm the user has provided a PDF file path. If not, ask for it.
2. Check that `python` (or `python3`) is available. If not, inform the user and stop.
3. Check that `pypdf` is installed:
   ```
   python -c "import pypdf" 2>&1
   ```
   If missing, run `pip install pypdf` before proceeding.
4. Run the cleaning script:
   ```
   python ./scripts/clean-pdf.py --input "<path-to-pdf>"
   ```
   To overwrite the original instead of creating a `_clean` copy:
   ```
   python ./scripts/clean-pdf.py --input "<path-to-pdf>" --overwrite
   ```
5. Report the result to the user: how many pages were removed, which categories
   (blank / notes), and the path to the saved output file.
6. If zero pages were removed, tell the user the PDF was already clean and no
   output file was written.

## Examples

### Example 1: Happy path — clean a single PDF

**User says:** "Clean up `./reports/Q2_deck.pdf` and remove the blank pages and notes page."

**Skill does:**
1. Verifies Python and `pypdf` are available.
2. Runs `python ./scripts/clean-pdf.py --input "./reports/Q2_deck.pdf"`.
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
- Never commit secrets or credentials — this skill needs no auth.
- Always report page counts (removed and remaining) so the user can verify.
- Do not alter page content — only remove entire pages.

## Changelog

- 2026-07-01: Initial version
