# 🔐 Настройка Webhook для Payme

**Дата:** 22.12.2025  
**Проект:** Sony Photobooth - Интеграция Payme

---

## 📋 Что нужно сделать

### Шаг 1: Получить Merchant ID и Key
1. Войдите в [Payme Business](https://business.payme.uz)
2. Зарегистрируйте новый мерчант для фотобудки
3. Скопируйте:
   - **Merchant ID** (например: `670a6af1a048b8a82254e446`)
   - **Merchant Key** (например: `cWdp34784eFsR...`)

### Шаг 2: Обновить конфигурацию
Откройте файл `backend/app.py` и замените:

```python
# Строки 23-28
PAYME_MERCHANT_ID = 'ВАШ_MERCHANT_ID'
PAYME_MERCHANT_KEY = 'ВАШ_MERCHANT_KEY'
```

### Шаг 3: Настроить Webhook URL в Payme

В личном кабинете Payme укажите URL для webhook'ов:

#### Для локального тестирования (через ngrok):
```bash
# 1. Установите ngrok: https://ngrok.com/download
# 2. Запустите туннель:
ngrok http 5000

# 3. Скопируйте URL (например: https://abc123.ngrok.io)
# 4. В Payme укажите:
```

**Webhook URL:**
```
https://abc123.ngrok.io/api/payme/webhook
```

#### Для production (с доменом):
```
https://ваш-домен.uz/api/payme/webhook
```

---

## 🔗 Endpoint для Payme Webhook

### URL для настройки в панели Payme:

```
https://ваш-домен.uz/api/payme/webhook
```

**Метод:** POST  
**Content-Type:** application/json

---

## 📊 Как работает Payme

### Схема взаимодействия:

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │────1───>│   Backend    │         │    Payme     │
│  (Photobooth)│         │  (Flask API) │<───2────│   Server     │
└──────────────┘         └──────────────┘         └──────────────┘
       │                         │                         │
       └────────3 (polling)──────┘                         │
       │                         │                         │
       └────────────4 (redirect to print)─────────────────┘
```

### Шаги процесса:

1. **Генерация QR кода:**
   - Frontend вызывает `/api/generate-qr`
   - Backend генерирует QR с данными для Payme
   - QR содержит: merchant_id, order_id, amount

2. **Пользователь сканирует QR:**
   - Открывается приложение Payme
   - Пользователь подтверждает оплату

3. **Payme отправляет webhook:**
   - `CheckPerformTransaction` - проверка возможности оплаты
   - `CreateTransaction` - создание транзакции
   - `PerformTransaction` - выполнение оплаты
   - `CheckTransaction` - проверка статуса (опционально)
   - `CancelTransaction` - отмена (если нужно)

4. **Frontend проверяет статус:**
   - Каждые 3 секунды вызывает `/api/payment-status/:order_id`
   - При статусе `success` переходит на печать

---

## 🧪 Тестирование

### 1. Тест генерации QR кода:
```bash
curl -X POST http://localhost:5000/api/generate-qr \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "photobooth-test-123",
    "paymentType": "payme",
    "amount": 10000
  }'
```

**Ожидаемый ответ:**
```json
{
  "qrCode": "data:image/png;base64,iVBORw0KG...",
  "paymeUrl": "https://checkout.paycom.uz/..."
}
```

### 2. Проверка статуса:
```bash
curl http://localhost:5000/api/payment-status/photobooth-test-123
```

**Ожидаемый ответ:**
```json
{
  "status": "pending",
  "order_id": "photobooth-test-123"
}
```

### 3. Имитация webhook от Payme (CheckPerformTransaction):
```bash
curl -X POST http://localhost:5000/api/payme/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "method": "CheckPerformTransaction",
    "params": {
      "account": {
        "order_id": "photobooth-test-123"
      },
      "amount": 1000000
    }
  }'
```

**Ожидаемый ответ:**
```json
{
  "result": {
    "allow": true
  }
}
```

### 4. Имитация успешной оплаты:
```bash
# Используйте тестовый endpoint:
curl -X POST http://localhost:5000/api/test-payment/photobooth-test-123
```

---

## 📋 Методы Payme (которые обрабатывает backend)

### 1. CheckPerformTransaction
**Цель:** Проверить, может ли транзакция быть выполнена

**Запрос от Payme:**
```json
{
  "id": 1,
  "method": "CheckPerformTransaction",
  "params": {
    "account": {
      "order_id": "photobooth-ORDER_ID"
    },
    "amount": 1000000
  }
}
```

**Ответ нашего backend:**
```json
{
  "result": {
    "allow": true
  }
}
```

### 2. CreateTransaction
**Цель:** Создать транзакцию (резервирование платежа)

**Запрос от Payme:**
```json
{
  "id": 2,
  "method": "CreateTransaction",
  "params": {
    "id": "transaction_id_from_payme",
    "account": {
      "order_id": "photobooth-ORDER_ID"
    },
    "amount": 1000000,
    "time": 1640000000000
  }
}
```

**Ответ нашего backend:**
```json
{
  "result": {
    "create_time": 1640000000000,
    "transaction": "1",
    "state": 1
  }
}
```

### 3. PerformTransaction
**Цель:** Выполнить транзакцию (списать деньги)

**Запрос от Payme:**
```json
{
  "id": 3,
  "method": "PerformTransaction",
  "params": {
    "id": "transaction_id_from_payme"
  }
}
```

**Ответ нашего backend:**
```json
{
  "result": {
    "transaction": "1",
    "perform_time": 1640000005000,
    "state": 2
  }
}
```

### 4. CancelTransaction
**Цель:** Отменить транзакцию

**Запрос от Payme:**
```json
{
  "id": 4,
  "method": "CancelTransaction",
  "params": {
    "id": "transaction_id_from_payme",
    "reason": 1
  }
}
```

**Ответ нашего backend:**
```json
{
  "result": {
    "transaction": "1",
    "cancel_time": 1640000010000,
    "state": -2
  }
}
```

---

## 🔐 Безопасность (Production)

### Проверка подписи запросов

Payme отправляет в каждом запросе заголовок `Authorization`:
```
Authorization: Basic base64(merchant_id:password)
```

В production нужно проверять этот заголовок!

**Добавьте в `app.py`:**
```python
import base64

def check_payme_auth():
    """Проверка авторизации от Payme"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False
    
    try:
        # Формат: "Basic base64(merchant_id:password)"
        auth_type, credentials = auth_header.split()
        decoded = base64.b64decode(credentials).decode('utf-8')
        merchant_id, password = decoded.split(':')
        
        return merchant_id == PAYME_MERCHANT_ID and password == PAYME_MERCHANT_KEY
    except:
        return False

@app.route('/api/payme/webhook', methods=['POST'])
def payme_webhook():
    # Проверяем подпись
    if not check_payme_auth():
        return jsonify({"error": {"code": -32504, "message": "Unauthorized"}}), 401
    
    # ... остальная логика
```

---

## 📝 Checklist для запуска

- [ ] Зарегистрирован Merchant ID в Payme
- [ ] Merchant ID и Key прописаны в `app.py`
- [ ] Backend запущен и доступен
- [ ] Настроен ngrok или домен с SSL
- [ ] Webhook URL указан в Payme кабинете
- [ ] Протестированы все методы (Check, Create, Perform)
- [ ] Frontend проверяет статус каждые 3 сек
- [ ] Добавлена проверка подписи (для production)

---

## 🆘 Troubleshooting

### Проблема: Webhook не приходит
**Решение:**
1. Проверьте URL в Payme кабинете
2. Убедитесь что backend доступен извне
3. Проверьте логи backend (`python app.py`)

### Проблема: "Абонента не существует"
**Решение:**
1. Merchant ID неправильный или от другого сервиса
2. Зарегистрируйте новый merchant для фотобудки

### Проблема: Frontend не видит успешный платёж
**Решение:**
1. Проверьте что webhook вызвал `PerformTransaction`
2. Убедитесь что БД обновилась (`status = 'success'`)
3. Проверьте что polling работает (смотрите Network в DevTools)

---

## 📞 Поддержка

**Техподдержка Payme:**
- Телефон: +998 78 113 80 00
- Email: support@payme.uz
- Документация: https://developer.help.paycom.uz

**Разработчик фотобудки:**
- Muhamadaliyev Abu Solih

---

## 🌐 Финальные endpoint'ы

### Для настройки в Payme:

#### Local (через ngrok):
```
https://ваш-ngrok-домен.ngrok.io/api/payme/webhook
```

#### Production:
```
https://ваш-домен.uz/api/payme/webhook
```

### Тестовые endpoint'ы:
- Генерация QR: `POST /api/generate-qr`
- Проверка статуса: `GET /api/payment-status/:order_id`
- Тестовая оплата: `POST /api/test-payment/:order_id`
- Статистика: `GET /api/stats`

---

**Готово! Теперь Payme интегрирован полностью! 🎉**
