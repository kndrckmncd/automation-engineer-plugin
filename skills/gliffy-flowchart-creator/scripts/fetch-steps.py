#!/usr/bin/env python3
"""
Fetch as-is process steps from a Confluence page.

Reads the body of a Confluence page and extracts ordered list items,
unordered list items, or step-prefixed paragraphs as a list of process steps.

Usage:
    python fetch-steps.py --page-url URL

Inputs:
    --page-url URL   Full Confluence page URL (required)
    Environment:
        CONFLUENCE_EMAIL — Confluence user email (Cloud: required for Basic auth)
        CONFLUENCE_TOKEN — Confluence API token (Cloud) or Personal Access Token (Server/DC)

Outputs:
    JSON to stdout:
    {
      "page_id": "...",
      "page_title": "...",
      "steps": ["Step 1 text", "Step 2 text", ...]
    }

Exit codes:
    0 — success
    1 — input error (missing arg, invalid URL)
    2 — API error (auth failure, page not found)
"""

import argparse
import base64
import json
import os
import re
import sys
from typing import Any
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET

try:
    import requests
except ImportError:
    print("Error: requests is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch process steps from a Confluence page.")
    parser.add_argument("--page-url", required=True, metavar="URL", help="Full Confluence page URL.")
    return parser.parse_args()


def get_auth_headers(email: str | None, token: str) -> dict[str, str]:
    """Build Authorization header for Cloud (Basic) or Server (Bearer)."""
    if email:
        creds = base64.b64encode(f"{email}:{token}".encode()).decode()
        return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def extract_page_id_and_base(page_url: str) -> tuple[str | None, str]:
    """
    Extract the page ID and base URL from a Confluence page URL.
    Supports:
      - Cloud:  https://site.atlassian.net/wiki/spaces/SPACE/pages/12345/Title
      - Server: https://confluence.company.com/pages/viewpage.action?pageId=12345
      - Server: https://confluence.company.com/display/SPACE/Title
    Returns (page_id_or_none, base_url).
    """
    parsed = urlparse(page_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Cloud: /wiki/spaces/XX/pages/12345/...
    m = re.search(r"/pages/(\d+)", parsed.path)
    if m:
        return m.group(1), base + "/wiki" if "/wiki" in parsed.path else base

    # Server: ?pageId=12345
    qs = parse_qs(parsed.query)
    if "pageId" in qs:
        return qs["pageId"][0], base

    return None, base


def get_page_by_id(base_url: str, page_id: str, headers: dict) -> dict[str, Any]:
    url = f"{base_url}/rest/api/content/{page_id}?expand=body.storage,title"
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        print(f"API error {status}: {e}", file=sys.stderr)
        sys.exit(2)
    except requests.exceptions.ConnectionError:
        print(f"Connection failed: could not reach {url}", file=sys.stderr)
        sys.exit(2)
    except requests.exceptions.Timeout:
        print(f"Request timed out: {url}", file=sys.stderr)
        sys.exit(2)


def extract_steps_from_storage(storage_html: str) -> list[str]:
    """
    Parse Confluence storage format XML and extract process steps.
    Priority:
      1. Ordered list items (<ol><li>)
      2. Unordered list items (<ul><li>)
      3. Paragraphs matching "Step N:" or numbered patterns
    """
    # Wrap in a root element to make valid XML
    try:
        root = ET.fromstring(f"<root>{storage_html}</root>")
    except ET.ParseError:
        # Fallback: strip tags with regex
        items = re.findall(r"<li[^>]*>(.*?)</li>", storage_html, re.DOTALL)
        return [re.sub(r"<[^>]+>", "", item).strip() for item in items if item.strip()]

    steps = []

    # Try ordered list first
    ol = root.find(".//ol")
    if ol is not None:
        for li in ol.findall("li"):
            text = "".join(li.itertext()).strip()
            if text:
                steps.append(text)

    # Fall back to unordered list
    if not steps:
        ul = root.find(".//ul")
        if ul is not None:
            for li in ul.findall("li"):
                text = "".join(li.itertext()).strip()
                if text:
                    steps.append(text)

    # Fall back to step-prefixed paragraphs
    if not steps:
        for p in root.iter("p"):
            text = "".join(p.itertext()).strip()
            if re.match(r"^(step\s*\d+|^\d+[\.\)])", text, re.IGNORECASE):
                steps.append(text)

    return steps


def main() -> None:
    args = parse_args()

    email = os.environ.get("CONFLUENCE_EMAIL")
    token = os.environ.get("CONFLUENCE_TOKEN")
    if not token:
        print("Error: CONFLUENCE_TOKEN environment variable is required.", file=sys.stderr)
        sys.exit(1)

    headers = get_auth_headers(email, token)
    page_id, base_url = extract_page_id_and_base(args.page_url)

    if not page_id:
        print(f"Error: Could not extract page ID from URL: {args.page_url}", file=sys.stderr)
        sys.exit(1)

    page = get_page_by_id(base_url, page_id, headers)
    storage_html = page.get("body", {}).get("storage", {}).get("value", "")
    title = page.get("title", "Unknown")

    steps = extract_steps_from_storage(storage_html)

    if not steps:
        print(f"Warning: No process steps found on page '{title}'. Check that the page has an ordered or unordered list.", file=sys.stderr)

    print(json.dumps({"page_id": page_id, "page_title": title, "steps": steps}, indent=2))


if __name__ == "__main__":
    main()
