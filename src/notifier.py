import os
import requests
from dotenv import load_dotenv

load_dotenv()

def send_ntfy_alert(message, title="Finance Report"):
    """
    Sends an ntfy alert. 
    NOTE: Title must be ASCII only to avoid encoding errors.
    """
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        print("❌ Error: NTFY_TOPIC missing in .env")
        return

    url = f"https://ntfy.sh/{topic}"
    
    # Title is now ASCII only. The emoji is moved to the body.
    headers = {
        "Title": title,
        "Priority": "default",
        "Tags": "money_with_wings"
    }
    
    try:
        # Encode message to bytes (utf-8) to support emojis in the body
        response = requests.post(url, data=message.encode('utf-8'), headers=headers)
        
        if response.status_code == 200:
            print("✅ Alert sent via ntfy!")
        else:
            print(f"❌ Failed to send. Status: {response.status_code}")
    except Exception as e:
        print(f"🚨 Error dispatching ntfy notification: {e}")