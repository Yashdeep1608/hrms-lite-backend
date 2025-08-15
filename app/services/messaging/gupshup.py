import requests
from app.core.config import settings

# Use the template name "common_otp" for sandbox testing
GUPSHUP_API_KEY = settings.GUPSHUP_API_KEY
GUPSHUP_SOURCE = settings.GUPSHUP_SOURCE_NUMBER
GUPSHUP_APP_NAME = settings.GUPSHUP_APP_NAME   # Same as your Gupshup app name
GUPSHUP_TEMPLATE = "common_otp"  # Updated template name for sandbox testing

def send_whatsapp_otp_gupshup(isd_code: str, phone_number: str, otp: str):
    """
    Send OTP via Gupshup WhatsApp Template
    """
    try:
        url = "https://api.gupshup.io/wa/api/v1/template/msg"
        
        # Construct the full phone number (ISD code + phone number)
        full_number = f"{isd_code}{phone_number}".replace("+", "").strip()
        
        # Prepare the payload for the API request
        payload = {
            "channel": "whatsapp",
            "source": GUPSHUP_SOURCE,  # Sender's number
            "destination": full_number,  # Receiver's number
            "src.name": GUPSHUP_APP_NAME,  # App name
            "template": GUPSHUP_TEMPLATE,  # Template to use
            "lang": "en",  # Language for the template (can be customized)
            "params": ['Kriyato', otp, '10 minutes']  # Template parameters, {{1}} will be replaced with OTP
        }
        
        headers = {
            "apikey": GUPSHUP_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Make the POST request to Gupshup API
        response = requests.post(url, data=payload, headers=headers)
        
        # Log the response for debugging
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        # Check for successful response
        if response.status_code != 200:
            raise Exception(f"Gupshup HTTP Error: {response.status_code} - {response.text}")
        
        # Parse the response JSON to check the status
        resp_json = response.json()
        print(f"Response JSON: {resp_json}")
        
        if resp_json.get("status") != "submitted":
            raise Exception(f"Gupshup API Error: {resp_json}")
        
        # If everything is fine, return True
        return True
    except Exception as e:
        print(f"WhatsApp OTP send failed: {e}")
        raise Exception(str(e))
        return False