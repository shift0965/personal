from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_ID

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Sheet tab names
ARTICLES_TAB = "Articles"
USAGE_TAB = "Usage"

# Headers for each tab
ARTICLES_HEADERS = ["Date", "Title", "URL", "Source", "Published", "Summary", "Tags", "Status", "Rating", "Notes"]
USAGE_HEADERS = ["Date", "Input Tokens", "Output Tokens", "Cost USD", "Articles Analyzed", "Duration (s)"]


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

    _ensure_tab(spreadsheet, ARTICLES_TAB, ARTICLES_HEADERS)
    _ensure_tab(spreadsheet, USAGE_TAB, USAGE_HEADERS)


def read_feedback() -> list[dict]:
    """Read feedback from the Rating/Notes columns in the Articles tab."""
    spreadsheet = _get_spreadsheet()
    ws = _ensure_tab(spreadsheet, ARTICLES_TAB, ARTICLES_HEADERS)

    rows = ws.get_all_values()
    if len(rows) <= 1:
        return []

    feedback = []
    for row in rows[1:]:
        # Rating is col 8 (index 8), Notes is col 9 (index 9)
        rating = row[8].strip() if len(row) > 8 else ""
        if not rating:
            continue
        feedback.append({
            "date": row[0],
            "title": row[1] if len(row) > 1 else "",
            "url": row[2] if len(row) > 2 else "",
            "rating": rating,
            "notes": row[9].strip() if len(row) > 9 else "",
        })
    return feedback


def read_sent_articles() -> list[dict]:
    """Read sent articles with title, URL, tags, and rating for Claude context."""
    spreadsheet = _get_spreadsheet()
    ws = _ensure_tab(spreadsheet, ARTICLES_TAB, ARTICLES_HEADERS)

    rows = ws.get_all_values()
    if len(rows) <= 1:
        return []

    articles = []
    for row in rows[1:]:
        if len(row) < 3 or not row[2].strip():
            continue
        articles.append({
            "title": row[1] if len(row) > 1 else "",
            "url": row[2],
            "tags": row[6] if len(row) > 6 else "",
            "rating": row[8] if len(row) > 8 else "",
            "notes": row[9] if len(row) > 9 else "",
        })
    return articles


def write_articles(articles: list[dict], status: str = "sent"):
    """Write articles to the Articles sheet."""
    spreadsheet = _get_spreadsheet()
    ws = _ensure_tab(spreadsheet, ARTICLES_TAB, ARTICLES_HEADERS)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = []
    for article in articles:
        tags = ", ".join(article.get("tags", []))
        rows.append([
            today,
            _safe_cell(article.get("title", "")),
            article.get("url", ""),
            _safe_cell(article.get("source", "")),
            article.get("published_date", ""),
            _safe_cell(article.get("summary", "")),
            _safe_cell(tags),
            status,
        ])

    if rows:
        ws.append_rows(rows)


def write_usage(usage: dict, articles_analyzed: int):
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
        str(articles_analyzed),
        str(usage.get("duration_secs", 0)),
    ])
