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
    solved_slugs = read_solved()
    sent = read_sent()
    feedback = [s for s in sent if s.get("difficulty_rating")]

    print(f"       Catalog: {len(problems)} problems, Solved: {len(solved_slugs)}, Sent: {len(sent)}, Feedback: {len(feedback)}")

    if not problems:
        print("[ERROR] No problems in catalog. Run --init-catalog first.")
        sys.exit(1)

    print("[3] Filtering and sampling...")
    sampled = filter_and_sample(problems, solved_slugs, sent)
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
