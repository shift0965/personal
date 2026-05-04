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
