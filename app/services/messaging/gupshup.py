import json
import requests
from app.core.config import settings

# Use the template name "common_otp" for sandbox testing
GUPSHUP_API_KEY = settings.GUPSHUP_API_KEY
GUPSHUP_SOURCE = settings.GUPSHUP_SOURCE_NUMBER
GUPSHUP_APP_NAME = settings.GUPSHUP_APP_NAME
GUPSHUP_TEMPLATE_ID = "3dfcaf58-f217-43f6-91e7-a8b59565938b"  # Use your actual template ID


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
            "id": GUPSHUP_TEMPLATE_ID,
            "params": [otp]  # match your template placeholders
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
        # # 🟢 Print final curl equivalent
        # print(dict_to_curl(url, payload, headers))
        # Make the POST request
        response = requests.post(url, data=payload, headers=headers)

        # print(f"Response Status Code: {response.status_code}")
        # print(f"Response Body: {response.text}")

        if response.status_code != 202:
            raise Exception(f"Gupshup HTTP Error: {response.status_code} - {response.text}")

        resp_json = response.json()

        # Successful submission check
        if resp_json.get("status") != "submitted":
            raise Exception(f"Gupshup API Error: {resp_json}")

        return True

    except Exception as e:
        # print(f"WhatsApp OTP send failed: {e}")
        return False
    
# import requests
# import json

# def dict_to_curl(url, data, headers):
#     curl_parts = ["curl --request POST \\"]
#     curl_parts.append(f"     --url {url} \\")
#     for k, v in headers.items():
#         curl_parts.append(f"     --header '{k}: {v}' \\")
#     for k, v in data.items():
#         curl_parts.append(f"     --data '{k}={v}' \\")
#     return "\n".join(curl_parts)
