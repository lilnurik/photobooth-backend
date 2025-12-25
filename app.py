from flask import Flask, jsonify, request
from flask_cors import CORS
import io, base64, qrcode
from datetime import datetime
import json
import os
import threading
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

from models import db, Payment, Photo, Session, SessionPhoto
from session_routes import init_session_routes

app = Flask(__name__)
CORS(app, origins=['http://localhost:5173'], supports_credentials=True)

# Конфигурация базы данных SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "photobooth.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация БД
db.init_app(app)

# ⚠️ ВАЖНО: Конфигурация для Payme и Click
# ВАШИ РЕАЛЬНЫЕ ДАННЫЕ КАССЫ ФОТОБУДКИ
PAYME_MERCHANT_ID = '670a6af1a048b8a82254e446'  # ✅ Ваша касса
PAYME_MERCHANT_KEY = 'dWa%hsRz0I2?SGKOR6IUnfP5W%RPZPKGeHXX'  # ✅ Ваш ключ
CLICK_MERCHANT_ID = '29137'
CLICK_SERVICE_ID = '38261'

# Функция проверки подписи Payme (для production)
def check_payme_auth():
    """Проверка авторизации от Payme через Basic Auth"""
    if not PAYME_MERCHANT_KEY:
        # В режиме разработки без ключа - пропускаем
        return True
    
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False
    
    try:
        # Формат: "Basic base64(merchant_id:password)"
        auth_type, credentials = auth_header.split(' ', 1)
        if auth_type != 'Basic':
            return False
        
        decoded = base64.b64decode(credentials).decode('utf-8')
        merchant_id, password = decoded.split(':', 1)
        
        return merchant_id == PAYME_MERCHANT_ID and password == PAYME_MERCHANT_KEY
    except Exception as e:
        print(f"DEBUG: Auth check error: {e}", flush=True)
        return False

# Создание таблиц при первом запуске
with app.app_context():
    db.create_all()
    print("Database tables created successfully!", flush=True)
    print("✅ Tables: payments, photos, sessions, session_photos", flush=True)

# Инициализация роутов для сессий
init_session_routes(app)

@app.route('/api/test', methods=['GET'])
def test():
    # Подсчитаем количество платежей в БД
    payment_count = Payment.query.count()
    return jsonify({
        'status': 'OK', 
        'message': 'Photobooth payment API working with SQLite',
        'database': 'SQLite',
        'payments_count': payment_count
    })

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    data = request.get_json()
    print(f"DEBUG: generate_qr data={data}", flush=True)
    
    order_id = data.get('order_id')
    payment_type = data.get('paymentType')
    amount = data.get('amount')
    
    print(f"DEBUG: order_id={order_id}, payment_type={payment_type}, amount={amount}", flush=True)
    
    # ✅ СОЗДАЁМ запись в БД СРАЗУ при генерации QR
    existing_payment = Payment.query.filter_by(order_id=order_id).first()
    
    if not existing_payment:
        try:
            payment = Payment(
                order_id=order_id,
                transaction_id=None,  # Будет заполнено при webhook
                amount=int(float(amount)),
                payment_type=payment_type,
                status='pending',
                state=0,  # 0 = создан, ожидает оплаты
                create_time=datetime.utcnow()
            )
            db.session.add(payment)
            db.session.commit()
            print(f"DEBUG: Created payment record for {payment_type}: order_id={order_id}, id={payment.id}", flush=True)
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: ERROR creating payment: {e}", flush=True)
            return jsonify({'error': 'Failed to create payment'}), 500
    else:
        print(f"DEBUG: Payment already exists: order_id={order_id}", flush=True)
    
    if payment_type == 'payme':
        # Payme требует сумму в тийинах (1 сум = 100 тийин)
        amount_tiyin = int(float(amount) * 100)
        # ВАЖНО: Формат для Payme - m=MERCHANT_ID;ac.order_id=ORDER_ID;a=AMOUNT_TIYIN
        payme_str = f"m={PAYME_MERCHANT_ID};ac.order_id={order_id};a={amount_tiyin}"
        payme_b64 = base64.b64encode(payme_str.encode()).decode()
        payme_url = f"https://checkout.paycom.uz/{payme_b64}"
        
        print(f"DEBUG: payme_str={payme_str}", flush=True)
        print(f"DEBUG: payme_b64={payme_b64}", flush=True)
        print(f"DEBUG: payme_url={payme_url}", flush=True)
        
        img = qrcode.make(payme_url)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_b64 = 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({'qrCode': qr_b64, 'paymeUrl': payme_url})
        
    elif payment_type == 'click':
        # Click требует сумму в сумах с 2 десятичными знаками
        amount_str = "{:.2f}".format(float(amount))
        # ВАЖНО: transaction_param используется как идентификатор заказа
        click_url = (
            f"https://my.click.uz/services/pay?"
            f"service_id={CLICK_SERVICE_ID}&merchant_id={CLICK_MERCHANT_ID}"
            f"&amount={amount_str}&transaction_param={order_id}"
        )
        
        print(f"DEBUG: click_url={click_url}", flush=True)
        
        img = qrcode.make(click_url)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_b64 = 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({'qrCode': qr_b64, 'clickUrl': click_url})
        
    else:
        return jsonify({'error': 'Invalid payment type'}), 400

@app.route('/api/payment-status/<order_id>', methods=['GET'])
def payment_status(order_id):
    """Проверка статуса платежа из БД"""
    payment = Payment.query.filter_by(order_id=order_id).first()
    if payment:
        return jsonify(payment.to_dict())
    return jsonify({'status': 'pending', 'order_id': order_id})

@app.route('/api/payme/webhook', methods=['POST'])
def payme_webhook():
    """Webhook для обработки уведомлений от Payme
    
    Этот endpoint принимает запросы от Payme сервера.
    URL для настройки в Payme: https://ваш-домен.uz/api/payme/webhook
    
    Payme вызывает следующие методы:
    - CheckPerformTransaction - проверка возможности оплаты
    - CreateTransaction - создание транзакции
    - PerformTransaction - выполнение оплаты
    - CancelTransaction - отмена транзакции
    - CheckTransaction - проверка статуса
    - GetStatement - получение выписки
    """
    # Проверяем авторизацию (для production)
    # if not check_payme_auth():
    #     return jsonify({"error": {"code": -32504, "message": "Unauthorized"}}), 401
    
    data = request.json
    print("DEBUG: payme_webhook data:", data, flush=True)
    
    id = data.get('id')
    method = data.get('method')
    params = data.get('params', {})
    
    if method == 'CheckPerformTransaction':
        account = params.get('account', {})
        order_id = account.get('order_id')
        amount = params.get('amount')
        
        print(f"DEBUG: CheckPerformTransaction order_id={order_id}, amount={amount}", flush=True)
        return jsonify({"result": {"allow": True}})
        
    elif method == 'CreateTransaction':
        transaction_id = params.get('id')
        amount = params.get('amount')
        account = params.get('account', {})
        order_id = account.get('order_id')
        
        print(f"DEBUG: CreateTransaction order_id={order_id}, transaction_id={transaction_id}", flush=True)
        
        # Проверяем существует ли уже платёж
        payment = Payment.query.filter_by(transaction_id=transaction_id).first()
        
        if not payment:
            # Создаём новый платёж
            payment = Payment(
                order_id=order_id,
                transaction_id=transaction_id,
                amount=amount // 100,  # конвертируем тийины в сумы
                payment_type='payme',
                status='pending',
                state=1,
                create_time=datetime.utcnow()
            )
            db.session.add(payment)
            db.session.commit()
            print(f"DEBUG: Created new payment: {payment}", flush=True)
        
        return jsonify({
            "result": {
                "create_time": int(payment.create_time.timestamp() * 1000),
                "transaction": str(payment.id),
                "state": 1
            }
        })
        
    elif method == 'PerformTransaction':
        transaction_id = params.get('id')
        
        # Находим платёж по transaction_id
        payment = Payment.query.filter_by(transaction_id=transaction_id).first()
        
        if not payment:
            return jsonify({
                "id": id,
                "error": {"code": -32504, "message": "Transaction not found"}
            })
        
        # Обновляем статус на success
        payment.status = 'success'
        payment.state = 2
        payment.perform_time = datetime.utcnow()
        db.session.commit()
        
        print(f"DEBUG: Payment success for order_id={payment.order_id}", flush=True)
        
        return jsonify({
            "result": {
                "transaction": str(payment.id),
                "perform_time": int(payment.perform_time.timestamp() * 1000),
                "state": 2
            }
        })
        
    elif method == 'CancelTransaction':
        transaction_id = params.get('id')
        
        # Находим и отменяем платёж
        payment = Payment.query.filter_by(transaction_id=transaction_id).first()
        
        if payment:
            payment.status = 'canceled'
            payment.state = -2
            payment.cancel_time = datetime.utcnow()
            db.session.commit()
            print(f"DEBUG: Payment canceled: {payment}", flush=True)
        
        return jsonify({
            "result": {
                "transaction": str(payment.id) if payment else transaction_id,
                "cancel_time": int(payment.cancel_time.timestamp() * 1000) if payment and payment.cancel_time else int(datetime.utcnow().timestamp() * 1000),
                "state": -2
            }
        })
        
    elif method == 'CheckTransaction':
        transaction_id = params.get('id')
        
        # Находим платёж
        payment = Payment.query.filter_by(transaction_id=transaction_id).first()
        
        if not payment:
            return jsonify({
                "id": id,
                "error": {"code": -32504, "message": "Transaction not found"}
            })
        
        status_map = {"pending": 1, "success": 2, "canceled": -2, "failed": -1}
        state = status_map.get(payment.status, 1)
        
        return jsonify({
            "result": {
                "create_time": int(payment.create_time.timestamp() * 1000) if payment.create_time else 0,
                "perform_time": int(payment.perform_time.timestamp() * 1000) if payment.perform_time else 0,
                "cancel_time": int(payment.cancel_time.timestamp() * 1000) if payment.cancel_time else 0,
                "transaction": str(payment.id),
                "state": state,
                "reason": None
            }
        })
        
    elif method == 'GetStatement':
        from_ts = params.get('from')
        to_ts = params.get('to')
        print(f"DEBUG: GetStatement from={from_ts}, to={to_ts}", flush=True)
        
        from_dt = datetime.fromtimestamp(from_ts / 1000) if from_ts else None
        to_dt = datetime.fromtimestamp(to_ts / 1000) if to_ts else None
        
        query = Payment.query
        if from_dt:
            query = query.filter(Payment.create_time >= from_dt)
        if to_dt:
            query = query.filter(Payment.create_time <= to_dt)
        
        payments = query.order_by(Payment.create_time.desc()).all()
        
        statement = []
        for p in payments:
            statement.append({
                "id": p.state or 1,
                "amount": p.amount * 100,
                "account": {
                    "order_id": p.order_id
                },
                "create_time": int(p.create_time.timestamp() * 1000) if p.create_time else 0,
                "perform_time": int(p.perform_time.timestamp() * 1000) if p.perform_time else 0,
                "cancel_time": int(p.cancel_time.timestamp() * 1000) if p.cancel_time else 0,
                "transaction": str(p.id),
                "state": {"pending": 1, "success": 2, "canceled": -2, "failed": -1}.get(p.status, 1),
                "reason": None
            })
        
        print(f"DEBUG: GetStatement result count={len(statement)}", flush=True)
        return jsonify({
            "result": {
                "transactions": statement
            }
        })
    
    else:
        print(f"DEBUG: Unknown method: {method}", flush=True)
        return jsonify({"error": {"code": -32601, "message": "Unknown method"}})

@app.route('/api/click/prepare', methods=['POST'])
def click_prepare():
    """Click prepare endpoint"""
    data = request.form if request.form else request.json
    print(f"DEBUG: click_prepare data={data}", flush=True)
    
    click_trans_id = data.get('click_trans_id')
    service_id = data.get('service_id')
    merchant_trans_id = data.get('merchant_trans_id')  # это наш order_id
    amount = data.get('amount')
    
    print(f"DEBUG: Searching for order_id={merchant_trans_id}, amount={amount}", flush=True)
    
    # Проверка обязательных параметров
    if not merchant_trans_id or not amount:
        print(f"DEBUG: ERROR - Missing required parameters: merchant_trans_id={merchant_trans_id}, amount={amount}", flush=True)
        return jsonify({
            "error": -8,
            "error_note": "Missing required parameters",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_prepare_id": None
        })
    
    # Проверка service_id
    if service_id and str(service_id) != CLICK_SERVICE_ID:
        print(f"DEBUG: ERROR - Invalid service_id: {service_id}, expected: {CLICK_SERVICE_ID}", flush=True)
        return jsonify({
            "error": -5,
            "error_note": "Invalid service_id",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_prepare_id": None
        })
    
    # Проверяем существование заказа по order_id (должен быть создан при генерации QR)
    # ИЗМЕНЕНО: Сначала ищем с точным payment_type, затем без него
    payment = Payment.query.filter_by(order_id=merchant_trans_id, payment_type='click').first()
    
    if not payment:
        # Попробуем найти без проверки payment_type (возможно был создан с другим типом)
        payment = Payment.query.filter_by(order_id=merchant_trans_id).first()
        
        if payment:
            print(f"DEBUG: Found payment with different type: {payment.payment_type}, updating to 'click'", flush=True)
            # Обновляем payment_type на правильный
            payment.payment_type = 'click'
            db.session.commit()
        else:
            # Заказ не найден вообще - создаём новый (защита от race condition)
            print(f"DEBUG: Order not found, creating new: {merchant_trans_id}", flush=True)
            try:
                payment = Payment(
                    order_id=merchant_trans_id,
                    transaction_id=None,  # Будет установлен ниже
                    amount=int(float(amount)),
                    payment_type='click',
                    status='pending',
                    state=0,
                    create_time=datetime.utcnow()
                )
                db.session.add(payment)
                db.session.commit()
                print(f"DEBUG: Created new payment in prepare: payment_id={payment.id}", flush=True)
            except Exception as e:
                db.session.rollback()
                print(f"DEBUG: ERROR - Failed to create payment: {e}", flush=True)
                return jsonify({
                    "error": -9,
                    "error_note": "Database error",
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                    "merchant_prepare_id": None
                })
    
    # Проверка суммы (только если payment уже существовал до этого)
    # Если мы только что создали payment с amount из запроса, проверять не нужно
    if payment.amount and int(float(amount)) != int(payment.amount):
        print(f"DEBUG: WARNING - Amount mismatch: expected={payment.amount}, got={amount}", flush=True)
        # Обновляем сумму на актуальную из Click
        payment.amount = int(float(amount))
        db.session.commit()
        print(f"DEBUG: Updated amount to {payment.amount}", flush=True)
    
    # Обновляем transaction_id и state если это первый prepare
    if not payment.transaction_id:
        try:
            payment.transaction_id = click_trans_id
            payment.state = 1  # 1 = prepare выполнен
            db.session.commit()
            print(f"DEBUG: Updated payment with transaction_id: payment_id={payment.id}, click_trans_id={click_trans_id}", flush=True)
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: ERROR - Database error: {e}", flush=True)
            return jsonify({
                "error": -9,
                "error_note": "Database error",
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "merchant_prepare_id": None
            })
    else:
        # Проверяем что transaction_id совпадает (защита от дубликатов)
        if payment.transaction_id != click_trans_id:
            print(f"DEBUG: WARNING - Transaction ID mismatch: stored={payment.transaction_id}, received={click_trans_id}", flush=True)
            # Но всё равно возвращаем success (возможно повторный prepare)
    
    print(f"DEBUG: Click prepare success: payment_id={payment.id}", flush=True)
    
    return jsonify({
        "error": 0,
        "error_note": "Success",
        "click_trans_id": click_trans_id,
        "merchant_trans_id": merchant_trans_id,
        "merchant_prepare_id": payment.id
    })

@app.route('/api/click/complete', methods=['POST'])
def click_complete():
    """Click complete endpoint"""
    data = request.form if request.form else request.json
    print(f"DEBUG: click_complete data={data}", flush=True)
    
    click_trans_id = data.get('click_trans_id')
    service_id = data.get('service_id')
    merchant_trans_id = data.get('merchant_trans_id')
    merchant_prepare_id = data.get('merchant_prepare_id')
    amount = data.get('amount')
    action = data.get('action')
    error = data.get('error')
    
    # Находим платёж по merchant_prepare_id и click_trans_id
    payment = Payment.query.filter_by(
        id=merchant_prepare_id,
        transaction_id=click_trans_id,
        payment_type='click'
    ).first()
    
    if not payment:
        print(f"DEBUG: ERROR - Transaction not found: merchant_prepare_id={merchant_prepare_id}, click_trans_id={click_trans_id}", flush=True)
        return jsonify({
            "error": -6,
            "error_note": "Transaction not found",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": None
        })
    
    # Проверка service_id
    if service_id and str(service_id) != CLICK_SERVICE_ID:
        print(f"DEBUG: ERROR - Invalid service_id in complete: {service_id}", flush=True)
        return jsonify({
            "error": -5,
            "error_note": "Invalid service_id",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": None
        })
    
    # Проверка суммы
    if amount and int(float(amount)) != int(payment.amount):
        print(f"DEBUG: ERROR - Incorrect amount in complete: amount={amount}, payment.amount={payment.amount}", flush=True)
        return jsonify({
            "error": -2,
            "error_note": "Incorrect amount",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": None
        })
    
    # Проверка на ошибку от Click
    if error and str(error) != "0":
        print(f"DEBUG: Click error received: error={error}", flush=True)
        payment.status = 'failed'
        payment.state = -1
        payment.cancel_time = datetime.utcnow()
        db.session.commit()
        return jsonify({
            "error": -9,
            "error_note": "Payment failed on Click side",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": payment.id
        })
    
    # Action = 0 означает отмена
    if str(action) == "0":
        print(f"DEBUG: Transaction canceled: payment_id={payment.id}", flush=True)
        payment.status = 'canceled'
        payment.state = -2
        payment.cancel_time = datetime.utcnow()
        db.session.commit()
        return jsonify({
            "error": 0,
            "error_note": "Canceled",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": payment.id
        })
    
    # Action = 1 означает успешная оплата
    if str(action) == "1":
        # Проверяем что платёж не был уже выполнен
        if payment.status == 'success':
            print(f"DEBUG: Payment already completed: {payment.id}", flush=True)
            return jsonify({
                "error": 0,
                "error_note": "Already paid",
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "merchant_confirm_id": payment.id
            })
        
        # Обновляем статус на success
        payment.status = 'success'
        payment.state = 2
        payment.perform_time = datetime.utcnow()
        db.session.commit()
        
        print(f"DEBUG: Payment success for order_id={payment.order_id}", flush=True)
        
        return jsonify({
            "error": 0,
            "error_note": "Success",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": payment.id
        })
    
    # Неизвестное действие
    print(f"DEBUG: ERROR - Invalid action: action={action}", flush=True)
    return jsonify({
        "error": -3,
        "error_note": "Invalid action",
        "click_trans_id": click_trans_id,
        "merchant_trans_id": merchant_trans_id,
        "merchant_confirm_id": None
    })

@app.route('/api/test-payment/<order_id>', methods=['POST'])
def test_payment(order_id):
    """Тестовый endpoint для имитации успешной оплаты (только для разработки!)"""
    # Ищем существующий платёж или создаём новый
    payment = Payment.query.filter_by(order_id=order_id).first()
    
    if not payment:
        payment = Payment(
            order_id=order_id,
            transaction_id=f'test-{order_id}',
            amount=10000,
            payment_type='test',
            status='success',
            create_time=datetime.utcnow(),
            perform_time=datetime.utcnow()
        )
        db.session.add(payment)
    else:
        payment.status = 'success'
        payment.perform_time = datetime.utcnow()
    
    db.session.commit()
    
    print(f"DEBUG: Test payment success for order_id={order_id}", flush=True)
    return jsonify({'status': 'ok', 'message': 'Payment simulated successfully', 'payment': payment.to_dict()})

@app.route('/api/payments', methods=['GET'])
def get_all_payments():
    """Получить все платежи (для админки/статистики)"""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    status = request.args.get('status')  # pending, success, canceled
    
    query = Payment.query
    
    if status:
        query = query.filter_by(status=status)
    
    total = query.count()
    payments = query.order_by(Payment.created_at.desc()).limit(limit).offset(offset).all()
    
    return jsonify({
        'total': total,
        'limit': limit,
        'offset': offset,
        'payments': [p.to_dict() for p in payments]
    })

@app.route('/api/payments/<int:payment_id>', methods=['GET'])
def get_payment_by_id(payment_id):
    """Получить платёж по ID"""
    payment = Payment.query.get_or_404(payment_id)
    return jsonify(payment.to_dict())

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Статистика платежей"""
    total_payments = Payment.query.count()
    success_payments = Payment.query.filter_by(status='success').count()
    pending_payments = Payment.query.filter_by(status='pending').count()
    canceled_payments = Payment.query.filter_by(status='canceled').count()
    
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='success').scalar() or 0
    
    return jsonify({
        'total_payments': total_payments,
        'success_payments': success_payments,
        'pending_payments': pending_payments,
        'canceled_payments': canceled_payments,
        'total_revenue': total_revenue
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 ЗАПУСК СИСТЕМЫ PHOTOBOOTH")
    print("=" * 60)
    print()
    print("✅ Flask API: http://localhost:5000")
    print("✅ Test endpoint: http://localhost:5000/api/test")
    print()
    
    # Запуск Telegram бота в отдельном потоке
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE':
        print("🤖 Запуск Telegram бота...")
        
        def run_telegram_bot():
            try:
                from telegram_bot import bot
                print("✅ Telegram Bot запущен!")
                print(f"   Bot Token: {BOT_TOKEN[:10]}...")
                print()
                bot.infinity_polling()
            except Exception as e:
                print(f"❌ Ошибка Telegram бота: {e}")
        
        # Запускаем бота в отдельном потоке
        bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
        bot_thread.start()
    else:
        print("⚠️  Telegram бот НЕ запущен (токен не установлен)")
        print("   Установите: set TELEGRAM_BOT_TOKEN=ваш_токен")
        print()
    
    print("=" * 60)
    print("Система готова к работе!")
    print("Нажмите Ctrl+C для остановки")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
