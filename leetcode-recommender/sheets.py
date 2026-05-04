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
