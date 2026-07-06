#!/usr/bin/env python3
"""
Generate a draw.io flowchart from process steps matching team diagram style:
  - Horizontal left-to-right flow with row wrapping
  - Rectangles for process steps, diamonds for decisions
  - Exception paths branch downward in red
  - Orange circle connectors between rows
  - Standard steps (Get Work, Audit Report, Update Critical Data) always included

Usage:
    python create-diagram.py --target-url URL --diagram-name TEXT --steps-json FILE
      [--work-source TEXT] [--platform TEXT] [--systems TEXT]

Inputs:
    --target-url URL       Confluence page URL to upload attachment to (required)
    --diagram-name TEXT    Name for the diagram file (required)
    --steps-json FILE      Path to JSON file from fetch-steps.py (required)
    --work-source TEXT     Where work items come from (e.g. "Excel audit report")
    --platform TEXT        RPA platform (e.g. "UiPath", "Power Automate Desktop")
    --systems TEXT         Comma-separated systems accessed (e.g. "DSS,Salesforce")
    Environment:
        CONFLUENCE_EMAIL — Confluence user email (Cloud Basic auth)
        CONFLUENCE_TOKEN — Confluence API token or PAT

Outputs:
    JSON to stdout with attachment details and manual import instructions.

Exit codes:
    0 — success
    1 — input error
    2 — API error
"""

import argparse
import base64
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse, parse_qs

try:
    import requests
except ImportError:
    print("Error: requests is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

BOX_W, BOX_H       = 130, 55
DIA_W, DIA_H       = 110, 85
START_W, START_H   = 90, 40
CONN_SIZE          = 44
H_GAP              = 28
V_ROW_GAP          = 120       # vertical gap between rows
EXC_V_GAP          = 50        # vertical gap between exception boxes
MAX_ROW_WIDTH      = 1150      # wrap after this x
ROW_BASE_Y         = 80        # y of first row centre
STEPS_PER_ROW      = 7         # soft limit; wraps when exceeding MAX_ROW_WIDTH

# Styles
S_PROCESS   = ("rounded=0;whiteSpace=wrap;html=1;fontSize=10;"
               "fillColor=#ffffff;strokeColor=#333333;")
S_DECISION  = ("rhombus;whiteSpace=wrap;html=1;fontSize=10;"
               "fillColor=#ffffff;strokeColor=#333333;")
S_START     = ("ellipse;whiteSpace=wrap;html=1;fontSize=11;fontStyle=1;"
               "fillColor=#d5e8d4;strokeColor=#82b366;")
S_END       = ("ellipse;whiteSpace=wrap;html=1;fontSize=11;fontStyle=1;"
               "fillColor=#f8cecc;strokeColor=#b85450;")
S_EXCEPTION = ("rounded=0;whiteSpace=wrap;html=1;fontSize=10;"
               "fillColor=#f8cecc;strokeColor=#b85450;fontColor=#b85450;")
S_STOP      = ("doubleEllipse;whiteSpace=wrap;html=1;fontSize=10;fontStyle=1;"
               "fillColor=#f8cecc;strokeColor=#b85450;fontColor=#b85450;")
S_CONNECTOR = ("ellipse;whiteSpace=wrap;html=1;fontSize=11;fontStyle=1;"
               "fillColor=#FF8000;strokeColor=#d36000;fontColor=#ffffff;")
S_ARROW     = ("edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
               "jettySize=auto;fontSize=10;")
S_ARROW_EXC = ("edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#b85450;"
               "fontColor=#b85450;fontSize=10;")


# ---------------------------------------------------------------------------
# Step classification helpers
# ---------------------------------------------------------------------------

DECISION_RE = re.compile(
    r"\b(check|verif|if\s+there|if\s+any|any\s+active|are\s+there|"
    r"whether|found|exists?|has\s+active|active\s+\w+\s+code)\b",
    re.IGNORECASE,
)
EXCEPTION_ONLY_RE = re.compile(
    r"^(exception|escalat|raise|send\s+(exception|details))",
    re.IGNORECASE,
)


def classify(text: str) -> str:
    if EXCEPTION_ONLY_RE.search(text.strip()):
        return "exception"
    if DECISION_RE.search(text):
        return "decision"
    return "process"


def split_decision(text: str) -> tuple[str, str | None]:
    """
    Split a step into (condition_label, exception_action | None).
    Splits on '. If there is any', '. Exception', 'If found, Exception'
    """
    for pattern in [
        r"\.\s*[Ii]f\s+there\s+is\s+any[,.].*",
        r"\.\s*[Ee]xception.*",
        r",?\s*[Ee]xception\s+the\s+process.*",
    ]:
        m = re.search(pattern, text)
        if m:
            condition = text[:m.start()].strip(" .,")
            exception = text[m.start():].strip(" .,")
            return condition, exception
    return text, None


def shorten(text: str, max_len: int = 70) -> str:
    return (text[:max_len - 3] + "...") if len(text) > max_len else text


def esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# draw.io XML builder
# ---------------------------------------------------------------------------

class Cell:
    __slots__ = ("cid", "xml")

    def __init__(self, cid: int, xml: str):
        self.cid = cid
        self.xml = xml


class DiagramBuilder:
    def __init__(self):
        self._cells: list[Cell] = []
        self._nid = 2

    def _alloc(self) -> int:
        n = self._nid
        self._nid += 1
        return n

    def vertex(self, x: int, y: int, w: int, h: int,
               label: str, style: str) -> int:
        cid = self._alloc()
        self._cells.append(Cell(cid,
            f'<mxCell id="{cid}" value="{esc(label)}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
            f'</mxCell>'
        ))
        return cid

    def edge(self, src: int, tgt: int, label: str = "",
             style: str = S_ARROW) -> int:
        cid = self._alloc()
        self._cells.append(Cell(cid,
            f'<mxCell id="{cid}" value="{esc(label)}" style="{style}" '
            f'edge="1" source="{src}" target="{tgt}" parent="1">'
            f'<mxGeometry relative="1" as="geometry"/>'
            f'</mxCell>'
        ))
        return cid

    def to_xml(self, page_w: int, page_h: int) -> str:
        body = "\n    ".join(c.xml for c in self._cells)
        return (
            f'<mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" '
            f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" '
            f'page="1" pageScale="1" '
            f'pageWidth="{page_w}" pageHeight="{page_h}" '
            f'math="0" shadow="0">'
            f'<root>'
            f'<mxCell id="0"/>'
            f'<mxCell id="1" parent="0"/>'
            f'\n    {body}\n'
            f'</root></mxGraphModel>'
        )


# ---------------------------------------------------------------------------
# Flowchart layout engine
# ---------------------------------------------------------------------------

def build_drawio_xml(diagram_name: str, steps: list[str]) -> str:
    b = DiagramBuilder()

    cx = 40
    row_y = ROW_BASE_Y
    row_count = 0
    conn_letter = ord("A")

    # Track the previous shape id for arrows
    prev_id: int | None = None

    # Pending exceptions: list of (decision_id, exception_text, row_y_at_time)
    pending_exc: list[tuple[int, str, int]] = []

    def center_y(shape_h: int) -> int:
        """Y coord to vertically centre shape on the current row."""
        return row_y + (BOX_H - shape_h) // 2

    def need_wrap(next_w: int) -> bool:
        return cx + next_w > MAX_ROW_WIDTH

    def wrap_row(nonlocal_refs: dict) -> None:
        """Place end connector, advance to next row, place start connector."""
        nonlocal_refs["cx"] = cx
        nonlocal_refs["row_y"] = row_y
        nonlocal_refs["row_count"] = row_count
        nonlocal_refs["conn_letter"] = conn_letter

        letter = chr(nonlocal_refs["conn_letter"])
        end_cx = nonlocal_refs["cx"]
        end_ry = nonlocal_refs["row_y"]

        conn_y = end_ry + (BOX_H - CONN_SIZE) // 2
        end_conn_id = b.vertex(end_cx, conn_y, CONN_SIZE, CONN_SIZE,
                               letter, S_CONNECTOR)
        if nonlocal_refs["prev_id"] is not None:
            b.edge(nonlocal_refs["prev_id"], end_conn_id)

        new_ry = end_ry + BOX_H + V_ROW_GAP
        start_conn_id = b.vertex(40, new_ry + (BOX_H - CONN_SIZE) // 2,
                                 CONN_SIZE, CONN_SIZE, letter, S_CONNECTOR)
        b.edge(end_conn_id, start_conn_id,
               style=S_ARROW + "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                              "entryX=0.5;entryY=0;entryDx=0;entryDy=0;")

        nonlocal_refs["cx"] = 40 + CONN_SIZE + H_GAP
        nonlocal_refs["row_y"] = new_ry
        nonlocal_refs["row_count"] += 1
        nonlocal_refs["conn_letter"] += 1
        nonlocal_refs["prev_id"] = start_conn_id

    # Use a mutable container to share state with the helper
    state = {
        "cx": cx, "row_y": row_y, "row_count": row_count,
        "conn_letter": conn_letter, "prev_id": None
    }

    # --- Start shape ---
    sy = state["row_y"] + (BOX_H - START_H) // 2
    start_id = b.vertex(state["cx"], sy, START_W, START_H, "START", S_START)
    state["prev_id"] = start_id
    state["cx"] += START_W + H_GAP

    # --- Process each step ---
    for step in steps:
        kind = classify(step)

        if kind == "decision":
            cond, exc_text = split_decision(step)
            shape_w, shape_h = DIA_W, DIA_H
        else:
            shape_w, shape_h = BOX_W, BOX_H

        # Wrap if needed
        if state["cx"] + shape_w > MAX_ROW_WIDTH:
            wrap_row(state)

        shape_y = state["row_y"] + (BOX_H - shape_h) // 2

        if kind == "decision":
            short_cond = shorten(cond, 55)
            shape_id = b.vertex(state["cx"], shape_y,
                                shape_w, shape_h, short_cond, S_DECISION)
            if state["prev_id"] is not None:
                b.edge(state["prev_id"], shape_id)
            if exc_text:
                pending_exc.append((shape_id, exc_text, state["row_y"]))
        else:
            short_step = shorten(step, 70)
            style = S_EXCEPTION if kind == "exception" else S_PROCESS
            shape_id = b.vertex(state["cx"], shape_y,
                                shape_w, shape_h, short_step, style)
            if state["prev_id"] is not None:
                arrow_label = "No" if classify(step) == "decision" else ""
                b.edge(state["prev_id"], shape_id)

        state["prev_id"] = shape_id
        state["cx"] += shape_w + H_GAP

    # --- End shape ---
    if state["cx"] + START_W > MAX_ROW_WIDTH:
        wrap_row(state)
    end_y = state["row_y"] + (BOX_H - START_H) // 2
    end_id = b.vertex(state["cx"], end_y, START_W, START_H, "END", S_END)
    if state["prev_id"] is not None:
        b.edge(state["prev_id"], end_id)

    # --- Exception branches (below all rows) ---
    exc_base_y = state["row_y"] + BOX_H + V_ROW_GAP + 20
    for dia_id, exc_text, _ in pending_exc:
        short_exc = shorten(exc_text, 80)
        exc_id = b.vertex(40, exc_base_y, BOX_W + 40, BOX_H,
                          short_exc, S_EXCEPTION)
        b.edge(dia_id, exc_id, "Yes",
               S_ARROW_EXC + "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                             "entryX=0.5;entryY=0;entryDx=0;entryDy=0;")
        # No label on the main (right) path
        stop_y = exc_base_y + BOX_H + EXC_V_GAP // 2
        stop_id = b.vertex(40 + (BOX_W + 40 - 60) // 2, stop_y,
                           60, 40, "STOP", S_STOP)
        b.edge(exc_id, stop_id,
               style=S_ARROW_EXC + "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                                   "entryX=0.5;entryY=0;entryDx=0;entryDy=0;")
        exc_base_y = stop_y + 40 + EXC_V_GAP

    page_w = 1169
    page_h = max(827, exc_base_y + 100)
    return b.to_xml(page_w, page_h)


# ---------------------------------------------------------------------------
# Standard step injection
# ---------------------------------------------------------------------------

def inject_standard_steps(steps: list[str],
                           work_source: str,
                           platform: str,
                           systems: str) -> list[str]:
    """Prepend Get Work + Audit Report if missing; append Update Critical Data."""
    lower_steps = [s.lower() for s in steps]

    prefix = []
    if not any("get work" in s or "retrieve work" in s for s in lower_steps):
        src = f" from {work_source}" if work_source else ""
        pfm = f" ({platform})" if platform else ""
        prefix.append(f"Get Work{pfm}: Retrieve work items{src}.")

    if not any("audit report" in s for s in lower_steps):
        prefix.append("Generate Audit Report: Review Bot output and validate work queue.")

    suffix = []
    if not any("update critical" in s or "critical data" in s for s in lower_steps):
        sys_note = f" in {systems}" if systems else ""
        suffix.append(f"Update Critical Data{sys_note}: Record process completion and update tracking logs.")

    return prefix + steps + suffix


# ---------------------------------------------------------------------------
# Auth & Confluence helpers
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate draw.io flowchart and upload to Confluence.")
    p.add_argument("--target-url", required=True)
    p.add_argument("--diagram-name", required=True)
    p.add_argument("--steps-json", required=True)
    p.add_argument("--work-source", default="")
    p.add_argument("--platform", default="")
    p.add_argument("--systems", default="")
    return p.parse_args()


def get_auth_headers(email: str | None, token: str) -> dict:
    if email:
        creds = base64.b64encode(f"{email}:{token}".encode()).decode()
        return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def extract_page_id_and_base(url: str) -> tuple[str | None, str]:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    m = re.search(r"/pages/(\d+)", parsed.path)
    if m:
        return m.group(1), base + "/wiki" if "/wiki" in parsed.path else base
    qs = parse_qs(parsed.query)
    if "pageId" in qs:
        return qs["pageId"][0], base
    return None, base


def upload_attachment(base_url: str, page_id: str,
                      file_path: Path, auth_headers: dict) -> str:
    url = f"{base_url}/rest/api/content/{page_id}/child/attachment"
    up_headers = {"Authorization": auth_headers["Authorization"],
                  "X-Atlassian-Token": "no-check"}

    # Remove existing attachment with same name
    chk = requests.get(f"{url}?filename={file_path.name}",
                       headers=auth_headers, timeout=30)
    if chk.ok:
        for att in chk.json().get("results", []):
            requests.delete(f"{base_url}/rest/api/content/{att['id']}",
                            headers=auth_headers, timeout=30)

    with open(file_path, "rb") as f:
        r = requests.post(url, headers=up_headers,
                          files={"file": (file_path.name, f, "application/octet-stream")},
                          data={"minorEdit": "true",
                                "comment": "Auto-generated draw.io flowchart"},
                          timeout=30)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        print(f"Upload error {r.status_code}: {r.text}", file=sys.stderr)
        sys.exit(2)

    dl = r.json()["results"][0].get("_links", {}).get("download", "")
    return f"{base_url}{dl}" if dl else url


def api_get(url: str, headers: dict) -> dict:
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        print(f"API error: {e}", file=sys.stderr)
        sys.exit(2)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f"Connection error: {e}", file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    email = os.environ.get("CONFLUENCE_EMAIL")
    token = os.environ.get("CONFLUENCE_TOKEN")
    if not token:
        print("Error: CONFLUENCE_TOKEN is required.", file=sys.stderr)
        sys.exit(1)

    with open(args.steps_json) as f:
        steps_data = json.load(f)

    raw_steps = [s.strip() for s in steps_data.get("steps", []) if s.strip()]
    if not raw_steps:
        print("Error: No steps found in steps JSON.", file=sys.stderr)
        sys.exit(1)

    steps = inject_standard_steps(raw_steps, args.work_source,
                                   args.platform, args.systems)

    headers = get_auth_headers(email, token)
    page_id, base_url = extract_page_id_and_base(args.target_url)
    if not page_id:
        print(f"Error: Could not extract page ID from: {args.target_url}", file=sys.stderr)
        sys.exit(1)

    page = api_get(f"{base_url}/rest/api/content/{page_id}?expand=title", headers)
    page_title = page.get("title", "Unknown")

    # Generate draw.io XML
    diagram_xml = build_drawio_xml(args.diagram_name, steps)
    safe_name = re.sub(r"[^\w\- ]", "_", args.diagram_name).strip()
    diagram_file = Path(tempfile.gettempdir()) / f"{safe_name}.drawio"
    diagram_file.write_text(diagram_xml, encoding="utf-8")

    # Upload to Confluence
    attachment_url = upload_attachment(base_url, page_id,
                                        diagram_file, headers)

    result = {
        "diagram_name": args.diagram_name,
        "diagram_file": str(diagram_file),
        "steps_count": len(steps),
        "standard_steps_added": len(steps) - len(raw_steps),
        "target_page": page_title,
        "attachment_url": attachment_url,
        "status": "uploaded"
    }
    print(json.dumps(result, indent=2))

    print("\n--- How to import into Confluence ---", file=sys.stderr)
    print(f"1. Open: {args.target_url}", file=sys.stderr)
    print(f"2. Edit the page and place cursor under the target heading.", file=sys.stderr)
    print(f"3. Insert a draw.io macro.", file=sys.stderr)
    print(f"4. Choose 'Import' and select '{safe_name}.drawio' from page attachments.", file=sys.stderr)
    print(f"5. Save and publish.", file=sys.stderr)


if __name__ == "__main__":
    main()
