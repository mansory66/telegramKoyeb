import requests
import base64
import json
import sys
from config import MOYSKLAD_LOGIN, MOYSKLAD_PASSWORD

# Функция для получения заголовка авторизации
def get_auth_header():
    credentials = f"{MOYSKLAD_LOGIN}:{MOYSKLAD_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return {'Authorization': f'Basic {encoded_credentials}'}

# Получение товара по ID для тестирования
def get_product_by_id(product_id):
    url = f"https://api.moysklad.ru/api/remap/1.2/entity/product/{product_id}"
    headers = get_auth_header()
    
    print(f"Запрос данных о товаре с ID: {product_id}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        product = response.json()
        print(f"Товар найден: {product.get('name')}")
        return product
    else:
        print(f"Ошибка при получении товара: {response.status_code}")
        return None

# Получение остатков товара методом 1 (report/stock/all)
def check_stock_method1(product_id, product_name):
    url = f"https://api.moysklad.ru/api/remap/1.2/report/stock/all?product.id={product_id}"
    headers = get_auth_header()
    
    print(f"\n=== МЕТОД 1: report/stock/all ===")
    print(f"URL запроса: {url}")
    
    response = requests.get(url, headers=headers)
    print(f"Код ответа: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        # Печатаем основную информацию о формате ответа
        print(f"Тип данных ответа: {type(data)}")
        if isinstance(data, list):
            print(f"Количество элементов в ответе: {len(data)}")
            
            # Проверяем первый элемент если он есть
            if data:
                first_item = data[0]
                print(f"Ключи первого элемента: {list(first_item.keys())}")
                
                # Проверяем наличие полей с остатками
                if 'stock' in first_item:
                    print(f"Значение 'stock': {first_item['stock']}")
                else:
                    print("Поле 'stock' отсутствует")
                
                if 'quantity' in first_item:
                    print(f"Значение 'quantity': {first_item['quantity']}")
                
                if 'inTransit' in first_item:
                    print(f"Значение 'inTransit': {first_item['inTransit']}")
                
                if 'reserve' in first_item:
                    print(f"Значение 'reserve': {first_item['reserve']}")
                
                # Проверяем склады
                if 'stockByStore' in first_item:
                    stores = first_item['stockByStore']
                    print(f"Количество складов: {len(stores)}")
                    
                    for idx, store in enumerate(stores[:3]):  # Показываем только первые 3 склада
                        print(f"  Склад {idx+1}:")
                        for key, value in store.items():
                            print(f"    {key}: {value}")
                        
                        if idx == 2 and len(stores) > 3:
                            print(f"  ... и еще {len(stores) - 3} складов")
                else:
                    print("Данные по складам отсутствуют")
                
                # Полный вывод первого элемента для анализа
                print("\nПолный вывод первого элемента:")
                print(json.dumps(first_item, indent=2, ensure_ascii=False))
        else:
            print("Ответ не является списком")
            print("Полный вывод ответа:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"Ошибка запроса: {response.text}")

# Получение остатков товара методом 2 (report/stock/bystore)
def check_stock_method2(product_id, product_name):
    url = f"https://api.moysklad.ru/api/remap/1.2/report/stock/bystore?product.id={product_id}"
    headers = get_auth_header()
    
    print(f"\n=== МЕТОД 2: report/stock/bystore ===")
    print(f"URL запроса: {url}")
    
    response = requests.get(url, headers=headers)
    print(f"Код ответа: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        # Печатаем основную информацию о формате ответа
        print(f"Тип данных ответа: {type(data)}")
        
        if isinstance(data, dict) and 'rows' in data:
            rows = data['rows']
            print(f"Количество строк: {len(rows)}")
            
            # Подсчитываем общий остаток
            total_stock = 0
            stores_with_stock = 0
            
            for row in rows:
                if 'stock' in row and row['stock'] > 0:
                    total_stock += row['stock']
                    stores_with_stock += 1
            
            print(f"Найдено {stores_with_stock} складов с положительным остатком")
            print(f"Общий остаток по всем складам: {total_stock}")
            
            # Показываем первые 3 строки
            if rows:
                for idx, row in enumerate(rows[:3]):
                    print(f"\n  Строка {idx+1}:")
                    for key, value in row.items():
                        print(f"    {key}: {value}")
                    
                    if idx == 2 and len(rows) > 3:
                        print(f"  ... и еще {len(rows) - 3} строк")
        else:
            print("Ответ имеет неожиданную структуру")
            print("Полный вывод ответа:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"Ошибка запроса: {response.text}")

# Основная функция для тестирования остатков
def main():
    # Если передан ID товара, используем его, иначе получаем первый товар
    if len(sys.argv) > 1:
        product_id = sys.argv[1]
        product = get_product_by_id(product_id)
        product_name = product.get('name', 'Неизвестный товар') if product else 'Неизвестный товар'
    else:
        # Получаем первый товар для тестирования
        url = "https://api.moysklad.ru/api/remap/1.2/entity/product"
        headers = get_auth_header()
        
        print("Получение первого товара из списка...")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if 'rows' in data and data['rows']:
                product = data['rows'][0]
                product_id = product['id']
                product_name = product['name']
                print(f"Выбран товар: {product_name} (ID: {product_id})")
            else:
                print("Товары не найдены")
                return
        else:
            print(f"Ошибка при получении товаров: {response.status_code}")
            return
    
    # Проверяем оба метода получения остатков
    check_stock_method1(product_id, product_name)
    check_stock_method2(product_id, product_name)
    
    print("\n=== ИТОГОВАЯ РЕКОМЕНДАЦИЯ ===")
    print("Для правильного получения остатков товаров используйте:")
    print("1. Метод report/stock/all с обработкой поля 'stock'")
    print("2. Учитывайте, что ответ может быть списком с одним элементом")
    print("3. Если первый метод не дал результата, попробуйте report/stock/bystore и суммируйте 'stock' по всем складам")

if __name__ == "__main__":
    main() 