# 🔧 Исправление Payme Webhook - UNIQUE constraint failed

**Дата:** 2025-12-26  
**Проблема:** `sqlite3.IntegrityError: UNIQUE constraint failed: payments.order_id`

---

## ❌ Проблема

### Что происходило:
1. При `/api/generate-qr` создавалась запись с `order_id`
2. Payme вызывал `CheckPerformTransaction` — проверка OK
3. Payme вызывал `CreateTransaction` — **пытался создать новую запись с тем же `order_id`**
4. SQLite падал с ошибкой UNIQUE constraint

### Ошибка в логике:
```python
# ❌ НЕПРАВИЛЬНО (старый код)
if not payment:
    payment = Payment(
        order_id=order_id,  # ← Дубль! order_id уже существует
        transaction_id=transaction_id,
        ...
    )
    db.session.add(payment)  # ← Попытка создать заново
```

---

## ✅ Решение

### Правильная архитектура:

**Этап 1: `/api/generate-qr`**
- Создаётся запись Payment с `order_id`
- `transaction_id` = None (ещё нет)
- `status` = 'pending'

**Этап 2: `CheckPerformTransaction` (webhook)**
- **ТОЛЬКО ПРОВЕРКА** — ничего не создаётся
- Проверяем: существует ли order_id
- Проверяем: совпадает ли сумма
- Возвращаем `{"allow": True}` или ошибку

**Этап 3: `CreateTransaction` (webhook)**
- **ОБНОВЛЯЕМ** существующую запись
- Находим по `order_id`
- Привязываем `transaction_id`
- Меняем `state = 1` (created)

**Этап 4: `PerformTransaction` (webhook)**
- **ОБНОВЛЯЕМ** существующую запись
- Находим по `transaction_id`
- Меняем `status = 'success'`, `state = 2`

---

## 🔧 Что изменено в app.py

### 1. CheckPerformTransaction (строки ~189-213)

**Было:**
```python
return jsonify({"result": {"allow": True}})  # Без проверок
```

**Стало:**
```python
# Проверяем существование заказа
payment = Payment.query.filter_by(order_id=order_id).first()

if not payment:
    return jsonify({"error": {"code": -31050, "message": "Order not found"}})

# Проверяем сумму (amount в тийинах, у нас в сумах)
expected_amount = payment.amount * 100
if amount != expected_amount:
    return jsonify({"error": {"code": -31001, "message": "Incorrect amount"}})

return jsonify({"id": id, "result": {"allow": True}})
```

### 2. CreateTransaction (строки ~214-262)

**Было:**
```python
# ❌ Создавал новую запись
payment = Payment.query.filter_by(transaction_id=transaction_id).first()

if not payment:
    payment = Payment(
        order_id=order_id,  # ← ДУБЛЬ!
        transaction_id=transaction_id,
        ...
    )
    db.session.add(payment)
```

**Стало:**
```python
# ✅ Обновляем существующую
payment = Payment.query.filter_by(order_id=order_id).first()

if not payment:
    return jsonify({"error": {"code": -31050, "message": "Order not found"}})

# ОБНОВЛЯЕМ (не создаём!)
payment.transaction_id = transaction_id
payment.state = 1
if not payment.create_time:
    payment.create_time = datetime.utcnow()

db.session.commit()
```

---

## 🧪 Как проверить

### 1. Перезапустить backend
```bash
cd photobooth-magic-main\backend
python app.py
```

### 2. Протестировать оплату
```bash
# В приложении:
1. Выбрать количество копий
2. Нажать "Оплатить"
3. Выбрать Payme
4. Сканировать QR код и оплатить
```

### 3. Проверить логи
Должно быть:
```
DEBUG: Created payment record for payme: order_id=...
DEBUG: CheckPerformTransaction order_id=...
DEBUG: CreateTransaction order_id=...
DEBUG: Updated payment with transaction_id: ...  ← НЕ Created!
DEBUG: PerformTransaction transaction_id=...
DEBUG: Payment success for order_id=...
```

❌ Не должно быть:
```
sqlite3.IntegrityError: UNIQUE constraint failed
```

---

## 📊 Жизненный цикл Payme транзакции

```
[Frontend] → /api/generate-qr
    ↓
[БД] Payment создана (order_id, transaction_id=None)
    ↓
[Payme] → CheckPerformTransaction
    ↓
[БД] ТОЛЬКО проверка (ничего не меняем)
    ↓
[Payme] → CreateTransaction
    ↓
[БД] ОБНОВЛЯЕМ (добавляем transaction_id, state=1)
    ↓
[Payme] → PerformTransaction
    ↓
[БД] ОБНОВЛЯЕМ (status='success', state=2)
    ↓
[Frontend] получает status='success'
    ↓
🎉 Печать!
```

---

## 💡 Ключевые принципы

1. **order_id** — ТВОЙ уникальный идентификатор заказа
2. **transaction_id** — Payme присваивает в CreateTransaction
3. **CheckPerformTransaction** — ТОЛЬКО проверка, БЕЗ изменений в БД
4. **CreateTransaction** — ОБНОВЛЕНИЕ existing записи, НЕ создание новой
5. **PerformTransaction** — финальное ОБНОВЛЕНИЕ статуса

---

## ✅ Статус

- [x] Исправлена ошибка UNIQUE constraint
- [x] Добавлены проверки в CheckPerformTransaction
- [x] CreateTransaction теперь обновляет, а не создаёт
- [x] Добавлено логирование для отладки

**Тестирование:** Требуется проверка с реальным Payme QR кодом

---

## 📝 Коды ошибок Payme

| Код | Значение |
|-----|----------|
| -31050 | Order not found |
| -31001 | Incorrect amount |
| -32504 | Transaction not found |
| -31008 | Transaction already exists |

Подробнее: https://developer.help.paycom.uz/metody-merchant-api/
