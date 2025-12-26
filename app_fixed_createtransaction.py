# 🔧 ИСПРАВЛЕННЫЙ КОД для CreateTransaction webhook
# 
# ⚠️ ИНСТРУКЦИЯ ПО ПРИМЕНЕНИЮ:
# 
# 1. Остановить сервер Flask (Ctrl+C)
# 2. Скопировать этот код в /var/www/photobooth-backend/app.py (строки ~215-262)
#    ИЛИ заменить весь файл app.py этой версией
# 3. Перезапустить сервер: python app.py
#
# ГЛАВНОЕ ИЗМЕНЕНИЕ: CreateTransaction теперь ОБНОВЛЯЕТ существующую запись,
# а не создаёт новую → исправлена ошибка UNIQUE constraint failed

# ============================================================
# ФРАГМЕНТ КОДА ДЛЯ ЗАМЕНЫ (CreateTransaction)
# Найдите в app.py строку: elif method == 'CreateTransaction':
# И замените весь блок до следующего elif на этот код:
# ============================================================

elif method == 'CreateTransaction':
    transaction_id = params.get('id')
    amount = params.get('amount')
    account = params.get('account', {})
    order_id = account.get('order_id')
    
    print(f"DEBUG: CreateTransaction order_id={order_id}, transaction_id={transaction_id}", flush=True)
    
    # ✅ ШАГ 1: Ищем существующий платёж по order_id (он уже был создан в /generate-qr)
    payment = Payment.query.filter_by(order_id=order_id).first()
    
    if not payment:
        print(f"ERROR: Order not found: {order_id}", flush=True)
        return jsonify({
            "id": id,
            "error": {"code": -31050, "message": "Order not found"}
        })
    
    # ✅ ШАГ 2: Проверяем, может транзакция уже существует
    existing_with_txid = Payment.query.filter_by(transaction_id=transaction_id).first()
    if existing_with_txid:
        # Транзакция уже была создана ранее (повторный вызов)
        print(f"DEBUG: Transaction already exists: {transaction_id}", flush=True)
        return jsonify({
            "id": id,
            "result": {
                "create_time": int(existing_with_txid.create_time.timestamp() * 1000),
                "transaction": str(existing_with_txid.id),
                "state": existing_with_txid.state
            }
        })
    
    # ✅ ШАГ 3: ОБНОВЛЯЕМ существующую запись (НЕ СОЗДАЁМ НОВУЮ!)
    print(f"DEBUG: Updating payment order_id={order_id} with transaction_id={transaction_id}", flush=True)
    
    payment.transaction_id = transaction_id
    payment.state = 1  # created
    if not payment.create_time:
        payment.create_time = datetime.utcnow()
    
    # ⚠️ ВАЖНО: используем merge чтобы избежать конфликтов
    db.session.merge(payment)
    db.session.commit()
    
    print(f"DEBUG: ✅ Updated payment successfully: order_id={order_id}, transaction_id={transaction_id}", flush=True)
    
    return jsonify({
        "id": id,
        "result": {
            "create_time": int(payment.create_time.timestamp() * 1000),
            "transaction": str(payment.id),
            "state": 1
        }
    })

# ============================================================
# КОНЕЦ ФРАГМЕНТА
# ============================================================

# 📝 Альтернативный вариант с ещё более безопасной логикой:
# Если проблема повторяется, замените на этот код:

elif method == 'CreateTransaction':
    transaction_id = params.get('id')
    amount = params.get('amount')
    account = params.get('account', {})
    order_id = account.get('order_id')
    
    print(f"DEBUG: CreateTransaction order_id={order_id}, transaction_id={transaction_id}", flush=True)
    
    try:
        # Проверяем по transaction_id - может уже создано
        existing = Payment.query.filter_by(transaction_id=transaction_id).first()
        if existing:
            print(f"DEBUG: Transaction already exists, returning existing", flush=True)
            return jsonify({
                "id": id,
                "result": {
                    "create_time": int(existing.create_time.timestamp() * 1000),
                    "transaction": str(existing.id),
                    "state": existing.state
                }
            })
        
        # Ищем по order_id
        payment = Payment.query.filter_by(order_id=order_id).first()
        
        if not payment:
            return jsonify({
                "id": id,
                "error": {"code": -31050, "message": "Order not found"}
            })
        
        # Обновляем используя UPDATE напрямую (безопаснее)
        Payment.query.filter_by(order_id=order_id).update({
            'transaction_id': transaction_id,
            'state': 1,
            'create_time': datetime.utcnow() if not payment.create_time else payment.create_time
        })
        db.session.commit()
        
        # Перечитываем обновлённую запись
        payment = Payment.query.filter_by(order_id=order_id).first()
        
        print(f"DEBUG: ✅ Updated via UPDATE query: order_id={order_id}", flush=True)
        
        return jsonify({
            "id": id,
            "result": {
                "create_time": int(payment.create_time.timestamp() * 1000),
                "transaction": str(payment.id),
                "state": 1
            }
        })
        
    except Exception as e:
        print(f"ERROR in CreateTransaction: {e}", flush=True)
        db.session.rollback()
        return jsonify({
            "id": id,
            "error": {"code": -32400, "message": f"Internal error: {str(e)}"}
        })
