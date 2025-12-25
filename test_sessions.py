"""
Тестирование Session API endpoints
"""
import requests
import json

API_URL = "http://localhost:5000/api"

def test_create_session():
    """Тест создания сессии"""
    print("\n1️⃣  Тест: Создание upload сессии")
    response = requests.post(f"{API_URL}/session/create", json={
        "type": "upload",
        "kiosk_id": 1,
        "data": {"test": "data"}
    })
    
    assert response.status_code == 201
    data = response.json()
    session_id = data['session']['id']
    print(f"✅ Session created: {session_id}")
    return session_id

def test_get_session(session_id):
    """Тест получения сессии"""
    print(f"\n2️⃣  Тест: Получение сессии {session_id}")
    response = requests.get(f"{API_URL}/session/{session_id}")
    
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Session retrieved: {data['type']} - {data['status']}")
    return data

def test_add_photo(session_id):
    """Тест добавления фото"""
    print(f"\n3️⃣  Тест: Добавление фото в сессию")
    
    # Добавляем 3 фото
    for i in range(3):
        response = requests.post(f"{API_URL}/session/{session_id}/photos", json={
            "photo_type": "uploaded",
            "photo_data": f"base64_photo_data_{i}",
            "telegram_file_id": f"file_{i}",
            "width": 1920,
            "height": 1080,
            "order_index": i
        })
        
        assert response.status_code == 201
        print(f"✅ Photo {i+1} added")
    
    return True

def test_get_photos(session_id):
    """Тест получения фото"""
    print(f"\n4️⃣  Тест: Получение фото сессии")
    response = requests.get(f"{API_URL}/session/{session_id}/photos")
    
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Photos retrieved: {len(data['photos'])} photos")
    
    for photo in data['photos']:
        print(f"   - Photo {photo['id']}: {photo['photo_type']}, index: {photo['order_index']}")
    
    return data['photos']

def test_update_session(session_id):
    """Тест обновления сессии"""
    print(f"\n5️⃣  Тест: Обновление сессии")
    response = requests.put(f"{API_URL}/session/{session_id}", json={
        "status": "completed",
        "telegram_user_id": 123456,
        "telegram_username": "test_user"
    })
    
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Session updated: {data['status']}")
    return data

def test_list_sessions():
    """Тест списка сессий"""
    print(f"\n6️⃣  Тест: Список активных сессий")
    response = requests.get(f"{API_URL}/sessions/list")
    
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Active sessions: {data['count']}")
    return data

def test_delete_session(session_id):
    """Тест удаления сессии"""
    print(f"\n7️⃣  Тест: Удаление сессии")
    response = requests.delete(f"{API_URL}/session/{session_id}")
    
    assert response.status_code == 200
    print(f"✅ Session deleted")
    return True

def run_all_tests():
    """Запустить все тесты"""
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ SESSION API")
    print("=" * 60)
    
    try:
        # Тест 1: Создание
        session_id = test_create_session()
        
        # Тест 2: Получение
        test_get_session(session_id)
        
        # Тест 3: Добавление фото
        test_add_photo(session_id)
        
        # Тест 4: Получение фото
        test_get_photos(session_id)
        
        # Тест 5: Обновление
        test_update_session(session_id)
        
        # Тест 6: Список
        test_list_sessions()
        
        # Тест 7: Удаление
        test_delete_session(session_id)
        
        print("\n" + "=" * 60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ ТЕСТ ПРОВАЛЕН: {e}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n❌ ОШИБКА: Backend не запущен на {API_URL}")
        print("Запустите: python app.py")
        return False
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        return False
    
    return True

if __name__ == "__main__":
    run_all_tests()
