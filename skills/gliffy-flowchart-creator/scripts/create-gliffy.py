#!/usr/bin/env python3
"""
Create a Gliffy flowchart on a Confluence page from process steps.

Generates a vertical flowchart from a list of process steps and embeds
it as a Gliffy diagram under a specified heading on the target Confluence page.

Usage:
    python create-gliffy.py --target-url URL --heading TEXT --diagram-name TEXT --steps-json FILE

Inputs:
    --target-url URL      Full Confluence page URL where diagram will be placed (required)
    --heading TEXT        Exact heading text on the target page under which to insert the diagram (required)
    --diagram-name TEXT   Name for the Gliffy diagram (required)
    --steps-json FILE     Path to JSON file output from fetch-steps.py (required)
    Environment:
        CONFLUENCE_EMAIL — Confluence user email (Cloud Basic auth)
        CONFLUENCE_TOKEN — Confluence API token (Cloud) or Personal Access Token (Server/DC)

Outputs:
    JSON to stdout:
    {
      "diagram_name": "...",
      "steps_count": N,
      "target_page": "...",
      "status": "created"
    }

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
from typing import Any
from urllib.parse import urlparse, parse_qs

try:
    import requests
except ImportError:
    print("Error: requests is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Auth & HTTP helpers
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Gliffy flowchart on a Confluence page.")
    parser.add_argument("--target-url", required=True, metavar="URL", help="Target Confluence page URL.")
    parser.add_argument("--heading", required=True, metavar="TEXT", help="Heading under which to insert the diagram.")
    parser.add_argument("--diagram-name", required=True, metavar="TEXT", help="Name for the Gliffy diagram.")
    parser.add_argument("--steps-json", required=True, metavar="FILE", help="Path to JSON file with steps.")
    return parser.parse_args()


def get_auth_headers(email: str | None, token: str) -> dict[str, str]:
    if email:
        creds = base64.b64encode(f"{email}:{token}".encode()).decode()
        return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def extract_page_id_and_base(page_url: str) -> tuple[str | None, str]:
    parsed = urlparse(page_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    m = re.search(r"/pages/(\d+)", parsed.path)
    if m:
        return m.group(1), base + "/wiki" if "/wiki" in parsed.path else base
    qs = parse_qs(parsed.query)
    if "pageId" in qs:
        return qs["pageId"][0], base
    return None, base


def api_get(url: str, headers: dict) -> dict[str, Any]:
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        print(f"API error {status} GET {url}: {e}", file=sys.stderr)
        sys.exit(2)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f"Connection error: {e}", file=sys.stderr)
        sys.exit(2)


def api_post(url: str, headers: dict, body: Any) -> dict[str, Any]:
    try:
        r = requests.post(url, headers=headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        print(f"API error {status} POST {url}: {e.response.text if e.response else e}", file=sys.stderr)
        sys.exit(2)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f"Connection error: {e}", file=sys.stderr)
        sys.exit(2)


def api_put(url: str, headers: dict, body: Any) -> dict[str, Any]:
    try:
        r = requests.put(url, headers=headers, json=body, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        print(f"API error {status} PUT {url}: {e.response.text if e.response else e}", file=sys.stderr)
        sys.exit(2)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f"Connection error: {e}", file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Gliffy diagram JSON generation
# ---------------------------------------------------------------------------

SHAPE_W = 220
SHAPE_H = 60
START_END_W = 140
START_END_H = 50
ARROW_H = 40
X_CENTER = 300
Y_START = 60
Y_STEP = SHAPE_H + ARROW_H


def _text_child(parent_id: int, node_id: int, w: int, h: int, text: str) -> dict:
    return {
        "x": 0.5, "y": 0.5, "id": node_id,
        "width": w - 1, "height": h - 1,
        "uid": "com.gliffy.shape.basic.basic_v1.default.text",
        "order": "auto", "lockAspectRatio": False, "lockShape": False,
        "graphic": {
            "type": "Text",
            "Text": {
                "overflow": "none",
                "paddingTop": 8, "paddingRight": 8,
                "paddingBottom": 8, "paddingLeft": 8,
                "html": f'<p style="text-align:center;"><span style="font-family:Arial;font-size:11px;">{text}</span></p>'
            }
        },
        "children": []
    }


def _oval(node_id: int, text_id: int, x: int, y: int, w: int, h: int,
          text: str, fill: str = "#d5e8d4") -> dict:
    return {
        "x": x, "y": y, "id": node_id, "width": w, "height": h,
        "uid": "com.gliffy.shape.flowchart.flowchart_v1.default.start2",
        "order": "auto", "lockAspectRatio": False, "lockShape": False,
        "graphic": {
            "type": "Shape",
            "Shape": {
                "tid": "com.gliffy.stencil.flowchart.flowchart_v1.default.start2",
                "strokeWidth": 2, "strokeColor": "#333333",
                "fillColor": fill, "gradient": False,
                "dropShadow": False, "state": 0, "opacity": 1,
                "shadowX": 0, "shadowY": 0
            }
        },
        "children": [_text_child(node_id, text_id, w, h, text)]
    }


def _process_box(node_id: int, text_id: int, x: int, y: int, w: int, h: int,
                 text: str) -> dict:
    return {
        "x": x, "y": y, "id": node_id, "width": w, "height": h,
        "uid": "com.gliffy.shape.flowchart.flowchart_v1.default.process",
        "order": "auto", "lockAspectRatio": False, "lockShape": False,
        "graphic": {
            "type": "Shape",
            "Shape": {
                "tid": "com.gliffy.stencil.flowchart.flowchart_v1.default.process",
                "strokeWidth": 2, "strokeColor": "#333333",
                "fillColor": "#dae8fc", "gradient": False,
                "dropShadow": False, "state": 0, "opacity": 1,
                "shadowX": 0, "shadowY": 0
            }
        },
        "children": [_text_child(node_id, text_id, w, h, text)]
    }


def _arrow(node_id: int, from_id: int, to_id: int,
           x: int, y: int, h: int) -> dict:
    return {
        "x": x, "y": y, "id": node_id, "width": 0, "height": h,
        "uid": "com.gliffy.shape.basic.basic_v1.default.line",
        "order": "auto", "lockAspectRatio": False, "lockShape": False,
        "graphic": {
            "type": "Line",
            "Line": {
                "strokeWidth": 2, "strokeColor": "#333333",
                "fillColor": "none", "dashStyle": None,
                "startArrow": 0, "endArrow": 1,
                "startArrowRotation": "auto", "endArrowRotation": "auto",
                "interpolationType": "linear",
                "cornerRadius": None,
                "controlPath": [[0, 0], [0, h]],
                "lockSegments": {}
            }
        },
        "constraints": {
            "startConstraint": {
                "type": "StartPositionConstraint",
                "StartPositionConstraint": {"nodeId": from_id, "px": 0.5, "py": 1.0}
            },
            "endConstraint": {
                "type": "EndPositionConstraint",
                "EndPositionConstraint": {"nodeId": to_id, "px": 0.5, "py": 0.0}
            }
        },
        "children": []
    }


def build_gliffy_diagram(diagram_name: str, steps: list[str]) -> str:
    """
    Build a Gliffy JSON flowchart string from a list of process steps.
    Layout: Start oval → process box per step → End oval, connected by arrows.
    """
    objects = []
    node_id = 1

    # Start oval
    start_x = X_CENTER - START_END_W // 2
    start_id = node_id
    objects.append(_oval(node_id, node_id + 1, start_x, Y_START, START_END_W, START_END_H, "Start"))
    node_id += 2

    prev_id = start_id
    current_y = Y_START + START_END_H

    # Arrow from Start to first step
    arrow_id = node_id
    objects.append(_arrow(node_id, prev_id, node_id + 1,
                          X_CENTER, current_y, ARROW_H))
    node_id += 1
    current_y += ARROW_H

    # Process boxes
    for step in steps:
        box_x = X_CENTER - SHAPE_W // 2
        box_id = node_id
        safe_text = step.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        objects.append(_process_box(node_id, node_id + 1, box_x, current_y,
                                    SHAPE_W, SHAPE_H, safe_text))
        prev_id = box_id
        node_id += 2
        current_y += SHAPE_H

        # Arrow to next shape
        objects.append(_arrow(node_id, prev_id, node_id + 1,
                              X_CENTER, current_y, ARROW_H))
        node_id += 1
        current_y += ARROW_H

    # End oval
    end_x = X_CENTER - START_END_W // 2
    end_id = node_id
    objects.append(_oval(node_id, node_id + 1, end_x, current_y,
                         START_END_W, START_END_H, "End", fill="#f8cecc"))
    node_id += 2

    diagram = {
        "contentType": "application/gliffy+json",
        "version": "1.3",
        "metadata": {"title": diagram_name, "revision": 1, "exportBorder": False},
        "embeddedResources": {"index": 0, "resources": []},
        "stage": {
            "exportBorder": False,
            "exportPadding": 10,
            "maxWidth": 5000,
            "maxHeight": 5000,
            "x": 0, "y": 0,
            "width": X_CENTER * 2,
            "height": current_y + START_END_H + 60,
            "nodeIndex": node_id,
            "autoFit": True,
            "objects": objects,
            "layers": [
                {"guid": "layer0", "order": 0, "name": "Background",
                 "active": False, "locked": True, "visible": True, "nodeIndex": 0},
                {"guid": "layer1", "order": 1, "name": "Default",
                 "active": True, "locked": False, "visible": True, "nodeIndex": node_id}
            ],
            "shapeStyles": {},
            "lineStyles": {"global": {}},
            "textStyles": {"global": {
                "face": "Arial", "size": "11",
                "bold": False, "italic": False,
                "color": "#000000", "align": "center"
            }}
        }
    }
    return json.dumps(diagram)


# ---------------------------------------------------------------------------
# Gliffy & Confluence API
# ---------------------------------------------------------------------------

def create_gliffy_diagram(base_url: str, page_id: str, diagram_name: str,
                           diagram_json: str, headers: dict) -> None:
    """Upload the Gliffy diagram to the target Confluence page."""
    url = f"{base_url}/rest/gliffy/1.0/page/{page_id}/diagram"
    gliffy_headers = {**headers, "Content-Type": "application/x-www-form-urlencoded"}
    from urllib.parse import urlencode
    data = urlencode({"name": diagram_name, "diagramData": diagram_json})
    try:
        r = requests.post(url, headers=gliffy_headers, data=data, timeout=30)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        print(f"Gliffy API error {status}: {e.response.text if e.response else e}", file=sys.stderr)
        sys.exit(2)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        print(f"Connection error creating diagram: {e}", file=sys.stderr)
        sys.exit(2)


def insert_gliffy_macro(storage_body: str, heading: str,
                         diagram_name: str, page_id: str) -> str:
    """
    Insert the Gliffy macro into the Confluence storage body
    immediately after the specified heading tag.
    """
    gliffy_macro = (
        f'<ac:structured-macro ac:name="gliffy" ac:schema-version="1">'
        f'<ac:parameter ac:name="name">{diagram_name}</ac:parameter>'
        f'<ac:parameter ac:name="pageId">{page_id}</ac:parameter>'
        f'<ac:parameter ac:name="version">1</ac:parameter>'
        f'<ac:parameter ac:name="size">L</ac:parameter>'
        f'<ac:parameter ac:name="align">center</ac:parameter>'
        f'</ac:structured-macro>'
    )

    # Match any heading level (h1–h6) containing the specified text
    pattern = re.compile(
        r'(<h[1-6][^>]*>.*?' + re.escape(heading) + r'.*?</h[1-6]>)',
        re.IGNORECASE | re.DOTALL
    )
    match = pattern.search(storage_body)
    if not match:
        print(f"Warning: Heading '{heading}' not found — appending diagram at end of page.", file=sys.stderr)
        return storage_body + gliffy_macro

    insert_pos = match.end()
    return storage_body[:insert_pos] + gliffy_macro + storage_body[insert_pos:]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    email = os.environ.get("CONFLUENCE_EMAIL")
    token = os.environ.get("CONFLUENCE_TOKEN")
    if not token:
        print("Error: CONFLUENCE_TOKEN environment variable is required.", file=sys.stderr)
        sys.exit(1)

    # Load steps
    try:
        with open(args.steps_json) as f:
            steps_data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading steps file '{args.steps_json}': {e}", file=sys.stderr)
        sys.exit(1)

    steps = steps_data.get("steps", [])
    if not steps:
        print("Error: No steps found in the steps JSON file.", file=sys.stderr)
        sys.exit(1)

    headers = get_auth_headers(email, token)
    page_id, base_url = extract_page_id_and_base(args.target_url)

    if not page_id:
        print(f"Error: Could not extract page ID from URL: {args.target_url}", file=sys.stderr)
        sys.exit(1)

    # Get current page version and body
    page = api_get(f"{base_url}/rest/api/content/{page_id}?expand=body.storage,version,title", headers)
    current_version = page["version"]["number"]
    current_body = page["body"]["storage"]["value"]
    page_title = page["title"]

    # Build and upload the Gliffy diagram
    diagram_json = build_gliffy_diagram(args.diagram_name, steps)
    create_gliffy_diagram(base_url, page_id, args.diagram_name, diagram_json, headers)

    # Insert the macro into the page body under the specified heading
    new_body = insert_gliffy_macro(current_body, args.heading, args.diagram_name, page_id)

    # Update the page
    api_put(
        f"{base_url}/rest/api/content/{page_id}",
        headers,
        {
            "version": {"number": current_version + 1},
            "title": page_title,
            "type": "page",
            "body": {"storage": {"value": new_body, "representation": "storage"}}
        }
    )

    print(json.dumps({
        "diagram_name": args.diagram_name,
        "steps_count": len(steps),
        "target_page": page_title,
        "status": "created"
    }, indent=2))


if __name__ == "__main__":
    main()
