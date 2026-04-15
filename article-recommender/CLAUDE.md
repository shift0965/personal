# Article Recommender

AI-powered daily article recommender for software engineering skill development.

## What This Project Does

Daily article recommender that sends 1 classic software engineering article per day. Uses a 2-phase Claude flow: Phase 1 generates 5 candidate articles, Phase 2 fetches their content and picks the best one with a summary. Stores history in Google Sheets and sends picks via Telegram. Runs on a Mac home server via cron at 8 AM daily.

## Architecture

```
Phase 1: Claude suggests 5 candidates (based on goals + sent history + feedback)
Phase 2: Fetch article content → Claude picks best 1 + writes summary/tags
→ Google Sheets + Telegram
```

## Daily Flow (main.py)

1. Init sheets (create tabs if missing)
2. Read context from Sheets (sent history with tags/ratings, feedback)
3. **Phase 1 — Recommend**: Claude suggests 5 classic article candidates, avoiding previously sent articles
4. **Phase 2 — Evaluate**: Fetch content from those 5 URLs, Claude picks the best 1, writes summary + tags
5. Write pick to Articles tab, send via Telegram, log usage

## File Structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point, orchestrates the daily flow. Flags: `--init`, `--dry-run` |
| `config.py` | All configuration: API keys (from `.env`), `USER_PROFILE` (learning goals — single source of truth) |
| `analyzer.py` | Claude CLI integration — 2-phase recommend + evaluate, content fetching |
| `sheets.py` | Google Sheets CRUD via `gspread` — Articles, Usage tabs |
| `chat.py` | Telegram Bot API sender with HTML escaping |

## Google Sheets Layout (1 spreadsheet, 2 tabs)

- **Articles** — sent articles with summaries, tags, status, + Rating/Notes columns for inline feedback
- **Usage** — daily token usage tracking (input/output tokens, cost)

## Key Design Decisions

- **No static pool** — Claude generates fresh candidates each run based on `USER_PROFILE` in config.py, feedback, and sent history
- **2-phase Claude flow** — Phase 1 suggests candidates, Phase 2 reads actual content to make the final pick
- **Claude CLI (`claude -p`)** instead of Anthropic API — uses the user's Pro subscription, no extra cost
- **Content fetching** — Phase 2 fetches full article content via HTTP, strips HTML, truncates to ~5000 chars
- **Structured output** — Claude returns JSON via `--output-format json`, responses validated

## User Profile Context

The user's personal profile, learning goals, and article selection guidance are defined in `USER_PROFILE` in `config.py` (single source of truth).

## Environment (.env)

```
GOOGLE_CREDENTIALS_PATH=/absolute/path/to/service-account.json
GOOGLE_SHEET_ID=<sheet-id>
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_CHAT_ID=<chat-id>
```

## Running

```bash
python3 main.py --init      # First time: create sheet tabs
python3 main.py --dry-run   # Test without sending Telegram or writing Sheets
python3 main.py             # Normal daily run
```

## Cron

```
0 8 * * * cd /Users/jackie/personal/article-recommender && python3 main.py >> cron.log 2>&1
```

## Security Notes

- Error logs sanitized to redact secrets (Telegram token, sheet ID)
- Article content treated as untrusted — Claude prompt includes injection guard
- Telegram messages HTML-escaped to prevent injection from article titles
- Service account scoped to Sheets API only
- Dependencies pinned in `requirements.txt`
