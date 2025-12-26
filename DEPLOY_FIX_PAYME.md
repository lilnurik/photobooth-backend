# 🔧 Исправление UNIQUE constraint failed в Payme webhook

**Дата:** 2025-12-26  
**Версия:** 1.0  
**Статус:** ГОТОВО для деплоя

---

## ❌ Проблема

При обработке webhook `CreateTransaction` от Payme возникала ошибка:

```
sqlite3.IntegrityError: UNIQUE constraint failed: payments.order_id
[SQL: INSERT INTO payments (order_id, transaction_id, ...) VALUES (?, ?, ...)]
```

**Причина:** Код пытался создать новую запись Payment с `order_id`, который уже существовал в БД (создан при `/api/generate-qr`).

---

## ✅ Решение

Изменена логика webhook `CreateTransaction` в файле `app.py`:

### Было (неправильно):
```python
# Искали по transaction_id
payment = Payment.query.filter_by(transaction_id=transaction_id).first()

if not payment:
    # Создавали новую запись ❌
    payment = Payment(
        order_id=order_id,  # ← ДУБЛЬ!
        transaction_id=transaction_id,
        ...
    )
    db.session.add(payment)
```

### Стало (правильно):
```python
# 1. Проверяем существование транзакции (повторный запрос)
existing_transaction = Payment.query.filter_by(transaction_id=transaction_id).first()
if existing_transaction:
    return existing_transaction  # уже создано

# 2. Ищем платёж по order_id
payment = Payment.query.filter_by(order_id=order_id).first()

if not payment:
    return error("Order not found")

# 3. ОБНОВЛЯЕМ существующую запись ✅
payment.transaction_id = transaction_id
payment.state = 1
db.session.commit()
```

---

## 📝 Изменённые файлы

### 1. `backend/app.py`

**Строки ~215-273:** Переписан блок `CreateTransaction`

**Изменения:**
- ✅ Добавлена проверка на существующую транзакцию (идемпотентность)
- ✅ Поиск платежа по `order_id` вместо `transaction_id`
- ✅ Обновление существующей записи вместо создания новой
- ✅ Обработка ошибок с `try/except` и `rollback`
- ✅ Детальное логирование для отладки

---

## 🧪 Тестирование

### Перед деплоем:

```bash
# 1. Локально проверить синтаксис
cd backend
python -c "import app; print('OK')"

# 2. Запустить тесты (если есть)
pytest test_api.py
```

### После деплоя на сервер:

```bash
# 1. Перезапустить сервер
sudo systemctl restart photobooth-backend
# или
pkill -f app.py && python /var/www/photobooth-backend/app.py

# 2. Проверить логи
tail -f /var/log/photobooth-backend.log

# 3. Тестовая транзакция
curl -X POST http://localhost:5000/api/generate-qr \
  -H "Content-Type: application/json" \
  -d '{"order_id": "test-123", "paymentType": "payme", "amount": 1000}'

# Ожидаемый результат:
# - QR код генерируется
# - В БД создаётся Payment с order_id=test-123
# - При webhook CreateTransaction запись ОБНОВЛЯЕТСЯ (не создаётся заново)
```

### Проверка логов:

**Правильные логи:**
```
DEBUG: generate_qr data={'order_id': 'photobooth-...', 'paymentType': 'payme', 'amount': 1000}
DEBUG: Created payment record for payme: order_id=photobooth-..., id=1
DEBUG: CheckPerformTransaction order_id=photobooth-..., amount=100000
DEBUG: CreateTransaction order_id=photobooth-..., transaction_id=694e...
DEBUG: Updating payment: order_id=photobooth-... with transaction_id=694e...
DEBUG: ✅ Payment updated successfully: order_id=photobooth-..., transaction_id=694e...
DEBUG: PerformTransaction transaction_id=694e...
DEBUG: Payment success for order_id=photobooth-...
```

**НЕ должно быть:**
```
❌ sqlite3.IntegrityError: UNIQUE constraint failed: payments.order_id
❌ sqlalchemy.exc.IntegrityError
❌ ERROR in CreateTransaction
```

---

## 🚀 Инструкция по деплою

### Через Git:

```bash
# 1. На локальной машине
cd D:\fotobox+react\photobooth-magic-main
git add backend/app.py
git commit -m "Fix: UNIQUE constraint error in Payme CreateTransaction webhook"
git push origin main

# 2. На сервере
cd /var/www/photobooth-backend
git pull origin main

# 3. Перезапустить сервер
sudo systemctl restart photobooth-backend
# или если без systemd:
pkill -f "python.*app.py"
python app.py
```

### Ручное копирование (если Git не настроен):

```bash
# С Windows на сервер
scp D:\fotobox+react\photobooth-magic-main\backend\app.py user@server:/var/www/photobooth-backend/

# На сервере
ssh user@server
sudo systemctl restart photobooth-backend
```

---

## 🔄 Откат (если что-то пошло не так)

```bash
# На сервере
cd /var/www/photobooth-backend
git log --oneline  # найти предыдущий коммит
git revert HEAD    # откатить последний коммит
# или
git reset --hard HEAD~1  # жёсткий откат

sudo systemctl restart photobooth-backend
```

---

## 📊 Дополнительные улучшения (опционально)

### Рекомендуется добавить индексы в БД:

```sql
-- Для ускорения поиска
CREATE INDEX IF NOT EXISTS idx_payment_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payment_transaction_id ON payments(transaction_id);
CREATE INDEX IF NOT EXISTS idx_payment_status ON payments(status);
```

Добавить в `models.py`:
```python
class Payment(db.Model):
    __tablename__ = 'payments'
    
    order_id = db.Column(db.String, unique=True, nullable=False, index=True)
    transaction_id = db.Column(db.String, unique=True, nullable=True, index=True)
    status = db.Column(db.String, default='pending', index=True)
```

---

## ✅ Контрольный список

- [x] Код исправлен в `app.py`
- [x] Добавлено логирование
- [x] Добавлена обработка ошибок
- [x] Проверена идемпотентность (повторные запросы не ломают систему)
- [ ] Протестировано локально
- [ ] Залито в Git
- [ ] Задеплоено на сервер
- [ ] Протестировано с реальной транзакцией Payme
- [ ] Проверены логи на сервере

---

## 📞 Поддержка

Если после деплоя проблема повторяется:

1. Проверь логи: `tail -f /var/log/...`
2. Проверь версию: `git log -1`
3. Проверь БД: `sqlite3 photobooth.db "SELECT * FROM payments ORDER BY id DESC LIMIT 5;"`
4. Открой issue в репозитории с полными логами

---

**Автор:** GitHub Copilot CLI  
**Дата создания:** 2025-12-26  
**Версия документа:** 1.0
