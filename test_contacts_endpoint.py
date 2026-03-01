import requests

# Test the contacts endpoint
url = "http://localhost:8000/admin/jewellers/9/contacts?page_size=50"

try:
    response = requests.get(url, timeout=5)
    print(f"✅ Status Code: {response.status_code}")
    print(f"✅ CORS Header: {response.headers.get('Access-Control-Allow-Origin', 'MISSING')}")
    print(f"✅ Content-Type: {response.headers.get('Content-Type', 'MISSING')}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Contacts returned: {len(data.get('contacts', []))}")
        print(f"✅ Total contacts: {data.get('total', 0)}")
        print("🎉 SUCCESS: Endpoint working correctly!")
    else:
        print(f"❌ ERROR: {response.text[:200]}")
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to backend - is it running on port 8000?")
except Exception as e:
    print(f"❌ Error: {e}")
