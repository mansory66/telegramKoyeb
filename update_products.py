import logging
import sys
import os
from logging.handlers import RotatingFileHandler

from moysklad import get_all_products
from database import Database

# Настройка логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
log_level = getattr(logging, LOG_LEVEL)

handlers = [logging.StreamHandler(sys.stdout)]  # Всегда логируем в stdout

# Создаем директорию для логов если её нет
if not os.path.exists('logs'):
    os.makedirs('logs')
    
handlers.append(
    RotatingFileHandler(
        'logs/update_products.log',
        maxBytes=10485760,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=log_level,
    handlers=handlers
)

logger = logging.getLogger(__name__)

def main():
    """Основная функция обновления товаров"""
    try:
        logger.info("Начало обновления товаров из МойСклад")
        
        # Получаем товары из МойСклад
        products = get_all_products()
        logger.info(f"Получено {len(products)} товаров из МойСклад")
        
        # Подключаемся к базе данных
        with Database() as db:
            # Получаем существующие товары
            existing_products = db.get_all_products()
            existing_product_codes = {p['code']: p for p in existing_products} if existing_products else {}
            logger.info(f"В базе данных найдено {len(existing_product_codes)} товаров")
            
            added = 0
            updated = 0
            
            # Обновляем или добавляем товары
            for product in products:
                if product['code'] in existing_product_codes:
                    # Обновляем существующий товар
                    db.update_product(
                        product_id=existing_product_codes[product['code']]['id'],
                        name=product['name'],
                        description=product.get('description', ''),
                        price=product['price'],
                        quantity=product['quantity'],
                        category_id=product.get('category_id'),
                        image_url=product.get('image_url', '')
                    )
                    updated += 1
                else:
                    # Добавляем новый товар
                    db.create_product(
                        name=product['name'],
                        code=product['code'],
                        description=product.get('description', ''),
                        price=product['price'],
                        quantity=product['quantity'],
                        category_id=product.get('category_id'),
                        image_url=product.get('image_url', '')
                    )
                    added += 1
            
            logger.info(f"Обновление завершено: добавлено {added} новых товаров, обновлено {updated} товаров")
    except Exception as e:
        logger.error(f"Ошибка при обновлении товаров: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 