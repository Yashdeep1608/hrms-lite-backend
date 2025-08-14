import requests
from app.core.config import settings

GUPSHUP_API_KEY = settings.GUPSHUP_API_KEY
GUPSHUP_SOURCE = settings.GUPSHUP_SOURCE_NUMBER
GUPSHUP_APP_NAME = settings.GUPSHUP_APP_NAME   # Same as your Gupshup app name
GUPSHUP_TEMPLATE = settings.GUPSHUP_OTP_TEMPLATE

def send_whatsapp_otp_gupshup(isd_code: str, phone_number: str, otp: str):
    """
    Send OTP via Gupshup WhatsApp Template
    """
    try:
        url = "https://api.gupshup.io/wa/api/v1/template/msg"
        
        full_number = f"{isd_code}{phone_number}".replace("+", "").strip()
        
        payload = {
            "channel": "whatsapp",
            "source": GUPSHUP_SOURCE,
            "destination": full_number,
            "src.name": GUPSHUP_APP_NAME,
            "template": GUPSHUP_TEMPLATE,
            "lang": "en",
            "params": [otp]  # Matches {{1}} in your template
        }
        
        headers = {
            "apikey": GUPSHUP_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(url, data=payload, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Gupshup HTTP Error: {response.status_code} - {response.text}")
        
        resp_json = response.json()
        if resp_json.get("status") != "submitted":
            raise Exception(f"Gupshup API Error: {resp_json}")
        
        return True
    except Exception as e:
        print(f"WhatsApp OTP send failed: {e}")
        return False
