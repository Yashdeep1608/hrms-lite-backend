import json
import requests
from app.core.config import settings

# Use the template name "common_otp" for sandbox testing
GUPSHUP_API_KEY = settings.GUPSHUP_API_KEY
GUPSHUP_SOURCE = settings.GUPSHUP_SOURCE_NUMBER
GUPSHUP_APP_NAME = settings.GUPSHUP_APP_NAME
GUPSHUP_TEMPLATE_OTP_ID = "3dfcaf58-f217-43f6-91e7-a8b59565938b"  # Use your actual template ID
GUPSHUP_TEMPLATE_TRANSACTION_ID = "84b5f824-cb0c-4dec-81a7-0eca86602123"  # Use your actual template ID
GUPSHUP_TEMPLATE_TRANSACTION2_ID = "ae10e65e-44f9-4f81-bc3a-6252b8d333fd"  # Use your actual template ID


def send_whatsapp_otp_gupshup(isd_code: str, phone_number: str, otp: str):
    """
    Send OTP via Gupshup WhatsApp Template
    """
    try:
        url = "https://api.gupshup.io/wa/api/v1/template/msg"

        # Construct the full phone number (remove any +)
        full_number = f"{isd_code}{phone_number}".replace("+", "").strip()

        # Build template payload as JSON string
        template_payload = {
            "id": GUPSHUP_TEMPLATE_OTP_ID,
            "params": [otp,otp]  # match your template placeholders
        }

        # Prepare the form-data payload
        payload = {
            "channel": "whatsapp",
            "source": GUPSHUP_SOURCE,
            "src.name": GUPSHUP_APP_NAME,
            "destination": full_number,
            "template": json.dumps(template_payload),  # must be stringified JSON
        }

        headers = {
            "apikey": GUPSHUP_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
            "accept": "application/json",
        }
        response = requests.post(url, data=payload, headers=headers)
        
        if response.status_code != 202:
            raise Exception(f"Gupshup HTTP Error: {response.status_code} - {response.text}")

        resp_json = response.json()

        # Successful submission check
        if resp_json.get("status") != "submitted":
            raise Exception(f"Gupshup API Error: {resp_json}")

        return True

    except Exception as e:
        print(f"WhatsApp OTP send failed: {e}")
        return False
    
def send_whatsapp_transaction_gupshup(isd_code: str, phone_number: str, name: str, amount:str, valid:str,plan:str):
    """
    Send OTP via Gupshup WhatsApp Template
    """
    try:
        url = "https://api.gupshup.io/wa/api/v1/template/msg"

        # Construct the full phone number (remove any +)
        full_number = f"{isd_code}{phone_number}".replace("+", "").strip()

        # Build template payload as JSON string
        template_payload = {
            "id": GUPSHUP_TEMPLATE_TRANSACTION_ID,
            "params": [name,plan,valid,amount]  # match your template placeholders
        }

        # Prepare the form-data payload
        payload = {
            "channel": "whatsapp",
            "source": GUPSHUP_SOURCE,
            "src.name": GUPSHUP_APP_NAME,
            "destination": full_number,
            "template": json.dumps(template_payload),  # must be stringified JSON
        }

        headers = {
            "apikey": GUPSHUP_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
            "accept": "application/json",
        }
        response = requests.post(url, data=payload, headers=headers)
        
        if response.status_code != 202:
            raise Exception(f"Gupshup HTTP Error: {response.status_code} - {response.text}")

        resp_json = response.json()

        # Successful submission check
        if resp_json.get("status") != "submitted":
            raise Exception(f"Gupshup API Error: {resp_json}")

        return True

    except Exception as e:
        print(f"WhatsApp OTP send failed: {e}")
        return False
    
def send_whatsapp_transaction2_gupshup(isd_code: str, phone_number: str,name: str,users:str,amount:str,valid:str,total_amount:str):
    try:
        url = "https://api.gupshup.io/wa/api/v1/template/msg"

        # Construct the full phone number (remove any +)
        full_number = f"{isd_code}{phone_number}".replace("+", "").strip()

        # Build template payload as JSON string
        template_payload = {
            "id": GUPSHUP_TEMPLATE_TRANSACTION2_ID,
            "params": [name,users,amount,valid,total_amount]  # match your template placeholders
        }

        # Prepare the form-data payload
        payload = {
            "channel": "whatsapp",
            "source": GUPSHUP_SOURCE,
            "src.name": GUPSHUP_APP_NAME,
            "destination": full_number,
            "template": json.dumps(template_payload),  # must be stringified JSON
        }

        headers = {
            "apikey": GUPSHUP_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
            "accept": "application/json",
        }
        response = requests.post(url, data=payload, headers=headers)
        
        if response.status_code != 202:
            raise Exception(f"Gupshup HTTP Error: {response.status_code} - {response.text}")

        resp_json = response.json()

        # Successful submission check
        if resp_json.get("status") != "submitted":
            raise Exception(f"Gupshup API Error: {resp_json}")

        return True

    except Exception as e:
        print(f"WhatsApp OTP send failed: {e}")
        return False
    