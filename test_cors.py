import requests

# Test CORS preflight (OPTIONS request)
url = "http://localhost:8000/admin/jewellers/9/contacts"

try:
    # Test OPTIONS request (CORS preflight)
    print("Testing OPTIONS (CORS preflight)...")
    response = requests.options(url, headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization"
    }, timeout=5)
    
    print(f"✅ Status Code: {response.status_code}")
    print(f"✅ Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'MISSING')}")
    print(f"✅ Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'MISSING')}")
    print(f"✅ Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers', 'MISSING')}")
    print(f"✅ Access-Control-Allow-Credentials: {response.headers.get('Access-Control-Allow-Credentials', 'MISSING')}")
    
    # Test GET request with Origin header
    print("\nTesting GET with Origin header...")
    response = requests.get(url, headers={
        "Origin": "http://localhost:3000"
    }, timeout=5)
    
    print(f"✅ Status Code: {response.status_code}")
    print(f"✅ Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'MISSING')}")
    
    if response.status_code == 401:
        print("✅ 401 is expected (no auth token)")
    
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to backend")
except Exception as e:
    print(f"❌ Error: {e}")
