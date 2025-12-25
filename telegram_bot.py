"""
Telegram бот для фотобудки
Поддерживает загрузку и скачивание фото через сессии
"""

import telebot
from telebot import types
import requests
import os
import base64
from io import BytesIO
from PIL import Image

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8565934485:AAELT16NMIp12QX_C7bzN7vXt63NX4ITraU')
API_URL = os.getenv('API_URL', 'http://localhost:5000/api')

bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище для отслеживания сессий пользователей
user_sessions = {}  # {user_id: session_id}

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_session(session_id):
    """Получить данные сессии из API"""
    try:
        response = requests.get(f"{API_URL}/session/{session_id}")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error getting session: {e}")
        return None

def update_session(session_id, data):
    """Обновить данные сессии"""
    try:
        response = requests.put(f"{API_URL}/session/{session_id}", json=data)
        return response.status_code == 200
    except Exception as e:
        print(f"Error updating session: {e}")
        return False

def add_photo_to_session(session_id, photo_data):
    """Добавить фото в сессию"""
    try:
        response = requests.post(f"{API_URL}/session/{session_id}/photos", json=photo_data)
        return response.status_code == 201
    except Exception as e:
        print(f"Error adding photo: {e}")
        return False

def get_session_photos(session_id, photo_type='result'):
    """Получить фото из сессии"""
    try:
        response = requests.get(f"{API_URL}/session/{session_id}/photos?type={photo_type}")
        if response.status_code == 200:
            return response.json().get('photos', [])
        return []
    except Exception as e:
        print(f"Error getting photos: {e}")
        return []

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработка команды /start
    
    Формат: /start upload_SESSION_ID или /start download_SESSION_ID
    """
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    
    # Парсим параметр команды
    command_parts = message.text.split('_', 1)
    
    if len(command_parts) < 2:
        # Обычный старт без параметров
        bot.send_message(
            message.chat.id,
            "👋 Добро пожаловать в Sony Photobooth Bot!\n\n"
            "Этот бот помогает:\n"
            "📤 Загружать ваши фото для печати\n"
            "📥 Скачивать готовые фото с фотобудки\n\n"
            "Отсканируйте QR код на фотобудке для начала работы."
        )
        return
    
    # Парсим тип и session_id
    session_type = command_parts[0].replace('/start ', '')
    session_id = command_parts[1]
    
    # Проверяем существование сессии
    session_data = get_session(session_id)
    
    if not session_data:
        bot.send_message(
            message.chat.id,
            "❌ Сессия не найдена или истекла.\n\n"
            "Пожалуйста, отсканируйте QR код заново."
        )
        return
    
    # Проверяем что сессия не истекла
    if session_data.get('status') == 'expired':
        bot.send_message(
            message.chat.id,
            "⏰ Сессия истекла (прошло более 30 минут).\n\n"
            "Пожалуйста, создайте новую сессию на фотобудке."
        )
        return
    
    # Сохраняем связь пользователь-сессия
    user_sessions[user_id] = session_id
    
    # Обновляем информацию о пользователе в сессии
    update_session(session_id, {
        'telegram_user_id': user_id,
        'telegram_username': username
    })
    
    # Разные сценарии для upload и download
    if session_type == 'upload':
        handle_upload_start(message, session_id)
    elif session_type == 'download':
        handle_download_start(message, session_id)
    else:
        bot.send_message(
            message.chat.id,
            "❌ Неизвестный тип сессии. Отсканируйте QR код заново."
        )

def handle_upload_start(message, session_id):
    """Начало загрузки фото"""
    bot.send_message(
        message.chat.id,
        "📤 *Загрузка ваших фото*\n\n"
        "Отправьте мне *3 фотографии* которые вы хотите напечатать.\n\n"
        "💡 *Можете отправить:*\n"
        "  • 📷 Как обычное фото (быстро)\n"
        "  • 📎 Как файл (лучшее качество)\n\n"
        "📸 Форматы: JPG, PNG, HEIC\n"
        "📏 Макс размер: 4096px\n\n"
        "Просто отправьте фото - я пойму как их обработать!",
        parse_mode='Markdown'
    )
    
    print(f"✅ Upload session started: {session_id} for user {message.from_user.id}")

def handle_download_start(message, session_id):
    """Начало скачивания фото"""
    bot.send_message(
        message.chat.id,
        "📥 *Скачивание готовых фото*\n\n"
        "Подождите немного, загружаю ваши фотографии в высоком качестве...",
        parse_mode='Markdown'
    )
    
    # Получаем готовые фото из сессии
    photos = get_session_photos(session_id, 'result')
    
    if not photos:
        bot.send_message(
            message.chat.id,
            "❌ Готовые фото ещё не доступны.\n\n"
            "Пожалуйста, подождите пока фотобудка обработает изображения."
        )
        return
    
    # Отправляем каждое фото КАК ДОКУМЕНТ (без сжатия!)
    for idx, photo in enumerate(photos):
        try:
            # Декодируем base64 в изображение
            photo_data = photo.get('photo_data')
            if photo_data:
                # Убираем prefix если есть (data:image/jpeg;base64,)
                if ',' in photo_data:
                    photo_data = photo_data.split(',')[1]
                
                image_bytes = base64.b64decode(photo_data)
                
                # Отправляем КАК ДОКУМЕНТ для максимального качества!
                bot.send_document(
                    message.chat.id,
                    document=image_bytes,
                    visible_file_name=f'photobooth_photo_{idx + 1}.jpg',
                    caption=f"📷 Фото {idx + 1}/{len(photos)} в высоком качестве!"
                )
        except Exception as e:
            print(f"Error sending photo: {e}")
            bot.send_message(
                message.chat.id,
                f"❌ Ошибка при отправке фото {idx + 1}"
            )
    
    bot.send_message(
        message.chat.id,
        "✅ *Все фото отправлены!*\n\n"
        "💾 Фото сохранены в лучшем качестве!\n"
        "📱 Найдите их в разделе \"Файлы\" или \"Загрузки\"\n\n"
        "Спасибо что воспользовались Sony Photobooth! 🎉",
        parse_mode='Markdown'
    )
    
    # Отмечаем сессию как завершённую
    update_session(session_id, {'status': 'completed'})
    
    print(f"✅ Download completed: {session_id} for user {message.from_user.id}")

# ============================================
# ОБРАБОТЧИК ФОТОГРАФИЙ
# ============================================

@bot.message_handler(content_types=['photo', 'document'])
def handle_photo_or_document(message):
    """Обработка фото и документов (файлов)"""
    user_id = message.from_user.id
    
    # Проверяем есть ли активная сессия у пользователя
    session_id = user_sessions.get(user_id)
    
    if not session_id:
        bot.send_message(
            message.chat.id,
            "❌ У вас нет активной сессии.\n\n"
            "Отсканируйте QR код на фотобудке для загрузки фото."
        )
        return
    
    # Получаем данные сессии
    session_data = get_session(session_id)
    
    if not session_data:
        bot.send_message(
            message.chat.id,
            "❌ Сессия не найдена или истекла.\n\n"
            "Создайте новую сессию на фотобудке."
        )
        del user_sessions[user_id]
        return
    
    # Проверяем что это upload сессия
    if session_data['type'] != 'upload':
        bot.send_message(
            message.chat.id,
            "❌ Эта сессия предназначена для скачивания, а не загрузки фото."
        )
        return
    
    # Проверяем количество уже загруженных фото
    current_photos = get_session_photos(session_id, 'uploaded')
    
    if len(current_photos) >= 5:
        bot.send_message(
            message.chat.id,
            "❌ Достигнут лимит - максимум 5 фотографий.\n\n"
            "Ваши фото уже загружены и доступны на фотобудке."
        )
        return
    
    try:
        # Определяем тип контента и получаем файл
        if message.content_type == 'photo':
            # Обычное фото (сжатое Telegram)
            photo = message.photo[-1]  # Самое большое разрешение
            file_info = bot.get_file(photo.file_id)
            file_type_emoji = "📷"
            file_type_text = "Фото"
        elif message.content_type == 'document':
            # Документ (файл) - проверяем что это изображение
            document = message.document
            
            if not document.mime_type or not document.mime_type.startswith('image/'):
                bot.send_message(
                    message.chat.id,
                    "❌ Пожалуйста, отправьте изображение (JPG, PNG, HEIC)!"
                )
                return
            
            file_info = bot.get_file(document.file_id)
            file_type_emoji = "📎"
            file_type_text = "Файл"
        else:
            bot.send_message(message.chat.id, "❌ Неподдерживаемый тип файла.")
            return
        
        # Скачиваем файл
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Открываем изображение с помощью PIL
        img = Image.open(BytesIO(downloaded_file))
        
        # Конвертируем в RGB если нужно
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        # Изменяем размер если очень большое (макс 4096px)
        max_size = 4096
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Сохраняем в JPEG с качеством 95%
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=95)
        photo_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        photo_data_uri = f"data:image/jpeg;base64,{photo_base64}"
        
        # Получаем размеры
        width, height = img.size
        
        # Отправляем на backend
        success = add_photo_to_session(session_id, {
            'photo_type': 'uploaded',
            'photo_data': photo_data_uri,
            'telegram_file_id': file_info.file_id if message.content_type == 'photo' else message.document.file_id,
            'telegram_file_size': file_info.file_size,
            'width': width,
            'height': height,
            'order_index': len(current_photos)
        })
        
        if success:
            uploaded_count = len(current_photos) + 1
            
            if uploaded_count >= 3:
                bot.send_message(
                    message.chat.id,
                    f"✅ Фото {uploaded_count} загружено!\n\n"
                    "🎉 Все фото получены!\n"
                    "Вернитесь к фотобудке для выбора и печати.",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                
                # Обновляем статус сессии
                update_session(session_id, {'status': 'ready'})
                
                # Удаляем сессию из кеша
                del user_sessions[user_id]
            else:
                remaining = 3 - uploaded_count
                bot.send_message(
                    message.chat.id,
                    f"✅ Фото {uploaded_count}/3 загружено!\n\n"
                    f"Отправьте ещё {remaining} фото."
                )
        else:
            bot.send_message(
                message.chat.id,
                "❌ Ошибка при загрузке фото. Попробуйте ещё раз."
            )
    
    except Exception as e:
        print(f"Error processing photo: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Ошибка при обработке фото.\n\n"
            "Убедитесь что вы отправляете фото как изображение, а не как файл."
        )

# ============================================
# ДРУГИЕ ОБРАБОТЧИКИ
# ============================================

@bot.message_handler(commands=['help'])
def help_command(message):
    """Команда помощи"""
    bot.send_message(
        message.chat.id,
        "ℹ️ *Sony Photobooth Bot - Помощь*\n\n"
        "*Как использовать:*\n\n"
        "1️⃣ Отсканируйте QR код на фотобудке\n"
        "2️⃣ Бот откроется автоматически\n"
        "3️⃣ Следуйте инструкциям:\n"
        "   • Загрузка: отправьте 3 фото\n"
        "   • Скачивание: получите готовые фото\n\n"
        "*Команды:*\n"
        "/start - Начать работу\n"
        "/help - Эта справка\n"
        "/cancel - Отменить текущую сессию\n\n"
        "💡 *Совет:* Отправляйте фото как изображения (не файлы) для лучшего качества.",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    """Отмена текущей сессии"""
    user_id = message.from_user.id
    
    if user_id in user_sessions:
        del user_sessions[user_id]
        bot.send_message(
            message.chat.id,
            "✅ Текущая сессия отменена.\n\n"
            "Отсканируйте QR код заново для создания новой сессии.",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        bot.send_message(
            message.chat.id,
            "У вас нет активной сессии."
        )

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Обработка всех остальных сообщений"""
    bot.send_message(
        message.chat.id,
        "❓ Я не понимаю эту команду.\n\n"
        "Отсканируйте QR код на фотобудке или используйте /help для справки."
    )

# ============================================
# ЗАПУСК БОТА
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("🤖 TELEGRAM BOT STARTED")
    print("=" * 60)
    print(f"Bot Token: {BOT_TOKEN[:10]}...")
    print(f"API URL: {API_URL}")
    print("Waiting for messages...")
    print("=" * 60)
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Bot stopped: {e}")
