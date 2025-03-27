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
                # Получение цены товара
                price = 0
                try:
                    if 'salePrices' in item and len(item['salePrices']) > 0:
                        # Цена в МойСклад хранится в копейках, поэтому делим на 100
                        price = item['salePrices'][0]['value'] / 100
                except Exception as e:
                    logger.error(f"Ошибка при получении цены товара {item.get('name', '')}: {str(e)}")
                
                # Получение количества товара с исправленной логикой обработки ответа
                quantity = 0
                try:
                    stock_url = f"https://api.moysklad.ru/api/remap/1.2/report/stock/all?product.id={item['id']}"
                    stock_response = requests.get(stock_url, headers=headers)
                    
                    logger.info(f"Запрос остатков для товара {item.get('name')}: {stock_url}")
                    
                    if stock_response.status_code == 200:
                        stock_data = stock_response.json()
                        
                        # Более детальное логирование при отладке
                        if logger.level == logging.DEBUG:
                            logger.debug(f"Данные о количестве товара {item.get('name')}: {json.dumps(stock_data, ensure_ascii=False)}")
                        
                        # Проверяем наличие данных и исправляем парсинг
                        if isinstance(stock_data, list) and len(stock_data) > 0:
                            for stock_item in stock_data:
                                if 'stock' in stock_item:
                                    quantity += stock_item.get('stock', 0)
                                    logger.info(f"Найден остаток 'stock': {stock_item.get('stock', 0)}")
                                elif 'quantity' in stock_item:
                                    quantity += stock_item.get('quantity', 0)
                                    logger.info(f"Найден остаток 'quantity': {stock_item.get('quantity', 0)}")
                                # Добавляем поле stockByStore если доступно
                                if 'stockByStore' in stock_item:
                                    for store_stock in stock_item['stockByStore']:
                                        if 'stock' in store_stock:
                                            store_quantity = store_stock.get('stock', 0)
                                            quantity += store_quantity
                                            store_name = store_stock.get('name', 'Неизвестный склад')
                                            logger.info(f"Найден остаток по складу '{store_name}': {store_quantity}")
                except Exception as e:
                    logger.error(f"Ошибка при получении остатков товара {item.get('name', '')}: {str(e)}")
                
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

def get_stock_info(product_id: str) -> int:
    """Получить информацию о наличии товара"""
    try:
        # Используем правильный URL для получения остатка товара
        url = f"https://api.moysklad.ru/api/remap/1.2/report/stock/all?product.id={product_id}"
        headers = get_auth_header()
        logger.info(f"Запрос остатков для товара {product_id}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        if logger.level == logging.DEBUG:
            logger.debug(f"Данные о количестве товара {product_id}: {json.dumps(data, ensure_ascii=False)}")
        
        total_stock = 0
        # Проверяем формат ответа и извлекаем остатки
        if isinstance(data, list):
            for item in data:
                if 'stock' in item:
                    total_stock += item.get('stock', 0)
                elif 'quantity' in item:
                    total_stock += item.get('quantity', 0)
                # Добавляем поддержку поля stockByStore
                if 'stockByStore' in item:
                    for store_stock in item['stockByStore']:
                        total_stock += store_stock.get('stock', 0)
        
        logger.info(f"Общий остаток товара {product_id}: {total_stock}")
        return total_stock
    except Exception as e:
        logger.error(f"Ошибка при получении информации о наличии: {str(e)}")
        return 0 