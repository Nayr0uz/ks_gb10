import requests
import json

url = "http://localhost:8002/signup"
payload = {
    "email": "debug_test@example.com",
    "password": "password123",
    "confirm_password": "password123",
    "full_name": "Debug User"
}

try:
    print(f"Testing signup to {url}...")
    resp = requests.post(url, json=payload)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Request failed: {e}")
