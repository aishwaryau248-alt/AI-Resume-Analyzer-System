import httpx

try:
    response = httpx.get(
        "https://api-inference.huggingface.co"
    )

    print("Status:", response.status_code)

except Exception as e:
    print("Error:", e)