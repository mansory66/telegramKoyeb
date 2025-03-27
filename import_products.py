import requests
import base64
from config import MOYSKLAD_LOGIN, MOYSKLAD_PASSWORD, DB_CONFIG
import mysql.connector
from datetime import datetime

def get_moysklad_token():
    """Получение токена для доступа к API МойСклад"""
    credentials = f"{MOYSKLAD_LOGIN}:{MOYSKLAD_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return encoded_credentials

def get_products_from_moysklad():
    """Получение списка товаров из МойСклад"""
    token = get_moysklad_token()
    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }
    
    url = "https://api.moysklad.ru/api/remap/1.2/entity/product"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()['rows']
    else:
        print(f"Ошибка при получении товаров: {response.status_code}")
        print(response.text)
        return None

def get_full_category_path(product, headers):
    """Получение полного пути категории товара"""
    if 'pathName' in product:
        return product['pathName'].split('/')
    elif 'productFolder' in product and product['productFolder']:
        folder_url = product['productFolder']['meta']['href']
        folder_response = requests.get(folder_url, headers=headers)
        if folder_response.status_code == 200:
            folder_data = folder_response.json()
            if 'pathName' in folder_data:
                return folder_data['pathName'].split('/')
            return [folder_data['name']]
    return ['Без категории']

def ensure_category_exists(cursor, conn, category_path, categories):
    """Создание категории и подкатегорий если они не существуют"""
    parent_id = None
    current_path = []
    
    for level in category_path:
        current_path.append(level)
        current_name = current_path[-1]  # Текущее имя категории
        full_path = ' / '.join(current_path)  # Полный путь для отображения
        
        # Проверяем существование категории по имени и parent_id
        if parent_id is None:
            cursor.execute(
                "SELECT id FROM categories WHERE name = %s AND parent_id IS NULL",
                (current_name,)
            )
        else:
            cursor.execute(
                "SELECT id FROM categories WHERE name = %s AND parent_id = %s",
                (current_name, parent_id)
            )
        category = cursor.fetchone()
        
        if not category:
            # Создаем новую категорию
            cursor.execute(
                "INSERT INTO categories (name, parent_id) VALUES (%s, %s)",
                (current_name, parent_id)
            )
            conn.commit()
            
            # Получаем ID новой категории
            if parent_id is None:
                cursor.execute(
                    "SELECT id FROM categories WHERE name = %s AND parent_id IS NULL",
                    (current_name,)
                )
            else:
                cursor.execute(
                    "SELECT id FROM categories WHERE name = %s AND parent_id = %s",
                    (current_name, parent_id)
                )
            category = cursor.fetchone()
            print(f"Создана новая категория: {full_path}")
        
        # Сохраняем ID текущей категории как parent_id для следующего уровня
        parent_id = category['id'] if isinstance(category, dict) else category[0]
        
        # Добавляем в словарь categories
        categories[full_path] = parent_id
    
    return parent_id  # Возвращаем ID последней категории в пути

def get_product_stock(product_id, headers):
    """Получение остатков товара по всем складам"""
    url = "https://api.moysklad.ru/api/remap/1.2/report/stock/bystore/current"
    params = {
        'filter': f'assortmentId={product_id}'
    }
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        print(f"Ответ API по остаткам: {response.text}")  # Отладочный вывод
        return response.json()
    else:
        print(f"Ошибка при получении остатков: {response.status_code}")
        print(f"Текст ошибки: {response.text}")
        return []

def import_products_to_db():
    """Импорт товаров из МойСклад в базу данных"""
    products = get_products_from_moysklad()
    if not products:
        print("Не удалось получить товары из МойСклад")
        return

    # Подключение к базе данных
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    # Определяем заголовки для всех API-запросов
    headers = {
        'Authorization': f'Basic {get_moysklad_token()}',
        'Content-Type': 'application/json'
    }

    try:
        # Получаем существующие категории
        cursor.execute("SELECT id, name FROM categories")
        categories = {cat['name']: cat['id'] for cat in cursor.fetchall()}

        # Получаем информацию о складах
        stores_url = "https://api.moysklad.ru/api/remap/1.2/entity/store"
        stores_response = requests.get(stores_url, headers=headers)
        stores = {}
        if stores_response.status_code == 200:
            for store in stores_response.json()['rows']:
                stores[store['id']] = store['name']
                print(f"Найден склад: {store['name']} (ID: {store['id']})")

        for product in products:
            try:
                # Получаем название товара
                product_name = product['name']
                print(f"\nОбработка товара: {product_name}")

                # Получаем полный путь категории
                category_path = get_full_category_path(product, headers)
                print(f"Полный путь категории: {' / '.join(category_path)}")
                
                # Создаем категории если они не существуют и получаем ID последней категории
                category_id = ensure_category_exists(cursor, conn, category_path, categories)

                # Получаем остатки на складах
                stock_data = get_product_stock(product['id'], headers)
                
                # Определяем наличие на складах
                stock_point1 = 0
                stock_point2 = 0
                
                if isinstance(stock_data, list):
                    for stock in stock_data:
                        store_id = stock.get('storeId', '')
                        if store_id in stores:
                            store_name = stores[store_id]
                            stock_quantity = float(stock.get('stock', 0))
                            print(f"Склад: {store_name}, остаток: {stock_quantity}")
                            
                            if "1 склад" in store_name or "Дзержинского" in store_name:
                                stock_point1 = int(stock_quantity)
                            elif "2 склад" in store_name or "Степана Разина" in store_name:
                                stock_point2 = int(stock_quantity)

                print(f"Итоговые остатки:")
                print(f"1 склад (Дзержинского): {stock_point1}")
                print(f"2 склад (Степана Разина): {stock_point2}")

                # Получаем крепость из характеристик товара
                strength = None
                if 'characteristics' in product:
                    for char in product['characteristics']:
                        if char['name'].lower() == 'крепость':
                            strength = char['value']
                            print(f"Крепость: {strength}")

                # Проверяем, существует ли товар
                cursor.execute(
                    "SELECT id FROM products WHERE moysklad_id = %s",
                    (product['id'],)
                )
                existing_product = cursor.fetchone()

                if existing_product:
                    # Обновляем существующий товар
                    cursor.execute("""
                        UPDATE products 
                        SET name = %s, description = %s, price = %s, 
                            category_id = %s, stock_point1 = %s, stock_point2 = %s,
                            strength = %s
                        WHERE moysklad_id = %s
                    """, (
                        product_name,
                        product.get('description', ''),
                        float(product.get('salePrices', [{'value': 0}])[0]['value']) / 100,
                        category_id,
                        stock_point1 > 0,
                        stock_point2 > 0,
                        strength,
                        product['id']
                    ))
                    print("Товар обновлен в базе данных")
                else:
                    # Добавляем новый товар
                    cursor.execute("""
                        INSERT INTO products (
                            moysklad_id, name, description, price, 
                            category_id, stock_point1, stock_point2, strength
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        product['id'],
                        product_name,
                        product.get('description', ''),
                        float(product.get('salePrices', [{'value': 0}])[0]['value']) / 100,
                        category_id,
                        stock_point1 > 0,
                        stock_point2 > 0,
                        strength
                    ))
                    print("Товар добавлен в базу данных")

                conn.commit()
                print(f"Наличие: 1 склад (Дзержинского) - {stock_point1} шт., 2 склад (Степана Разина) - {stock_point2} шт.")
                print(f"В базе данных: 1 склад - {stock_point1 > 0}, 2 склад - {stock_point2 > 0}")
                print("------------------")

            except Exception as e:
                print(f"Ошибка при обработке товара {product.get('name', 'Неизвестный товар')}: {str(e)}")
                print(f"Детали ошибки: {e.__class__.__name__}")
                continue

    except Exception as e:
        print(f"Ошибка при импорте товаров: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("Начинаем импорт товаров из МойСклад...")
    import_products_to_db()
    print("Импорт завершен") 