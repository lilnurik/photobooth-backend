# 🔧 ИСПРАВЛЕНИЕ ГОТОВО - Payme Webhook

**Дата:** 26 декабря 2025  
**Проблема:** `sqlite3.IntegrityError: UNIQUE constraint failed: payments.order_id`  
**Статус:** ✅ ИСПРАВЛЕНО, готово к деплою

---

## 📋 Краткое описание

При обработке webhook `CreateTransaction` от Payme возникала ошибка дублирования `order_id` в базе данных. Код пытался создать новую запись Payment, хотя она уже существовала.

**Решение:** Изменена логика на обновление существующей записи вместо создания новой.

---

## 📦 Что нужно задеплоить

### Изменённые файлы:
1. `backend/app.py` — исправлена логика CreateTransaction (строки 215-274)

### Новые файлы (документация):
- `DEPLOY_FIX_PAYME.md` — полная инструкция по деплою
- `⚡_DEPLOY_CHECKLIST.md` — быстрый чеклист
- `PAYME_WEBHOOK_FIX.md` — техническое описание проблемы
- Этот файл (`README_FIX.md`)

---

## 🚀 Быстрый деплой (3 минуты)

```bash
# 1. Локально
cd D:\fotobox+react\photobooth-magic-main
git add .
git commit -m "Fix: Payme CreateTransaction UNIQUE constraint error"
git push origin main

# 2. На сервере
ssh user@server
cd /var/www/photobooth-backend
sudo systemctl stop photobooth-backend
git pull origin main
sudo systemctl start photobooth-backend

# 3. Проверка
tail -f photobooth.log | grep "CreateTransaction"
```

---

## 🔍 Что изменилось в коде

### БЫЛО (неправильно):
```python
elif method == 'CreateTransaction':
    # Искали по transaction_id
    payment = Payment.query.filter_by(transaction_id=transaction_id).first()
    
    if not payment:
        # ❌ Создавали новую запись с order_id
        payment = Payment(
            order_id=order_id,  # ← Дубль! order_id уже есть в БД
            transaction_id=transaction_id,
            ...
        )
        db.session.add(payment)
        db.session.commit()
```

### СТАЛО (правильно):
```python
elif method == 'CreateTransaction':
    try:
        # ✅ Проверка 1: Может транзакция уже создана (идемпотентность)
        existing = Payment.query.filter_by(transaction_id=transaction_id).first()
        if existing:
            return existing_data  # Уже создано, возвращаем существующее
        
        # ✅ Проверка 2: Ищем платёж по order_id
        payment = Payment.query.filter_by(order_id=order_id).first()
        
        if not payment:
            return error("Order not found")
        
        # ✅ ОБНОВЛЯЕМ существующую запись (НЕ создаём новую)
        payment.transaction_id = transaction_id
        payment.state = 1
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        return error(str(e))
```

---

## ✅ Преимущества нового кода

1. **Идемпотентность** — повторные вызовы webhook не ломают систему
2. **Нет дубликатов** — используется UPDATE вместо INSERT
3. **Обработка ошибок** — try/except с rollback
4. **Логирование** — детальные DEBUG сообщения для отладки
5. **Безопасность** — проверка существования order_id

---

## 🧪 Как проверить что всё работает

### После деплоя:

```bash
# 1. Создать тестовый платёж
curl -X POST http://localhost:5000/api/generate-qr \
  -H "Content-Type: application/json" \
  -d '{"order_id":"test-123","paymentType":"payme","amount":1000}'

# 2. Проверить логи (должны быть эти строки):
tail -f photobooth.log
```

**Ожидаемые логи:**
```
DEBUG: generate_qr data={'order_id': 'test-123', ...}
DEBUG: Created payment record for payme: order_id=test-123, id=1
DEBUG: CheckPerformTransaction order_id=test-123, amount=100000
✅ CheckPerformTransaction passed

DEBUG: CreateTransaction order_id=test-123, transaction_id=694e...
DEBUG: Updating payment: order_id=test-123 with transaction_id=694e...
DEBUG: ✅ Payment updated successfully: order_id=test-123, transaction_id=694e...

DEBUG: PerformTransaction transaction_id=694e...
DEBUG: Payment success for order_id=test-123
```

**НЕ должно быть:**
```
❌ sqlite3.IntegrityError: UNIQUE constraint failed: payments.order_id
❌ sqlalchemy.exc.IntegrityError
❌ [SQL: INSERT INTO payments ...]
```

---

## 📊 Жизненный цикл Payme транзакции (после исправления)

```
1. Frontend → POST /api/generate-qr
   ↓
   БД: INSERT Payment (order_id, transaction_id=NULL, status='pending')
   ✅ Создана запись №1

2. Payme → CheckPerformTransaction
   ↓
   БД: SELECT * FROM payments WHERE order_id=...
   ✅ Проверка существования и суммы

3. Payme → CreateTransaction
   ↓
   БД: UPDATE payments SET transaction_id=..., state=1 WHERE order_id=...
   ✅ Обновлена запись №1 (НЕ создана новая!)

4. Payme → PerformTransaction
   ↓
   БД: UPDATE payments SET status='success', state=2 WHERE transaction_id=...
   ✅ Обновлена запись №1

5. Frontend → GET /api/payment-status/:order_id
   ↓
   БД: SELECT * FROM payments WHERE order_id=...
   ✅ Возвращает status='success'
   ↓
   Frontend → Переход на экран печати 🎉
```

**Главное:** На всех этапах работаем с ОДНОЙ записью в БД!

---

## 🔄 Откат (если что-то пошло не так)

```bash
# На сервере
cd /var/www/photobooth-backend

# Посмотреть последние коммиты
git log --oneline -5

# Откатить на предыдущую версию
git reset --hard HEAD~1

# Перезапустить
sudo systemctl restart photobooth-backend

# Проверить
tail -f photobooth.log
```

---

## 📞 Поддержка

Если после деплоя проблема повторяется:

1. **Проверь версию кода:**
   ```bash
   cd /var/www/photobooth-backend
   git log -1
   grep "ПРОВЕРКА 1" app.py  # Должна быть эта строка
   ```

2. **Проверь логи:**
   ```bash
   tail -n 100 photobooth.log | grep -E "(ERROR|CreateTransaction)"
   ```

3. **Проверь БД:**
   ```bash
   sqlite3 photobooth.db "SELECT * FROM payments ORDER BY id DESC LIMIT 5;"
   ```

4. **Очисти БД (если нужно):**
   ```bash
   sqlite3 photobooth.db "DELETE FROM payments WHERE status='pending';"
   ```

---

## 📚 Дополнительная документация

- `DEPLOY_FIX_PAYME.md` — полная инструкция (6 КБ)
- `⚡_DEPLOY_CHECKLIST.md` — быстрый чеклист (2.7 КБ)
- `PAYME_WEBHOOK_FIX.md` — техническое описание (8 КБ)

---

## ✅ Контрольный список деплоя

- [x] Код исправлен в `app.py`
- [x] Добавлена обработка ошибок (try/except)
- [x] Добавлена идемпотентность
- [x] Добавлено детальное логирование
- [x] Создана документация
- [ ] Закоммичено в Git
- [ ] Залито на GitHub
- [ ] Задеплоено на сервер
- [ ] Протестировано с реальной оплатой
- [ ] Проверены логи

---

**Готово к деплою!** 🚀

Просто сделай:
```bash
git add .
git commit -m "Fix: Payme webhook UNIQUE constraint error"
git push
```

И на сервере:
```bash
git pull && sudo systemctl restart photobooth-backend
```

**Время на деплой:** 2-3 минуты  
**Риск:** Минимальный  
**Даунтайм:** ~30 секунд
