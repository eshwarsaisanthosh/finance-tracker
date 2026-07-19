"""Send finance reports via WhatsApp using CallMeBot (free, no account needed).

Setup (one-time):
  1. Save +34 644 59 72 23 in your phone contacts as "CallMeBot".
  2. Send it this WhatsApp message: "I allow callmebot to send me messages"
  3. It replies with your personal API key.
  4. Add to .env:
       CALLMEBOT_PHONE=+1YOURNUMBER      # your WhatsApp number, E.164 format
       CALLMEBOT_APIKEY=123456           # the key CallMeBot sent you

Usage:
  from src.whatsapp_notifier import send_whatsapp_alert
  send_whatsapp_alert(report, title="Finance Report")
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

_API_URL = "https://api.callmebot.com/whatsapp.php"
# CallMeBot handles long text, but keep messages reasonable.
_MAX_CHARS = 3000


def _truncate(message: str, limit: int = _MAX_CHARS) -> str:
    if len(message) <= limit:
        return message
    cutoff = message.rfind("\n", 0, limit - 40)
    cutoff = cutoff if cutoff > 0 else limit - 40
    return message[:cutoff] + "\n\n(report truncated)"


def _normalize_phone(raw: str) -> str:
    """Strip spaces/dashes/parens and guarantee a single leading '+'."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    return "+" + digits


def send_whatsapp_alert(message: str, title: str = "Finance Report") -> None:
    """Send a WhatsApp message via CallMeBot. Skips gracefully if creds are missing."""
    phone = os.getenv("CALLMEBOT_PHONE")
    apikey = os.getenv("CALLMEBOT_APIKEY")

    missing = [k for k, v in {
        "CALLMEBOT_PHONE": phone,
        "CALLMEBOT_APIKEY": apikey,
    }.items() if not v]

    if missing:
        print(f"❌ WhatsApp: missing env vars: {', '.join(missing)}")
        return

    phone = _normalize_phone(phone)
    body = f"*{title}*\n\n{_truncate(message)}"

    try:
        response = requests.get(
            _API_URL,
            params={"phone": phone, "text": body, "apikey": apikey},
            timeout=30,
        )
        snippet = response.text[:300].replace("\n", " ").strip()
        if response.status_code == 200:
            print(f"✅ WhatsApp accepted by CallMeBot. Response: {snippet}")
        else:
            print(f"❌ WhatsApp failed. Status: {response.status_code} — {snippet}")
    except Exception as e:
        print(f"🚨 WhatsApp send failed: {e}")
