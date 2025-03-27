import mysql.connector
from config import DB_CONFIG

def drop_tables():
    """Удаление всех таблиц"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # Отключаем проверку внешних ключей
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

        # Удаляем таблицы
        tables = ['orders', 'products', 'categories', 'users']
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"Таблица {table} удалена")

        # Включаем проверку внешних ключей
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        conn.commit()
        print("Все таблицы успешно удалены")

    except Exception as e:
        print(f"Ошибка при удалении таблиц: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("Начинаем удаление таблиц...")
    drop_tables()
    print("Удаление завершено") 