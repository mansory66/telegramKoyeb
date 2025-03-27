import mysql.connector
import logging
from config import DB_CONFIG
import os
import pymysql
import sys

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            logger.info("Попытка подключения к базе данных...")
            self.connection = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor(dictionary=True)
            logger.info("Успешное подключение к базе данных")
            self._add_code_column()
        except mysql.connector.Error as err:
            logger.error(f"Ошибка подключения к базе данных: {err}")
            raise
    
    def _add_code_column(self):
        """Добавляет столбец code в таблицу products, если он не существует"""
        try:
            # Проверяем, существует ли столбец code в таблице products
            self.cursor.execute("DESCRIBE products")
            columns = self.cursor.fetchall()
            
            # Проверяем, есть ли столбец code среди колонок
            column_exists = any(column['Field'] == 'code' for column in columns)
            
            if not column_exists:
                logger.info("Добавление столбца 'code' в таблицу products")
                self.cursor.execute("ALTER TABLE products ADD COLUMN code VARCHAR(255)")
                self.connection.commit()
                logger.info("Столбец 'code' успешно добавлен")
            else:
                logger.info("Столбец 'code' уже существует в таблице products")
            
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при добавлении столбца code: {err}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.connection.close()
            logger.info("Соединение с базой данных закрыто")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения: {e}")
    
    def get_user(self, telegram_id):
        try:
            self.cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
            return self.cursor.fetchone()
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при получении пользователя: {err}")
            raise

    def create_user(self, telegram_id, username, language='ru'):
        """
        Создает нового пользователя или возвращает существующего
        
        Args:
            telegram_id (int): ID пользователя в Telegram
            username (str): Имя пользователя
            language (str): Код языка (ru/en/uz), по умолчанию 'ru'
            
        Returns:
            dict: Данные пользователя
        """
        try:
            # Сначала проверяем, существует ли пользователь
            existing_user = self.get_user(telegram_id)
            if existing_user:
                logger.info(f"Пользователь {telegram_id} уже существует")
                return existing_user

            # Создаем нового пользователя
            self.cursor.execute(
                "INSERT INTO users (telegram_id, username, language) VALUES (%s, %s, %s)",
                (telegram_id, username, language)
            )
            self.connection.commit()
            logger.info(f"Создан новый пользователь: {telegram_id} с языком {language}")
            
            # Возвращаем созданного пользователя
            return self.get_user(telegram_id)
            
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при создании пользователя: {err}")
            self.connection.rollback()
            raise

    def update_subscription(self, telegram_id, is_subscribed):
        self.cursor.execute(
            "UPDATE users SET is_subscribed = %s WHERE telegram_id = %s",
            (is_subscribed, telegram_id)
        )
        self.connection.commit()

    def update_nickname(self, telegram_id, nickname):
        self.cursor.execute(
            "UPDATE users SET nickname = %s WHERE telegram_id = %s",
            (nickname, telegram_id)
        )
        self.connection.commit()

    def get_categories(self, parent_id=None):
        """Получить категории с указанным родителем"""
        try:
            if parent_id is None:
                self.cursor.execute("SELECT * FROM categories WHERE parent_id IS NULL")
            else:
                self.cursor.execute("SELECT * FROM categories WHERE parent_id = %s", (parent_id,))
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при получении категорий: {err}")
            return []

    def get_category(self, category_id):
        """Получить информацию о категории"""
        try:
            self.cursor.execute("SELECT * FROM categories WHERE id = %s", (category_id,))
            return self.cursor.fetchone()
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при получении категории: {err}")
            return None

    def get_category_path(self, category_id):
        """Получить путь к категории (список родительских категорий)"""
        try:
            path = []
            current_id = category_id
            
            while current_id is not None:
                self.cursor.execute("SELECT * FROM categories WHERE id = %s", (current_id,))
                category = self.cursor.fetchone()
                if category:
                    path.insert(0, category)
                    current_id = category['parent_id']
                else:
                    break
                    
            return path
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при получении пути категории: {err}")
            return []

    def create_category(self, name, parent_id=None):
        """Создать новую категорию"""
        try:
            self.cursor.execute(
                "INSERT INTO categories (name, parent_id) VALUES (%s, %s)",
                (name, parent_id)
            )
            self.connection.commit()
            return self.cursor.lastrowid
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при создании категории: {err}")
            self.connection.rollback()
            return None

    def update_category(self, category_id, name=None, parent_id=None):
        """Обновить информацию о категории"""
        try:
            if name and parent_id is not None:
                self.cursor.execute(
                    "UPDATE categories SET name = %s, parent_id = %s WHERE id = %s",
                    (name, parent_id, category_id)
                )
            elif name:
                self.cursor.execute(
                    "UPDATE categories SET name = %s WHERE id = %s",
                    (name, category_id)
                )
            elif parent_id is not None:
                self.cursor.execute(
                    "UPDATE categories SET parent_id = %s WHERE id = %s",
                    (parent_id, category_id)
                )
            
            self.connection.commit()
            return True
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при обновлении категории: {err}")
            self.connection.rollback()
            return False

    def delete_category(self, category_id):
        """Удалить категорию"""
        try:
            self.cursor.execute("DELETE FROM categories WHERE id = %s", (category_id,))
            self.connection.commit()
            return True
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при удалении категории: {err}")
            self.connection.rollback()
            return False

    def get_products_by_category(self, category_id):
        try:
            self.cursor.execute("SELECT * FROM products WHERE category_id = %s", (category_id,))
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при получении товаров по категории: {err}")
            return []

    def get_all_products(self):
        """Получить все товары из базы данных"""
        try:
            self.cursor.execute("SELECT * FROM products")
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при получении всех товаров: {err}")
            return []

    def get_product(self, product_id):
        self.cursor.execute(
            "SELECT * FROM products WHERE id = %s",
            (product_id,)
        )
        return self.cursor.fetchone()

    def create_order(self, user_id, product_id, delivery_point):
        """Создает новый заказ и добавляет в него товар"""
        try:
            # Получаем информацию о товаре
            self.cursor.execute("SELECT price FROM products WHERE id = %s", (product_id,))
            product = self.cursor.fetchone()
            if not product:
                raise ValueError("Товар не найден")

            # Создаем заказ
            self.cursor.execute(
                """INSERT INTO orders (user_id, total_amount, delivery_type, status) 
                VALUES (%s, %s, %s, %s)""",
                (user_id, product['price'], f"point{delivery_point}", "pending")
            )
            order_id = self.cursor.lastrowid

            # Добавляем товар в заказ
            self.cursor.execute(
                """INSERT INTO order_items (order_id, product_id, quantity, price) 
                VALUES (%s, %s, %s, %s)""",
                (order_id, product_id, 1, product['price'])
            )

            self.connection.commit()
            return order_id
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при создании заказа: {err}")
            self.connection.rollback()
            raise

    def get_user_orders(self, user_id):
        self.cursor.execute("""
            SELECT o.*, 
                   GROUP_CONCAT(p.name) as product_names,
                   GROUP_CONCAT(p.price) as prices,
                   GROUP_CONCAT(oi.quantity) as quantities
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            WHERE o.user_id = %s
            GROUP BY o.id
            ORDER BY o.created_at DESC
        """, (user_id,))
        return self.cursor.fetchall()

    def update_order_status(self, order_id, status):
        """Обновляет статус заказа"""
        self.cursor.execute(
            "UPDATE orders SET status = %s WHERE id = %s",
            (status, order_id)
        )
        self.connection.commit()

    def get_order(self, order_id):
        """Получает информацию о заказе по его ID"""
        self.cursor.execute("""
            SELECT o.*, u.telegram_id as user_telegram_id 
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE o.id = %s
        """, (order_id,))
        order = self.cursor.fetchone()
        if order:
            return dict(order)
        return None

    def get_pending_orders(self):
        """Получает список заказов, ожидающих подтверждения"""
        self.cursor.execute("""
            SELECT o.*, u.telegram_id, u.username, 
                   GROUP_CONCAT(p.name) as product_names,
                   GROUP_CONCAT(oi.quantity) as quantities
            FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            WHERE o.status IN ('pending', 'paid')
            GROUP BY o.id
            ORDER BY o.created_at DESC
        """)
        return self.cursor.fetchall()

    def get_all_orders(self):
        """Получить все заказы"""
        self.cursor.execute("""
            SELECT o.*, 
                   u.username,
                   GROUP_CONCAT(p.name) as product_names,
                   GROUP_CONCAT(oi.quantity) as quantities
            FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            GROUP BY o.id
            ORDER BY o.created_at DESC
        """)
        return self.cursor.fetchall()

    def get_all_users(self):
        """Получить всех пользователей"""
        self.cursor.execute("SELECT * FROM users")
        return self.cursor.fetchall()

    def update_product_stock(self, product_id, point_number, in_stock):
        """Обновить наличие товара"""
        field = f"stock_point{point_number}"
        self.cursor.execute(
            f"UPDATE products SET {field} = %s WHERE id = %s",
            (in_stock, product_id)
        )
        self.connection.commit()

    def delete_product(self, product_id):
        """Удалить товар"""
        self.cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        self.connection.commit()

    def add_product(self, category_id, name, description, price, strength=None):
        """Добавить новый товар"""
        self.cursor.execute(
            """INSERT INTO products 
               (category_id, name, description, price, strength) 
               VALUES (%s, %s, %s, %s, %s)""",
            (category_id, name, description, price, strength)
        )
        self.connection.commit()
        return self.cursor.lastrowid

    def get_product_by_article(self, article):
        """Получить товар по артикулу"""
        try:
            self.cursor.execute(
                "SELECT * FROM products WHERE article = %s",
                (article,)
            )
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при получении товара по артикулу: {str(e)}")
            return None

    def update_product(self, product_id, name=None, description=None, price=None, 
                      quantity=None, category_id=None, image_url=None):
        """Обновить информацию о товаре"""
        try:
            query_parts = []
            params = []
            
            if name is not None:
                query_parts.append("name = %s")
                params.append(name)
                
            if description is not None:
                query_parts.append("description = %s")
                params.append(description)
                
            if price is not None:
                query_parts.append("price = %s")
                params.append(price)
                
            if quantity is not None:
                query_parts.append("quantity = %s")
                params.append(quantity)
                
            if category_id is not None:
                query_parts.append("category_id = %s")
                params.append(category_id)
                
            if image_url is not None:
                query_parts.append("image_url = %s")
                params.append(image_url)
                
            if not query_parts:
                return False  # Нечего обновлять
                
            params.append(product_id)  # ID товара для WHERE условия
            
            query = f"UPDATE products SET {', '.join(query_parts)} WHERE id = %s"
            self.cursor.execute(query, params)
            self.connection.commit()
            
            logger.info(f"Товар {product_id} успешно обновлен")
            return True
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при обновлении товара: {err}")
            self.connection.rollback()
            return False

    def update_user_nickname(self, telegram_id: int, nickname: str) -> None:
        """Обновляет никнейм пользователя"""
        query = "UPDATE users SET nickname = %s WHERE telegram_id = %s"
        self.cursor.execute(query, (nickname, telegram_id))
        self.connection.commit()

    def save_feedback(self, user_id: int, text: str) -> int:
        """Сохраняет отзыв пользователя в базу данных"""
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT,
                    text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status ENUM('new', 'read', 'answered') DEFAULT 'new'
                )
            """)
            
            cursor.execute(
                "INSERT INTO feedback (user_id, text) VALUES (%s, %s)",
                (user_id, text)
            )
            self.connection.commit()
            return cursor.lastrowid
        finally:
            cursor.close()

    def get_feedback(self, status: str = None) -> list:
        """Получает список отзывов с опциональной фильтрацией по статусу"""
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            if status:
                cursor.execute(
                    "SELECT * FROM feedback WHERE status = %s ORDER BY created_at DESC",
                    (status,)
                )
            else:
                cursor.execute("SELECT * FROM feedback ORDER BY created_at DESC")
            
            return cursor.fetchall()
        finally:
            cursor.close()

    def update_feedback_status(self, feedback_id: int, status: str) -> bool:
        """Обновляет статус отзыва"""
        cursor = self.connection.cursor()
        
        try:
            cursor.execute(
                "UPDATE feedback SET status = %s WHERE id = %s",
                (status, feedback_id)
            )
            self.connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()

    def get_statistics(self, period: str = 'week') -> dict:
        """Получает статистику магазина за указанный период"""
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            # Определяем временной интервал
            if period == 'day':
                interval = "AND created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)"
            elif period == 'month':
                interval = "AND created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)"
            else:  # week по умолчанию
                interval = "AND created_at >= DATE_SUB(NOW(), INTERVAL 1 WEEK)"
            
            # Общая статистика заказов
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                    SUM(total_price) as total_sales
                FROM orders
                WHERE 1=1 {interval}
            """)
            orders_stats = cursor.fetchone()
            
            # Статистика пользователей
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_users,
                    SUM(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 ELSE 0 END) as new_users_24h
                FROM users
            """)
            users_stats = cursor.fetchone()
            
            # Топ продуктов
            cursor.execute(f"""
                SELECT p.name, COUNT(*) as count
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                JOIN orders o ON o.id = oi.order_id
                WHERE 1=1 {interval}
                GROUP BY p.id, p.name
                ORDER BY count DESC
                LIMIT 5
            """)
            top_products = cursor.fetchall()
            
            # Продажи по дням
            cursor.execute(f"""
                SELECT 
                    DATE(created_at) as date,
                    SUM(total_price) as sales
                FROM orders
                WHERE 1=1 {interval}
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            sales_by_day = cursor.fetchall()
            
            # Находим максимальные дневные продажи для масштабирования графика
            max_daily_sales = max([day['sales'] for day in sales_by_day]) if sales_by_day else 0
            
            return {
                'total_orders': orders_stats['total_orders'],
                'completed_orders': orders_stats['completed_orders'],
                'total_sales': orders_stats['total_sales'],
                'total_users': users_stats['total_users'],
                'new_users_24h': users_stats['new_users_24h'],
                'top_products': top_products,
                'sales_by_day': sales_by_day,
                'max_daily_sales': max_daily_sales
            }
        finally:
            cursor.close()

    def update_user_language(self, telegram_id, language):
        """
        Обновляет язык пользователя
        
        Args:
            telegram_id (int): ID пользователя в Telegram
            language (str): Новый код языка (ru/en/uz)
        """
        try:
            self.cursor.execute(
                "UPDATE users SET language = %s WHERE telegram_id = %s",
                (language, telegram_id)
            )
            self.connection.commit()
            logger.info(f"Обновлен язык пользователя {telegram_id} на {language}")
            return True
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при обновлении языка пользователя: {err}")
            self.connection.rollback()
            return False

    def get_user_language(self, telegram_id):
        """
        Получает текущий язык пользователя
        
        Args:
            telegram_id (int): ID пользователя в Telegram
            
        Returns:
            str: Код языка пользователя (ru/en/uz) или 'ru' по умолчанию
        """
        try:
            self.cursor.execute(
                "SELECT language FROM users WHERE telegram_id = %s",
                (telegram_id,)
            )
            result = self.cursor.fetchone()
            return result['language'] if result else 'ru'
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при получении языка пользователя: {err}")
            return 'ru'

    def get_user(self, user_id: int) -> dict:
        """Получает информацию о пользователе"""
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            cursor.execute(
                "SELECT * FROM users WHERE telegram_id = %s",
                (user_id,)
            )
            user = cursor.fetchone()
            if not user:
                # Создаем нового пользователя с дефолтным языком
                cursor.execute(
                    "INSERT INTO users (telegram_id, language) VALUES (%s, 'ru')",
                    (user_id,)
                )
                self.connection.commit()
                cursor.execute(
                    "SELECT * FROM users WHERE telegram_id = %s",
                    (user_id,)
                )
                user = cursor.fetchone()
            return user
        finally:
            cursor.close()

    def get_user_orders_count(self, user_id: int) -> int:
        """Получает количество заказов пользователя"""
        cursor = self.connection.cursor()
        
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM orders WHERE user_id = %s",
                (user_id,)
            )
            return cursor.fetchone()[0]
        finally:
            cursor.close()

    def get_abandoned_carts(self) -> list:
        """Получает список брошенных корзин"""
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            # Создаем таблицу корзин, если её нет
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS carts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT,
                    product_id INT,
                    quantity INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    status ENUM('active', 'abandoned', 'completed') DEFAULT 'active'
                )
            """)
            
            # Получаем брошенные корзины (неактивные более 24 часов)
            cursor.execute("""
                SELECT c.*, p.name as product_name, p.price
                FROM carts c
                JOIN products p ON p.id = c.product_id
                WHERE c.status = 'active'
                AND c.last_updated < DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            return cursor.fetchall()
        finally:
            cursor.close()

    def get_cart(self, cart_id: int) -> dict:
        """Получает информацию о корзине"""
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT c.*, p.name as product_name, p.price
                FROM carts c
                JOIN products p ON p.id = c.product_id
                WHERE c.id = %s
            """, (cart_id,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def create_order_from_cart(self, cart_id: int) -> int:
        """Создает заказ из брошенной корзины"""
        cursor = self.connection.cursor()
        
        try:
            # Получаем информацию о корзине
            cart = self.get_cart(cart_id)
            if not cart:
                return None
            
            # Создаем заказ
            cursor.execute("""
                INSERT INTO orders (user_id, status, total_price)
                VALUES (%s, 'created', %s)
            """, (cart['user_id'], cart['price'] * cart['quantity']))
            order_id = cursor.lastrowid
            
            # Добавляем товары в заказ
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, cart['product_id'], cart['quantity'], cart['price']))
            
            # Обновляем статус корзины
            cursor.execute("""
                UPDATE carts
                SET status = 'completed'
                WHERE id = %s
            """, (cart_id,))
            
            self.connection.commit()
            return order_id
        finally:
            cursor.close()

    def delete_cart(self, cart_id: int) -> bool:
        """Удаляет корзину"""
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("""
                UPDATE carts
                SET status = 'abandoned'
                WHERE id = %s
            """, (cart_id,))
            self.connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()

    def get_order(self, order_id: int) -> dict:
        """Получает информацию о заказе"""
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT o.*, p.name as product_name
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN products p ON p.id = oi.product_id
                WHERE o.id = %s
            """, (order_id,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def update_order_status(self, order_id: int, status: str) -> bool:
        """Обновляет статус заказа"""
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("""
                UPDATE orders
                SET status = %s
                WHERE id = %s
            """, (status, order_id))
            self.connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()

    def create_product(self, name, code, price, quantity, category_id=None, description="", image_url=""):
        """Создать новый товар"""
        try:
            self.cursor.execute(
                """
                INSERT INTO products 
                (name, code, description, price, quantity, category_id, image_url) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (name, code, description, price, quantity, category_id, image_url)
            )
            self.connection.commit()
            return self.cursor.lastrowid
        except mysql.connector.Error as err:
            logger.error(f"Ошибка при создании товара: {err}")
            self.connection.rollback()
            return None 