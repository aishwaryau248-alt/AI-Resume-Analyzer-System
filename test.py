import httpx

response = httpx.get(
    "https://huggingface.co"
)

print(response.status_code)

import httpx

url = "https://router.huggingface.co/hf-inference/models/google/flan-t5-base"

try:
    response = httpx.get(url)
    print(response.status_code)
    print(response.text)
except Exception as e:
    print("Error:", e)