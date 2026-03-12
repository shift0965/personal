"""
AI Article Recommender — Daily runner

2-phase Claude recommendation:
  Phase 1: Claude suggests 5 classic article candidates based on goals + history
  Phase 2: Claude reads those articles (fetched content) and picks the best 1

Usage:
    python main.py              # Normal daily run
    python main.py --init       # Initialize sheets only (first-time setup)
    python main.py --dry-run    # Run without sending Telegram or writing to Sheets
"""

import os
import sys
import traceback

from analyzer import recommend_candidates, evaluate_and_pick
from sheets import (
    init_sheets,
    read_feedback,
    read_sent_articles,
    write_articles,
    write_usage,
)
from chat import send_pick, send_error_notification


def run():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("[DRY RUN MODE] Will not send Telegram messages or write to Sheets.\n")

    print("[1/5] Initializing sheets...")
    init_sheets()

    if "--init" in sys.argv:
        print("[DONE] Sheets initialized.")
        return

    print("[2/5] Reading context from Sheets...")
    feedback = read_feedback()
    sent_articles = read_sent_articles()

    print(f"       Feedback: {len(feedback)} entries, Sent: {len(sent_articles)} articles")

    print("[3/5] Phase 1 — Asking Claude for 5 article candidates...")
    candidates, phase1_usage = recommend_candidates(sent_articles, feedback)

    if not candidates:
        print("[DONE] Claude returned no candidates.")
        send_pick(None, dry_run=dry_run)
        return

    print(f"       Got {len(candidates)} candidates:")
    for c in candidates:
        print(f"         - {c['title']}")

    print("[4/5] Phase 2 — Fetching content & picking best article...")
    winner, phase2_usage = evaluate_and_pick(candidates, feedback)
    print(f"       Winner: {winner['title']}")

    # Combine usage from both phases
    usage = {}
    for key in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens", "cost_usd"):
        usage[key] = phase1_usage.get(key, 0) + phase2_usage.get(key, 0)

    if usage:
        print(f"       Total tokens: {usage.get('input_tokens', 0)} in / {usage.get('output_tokens', 0)} out | Cost: ${usage.get('cost_usd', 0):.4f}")

    if dry_run:
        print("[5/5] [DRY RUN] Telegram message preview:")
        send_pick(winner, dry_run=True)
    else:
        print("[5/5] Writing to Sheets & sending Telegram...")
        write_articles([winner], status="sent")
        if usage:
            write_usage(usage, len(candidates))
        send_pick(winner)

    print("[DONE] Sent 1 article.")


def _sanitize(text: str) -> str:
    """Strip secrets from error output before logging or sending."""
    secrets = [
        os.getenv("TELEGRAM_BOT_TOKEN", ""),
        os.getenv("TELEGRAM_CHAT_ID", ""),
        os.getenv("GOOGLE_SHEET_ID", ""),
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
