# ⚡ Быстрое тестирование после исправления

## Что было исправлено
✅ UNIQUE constraint failed: payments.order_id — ИСПРАВЛЕНО

## Как протестировать

### 1️⃣ Перезапустить backend
```bash
cd D:\fotobox+react\photobooth-magic-main\backend

# Если backend запущен — остановить (Ctrl+C)
# Затем запустить заново:
python app.py
```

### 2️⃣ Запустить frontend (если не запущен)
```bash
cd D:\fotobox+react\photobooth-magic-main
npm run electron:dev
```

### 3️⃣ Протестировать оплату
1. Выбрать формат фото
2. Сделать фотографии
3. Выбрать количество копий (например, 1 копия = 1000 сум)
4. Нажать "Оплатить"
5. Выбрать Payme
6. Сканировать QR код телефоном
7. Оплатить через Payme

### 4️⃣ Что проверить в логах backend

**Должно быть:**
```
DEBUG: generate_qr data={'order_id': '...', 'paymentType': 'payme', 'amount': 1000}
DEBUG: Created payment record for payme: order_id=..., id=1

DEBUG: CheckPerformTransaction order_id=..., amount=100000
✅ Возврат: {"id": ..., "result": {"allow": true}}

DEBUG: CreateTransaction order_id=..., transaction_id=...
DEBUG: Updated payment with transaction_id: ...
✅ Возврат: {"id": ..., "result": {"create_time": ..., "transaction": "1", "state": 1}}

DEBUG: PerformTransaction transaction_id=...
DEBUG: Payment success for order_id=...
✅ Возврат: {"id": ..., "result": {"state": 2, "perform_time": ...}}
```

**НЕ должно быть:**
```
❌ sqlite3.IntegrityError: UNIQUE constraint failed: payments.order_id
❌ sqlalchemy.exc.IntegrityError
```

### 5️⃣ Проверить БД
```bash
cd backend
python db_viewer.py
```

Или через API:
```bash
curl http://localhost:5000/api/stats
```

Должна быть 1 запись на каждый order_id (не дубликаты).

---

## 🔍 Ключевые изменения в коде

### CheckPerformTransaction
**Было:** Возвращал allow без проверок  
**Стало:** Проверяет существование order_id и корректность суммы

### CreateTransaction
**Было:** Пытался создать новую запись → UNIQUE constraint error  
**Стало:** Находит существующую запись и ОБНОВЛЯЕТ её

---

## 📊 Ожидаемый поток

```
1. Frontend → /api/generate-qr
   БД: Payment(order_id="...", transaction_id=None, status="pending")
   
2. Payme → CheckPerformTransaction
   БД: Без изменений (только проверка)
   
3. Payme → CreateTransaction
   БД: UPDATE Payment SET transaction_id="...", state=1
   
4. Payme → PerformTransaction
   БД: UPDATE Payment SET status="success", state=2
   
5. Frontend видит status="success" → переход на печать
```

---

## ✅ Готово!

Теперь система должна корректно обрабатывать webhook'и от Payme без ошибок UNIQUE constraint.

**Если всё работает:**
- ✅ Оплата проходит успешно
- ✅ Нет ошибок в логах
- ✅ В БД только 1 запись на order_id

**Если что-то не работает:**
- Проверь логи backend (см. выше)
- Проверь БД через db_viewer.py
- Смотри документацию: PAYME_WEBHOOK_FIX.md
