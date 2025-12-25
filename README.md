# Photobooth Payment Backend

Backend для обработки платежей через Payme и Click.

## Установка

```bash
pip install -r requirements.txt
```

## Запуск

```bash
python app.py
```

Сервер запустится на `http://localhost:5000`

## Endpoints

### 1. Генерация QR кода
**POST** `/api/generate-qr`

Request:
```json
{
  "order_id": "photobooth-123456789",
  "paymentType": "payme",
  "amount": 10000
}
```

Response:
```json
{
  "qrCode": "data:image/png;base64,...",
  "paymeUrl": "https://checkout.paycom.uz/..."
}
```

### 2. Проверка статуса платежа
**GET** `/api/payment-status/<order_id>`

Response:
```json
{
  "status": "success",
  "amount": 10000,
  "payment_type": "payme"
}
```

### 3. Payme Webhook
**POST** `/api/payme/webhook`

Для обработки уведомлений от Payme.

### 4. Click Webhook
**POST** `/api/click/prepare`
**POST** `/api/click/complete`

Для обработки уведомлений от Click.

## Конфигурация

В `app.py` измените:
- `PAYME_MERCHANT_ID` - ваш ID мерчанта Payme
- `CLICK_MERCHANT_ID` - ваш ID мерчанта Click
- `CLICK_SERVICE_ID` - ваш Service ID Click

## Для продакшена

1. Используйте базу данных вместо `payments = {}`
2. Добавьте Redis для pub/sub уведомлений
3. Настройте HTTPS
4. Добавьте аутентификацию для webhook'ов
