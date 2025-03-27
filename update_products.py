import logging
import sys
import os
from logging.handlers import RotatingFileHandler

from moysklad import get_all_products
from database import Database
from config import LOG_LEVEL_CODE

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
        if not products:
            logger.warning("Не удалось получить товары из МойСклад или список товаров пуст")
            return False
            
        logger.info(f"Получено {len(products)} товаров из МойСклад")
        
        # Подключаемся к базе данных
        with Database() as db:
            # Получаем существующие товары
            try:
                existing_products = db.get_all_products()
                existing_product_codes = {p['code']: p for p in existing_products} if existing_products else {}
                logger.info(f"В базе данных найдено {len(existing_product_codes)} товаров")
            except Exception as e:
                logger.error(f"Ошибка при получении существующих товаров: {str(e)}")
                return False
            
            added = 0
            updated = 0
            errors = 0
            
            # Обновляем или добавляем товары
            for product in products:
                try:
                    if not product.get('code'):
                        logger.warning(f"Пропускаем товар без кода: {product.get('name', 'Неизвестный товар')}")
                        continue
                        
                    if product['code'] in existing_product_codes:
                        # Обновляем существующий товар
                        result = db.update_product(
                            product_id=existing_product_codes[product['code']]['id'],
                            name=product['name'],
                            description=product.get('description', ''),
                            price=product['price'],
                            quantity=product['quantity'],
                            category_id=product.get('category_id'),
                            image_url=product.get('image_url', '')
                        )
                        if result:
                            updated += 1
                        else:
                            errors += 1
                    else:
                        # Добавляем новый товар
                        result = db.create_product(
                            name=product['name'],
                            code=product['code'],
                            description=product.get('description', ''),
                            price=product['price'],
                            quantity=product['quantity'],
                            category_id=product.get('category_id'),
                            image_url=product.get('image_url', '')
                        )
                        if result:
                            added += 1
                        else:
                            errors += 1
                except Exception as e:
                    logger.error(f"Ошибка при обработке товара {product.get('name', 'Неизвестный товар')}: {str(e)}")
                    errors += 1
            
            logger.info(f"Обновление завершено: добавлено {added} новых товаров, обновлено {updated} товаров, ошибок: {errors}")
            return errors == 0  # Возвращаем True, если не было ошибок
    except Exception as e:
        logger.error(f"Ошибка при обновлении товаров: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 