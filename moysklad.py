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
        
        logger.info("Запрос списка товаров из МойСклад")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Ошибка API МойСклад: {response.status_code}")
            if logger.level <= logging.DEBUG:
                logger.debug(f"Текст ошибки: {response.text}")
            return []
        
        data = response.json()
        products_count = len(data.get('rows', []))
        logger.info(f"Получено {products_count} товаров из МойСклад")
        products = []
        
        for index, item in enumerate(data.get('rows', [])):
            try:
                product_id = item.get('id')
                product_name = item.get('name', 'Неизвестный товар')
                
                if not product_id:
                    logger.warning(f"Товар без ID: {product_name}, пропускаем")
                    continue
                
                # Получение цены товара
                price = 0
                if 'salePrices' in item and len(item['salePrices']) > 0:
                    # Цена в МойСклад хранится в копейках, поэтому делим на 100
                    price = item['salePrices'][0]['value'] / 100
                
                # Получение количества товара с учетом всех методов API
                quantity = get_product_stock(product_id, headers, product_name)
                
                # Формирование данных о товаре, генерируем код если его нет
                product_code = item.get('code', '')
                if not product_code:
                    # Если код отсутствует, генерируем его из id или другого уникального поля
                    product_code = f"ID_{item.get('id', '')[-6:]}"
                    logger.debug(f"Сгенерирован код для товара '{product_name}': {product_code}")
                
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
                    'name': product_name,
                    'code': product_code,
                    'description': description,
                    'price': price,
                    'quantity': quantity,
                    'category_id': None,
                    'image_url': ''
                }
                
                # Только в режиме DEBUG логируем каждый товар
                if logger.level <= logging.DEBUG:
                    logger.debug(f"Обработан товар #{index+1}: {product_name}, цена: {price}, остаток: {quantity}")
                
                # В режиме INFO логируем прогресс каждые 50 товаров
                if index % 50 == 0 and index > 0 and logger.level <= logging.INFO:
                    logger.info(f"Обработано {index} товаров из {products_count}...")
                
                products.append(product)
            except Exception as e:
                logger.error(f"Ошибка обработки товара '{item.get('name', '')}': {str(e)}")
        
        logger.info(f"Успешно обработано {len(products)} товаров из {products_count}")
        return products
    except Exception as e:
        logger.error(f"Ошибка при работе с API МойСклад: {str(e)}")
        return []

def get_product_stock(product_id, headers, product_name=''):
    """Получение остатков конкретного товара"""
    try:
        # МЕТОД 1: /report/stock/all - прямой метод получения
        # Этот метод возвращает остатки всех товаров, но мы фильтруем по ID
        stock_url = f"https://api.moysklad.ru/api/remap/1.2/report/stock/all?product.id={product_id}"
        
        response = requests.get(stock_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            
            # В API МойСклад ответ приходит в виде списка, даже если это один товар
            if isinstance(data, list):
                # Просматриваем все элементы и ищем наш товар
                for item in data:
                    # Проверяем наличие поля stock
                    if 'stock' in item:
                        # В поле stock хранится числовое значение остатка
                        stock_value = float(item.get('stock', 0))
                        if logger.level <= logging.DEBUG:
                            logger.debug(f"Товар '{product_name}': остаток = {stock_value}")
                        return stock_value
            
            # Если не нашли остаток через первый метод, возвращаем 0
            # или можно попробовать другой метод (ниже)
            return 0
        
        # МЕТОД 2: /report/stock/bystore
        # Если первый метод не сработал или не дал результатов, пробуем 
        # получить остатки по складам и суммировать их
        stock_url = f"https://api.moysklad.ru/api/remap/1.2/report/stock/bystore?product.id={product_id}"
        
        response = requests.get(stock_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            
            # Проверяем, что в ответе есть поле rows
            if isinstance(data, dict) and 'rows' in data:
                rows = data.get('rows', [])
                
                # Инициализируем общий остаток
                total_stock = 0
                
                # Суммируем остатки по всем складам
                for row in rows:
                    # В каждой строке проверяем наличие поля stockByStore
                    if 'stockByStore' in row:
                        # stockByStore - это список остатков по складам
                        stores = row.get('stockByStore', [])
                        for store in stores:
                            # Для каждого склада проверяем наличие положительного остатка
                            if 'stock' in store and store.get('stock', 0) > 0:
                                # Добавляем остаток к общему количеству
                                total_stock += float(store.get('stock', 0))
                
                if total_stock > 0 and logger.level <= logging.DEBUG:
                    logger.debug(f"Товар '{product_name}': общий остаток по складам = {total_stock}")
                
                return total_stock
        
        # Если не получилось найти остатки ни одним из методов, возвращаем 0
        return 0
    except Exception as e:
        logger.error(f"Ошибка при получении остатков для '{product_name}': {str(e)}")
        return 0

def get_stock_info(product_id: str) -> int:
    """Получить информацию о наличии товара"""
    headers = get_auth_header()
    return get_product_stock(product_id, headers) 