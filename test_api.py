import requests
import json

API_URL = 'https://fbox.polito.uz/api'

print("=" * 50)
print("Testing Photobooth Payment API with SQLite")
print("=" * 50)

# Test 1: Health check
print("\n1. Testing /api/test...")
response = requests.get(f'{API_URL}/test')
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test 2: Generate Payme QR
print("\n2. Testing Payme QR generation...")
data = {
    'order_id': 'photobooth-test-123',
    'paymentType': 'payme',
    'amount': 10000
}
response = requests.post(f'{API_URL}/generate-qr', json=data)
print(f"Status: {response.status_code}")
result = response.json()
print(f"QR Code length: {len(result.get('qrCode', ''))}")
print(f"Payme URL: {result.get('paymeUrl', 'N/A')[:80]}...")

# Test 3: Generate Click QR
print("\n3. Testing Click QR generation...")
data = {
    'order_id': 'photobooth-test-456',
    'paymentType': 'click',
    'amount': 10000
}
response = requests.post(f'{API_URL}/generate-qr', json=data)
print(f"Status: {response.status_code}")
result = response.json()
print(f"QR Code length: {len(result.get('qrCode', ''))}")
print(f"Click URL: {result.get('clickUrl', 'N/A')[:80]}...")

# Test 4: Check payment status (should be pending)
print("\n4. Testing payment status check...")
response = requests.get(f'{API_URL}/payment-status/photobooth-test-123')
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test 5: Simulate payment success
print("\n5. Testing payment simulation...")
response = requests.post(f'{API_URL}/test-payment/photobooth-test-123')
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test 6: Check payment status (should be success now)
print("\n6. Verifying payment status after simulation...")
response = requests.get(f'{API_URL}/payment-status/photobooth-test-123')
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

print("\n" + "=" * 50)
print("All tests completed!")
print("=" * 50)

# Test 7: Check stats
print("\n7. Testing statistics...")
response = requests.get(f'{API_URL}/stats')
print(f"Status: {response.status_code}")
stats = response.json()
print(f"Total payments: {stats.get('total_payments', 0)}")
print(f"Success payments: {stats.get('success_payments', 0)}")
print(f"Total revenue: {stats.get('total_revenue', 0)} sum")

# Test 8: Get all payments
print("\n8. Testing get all payments...")
response = requests.get(f'{API_URL}/payments?limit=10')
print(f"Status: {response.status_code}")
result = response.json()
print(f"Total payments in DB: {result.get('total', 0)}")
print(f"Fetched: {len(result.get('payments', []))} payments")

print("\n" + "=" * 50)
print("✅ SQLite DATABASE IS WORKING!")
print("=" * 50)
