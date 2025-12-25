"""
Тестируем сценарий когда Click приходит БЕЗ предварительного создания заказа
(как в реальных логах)
"""
import requests
import json
import time

API_URL = "http://localhost:5000/api"

def test_click_without_generate_qr():
    print("=" * 60)
    print("🧪 ТЕСТ: Click БЕЗ generate-qr (как в логах)")
    print("=" * 60)
    print()
    
    # НЕ вызываем generate-qr, сразу идём в prepare
    order_id = "photobooth-1766558416339"  # Из твоих логов
    amount = 1000
    
    print(f"⚠️  ПРОПУСКАЕМ generate-qr (имитируем реальную ситуацию)")
    print(f"   order_id: {order_id}")
    print(f"   amount: {amount}")
    print()
    
    # 1. Проверяем что заказа НЕТ в базе
    print(f"1️⃣ Проверка что заказ НЕ существует...")
    try:
        response = requests.get(f"{API_URL}/payment-status/{order_id}")
        data = response.json()
        if 'id' in data:
            print(f"   ⚠️ Заказ УЖЕ существует! ID: {data['id']}")
        else:
            print(f"   ✅ Заказ НЕ найден (status: {data.get('status')})")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print()
    
    # 2. Click вызывает prepare БЕЗ предварительного заказа
    print(f"2️⃣ Click prepare (БЕЗ заказа в БД)...")
    try:
        click_trans_id = f"test_{int(time.time())}"
        response = requests.post(f"{API_URL}/click/prepare", data={
            "click_trans_id": click_trans_id,
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
            print("   ✅ Prepare успешен! Заказ был создан автоматически!")
            merchant_prepare_id = data.get('merchant_prepare_id')
            
            print()
            
            # 3. Проверяем что заказ теперь создан
            print(f"3️⃣ Проверка что заказ создан в БД...")
            response = requests.get(f"{API_URL}/payment-status/{order_id}")
            data = response.json()
            print(f"   Status: {data.get('status', 'N/A')}")
            print(f"   Payment Type: {data.get('payment_type', 'N/A')}")
            print(f"   Amount: {data.get('amount', 'N/A')}")
            print(f"   ID: {data.get('id', 'N/A')}")
            
            if data.get('payment_type') == 'click':
                print("   ✅ Заказ создан правильно!")
            else:
                print(f"   ⚠️ Неправильный payment_type: {data.get('payment_type')}")
            
            print()
            
            # 4. Complete
            print(f"4️⃣ Click complete...")
            response = requests.post(f"{API_URL}/click/complete", data={
                "click_trans_id": click_trans_id,
                "service_id": "38261",
                "merchant_trans_id": order_id,
                "merchant_prepare_id": str(merchant_prepare_id),
                "amount": str(amount),
                "action": "1",
                "error": "0",
                "error_note": "Success"
            })
            
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            if data.get('error') == 0:
                print("   ✅ Complete успешен!")
                
                print()
                
                # 5. Финальный статус
                print(f"5️⃣ Финальный статус...")
                response = requests.get(f"{API_URL}/payment-status/{order_id}")
                data = response.json()
                print(f"   Status: {data.get('status', 'N/A')}")
                
                if data.get('status') == 'success':
                    print("   ✅ Платёж завершён успешно!")
                else:
                    print(f"   ⚠️ Статус: {data.get('status')}")
            else:
                print(f"   ❌ Complete failed: {data}")
        else:
            print(f"   ❌ Prepare failed с ошибкой {data.get('error')}: {data.get('error_note')}")
            print(f"   ⚠️ ЭТО ПРОБЛЕМА ИЗ ТВОИХ ЛОГОВ!")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print()
    print("=" * 60)
    print("✅ ТЕСТ ЗАВЕРШЁН")
    print("=" * 60)

if __name__ == "__main__":
    test_click_without_generate_qr()
