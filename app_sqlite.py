from flask import Flask, jsonify, request
from flask_cors import CORS
import io, base64, qrcode
from datetime import datetime
import json
import os

from models import db, Payment, Photo

app = Flask(__name__)
CORS(app, origins=['http://localhost:5173'], supports_credentials=True)

# Конфигурация базы данных SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "photobooth.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация БД
db.init_app(app)

# Конфигурация для Payme и Click
PAYME_MERCHANT_ID = '68413113d629feb59d31ec2d'
CLICK_MERCHANT_ID = '29137'
CLICK_SERVICE_ID = '75063'

# Создание таблиц при первом запуске
with app.app_context():
    db.create_all()
    print("Database tables created successfully!", flush=True)

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
    
    if payment_type == 'payme':
        amount_tiyin = int(float(amount) * 100)
        payme_str = f"m={PAYME_MERCHANT_ID};ac.order_id={order_id};a={amount_tiyin}"
        payme_b64 = base64.b64encode(payme_str.encode()).decode()
        payme_url = f"https://checkout.paycom.uz/{payme_b64}"
        
        print(f"DEBUG: payme_url={payme_url}", flush=True)
        
        img = qrcode.make(payme_url)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_b64 = 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({'qrCode': qr_b64, 'paymeUrl': payme_url})
        
    elif payment_type == 'click':
        amount_str = "{:.2f}".format(float(amount))
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
    """Webhook для обработки уведомлений от Payme"""
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
    merchant_trans_id = data.get('merchant_trans_id')  # это наш order_id
    amount = data.get('amount')
    
    if not merchant_trans_id or not amount:
        return jsonify({
            "error": -8,
            "error_note": "Missing required parameters",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_prepare_id": None
        })
    
    # Проверяем существует ли уже платёж
    payment = Payment.query.filter_by(order_id=merchant_trans_id).first()
    
    if not payment:
        # Создаём новый платёж
        payment = Payment(
            order_id=merchant_trans_id,
            transaction_id=click_trans_id,
            amount=int(float(amount)),
            payment_type='click',
            status='pending',
            create_time=datetime.utcnow()
        )
        db.session.add(payment)
        db.session.commit()
        print(f"DEBUG: Created new Click payment: {payment}", flush=True)
    
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
    merchant_trans_id = data.get('merchant_trans_id')
    merchant_prepare_id = data.get('merchant_prepare_id')
    action = data.get('action')
    
    # Находим платёж
    payment = Payment.query.filter_by(id=merchant_prepare_id).first()
    
    if not payment:
        return jsonify({
            "error": -6,
            "error_note": "Transaction not found",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": None
        })
    
    if str(action) == "0":
        # Отменить
        payment.status = 'canceled'
        payment.cancel_time = datetime.utcnow()
        db.session.commit()
        print(f"DEBUG: Payment canceled: {payment}", flush=True)
        
        return jsonify({
            "error": 0,
            "error_note": "Canceled",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": payment.id
        })
    
    if str(action) == "1":
        # Успешно
        if payment.status == 'success':
            return jsonify({
                "error": 0,
                "error_note": "Already paid",
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "merchant_confirm_id": payment.id
            })
        
        payment.status = 'success'
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
    print("Starting Photobooth Payment API with SQLite on port 5000", flush=True)
    print("Database file: photobooth.db", flush=True)
    print("Test endpoint available: POST /api/test-payment/<order_id>", flush=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
