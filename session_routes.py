"""
Endpoints для работы с сессиями Telegram бота
"""
from flask import jsonify, request
from datetime import datetime, timedelta
from models import db, Session, SessionPhoto
import uuid
import json
import base64
import os


def init_session_routes(app):
    """Инициализация роутов для сессий"""
    
    # ============================================
    # СОЗДАНИЕ СЕССИИ
    # ============================================
    
    @app.route('/api/session/create', methods=['POST'])
    def create_session():
        """Создать новую сессию
        
        Body:
        {
            "type": "upload" | "download",
            "kiosk_id": 1 (опционально),
            "data": {} (опционально)
        }
        """
        data = request.get_json()
        
        session_type = data.get('type')
        if session_type not in ['upload', 'download']:
            return jsonify({'error': 'Invalid type. Must be "upload" or "download"'}), 400
        
        # Генерируем уникальный ID
        session_id = str(uuid.uuid4())
        
        # Сессия истекает через 30 минут
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        
        session = Session(
            id=session_id,
            kiosk_id=data.get('kiosk_id'),
            type=session_type,
            status='pending',
            expires_at=expires_at,
            data=json.dumps(data.get('data', {}))
        )
        
        db.session.add(session)
        db.session.commit()
        
        print(f"✅ Session created: {session_id} ({session_type})", flush=True)
        
        return jsonify({
            'success': True,
            'session': session.to_dict()
        }), 201
    
    # ============================================
    # ПОЛУЧЕНИЕ СЕССИИ
    # ============================================
    
    @app.route('/api/session/<session_id>', methods=['GET'])
    def get_session(session_id):
        """Получить данные сессии"""
        session = Session.query.get(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if session.is_expired:
            return jsonify({'error': 'Session expired'}), 410
        
        return jsonify(session.to_dict())
    
    # ============================================
    # ОБНОВЛЕНИЕ СЕССИИ
    # ============================================
    
    @app.route('/api/session/<session_id>', methods=['PUT'])
    def update_session(session_id):
        """Обновить данные сессии
        
        Body:
        {
            "status": "ready" | "completed",
            "telegram_user_id": 123456,
            "telegram_username": "user123",
            "data": {}
        }
        """
        session = Session.query.get(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if session.is_expired:
            return jsonify({'error': 'Session expired'}), 410
        
        data = request.get_json()
        
        if 'status' in data:
            session.status = data['status']
            if data['status'] == 'completed':
                session.completed_at = datetime.utcnow()
        
        if 'telegram_user_id' in data:
            session.telegram_user_id = data['telegram_user_id']
        
        if 'telegram_username' in data:
            session.telegram_username = data['telegram_username']
        
        if 'data' in data:
            session.data = json.dumps(data['data'])
        
        db.session.commit()
        
        print(f"✅ Session updated: {session_id}", flush=True)
        
        return jsonify(session.to_dict())
    
    # ============================================
    # УДАЛЕНИЕ СЕССИИ
    # ============================================
    
    @app.route('/api/session/<session_id>', methods=['DELETE'])
    def delete_session(session_id):
        """Удалить сессию и все связанные фото"""
        session = Session.query.get(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        db.session.delete(session)
        db.session.commit()
        
        print(f"✅ Session deleted: {session_id}", flush=True)
        
        return jsonify({'success': True, 'message': 'Session deleted'})
    
    # ============================================
    # РАБОТА С ФОТОГРАФИЯМИ
    # ============================================
    
    @app.route('/api/session/<session_id>/photos', methods=['POST'])
    def add_session_photo(session_id):
        """Добавить фото в сессию (от Telegram бота)
        
        Body:
        {
            "photo_type": "uploaded" | "result",
            "photo_data": "base64_string" (опционально),
            "telegram_file_id": "file_id" (опционально),
            "telegram_file_size": 123456,
            "width": 1920,
            "height": 1080,
            "order_index": 0
        }
        """
        session = Session.query.get(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if session.is_expired:
            return jsonify({'error': 'Session expired'}), 410
        
        data = request.get_json()
        
        # Проверка лимита фото (макс 5 uploaded фото)
        if data.get('photo_type') == 'uploaded':
            uploaded_count = session.photos.filter_by(photo_type='uploaded').count()
            if uploaded_count >= 5:
                return jsonify({'error': 'Maximum 5 photos allowed'}), 400
        
        # Создаём фото
        photo = SessionPhoto(
            session_id=session_id,
            photo_type=data.get('photo_type', 'uploaded'),
            photo_data=data.get('photo_data'),
            telegram_file_id=data.get('telegram_file_id'),
            telegram_file_size=data.get('telegram_file_size'),
            width=data.get('width'),
            height=data.get('height'),
            order_index=data.get('order_index', 0)
        )
        
        db.session.add(photo)
        
        # Если загружены все фото (например, 3), ставим статус ready
        uploaded_count = session.photos.filter_by(photo_type='uploaded').count()
        if data.get('photo_type') == 'uploaded' and uploaded_count + 1 >= 3:
            session.status = 'ready'
        
        db.session.commit()
        
        print(f"✅ Photo added to session {session_id}: {photo.id}", flush=True)
        
        return jsonify({
            'success': True,
            'photo': photo.to_dict(),
            'session': session.to_dict()
        }), 201
    
    @app.route('/api/session/<session_id>/photos', methods=['GET'])
    def get_session_photos(session_id):
        """Получить все фото сессии"""
        session = Session.query.get(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if session.is_expired:
            return jsonify({'error': 'Session expired'}), 410
        
        photo_type = request.args.get('type')  # uploaded или result
        
        if photo_type:
            photos = session.photos.filter_by(photo_type=photo_type).order_by(SessionPhoto.order_index).all()
        else:
            photos = session.photos.order_by(SessionPhoto.order_index).all()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'photos': [photo.to_dict() for photo in photos]
        })
    
    @app.route('/api/session/<session_id>/result', methods=['POST'])
    def save_result_photo(session_id):
        """Сохранить готовое фото (от фотобудки)
        
        Body:
        {
            "photo_data": "base64_string",
            "width": 1920,
            "height": 1080
        }
        """
        session = Session.query.get(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if session.is_expired:
            return jsonify({'error': 'Session expired'}), 410
        
        data = request.get_json()
        
        photo = SessionPhoto(
            session_id=session_id,
            photo_type='result',
            photo_data=data.get('photo_data'),
            width=data.get('width'),
            height=data.get('height'),
            order_index=0
        )
        
        db.session.add(photo)
        session.status = 'ready'  # Готово к скачиванию
        db.session.commit()
        
        print(f"✅ Result photo saved for session {session_id}", flush=True)
        
        return jsonify({
            'success': True,
            'photo': photo.to_dict()
        }), 201
    
    @app.route('/api/session/<session_id>/result', methods=['GET'])
    def get_result_photo(session_id):
        """Получить готовое фото"""
        session = Session.query.get(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if session.is_expired:
            return jsonify({'error': 'Session expired'}), 410
        
        result_photo = session.photos.filter_by(photo_type='result').first()
        
        if not result_photo:
            return jsonify({'error': 'Result photo not found'}), 404
        
        return jsonify(result_photo.to_dict())
    
    # ============================================
    # УТИЛИТЫ
    # ============================================
    
    @app.route('/api/sessions/cleanup', methods=['POST'])
    def cleanup_expired_sessions():
        """Очистка истёкших сессий (можно вызывать по cron)"""
        expired = Session.query.filter(Session.expires_at < datetime.utcnow()).all()
        
        count = len(expired)
        for session in expired:
            db.session.delete(session)
        
        db.session.commit()
        
        print(f"✅ Cleaned up {count} expired sessions", flush=True)
        
        return jsonify({
            'success': True,
            'deleted_count': count
        })
    
    @app.route('/api/sessions/list', methods=['GET'])
    def list_sessions():
        """Получить список всех активных сессий (для дебага)"""
        sessions = Session.query.filter(Session.expires_at > datetime.utcnow()).all()
        
        return jsonify({
            'success': True,
            'count': len(sessions),
            'sessions': [session.to_dict() for session in sessions]
        })
    
    print("✅ Session routes initialized!", flush=True)
