import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

tally_api_key = os.getenv("TALLY_API_KEY")

payload = {
    "eventTypes": ["FORM_CONTENT", "warranty-management"],
    "formId": "wLLK52",
    "url": "https://webhook.site/754ce517-7228-4f5c-b0e6-45891b2b2e79"
}

response = requests.get(
    "https://api.tally.so/webhooks",
    headers={"Authorization": f"Bearer {tally_api_key}"}
)

print(json.dumps(response.json(), indent=4))