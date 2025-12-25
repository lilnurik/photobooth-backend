"""
Тестовый скрипт для проверки генерации QR кодов Payme и Click
"""
import base64

# Конфигурация (те же ID что в app.py)
PAYME_MERCHANT_ID = '670a6af1a048b8a82254e446'
CLICK_MERCHANT_ID = '29137'
CLICK_SERVICE_ID = '38261'

# Тестовые данные
order_id = "photobooth-test-123"
amount = 1000  # сумов

print("=" * 80)
print("ТЕСТ ГЕНЕРАЦИИ QR КОДОВ")
print("=" * 80)

# PAYME
print("\n📱 PAYME:")
print("-" * 80)
amount_tiyin = int(float(amount) * 100)  # 1000 сум = 100000 тийин
payme_str = f"m={PAYME_MERCHANT_ID};ac.order_id={order_id};a={amount_tiyin}"
payme_b64 = base64.b64encode(payme_str.encode()).decode()
payme_url = f"https://checkout.paycom.uz/{payme_b64}"

print(f"Order ID: {order_id}")
print(f"Amount: {amount} сум = {amount_tiyin} тийин")
print(f"Merchant ID: {PAYME_MERCHANT_ID}")
print(f"\nPayme String:")
print(f"  {payme_str}")
print(f"\nPayme Base64:")
print(f"  {payme_b64}")
print(f"\nPayme URL:")
print(f"  {payme_url}")

# CLICK
print("\n\n💳 CLICK:")
print("-" * 80)
amount_str = "{:.2f}".format(float(amount))
click_url = (
    f"https://my.click.uz/services/pay?"
    f"service_id={CLICK_SERVICE_ID}&merchant_id={CLICK_MERCHANT_ID}"
    f"&amount={amount_str}&transaction_param={order_id}"
)

print(f"Order ID: {order_id}")
print(f"Amount: {amount_str} сум")
print(f"Merchant ID: {CLICK_MERCHANT_ID}")
print(f"Service ID: {CLICK_SERVICE_ID}")
print(f"\nClick URL:")
print(f"  {click_url}")

print("\n" + "=" * 80)
print("ЧТО ПРОВЕРИТЬ:")
print("=" * 80)
print("\n1. Payme Merchant ID правильный?")
print(f"   Ваш ID: {PAYME_MERCHANT_ID}")
print("   Проверьте в личном кабинете Payme")

print("\n2. Click Merchant ID и Service ID правильные?")
print(f"   Merchant ID: {CLICK_MERCHANT_ID}")
print(f"   Service ID: {CLICK_SERVICE_ID}")
print("   Проверьте в личном кабинете Click")

print("\n3. В настройках Payme/Click:")
print("   - Проверьте что merchant активен")
print("   - Проверьте минимальную сумму платежа")
print("   - Убедитесь что тестовый режим отключен (если нужен прод)")

print("\n4. Откройте URL в браузере:")
print(f"   {payme_url}")
print(f"   {click_url}")
print("   Если видите ошибку - значит проблема в merchant ID")

print("\n" + "=" * 80)
