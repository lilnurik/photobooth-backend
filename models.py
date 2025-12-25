from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Payment(db.Model):
    """Модель для хранения информации о платежах"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    transaction_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    amount = db.Column(db.Integer, nullable=False)  # в сумах
    payment_type = db.Column(db.String(20), nullable=False)  # payme, click, test
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, success, canceled, failed
    state = db.Column(db.Integer, nullable=True)  # для Payme: 1=pending, 2=success, -2=canceled
    
    # Временные метки
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    perform_time = db.Column(db.DateTime, nullable=True)
    cancel_time = db.Column(db.DateTime, nullable=True)
    
    # Дополнительная информация
    metadata_json = db.Column(db.Text, nullable=True)  # для хранения любой доп. информации
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payment {self.order_id} - {self.status}>'
    
    def to_dict(self):
        """Преобразование в словарь для JSON ответа"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'transaction_id': self.transaction_id,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'status': self.status,
            'state': self.state,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'perform_time': self.perform_time.isoformat() if self.perform_time else None,
            'cancel_time': self.cancel_time.isoformat() if self.cancel_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Photo(db.Model):
    """Модель для хранения информации о сделанных фото (опционально)"""
    __tablename__ = 'photos'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    template_name = db.Column(db.String(50), nullable=False)  # format_1, format_2, etc
    copy_count = db.Column(db.Integer, nullable=False, default=1)
    composite_path = db.Column(db.String(255), nullable=True)  # путь к готовому фото
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связь с платежом
    payment = db.relationship('Payment', backref=db.backref('photos', lazy=True))
    
    def __repr__(self):
        return f'<Photo {self.id} - {self.template_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'template_name': self.template_name,
            'copy_count': self.copy_count,
            'composite_path': self.composite_path,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================
# МОДЕЛИ ДЛЯ TELEGRAM БОТА И СЕССИЙ
# ============================================

class Session(db.Model):
    """Сессия для работы с Telegram ботом
    
    Каждая сессия представляет одно взаимодействие:
    - upload: пользователь загружает фото через бота
    - download: пользователь скачивает готовые фото
    """
    __tablename__ = 'sessions'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    kiosk_id = db.Column(db.Integer)  # ID фотобудки (для multi-kiosk setup)
    type = db.Column(db.String(20), nullable=False)  # 'upload' или 'download'
    status = db.Column(db.String(20), default='pending')  # pending, ready, completed, expired
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)  # Через 30 минут
    completed_at = db.Column(db.DateTime)
    
    telegram_user_id = db.Column(db.BigInteger)  # ID пользователя Telegram
    telegram_username = db.Column(db.String(100))  # Username Telegram
    
    data = db.Column(db.Text)  # JSON данные (дополнительная информация)
    
    # Relationships
    photos = db.relationship('SessionPhoto', backref='session', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Session {self.id} - {self.type} - {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'kiosk_id': self.kiosk_id,
            'type': self.type,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'telegram_user_id': self.telegram_user_id,
            'telegram_username': self.telegram_username,
            'data': json.loads(self.data) if self.data else None,
            'photos_count': self.photos.count()
        }
    
    @property
    def is_expired(self):
        """Проверка истекла ли сессия"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def photo_list(self):
        """Получить список фото сессии"""
        return [photo.to_dict() for photo in self.photos.all()]


class SessionPhoto(db.Model):
    """Фотографии связанные с сессией
    
    Хранит как загруженные пользователем фото (type='uploaded'),
    так и готовые обработанные фото (type='result')
    """
    __tablename__ = 'session_photos'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.id'), nullable=False)
    
    photo_type = db.Column(db.String(20), nullable=False)  # 'uploaded' или 'result'
    photo_path = db.Column(db.String(500))  # Путь к файлу на диске
    photo_data = db.Column(db.Text)  # Base64 данные (опционально)
    
    telegram_file_id = db.Column(db.String(200))  # File ID из Telegram
    telegram_file_size = db.Column(db.Integer)  # Размер файла
    
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Метаданные
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    order_index = db.Column(db.Integer, default=0)  # Порядок фото в сессии
    
    def __repr__(self):
        return f'<SessionPhoto {self.id} - {self.photo_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'photo_type': self.photo_type,
            'photo_path': self.photo_path,
            'photo_data': self.photo_data if self.photo_data else None,
            'telegram_file_id': self.telegram_file_id,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'width': self.width,
            'height': self.height,
            'order_index': self.order_index
        }