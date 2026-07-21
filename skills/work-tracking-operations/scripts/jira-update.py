#!/usr/bin/env python3
"""
Update a Jira ticket's status (transition) via the Jira REST API.
Supports both direct ticket key and keyword search to locate a ticket.

Usage:
    # Transition by ticket key:
    python jira-update.py --domain DOMAIN --email EMAIL --ticket PROJ-123 --status "Done"

    # Search for a ticket by keyword, then transition:
    python jira-update.py --domain DOMAIN --email EMAIL --search "database table" --project PROJ --status "Done"

    # List available swimlanes for a ticket:
    python jira-update.py --domain DOMAIN --email EMAIL --ticket PROJ-123 --list-transitions

Arguments:
    --domain            Jira cloud domain, e.g. mycompany.atlassian.net
    --email             Atlassian account email used for authentication
    --token             Jira API token (or set JIRA_API_TOKEN env var)
    --ticket            Jira issue key, e.g. PROJ-123 (mutually exclusive with --search)
    --search            Keyword to search for in ticket summaries
    --project           Project key to scope the search (e.g. PROJ)
    --assignee          Assignee email to scope the search (defaults to --email)
    --status            Target status/swimlane name, e.g. "Done", "Dev - In Progress"
    --list-transitions  Print available transitions for a ticket and exit

Outputs:
    Prints a JSON summary to stdout:
    {
      "ticket": "PROJ-123",
      "previous_status": "In Progress",
      "new_status": "Done",
      "success": true
    }

Exit codes:
    0 — success
    1 — error (auth failure, ticket not found, invalid transition, etc.)
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _load_env():
    """Walk up from this file to find and load a .env file."""
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
    parser = argparse.ArgumentParser(description="Update a Jira ticket status.")
    parser.add_argument("--domain", default=None, help="Jira domain (or set JIRA_DOMAIN env var)")
    parser.add_argument("--email", default=None, help="Atlassian account email (or set JIRA_EMAIL / email env var)")
    parser.add_argument(
        "--token",
        default=None,
        help="Jira API token. If omitted, reads from the JIRA_API_TOKEN environment variable.",
    )
    # Ticket identification — provide either --ticket or --search
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ticket", help="Jira issue key, e.g. PROJ-123")
    group.add_argument("--search", help="Keyword to search for in ticket summary")
    parser.add_argument("--project", help="Project key to scope the search (e.g. PROJ)")
    parser.add_argument("--assignee", help="Assignee email to scope search (defaults to --email)")
    parser.add_argument("--status", help="Target status/swimlane name, e.g. Done")
    parser.add_argument(
        "--list-transitions", action="store_true", help="List available swimlanes for a ticket and exit"
    )
    args = parser.parse_args()

    # Resolve domain and email from env if not passed
    if not args.domain:
        args.domain = os.environ.get("JIRA_DOMAIN", "manulife-cdn.atlassian.net")
    if not args.email:
        args.email = os.environ.get("JIRA_EMAIL") or os.environ.get("email")
    if not args.email:
        print("Error: Jira email not provided. Pass --email or set JIRA_EMAIL in .env", file=sys.stderr)
        sys.exit(1)

    if not args.token:
        args.token = os.environ.get("JIRA_API_TOKEN")
    if not args.token:
        print(
            "Error: Jira API token not provided. Pass --token or set the JIRA_API_TOKEN environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.ticket and not args.search:
        print("Error: Provide either --ticket or --search to identify the issue.", file=sys.stderr)
        sys.exit(1)

    if not args.list_transitions and not args.status:
        print("Error: --status is required unless --list-transitions is used.", file=sys.stderr)
        sys.exit(1)

    return args


def make_auth_header(email: str, token: str) -> str:
    credentials = f"{email}:{token}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def jira_request(url: str, auth_header: str, method: str = "GET", body: dict = None):
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Error: HTTP {e.code} — {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not reach Jira — {e.reason}", file=sys.stderr)
        sys.exit(1)


def get_issue_fields(base_url: str, auth_header: str, ticket: str) -> dict:
    url = f"{base_url}/issue/{ticket}?fields=status,customfield_10022"
    return jira_request(url, auth_header)


def search_tickets(base_url: str, auth_header: str, keyword: str, project: str = None, assignee: str = None) -> list:
    """Search for tickets by keyword in summary, optionally scoped by project and assignee."""
    jql_parts = [f'summary ~ "{keyword}"']
    if project:
        jql_parts.append(f"project = {project}")
    if assignee:
        jql_parts.append(f"assignee = '{assignee}'")
    jql = " AND ".join(jql_parts) + " ORDER BY updated DESC"

    url = f"{base_url}/search/jql"
    body = {"jql": jql, "maxResults": 10, "fields": ["summary", "status"]}
    result = jira_request(url, auth_header, method="POST", body=body)
    return result.get("issues", [])


def get_transitions(base_url: str, auth_header: str, ticket: str) -> list:
    url = f"{base_url}/issue/{ticket}/transitions"
    result = jira_request(url, auth_header)
    return result.get("transitions", [])


def find_transition_id(transitions: list, target_status: str) -> str | None:
    for t in transitions:
        if t["to"]["name"].lower() == target_status.lower():
            return t["id"]
    return None


def fix_story_points_if_needed(base_url: str, auth_header: str, ticket: str) -> bool:
    """
    Jira stores story points as floats (e.g. 1.0) but some transition validators
    compare against a regex that only allows integers (1, 2, 3...). When the stored
    value is '1.0' the regex fails even though it represents 1 point.

    Workaround: temporarily set to 0.5 (a valid regex match), perform the transition,
    then restore the original integer value. Returns True if a workaround was applied.
    """
    issue = get_issue_fields(base_url, auth_header, ticket)
    sp = issue["fields"].get("customfield_10022")
    if sp is None:
        return False

    sp_str = str(sp)
    # Detect float representation of a whole number (e.g. "1.0", "2.0")
    if "." in sp_str and sp_str.endswith(".0"):
        # Temporarily set to 0.5 to pass the regex, then restore proper int value
        int_value = int(float(sp_str))
        body_fix = {"fields": {"customfield_10022": 0.5}}
        jira_request(f"{base_url}/issue/{ticket}", auth_header, method="PUT", body=body_fix)
        return int_value  # return the original int so caller can restore it
    return False


def transition_ticket(base_url: str, auth_header: str, ticket: str, transition_id: str) -> None:
    url = f"{base_url}/issue/{ticket}/transitions"
    body = {"transition": {"id": transition_id}}
    jira_request(url, auth_header, method="POST", body=body)


def restore_story_points(base_url: str, auth_header: str, ticket: str, original_value: int) -> None:
    body = {"fields": {"customfield_10022": original_value}}
    jira_request(f"{base_url}/issue/{ticket}", auth_header, method="PUT", body=body)


def main() -> None:
    args = parse_args()
    base_url = f"https://{args.domain}/rest/api/3"
    auth_header = make_auth_header(args.email, args.token)

    # Resolve ticket key
    ticket = args.ticket
    if args.search:
        assignee = args.assignee or args.email
        issues = search_tickets(base_url, auth_header, args.search, args.project, assignee)
        if not issues:
            print(f"Error: No tickets found matching '{args.search}'.", file=sys.stderr)
            sys.exit(1)
        if len(issues) == 1:
            ticket = issues[0]["key"]
            print(f"Found: [{ticket}] {issues[0]['fields']['summary']}", file=sys.stderr)
        else:
            print("Multiple tickets found — please pick one:", file=sys.stderr)
            for i in issues:
                print(f"  {i['key']}: {i['fields']['summary']} ({i['fields']['status']['name']})", file=sys.stderr)
            sys.exit(1)

    # List transitions mode
    if args.list_transitions:
        transitions = get_transitions(base_url, auth_header, ticket)
        available = [{"id": t["id"], "name": t["to"]["name"]} for t in transitions]
        print(json.dumps({"ticket": ticket, "available_transitions": available}, indent=2))
        return

    # Get current status
    issue_data = get_issue_fields(base_url, auth_header, ticket)
    previous_status = issue_data["fields"]["status"]["name"]

    # Get available transitions
    transitions = get_transitions(base_url, auth_header, ticket)
    transition_id = find_transition_id(transitions, args.status)

    if not transition_id:
        available = [t["to"]["name"] for t in transitions]
        print(
            f"Error: Cannot transition '{ticket}' to '{args.status}'. "
            f"Available transitions: {available}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Apply story points workaround if needed, then transition
    original_sp = fix_story_points_if_needed(base_url, auth_header, ticket)
    transition_ticket(base_url, auth_header, ticket, transition_id)
    if original_sp:
        restore_story_points(base_url, auth_header, ticket, original_sp)

    result = {
        "ticket": ticket,
        "previous_status": previous_status,
        "new_status": args.status,
        "success": True,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
