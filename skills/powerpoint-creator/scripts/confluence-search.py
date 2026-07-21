#!/usr/bin/env python3
"""
Search Confluence for pages matching a keyword and return clean text excerpts.

Usage:
    python confluence-search.py --keyword "booklets" --space CDTPACS
    python confluence-search.py --keyword "advisor termination" --max-results 5

Arguments:
    --keyword       Search term (required)
    --space         Confluence space key (default: CDTPACS)
    --max-results   Maximum number of pages to return (default: 3)
    --max-chars     Maximum characters of body text per page (default: 1500)
    --domain        Confluence domain (or set CONFLUENCE_DOMAIN / JIRA_URL env var)
    --email         Atlassian account email (or set CONFLUENCE_EMAIL / email env var)
    --token         API token (or set CONFLUENCE_TOKEN / JIRA_API_TOKEN env var)

Outputs JSON:
    {
      "keyword": "...",
      "space": "CDTPACS",
      "results": [
        {
          "title": "Page Title",
          "url": "https://...",
          "text": "Plain text content excerpt..."
        }
      ]
    }
"""

import argparse
import base64
import html as html_lib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _load_env():
    path = Path(__file__).resolve()
    for parent in [path, *path.parents]:
        env_file = parent / ".env"
        if env_file.is_file():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())
            break


_load_env()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search Confluence pages by keyword.")
    parser.add_argument("--keyword", required=True, help="Search keyword")
    parser.add_argument("--space", default="CDTPACS", help="Confluence space key")
    parser.add_argument("--max-results", type=int, default=3, help="Max pages to return")
    parser.add_argument("--max-chars", type=int, default=1500, help="Max body chars per page")
    parser.add_argument("--domain", default=None)
    parser.add_argument("--email", default=None)
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    if not args.domain:
        jira_url = os.environ.get("JIRA_URL", "")
        if jira_url:
            args.domain = jira_url.replace("https://", "").replace("http://", "").rstrip("/")
        else:
            args.domain = "manulife-cdn.atlassian.net"

    if not args.email:
        args.email = (os.environ.get("CONFLUENCE_EMAIL")
                      or os.environ.get("JIRA_EMAIL")
                      or os.environ.get("email"))
    if not args.email:
        print("Error: email not set.", file=sys.stderr)
        sys.exit(1)

    if not args.token:
        args.token = (os.environ.get("CONFLUENCE_TOKEN")
                      or os.environ.get("JIRA_API_TOKEN"))
    if not args.token:
        print("Error: API token not set.", file=sys.stderr)
        sys.exit(1)

    return args


def make_auth_header(email: str, token: str) -> str:
    return "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()


def confluence_request(url: str, auth: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": auth,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} — {e.read().decode()[:200]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def strip_html(raw: str) -> str:
    """Strip HTML/XML tags and decode entities to plain text."""
    # Remove style blocks first (they contain a lot of noise)
    raw = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.DOTALL)
    # Strip all remaining tags
    raw = re.sub(r"<[^>]+>", " ", raw)
    # Decode HTML entities
    raw = html_lib.unescape(raw)
    # Collapse whitespace
    return re.sub(r"\s+", " ", raw).strip()


def search_pages(base_url: str, auth: str, keyword: str, space: str, max_results: int) -> list:
    cql = f'space="{space}" AND type=page AND text~"{keyword}" ORDER BY lastmodified DESC'
    params = urllib.parse.urlencode({
        "cql": cql,
        "limit": max_results,
    })
    url = f"{base_url}/wiki/rest/api/content/search?{params}"
    data = confluence_request(url, auth)
    return data.get("results", [])


def fetch_page_body(base_url: str, auth: str, page_id: str) -> str:
    url = f"{base_url}/wiki/rest/api/content/{page_id}?expand=body.storage"
    data = confluence_request(url, auth)
    raw = data.get("body", {}).get("storage", {}).get("value", "")
    return strip_html(raw)


def main() -> None:
    args = parse_args()
    base_url = f"https://{args.domain}"
    auth = make_auth_header(args.email, args.token)

    pages = search_pages(base_url, auth, args.keyword, args.space, args.max_results)

    if not pages:
        print(json.dumps({"keyword": args.keyword, "space": args.space, "results": []}))
        return

    results = []
    for page in pages:
        page_id = page["id"]
        title = page.get("title", "")
        url = f"{base_url}/wiki{page.get('_links', {}).get('webui', '')}"

        # Only fetch body for actual pages (not attachments)
        if page.get("type") != "page":
            continue

        body = fetch_page_body(base_url, auth, page_id)
        excerpt = body[: args.max_chars]

        results.append({"title": title, "url": url, "text": excerpt})

    print(json.dumps({"keyword": args.keyword, "space": args.space, "results": results}, indent=2))


if __name__ == "__main__":
    main()
