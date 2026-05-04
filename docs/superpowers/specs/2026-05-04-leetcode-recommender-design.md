# LeetCode Problem Recommender — Design Spec

**Date:** 2026-05-04
**Project location:** `/Users/jackie/personal/leetcode-recommender/`
**Goal:** AI-powered LeetCode problem feeder targeting Mag 7 internship interview prep

## Overview

A CLI tool that recommends 3 LeetCode problems per invocation, using Claude to intelligently select problems based on the user's feedback history, solved history, and weak areas. Problems are delivered via Telegram with direct LeetCode links.

Follows the same architecture patterns as the article-recommender project.

## User Profile

- Software Engineer II, ~2 years experience, EE degree
- 700+ LeetCode problems already solved
- Target: Mag 7 (FAANG) internship interviews, Fall 2026
- Focus: Medium and Hard problems only (Easy excluded — not interview-relevant)

## Architecture

```
leetcode-recommender/
├── main.py          # Entry point, orchestration, CLI flags
├── config.py        # Env vars, user profile string
├── sheets.py        # Google Sheets read/write (gspread)
├── leetcode.py      # LeetCode GraphQL API client
├── analyzer.py      # Claude CLI integration (problem selection)
├── chat.py          # Telegram notifications
├── requirements.txt
├── .env / .env.example
├── .gitignore
└── CLAUDE.md
```

## Commands

| Command | Purpose |
|---------|---------|
| `python3 main.py --init-catalog` | Fetch full LeetCode problem catalog to Problems tab |
| `python3 main.py --init-solved` | Fetch solved history from LeetCode (requires `LEETCODE_SESSION` in `.env`) to Solved tab |
| `python3 main.py` | Pick 3 problems, write to Sent tab, send via Telegram |
| `python3 main.py --dry-run` | Pick 3 problems without writing to Sheet or sending Telegram |

`--init-catalog` and `--init-solved` are one-time setup steps (re-runnable to refresh).

## Data Model (Google Sheets)

### Problems Tab — Cached catalog from LeetCode API

| Column | Description |
|--------|-------------|
| ID | LeetCode problem number |
| Title | Problem title |
| Slug | URL slug (e.g., `two-sum`) |
| Difficulty | Medium or Hard (Easy excluded) |
| Tags | Topic tags (e.g., "Array, Two Pointers") |
| Acceptance Rate | Percentage |

Populated by `--init-catalog`. Fetches only free, non-premium Medium/Hard problems (Easy excluded at fetch time).

### Solved Tab — One-time import from LeetCode account

| Column | Description |
|--------|-------------|
| ID | LeetCode problem number |
| Title | Problem title |
| Solved Date | When accepted |

Populated by `--init-solved` using `LEETCODE_SESSION` cookie. Fetches accepted submissions from the past year.

### Sent Tab — Recommended problems with feedback

| Column | Description |
|--------|-------------|
| Date | Date recommended |
| ID | LeetCode problem number |
| Title | Problem title |
| Difficulty | Medium or Hard |
| Tags | Topic tags |
| URL | Direct link to problem |
| Difficulty Rating | User feedback: 1-5 (1=trivial, 5=couldn't solve) |
| Notes | Optional free-text feedback |

User fills in "Difficulty Rating" and "Notes" columns inline in the Sheet.

### Usage Tab — Token tracking

| Column | Description |
|--------|-------------|
| Date | Run date |
| Input Tokens | Claude input tokens |
| Output Tokens | Claude output tokens |
| Cost USD | Estimated cost |
| Duration (s) | Run duration |

## LeetCode API Client (`leetcode.py`)

Uses LeetCode's unofficial GraphQL endpoint at `POST https://leetcode.com/graphql/`.

### `fetch_problem_catalog()`

- No auth required
- Paginated query using `problemsetQuestionList` with `limit`/`skip`
- Fetches: ID, title, slug, difficulty, tags, acceptance rate
- Filters out Easy and premium-only problems (only stores Medium/Hard)
- 1-second delay between paginated requests (rate limiting)
- Writes results to Problems tab

### `fetch_solved_history(session_cookie)`

- Requires `LEETCODE_SESSION` cookie for auth
- Fetches all accepted submissions from the past year
- Extracts problem ID, title, and solve date
- Writes results to Solved tab

### `get_problem_url(slug)`

Returns `https://leetcode.com/problems/{slug}/`

## Recommender Logic (`analyzer.py`)

### Step 1 — Code filtering and sampling

1. Read Problems tab, Solved tab, and Sent tab from Sheets
2. Remove: solved problems, problems sent in previous 16 months
3. From the remaining pool, randomly sample ~100 problems (uniform random, each problem has equal chance regardless of how many tags it has)
4. This keeps Claude's input small while ensuring fair representation

### Step 2 — Claude picks 3

Sends to Claude CLI:
- Sampled problem list from Step 1 (ID, title, difficulty, tags)
- Recent feedback (last 20 entries from Sent tab with ratings + notes)
- User profile from config.py

Claude selects 3 problems, balancing:
- **Weak areas first** — topics where user rated difficulty high or left struggling notes
- **Difficulty progression** — appropriate mix of Medium/Hard per topic mastery
- **Topic diversity** — 3 different topics per batch when possible
- **Interview relevance** — prioritize patterns common in Mag 7 interviews (DP, graphs, trees, system design-adjacent algorithms)
- **Ignore sample distribution** — the input is a random sample; do NOT pick topics just because they appear more often in the sample. Base topic selection solely on the user's feedback and weak areas

Returns JSON:
```json
[
  {
    "id": "123",
    "title": "Problem Name",
    "slug": "problem-name",
    "difficulty": "Medium",
    "tags": ["Dynamic Programming", "Arrays"],
    "reason": "You struggled with DP state transitions — this is a classic interval DP"
  }
]
```

Claude CLI invocation: `claude -p --model sonnet --output-format json --max-turns 1 --allowedTools ""`

## Telegram Delivery (`chat.py`)

Single message with 3 problems:

```
LeetCode Problems for Today

1. Problem Name (Medium)
   Tags: Two Pointers, Binary Search
   Why: You rated hash map problems easy — this tests the same pattern with constraints
   https://leetcode.com/problems/problem-name/

2. ...

3. ...

Rate in the Sent sheet to improve future picks!
```

Uses same Telegram bot + chat ID as article-recommender. HTML formatting, link previews disabled.

## Configuration (`.env`)

```
GOOGLE_SHEET_ID=your-google-sheet-id
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=your-chat-id
LEETCODE_SESSION=your-session-cookie  # only needed for --init-solved
```

`GOOGLE_CREDENTIALS_PATH` points to the same service account JSON as article-recommender.

## Dependencies (`requirements.txt`)

- `gspread` — Google Sheets API
- `google-auth` — Google OAuth2
- `requests` — HTTP client (LeetCode API + Telegram)
- `python-dotenv` — Load `.env`

Same dependencies as article-recommender. No new libraries needed.

## Error Handling

- Secret sanitization in error logs (same pattern as article-recommender)
- LeetCode API failures: retry once, then report via Telegram
- Claude CLI failures: report error, don't write to Sheet
- Rate limiting: 1-second delay between LeetCode API pages

## Security

- Secrets in `.env`, not committed
- `LEETCODE_SESSION` only used during `--init-solved`, not stored in Sheet
- Formula injection prevention in Sheets cells (same `_safe_cell()` pattern)
- Telegram HTML escaping
- Service account scoped to Sheets API only
