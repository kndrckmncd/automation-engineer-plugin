#!/usr/bin/env python3
"""
Clean a PDF by removing blank pages and notes pages.

A "blank page" is one whose extracted text contains no non-whitespace characters.
A "notes page" is one whose extracted text contains the phrase
"DELETE NOTES PAGE BEFORE PUBLICATION" (case-insensitive).

Usage:
    python clean-pdf.py --input FILE [--overwrite]

Inputs:
    --input FILE   Path to the source PDF file (required).
    --overwrite    Replace the original file. Default: write <name>_clean.pdf
                   alongside the original.

Outputs:
    Writes the cleaned PDF to disk and prints a JSON summary to stdout:
    {
      "output": "<path>",
      "pages_original": <int>,
      "pages_removed_blank": <int>,
      "pages_removed_notes": <int>,
      "pages_remaining": <int>
    }

Exit codes:
    0 — success (including "no pages removed" case)
    1 — input error (file not found, not a PDF, bad args)
    2 — safety abort (cleaned PDF would have 0 pages)
"""

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean blank and notes pages from a PDF.")
    parser.add_argument("--input", required=True, metavar="FILE", help="Path to the PDF file.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the original file instead of writing a _clean copy.",
    )
    return parser.parse_args()


def is_blank_page(page) -> bool:
    """Return True if the page has no extractable non-whitespace text."""
    try:
        text = page.extract_text() or ""
        return not text.strip()
    except Exception:
        return False


def is_notes_page(page) -> bool:
    """Return True if the page contains the deletion marker phrase."""
    try:
        text = page.extract_text() or ""
        return "DELETE NOTES PAGE BEFORE PUBLICATION" in text.upper()
    except Exception:
        return False


def clean_pdf(input_path: Path, overwrite: bool) -> dict:
    """
    Remove blank and notes pages from a PDF.

    Args:
        input_path: Path to the source PDF.
        overwrite:  If True, replace the original; otherwise write <stem>_clean.pdf.

    Returns:
        Summary dict with counts and output path.

    Raises:
        SystemExit(1): on input errors.
        SystemExit(2): if the cleaned PDF would be empty.
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("Error: pypdf is not installed. Run: pip install pypdf", file=sys.stderr)
        sys.exit(1)

    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        reader = PdfReader(str(input_path))
    except Exception as exc:
        print(f"Error: Could not read PDF '{input_path}': {exc}", file=sys.stderr)
        sys.exit(1)

    writer = PdfWriter()
    blank_count = 0
    notes_count = 0
    total_pages = len(reader.pages)

    for page in reader.pages:
        if is_notes_page(page):
            notes_count += 1
        elif is_blank_page(page):
            blank_count += 1
        else:
            writer.add_page(page)

    pages_remaining = total_pages - blank_count - notes_count

    if pages_remaining == 0:
        print(
            "Error: All pages would be removed — aborting to avoid writing an empty PDF.",
            file=sys.stderr,
        )
        sys.exit(2)

    if blank_count == 0 and notes_count == 0:
        # Nothing to do — report and exit cleanly without writing a file.
        return {
            "output": None,
            "pages_original": total_pages,
            "pages_removed_blank": 0,
            "pages_removed_notes": 0,
            "pages_remaining": total_pages,
        }

    if overwrite:
        output_path = input_path
    else:
        output_path = input_path.with_stem(input_path.stem + "_clean")

    try:
        with open(output_path, "wb") as fh:
            writer.write(fh)
    except OSError as exc:
        print(f"Error: Could not write output file '{output_path}': {exc}", file=sys.stderr)
        sys.exit(1)

    return {
        "output": str(output_path),
        "pages_original": total_pages,
        "pages_removed_blank": blank_count,
        "pages_removed_notes": notes_count,
        "pages_remaining": pages_remaining,
    }


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)

    result = clean_pdf(input_path, args.overwrite)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
