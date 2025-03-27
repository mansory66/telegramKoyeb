import logging
import requests
import json
import sys
from config import MOYSKLAD_LOGIN, MOYSKLAD_PASSWORD
import base64

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

def get_auth_header():
    """Получение заголовка авторизации для API МойСклад"""
    credentials = f"{MOYSKLAD_LOGIN}:{MOYSKLAD_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return {'Authorization': f'Basic {encoded_credentials}'}

def test_stock_api():
    """Тестирование API остатков"""
    headers = get_auth_header()
    
    # Получаем список товаров
    try:
        url = "https://api.moysklad.ru/api/remap/1.2/entity/product"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            products = data.get('rows', [])
            print(f"Получено товаров: {len(products)}")
            
            if products:
                # Тестируем первые 2 товара
                for i, product in enumerate(products[:2]):
                    product_id = product.get('id')
                    product_name = product.get('name')
                    print(f"\n===== Товар {i+1}: {product_name} (ID: {product_id}) =====")
                    
                    # Тестируем разные API для получения остатков
                    test_stock_all_api(product_id, headers)
                    test_stock_bystore_api(product_id, headers)
        else:
            print(f"Ошибка при получении товаров: {response.status_code}")
    except Exception as e:
        print(f"Ошибка: {str(e)}")

def test_stock_all_api(product_id, headers):
    """Тестирование API report/stock/all"""
    print("\n-- Тест API report/stock/all --")
    url = f"https://api.moysklad.ru/api/remap/1.2/report/stock/all?product.id={product_id}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"Тип данных ответа: {type(data)}")
            
            if isinstance(data, list):
                print(f"Количество элементов: {len(data)}")
                
                for item in data:
                    print(f"Ключи элемента: {list(item.keys())}")
                    
                    # Проверяем ключи, связанные с количеством
                    if 'stock' in item:
                        print(f"- stock: {item['stock']}")
                    if 'reserve' in item:
                        print(f"- reserve: {item['reserve']}")
                    if 'inTransit' in item:
                        print(f"- inTransit: {item['inTransit']}")
                    if 'quantity' in item:
                        print(f"- quantity: {item['quantity']}")
                    
                    # Проверяем остатки по складам
                    if 'stockByStore' in item:
                        stores = item['stockByStore']
                        print(f"Количество складов: {len(stores)}")
                        
                        for store in stores:
                            store_name = store.get('name', 'Неизвестно')
                            store_stock = store.get('stock', 0)
                            print(f"  * Склад '{store_name}': {store_stock}")
            else:
                print("Ответ не является списком")
                print(f"Ответ: {data}")
        else:
            print(f"Ошибка запроса: {response.status_code}")
            print(f"Текст ошибки: {response.text}")
    except Exception as e:
        print(f"Исключение: {str(e)}")

def test_stock_bystore_api(product_id, headers):
    """Тестирование API report/stock/bystore"""
    print("\n-- Тест API report/stock/bystore --")
    url = f"https://api.moysklad.ru/api/remap/1.2/report/stock/bystore?product.id={product_id}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"Тип данных ответа: {type(data)}")
            
            if isinstance(data, dict) and 'rows' in data:
                rows = data['rows']
                print(f"Количество строк: {len(rows)}")
                
                for row in rows:
                    store_name = row.get('name', 'Неизвестно')
                    print(f"Склад: {store_name}")
                    
                    # Проверяем наличие ключей, связанных с количеством
                    if 'stock' in row:
                        print(f"- stock: {row['stock']}")
                    if 'reserve' in row:
                        print(f"- reserve: {row['reserve']}")
                    if 'inTransit' in row:
                        print(f"- inTransit: {row['inTransit']}")
            else:
                print("Ответ имеет неожиданную структуру")
                print(f"Ответ: {data}")
        else:
            print(f"Ошибка запроса: {response.status_code}")
            print(f"Текст ошибки: {response.text}")
    except Exception as e:
        print(f"Исключение: {str(e)}")

if __name__ == "__main__":
    print("Запуск тестирования API остатков МойСклад")
    test_stock_api()
    print("\nТестирование завершено") 