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
