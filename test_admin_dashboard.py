"""Test admin dashboard API endpoints"""
import requests
import json

API_BASE = "http://localhost:8000"

# Test 1: Login as admin
print("=== Test 1: Admin Login ===")
login_response = requests.post(f"{API_BASE}/auth/login", json={
    "email": "admin@example.com",
    "password": "Admin123!@#"
})

if login_response.status_code == 200:
    print("✅ Admin login successful")
    token = login_response.json()["access_token"]
    print(f"Token: {token[:50]}...")
else:
    print(f"❌ Admin login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

# Test 2: Get admin dashboard data
print("\n=== Test 2: Admin Dashboard Data ===")
headers = {"Authorization": f"Bearer {token}"}
dashboard_response = requests.get(f"{API_BASE}/analytics/admin/dashboard", headers=headers)

if dashboard_response.status_code == 200:
    print("✅ Dashboard data retrieved successfully")
    data = dashboard_response.json()
    print(f"\n📊 Dashboard KPIs:")
    print(f"  - Total Jewellers: {data.get('total_jewellers', 0)}")
    print(f"  - Active Jewellers: {data.get('active_jewellers', 0)}")
    print(f"  - Total Contacts: {data.get('total_contacts_across_jewellers', 0)}")
    print(f"  - Messages (30d): {data.get('messages_last_30_days', 0)}")
    print(f"  - Delivery Rate: {data.get('overall_delivery_rate', 0)}%")
    print(f"  - Read Rate: {data.get('overall_read_rate', 0)}%")
    print(f"\n👥 Jeweller Stats ({len(data.get('jeweller_stats', []))} jewellers):")
    for jeweller in data.get('jeweller_stats', [])[:5]:
        print(f"  - {jeweller['business_name']}: {jeweller['total_contacts']} contacts, {jeweller['total_campaigns']} campaigns")
else:
    print(f"❌ Dashboard request failed: {dashboard_response.status_code}")
    print(dashboard_response.text)

# Test 3: Get jewellers list
print("\n=== Test 3: Jewellers List ===")
jewellers_response = requests.get(f"{API_BASE}/admin/jewellers", headers=headers)

if jewellers_response.status_code == 200:
    print("✅ Jewellers list retrieved successfully")
    jewellers_data = jewellers_response.json()
    print(f"  - Total: {jewellers_data.get('total', 0)}")
    print(f"  - Pending: {jewellers_data.get('pending_count', 0)}")
    print(f"  - Approved: {jewellers_data.get('approved_count', 0)}")
    print(f"  - Rejected: {jewellers_data.get('rejected_count', 0)}")
else:
    print(f"❌ Jewellers list failed: {jewellers_response.status_code}")
    print(jewellers_response.text)

print("\n✅ All tests complete!")
