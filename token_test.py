from dotenv import load_dotenv
import os
import httpx

load_dotenv()

token = os.getenv("HF_API_KEY")

headers = {
    "Authorization": f"Bearer {token}"
}

response = httpx.get(
    "https://huggingface.co/api/whoami-v2",
    headers=headers
)

print("Status:", response.status_code)
print(response.text)