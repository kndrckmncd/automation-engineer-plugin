#!/usr/bin/env python3
"""
Query Jira for team member tickets and sprint story points.

Usage:
    # List tickets assigned to a team member (by display name):
    python jira-query.py --user "Joshua Ilunio"
    python jira-query.py --user "Shara Faelga" --status "Dev - In Progress"

    # Show story points remaining in the active sprint:
    python jira-query.py --sprint-points --project CTFSLBEB

    # Show story points remaining for a specific person in the active sprint:
    python jira-query.py --sprint-points --project CTFSLBEB --user "Joshua Ilunio"

Arguments:
    --user              Display name (or partial) of the team member to look up
    --status            Filter tickets by status (e.g. "Dev - In Progress", "Backlog")
    --sprint-points     Show story points remaining in the active sprint
    --project           Project key (default: CTFSLBEB)
    --domain            Jira cloud domain (or set JIRA_DOMAIN / JIRA_URL env var)
    --email             Atlassian account email (or set email env var)
    --token             Jira API token (or set JIRA_API_TOKEN env var)

Outputs JSON to stdout.
"""

import argparse
import base64
import json
import os
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
    parser = argparse.ArgumentParser(description="Query Jira tickets and sprint data.")
    parser.add_argument("--domain", default=None, help="Jira domain (e.g. mycompany.atlassian.net)")
    parser.add_argument("--email", default=None, help="Atlassian account email")
    parser.add_argument("--token", default=None, help="Jira API token (or JIRA_API_TOKEN env var)")
    parser.add_argument("--user", default=None, help="Display name of team member to look up")
    parser.add_argument("--status", default=None, help="Filter by ticket status")
    parser.add_argument("--sprint-points", action="store_true", help="Show story points remaining in active sprint")
    parser.add_argument("--project", default="CTFSLBEB", help="Project key (default: CTFSLBEB)")

    args = parser.parse_args()

    # Resolve domain from env
    if not args.domain:
        jira_url = os.environ.get("JIRA_URL", "")
        if jira_url:
            # Strip protocol prefix if present
            args.domain = jira_url.replace("https://", "").replace("http://", "").rstrip("/")
        else:
            args.domain = "manulife-cdn.atlassian.net"

    if not args.email:
        args.email = os.environ.get("JIRA_EMAIL") or os.environ.get("email")
    if not args.email:
        print("Error: Jira email not provided. Pass --email or set email in .env", file=sys.stderr)
        sys.exit(1)

    if not args.token:
        args.token = os.environ.get("JIRA_API_TOKEN")
    if not args.token:
        print("Error: Jira API token not provided. Pass --token or set JIRA_API_TOKEN in .env", file=sys.stderr)
        sys.exit(1)

    if not args.user and not args.sprint_points:
        print("Error: Provide --user and/or --sprint-points.", file=sys.stderr)
        sys.exit(1)

    return args


def make_auth_header(email: str, token: str) -> str:
    credentials = f"{email}:{token}"
    return "Basic " + base64.b64encode(credentials.encode()).decode()


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


def find_user(base_url: str, auth_header: str, display_name: str) -> dict:
    """Find a Jira user by display name. Returns the best match."""
    encoded = urllib.parse.quote(display_name)
    url = f"{base_url}/user/search?query={encoded}&maxResults=20"
    users = jira_request(url, auth_header)
    if not users:
        print(f"Error: No Jira user found matching '{display_name}'.", file=sys.stderr)
        sys.exit(1)

    # Exact match first (case-insensitive)
    name_lower = display_name.lower()
    for u in users:
        if u.get("displayName", "").lower() == name_lower:
            return u

    # Partial match
    for u in users:
        if name_lower in u.get("displayName", "").lower():
            return u

    # Fall back to first result
    return users[0]


def fetch_user_tickets(base_url: str, auth_header: str, account_id: str, status: str = None, project: str = None) -> list:
    """Fetch all tickets assigned to a user, optionally filtered by status and project."""
    jql_parts = [f"assignee = '{account_id}'"]
    if project:
        jql_parts.append(f"project = {project}")
    if status:
        jql_parts.append(f"status = \"{status}\"")
    jql = " AND ".join(jql_parts) + " ORDER BY updated DESC"

    body = {
        "jql": jql,
        "maxResults": 100,
        "fields": ["summary", "status", "priority", "issuetype", "story_points", "customfield_10022", "sprint"],
    }
    result = jira_request(f"{base_url}/search/jql", auth_header, method="POST", body=body)
    return result.get("issues", []), result.get("total", 0)


def find_active_sprint(base_url_agile: str, auth_header: str, project: str) -> dict | None:
    """Find the active sprint for a project via the Agile API."""
    # First, find the board for the project
    boards_url = f"{base_url_agile}/board?projectKeyOrId={project}&maxResults=10"
    boards_data = jira_request(boards_url, auth_header)
    boards = boards_data.get("values", [])

    if not boards:
        print(f"Error: No Scrum board found for project '{project}'.", file=sys.stderr)
        sys.exit(1)

    # Use first board (most likely the main one)
    board_id = boards[0]["id"]
    board_name = boards[0]["name"]
    print(f"Using board: [{board_id}] {board_name}", file=sys.stderr)

    # Find active sprint on this board
    sprints_url = f"{base_url_agile}/board/{board_id}/sprint?state=active"
    sprints_data = jira_request(sprints_url, auth_header)
    sprints = sprints_data.get("values", [])

    if not sprints:
        print(f"Error: No active sprint found on board '{board_name}'.", file=sys.stderr)
        sys.exit(1)

    return sprints[0], board_id


def fetch_sprint_issues(base_url: str, base_url_agile: str, auth_header: str, sprint_id: int, board_id: int, account_id: str = None) -> list:
    """Fetch all issues in a sprint, optionally filtered by assignee."""
    jql_parts = [f"sprint = {sprint_id}"]
    if account_id:
        jql_parts.append(f"assignee = '{account_id}'")
    jql = " AND ".join(jql_parts) + " ORDER BY status ASC"

    body = {
        "jql": jql,
        "maxResults": 200,
        "fields": ["summary", "status", "priority", "issuetype", "customfield_10022", "assignee"],
    }
    result = jira_request(f"{base_url}/search/jql", auth_header, method="POST", body=body)
    return result.get("issues", [])


def summarise_sprint_points(issues: list) -> dict:
    """Calculate total, completed, and remaining story points in a sprint."""
    total_sp = 0.0
    done_sp = 0.0
    remaining_sp = 0.0
    done_statuses = {"done", "cancelled", "closed"}

    breakdown = []
    for issue in issues:
        fields = issue["fields"]
        sp = fields.get("customfield_10022") or 0
        status = fields["status"]["name"]
        is_done = status.lower() in done_statuses

        total_sp += sp
        if is_done:
            done_sp += sp
        else:
            remaining_sp += sp

        breakdown.append({
            "key": issue["key"],
            "summary": fields["summary"],
            "status": status,
            "story_points": sp,
            "assignee": (fields.get("assignee") or {}).get("displayName", "Unassigned"),
        })

    return {
        "total_story_points": total_sp,
        "completed_story_points": done_sp,
        "remaining_story_points": remaining_sp,
        "issues": breakdown,
    }


def format_tickets_output(issues: list, total: int, user_name: str, status_filter: str = None) -> dict:
    """Format ticket list for output."""
    # Group by status
    groups: dict[str, list] = {}
    for issue in issues:
        st = issue["fields"]["status"]["name"]
        groups.setdefault(st, []).append({
            "key": issue["key"],
            "summary": issue["fields"]["summary"],
            "priority": (issue["fields"].get("priority") or {}).get("name", "None"),
            "type": issue["fields"]["issuetype"]["name"],
        })

    return {
        "assignee": user_name,
        "total": total,
        "status_filter": status_filter,
        "by_status": groups,
    }


def main() -> None:
    args = parse_args()
    base_url = f"https://{args.domain}/rest/api/3"
    base_url_agile = f"https://{args.domain}/rest/agile/1.0"
    auth_header = make_auth_header(args.email, args.token)

    user = None
    account_id = None

    # Resolve user if provided
    if args.user:
        user = find_user(base_url, auth_header, args.user)
        account_id = user["accountId"]
        print(f"Resolved user: {user['displayName']} ({user.get('emailAddress', '')})", file=sys.stderr)

    # Sprint points mode
    if args.sprint_points:
        sprint, board_id = find_active_sprint(base_url_agile, auth_header, args.project)
        sprint_id = sprint["id"]
        sprint_name = sprint["name"]
        print(f"Active sprint: [{sprint_id}] {sprint_name}", file=sys.stderr)

        issues = fetch_sprint_issues(base_url, base_url_agile, auth_header, sprint_id, board_id, account_id)
        summary = summarise_sprint_points(issues)

        output = {
            "sprint": sprint_name,
            "project": args.project,
            "filtered_by": user["displayName"] if user else "all team members",
            **summary,
        }
        print(json.dumps(output, indent=2))
        return

    # User ticket listing mode
    issues, total = fetch_user_tickets(base_url, auth_header, account_id, args.status, args.project)
    output = format_tickets_output(issues, total, user["displayName"], args.status)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
