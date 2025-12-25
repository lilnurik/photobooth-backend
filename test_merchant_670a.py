#!/usr/bin/env python3
"""
Проверка вашего конкретного Merchant ID: 670a6af1a048b8a82254e446
"""

import base64
import requests
import json

MERCHANT_ID = '670a6af1a048b8a82254e446'

print("=" * 70)
print("🔍 ПРОВЕРКА ВАШЕЙ КАССЫ PAYME")
print("=" * 70)
print()
print(f"ID кассы: {MERCHANT_ID}")
print()

# Тест 1: Простой order_id
print("📋 ТЕСТ 1: Простой order_id")
print("-" * 70)
order_id = "test-123"
amount = 100000  # 1000 сум в тийинах

payme_str = f"m={MERCHANT_ID};ac.order_id={order_id};a={amount}"
payme_b64 = base64.b64encode(payme_str.encode()).decode()
url1 = f"https://checkout.paycom.uz/{payme_b64}"

print(f"Order ID: {order_id}")
print(f"Сумма: 1,000 сум")
print(f"URL: {url1}")
print()

# Тест 2: Формат как в парфюмерии (число-число)
print("📋 ТЕСТ 2: Формат как в парфюмерии (kiosk_id-perfume_id)")
print("-" * 70)
order_id2 = "1-25"

payme_str2 = f"m={MERCHANT_ID};ac.order_id={order_id2};a={amount}"
payme_b642 = base64.b64encode(payme_str2.encode()).decode()
url2 = f"https://checkout.paycom.uz/{payme_b642}"

print(f"Order ID: {order_id2}")
print(f"Сумма: 1,000 сум")
print(f"URL: {url2}")
print()

# Тест 3: Формат фотобудки (photobooth-timestamp)
print("📋 ТЕСТ 3: Формат фотобудки (photobooth-timestamp)")
print("-" * 70)
order_id3 = "photobooth-1766460504607"

payme_str3 = f"m={MERCHANT_ID};ac.order_id={order_id3};a={amount}"
payme_b643 = base64.b64encode(payme_str3.encode()).decode()
url3 = f"https://checkout.paycom.uz/{payme_b643}"

print(f"Order ID: {order_id3}")
print(f"Сумма: 1,000 сум")
print(f"URL: {url3}")
print()

# Попробуем проверить через API Payme (если доступен)
print("=" * 70)
print("🧪 АВТОМАТИЧЕСКАЯ ПРОВЕРКА")
print("=" * 70)
print()

for i, (test_name, url) in enumerate([
    ("Тест 1 (test-123)", url1),
    ("Тест 2 (1-25)", url2),
    ("Тест 3 (photobooth-xxx)", url3)
], 1):
    print(f"{test_name}:")
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        
        # Проверяем содержимое ответа
        content = response.text.lower()
        
        if "недоступен" in content or "некорректно" in content:
            print("   ❌ Ошибка: Сервис недоступен")
        elif "не найден" in content or "not found" in content:
            print("   ❌ Ошибка: Merchant не найден")
        elif "неверн" in content or "invalid" in content:
            print("   ❌ Ошибка: Неверные данные")
        elif "paycom" in content or "payme" in content:
            # Проверяем есть ли форма оплаты
            if "payment" in content or "оплат" in content or "card" in content:
                print("   ✅ РАБОТАЕТ! Страница оплаты открылась")
            else:
                print("   ⚠️  Страница Payme открылась, но непонятно что показывает")
        else:
            print(f"   ⚠️  Странный ответ (status: {response.status_code})")
            
    except Exception as e:
        print(f"   ⚠️  Ошибка запроса: {e}")
    print()

print("=" * 70)
print("📝 ИНСТРУКЦИЯ")
print("=" * 70)
print()
print("1. Откройте каждый URL выше в браузере")
print("2. Проверьте какой из них работает:")
print()
print("   ✅ Если видите форму оплаты → этот формат order_id работает")
print("   ❌ Если видите ошибку → этот формат не поддерживается")
print()
print("3. Используйте рабочий формат в приложении")
print()
print("=" * 70)
print("🔧 ЧТО ПРОВЕРИТЬ В ЛИЧНОМ КАБИНЕТЕ PAYME")
print("=" * 70)
print()
print(f"Зайдите на: https://business.paycom.uz/")
print(f"Найдите кассу с ID: {MERCHANT_ID}")
print()
print("Проверьте:")
print("  ✅ Статус: Active (активна)")
print("  ✅ Категория: подходит для фотобудки")
print("  ✅ Настройки order_id: нет ограничений по формату")
print("  ✅ Webhook URL: настроен (для получения платежей)")
print()
print("=" * 70)
print()
