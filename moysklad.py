import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MoySklad:
    def __init__(self, login: str, password: str):
        self.base_url = "https://online.moysklad.ru/api/remap/1.2"
        self.auth = (login, password)
        
    def get_all_products(self) -> List[Dict[str, Any]]:
        """Получить все товары из МойСклад"""
        try:
            response = requests.get(
                f"{self.base_url}/entity/product",
                auth=self.auth
            )
            response.raise_for_status()
            data = response.json()
            
            products = []
            for item in data.get('rows', []):
                product = {
                    'name': item.get('name'),
                    'description': item.get('description', ''),
                    'price': float(item.get('salePrices', [{}])[0].get('value', 0)) / 100 if item.get('salePrices') else 0,
                    'article': item.get('article', ''),
                    'stock': item.get('quantity', 0),
                    # Добавьте дополнительные поля, которые вам нужны
                }
                products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Ошибка при получении товаров из МойСклад: {str(e)}")
            return []

    def get_stock_info(self, product_id: str) -> int:
        """Получить информацию о наличии товара"""
        try:
            response = requests.get(
                f"{self.base_url}/entity/product/{product_id}/positions",
                auth=self.auth
            )
            response.raise_for_status()
            data = response.json()
            
            return data.get('quantity', 0)
            
        except Exception as e:
            logger.error(f"Ошибка при получении остатков товара {product_id}: {str(e)}")
            return 0 