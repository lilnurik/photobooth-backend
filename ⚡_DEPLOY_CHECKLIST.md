# ⚡ БЫСТРЫЙ ДЕПЛОЙ - Исправление Payme

## 🎯 Что исправлено
`UNIQUE constraint failed: payments.order_id` — ИСПРАВЛЕНО ✅

## 📦 Что нужно задеплоить
Только 1 файл: `backend/app.py`

---

## 🚀 Команды для деплоя

### 1️⃣ Локально (Windows)
```bash
cd D:\fotobox+react\photobooth-magic-main

# Проверить что изменилось
git status
git diff backend/app.py

# Закоммитить
git add backend/app.py
git commit -m "Fix: Payme CreateTransaction UNIQUE constraint error"

# Залить на GitHub
git push origin main
```

### 2️⃣ На сервере (Linux)
```bash
# SSH подключение
ssh user@10.10.0.172

# Перейти в директорию
cd /var/www/photobooth-backend

# Остановить сервер
sudo systemctl stop photobooth-backend
# или если нет systemd:
pkill -f "python.*app.py"

# Подтянуть изменения
git pull origin main

# Перезапустить сервер
sudo systemctl start photobooth-backend
# или:
nohup python app.py > photobooth.log 2>&1 &

# Проверить что запустился
ps aux | grep app.py
tail -f photobooth.log
```

---

## ✅ Проверка после деплоя

```bash
# 1. Проверить что сервер работает
curl http://localhost:5000/api/test

# 2. Создать тестовую транзакцию
curl -X POST http://localhost:5000/api/generate-qr \
  -H "Content-Type: application/json" \
  -d '{"order_id":"test-'$(date +%s)'","paymentType":"payme","amount":1000}'

# 3. Проверить логи (должно быть "✅ Payment updated successfully")
tail -n 50 photobooth.log | grep CreateTransaction
```

### Ожидаемый лог:
```
DEBUG: CreateTransaction order_id=photobooth-..., transaction_id=694e...
DEBUG: Updating payment: order_id=photobooth-... with transaction_id=694e...
DEBUG: ✅ Payment updated successfully
```

### НЕ должно быть:
```
❌ sqlite3.IntegrityError: UNIQUE constraint failed
```

---

## 🔄 Если нужен откат

```bash
# На сервере
cd /var/www/photobooth-backend
git log --oneline -5
git reset --hard <previous_commit_hash>
sudo systemctl restart photobooth-backend
```

---

## 📝 Что изменилось в коде

**backend/app.py, строки 215-273:**

```python
# БЫЛО ❌
payment = Payment.query.filter_by(transaction_id=transaction_id).first()
if not payment:
    payment = Payment(...)  # Создавал заново
    db.session.add(payment)

# СТАЛО ✅
existing = Payment.query.filter_by(transaction_id=transaction_id).first()
if existing:
    return existing  # Уже создано

payment = Payment.query.filter_by(order_id=order_id).first()
payment.transaction_id = transaction_id  # ОБНОВЛЯЕМ
db.session.commit()
```

---

## 🎉 Готово!

После деплоя транзакции Payme будут работать без ошибок.

**Время деплоя:** ~2-3 минуты  
**Даунтайм:** ~30 секунд (перезапуск сервера)  
**Риск:** Минимальный (только обновление логики webhook)
