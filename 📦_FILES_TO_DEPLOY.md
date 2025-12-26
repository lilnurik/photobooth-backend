# 📦 ФАЙЛЫ ДЛЯ ДЕПЛОЯ

## ✅ Обязательные файлы (для исправления ошибки)

### 1. `backend/app.py` ⚠️ КРИТИЧНО
**Строки:** 215-274  
**Что изменено:** Логика CreateTransaction webhook  
**Статус:** ✅ Исправлено

---

## 📚 Документация (можно не заливать, но рекомендуется)

### 2. `backend/README_FIX.md`
Главный README с описанием исправления

### 3. `backend/DEPLOY_FIX_PAYME.md`
Полная инструкция по деплою с тестами

### 4. `backend/⚡_DEPLOY_CHECKLIST.md`
Быстрый чеклист для деплоя

### 5. `backend/PAYME_WEBHOOK_FIX.md`
Техническое описание проблемы и решения

### 6. `backend/⚡_ТЕСТИРОВАНИЕ_FIX.md`
Инструкция по тестированию после деплоя

### 7. `backend/⚠️_СЕРВЕР_НА_ДРУГОЙ_МАШИНЕ.md`
Объяснение почему изменения не применялись

### 8. `backend/app_fixed_createtransaction.py`
Фрагмент кода для ручной замены (резервный вариант)

---

## 🚀 Команды Git для деплоя

```bash
# Локально
cd D:\fotobox+react\photobooth-magic-main

# Добавить все файлы
git add backend/app.py
git add backend/*.md
git add backend/app_fixed_createtransaction.py

# Или добавить всё разом
git add .

# Коммит
git commit -m "Fix: Payme CreateTransaction UNIQUE constraint error

- Changed CreateTransaction to UPDATE existing payment instead of INSERT
- Added idempotency check for duplicate transaction_id
- Added try/except error handling with rollback
- Added detailed logging for debugging
- Created documentation for deployment"

# Залить на GitHub
git push origin main
```

---

## 📊 Размер изменений

| Файл | Размер | Строки | Критичность |
|------|--------|--------|-------------|
| app.py | ~60 строк | 215-274 | ⚠️ КРИТИЧНО |
| README_FIX.md | ~7 КБ | - | 📚 Документация |
| DEPLOY_FIX_PAYME.md | ~6 КБ | - | 📚 Документация |
| ⚡_DEPLOY_CHECKLIST.md | ~3 КБ | - | 📚 Документация |
| PAYME_WEBHOOK_FIX.md | ~8 КБ | - | 📚 Документация |
| Остальные | ~5 КБ | - | 📚 Документация |

**Итого:** 1 критичный файл + 7 файлов документации

---

## ⚡ Минимальный деплой (только критичное)

Если хочешь задеплоить ТОЛЬКО исправление без документации:

```bash
git add backend/app.py
git commit -m "Fix: Payme CreateTransaction UNIQUE constraint error"
git push origin main
```

На сервере:
```bash
cd /var/www/photobooth-backend
git pull origin main
sudo systemctl restart photobooth-backend
```

---

## 📝 Проверка перед коммитом

```bash
# 1. Проверить синтаксис Python
cd backend
python -c "import app; print('✅ Syntax OK')"

# 2. Посмотреть что изменилось
git diff backend/app.py

# 3. Проверить что файлы добавлены
git status
```

---

## ✅ После деплоя на сервер

```bash
# SSH на сервер
ssh user@server

# Проверить что файл обновился
cd /var/www/photobooth-backend
git log -1
grep "ПРОВЕРКА 1" app.py  # Должна быть эта строка

# Перезапустить
sudo systemctl restart photobooth-backend

# Проверить логи
tail -f photobooth.log | grep CreateTransaction
```

**Ожидаемый лог после исправления:**
```
DEBUG: CreateTransaction order_id=..., transaction_id=...
DEBUG: Updating payment: order_id=... with transaction_id=...
DEBUG: ✅ Payment updated successfully: order_id=..., transaction_id=...
```

---

## 🎯 Готово!

Все файлы готовы к деплою. Просто:

1. `git add .`
2. `git commit -m "Fix: Payme webhook"`
3. `git push`
4. На сервере: `git pull && restart`

**Время: 2-3 минуты**
