"""
Утилита для просмотра и управления базой данных SQLite
"""
import sqlite3
import sys
from datetime import datetime
from tabulate import tabulate

DB_PATH = 'photobooth.db'

def connect_db():
    """Подключение к БД"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        sys.exit(1)

def show_all_payments():
    """Показать все платежи"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, order_id, amount, payment_type, status, 
               create_time, perform_time
        FROM payments
        ORDER BY create_time DESC
    """)
    
    rows = cursor.fetchall()
    
    if not rows:
        print("❌ Платежей нет в базе данных")
        return
    
    # Преобразуем в список для tabulate
    data = []
    for row in rows:
        data.append([
            row['id'],
            row['order_id'][:20] + '...' if len(row['order_id']) > 20 else row['order_id'],
            f"{row['amount']} сум",
            row['payment_type'],
            row['status'],
            row['create_time'][:19] if row['create_time'] else 'N/A',
            row['perform_time'][:19] if row['perform_time'] else 'N/A'
        ])
    
    headers = ['ID', 'Order ID', 'Amount', 'Type', 'Status', 'Created', 'Performed']
    print("\n" + "=" * 100)
    print("📊 ВСЕ ПЛАТЕЖИ")
    print("=" * 100)
    print(tabulate(data, headers=headers, tablefmt='grid'))
    print(f"\nВсего платежей: {len(rows)}")
    
    conn.close()

def show_stats():
    """Показать статистику"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Общая статистика
    cursor.execute("SELECT COUNT(*) as total FROM payments")
    total = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as count FROM payments WHERE status = 'success'")
    success = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM payments WHERE status = 'pending'")
    pending = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM payments WHERE status = 'canceled'")
    canceled = cursor.fetchone()['count']
    
    cursor.execute("SELECT SUM(amount) as revenue FROM payments WHERE status = 'success'")
    revenue = cursor.fetchone()['revenue'] or 0
    
    # По типам оплаты
    cursor.execute("""
        SELECT payment_type, COUNT(*) as count 
        FROM payments 
        GROUP BY payment_type
    """)
    by_type = cursor.fetchall()
    
    print("\n" + "=" * 60)
    print("📈 СТАТИСТИКА ПЛАТЕЖЕЙ")
    print("=" * 60)
    print(f"\n📦 Общее количество: {total}")
    print(f"✅ Успешных: {success}")
    print(f"⏳ В ожидании: {pending}")
    print(f"❌ Отменённых: {canceled}")
    print(f"💰 Общий доход: {revenue:,} сум")
    
    print("\n📊 По типам оплаты:")
    for row in by_type:
        print(f"   {row['payment_type']}: {row['count']}")
    
    conn.close()

def show_payment_details(payment_id):
    """Показать детали конкретного платежа"""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    row = cursor.fetchone()
    
    if not row:
        print(f"❌ Платёж с ID {payment_id} не найден")
        conn.close()
        return
    
    print("\n" + "=" * 60)
    print(f"🔍 ДЕТАЛИ ПЛАТЕЖА #{payment_id}")
    print("=" * 60)
    
    for key in row.keys():
        value = row[key]
        if value is None:
            value = "N/A"
        print(f"{key:20}: {value}")
    
    conn.close()

def clear_database():
    """Очистить все данные из БД"""
    response = input("⚠️  Вы уверены? Все данные будут удалены (y/n): ")
    if response.lower() != 'y':
        print("Отменено")
        return
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM payments")
    cursor.execute("DELETE FROM photos")
    conn.commit()
    
    print("✅ База данных очищена")
    conn.close()

def export_to_csv():
    """Экспорт платежей в CSV"""
    import csv
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM payments ORDER BY create_time DESC")
    rows = cursor.fetchall()
    
    if not rows:
        print("❌ Нет данных для экспорта")
        conn.close()
        return
    
    filename = f"payments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Header
        writer.writerow(rows[0].keys())
        # Data
        for row in rows:
            writer.writerow(row)
    
    print(f"✅ Экспортировано {len(rows)} записей в {filename}")
    conn.close()

def main_menu():
    """Главное меню"""
    while True:
        print("\n" + "=" * 60)
        print("🗄️  УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ PHOTOBOOTH")
        print("=" * 60)
        print("1. Показать все платежи")
        print("2. Показать статистику")
        print("3. Детали платежа по ID")
        print("4. Экспорт в CSV")
        print("5. Очистить базу данных")
        print("0. Выход")
        print("=" * 60)
        
        choice = input("\nВыберите действие (0-5): ").strip()
        
        if choice == '1':
            show_all_payments()
        elif choice == '2':
            show_stats()
        elif choice == '3':
            payment_id = input("Введите ID платежа: ").strip()
            if payment_id.isdigit():
                show_payment_details(int(payment_id))
            else:
                print("❌ ID должен быть числом")
        elif choice == '4':
            export_to_csv()
        elif choice == '5':
            clear_database()
        elif choice == '0':
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор")

if __name__ == '__main__':
    main_menu()
