# 🚀 БЫСТРЫЙ СТАРТ - Исправление Payme

## ⚡ ЧТО ПРОИЗОШЛО

**Проблема:** `sqlite3.IntegrityError: UNIQUE constraint failed: payments.order_id`  
**Причина:** CreateTransaction пытался создать новую запись вместо обновления  
**Статус:** ✅ ИСПРАВЛЕНО

---

## 📦 ЧТО ДЕЛАТЬ

### 1️⃣ Git Push (на локальной машине)
```bash
cd D:\fotobox+react\photobooth-magic-main
git add .
git commit -m "Fix: Payme CreateTransaction UNIQUE constraint error"
git push origin main
```

### 2️⃣ Деплой (на сервере)
```bash
ssh user@server
cd /var/www/photobooth-backend
sudo systemctl stop photobooth-backend
git pull origin main
sudo systemctl start photobooth-backend
```

### 3️⃣ Проверка
```bash
tail -f photobooth.log | grep "✅ Payment updated"
```

---

## ✅ ИЗМЕНЕНИЯ

**Файл:** `backend/app.py`  
**Строки:** 215-274  

**Было:**
```python
payment = Payment.query.filter_by(transaction_id=transaction_id).first()
if not payment:
    payment = Payment(...)  # ❌ INSERT
    db.session.add(payment)
```

**Стало:**
```python
payment = Payment.query.filter_by(order_id=order_id).first()
payment.transaction_id = transaction_id  # ✅ UPDATE
db.session.commit()
```

---

## 📚 ДОКУМЕНТАЦИЯ

| Файл | Описание |
|------|----------|
| `✅_READY_TO_DEPLOY.md` | 👈 **НАЧНИ ОТСЮДА** |
| `⚡_DEPLOY_CHECKLIST.md` | Быстрый чеклист |
| `README_FIX.md` | Полное описание |
| `DEPLOY_FIX_PAYME.md` | Детальная инструкция |
| `PAYME_WEBHOOK_FIX.md` | Техническое описание |

---

## 🎯 ГОТОВО!

Выполни 2 команды:

```bash
# Локально
git add . && git commit -m "Fix: Payme webhook" && git push

# На сервере
git pull && sudo systemctl restart photobooth-backend
```

**Время:** 3 минуты 🚀
