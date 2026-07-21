#!/usr/bin/env python3
"""
Automation Engineer Bot — Desktop UI (tkinter)
Chat window for triggering plugin skills: PowerPoint, Jira, Gliffy.

Usage:
    python chatbot_ui.py

Requirements:
    pip install python-pptx   (for PowerPoint creation)
    JIRA_API_TOKEN env var    (for Jira operations)
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import tkinter as tk

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

# ── Paths & defaults ──────────────────────────────────────────────────────────
SKILLS_ROOT        = Path(__file__).resolve().parent.parent.parent
PPT_SCRIPT         = SKILLS_ROOT / "powerpoint-creator"       / "scripts" / "create-presentation.py"
CONFLUENCE_SCRIPT  = SKILLS_ROOT / "powerpoint-creator"       / "scripts" / "confluence-search.py"
JIRA_SCRIPT        = SKILLS_ROOT / "work-tracking-operations" / "scripts" / "jira-update.py"
QUERY_SCRIPT       = SKILLS_ROOT / "work-tracking-operations" / "scripts" / "jira-query.py"
DIAG_SCRIPT        = SKILLS_ROOT / "gliffy-flowchart-creator" / "scripts" / "create-diagram.py"

JIRA_DOMAIN        = "manulife-cdn.atlassian.net"
JIRA_EMAIL         = os.environ.get("JIRA_EMAIL") or os.environ.get("email", "manisea@mfcgd.com")
JIRA_PROJECT       = "CTFSLBEB"
CONFLUENCE_SPACE   = "CDTPACS"

# ── Palette ───────────────────────────────────────────────────────────────────
C = dict(
    bg      = "#F5F9FF",
    hdr     = "#1F4E79",
    hdr_fg  = "#FFFFFF",
    hdr_sub = "#7FB3D9",
    bot_lbl = "#1F4E79",
    usr_lbl = "#2E75B6",
    ok      = "#107C10",
    err     = "#C50F1F",
    info    = "#0078D4",
    muted   = "#767676",
    input_bg= "#FFFFFF",
    input_bd= "#B8C8D8",
    btn     = "#2E75B6",
    btn_fg  = "#FFFFFF",
    sep     = "#D0DCE8",
)

# ── Intent patterns ───────────────────────────────────────────────────────────
INTENTS = {
    "ppt":               [r"\b(create|make|build|generate)\b.*(ppt|powerpoint|presentation|deck|slides?)\b",
                          r"\b(ppt|deck|presentation)\b.*(about|on|for)\b"],
    "jira_move":         [r"\b(move|transition|set|change)\b.*(ticket|issue|story|task)\b",
                          r"\bticket\b.*(to|into)\b",
                          r"\b(CTFSLBEB|CTFSLACE)-\d+\b"],
    "jira_find":         [r"\b(find|search|look\s*up|show|get)\b.*(ticket|issue|story)\b"],
    "jira_list":         [r"\b(list|show all|display)\b.*(ticket|issue|mlm)\b",
                          r"\bmy (mlm|jira).*(ticket|issue)\b",
                          r"\ball (my\s+)?(tickets?|issues?)\b"],
    "jira_user_tickets": [r"\b(show|get|fetch|list|what).*(tickets?|stories|tasks?|issues?).*(for|of|assigned to)\b",
                          r"\b(tickets?|stories|tasks?|issues?).*(for|of)\s+\w+\s+\w+",
                          r"\bwhat('?s| is)\s+\w+\s+\w+\s+(working on|doing|assigned)\b",
                          r"\b(fetch|pull|get)\b.*\b(tickets?|stories|tasks?)\b.*\b(from|for)\b"],
    "jira_sprint_points":[r"\b(story\s*points?|points?)\b.*(left|remaining|sprint|this sprint)\b",
                          r"\b(sprint|current sprint)\b.*(points?|remaining|progress|status|burndown)\b",
                          r"\bhow (many|much).*(points?|sp)\b",
                          r"\bpoints?\s+(left|remaining|to (go|complete))\b"],
    "gliffy":            [r"\b(create|make|build|draw)\b.*(diagram|flowchart|swimlane|gliffy)\b",
                          r"\b(diagram|flowchart)\b.*(for|of|about)\b"],
    "help":              [r"^help$", r"\bwhat can you\b", r"\bcommands?\b"],
    "exit":              [r"^(quit|exit|bye)$"],
}

def detect_intent(text: str) -> str:
    t = text.lower().strip()
    for intent, patterns in INTENTS.items():
        for p in patterns:
            if re.search(p, t):
                return intent
    return "unknown"

# ── PPT content templates (real bullets per topic) ────────────────────────────
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
    "gliffy": [
        ("What is the Gliffy Flowchart Skill",
         ["Generates .gliffy swimlane diagrams from process descriptions",
          "Supports Master, Inserter, and multiple subprocess lanes",
          "Output is a .gliffy JSON file ready for Confluence import"]),
        ("Plugin Marketplace & Diskillery",
         ["Copilot CLI plugins extend the agent with domain skills",
          "Diskillery is a meta-plugin for building new plugins",
          "Steps: install marketplace -> run diskillery -> publish plugin"]),
        ("Creating the Automation Engineer Agent",
         ["Ran persona-interview skill to extract role knowledge",
          "Diskillery generated agent.md and plugin scaffolding",
          "Plugin committed to kndrckmncd/automation-engineer-plugin"]),
        ("Swimlane Architecture",
         ["Master lane: high-level process trigger to end state",
          "Inserter lane: data entry and form submission steps",
          "Subprocess lanes: one per downstream system (DSS, BizTalk, CAPSIL)"]),
        ("The create-diagram.py Script",
         ["Accepts JSON config: pool name, lanes, and step definitions",
          "Builds Gliffy JSON: nodes, edges, stage dimensions",
          "Writes final .gliffy file — drag-and-drop into Confluence"]),
        ("Key Fixes & Results",
         ["Bug fix: pool width now includes all subprocess lane widths",
          "Generated MLM_Terminate.gliffy with 10 subprocess lanes",
          "Skill is reusable for any process with any number of lanes"]),
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
          "High-level design and data flow diagram",
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

def get_outline(topic: str) -> list[dict]:
    key = next((k for k in PPT_SLIDES if k in topic.lower()), "default")
    return [{"title": t, "content": bullets} for t, bullets in PPT_SLIDES[key]]

# ── Jira helpers ──────────────────────────────────────────────────────────────
STATUS_MAP = {
    "done": "Done", "complete": "Done", "finished": "Done",
    "dev in progress": "Dev - In Progress", "dev": "Dev - In Progress",
    "in progress": "Dev - In Progress", "inprogress": "Dev - In Progress",
    "backlog": "Backlog", "review": "Code Review",
    "testing": "QA Testing", "qa": "QA Testing", "blocked": "Blocked",
}

def _jira_auth() -> str:
    token = os.environ.get("JIRA_API_TOKEN", "")
    return "Basic " + base64.b64encode(f"{JIRA_EMAIL}:{token}".encode()).decode()

def _jira_req(path: str, method: str = "GET", body: dict = None) -> dict:
    url     = f"https://{JIRA_DOMAIN}/rest/api/3/{path}"
    headers = {"Authorization": _jira_auth(),
               "Content-Type": "application/json", "Accept": "application/json"}
    data    = json.dumps(body).encode() if body else None
    req     = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            content = r.read()
            return json.loads(content) if content else {}
    except Exception as e:
        return {"_error": str(e)}

def jira_search(keyword: str) -> list:
    jql  = f'project = {JIRA_PROJECT} AND summary ~ "{keyword}" ORDER BY updated DESC'
    resp = _jira_req("search/jql", "POST",
                     {"jql": jql, "maxResults": 10, "fields": ["summary", "status"]})
    return resp.get("issues", [])

def jira_list_mine() -> list:
    jql  = f"project = {JIRA_PROJECT} AND assignee = '{JIRA_EMAIL}' ORDER BY updated DESC"
    resp = _jira_req("search/jql", "POST",
                     {"jql": jql, "maxResults": 25, "fields": ["summary", "status"]})
    return resp.get("issues", [])

def run_script(cmd: list) -> tuple[bool, str, str]:
    result = subprocess.run([sys.executable] + [str(c) for c in cmd],
                            capture_output=True, text=True)
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()

# ── Confluence helpers ────────────────────────────────────────────────────────
import html as _html_lib

def _confluence_auth() -> str:
    token = os.environ.get("CONFLUENCE_TOKEN") or os.environ.get("JIRA_API_TOKEN", "")
    email = os.environ.get("CONFLUENCE_EMAIL") or JIRA_EMAIL
    return "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()

def _strip_html(raw: str) -> str:
    raw = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.DOTALL)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = _html_lib.unescape(raw)
    return re.sub(r"\s+", " ", raw).strip()

def confluence_fetch_context(keyword: str, space: str = CONFLUENCE_SPACE,
                              max_results: int = 3, max_chars: int = 1200) -> str:
    """Search Confluence and return a plain-text context block for the AI."""
    try:
        cql = f'space="{space}" AND type=page AND text~"{keyword}" ORDER BY lastmodified DESC'
        params = urllib.parse.urlencode({"cql": cql, "limit": max_results})
        url = f"https://{JIRA_DOMAIN}/wiki/rest/api/content/search?{params}"
        req = urllib.request.Request(url, headers={"Authorization": _confluence_auth(),
                                                    "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            pages = json.loads(r.read()).get("results", [])
    except Exception:
        return ""

    snippets = []
    for page in pages:
        if page.get("type") != "page":
            continue
        page_id = page["id"]
        title   = page.get("title", "")
        try:
            body_url = f"https://{JIRA_DOMAIN}/wiki/rest/api/content/{page_id}?expand=body.storage"
            req2 = urllib.request.Request(body_url, headers={"Authorization": _confluence_auth(),
                                                              "Accept": "application/json"})
            with urllib.request.urlopen(req2, timeout=15) as r2:
                raw = json.loads(r2.read()).get("body", {}).get("storage", {}).get("value", "")
            text = _strip_html(raw)[:max_chars]
            snippets.append(f"### {title}\n{text}")
        except Exception:
            continue

    return "\n\n".join(snippets)

# ── GitHub Models AI ─────────────────────────────────────────────────────────
MODELS_URL = "https://models.inference.ai.azure.com/chat/completions"
AI_MODEL   = "gpt-4o-mini"

SYSTEM_PROMPT = f"""You are the Automation Engineer Bot for Sean Manicad,
an automation engineer at Manulife. You are helpful, concise, and professional.

You can execute these skills by appending a [SKILL] JSON tag at the END of your reply:

1. PowerPoint — when user wants to create a presentation/deck/ppt:
   [SKILL]{{"skill":"ppt","title":"...","topic":"...","author":"Sean Manicad","outline":[{{"title":"...","content":["bullet 1","bullet 2","bullet 3"]}}]}}
   - Always generate a 6-slide outline relevant to the topic with REAL meaningful bullets
   - If a [Confluence Context] block is present in the message, USE IT to make the bullets specific,
     accurate, and grounded in actual project details (bot names, process steps, systems, etc.)
   - Confirm the outline in plain text first, then include the [SKILL] tag to generate it
   - Save path: C:\\Users\\manisea\\OneDrive - Manulife\\Documents\\COPILOT_TEST\\PPT Creation\\

2. Jira Move — when user wants to move/transition a ticket:
   By ticket key:  [SKILL]{{"skill":"jira_move","ticket":"CTFSLBEB-XXX","status":"Done"}}
   By keyword:     [SKILL]{{"skill":"jira_move","keyword":"booklets agreement","status":"Done"}}
   - NEVER ask for the ticket number. Always extract keywords from the description and use keyword search.
   - Strip filler words ("my", "the", "ticket", "story", "task") — use the meaningful noun phrase as keyword.
   - Example: "move my booklets agreement ticket to done" → keyword: "booklets agreement", status: "Done"
   - Example: "transition the food file ticket to Dev In Progress" → keyword: "food file", status: "Dev - In Progress"
   - Valid statuses: Done, Dev - In Progress, Backlog, Code Review, QA Testing, Blocked, Ready for QA
   - Projects: CTFSLBEB (main), CTFSLACE (SFS)

3. Jira Find — when user wants to find/search for a ticket:
   [SKILL]{{"skill":"jira_find","keyword":"..."}}

4. Jira List — when user wants to list their own tickets:
   [SKILL]{{"skill":"jira_list"}}

5. Gliffy diagram — when user wants a swimlane diagram/flowchart:
   [SKILL]{{"skill":"gliffy","name":"...","inserter":"...","lanes":[{{"name":"...","steps":["step 1","step 2"]}}]}}
   - Gather the process name, inserter system, lane names, and steps from the user
   - Each lane = one downstream system (DSS, BizTalk, CAPSIL, PolicyCenter, etc.)

6. Jira User Tickets — when user asks about someone else's tickets, stories, or tasks:
   [SKILL]{{"skill":"jira_user_tickets","user":"Full Name","status":"Dev - In Progress"}}
   - Extract the person's full name from the user's message
   - "status" is optional — only include it if the user filtered by a specific status
   - Example phrases: "show joshua ilunio's tickets", "what is shara faelga working on", "fetch X's stories"

7. Sprint Story Points — when user asks about story points remaining/left in the sprint:
   [SKILL]{{"skill":"jira_sprint_points","project":"CTFSLBEB","user":"Full Name"}}
   - "user" is optional — only include it if the user asked about a specific person
   - Default project is CTFSLBEB unless the user specifies otherwise
   - Example phrases: "how many story points are left", "sprint points remaining", "sprint progress for joshua"

RULES:
- For jira_move: ALWAYS fire the skill immediately using keyword if no ticket key — never ask for the ticket number.
- Only hold back [SKILL] if you truly cannot extract even a keyword (e.g. user said only "move it to done" with no context).
- For PPT: include the full outline in the [SKILL] JSON — don't ask again after confirming.
- Respond conversationally for general questions without any [SKILL] tag.
- Keep responses brief and friendly.
"""


def get_github_token() -> str:
    """Get GitHub token via gh CLI."""
    try:
        result = subprocess.run(["gh", "auth", "token"],
                                capture_output=True, text=True, timeout=5)
        token = result.stdout.strip()
        if token:
            return token
    except Exception:
        pass
    return os.environ.get("GITHUB_TOKEN", "")


def ai_chat(history: list[dict]) -> str:
    """Call GitHub Models API and return the assistant's reply."""
    token = get_github_token()
    if not token:
        return "Error: No GitHub token found. Run `gh auth login` in your terminal."

    payload = json.dumps({
        "model":    AI_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history,
        "max_tokens": 1200,
        "temperature": 0.4,
    }).encode()

    req = urllib.request.Request(
        MODELS_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return f"AI error ({e.code}): {body[:200]}"
    except Exception as e:
        return f"AI error: {e}"


# ── Skill executor ────────────────────────────────────────────────────────────
def execute_skill(skill_json: dict, on_message, set_status=None) -> None:
    """Run the appropriate skill script based on parsed [SKILL] JSON."""
    _status = set_status or (lambda t: None)
    skill = skill_json.get("skill", "")

    if skill == "ppt":
        config = {
            "title":    skill_json.get("title", "Presentation"),
            "subtitle": f"Overview: {skill_json.get('topic', '')}",
            "author":   skill_json.get("author", ""),
            "slides":   skill_json.get("outline", []),
        }
        _status("⏳ Building PowerPoint...")
        on_message("⏳ Building your PowerPoint — this may take a moment...", "pending")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False, encoding="utf-8") as f:
            json.dump(config, f)
            tmp = f.name
        ok, stdout, stderr = run_script([PPT_SCRIPT, "--slides-json", tmp])
        Path(tmp).unlink(missing_ok=True)
        if ok:
            try:
                d = json.loads(stdout)
                on_message(f"✅ Done! Saved: {d['output']}\n({d['total_slides']} slides)", "ok")
            except Exception:
                on_message(f"✅ Done! {stdout}", "ok")
        else:
            on_message(f"❌ PPT error: {stderr or stdout}", "err")

    elif skill == "jira_move":
        ticket  = skill_json.get("ticket", "")
        keyword = skill_json.get("keyword", "")
        status  = skill_json.get("status", "")
        token   = os.environ.get("JIRA_API_TOKEN", "")

        if ticket:
            _status(f"⏳ Moving {ticket}...")
            on_message(f"⏳ Moving {ticket} to \"{status}\"...", "pending")
            cmd = [JIRA_SCRIPT, "--domain", JIRA_DOMAIN, "--email", JIRA_EMAIL,
                   "--token", token, "--ticket", ticket, "--status", status]
        elif keyword:
            _status(f"⏳ Searching for \"{keyword}\"...")
            on_message(f"⏳ Searching for \"{keyword}\" and moving to \"{status}\"...", "pending")
            cmd = [JIRA_SCRIPT, "--domain", JIRA_DOMAIN, "--email", JIRA_EMAIL,
                   "--token", token, "--search", keyword, "--project", JIRA_PROJECT,
                   "--status", status]
        else:
            on_message("❌ No ticket key or keyword provided.", "err")
            return

        ok, stdout, stderr = run_script(cmd)
        if ok:
            try:
                d = json.loads(stdout)
                on_message(f"✅ Done! {d['ticket']}: \"{d['previous_status']}\" → \"{d['new_status']}\"", "ok")
            except Exception:
                on_message(f"✅ Done! {stdout or stderr}", "ok")
        else:
            if "Multiple tickets found" in stderr:
                on_message(
                    f"Found multiple matches — which one did you mean?\n{stderr.strip()}\n\n"
                    f"Reply with the ticket key (e.g. CTFSLBEB-123) to move it to \"{status}\".",
                    "info"
                )
            elif "No tickets found" in stderr:
                on_message(f"❌ No tickets found matching \"{keyword}\". Try a different keyword.", "err")
            else:
                on_message(f"❌ Jira error: {stderr or stdout}", "err")

    elif skill == "jira_find":
        keyword = skill_json.get("keyword", "")
        _status(f"⏳ Searching Jira...")
        on_message(f"⏳ Searching for \"{keyword}\"...", "pending")
        issues  = jira_search(keyword)
        if not issues:
            on_message("✅ No tickets found.", "muted")
        else:
            lines = "\n".join(
                f"  [{x['key']}] {x['fields']['summary']}\n"
                f"         Status: {x['fields']['status']['name']}"
                for x in issues
            )
            on_message(f"✅ Results:\n{lines}", "info")

    elif skill == "jira_list":
        _status("⏳ Fetching your tickets...")
        on_message("⏳ Fetching your tickets...", "pending")
        issues = jira_list_mine()
        if not issues:
            on_message("✅ No tickets found.", "muted")
        else:
            lines = "\n".join(
                f"  [{x['key']}] {x['fields']['summary']}\n"
                f"         Status: {x['fields']['status']['name']}"
                for x in issues
            )
            on_message(f"✅ Your tickets:\n{lines}", "info")

    elif skill == "gliffy":
        config = {
            "system_name":      skill_json.get("name", "Process"),
            "inserter_source":  skill_json.get("inserter", "System"),
            "subprocess_lanes": skill_json.get("lanes", []),
        }
        _status("⏳ Generating diagram...")
        on_message("⏳ Generating Gliffy diagram...", "pending")
        ok, stdout, stderr = run_script([
            DIAG_SCRIPT,
            "--diagram-name", skill_json.get("name", "diagram").replace(" ", "_"),
            "--config-json",  json.dumps(config),
        ])
        if ok:
            on_message(f"✅ Diagram saved!\n{stdout or 'Check your Downloads folder.'}", "ok")
        else:
            on_message(f"❌ Gliffy error: {stderr or stdout}", "err")

    elif skill == "jira_user_tickets":
        user = skill_json.get("user", "")
        status = skill_json.get("status")
        _status(f"⏳ Fetching tickets for {user}...")
        on_message(f"⏳ Fetching tickets for {user}...", "pending")
        cmd = [QUERY_SCRIPT, "--user", user, "--project", JIRA_PROJECT]
        if status:
            cmd += ["--status", status]
        ok, stdout, stderr = run_script(cmd)
        if ok:
            try:
                data = json.loads(stdout)
                by_status = data.get("by_status", {})
                total = data.get("total", 0)
                lines = [f"✅ Tickets for {data.get('assignee', user)} (total: {total})"]
                if data.get("status_filter"):
                    lines[0] += f" — filtered by: {data['status_filter']}"
                for st, issues in by_status.items():
                    lines.append(f"\n  [{st}]")
                    for i in issues:
                        lines.append(f"    [{i['key']}] {i['summary']}")
                on_message("\n".join(lines), "info")
            except Exception:
                on_message(stdout or stderr, "info")
        else:
            on_message(f"❌ Error fetching tickets: {stderr or stdout}", "err")

    elif skill == "jira_sprint_points":
        project = skill_json.get("project", JIRA_PROJECT)
        user = skill_json.get("user")
        label = f"for {user}" if user else "for the full team"
        _status(f"⏳ Checking sprint points...")
        on_message(f"⏳ Checking sprint story points {label}...", "pending")
        cmd = [QUERY_SCRIPT, "--sprint-points", "--project", project]
        if user:
            cmd += ["--user", user]
        ok, stdout, stderr = run_script(cmd)
        if ok:
            try:
                data = json.loads(stdout)
                sprint = data.get("sprint", "Current Sprint")
                total = data.get("total_story_points", 0)
                done = data.get("completed_story_points", 0)
                remaining = data.get("remaining_story_points", 0)
                filtered_by = data.get("filtered_by", "all team members")
                lines = [
                    f"✅ Sprint: {sprint}",
                    f"   Filtered by: {filtered_by}",
                    f"",
                    f"   Total points:    {total}",
                    f"   Completed:       {done}",
                    f"   ⚡ Remaining:    {remaining}",
                ]
                on_message("\n".join(lines), "info")
            except Exception:
                on_message(stdout or stderr, "info")
        else:
            on_message(f"❌ Error fetching sprint points: {stderr or stdout}", "err")

    else:
        on_message(f"❌ Unknown skill: {skill}", "err")


HELP_TEXT = """\
Available commands — just type naturally:

  📊 PowerPoint
      "create a ppt about RPA"
      "make a deck for the MLM project"

  🎫 Jira — Move ticket
      "move CTFSLBEB-123 to Done"
      "transition my accessibility ticket to Dev In Progress"

  🔍 Jira — Find ticket
      "find ticket database table"
      "search for ticket booklets upload"

  📋 Jira — My tickets
      "list my tickets"
      "show all my issues"

  👤 Jira — Someone else's tickets
      "show Joshua Ilunio's tickets"
      "what is Shara Faelga working on"
      "fetch tickets for Joshua Ilunio in Dev In Progress"

  ⚡ Sprint story points
      "how many story points are left this sprint"
      "sprint points remaining"
      "sprint progress for Joshua Ilunio"

  📐 Gliffy diagram
      "create a diagram for advisor termination"
      "make a flowchart of the MLM process"

  ❓ help    — show this message
  🚪 quit    — exit the bot\
"""


def _extract_ppt_topic(text: str) -> str:
    """Extract the presentation topic from a natural language PPT request."""
    t = text.strip()
    # "create a ppt about X" / "make a deck for X" / "presentation on X"
    m = re.search(r'\b(?:about|on|for)\s+(.+?)(?:\s*$|\s*\bwith\b|\s*\busing\b)', t, re.I)
    if m:
        return m.group(1).strip()
    # "make a X ppt" / "build a X deck"
    m = re.search(r'\b(?:make|create|build|generate)\s+(?:a\s+)?(.+?)\s+(?:ppt|deck|presentation|slides?)\b', t, re.I)
    if m:
        return m.group(1).strip()
    return ""


class AIBotEngine:
    """
    AI-powered engine. Each user message is sent to GitHub Models API.
    The AI can trigger skills by appending [SKILL]{...} to its response.
    """
    def __init__(self, on_message, set_status=None):
        self._say        = on_message
        self._set_status = set_status or (lambda t: None)
        self.history     = []

    def say(self, text: str, style: str = "default") -> None:
        self._say(text, style)

    def process(self, user_text: str) -> None:
        t = user_text.strip().lower()

        # Handle built-in commands locally — no AI call needed
        if re.match(r'^help$|^what can you (do|help with)\??$|^commands?\??$', t):
            self.say(HELP_TEXT, "info")
            return
        if re.match(r'^(quit|exit|bye)$', t):
            self.say("Goodbye! 👋", "muted")
            return

        self.history.append({"role": "user", "content": user_text})

        # Phase 1: if PPT-related, enrich with Confluence context before asking AI
        enriched = user_text
        if detect_intent(user_text) == "ppt":
            topic = _extract_ppt_topic(user_text)
            if topic:
                self._set_status(f"⏳ Searching Confluence for \"{topic}\"...")
                ctx = confluence_fetch_context(topic)
                if ctx:
                    enriched = (
                        f"{user_text}\n\n"
                        f"[Confluence Context — from space CDTPACS, use this to make slides "
                        f"specific and accurate]\n{ctx}"
                    )
        self.history[-1]["content"] = enriched

        # Phase 2: ask the AI
        self._set_status("⏳ Thinking...")
        raw = ai_chat(self.history)

        # Split display text from [SKILL] tag
        skill_match = re.search(r'\[SKILL\]\s*(\{.*\})\s*$', raw, re.DOTALL)
        if skill_match:
            display = raw[:skill_match.start()].strip()
            skill_json_str = skill_match.group(1).strip()
        else:
            display = raw.strip()
            skill_json_str = None

        # Show AI's text response
        if display:
            self.say(display)

        # Store assistant turn (without the [SKILL] tag)
        self.history.append({"role": "assistant", "content": display or raw})

        # Execute skill if present
        if skill_json_str:
            try:
                skill_data = json.loads(skill_json_str)
                execute_skill(skill_data, self._say, self._set_status)
            except json.JSONDecodeError as e:
                self.say(f"Skill parse error: {e}\nRaw: {skill_json_str[:100]}", "err")
        
        self._set_status("")

        # Keep history to last 20 turns to avoid token limits
        if len(self.history) > 20:
            self.history = self.history[-20:]


# ── Chat Window ───────────────────────────────────────────────────────────────
class ChatUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root   = root
        self.root.title("Automation Engineer Bot")
        self.root.geometry("780x580")
        self.root.configure(bg=C["hdr"])
        self.root.resizable(True, True)
        self.root.minsize(520, 420)
        self.engine = AIBotEngine(self._on_bot_msg, self._set_status)
        self._build()
        self._welcome()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self) -> None:
        # Header
        hdr = tk.Frame(self.root, bg=C["hdr"], height=54)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  Automation Engineer Bot",
                 bg=C["hdr"], fg=C["hdr_fg"],
                 font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, pady=14)
        tk.Label(hdr, text="v0.1.5  ",
                 bg=C["hdr"], fg=C["hdr_sub"],
                 font=("Segoe UI", 9)).pack(side=tk.RIGHT, pady=14)

        # ── Input row — PACK FIRST so it stays at the bottom ─────────────────
        # (In tkinter, side=BOTTOM widgets must be packed before expand=True widgets)
        tk.Frame(self.root, bg=C["sep"], height=1).pack(fill=tk.X, side=tk.BOTTOM)

        inp = tk.Frame(self.root, bg="#EBF0F5", pady=8)
        inp.pack(fill=tk.X, side=tk.BOTTOM)

        self.var   = tk.StringVar()
        self.field = tk.Entry(
            inp, textvariable=self.var,
            font=("Segoe UI", 11), relief="flat", bd=0,
            bg=C["input_bg"], fg="#222", insertbackground="#333",
            highlightthickness=1, highlightbackground=C["input_bd"],
            highlightcolor=C["btn"],
        )
        self.field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(14, 8), ipady=8)
        self.field.bind("<Return>", self._send)

        self.send_btn = tk.Button(
            inp, text="Send", command=self._send,
            bg=C["btn"], fg=C["btn_fg"], activebackground=C["hdr"],
            activeforeground=C["btn_fg"],
            font=("Segoe UI", 10, "bold"), relief="flat",
            padx=20, pady=6, cursor="hand2", bd=0,
        )
        self.send_btn.pack(side=tk.RIGHT, padx=(0, 14))

        # Status indicator — shows "Bot is thinking..." while processing
        self.status_var = tk.StringVar(value="")
        tk.Label(inp, textvariable=self.status_var,
                 bg="#EBF0F5", fg=C["info"],
                 font=("Segoe UI", 8, "italic")).pack(side=tk.RIGHT, padx=(0, 6))

        # ── Chat area — packed AFTER inp so it fills remaining space ──────────
        chat_frame = tk.Frame(self.root, bg=C["bg"])
        chat_frame.pack(fill=tk.BOTH, expand=True)

        self.chat = tk.Text(
            chat_frame, state="disabled", wrap=tk.WORD, cursor="arrow",
            bg=C["bg"], relief="flat", padx=18, pady=14,
            font=("Segoe UI", 10), spacing1=2, spacing3=6,
        )
        sb = tk.Scrollbar(chat_frame, command=self.chat.yview,
                          troughcolor=C["bg"], bg=C["sep"])
        self.chat.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Text tags
        self.chat.tag_configure("bot_lbl",  foreground=C["bot_lbl"],
                                            font=("Segoe UI", 9, "bold"))
        self.chat.tag_configure("usr_lbl",  foreground=C["usr_lbl"],
                                            font=("Segoe UI", 9, "bold"))
        self.chat.tag_configure("default",  foreground="#222222",
                                            font=("Segoe UI", 10))
        self.chat.tag_configure("ok",       foreground=C["ok"],
                                            font=("Segoe UI", 10))
        self.chat.tag_configure("err",      foreground=C["err"],
                                            font=("Segoe UI", 10, "bold"))
        self.chat.tag_configure("info",     foreground=C["info"],
                                            font=("Segoe UI", 10))
        self.chat.tag_configure("muted",    foreground=C["muted"],
                                            font=("Segoe UI", 10, "italic"))
        self.chat.tag_configure("pending",  foreground=C["muted"],
                                            font=("Segoe UI", 10, "italic"))

        self.field.focus_set()

    # ── Message rendering ─────────────────────────────────────────────────────
    def _add_bot(self, msg: str, style: str = "default") -> None:
        self.chat.config(state="normal")
        self.chat.insert(tk.END, "Bot\n", "bot_lbl")
        self.chat.insert(tk.END, msg + "\n\n", style)
        self.chat.config(state="disabled")
        self.chat.see(tk.END)

    def _add_user(self, msg: str) -> None:
        self.chat.config(state="normal")
        self.chat.insert(tk.END, "You\n", "usr_lbl")
        self.chat.insert(tk.END, msg + "\n\n", "default")
        self.chat.config(state="disabled")
        self.chat.see(tk.END)

    def _on_bot_msg(self, text: str, style: str = "default") -> None:
        self.root.after(0, lambda: self._add_bot(text, style))

    def _set_status(self, text: str) -> None:
        self.root.after(0, lambda: self.status_var.set(text))

    # ── Interaction ───────────────────────────────────────────────────────────
    def _send(self, event=None) -> None:
        text = self.var.get().strip()
        if not text:
            return
        self.var.set("")
        self._add_user(text)
        self.status_var.set("⏳ Thinking...")
        self.send_btn.config(state="disabled")
        threading.Thread(target=self._dispatch, args=(text,), daemon=True).start()

    def _dispatch(self, text: str) -> None:
        try:
            self.engine.process(text)
        except Exception as e:
            self.root.after(0, lambda: self._add_bot(f"Unexpected error: {e}", "err"))
        finally:
            self.root.after(0, self._done_processing)

    def _done_processing(self) -> None:
        self.status_var.set("")
        self.send_btn.config(state="normal")
        self.field.focus_force()

    def _re_enable_field(self) -> None:
        self.field.config(state="normal")
        self.field.focus_force()

    def _welcome(self) -> None:
        self._add_bot(
            "Hi Sean! What would you like to do today?\n"
            "Type 'help' to see all available commands.\n"
            "New: ask about team members' tickets or sprint story points!",
            "info"
        )
        self.root.after(150, lambda: self.field.focus_force())

def main() -> None:
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    ChatUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
