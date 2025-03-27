import mysql.connector
from config import DB_CONFIG

def check_and_remove_duplicates():
    """Проверка и удаление дубликатов товаров"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    try:
        # Находим дубликаты по moysklad_id
        print("Проверяем дубликаты по moysklad_id...")
        cursor.execute("""
            SELECT 
                p1.moysklad_id,
                COUNT(*) as count,
                GROUP_CONCAT(p1.id) as ids,
                GROUP_CONCAT(DISTINCT p1.name) as names,
                GROUP_CONCAT(DISTINCT c.name) as categories,
                GROUP_CONCAT(DISTINCT CONCAT(
                    'ID:', p1.id, 
                    ' Название:', p1.name,
                    ' Кат:', IFNULL(c.name, 'Нет'),
                    ' Ост1:', p1.stock_point1,
                    ' Ост2:', p1.stock_point2,
                    ' Цена:', p1.price
                )) as details
            FROM products p1
            LEFT JOIN categories c ON p1.category_id = c.id
            GROUP BY p1.moysklad_id 
            HAVING COUNT(*) > 1
        """)
        duplicates_by_moysklad = cursor.fetchall()

        if duplicates_by_moysklad:
            print("\nНайдены дубликаты по moysklad_id:")
            for dup in duplicates_by_moysklad:
                print(f"\nMoySklad ID: {dup['moysklad_id']}")
                print(f"Количество: {dup['count']}")
                print(f"ID записей: {dup['ids']}")
                print(f"Названия: {dup['names']}")
                print(f"Категории: {dup['categories']}")
                print("Подробности:")
                for detail in dup['details'].split(','):
                    print(f"  {detail}")
                
                # Оставляем только самую последнюю запись
                ids = dup['ids'].split(',')
                latest_id = max(map(int, ids))
                
                # Удаляем все кроме последней записи
                cursor.execute("""
                    DELETE FROM products 
                    WHERE moysklad_id = %s AND id != %s
                """, (dup['moysklad_id'], latest_id))
                print(f"  ❗ Удалены дубликаты, оставлена запись с id={latest_id}")

        # Находим товары с одинаковым названием
        print("\nПроверяем товары с одинаковым названием...")
        cursor.execute("""
            SELECT 
                p1.name,
                COUNT(*) as count,
                GROUP_CONCAT(p1.id) as ids,
                GROUP_CONCAT(DISTINCT p1.moysklad_id) as moysklad_ids,
                GROUP_CONCAT(DISTINCT c.name) as categories,
                GROUP_CONCAT(DISTINCT CONCAT(
                    'ID:', p1.id, 
                    ' MoySkl:', p1.moysklad_id,
                    ' Кат:', IFNULL(c.name, 'Нет'),
                    ' Ост1:', p1.stock_point1,
                    ' Ост2:', p1.stock_point2,
                    ' Цена:', p1.price
                )) as details
            FROM products p1
            LEFT JOIN categories c ON p1.category_id = c.id
            GROUP BY p1.name 
            HAVING COUNT(*) > 1
        """)
        duplicates_by_name = cursor.fetchall()

        if duplicates_by_name:
            print("\nНайдены товары с одинаковым названием:")
            for dup in duplicates_by_name:
                print(f"\nНазвание: {dup['name']}")
                print(f"Количество: {dup['count']}")
                print(f"ID записей: {dup['ids']}")
                print(f"MoySklad ID: {dup['moysklad_ids']}")
                print(f"Категории: {dup['categories']}")
                print("Подробности:")
                for detail in dup['details'].split(','):
                    print(f"  {detail}")

                # Если у товаров разные moysklad_id, это разные товары
                if len(set(dup['moysklad_ids'].split(','))) > 1:
                    print("  ⚠️ Разные moysklad_id - возможно это разные товары")
                else:
                    print("  ❗ Одинаковый moysklad_id - вероятно дубликат")

        if not duplicates_by_moysklad and not duplicates_by_name:
            print("\nДубликатов не найдено")

        conn.commit()
        print("\nПроверка завершена")

    except Exception as e:
        print(f"Ошибка при проверке дубликатов: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("Начинаем проверку дубликатов...")
    check_and_remove_duplicates()
    print("Проверка завершена") 