"""
Jira GL Code Lookup
===================
Fetches your Jira epics and extracts the Related GL Code (customfield_25042)
so you can use them in the Planview time logger config.

Usage:
    python lookup-gl-codes.py [--jql "project = CTFSLBEB AND issuetype = Epic"]
"""

import os
import sys
import json
import argparse
import base64
import requests
from pathlib import Path


def _load_env():
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        env_file = parent / ".env"
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file, override=False)
            break


_load_env()


def jira_request(path, method="GET", body=None):
    domain = "manulife-cdn.atlassian.net"
    token  = os.environ.get("JIRA_API_TOKEN", "")
    email  = os.environ.get("JIRA_EMAIL") or os.environ.get("email", "")

    url = f"https://{domain}/rest/api/3{path}"
    resp = requests.request(
        method, url,
        auth=(email, token),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        json=body,
        timeout=30,
        verify=False,
    )
    if not resp.ok:
        print(f"HTTP {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
    resp.raise_for_status()
    return resp.json()


def fetch_epics_with_gl_codes(jql):
    results = []
    next_page_token = None
    while True:
        body = {
            "jql":        jql,
            "fields":     ["summary", "status", "customfield_25042", "customfield_25041"],
            "maxResults": 50,
        }
        if next_page_token:
            body["nextPageToken"] = next_page_token

        data = jira_request("/search/jql", method="POST", body=body)
        issues = data.get("issues", [])
        if not issues:
            break
        for issue in issues:
            f = issue["fields"]
            gl_code = f.get("customfield_25042") or ""
            if gl_code:
                results.append({
                    "key":      issue["key"],
                    "summary":  f.get("summary", ""),
                    "gl_code":  gl_code,
                    "status":   (f.get("status") or {}).get("name", ""),
                    "epic_id":  f.get("customfield_25041") or "",
                })
        next_page_token = data.get("nextPageToken")
        if not next_page_token or len(issues) < 50:
            break
    return results


def main():
    parser = argparse.ArgumentParser(description="List Jira epics with Related GL Codes")
    parser.add_argument(
        "--jql",
        default='assignee = currentUser() AND issuetype = Epic ORDER BY updated DESC',
        help="JQL query to filter epics"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    print(f"Fetching epics: {args.jql}\n")
    epics = fetch_epics_with_gl_codes(args.jql)

    if not epics:
        print("No epics with GL codes found.")
        return

    if args.json:
        print(json.dumps(epics, indent=2))
        return

    print(f"{'Key':<20} {'GL Code':<20} {'Summary':<60}")
    print("-" * 100)
    for e in epics:
        print(f"{e['key']:<20} {e['gl_code']:<20} {e['summary'][:60]}")

    print(f"\nTotal: {len(epics)} epic(s) with GL codes")


if __name__ == "__main__":
    main()
