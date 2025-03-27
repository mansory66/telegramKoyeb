import logging
import requests
import base64
import json
from requests.auth import HTTPBasicAuth
from config import MOYSKLAD_LOGIN, MOYSKLAD_PASSWORD

logger = logging.getLogger(__name__)

def get_auth_header():
    """Получение заголовка авторизации для API МойСклад"""
    credentials = f"{MOYSKLAD_LOGIN}:{MOYSKLAD_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return {'Authorization': f'Basic {encoded_credentials}'}

def get_all_products():
    """Получение всех товаров из МойСклад"""
    try:
        # Обновленный URL API МойСклад
        url = "https://api.moysklad.ru/api/remap/1.2/entity/product"
        headers = get_auth_header()
        logger.info(f"Выполняем запрос товаров к API: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Ошибка при получении товаров из МойСклад: {response.text}")
            return []
        
        data = response.json()
        logger.info(f"Успешно получено {len(data.get('rows', []))} товаров из API")
        products = []
        
        for index, item in enumerate(data.get('rows', [])):
            try:
                product_id = item.get('id')
                if not product_id:
                    logger.warning(f"Товар без ID: {item.get('name', 'Неизвестный товар')}, пропускаем")
                    continue
                
                # Получение цены товара
                price = 0
                try:
                    if 'salePrices' in item and len(item['salePrices']) > 0:
                        # Цена в МойСклад хранится в копейках, поэтому делим на 100
                        price = item['salePrices'][0]['value'] / 100
                except Exception as e:
                    logger.error(f"Ошибка при получении цены товара {item.get('name', '')}: {str(e)}")
                
                # Получение количества товара с ПРЯМЫМ запросом к API остатков
                quantity = get_product_stock(product_id, headers, item.get('name', ''))
                
                # Формирование данных о товаре, генерируем код если его нет
                product_code = item.get('code', '')
                if not product_code:
                    # Если код отсутствует, генерируем его из id или другого уникального поля
                    product_code = f"ID_{item.get('id', '')[-6:]}"
                    logger.warning(f"Для товара '{item.get('name', '')}' код отсутствует, сгенерирован: {product_code}")
                
                # Добавляем дополнительную информацию
                description = item.get('description', '')
                if not description and item.get('attributes'):
                    # Пытаемся составить описание из атрибутов товара
                    attributes = []
                    for attr in item.get('attributes', []):
                        if attr.get('name') and attr.get('value'):
                            attributes.append(f"{attr['name']}: {attr['value']}")
                    if attributes:
                        description = "\n".join(attributes)
                
                product = {
                    'name': item.get('name', ''),
                    'code': product_code,
                    'description': description,
                    'price': price,
                    'quantity': quantity,
                    'category_id': None,  # Нужно сопоставить с категориями в вашей базе данных
                    'image_url': ''  # Добавить получение изображений при необходимости
                }
                
                logger.info(f"Обработан товар #{index+1}: {product['name']}, цена: {product['price']}, остаток: {product['quantity']}")
                products.append(product)
            except Exception as e:
                logger.error(f"Ошибка при обработке товара {item.get('name', '')}: {str(e)}")
        
        logger.info(f"Всего обработано {len(products)} товаров из {len(data.get('rows', []))}")
        return products
    except Exception as e:
        logger.error(f"Ошибка при работе с API МойСклад: {str(e)}")
        return []

def get_product_stock(product_id, headers, product_name=''):
    """Получение остатков конкретного товара"""
    total_stock = 0
    
    try:
        # Метод 1: Пробуем отчет по остаткам для конкретного товара
        stock_url = f"https://api.moysklad.ru/api/remap/1.2/report/stock/all?product.id={product_id}"
        logger.info(f"Запрос остатков для товара '{product_name}' через report/stock/all")
        
        response = requests.get(stock_url, headers=headers)
        if response.status_code == 200:
            stock_data = response.json()
            
            if isinstance(stock_data, list):
                # Проходим по списку остатков
                for item in stock_data:
                    # Прямое значение stock
                    if 'stock' in item:
                        stock_value = float(item.get('stock', 0)) 
                        total_stock += stock_value
                        logger.info(f"Найден остаток stock для '{product_name}': {stock_value}")
                    
                    # Проверяем склады
                    if 'stockByStore' in item:
                        store_stocks = item.get('stockByStore', [])
                        for store in store_stocks:
                            if 'stock' in store:
                                store_value = float(store.get('stock', 0))
                                store_name = store.get('name', 'Неизвестный склад')
                                logger.info(f"Найден остаток на складе '{store_name}' для '{product_name}': {store_value}")
                                # Не добавляем, так как это уже учтено в общем stock
            else:
                logger.warning(f"Неожиданный формат данных об остатках для '{product_name}': {type(stock_data).__name__}")
        else:
            logger.error(f"Ошибка при запросе остатков для '{product_name}': {response.status_code} - {response.text}")
        
        # Если через первый метод не получили остатки, пробуем другой
        if total_stock == 0:
            # Метод 2: Пробуем отчет по остаткам для всех складов
            stock_url = f"https://api.moysklad.ru/api/remap/1.2/report/stock/bystore?product.id={product_id}"
            logger.info(f"Запрос остатков для товара '{product_name}' через report/stock/bystore")
            
            response = requests.get(stock_url, headers=headers)
            if response.status_code == 200:
                stock_data = response.json()
                
                if isinstance(stock_data, dict) and 'rows' in stock_data:
                    rows = stock_data.get('rows', [])
                    for row in rows:
                        if 'stock' in row:
                            stock_value = float(row.get('stock', 0))
                            total_stock += stock_value
                            store_name = row.get('name', 'Неизвестный склад')
                            logger.info(f"Найден остаток на складе '{store_name}' для '{product_name}': {stock_value}")
                else:
                    logger.warning(f"Неожиданный формат данных отчета по складам для '{product_name}': {stock_data}")
            else:
                logger.error(f"Ошибка при запросе остатков по складам для '{product_name}': {response.status_code} - {response.text}")
    
    except Exception as e:
        logger.error(f"Ошибка при получении остатков для товара '{product_name}': {str(e)}")
    
    logger.info(f"Итоговый остаток товара '{product_name}': {total_stock}")
    return total_stock

def get_stock_info(product_id: str) -> int:
    """Получить информацию о наличии товара"""
    headers = get_auth_header()
    return get_product_stock(product_id, headers) 