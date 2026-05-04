# LeetCode Problem Recommender Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AI-powered LeetCode problem recommender that picks 3 problems per invocation based on feedback, targeting Mag 7 interview prep.

**Architecture:** Same patterns as `/Users/jackie/personal/article-recommender/` — Google Sheets as DB, Claude CLI for AI selection, Telegram for delivery. New addition: LeetCode GraphQL API client for fetching problem catalog and solved history.

**Tech Stack:** Python 3, gspread, google-auth, requests, python-dotenv, Claude CLI (Pro plan)

**Spec:** `docs/superpowers/specs/2026-05-04-leetcode-recommender-design.md`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `leetcode-recommender/.gitignore`
- Create: `leetcode-recommender/.env.example`
- Create: `leetcode-recommender/requirements.txt`
- Create: `leetcode-recommender/config.py`

- [ ] **Step 1: Create project directory and .gitignore**

```bash
mkdir -p /Users/jackie/personal/leetcode-recommender
```

Write `leetcode-recommender/.gitignore`:
```
.env
__pycache__/
*.pyc
.venv/
service-account.json
cron.log
```

- [ ] **Step 2: Create .env.example**

Write `leetcode-recommender/.env.example`:
```
GOOGLE_SHEET_ID=your-google-sheet-id
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=your-chat-id
LEETCODE_SESSION=your-session-cookie
```

- [ ] **Step 3: Create requirements.txt**

Write `leetcode-recommender/requirements.txt`:
```
gspread==6.1.4
google-auth==2.38.0
requests==2.32.3
python-dotenv==1.0.1
```

Same pinned versions as article-recommender.

- [ ] **Step 4: Create config.py**

Write `leetcode-recommender/config.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()

# Google credentials
GOOGLE_CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "service-account.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LEETCODE_SESSION = os.getenv("LEETCODE_SESSION", "")

# User profile — used by Claude to select problems
USER_PROFILE = """
Software Engineer II with ~2 years experience at a Taiwan startup (foundi).
Background: EE degree (National Sun Yat-sen University), bootcamp (AppWorks School), full-stack with Angular/Node.js/React.
700+ LeetCode problems already solved.

Goal: Prepare for Fall 2026 tech internship interviews at Mag 7 / FAANG companies.

Focus areas for LeetCode practice:
- Dynamic Programming (state transitions, optimization, interval DP, bitmask DP)
- Graphs (BFS/DFS, shortest path, topological sort, union-find)
- Trees (binary trees, BST, segment trees, tries)
- Sliding Window / Two Pointers
- Stack / Monotonic Stack
- Binary Search (on answer, rotated arrays)
- Greedy algorithms
- Backtracking
- Heap / Priority Queue
- Bit Manipulation

Selection guidance:
- Only Medium and Hard problems (Easy is not interview-relevant at this level)
- Prioritize topics I'm weakest in based on my feedback history
- Provide topic diversity — 3 different topics per batch when possible
- Favor problems that test patterns commonly seen in Mag 7 interviews
"""
```

- [ ] **Step 5: Commit**

```bash
cd /Users/jackie/personal
git add leetcode-recommender/.gitignore leetcode-recommender/.env.example leetcode-recommender/requirements.txt leetcode-recommender/config.py
git commit -m "feat(leetcode-recommender): project scaffolding with config"
```

---

### Task 2: Google Sheets Layer

**Files:**
- Create: `leetcode-recommender/sheets.py`
- Reference: `article-recommender/sheets.py` for patterns

- [ ] **Step 1: Create sheets.py**

Write `leetcode-recommender/sheets.py`:
```python
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_ID

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Sheet tab names
PROBLEMS_TAB = "Problems"
SOLVED_TAB = "Solved"
SENT_TAB = "Sent"
USAGE_TAB = "LC Usage"

# Headers for each tab
PROBLEMS_HEADERS = ["ID", "Title", "Slug", "Difficulty", "Tags", "Acceptance Rate"]
SOLVED_HEADERS = ["ID", "Title", "Solved Date"]
SENT_HEADERS = ["Date", "ID", "Title", "Difficulty", "Tags", "URL", "Difficulty Rating", "Notes"]
USAGE_HEADERS = ["Date", "Input Tokens", "Output Tokens", "Cost USD", "Duration (s)"]

_cached_spreadsheet: gspread.Spreadsheet | None = None


def _safe_cell(value: str) -> str:
    """Prefix formula-triggering characters to prevent Google Sheets formula injection."""
    if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def _get_spreadsheet() -> gspread.Spreadsheet:
    global _cached_spreadsheet
    if _cached_spreadsheet is None:
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
        client = gspread.authorize(creds)
        _cached_spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    return _cached_spreadsheet


def _ensure_tab(spreadsheet: gspread.Spreadsheet, tab_name: str, headers: list[str]) -> gspread.Worksheet:
    """Get or create a worksheet tab with headers."""
    try:
        ws = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
        ws.append_row(headers)
    return ws


def init_sheets():
    """Initialize all tabs."""
    spreadsheet = _get_spreadsheet()
    _ensure_tab(spreadsheet, PROBLEMS_TAB, PROBLEMS_HEADERS)
    _ensure_tab(spreadsheet, SOLVED_TAB, SOLVED_HEADERS)
    _ensure_tab(spreadsheet, SENT_TAB, SENT_HEADERS)
    _ensure_tab(spreadsheet, USAGE_TAB, USAGE_HEADERS)


def read_problems() -> list[dict]:
    """Read all problems from the Problems tab."""
    spreadsheet = _get_spreadsheet()
    ws = _ensure_tab(spreadsheet, PROBLEMS_TAB, PROBLEMS_HEADERS)
    rows = ws.get_all_values()
    if len(rows) <= 1:
        return []
    problems = []
    for row in rows[1:]:
        if len(row) < 3 or not row[0].strip():
            continue
        problems.append({
            "id": row[0],
            "title": row[1],
            "slug": row[2],
            "difficulty": row[3] if len(row) > 3 else "",
            "tags": row[4] if len(row) > 4 else "",
            "acceptance_rate": row[5] if len(row) > 5 else "",
        })
    return problems


def read_solved() -> set[str]:
    """Read solved problem IDs from the Solved tab. Returns a set of ID strings."""
    spreadsheet = _get_spreadsheet()
    ws = _ensure_tab(spreadsheet, SOLVED_TAB, SOLVED_HEADERS)
    rows = ws.get_all_values()
    if len(rows) <= 1:
        return set()
    return {row[0].strip() for row in rows[1:] if row[0].strip()}


def read_sent() -> list[dict]:
    """Read sent problems with feedback from the Sent tab."""
    spreadsheet = _get_spreadsheet()
    ws = _ensure_tab(spreadsheet, SENT_TAB, SENT_HEADERS)
    rows = ws.get_all_values()
    if len(rows) <= 1:
        return []
    sent = []
    for row in rows[1:]:
        if len(row) < 2 or not row[1].strip():
            continue
        sent.append({
            "date": row[0],
            "id": row[1],
            "title": row[2] if len(row) > 2 else "",
            "difficulty": row[3] if len(row) > 3 else "",
            "tags": row[4] if len(row) > 4 else "",
            "url": row[5] if len(row) > 5 else "",
            "difficulty_rating": row[6].strip() if len(row) > 6 else "",
            "notes": row[7].strip() if len(row) > 7 else "",
        })
    return sent


def read_feedback() -> list[dict]:
    """Read feedback entries (only rows with a difficulty rating) from the Sent tab."""
    sent = read_sent()
    return [s for s in sent if s.get("difficulty_rating")]


def write_problems(problems: list[dict]):
    """Write problems to the Problems tab (clears existing data first)."""
    spreadsheet = _get_spreadsheet()
    ws = _ensure_tab(spreadsheet, PROBLEMS_TAB, PROBLEMS_HEADERS)
    # Clear all rows below header
    ws.resize(rows=1)
    ws.resize(rows=1000)
    rows = []
    for p in problems:
        tags = p.get("tags", "")
        if isinstance(tags, list):
            tags = ", ".join(tags)
        rows.append([
            str(p.get("id", "")),
            _safe_cell(str(p.get("title", ""))),
            str(p.get("slug", "")),
            str(p.get("difficulty", "")),
            _safe_cell(tags),
            str(p.get("acceptance_rate", "")),
        ])
    if rows:
        ws.append_rows(rows)


def write_solved(solved: list[dict]):
    """Write solved problems to the Solved tab (clears existing data first)."""
    spreadsheet = _get_spreadsheet()
    ws = _ensure_tab(spreadsheet, SOLVED_TAB, SOLVED_HEADERS)
    ws.resize(rows=1)
    ws.resize(rows=1000)
    rows = []
    for s in solved:
        rows.append([
            str(s.get("id", "")),
            _safe_cell(str(s.get("title", ""))),
            str(s.get("solved_date", "")),
        ])
    if rows:
        ws.append_rows(rows)


def write_sent(problems: list[dict]):
    """Append recommended problems to the Sent tab."""
    spreadsheet = _get_spreadsheet()
    ws = _ensure_tab(spreadsheet, SENT_TAB, SENT_HEADERS)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = []
    for p in problems:
        tags = p.get("tags", "")
        if isinstance(tags, list):
            tags = ", ".join(tags)
        rows.append([
            today,
            str(p.get("id", "")),
            _safe_cell(str(p.get("title", ""))),
            str(p.get("difficulty", "")),
            _safe_cell(tags),
            p.get("url", ""),
        ])
    if rows:
        ws.append_rows(rows)


def write_usage(usage: dict):
    """Append a row to the Usage tab with today's token usage."""
    spreadsheet = _get_spreadsheet()
    ws = _ensure_tab(spreadsheet, USAGE_TAB, USAGE_HEADERS)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_input = (
        usage.get("input_tokens", 0)
        + usage.get("cache_read_tokens", 0)
        + usage.get("cache_creation_tokens", 0)
    )
    ws.append_row([
        today,
        str(total_input),
        str(usage.get("output_tokens", 0)),
        str(round(usage.get("cost_usd", 0), 6)),
        str(usage.get("duration_secs", 0)),
    ])
```

- [ ] **Step 2: Verify sheets.py imports cleanly**

```bash
cd /Users/jackie/personal/leetcode-recommender
python3 -c "import sheets; print('sheets.py imports OK')"
```

Expected: `sheets.py imports OK` (will fail if .env is not set up yet — that's fine, just verify no syntax errors)

- [ ] **Step 3: Commit**

```bash
cd /Users/jackie/personal
git add leetcode-recommender/sheets.py
git commit -m "feat(leetcode-recommender): google sheets layer"
```

---

### Task 3: LeetCode API Client

**Files:**
- Create: `leetcode-recommender/leetcode.py`

- [ ] **Step 1: Create leetcode.py**

Write `leetcode-recommender/leetcode.py`:
```python
import time

import requests

GRAPHQL_URL = "https://leetcode.com/graphql/"
USER_AGENT = "LeetCodeRecommender/1.0"

CATALOG_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(categorySlug: $categorySlug, limit: $limit, skip: $skip, filters: $filters) {
    total: totalNum
    questions: data {
      acRate
      difficulty
      frontendQuestionId: questionFrontendId
      title
      titleSlug
      topicTags { name slug }
      isPaidOnly
    }
  }
}
"""

SUBMISSIONS_QUERY = """
query recentAcSubmissionList($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    id
    title
    titleSlug
    timestamp
  }
}
"""

# For authenticated full history, we use the submissions API
SUBMISSION_LIST_QUERY = """
query submissionList($offset: Int!, $limit: Int!, $questionSlug: String, $status: SubmissionStatusEnum) {
  submissionList(offset: $offset, limit: $limit, questionSlug: $questionSlug, status: $status) {
    lastKey
    hasNext
    submissions {
      id
      title
      titleSlug
      timestamp
      statusDisplay
    }
  }
}
"""


def fetch_problem_catalog() -> list[dict]:
    """Fetch all Medium/Hard free problems from LeetCode.

    Returns list of dicts with keys: id, title, slug, difficulty, tags, acceptance_rate
    """
    all_problems = []
    page_size = 100
    skip = 0

    # First request to get total count
    resp = _graphql_request(CATALOG_QUERY, {
        "categorySlug": "",
        "limit": page_size,
        "skip": 0,
        "filters": {},
    })
    data = resp["data"]["problemsetQuestionList"]
    total = data["total"]
    all_problems.extend(_parse_problems(data["questions"]))

    # Paginate through remaining
    skip = page_size
    while skip < total:
        time.sleep(1)  # Rate limiting
        resp = _graphql_request(CATALOG_QUERY, {
            "categorySlug": "",
            "limit": page_size,
            "skip": skip,
            "filters": {},
        })
        data = resp["data"]["problemsetQuestionList"]
        all_problems.extend(_parse_problems(data["questions"]))
        skip += page_size
        print(f"       Fetched {min(skip, total)}/{total} problems...")

    return all_problems


def fetch_solved_history(session_cookie: str) -> list[dict]:
    """Fetch all accepted submissions using authenticated session.

    Returns list of dicts with keys: id, title, solved_date
    """
    headers = {
        "Cookie": f"LEETCODE_SESSION={session_cookie}",
        "Referer": "https://leetcode.com",
        "User-Agent": USER_AGENT,
    }

    all_solved = {}  # dedupe by titleSlug
    offset = 0
    page_size = 20

    while True:
        resp = requests.post(
            GRAPHQL_URL,
            json={
                "query": SUBMISSION_LIST_QUERY,
                "variables": {
                    "offset": offset,
                    "limit": page_size,
                    "status": "AC",
                },
            },
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]["submissionList"]
        submissions = data["submissions"]

        if not submissions:
            break

        for s in submissions:
            slug = s.get("titleSlug", "")
            if slug and slug not in all_solved:
                from datetime import datetime, timezone
                ts = int(s.get("timestamp", 0))
                date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") if ts else ""
                all_solved[slug] = {
                    "id": s.get("id", ""),
                    "title": s.get("title", ""),
                    "slug": slug,
                    "solved_date": date_str,
                }

        if not data.get("hasNext"):
            break

        offset += page_size
        time.sleep(1)  # Rate limiting
        print(f"       Fetched {len(all_solved)} unique solved problems...")

    return list(all_solved.values())


def get_problem_url(slug: str) -> str:
    """Return the LeetCode problem URL for a given slug."""
    return f"https://leetcode.com/problems/{slug}/"


def _graphql_request(query: str, variables: dict) -> dict:
    """Make a GraphQL request to LeetCode."""
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_problems(questions: list[dict]) -> list[dict]:
    """Parse raw GraphQL question data into our format. Filters to Medium/Hard, free only."""
    problems = []
    for q in questions:
        if q.get("isPaidOnly"):
            continue
        difficulty = q.get("difficulty", "")
        if difficulty == "Easy":
            continue
        tags = [t["name"] for t in q.get("topicTags", [])]
        problems.append({
            "id": str(q.get("frontendQuestionId", "")),
            "title": q.get("title", ""),
            "slug": q.get("titleSlug", ""),
            "difficulty": difficulty,
            "tags": tags,
            "acceptance_rate": round(q.get("acRate", 0), 1),
        })
    return problems
```

- [ ] **Step 2: Verify leetcode.py imports cleanly**

```bash
cd /Users/jackie/personal/leetcode-recommender
python3 -c "import leetcode; print('leetcode.py imports OK')"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/jackie/personal
git add leetcode-recommender/leetcode.py
git commit -m "feat(leetcode-recommender): leetcode graphql api client"
```

---

### Task 4: Analyzer (Claude Recommender Logic)

**Files:**
- Create: `leetcode-recommender/analyzer.py`

- [ ] **Step 1: Create analyzer.py**

Write `leetcode-recommender/analyzer.py`:
```python
import json
import os
import random
import subprocess
from datetime import datetime, timedelta, timezone

from config import USER_PROFILE
from leetcode import get_problem_url


def filter_and_sample(problems: list[dict], solved_ids: set[str], sent: list[dict], sample_size: int = 100) -> list[dict]:
    """Filter out solved/recently-sent problems, then uniform-random sample.

    - Removes solved problems (from Solved tab)
    - Removes problems sent in the last 16 months
    - Randomly samples `sample_size` problems (uniform, each problem has equal chance)
    """
    # Build set of recently-sent IDs (last 16 months)
    cutoff = datetime.now(timezone.utc) - timedelta(days=16 * 30)
    recently_sent_ids = set()
    for s in sent:
        try:
            sent_date = datetime.strptime(s["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if sent_date >= cutoff:
                recently_sent_ids.add(s["id"])
        except (ValueError, KeyError):
            recently_sent_ids.add(s.get("id", ""))

    # Filter
    pool = [
        p for p in problems
        if p["id"] not in solved_ids and p["id"] not in recently_sent_ids
    ]

    if not pool:
        return []

    # Uniform random sample
    if len(pool) <= sample_size:
        return pool

    return random.sample(pool, sample_size)


def pick_problems(sampled: list[dict], feedback: list[dict]) -> tuple[list[dict], dict]:
    """Ask Claude to pick 3 problems from the sampled list based on feedback.

    Returns (list of 3 problem dicts with 'reason' field, usage_info).
    """
    prompt = f"""You are a LeetCode problem recommendation engine for a software engineer preparing for Mag 7 interviews.

## User Profile
{USER_PROFILE}
"""
    if feedback:
        prompt += "\n## Recent Feedback (how the user rated previous problems)\n"
        for fb in feedback[-20:]:
            rating = fb.get("difficulty_rating", "")
            title = fb.get("title", "")
            tags = fb.get("tags", "")
            notes = fb.get("notes", "")
            if rating and title:
                prompt += f'- "{title}" ({tags}) — difficulty rating {rating}/5'
                if notes:
                    prompt += f" ({notes})"
                prompt += "\n"

    prompt += "\n## Available Problems (random sample from unsolved pool)\n"
    prompt += "ID | Title | Difficulty | Tags\n"
    prompt += "---|-------|-----------|-----\n"
    for p in sampled:
        tags = p.get("tags", "")
        if isinstance(tags, list):
            tags = ", ".join(tags)
        prompt += f'{p["id"]} | {p["title"]} | {p["difficulty"]} | {tags}\n'

    prompt += """
## Task
Pick exactly 3 problems from the available list above for this user to practice today.

Selection criteria:
1. **Weak areas first** — pick topics where the user rated difficulty high (4-5) or left struggling notes
2. **Difficulty progression** — appropriate mix of Medium/Hard based on topic mastery
3. **Topic diversity** — pick 3 DIFFERENT topics, not 3 problems from the same category
4. **Interview relevance** — prioritize patterns common in Mag 7 interviews
5. **IMPORTANT: Ignore sample distribution** — the input is a random sample from a larger pool. Do NOT pick topics just because they appear more frequently in this sample. Base your topic selection SOLELY on the user's feedback and weak areas. If there is no feedback yet, pick 3 diverse topics that are most commonly tested in FAANG interviews.

Return ONLY a valid JSON array of exactly 3 objects:
[{"id": "123", "title": "Problem Name", "slug": "problem-slug", "difficulty": "Medium", "tags": ["Tag1", "Tag2"], "reason": "One sentence explaining why this problem was chosen"}]

No markdown, no explanation. Just the raw JSON array.
"""
    raw_output, usage = _call_claude_cli(prompt)

    try:
        results = _parse_json_response(raw_output)
        if not isinstance(results, list):
            print("[WARN] Claude returned non-array.")
            return [], usage
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[WARN] Failed to parse Claude response: {e}")
        return [], usage

    # Add URLs
    for r in results:
        r["url"] = get_problem_url(r.get("slug", ""))

    return results, usage


def _call_claude_cli(prompt: str) -> tuple[str, dict]:
    """Call claude CLI using the user's Pro plan. Returns (response_text, usage_info)."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    claude_bin = os.environ.get("CLAUDE_BIN", "/opt/homebrew/bin/claude")
    result = subprocess.run(
        [claude_bin, "-p", "--model", "sonnet", "--output-format", "json",
         "--max-turns", "1", "--allowedTools", ""],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    if result.returncode != 0:
        details = result.stderr[:500] or result.stdout[:500]
        raise RuntimeError(f"claude CLI failed (exit {result.returncode}): {details}")

    raw = result.stdout.strip()
    try:
        data = json.loads(raw)
        response_text = data.get("result", "")
        usage = {
            "input_tokens": data.get("usage", {}).get("input_tokens", 0),
            "output_tokens": data.get("usage", {}).get("output_tokens", 0),
            "cost_usd": data.get("total_cost_usd", 0),
        }
        return response_text, usage
    except (json.JSONDecodeError, KeyError):
        return raw, {}


def _parse_json_response(text: str) -> list | dict:
    """Parse JSON from Claude's response, handling possible markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)
```

- [ ] **Step 2: Verify analyzer.py imports cleanly**

```bash
cd /Users/jackie/personal/leetcode-recommender
python3 -c "import analyzer; print('analyzer.py imports OK')"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/jackie/personal
git add leetcode-recommender/analyzer.py
git commit -m "feat(leetcode-recommender): claude-powered problem selection"
```

---

### Task 5: Telegram Delivery

**Files:**
- Create: `leetcode-recommender/chat.py`

- [ ] **Step 1: Create chat.py**

Write `leetcode-recommender/chat.py`:
```python
import html

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_problems(problems: list[dict], dry_run: bool = False):
    """Send the recommended problems to Telegram."""
    if not problems:
        _send_message("No problems to recommend today. Claude returned no picks.", dry_run=dry_run)
        return

    text = "<b>LeetCode Problems for Today</b>\n"

    for i, p in enumerate(problems, 1):
        title = html.escape(p.get("title", ""))
        difficulty = html.escape(p.get("difficulty", ""))
        tags = p.get("tags", "")
        if isinstance(tags, list):
            tags = ", ".join(tags)
        tags = html.escape(tags)
        reason = html.escape(p.get("reason", ""))
        url = p.get("url", "")
        safe_url = html.escape(url, quote=True)

        text += f"\n<b>{i}. {title}</b> ({difficulty})\n"
        if tags:
            text += f"Tags: {tags}\n"
        if reason:
            text += f"Why: {reason}\n"
        text += f'<a href="{safe_url}">Solve on LeetCode</a>\n'

    text += "\n<i>Rate in the Sent sheet to improve future picks!</i>"

    _send_message(text, dry_run=dry_run)


def send_error_notification(error: str):
    """Send an error notification to Telegram."""
    safe_error = html.escape(error)
    text = f"<b>LeetCode Recommender Failed</b>\n\nError: {safe_error}\n\nCheck the logs for details."
    _send_message(text)


def _send_message(text: str, dry_run: bool = False):
    """Send a message via Telegram Bot API (HTML parse mode)."""
    if dry_run:
        print("[DRY RUN] Would send Telegram message:")
        print(text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    print("[INFO] Telegram message sent successfully.")
```

- [ ] **Step 2: Commit**

```bash
cd /Users/jackie/personal
git add leetcode-recommender/chat.py
git commit -m "feat(leetcode-recommender): telegram delivery"
```

---

### Task 6: Main Orchestration

**Files:**
- Create: `leetcode-recommender/main.py`

- [ ] **Step 1: Create main.py**

Write `leetcode-recommender/main.py`:
```python
"""
LeetCode Problem Recommender

Recommends 3 LeetCode problems per invocation based on feedback and weak areas.

Usage:
    python main.py                  # Recommend 3 problems
    python main.py --init-catalog   # Fetch problem catalog from LeetCode
    python main.py --init-solved    # Fetch solved history (needs LEETCODE_SESSION)
    python main.py --dry-run        # Run without writing to Sheets or sending Telegram
"""

import os
import sys
import time
import traceback

from analyzer import filter_and_sample, pick_problems
from chat import send_error_notification, send_problems
from config import LEETCODE_SESSION
from leetcode import fetch_problem_catalog, fetch_solved_history
from sheets import (
    init_sheets,
    read_feedback,
    read_problems,
    read_sent,
    read_solved,
    write_problems,
    write_sent,
    write_solved,
    write_usage,
)


def run():
    dry_run = "--dry-run" in sys.argv
    start_time = time.monotonic()

    if dry_run:
        print("[DRY RUN MODE] Will not send Telegram messages or write to Sheets.\n")

    print("[1] Initializing sheets...")
    init_sheets()

    # --init-catalog: fetch problem catalog from LeetCode API
    if "--init-catalog" in sys.argv:
        print("[2] Fetching problem catalog from LeetCode...")
        problems = fetch_problem_catalog()
        print(f"       Fetched {len(problems)} Medium/Hard free problems.")
        write_problems(problems)
        print("[DONE] Problem catalog written to Sheets.")
        return

    # --init-solved: fetch solved history from LeetCode
    if "--init-solved" in sys.argv:
        if not LEETCODE_SESSION:
            print("[ERROR] LEETCODE_SESSION not set in .env")
            sys.exit(1)
        print("[2] Fetching solved history from LeetCode...")
        solved = fetch_solved_history(LEETCODE_SESSION)
        print(f"       Fetched {len(solved)} unique solved problems.")
        write_solved(solved)
        print("[DONE] Solved history written to Sheets.")
        return

    # Normal run: recommend 3 problems
    print("[2] Reading context from Sheets...")
    problems = read_problems()
    solved_ids = read_solved()
    sent = read_sent()
    feedback = read_feedback()

    print(f"       Catalog: {len(problems)} problems, Solved: {len(solved_ids)}, Sent: {len(sent)}, Feedback: {len(feedback)}")

    if not problems:
        print("[ERROR] No problems in catalog. Run --init-catalog first.")
        sys.exit(1)

    print("[3] Filtering and sampling...")
    sampled = filter_and_sample(problems, solved_ids, sent)
    print(f"       Sampled {len(sampled)} problems for Claude.")

    if not sampled:
        print("[DONE] No unsolved problems left to recommend.")
        return

    print("[4] Asking Claude to pick 3 problems...")
    picks, usage = pick_problems(sampled, feedback)

    if not picks:
        print("[DONE] Claude returned no picks.")
        return

    print(f"       Picks:")
    for p in picks:
        print(f"         - [{p['difficulty']}] {p['title']}")

    if usage:
        print(f"       Tokens: {usage.get('input_tokens', 0)} in / {usage.get('output_tokens', 0)} out | Cost: ${usage.get('cost_usd', 0):.4f}")

    if dry_run:
        print("[5] [DRY RUN] Telegram message preview:")
        send_problems(picks, dry_run=True)
    else:
        print("[5] Writing to Sheets & sending Telegram...")
        write_sent(picks)
        if usage:
            usage["duration_secs"] = int(time.monotonic() - start_time)
            write_usage(usage)
        send_problems(picks)

    elapsed = time.monotonic() - start_time
    minutes, seconds = divmod(int(elapsed), 60)
    print(f"[DONE] Sent {len(picks)} problems. ({minutes}m {seconds}s)")


def _sanitize(text: str) -> str:
    """Strip secrets from error output before logging or sending."""
    secrets = [
        os.getenv("TELEGRAM_BOT_TOKEN", ""),
        os.getenv("TELEGRAM_CHAT_ID", ""),
        os.getenv("GOOGLE_SHEET_ID", ""),
        os.getenv("LEETCODE_SESSION", ""),
    ]
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***REDACTED***")
    return text


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        raw_tb = traceback.format_exc()
        safe_tb = _sanitize(raw_tb)
        safe_msg = _sanitize(f"{type(e).__name__}: {e}")
        print(f"[ERROR] {safe_msg}")
        print(safe_tb)
        try:
            send_error_notification(safe_msg)
        except Exception:
            print("[ERROR] Also failed to send error notification to Telegram.")
```

- [ ] **Step 2: Verify main.py imports cleanly**

```bash
cd /Users/jackie/personal/leetcode-recommender
python3 -c "import main; print('main.py imports OK')"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/jackie/personal
git add leetcode-recommender/main.py
git commit -m "feat(leetcode-recommender): main orchestration with CLI flags"
```

---

### Task 7: CLAUDE.md

**Files:**
- Create: `leetcode-recommender/CLAUDE.md`

- [ ] **Step 1: Create CLAUDE.md**

Write `leetcode-recommender/CLAUDE.md`:
```markdown
# LeetCode Problem Recommender

AI-powered LeetCode problem recommender targeting Mag 7 internship interview prep.

## What This Project Does

Recommends 3 LeetCode problems per invocation. Filters out solved/recently-sent problems, randomly samples 100 from the unsolved pool, then Claude picks 3 based on the user's feedback history and weak areas. Delivers via Telegram with direct LeetCode links.

## Architecture

```
Problems catalog (Google Sheets, fetched from LeetCode API)
     |
Filter: remove solved + recently sent
     |
Random sample 100 problems (uniform)
     |
Claude picks 3 (guided by feedback + user profile)
     |
Google Sheets (Sent tab) + Telegram
```

## File Structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point, orchestrates the flow. Flags: `--init-catalog`, `--init-solved`, `--dry-run` |
| `config.py` | Configuration: API keys (from `.env`), `USER_PROFILE` (learning goals) |
| `leetcode.py` | LeetCode GraphQL API client — fetch catalog and solved history |
| `analyzer.py` | Claude CLI integration — filter/sample/pick logic |
| `sheets.py` | Google Sheets CRUD via `gspread` — Problems, Solved, Sent, Usage tabs |
| `chat.py` | Telegram Bot API sender with HTML escaping |

## Google Sheets Layout (1 spreadsheet, 4 tabs)

- **Problems** — cached LeetCode catalog (Medium/Hard only, no Easy)
- **Solved** — one-time import of user's solved history
- **Sent** — recommended problems with inline Difficulty Rating/Notes columns for feedback
- **LC Usage** — token usage tracking per run

## Key Design Decisions

- **Full LeetCode catalog** — not a curated list, since user has 700+ solved (most curated lists would be mostly done)
- **No Easy problems** — filtered out at catalog fetch time, not interview-relevant
- **Uniform random sampling** — 100 problems sampled with equal probability, avoids topic distribution bias
- **Claude prompt warns against sample bias** — explicitly told to ignore topic frequency in the sample
- **16-month sent window** — problems sent more than 16 months ago can be re-recommended
- **One-time solved import** — uses LEETCODE_SESSION cookie once, then stored in Sheets
- **Claude CLI (`claude -p`)** instead of API — uses Pro subscription, no extra cost

## Environment (.env)

```
GOOGLE_SHEET_ID=<sheet-id>
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_CHAT_ID=<chat-id>
LEETCODE_SESSION=<session-cookie>  # only needed for --init-solved
```

Service account JSON at `service-account.json` (same one as article-recommender).

## Running

```bash
# First-time setup
python3 main.py --init-catalog   # Fetch LeetCode catalog (~3000 Medium/Hard problems)
python3 main.py --init-solved    # Import solved history (needs LEETCODE_SESSION in .env)

# Daily use
python3 main.py                  # Recommend 3 problems
python3 main.py --dry-run        # Test without Sheets/Telegram
```

## Security Notes

- Error logs sanitized to redact secrets
- LEETCODE_SESSION only used during --init-solved, not persisted in Sheets
- Formula injection prevention in Sheets cells
- Telegram messages HTML-escaped
- Service account scoped to Sheets API only
```

- [ ] **Step 2: Commit**

```bash
cd /Users/jackie/personal
git add leetcode-recommender/CLAUDE.md
git commit -m "feat(leetcode-recommender): add CLAUDE.md"
```

---

### Task 8: Setup and End-to-End Test

**Files:**
- Modify: `leetcode-recommender/.env` (created by user, copied from .env.example)

- [ ] **Step 1: Copy service account and create .env**

```bash
cd /Users/jackie/personal/leetcode-recommender
cp ../article-recommender/service-account.json .
cp .env.example .env
```

Then edit `.env` with actual values — copy `GOOGLE_SHEET_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` from `article-recommender/.env`. The `GOOGLE_SHEET_ID` can be the same spreadsheet (tabs are separate) or a new one.

- [ ] **Step 2: Set up venv and install dependencies**

```bash
cd /Users/jackie/personal/leetcode-recommender
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

- [ ] **Step 3: Initialize sheets**

```bash
cd /Users/jackie/personal/leetcode-recommender
source .venv/bin/activate
python3 -c "from sheets import init_sheets; init_sheets(); print('Sheets initialized')"
```

Expected: Creates Problems, Solved, Sent, LC Usage tabs in the spreadsheet.

- [ ] **Step 4: Fetch problem catalog**

```bash
python3 main.py --init-catalog
```

Expected: Fetches ~1500-2000 Medium/Hard problems, writes to Problems tab. Takes 30-60 seconds due to rate limiting.

- [ ] **Step 5: Fetch solved history (optional — needs LEETCODE_SESSION)**

Add your `LEETCODE_SESSION` cookie to `.env`, then:

```bash
python3 main.py --init-solved
```

Expected: Fetches your solved problem history, writes to Solved tab.

- [ ] **Step 6: Dry run**

```bash
python3 main.py --dry-run
```

Expected: Filters catalog, samples 100, Claude picks 3, prints Telegram preview without sending.

- [ ] **Step 7: Full run**

```bash
python3 main.py
```

Expected: Writes 3 problems to Sent tab, sends Telegram message, logs usage.

- [ ] **Step 8: Final commit**

```bash
cd /Users/jackie/personal
git add leetcode-recommender/
git commit -m "feat(leetcode-recommender): complete project ready for use"
```
