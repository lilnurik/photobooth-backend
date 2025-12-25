from flask import Flask, jsonify, request
from flask_cors import CORS
import io, base64, qrcode
from datetime import datetime
import json

app = Flask(__name__)
CORS(app, origins=['http://localhost:5173'], supports_credentials=True)

# Конфигурация для Payme и Click
PAYME_MERCHANT_ID = '68413113d629feb59d31ec2d'
CLICK_MERCHANT_ID = '29137'
CLICK_SERVICE_ID = '75063'

# Простое хранилище платежей в памяти (для продакшена использовать БД)
payments = {}

@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'status': 'OK', 'message': 'Photobooth payment API working'})

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    data = request.get_json()
    print(f"DEBUG: generate_qr data={data}", flush=True)
    
    order_id = data.get('order_id')  # уникальный ID заказа
    payment_type = data.get('paymentType')  # 'payme' или 'click'
    amount = data.get('amount')  # сумма в сумах
    
    print(f"DEBUG: order_id={order_id}, payment_type={payment_type}, amount={amount}", flush=True)
    
    if payment_type == 'payme':
        # Payme требует сумму в тийинах (1 сум = 100 тийин)
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
    """Проверка статуса платежа"""
    payment = payments.get(order_id)
    if payment:
        return jsonify(payment)
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
        
        # Сохраняем транзакцию
        payments[order_id] = {
            'transaction_id': transaction_id,
            'amount': amount // 100,  # конвертируем тийины в сумы
            'status': 'pending',
            'create_time': datetime.now().isoformat(),
            'payment_type': 'payme'
        }
        
        return jsonify({
            "result": {
                "create_time": int(datetime.now().timestamp() * 1000),
                "transaction": transaction_id,
                "state": 1
            }
        })
        
    elif method == 'PerformTransaction':
        transaction_id = params.get('id')
        
        # Находим платёж по transaction_id
        order_id = None
        for oid, payment in payments.items():
            if payment.get('transaction_id') == transaction_id:
                order_id = oid
                break
                
        if not order_id:
            return jsonify({
                "id": id,
                "error": {"code": -32504, "message": "Transaction not found"}
            })
            
        # Обновляем статус на success
        payments[order_id]['status'] = 'success'
        payments[order_id]['perform_time'] = datetime.now().isoformat()
        
        print(f"DEBUG: Payment success for order_id={order_id}", flush=True)
        
        return jsonify({
            "result": {
                "transaction": transaction_id,
                "perform_time": int(datetime.now().timestamp() * 1000),
                "state": 2
            }
        })
        
    elif method == 'CancelTransaction':
        transaction_id = params.get('id')
        
        # Находим и отменяем платёж
        for oid, payment in payments.items():
            if payment.get('transaction_id') == transaction_id:
                payments[oid]['status'] = 'canceled'
                payments[oid]['cancel_time'] = datetime.now().isoformat()
                break
                
        return jsonify({
            "result": {
                "transaction": transaction_id,
                "cancel_time": int(datetime.now().timestamp() * 1000),
                "state": -2
            }
        })
        
    elif method == 'CheckTransaction':
        transaction_id = params.get('id')
        
        # Находим платёж
        for oid, payment in payments.items():
            if payment.get('transaction_id') == transaction_id:
                status_map = {"pending": 1, "success": 2, "canceled": -2}
                state = status_map.get(payment['status'], 1)
                
                return jsonify({
                    "result": {
                        "create_time": int(datetime.fromisoformat(payment.get('create_time', datetime.now().isoformat())).timestamp() * 1000),
                        "perform_time": int(datetime.fromisoformat(payment.get('perform_time', datetime.now().isoformat())).timestamp() * 1000) if payment.get('perform_time') else 0,
                        "cancel_time": int(datetime.fromisoformat(payment.get('cancel_time', datetime.now().isoformat())).timestamp() * 1000) if payment.get('cancel_time') else 0,
                        "transaction": transaction_id,
                        "state": state,
                        "reason": None
                    }
                })
                
        return jsonify({
            "id": id,
            "error": {"code": -32504, "message": "Transaction not found"}
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
        
    # Сохраняем транзакцию
    payments[merchant_trans_id] = {
        'transaction_id': click_trans_id,
        'amount': int(float(amount)),
        'status': 'pending',
        'create_time': datetime.now().isoformat(),
        'payment_type': 'click'
    }
    
    return jsonify({
        "error": 0,
        "error_note": "Success",
        "click_trans_id": click_trans_id,
        "merchant_trans_id": merchant_trans_id,
        "merchant_prepare_id": merchant_trans_id
    })

@app.route('/api/click/complete', methods=['POST'])
def click_complete():
    """Click complete endpoint"""
    data = request.form if request.form else request.json
    print(f"DEBUG: click_complete data={data}", flush=True)
    
    click_trans_id = data.get('click_trans_id')
    merchant_trans_id = data.get('merchant_trans_id')
    action = data.get('action')
    
    if merchant_trans_id not in payments:
        return jsonify({
            "error": -6,
            "error_note": "Transaction not found",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": None
        })
        
    if str(action) == "0":
        # Отменить
        payments[merchant_trans_id]['status'] = 'canceled'
        payments[merchant_trans_id]['cancel_time'] = datetime.now().isoformat()
        return jsonify({
            "error": 0,
            "error_note": "Canceled",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": merchant_trans_id
        })
        
    if str(action) == "1":
        # Успешно
        payments[merchant_trans_id]['status'] = 'success'
        payments[merchant_trans_id]['perform_time'] = datetime.now().isoformat()
        
        print(f"DEBUG: Payment success for order_id={merchant_trans_id}", flush=True)
        
        return jsonify({
            "error": 0,
            "error_note": "Success",
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": merchant_trans_id
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
    payments[order_id] = {
        'status': 'success',
        'amount': 10000,
        'payment_type': 'test',
        'create_time': datetime.now().isoformat(),
        'perform_time': datetime.now().isoformat()
    }
    print(f"DEBUG: Test payment success for order_id={order_id}", flush=True)
    return jsonify({'status': 'ok', 'message': 'Payment simulated successfully'})

if __name__ == '__main__':
    print("Starting Photobooth Payment API on port 5000", flush=True)
    print("Test endpoint available: POST /api/test-payment/<order_id>", flush=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
