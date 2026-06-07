"""
telegram_send.py — send messages to the configured Telegram chat.

Usage (as a module):
    from tools.telegram_send import send_message
    send_message("hello")

Usage (CLI test):
    python tools/telegram_send.py "test message"
    python tools/telegram_send.py            # sends a default ping
"""

import os
import sys

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TELEGRAM_API_BASE

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_message(text, parse_mode="HTML", disable_preview=True):
    """
    Send a message to the configured chat. Returns the Telegram API response
    dict. Raises RuntimeError if credentials are missing or the API errors.
    """
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set in .env")

    url = f"{TELEGRAM_API_BASE}/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_preview,
    }
    resp = requests.post(url, json=payload, timeout=30)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "✅ betsu is wired up. Telegram channel works."
    result = send_message(msg)
    print(f"Sent. message_id={result['result']['message_id']}")
