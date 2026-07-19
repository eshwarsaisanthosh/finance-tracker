"""Send finance reports via WhatsApp using Twilio.

Setup (one-time):
  1. pip install twilio
  2. Add to .env:
       TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
       TWILIO_AUTH_TOKEN=your_auth_token
       TWILIO_WHATSAPP_FROM=whatsapp:+14155238886   # Twilio sandbox number
       TWILIO_WHATSAPP_TO=whatsapp:+1YOURNUMBER

  Sandbox: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
  Production: requires a Twilio-approved WhatsApp sender.

Usage:
  from src.whatsapp_notifier import send_whatsapp_alert
  send_whatsapp_alert(report, title="Finance Report")
"""

import os
from dotenv import load_dotenv

load_dotenv()

# WhatsApp has a 1600-character message limit.
_MAX_CHARS = 1600


def _truncate(message: str, limit: int = _MAX_CHARS) -> str:
    if len(message) <= limit:
        return message
    cutoff = message.rfind("\n", 0, limit - 40)
    cutoff = cutoff if cutoff > 0 else limit - 40
    return message[:cutoff] + "\n\n_(report truncated)_"


def send_whatsapp_alert(message: str, title: str = "Finance Report") -> None:
    """Send a WhatsApp message via Twilio. Silently skips if credentials are missing."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_FROM")
    to_number = os.getenv("TWILIO_WHATSAPP_TO")

    missing = [k for k, v in {
        "TWILIO_ACCOUNT_SID": account_sid,
        "TWILIO_AUTH_TOKEN": auth_token,
        "TWILIO_WHATSAPP_FROM": from_number,
        "TWILIO_WHATSAPP_TO": to_number,
    }.items() if not v]

    if missing:
        print(f"❌ WhatsApp: missing env vars: {', '.join(missing)}")
        return

    try:
        from twilio.rest import Client  # imported here so missing package gives a clear error
    except ImportError:
        print("❌ WhatsApp: twilio package not installed. Run: pip install twilio")
        return

    body = f"*{title}*\n\n{_truncate(message)}"

    try:
        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            from_=from_number,
            to=to_number,
            body=body,
        )
        print(f"✅ WhatsApp alert sent! SID: {msg.sid}")
    except Exception as e:
        print(f"🚨 WhatsApp send failed: {e}")
