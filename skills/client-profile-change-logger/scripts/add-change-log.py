import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
Client Profile Change Logger
=============================
Adds a new row to the Summary of Changes table in a GB Client Profile .doc file.

  Date        : today's date  (e.g. August 5, 2026)
  Updated By  : GB0074 Bot
  Description : provided via --description argument

Usage:
    python add-change-log.py --file "path/to/ClientProfile.doc" --description "your description"
"""

import argparse
from datetime import date
from pathlib import Path


def find_change_log_table(doc):
    """
    Return the Summary of Changes table — identified by a 3-column table
    whose first cell header contains 'date'.
    """
    for tbl in doc.Tables:
        try:
            header = tbl.Cell(1, 1).Range.Text.rstrip("\x07").strip().lower()
            if "date" in header and tbl.Columns.Count == 3:
                return tbl
        except Exception:
            continue
    return None


def format_date(d: date) -> str:
    """Format as 'August 5, 2026' (no leading zero on day)."""
    return d.strftime("%B %-d, %Y") if sys.platform != "win32" else \
           f"{d.strftime('%B')} {d.day}, {d.year}"


def add_change_log(doc_path: str, description: str) -> dict:
    import win32com.client

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    doc  = word.Documents.Open(doc_path)

    try:
        tbl = find_change_log_table(doc)
        if not tbl:
            raise RuntimeError("Summary of Changes table not found in document.")

        today     = format_date(date.today())
        updated_by = "GB0074 Bot"

        # Add a new row at the bottom
        new_row = tbl.Rows.Add()

        new_row.Cells(1).Range.Text = today
        new_row.Cells(2).Range.Text = updated_by
        new_row.Cells(3).Range.Text = description

        doc.Save()

        return {
            "status":      "success",
            "date":        today,
            "updated_by":  updated_by,
            "description": description,
            "row_number":  tbl.Rows.Count,
        }

    finally:
        doc.Close(False)
        word.Quit()


def main():
    parser = argparse.ArgumentParser(description="Add a row to the Client Profile Summary of Changes table")
    parser.add_argument("--file",        required=True, help="Path to .doc Client Profile file")
    parser.add_argument("--description", required=True, help="Description of the change")
    args = parser.parse_args()

    doc_path = str(Path(args.file).resolve())
    print(f"File: {doc_path}", file=sys.stderr)

    result = add_change_log(doc_path, args.description)

    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\n✓ Row added at position {result['row_number']}", file=sys.stderr)


if __name__ == "__main__":
    main()
