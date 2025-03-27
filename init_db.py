import mysql.connector
from config import DB_CONFIG

def init_db():
    """Инициализация базы данных"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # Создание таблицы категорий с поддержкой иерархии
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                parent_id INT NULL,
                CONSTRAINT fk_parent 
                    FOREIGN KEY (parent_id) 
                    REFERENCES categories(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB
        """)

        # Создание таблицы товаров
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                moysklad_id VARCHAR(255) UNIQUE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price DECIMAL(10, 2),
                category_id INT,
                stock_point1 BOOLEAN DEFAULT FALSE,
                stock_point2 BOOLEAN DEFAULT FALSE,
                strength VARCHAR(50),
                FOREIGN KEY (category_id) 
                    REFERENCES categories(id)
                    ON DELETE SET NULL
            ) ENGINE=InnoDB
        """)

        # Создание таблицы заказов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                username VARCHAR(255),
                phone VARCHAR(20),
                address TEXT,
                delivery_type VARCHAR(50),
                payment_type VARCHAR(50),
                total_amount DECIMAL(10, 2),
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        """)

        # Создание таблицы товаров в заказе
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT,
                product_id INT,
                quantity INT,
                price DECIMAL(10, 2),
                FOREIGN KEY (order_id) 
                    REFERENCES orders(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (product_id) 
                    REFERENCES products(id)
                    ON DELETE SET NULL
            ) ENGINE=InnoDB
        """)

        conn.commit()
        print("База данных успешно инициализирована")

    except mysql.connector.Error as err:
        print(f"Ошибка при инициализации базы данных: {err}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("Начинаем инициализацию базы данных...")
    init_db()
    print("Инициализация завершена") 