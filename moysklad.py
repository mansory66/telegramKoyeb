import logging
import requests
import base64
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
        url = "https://online.moysklad.ru/api/remap/1.2/entity/product"
        headers = get_auth_header()
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Ошибка при получении товаров из МойСклад: {response.text}")
            return []
        
        data = response.json()
        products = []
        
        for item in data.get('rows', []):
            # Получение цены товара
            price = 0
            try:
                if 'salePrices' in item and len(item['salePrices']) > 0:
                    # Цена в МойСклад хранится в копейках, поэтому делим на 100
                    price = item['salePrices'][0]['value'] / 100
            except Exception as e:
                logger.error(f"Ошибка при получении цены товара: {str(e)}")
            
            # Получение количества товара
            quantity = 0
            try:
                stock_url = f"https://online.moysklad.ru/api/remap/1.2/report/stock/all?product.id={item['id']}"
                stock_response = requests.get(stock_url, headers=headers)
                
                if stock_response.status_code == 200:
                    stock_data = stock_response.json()
                    if len(stock_data) > 0:
                        quantity = stock_data[0].get('quantity', 0)
            except Exception as e:
                logger.error(f"Ошибка при получении остатков товара: {str(e)}")
            
            # Формирование данных о товаре, генерируем код если его нет
            product_code = item.get('code', '')
            if not product_code:
                # Если код отсутствует, генерируем его из id или другого уникального поля
                product_code = f"ID_{item.get('id', '')[-6:]}"
                logger.warning(f"Для товара '{item.get('name', '')}' код отсутствует, сгенерирован: {product_code}")
            
            product = {
                'name': item.get('name', ''),
                'code': product_code,
                'description': item.get('description', ''),
                'price': price,
                'quantity': quantity,
                'category_id': None,  # Нужно сопоставить с категориями в вашей базе данных
                'image_url': ''  # Добавить получение изображений при необходимости
            }
            
            products.append(product)
        
        return products
    except Exception as e:
        logger.error(f"Ошибка при работе с API МойСклад: {str(e)}")
        return []

def get_stock_info(product_id: str) -> int:
    """Получить информацию о наличии товара"""
    try:
        response = requests.get(
            f"https://online.moysklad.ru/api/remap/1.2/entity/product/{product_id}/positions",
            auth=HTTPBasicAuth(MOYSKLAD_LOGIN, MOYSKLAD_PASSWORD)
        )
        response.raise_for_status()
        data = response.json()
        
        return data.get('quantity', 0)
        
    except Exception as e:
        logger.error(f"Ошибка при получении остатков товара {product_id}: {str(e)}")
        return 0 