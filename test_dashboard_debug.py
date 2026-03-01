"""Test admin dashboard with detailed error info"""
import requests
import json

API_BASE = "http://localhost:8000"

# Login
login_response = requests.post(f"{API_BASE}/auth/login", json={
    "email": "admin@example.com",
    "password": "Admin123!@#"
})

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Test dashboard with error details
print("=== Testing /analytics/admin/dashboard ===")
try:
    response = requests.get(f"{API_BASE}/analytics/admin/dashboard", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ SUCCESS!")
        print(json.dumps(data, indent=2))
    else:
        print(f"\n❌ FAILED")
        
except Exception as e:
    print(f"❌ Exception: {e}")
