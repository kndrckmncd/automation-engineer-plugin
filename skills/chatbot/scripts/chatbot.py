#!/usr/bin/env python3
"""
Automation Engineer Bot — terminal chatbot for triggering plugin skills.

Usage:
    python chatbot.py

Supported skills:
    - PowerPoint Creator    : "create a ppt about X", "make a deck for X"
    - Jira Operations       : "move ticket X to Y", "find ticket X", "list my tickets"
    - Gliffy Diagram        : "create a diagram for X", "make a flowchart of X"

Exit:
    Type 'quit' or 'exit', or press Ctrl+C.
"""

import base64
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from textwrap import dedent

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Load .env from repo root ──────────────────────────────────────────────────
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

# ── Rich UI (optional) ────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None

# ── Script paths (relative to this file inside skills/) ───────────────────────
SKILLS_ROOT  = Path(__file__).resolve().parent.parent.parent
PPT_SCRIPT   = SKILLS_ROOT / "powerpoint-creator"       / "scripts" / "create-presentation.py"
JIRA_SCRIPT  = SKILLS_ROOT / "work-tracking-operations" / "scripts" / "jira-update.py"
DIAG_SCRIPT  = SKILLS_ROOT / "gliffy-flowchart-creator" / "scripts" / "create-diagram.py"

# ── Jira defaults ─────────────────────────────────────────────────────────────
JIRA_DOMAIN  = "manulife-cdn.atlassian.net"
JIRA_EMAIL   = os.environ.get("JIRA_EMAIL") or os.environ.get("email", "manisea@mfcgd.com")
JIRA_PROJECT = "CTFSLBEB"

# ── Intent patterns ───────────────────────────────────────────────────────────
INTENTS = {
    "ppt": [
        r"\b(create|make|build|generate|write)\b.*(ppt|powerpoint|presentation|deck|slides?)\b",
        r"\b(ppt|powerpoint|presentation|deck)\b.*(about|on|for)\b",
        r"\bslide.*(deck|present)\b",
    ],
    "jira_move": [
        r"\b(move|transition|update|set|change)\b.*(ticket|issue|story|task)\b",
        r"\bticket\b.*(to|into)\b",
        r"\b(CTFSLBEB|CTFSLACE)-\d+\b.*(to|done|progress|backlog)\b",
    ],
    "jira_find": [
        r"\b(find|search|look ?up|show|get)\b.*(ticket|issue|story)\b",
        r"\bticket\b.*(find|search|where|what)\b",
    ],
    "jira_list": [
        r"\b(list|show all|display)\b.*(ticket|issue|story|mlm)\b",
        r"\bmy (mlm|jira|ctfsl).*(ticket|issue)\b",
        r"\ball tickets?\b",
    ],
    "gliffy": [
        r"\b(create|make|build|generate|draw)\b.*(diagram|flowchart|flow chart|swimlane|gliffy)\b",
        r"\b(diagram|flowchart|swimlane)\b.*(for|of|about)\b",
    ],
    "help": [r"^help$", r"\bwhat can you\b", r"\bcommands?\b", r"\bwhat do you\b"],
    "exit": [r"^(quit|exit|bye|goodbye|stop)$"],
}


# ── UI helpers ────────────────────────────────────────────────────────────────

def bot(msg: str, style: str = "cyan") -> None:
    tag = "[Bot]"
    if HAS_RICH:
        console.print(f"[{style}]{tag} {msg}[/]")
    else:
        print(f"{tag} {msg}")


def ask(prompt: str = "You") -> str:
    if HAS_RICH:
        return console.input(f"[bold white]{prompt}:[/] ").strip()
    return input(f"{prompt}: ").strip()


def info(msg: str)    -> None: bot(msg, "blue")
def ok(msg: str)      -> None: bot(msg, "green")
def warn(msg: str)    -> None: bot(msg, "yellow")
def err(msg: str)     -> None: bot(msg, "red")
def say(msg: str)     -> None: bot(msg, "cyan")


def table(rows: list[tuple], headers: list[str]) -> None:
    if HAS_RICH:
        t = Table(*headers, show_lines=True, style="cyan")
        for row in rows:
            t.add_row(*[str(c) for c in row])
        console.print(t)
    else:
        print("  " + " | ".join(headers))
        print("  " + "-" * 60)
        for row in rows:
            print("  " + " | ".join(str(c) for c in row))


# ── Core helpers ──────────────────────────────────────────────────────────────

def detect_intent(text: str) -> str:
    t = text.lower().strip()
    for intent, patterns in INTENTS.items():
        for p in patterns:
            if re.search(p, t):
                return intent
    return "unknown"


def run(cmd: list[str]) -> tuple[bool, str, str]:
    """Run a Python script. Returns (success, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable] + [str(c) for c in cmd],
        capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()


def get_token() -> str:
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not token:
        warn("JIRA_API_TOKEN not set. Please enter your Jira API token:")
        token = ask("Token")
    return token


def jira_auth_header() -> str:
    token = get_token()
    return "Basic " + base64.b64encode(f"{JIRA_EMAIL}:{token}".encode()).decode()


def jira_request(path: str, method: str = "GET", body: dict = None) -> dict:
    url = f"https://{JIRA_DOMAIN}/rest/api/3/{path}"
    headers = {"Authorization": jira_auth_header(),
               "Content-Type": "application/json", "Accept": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            content = r.read()
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err(f"HTTP {e.code}: {e.read().decode()}")
        return {}


# ── Skill: Jira ───────────────────────────────────────────────────────────────

STATUS_MAP = {
    "done": "Done", "complete": "Done", "finished": "Done",
    "dev in progress": "Dev - In Progress", "dev": "Dev - In Progress",
    "in progress": "Dev - In Progress", "inprogress": "Dev - In Progress",
    "backlog": "Backlog", "review": "Code Review",
    "testing": "QA Testing", "qa": "QA Testing",
    "blocked": "Blocked",
}


def handle_jira_list() -> None:
    info("Fetching your CTFSLBEB tickets...")
    jql  = f"project = {JIRA_PROJECT} AND assignee = '{JIRA_EMAIL}' ORDER BY updated DESC"
    resp = jira_request("search/jql", method="POST",
                        body={"jql": jql, "maxResults": 25, "fields": ["summary", "status"]})
    issues = resp.get("issues", [])
    if not issues:
        warn("No tickets found.")
        return
    rows = [(i["key"], i["fields"]["summary"][:60], i["fields"]["status"]["name"]) for i in issues]
    table(rows, ["Key", "Summary", "Status"])


def handle_jira_find(text: str) -> None:
    kw_match = re.search(r"\b(find|search|look\s?up|show|get)\b\s+(?:ticket\s+)?(?:for\s+)?(.+)$", text, re.I)
    keyword  = kw_match.group(2).strip() if kw_match else ""
    if not keyword:
        say("What ticket are you looking for? (keyword or ticket ID)")
        keyword = ask()

    info(f"Searching for '{keyword}'...")
    jql  = f'project = {JIRA_PROJECT} AND summary ~ "{keyword}" ORDER BY updated DESC'
    resp = jira_request("search/jql", method="POST",
                        body={"jql": jql, "maxResults": 10, "fields": ["summary", "status"]})
    issues = resp.get("issues", [])
    if not issues:
        warn("No tickets found.")
        return
    rows = [(i["key"], i["fields"]["summary"][:60], i["fields"]["status"]["name"]) for i in issues]
    table(rows, ["Key", "Summary", "Status"])


def handle_jira_move(text: str) -> None:
    ticket_match = re.search(r"\b(CTFSLBEB|CTFSLACE)-\d+\b", text, re.I)
    ticket_id    = ticket_match.group(0).upper() if ticket_match else ""

    if not ticket_id:
        say("No ticket ID found. Enter a ticket ID (e.g. CTFSLBEB-809) or a keyword to search:")
        raw = ask().strip()
        if re.match(r"^(CTFSLBEB|CTFSLACE)-\d+$", raw, re.I):
            ticket_id = raw.upper()
        else:
            # Search by keyword
            info(f"Searching for '{raw}'...")
            jql  = f'project = {JIRA_PROJECT} AND summary ~ "{raw}" ORDER BY updated DESC'
            resp = jira_request("search/jql", method="POST",
                                body={"jql": jql, "maxResults": 10, "fields": ["summary", "status"]})
            issues = resp.get("issues", [])
            if not issues:
                warn("No tickets found. Try again with a ticket ID.")
                return
            if len(issues) == 1:
                ticket_id = issues[0]["key"]
                say(f"Found: [{ticket_id}] {issues[0]['fields']['summary']}")
            else:
                rows = [(i["key"], i["fields"]["summary"][:55], i["fields"]["status"]["name"]) for i in issues]
                table(rows, ["#", "Summary", "Status"])
                say("Enter the ticket ID from the list above:")
                ticket_id = ask().strip().upper()

    target = ""
    for kw, status in STATUS_MAP.items():
        if kw in text.lower():
            target = status
            break
    if not target:
        say("Where should I move it to?")
        say("Options: Done | Dev - In Progress | Backlog | Code Review | QA Testing | Blocked")
        target = ask()

    info(f"Moving {ticket_id} to '{target}'...")
    token = get_token()
    ok_run, stdout, stderr = run([
        JIRA_SCRIPT,
        "--domain", JIRA_DOMAIN, "--email", JIRA_EMAIL, "--token", token,
        "--ticket", ticket_id, "--status", target,
    ])
    if ok_run:
        try:
            data = json.loads(stdout)
            ok(f"Done! {ticket_id}: '{data['previous_status']}' -> '{data['new_status']}'")
        except Exception:
            ok(f"Done! {stdout or stderr}")
    else:
        err(f"Error: {stderr or stdout}")


# ── Skill: PowerPoint ─────────────────────────────────────────────────────────

PPT_SLIDES = {
    "rpa": [
        ("Introduction to RPA",
         ["Robotic Process Automation automates rule-based digital tasks",
          "Bots mimic human actions — no changes to existing systems needed",
          "Scope: which processes are targeted for automation"]),
        ("Current Process (As-Is)",
         ["Manual steps involved in the current workflow",
          "Pain points: high error rate, processing delays, staff effort",
          "Volume and frequency of transactions processed"]),
        ("Bot Solution Design",
         ["Technology stack: AA360 / Power Automate",
          "Input triggers, data sources, and integration points",
          "Key automation logic and decision points"]),
        ("Implementation Steps",
         ["Phase 1: Development and unit testing",
          "Phase 2: SIT and UAT sign-off with business",
          "Phase 3: Production deployment and hypercare"]),
        ("Exception Handling",
         ["Business exceptions: invalid data, missing records",
          "System exceptions: connectivity failures, timeouts",
          "Escalation paths and manual fallback procedures"]),
        ("Results & Next Steps",
         ["Expected time savings and error reduction metrics",
          "KPIs: throughput, accuracy, cost savings",
          "Future enhancements and automation roadmap"]),
    ],
    "mlm": [
        ("Project Background",
         ["MLM system modernisation scope and objectives",
          "Policy, agent, and commission processing workflows",
          "Key stakeholders, timeline, and project phases"]),
        ("As-Is Process",
         ["Current manual workflow steps end-to-end",
          "Systems involved: PolicyCenter, DSS, CAPSIL, BizTalk",
          "Known pain points, bottlenecks, and error hotspots"]),
        ("System Overview",
         ["Integration landscape: source and target systems",
          "Data flow between platforms and APIs",
          "File-based and real-time interfaces"]),
        ("Bot Design",
         ["Automation approach and swimlane ownership",
          "Key business rules encoded in the bot",
          "Exception handling and escalation logic"]),
        ("Testing & UAT",
         ["Test scenarios mapped to As-Is process steps",
          "UAT sign-off criteria and acceptance conditions",
          "Defect tracking, resolution, and regression testing"]),
        ("Go-Live Plan",
         ["Cutover strategy and rollback plan",
          "Hypercare period: support model and escalation",
          "Post-go-live monitoring, KPIs, and reporting"]),
    ],
    "automation": [
        ("Overview",
         ["Project name, objective, and target audience",
          "Team members, roles, and responsibilities",
          "Timeline and key delivery milestones"]),
        ("Problem Statement",
         ["Current state pain points and business impact",
          "Root causes driving the need for automation",
          "Why automation is the right approach"]),
        ("Solution Architecture",
         ["Tools and technologies selected",
          "High-level design and data flow",
          "Integration points with existing systems"]),
        ("Technical Details",
         ["Detailed logic, decision trees, and business rules",
          "Data inputs, transformations, and outputs",
          "Error handling, logging, and monitoring"]),
        ("Results & Metrics",
         ["Time saved per transaction and per day",
          "Error rate: before vs. after automation",
          "ROI and business value delivered"]),
        ("Lessons Learned",
         ["What went well during design and development",
          "Challenges encountered and how they were resolved",
          "Recommendations for future automation projects"]),
    ],
    "default": [
        ("Introduction",
         ["Purpose and scope of this presentation",
          "Background and context",
          "Key objectives and expected outcomes"]),
        ("Background & Context",
         ["Problem or opportunity being addressed",
          "Current state and constraints",
          "Relevant stakeholders and dependencies"]),
        ("Solution Overview",
         ["Proposed approach and rationale",
          "High-level design",
          "Tools, technologies, or processes involved"]),
        ("Key Details",
         ["Step-by-step breakdown of the solution",
          "Key decisions and trade-offs made",
          "Risks and mitigation strategies"]),
        ("Implementation",
         ["Timeline, phases, and milestones",
          "Resources required and team responsibilities",
          "Success criteria and acceptance conditions"]),
        ("Summary & Next Steps",
         ["Key takeaways from this presentation",
          "Immediate actions and owners",
          "Open questions and follow-up items"]),
    ],
}


def generate_outline(topic: str) -> list[dict]:
    key = next((k for k in PPT_SLIDES if k in topic.lower()), "default")
    return [{"title": t, "content": bullets} for t, bullets in PPT_SLIDES[key]]


def handle_ppt(text: str) -> None:
    m     = re.search(r"\b(about|on|for|regarding)\b\s+(.+)$", text, re.I)
    topic = m.group(2).strip() if m else ""
    if not topic:
        say("What is the presentation about?")
        topic = ask()

    say(f"Title? (Press Enter to use: '{topic}')")
    title_in = ask()
    title    = title_in or topic

    say("Author name? (Press Enter to skip)")
    author = ask()

    say("Generating slide outline...")
    outline = generate_outline(topic)

    say("Here's the proposed outline:")
    for i, s in enumerate(outline, 1):
        if HAS_RICH:
            console.print(f"  [bold]{i}.[/] {s['title']}")
        else:
            print(f"  {i}. {s['title']}")

    say("Looks good? (yes / no — or type custom slide titles separated by commas)")
    confirm = ask()

    if confirm.lower() not in ("yes", "y", ""):
        if "," in confirm:
            titles  = [t.strip() for t in confirm.split(",")]
            outline = [{"title": t, "content": [f"{t} — point 1", f"{t} — point 2"]} for t in titles]
        else:
            say("Enter slide titles separated by commas:")
            raw     = ask()
            titles  = [t.strip() for t in raw.split(",")]
            outline = [{"title": t, "content": [f"{t} — point 1", f"{t} — point 2"]} for t in titles]

    config = {"title": title, "subtitle": f"Overview: {topic}", "author": author, "slides": outline}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        tmp = f.name

    info("Building your PowerPoint...")
    ok_run, stdout, stderr = run([PPT_SCRIPT, "--slides-json", tmp])
    Path(tmp).unlink(missing_ok=True)

    if ok_run:
        try:
            data = json.loads(stdout)
            ok(f"✅ Saved: {data['output']}  ({data['total_slides']} slides)")
        except Exception:
            ok(f"✅ Done! {stdout}")
    else:
        err(f"❌ {stderr or stdout}")


# ── Skill: Gliffy Diagram ─────────────────────────────────────────────────────

def handle_gliffy(text: str) -> None:
    m     = re.search(r"\b(for|of|about|on)\b\s+(.+)$", text, re.I)
    topic = m.group(2).strip() if m else ""
    if not topic:
        say("What process should the diagram document?")
        topic = ask()

    say(f"Got it. Let's build a swimlane diagram for: '{topic}'")
    say("What is the source system or inserter? (e.g. PolicyCenter, Portal — Press Enter to skip)")
    inserter = ask() or "System"

    say("How many subprocess lanes do you need? (Press Enter for 1)")
    num_input = ask()
    num_lanes = int(num_input) if num_input.isdigit() else 1

    lanes = []
    for i in range(num_lanes):
        say(f"Lane {i+1} name? (e.g. DSS, BizTalk, CAPSIL)")
        lane_name = ask() or f"Lane {i+1}"
        say(f"Steps for '{lane_name}' (one per line — blank line to finish):")
        steps = []
        while True:
            step = ask(f"  Step {len(steps)+1}")
            if not step:
                break
            steps.append(step)
        lanes.append({"name": lane_name, "steps": steps or ["Process Step 1", "Process Step 2"]})

    config = {
        "system_name": topic,
        "inserter_source": inserter,
        "subprocess_lanes": lanes,
    }

    info("Generating Gliffy diagram...")
    ok_run, stdout, stderr = run([
        DIAG_SCRIPT,
        "--diagram-name", topic.replace(" ", "_"),
        "--config-json", json.dumps(config),
    ])

    if ok_run:
        ok(f"✅ Diagram generated!\n{stdout or 'Check your Downloads folder.'}")
    else:
        err(f"❌ {stderr or stdout}")


# ── Help ──────────────────────────────────────────────────────────────────────

HELP_TEXT = dedent("""
  [PPT]  PowerPoint
       "create a ppt about [topic]"
       "make a deck for [topic]"
       "build a presentation on [topic]"

  [Jira] Jira
       "move ticket CTFSLBEB-123 to Done"
       "find ticket [keyword]"
       "list my tickets"

  [Dia]  Gliffy Diagram
       "create a diagram for [process]"
       "make a flowchart of [process]"

  [?]    Other
       "help"  -- show this menu
       "quit"  -- exit
""").strip()


def show_help() -> None:
    if HAS_RICH:
        console.print(Panel(HELP_TEXT, title="[bold cyan]Available Commands[/]", border_style="cyan"))
    else:
        print("\n" + HELP_TEXT + "\n")


# ── Main loop ─────────────────────────────────────────────────────────────────

BANNER = "[Bot] Automation Engineer Bot  |  type 'help' for commands  |  'quit' to exit"


def main() -> None:
    if HAS_RICH:
        console.print(Panel(f"[bold cyan]{BANNER}[/]", border_style="cyan"))
    else:
        print("=" * 65)
        print(BANNER)
        print("=" * 65)

    say("Hi Sean! What would you like to do today?")

    handlers = {
        "ppt":        lambda t: handle_ppt(t),
        "jira_move":  lambda t: handle_jira_move(t),
        "jira_find":  lambda t: handle_jira_find(t),
        "jira_list":  lambda _: handle_jira_list(),
        "gliffy":     lambda t: handle_gliffy(t),
        "help":       lambda _: show_help(),
    }

    while True:
        try:
            text = ask("You")
        except (KeyboardInterrupt, EOFError):
            say("Goodbye!")
            break

        if not text:
            continue

        intent = detect_intent(text)

        if intent == "exit":
            say("Goodbye!")
            break
        elif intent in handlers:
            handlers[intent](text)
        else:
            warn("I didn't catch that. Type 'help' to see what I can do.")


if __name__ == "__main__":
    main()
