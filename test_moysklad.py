import logging
import requests
import json
import sys
from moysklad import get_auth_header, get_all_products

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def test_api_format():
    """Проверка формата данных API МойСклад"""
    headers = get_auth_header()
    
    # Тест 1: Получение списка товаров
    try:
        url = "https://api.moysklad.ru/api/remap/1.2/entity/product"
        logger.info(f"Выполняем запрос к API: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Получено товаров: {len(data.get('rows', []))}")
            
            # Проверяем первый товар
            if data.get('rows') and len(data.get('rows')) > 0:
                first_product = data.get('rows')[0]
                logger.info(f"Первый товар: {first_product.get('name')}")
                logger.info(f"Структура первого товара: {json.dumps(first_product, indent=2, ensure_ascii=False)[:500]}...")
                
                # Тест 2: Проверка остатков для первого товара
                product_id = first_product.get('id')
                if product_id:
                    test_stock_format(product_id, headers)
        else:
            logger.error(f"Ошибка при запросе списка товаров: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Ошибка при тестировании API: {str(e)}")

def test_stock_format(product_id, headers):
    """Проверка формата данных об остатках"""
    stock_url = f"https://api.moysklad.ru/api/remap/1.2/report/stock/all?product.id={product_id}"
    logger.info(f"Получение остатков для товара: {stock_url}")
    
    try:
        stock_response = requests.get(stock_url, headers=headers)
        
        if stock_response.status_code == 200:
            stock_data = stock_response.json()
            logger.info(f"Формат данных об остатках: {json.dumps(stock_data, indent=2, ensure_ascii=False)}")
            
            # Анализ структуры данных
            if isinstance(stock_data, list):
                logger.info(f"Данные об остатках представлены в виде списка, элементов: {len(stock_data)}")
                
                for i, item in enumerate(stock_data):
                    logger.info(f"Элемент {i+1}: ключи {', '.join(item.keys())}")
                    
                    # Проверяем наличие ключей для остатков
                    stock_field = None
                    if 'stock' in item:
                        stock_field = 'stock'
                        logger.info(f"Найдено поле 'stock': {item['stock']}")
                    elif 'quantity' in item:
                        stock_field = 'quantity'
                        logger.info(f"Найдено поле 'quantity': {item['quantity']}")
                    
                    # Проверяем наличие остатков по складам
                    if 'stockByStore' in item:
                        logger.info(f"Найдено поле 'stockByStore', элементов: {len(item['stockByStore'])}")
                        for j, store in enumerate(item['stockByStore']):
                            store_stock = store.get('stock', 0)
                            store_name = store.get('name', 'Неизвестный склад')
                            logger.info(f"  - Склад {j+1}: {store_name} = {store_stock}")
            else:
                logger.warning(f"Неожиданный формат данных об остатках: {type(stock_data).__name__}")
        else:
            logger.error(f"Ошибка при запросе остатков: {stock_response.status_code} - {stock_response.text}")
    except Exception as e:
        logger.error(f"Ошибка при получении информации об остатках: {str(e)}")

if __name__ == "__main__":
    logger.info("Запуск тестирования API МойСклад")
    test_api_format()
    logger.info("Тестирование API МойСклад завершено") 