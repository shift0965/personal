import html
from datetime import datetime, timezone

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_pick(article: dict | None, dry_run: bool = False):
    """Send the daily article pick to Telegram."""
    if not article:
        _send_message("No article to recommend today. Claude returned no candidates.", dry_run=dry_run)
        return

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    tags = html.escape(", ".join(article.get("tags", [])))
    title = html.escape(article.get("title", ""))
    source = html.escape(article.get("source", "Unknown"))
    summary = html.escape(article.get("summary", "No summary available."))
    url = article.get("url", "")
    read_time = article.get("estimated_read_minutes", "?")

    text = f"<b>Today's Read ({today})</b>\n\n"
    text += f"<b>{title}</b>\n"
    text += f"Source: {source} | {read_time} min read\n"
    if tags:
        text += f"Tags: {tags}\n"
    text += f"\n{summary}\n\n"
    safe_url = html.escape(url, quote=True)
    text += f"<a href=\"{safe_url}\">Read article</a>\n\n"
    text += "<i>Rate in the Articles sheet to improve future picks!</i>"

    _send_message(text, dry_run=dry_run)


def send_error_notification(error: str):
    """Send an error notification to Telegram."""
    safe_error = html.escape(error)
    text = f"<b>Article Recommender Failed</b>\n\nError: {safe_error}\n\nCheck the logs for details."
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
