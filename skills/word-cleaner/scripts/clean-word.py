#!/usr/bin/env python3
"""
Clean a Word (.docx) document by updating the notes page.

On the notes page (last page of the document):
  1. Appends the line "This document has been made accessible"
  2. Finds the "Revised:" or "Revised Date:" label and updates the
     adjacent date value to today in YYYY-MM-DD format.

Usage:
    python clean-word.py --input FILE [--overwrite]

Inputs:
    --input FILE   Path to the source .docx file (required).
    --overwrite    Replace the original file. Default: write <name>_clean.docx
                   alongside the original.

Outputs:
    Writes the cleaned .docx to disk and prints a JSON summary to stdout:
    {
      "output": "<path>",
      "accessibility_line_added": true|false,
      "revised_date_updated": true|false,
      "revised_date_new_value": "<YYYY-MM-DD>" | null
    }

Exit codes:
    0 — success
    1 — input error (file not found, not a docx, bad args)
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean a Word document notes page.")
    parser.add_argument("--input", required=True, metavar="FILE", help="Path to the .docx file.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the original file instead of writing a _clean copy.",
    )
    return parser.parse_args()


def find_notes_page_end(doc) -> int:
    """
    Locate the end of the notes page (first page).
    The notes page is identified by the presence of 'DELETE NOTES PAGE BEFORE PUBLICATION'.
    Returns the index of the last paragraph on that page (before the first page break).
    """
    paragraphs = doc.paragraphs
    for i, para in enumerate(paragraphs):
        # Stop at first explicit page break — that marks end of notes page
        xml = para._element.xml
        if 'w:type="page"' in xml or 'w:type val="page"' in xml:
            return i
        for run in para.runs:
            if run.text and "\x0c" in run.text:
                return i
    # Fallback: return index of last paragraph containing notes marker
    for i, para in enumerate(paragraphs):
        if "DELETE NOTES PAGE BEFORE PUBLICATION" in para.text.upper():
            # Return up to ~15 paragraphs after the marker as the notes page
            return min(i + 15, len(paragraphs) - 1)
    return 20  # safe fallback


def add_accessibility_line(doc, notes_page_end: int) -> bool:
    """
    Append "This document has been made accessible" to the notes page (first page)
    if not already present. Inserts before the first page break, matching the
    font name and size of the surrounding notes page paragraphs.
    Returns True if the line was added.
    """
    accessibility_text = "This document has been made accessible"
    paragraphs = doc.paragraphs

    # Check if already present anywhere on the notes page
    for para in paragraphs[:notes_page_end + 1]:
        if accessibility_text.lower() in para.text.lower():
            return False

    # Detect font name and size from the first non-empty run on the notes page
    ref_font_name = None
    ref_font_size = None
    for para in paragraphs[:notes_page_end]:
        for run in para.runs:
            if run.text.strip() and run.font.name:
                ref_font_name = run.font.name
                ref_font_size = run.font.size
                break
        if ref_font_name:
            break

    # Insert a new paragraph just before the page break paragraph
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    import copy

    page_break_para = paragraphs[notes_page_end]
    new_para = OxmlElement("w:p")

    # Apply paragraph style to match surrounding text
    pPr = OxmlElement("w:pPr")
    pStyle = OxmlElement("w:pStyle")
    pStyle.set(qn("w:val"), page_break_para._element.find(
        f".//{qn('w:pStyle')}", page_break_para._element.nsmap or {}
    ).get(qn("w:val")) if page_break_para._element.find(
        f".//{qn('w:pStyle')}"
    ) is not None else "Normal")
    pPr.append(pStyle)
    new_para.append(pPr)

    new_run = OxmlElement("w:r")

    # Apply run properties (font) to match surrounding text
    if ref_font_name or ref_font_size:
        rPr = OxmlElement("w:rPr")
        if ref_font_name:
            rFonts = OxmlElement("w:rFonts")
            rFonts.set(qn("w:ascii"), ref_font_name)
            rFonts.set(qn("w:hAnsi"), ref_font_name)
            rPr.append(rFonts)
        if ref_font_size:
            sz = OxmlElement("w:sz")
            # font.size is in EMUs (1pt = 12700); w:sz uses half-points
            half_pts = str(int(ref_font_size / 6350))
            sz.set(qn("w:val"), half_pts)
            szCs = OxmlElement("w:szCs")
            szCs.set(qn("w:val"), half_pts)
            rPr.append(sz)
            rPr.append(szCs)
        new_run.append(rPr)

    new_text = OxmlElement("w:t")
    new_text.text = accessibility_text
    new_run.append(new_text)
    new_para.append(new_run)
    page_break_para._element.addprevious(new_para)
    return True


def update_booklet_produced_date(doc, today: str) -> bool:
    """
    Find the "This booklet produced:" field on the cover page (page 2 — between
    the first and second page breaks) and update its date to today (YYYY-MM-DD).
    Returns True if the date was updated.
    """
    date_pattern = re.compile(
        r"(this\s+booklet\s+produced[\s:]*)"
        r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|"
        r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s,]*\d{1,2}[\s,]*\d{4})",
        re.IGNORECASE,
    )

    paragraphs = doc.paragraphs
    page_breaks_seen = 0
    cover_page_paras = []

    for para in paragraphs:
        xml = para._element.xml
        is_page_break = 'w:type' in xml and 'page' in xml
        if is_page_break:
            page_breaks_seen += 1
            if page_breaks_seen == 2:
                break  # Reached end of cover page
        if page_breaks_seen == 1:
            cover_page_paras.append(para)

    # Search cover page first; fall back to full document if not found
    search_scope = cover_page_paras if cover_page_paras else paragraphs

    for para in search_scope:
        if re.search(r"this\s+booklet\s+produced", para.text, re.IGNORECASE):
            for run in para.runs:
                new_text, count = date_pattern.subn(
                    lambda m: m.group(1) + today, run.text
                )
                if count:
                    run.text = new_text
                    return True
            # Date may be split across runs — replace via first run
            full_text = para.text
            new_text, count = date_pattern.subn(
                lambda m: m.group(1) + today, full_text
            )
            if count and para.runs:
                para.runs[0].text = new_text
                for run in para.runs[1:]:
                    run.text = ""
                return True

    return False


def clean_word(input_path: Path, overwrite: bool) -> dict:
    try:
        from docx import Document
    except ImportError:
        print("Error: python-docx is not installed. Run: pip install python-docx", file=sys.stderr)
        sys.exit(1)

    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if input_path.suffix.lower() != ".docx":
        print(f"Error: File must be a .docx file: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        doc = Document(str(input_path))
    except Exception as exc:
        print(f"Error: Could not open Word document '{input_path}': {exc}", file=sys.stderr)
        sys.exit(1)

    today = date.today().strftime("%Y-%m-%d")
    notes_page_end = find_notes_page_end(doc)

    accessibility_added = add_accessibility_line(doc, notes_page_end)
    date_updated = update_booklet_produced_date(doc, today)

    if overwrite:
        output_path = input_path
    else:
        output_path = input_path.with_stem(input_path.stem + "_clean")

    try:
        doc.save(str(output_path))
    except OSError as exc:
        print(f"Error: Could not write output file '{output_path}': {exc}", file=sys.stderr)
        sys.exit(1)

    return {
        "output": str(output_path),
        "accessibility_line_added": accessibility_added,
        "booklet_produced_date_updated": date_updated,
        "booklet_produced_date_new_value": today if date_updated else None,
    }


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    result = clean_word(input_path, args.overwrite)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
