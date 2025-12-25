"""
Тестовый скрипт для проверки исправления Click
"""
import requests
import json
import time

API_URL = "http://localhost:5000/api"

def test_click_flow():
    print("=" * 60)
    print("🧪 ТЕСТ: Click Payment Flow")
    print("=" * 60)
    print()
    
    # 1. Генерируем QR код
    order_id = f"photobooth-test-{int(time.time())}"
    amount = 1000
    
    print(f"1️⃣ Генерация QR кода...")
    print(f"   order_id: {order_id}")
    print(f"   amount: {amount}")
    print()
    
    try:
        response = requests.post(f"{API_URL}/generate-qr", json={
            "order_id": order_id,
            "paymentType": "click",
            "amount": amount
        })
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ QR код сгенерирован")
            print(f"   Click URL: {data.get('clickUrl', 'N/A')[:80]}...")
        else:
            print(f"   ❌ Ошибка: {response.status_code}")
            print(f"   {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return
    
    print()
    
    # 2. Проверяем статус
    print(f"2️⃣ Проверка статуса платежа...")
    try:
        response = requests.get(f"{API_URL}/payment-status/{order_id}")
        data = response.json()
        print(f"   Status: {data.get('status', 'N/A')}")
        print(f"   Payment Type: {data.get('payment_type', 'N/A')}")
        print(f"   Amount: {data.get('amount', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return
    
    print()
    
    # 3. Симулируем Click prepare
    print(f"3️⃣ Симуляция Click prepare...")
    try:
        response = requests.post(f"{API_URL}/click/prepare", data={
            "click_trans_id": f"test_{int(time.time())}",
            "service_id": "38261",
            "merchant_trans_id": order_id,
            "amount": str(amount),
            "action": "0",
            "sign_time": "2025-12-25 12:00:00",
            "error": "0",
            "error_note": "Success"
        })
        
        data = response.json()
        print(f"   Response: {json.dumps(data, indent=2)}")
        
        if data.get('error') == 0:
            print("   ✅ Prepare успешен!")
            merchant_prepare_id = data.get('merchant_prepare_id')
            click_trans_id = data.get('click_trans_id')
            
            print()
            
            # 4. Симулируем Click complete
            print(f"4️⃣ Симуляция Click complete...")
            response = requests.post(f"{API_URL}/click/complete", data={
                "click_trans_id": click_trans_id,
                "service_id": "38261",
                "merchant_trans_id": order_id,
                "merchant_prepare_id": str(merchant_prepare_id),
                "amount": str(amount),
                "action": "1",  # 1 = success
                "error": "0",
                "error_note": "Success"
            })
            
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            if data.get('error') == 0:
                print("   ✅ Complete успешен!")
                
                print()
                
                # 5. Проверяем финальный статус
                print(f"5️⃣ Проверка финального статуса...")
                response = requests.get(f"{API_URL}/payment-status/{order_id}")
                data = response.json()
                print(f"   Status: {data.get('status', 'N/A')}")
                print(f"   Perform Time: {data.get('perform_time', 'N/A')}")
                
                if data.get('status') == 'success':
                    print("   ✅ Платёж успешно завершён!")
                else:
                    print(f"   ⚠️ Статус: {data.get('status')}")
            else:
                print(f"   ❌ Complete failed: {data}")
        else:
            print(f"   ❌ Prepare failed: {data}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return
    
    print()
    print("=" * 60)
    print("✅ ТЕСТ ЗАВЕРШЁН")
    print("=" * 60)

if __name__ == "__main__":
    test_click_flow()
