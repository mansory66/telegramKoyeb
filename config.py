import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройки Telegram бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "7624944977:AAEsNgBqplefNXU8l5tTPSzoXn0CpzFn9I8")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@puff_smoketlt")

# Настройки платежа
PAYMENT_INFO = {
    'phone': os.getenv("PAYMENT_PHONE", "89967394080"),
    'bank': os.getenv("PAYMENT_BANK", "ТИНЬКОФФ")
}

# Настройки базы данных
DB_CONFIG = {
    'host': os.getenv("DB_HOST", 'FVH1.spaceweb.ru'),
    'user': os.getenv("DB_USER", 'antonprozd'),
    'password': os.getenv("DB_PASSWORD", 'Qweasdzxc_123'),
    'database': os.getenv("DB_NAME", 'antonprozd'),
    'port': int(os.getenv("DB_PORT", 3306))
}

# Адреса магазинов
SHOP_ADDRESSES = {
    1: os.getenv("SHOP_ADDRESS_1", "Дзержинского 16"),
    2: os.getenv("SHOP_ADDRESS_2", "Степана Разина 60д")
}

# Список администраторов
ADMIN_USERNAMES = os.getenv("ADMIN_USERNAMES", "BrabusGT,apoli1nariaa").split(",")

# Настройки МойСклад
MOYSKLAD_LOGIN = os.getenv("MOYSKLAD_LOGIN", "admin@nulia49121")  # Логин МойСклад
MOYSKLAD_PASSWORD = os.getenv("MOYSKLAD_PASSWORD", "228674Polina")  # Пароль МойСклад

# Сообщения бота
WELCOME_MESSAGE = """
Добро пожаловать в магазин PUFF SMOKE! 🌬️

Мы предлагаем широкий ассортимент товаров высокого качества.
Для продолжения необходимо подписаться на наш канал.
"""

SUBSCRIPTION_MESSAGE = """
Для использования бота необходимо подписаться на наш канал.
Нажмите кнопку ниже, чтобы подписаться.
"""

CATEGORIES_MESSAGE = """
Выберите категорию товаров:
""" 