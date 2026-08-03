import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
Client Profile Extractor
========================
Extracts the following from a GB Client Profile .doc file:
  - Webpak Group #
  - Policyholder Name
  - Policy Outline table(s)   — with "Do not post" comment as "comment" field
  - Booklet Outline table(s)  — with "Do not post" comment as "comment" field

Usage:
    python extract-client-profile.py --file "path/to/ClientProfile.doc"
    python extract-client-profile.py --file "path/to/ClientProfile.doc" --output "result.json"

Output: JSON printed to stdout (and optionally written to --output file).
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ── Helpers ──────────────────────────────────────────────────────────────────

def clean(text):
    """Strip trailing Word cell marker and whitespace."""
    return text.rstrip("\x07").strip()


def split_id_and_comment(cell_text):
    """
    A cell like '83143\\rDo not post to site approval required' contains the
    document/pub number on the first line and an optional comment on subsequent
    lines.  Split and return (id_value, comment).
    """
    parts = re.split(r"[\r\x0b]+", clean(cell_text))
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return "", ""
    id_value = parts[0]
    comment  = " ".join(parts[1:]) if len(parts) > 1 else ""
    return id_value, comment


def multivalue(cell_text):
    """
    Some cells hold multiple values separated by \\r (e.g. two EPAK names or
    bilingual CPM descriptions).  Return a list when there are multiple values,
    a plain string when there is exactly one, or "" when empty.
    """
    parts = [p.strip() for p in re.split(r"[\r\x0b]+", clean(cell_text)) if p.strip()]
    if not parts:
        return ""
    return parts if len(parts) > 1 else parts[0]


def get_cell(tbl, row, col):
    """Safely get cleaned cell text; return '' on error (merged cells etc.)."""
    try:
        return clean(tbl.Cell(row, col).Range.Text)
    except Exception:
        return ""


# ── Table parsers ─────────────────────────────────────────────────────────────

def parse_header_table(tbl):
    """Extract Webpak Group # and Policyholder Name from Table 1."""
    webpak = ""
    policyholder = ""
    for r in range(1, tbl.Rows.Count + 1):
        label = get_cell(tbl, r, 1).lower()
        value = get_cell(tbl, r, 2)
        if "webpak" in label or "webpack" in label:
            webpak = value
        elif "policyholder" in label:
            policyholder = value
    return webpak, policyholder


def parse_policy_outline(tbl):
    """
    Parse a Policy Outline table.
    Columns: Policy/Plan Doc # | EPAK | [Docunav] | CPM PDF Descriptions | Sub Folders
    Table 2 (83143) has 5 cols including Docunav; Table 3 (83144) has 4 cols.
    """
    num_cols = tbl.Columns.Count
    has_docunav = num_cols >= 5
    rows = []
    for r in range(2, tbl.Rows.Count + 1):          # row 1 is header
        policy_number, comment = split_id_and_comment(get_cell(tbl, r, 1))
        if not policy_number:
            continue
        epak    = multivalue(get_cell(tbl, r, 2))
        if has_docunav:
            docunav    = get_cell(tbl, r, 3)
            cpmpdf     = multivalue(get_cell(tbl, r, 4))
            sub_folders = multivalue(get_cell(tbl, r, 5))
        else:
            docunav    = ""
            cpmpdf     = multivalue(get_cell(tbl, r, 3))
            sub_folders = multivalue(get_cell(tbl, r, 4))
        rows.append({
            "policy_plan_doc_number":  policy_number,
            "comment":                 comment,
            "epak_naming_convention":  epak,
            "docunav_naming_convention": docunav,
            "cpmpdf_descriptions":     cpmpdf,
            "sub_folders":             sub_folders,
        })
    return rows


def parse_booklet_outline(tbl):
    """
    Parse a Booklet Outline table.
    Columns: PUB # | Class #'s | EPAK | Docunav | CPM PDF Descriptions | Sub Folders
    """
    rows = []
    for r in range(2, tbl.Rows.Count + 1):          # row 1 is header
        pub_number, comment = split_id_and_comment(get_cell(tbl, r, 1))
        if not pub_number:
            continue
        rows.append({
            "pub_number":              pub_number,
            "comment":                 comment,
            "class_numbers":           multivalue(get_cell(tbl, r, 2)),
            "epak_naming_convention":  multivalue(get_cell(tbl, r, 3)),
            "docunav_naming_convention": get_cell(tbl, r, 4),
            "cpmpdf_descriptions":     multivalue(get_cell(tbl, r, 5)),
            "sub_folders":             multivalue(get_cell(tbl, r, 6)),
        })
    return rows


# ── Document reading ──────────────────────────────────────────────────────────

def heading_before_table(paras, tbl_start):
    """Return the last non-empty paragraph text that ends before tbl_start."""
    candidate = ""
    for end, text in paras:
        if end <= tbl_start:
            candidate = text
        else:
            break
    return candidate


def extract(doc_path: str) -> dict:
    import win32com.client

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    doc  = word.Documents.Open(doc_path)

    try:
        # Build sorted paragraph list once (fast single pass)
        paras = []
        for p in doc.Paragraphs:
            t = p.Range.Text.strip().rstrip("\r").strip()
            if t:
                paras.append((p.Range.End, t))
        paras.sort(key=lambda x: x[0])

        webpak        = ""
        policyholder  = ""
        policy_outlines  = []
        booklet_outlines = []

        for i, tbl in enumerate(doc.Tables, 1):
            heading = heading_before_table(paras, tbl.Range.Start)
            heading_upper = heading.upper()

            if i == 1:
                webpak, policyholder = parse_header_table(tbl)

            elif "POLICY OUTLINE" in heading_upper:
                rows = parse_policy_outline(tbl)
                if rows:
                    policy_outlines.append({
                        "title": heading.strip(),
                        "rows":  rows,
                    })

            elif "BOOKLET OUTLINE" in heading_upper:
                rows = parse_booklet_outline(tbl)
                if rows:
                    booklet_outlines.append({
                        "title": heading.strip(),
                        "rows":  rows,
                    })

        return {
            "webpak_group_number": webpak,
            "policyholder_name":   policyholder,
            "policy_outlines":     policy_outlines,
            "booklet_outlines":    booklet_outlines,
        }

    finally:
        doc.Close(False)
        word.Quit()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract Client Profile data to JSON")
    parser.add_argument("--file",   required=True, help="Path to .doc Client Profile file")
    parser.add_argument("--output", help="Optional path to write JSON output file")
    args = parser.parse_args()

    doc_path = str(Path(args.file).resolve())
    print(f"Extracting: {doc_path}", file=sys.stderr)

    result = extract(doc_path)

    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    print(output_json)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(output_json, encoding="utf-8")
        print(f"Saved to: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
