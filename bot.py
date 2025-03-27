# Стандартные библиотеки
import asyncio
import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
import datetime
import hashlib
import random
import re
from decimal import Decimal

# Сторонние библиотеки
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Локальные импорты
from config import (
    BOT_TOKEN, CHANNEL_USERNAME, SHOP_ADDRESSES, 
    ADMIN_USERNAMES, PAYMENT_INFO, 
    MOYSKLAD_LOGIN, MOYSKLAD_PASSWORD,
    WELCOME_MESSAGE,
    SUBSCRIPTION_MESSAGE, CATEGORIES_MESSAGE,
    LOG_LEVEL_CODE
)
from database import Database
from update_products import main as update_products_from_moysklad

# Поддерживаемые языки
LANGUAGES = {
    'ru': 'Русский',
    'en': 'English',
    'uz': 'O\'zbek'
}

# Словарь с текстами на разных языках
TEXTS = {
    'ru': {
        'welcome': 'Добро пожаловать!',
        'profile': 'Ваш профиль',
        'feedback': 'Обратная связь',
        'categories': 'Категории',
        'back': 'Назад',
        'main_menu': 'Главное меню',
        'error': 'Произошла ошибка',
        'try_later': 'Попробуйте позже',
        'subscription_required': 'Требуется подписка',
        'not_subscribed': 'Вы не подписаны',
        'subscribe_first': 'Сначала подпишитесь',
        'check_subscription': 'Проверить подписку',
        'success': 'Успешно',
        'cancel': 'Отмена',
        'save': 'Сохранить',
        'edit': 'Изменить',
        'delete': 'Удалить'
    },
    'en': {
        'welcome': 'Welcome!',
        'profile': 'Your Profile',
        'feedback': 'Feedback',
        'categories': 'Categories',
        'back': 'Back',
        'main_menu': 'Main Menu',
        'error': 'Error occurred',
        'try_later': 'Try again later',
        'subscription_required': 'Subscription required',
        'not_subscribed': 'You are not subscribed',
        'subscribe_first': 'Please subscribe first',
        'check_subscription': 'Check subscription',
        'success': 'Success',
        'cancel': 'Cancel',
        'save': 'Save',
        'edit': 'Edit',
        'delete': 'Delete'
    },
    'uz': {
        'welcome': 'Xush kelibsiz!',
        'profile': 'Sizning profilingiz',
        'feedback': 'Fikr-mulohaza',
        'categories': 'Kategoriyalar',
        'back': 'Orqaga',
        'main_menu': 'Asosiy menyu',
        'error': 'Xato yuz berdi',
        'try_later': 'Keyinroq urinib ko\'ring',
        'subscription_required': 'Obuna talab qilinadi',
        'not_subscribed': 'Siz obuna bo\'lmagansiz',
        'subscribe_first': 'Avval obuna bo\'ling',
        'check_subscription': 'Obunani tekshirish',
        'success': 'Muvaffaqiyatli',
        'cancel': 'Bekor qilish',
        'save': 'Saqlash',
        'edit': 'O\'zgartirish',
        'delete': 'O\'chirish'
    }
}

def get_text(key: str, lang: str = 'ru') -> str:
    """
    Получает текст по ключу для указанного языка
    
    Args:
        key (str): Ключ текста
        lang (str): Код языка (ru/en/uz)
        
    Returns:
        str: Текст на указанном языке
    """
    return TEXTS.get(lang, TEXTS['ru']).get(key, TEXTS['ru'].get(key, key))

# Настройка логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
log_level = getattr(logging, LOG_LEVEL)

handlers = [logging.StreamHandler(sys.stdout)]  # Всегда логируем в stdout

# Создаем директорию для логов и добавляем файловый хендлер только если мы не на Koyeb
if not os.getenv("KOYEB", False) and not os.path.exists('logs'):
    os.makedirs('logs')
    
    # Добавляем файловый хендлер только если не на Koyeb
    if not os.getenv("KOYEB", False):
        handlers.append(
            RotatingFileHandler(
                'logs/bot.log',
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

PROFILE_MESSAGE = """
👤 *Ваш профиль*

🔹 Имя пользователя: {username}
🔹 Количество заказов: {orders_count}
🔹 Язык: {language}
"""

# Инициируем обновление товаров из МойСклад при запуске бота
try:
    logger.info("Запуск обновления товаров из МойСклад при старте бота")
    update_result = update_products_from_moysklad()
    if update_result:
        logger.info("Обновление товаров из МойСклад успешно выполнено")
    else:
        logger.warning("Не удалось обновить товары из МойСклад")
except Exception as e:
    logger.error(f"Ошибка при обновлении товаров из МойСклад: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info(f"Получена команда /start от пользователя {update.effective_user.id}")
        keyboard = [
            [InlineKeyboardButton("Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("Проверить подписку", callback_data="check_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Добро пожаловать в магазин PUFF SMOKE! 🌬️\n"
            "Для использования бота необходимо подписаться на наш канал.",
            reply_markup=reply_markup
        )
        logger.info(f"Отправлено приветственное сообщение пользователю {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Ошибка в функции start: {str(e)}")
        await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже или обратитесь к администратору.")

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        user_id = query.from_user.id
        logger.info(f"Проверка подписки для пользователя {user_id}")
        
        # Пропускаем проверку подписки для администраторов
        if query.from_user.username in ADMIN_USERNAMES:
            logger.info(f"Пользователь {user_id} является администратором, пропускаем проверку подписки")
            await show_main_menu(update, context)
            return
        
        # Проверка подписки на канал
        try:
            logger.info(f"Попытка проверить статус участника в канале {CHANNEL_USERNAME}")
            member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
            logger.info(f"Статус пользователя в канале: {member.status}")
            is_subscribed = member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logger.error(f"Ошибка при проверке подписки: {str(e)}")
            is_subscribed = False

        logger.info(f"Результат проверки подписки: {is_subscribed}")

        if is_subscribed:
            try:
                # Временно отключаем работу с базой данных
                await show_main_menu(update, context)
            except Exception as e:
                logger.error(f"Ошибка при показе главного меню: {str(e)}")
                await query.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
        else:
            logger.info("Пользователь не подписан на канал")
            await query.answer("Вы не подписаны на канал! Подпишитесь и попробуйте снова.", show_alert=True)
    except Exception as e:
        logger.error(f"Общая ошибка в check_subscription: {str(e)}")
        if query:
            await query.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("📦 Актуальное наличие", callback_data="show_categories")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📝 Обратная связь", callback_data="feedback")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(
            "Главное меню PUFF SMOKE 🏪",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "Главное меню PUFF SMOKE 🏪",
            reply_markup=reply_markup
        )

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает категории или подкатегории"""
    query = update.callback_query
    
    # Получаем parent_id из callback_data
    parent_id = None
    if query.data != "show_categories":
        # Формат может быть: category_list_[parent_id] или category_[id]
        parts = query.data.split('_')
        if len(parts) > 2 and parts[1] == "list":
            parent_id = int(parts[2])
        elif len(parts) == 2:
            parent_id = int(parts[1])
    
    with Database() as db:
        categories = db.get_categories(parent_id)
        # Проверяем, есть ли товары в текущей категории
        products = db.get_products_by_category(parent_id) if parent_id else []
    
    keyboard = []
    
    # Добавляем товары, если они есть
    if products:
        for product in products:
            keyboard.append([InlineKeyboardButton(f"📦 {product['name']}", 
                                               callback_data=f"product_{product['id']}")])
    
    # Добавляем подкатегории
    for category in categories:
        keyboard.append([InlineKeyboardButton(f"📁 {category['name']}", 
                                           callback_data=f"category_list_{category['id']}")])
    
    # Кнопка "Назад"
    if parent_id:
        # Получаем родительскую категорию текущей категории
        with Database() as db:
            current_category = db.get_category(parent_id)
            parent_category_id = current_category.get('parent_id') if current_category else None
        
        if parent_category_id:
            keyboard.append([InlineKeyboardButton("🔙 Назад", 
                                               callback_data=f"category_list_{parent_category_id}")])
        else:
            keyboard.append([InlineKeyboardButton("🔙 Назад", 
                                               callback_data="show_categories")])
    else:
        keyboard.append([InlineKeyboardButton("🔙 В главное меню", 
                                           callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Формируем заголовок
    if parent_id:
        with Database() as db:
            category = db.get_category(parent_id)
        header = f"Категория: {category['name'] if category else 'Неизвестная категория'}"
    else:
        header = "Выберите категорию:"
    
    await query.edit_message_text(header, reply_markup=reply_markup)

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    category_id = int(query.data.split('_')[1])
    
    with Database() as db:
        products = db.get_products_by_category(category_id)
    
    keyboard = []
    for product in products:
        keyboard.append([InlineKeyboardButton(product['name'], callback_data=f"product_{product['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="show_categories")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите товар:", reply_markup=reply_markup)

async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = int(query.data.split('_')[1])
    
    with Database() as db:
        product = db.get_product(product_id)
    
    availability = []
    if product['stock_point1']:
        availability.append(f"✅ {SHOP_ADDRESSES[1]}")
    else:
        availability.append(f"❌ {SHOP_ADDRESSES[1]}")
    if product['stock_point2']:
        availability.append(f"✅ {SHOP_ADDRESSES[2]}")
    else:
        availability.append(f"❌ {SHOP_ADDRESSES[2]}")

    message = (
        f"📦 {product['name']}\n\n"
        f"📝 Описание: {product['description']}\n"
        f"💰 Цена: {product['price']} руб.\n"
        f"💨 Крепость: {product['strength'] if product['strength'] else 'Не указана'}\n\n"
        f"📍 Наличие:\n{availability[0]}\n{availability[1]}"
    )

    keyboard = []
    if product['stock_point1'] or product['stock_point2']:
        keyboard.append([InlineKeyboardButton("🚚 Купить с доставкой", callback_data=f"buy_{product_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"category_{product['category_id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup)

async def process_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    product_id = int(query.data.split('_')[1])
    
    with Database() as db:
        product = db.get_product(product_id)
    
    message = (
        "🚚 Информация о доставке:\n\n"
        "1. Доставка осуществляется курьерской службой\n"
        "2. Товар надежно упакован и защищен от вскрытия\n"
        "3. Оплата производится переводом на карту\n\n"
        f"💰 Сумма к оплате: {product['price']} руб."
    )

    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить заказ", callback_data=f"confirm_{product_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"product_{product_id}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup)

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение заказа пользователем"""
    query = update.callback_query
    product_id = int(query.data.split('_')[1])
    user_id = query.from_user.id
    
    with Database() as db:
        user = db.get_user(user_id)
        product = db.get_product(product_id)
        order_id = db.create_order(user['id'], product_id, 1)  # По умолчанию с первой точки
    
    payment_info = (
        "💳 Информация об оплате:\n\n"
        f"Сумма: {product['price']} руб.\n"
        f"Банк: {PAYMENT_INFO['bank']}\n"
        f"Номер телефона: {PAYMENT_INFO['phone']}\n\n"
        "После оплаты, пожалуйста:\n"
        f"1. Напишите @{ADMIN_USERNAMES[0]}\n"
        "2. Отправьте скриншот или чек об оплате\n"
        "3. Укажите номер заказа: #" + str(order_id)
    )

    keyboard = [
        [InlineKeyboardButton("✅ Я оплатил заказ", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton("❌ Отменить заказ", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(payment_info, reply_markup=reply_markup)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает профиль пользователя"""
    user = update.effective_user
    
    with Database() as db:
        user_data = db.get_user(user.id)
        orders_count = db.get_user_orders_count(user.id)
        
        # Если у пользователя нет языка в базе, устанавливаем русский по умолчанию
        if not user_data or 'language' not in user_data:
            user_data = {'language': 'ru'}
            if not user_data:  # Если пользователя нет в базе, создаем его
                db.create_user(user.id, user.username or '', 'ru')
    
    message = PROFILE_MESSAGE.format(
        username=user.username or "Не указан",
        orders_count=orders_count,
        language=LANGUAGES[user_data['language']]
    )
    
    keyboard = [
        [InlineKeyboardButton("🌐 Изменить язык", callback_data="language")],
        [InlineKeyboardButton("📦 Мои заказы", callback_data="orders")],
        [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /admin с улучшенной безопасностью"""
    try:
        message_text = update.message.text
        user = update.effective_user
        logger.info(f"Попытка входа в админ-панель от пользователя {user.username} (ID: {user.id})")

        # Проверка формата команды
        if not message_text.startswith("/admin "):
            logger.warning(f"Неверный формат команды от пользователя {user.username}")
            await update.message.delete()
            return

        # Проверка прав администратора
        if user.username not in ADMIN_USERNAMES:
            logger.warning(f"Попытка входа от неавторизованного пользователя {user.username}")
            await update.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⛔️ Доступ запрещен. Попытка несанкционированного доступа зарегистрирована.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Вернуться в меню", callback_data="main_menu")
                ]])
            )
            # Уведомление других админов о попытке взлома
            for admin in ADMIN_USERNAMES:
                if admin != user.username:
                    await context.bot.send_message(
                        chat_id=f"@{admin}",
                        text=f"🚨 Внимание! Попытка входа в админ-панель\n"
                             f"От: @{user.username}\n"
                             f"ID: {user.id}\n"
                             f"Время: {update.message.date.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
            return

        # Парсинг введенных данных
        try:
            auth_data = message_text.replace("/admin ", "").strip().split()
            if len(auth_data) != 2:
                raise ValueError("Неверный формат аутентификации")
            password, auth_code = auth_data
        except Exception:
            logger.warning(f"Неверный формат аутентификации от админа {user.username}")
            await update.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Неверный формат. Используйте: /admin [пароль] [код аутентификации]"
            )
            return

        # Проверка пароля и кода аутентификации
        admin_password = "TestAdmin"  # В реальном проекте должен быть в защищенной конфигурации
        current_hour = update.message.date.strftime('%H')
        current_auth_code = f"PS{current_hour}2024"  # Динамический код, меняющийся каждый час

        if password != admin_password or auth_code != current_auth_code:
            logger.warning(f"Неверный пароль или код аутентификации от админа {user.username}")
            await update.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Неверный пароль или код аутентификации"
            )
            return

        # Если все проверки пройдены, показываем админ-панель
        logger.info(f"Успешный вход в админ-панель: {user.username}")
        keyboard = [
            [InlineKeyboardButton("📋 Ожидающие заказы", callback_data="admin_orders")],
            [InlineKeyboardButton("📦 Управление товарами", callback_data="admin_products")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🔒 Выйти", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.delete()
        admin_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "🔐 Админ-панель\n\n"
                f"👤 Администратор: @{user.username}\n"
                f"⏰ Время входа: {update.message.date.strftime('%H:%M:%S')}\n"
                "ℹ️ Для выхода нажмите кнопку 'Выйти'"
            ),
            reply_markup=reply_markup
        )
        
        # Уведомление других админов о входе
        for admin in ADMIN_USERNAMES:
            if admin != user.username:
                await context.bot.send_message(
                    chat_id=f"@{admin}",
                    text=f"ℹ️ Администратор @{user.username} вошел в панель управления\n"
                         f"⏰ Время: {update.message.date.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            
    except Exception as e:
        logger.error(f"Критическая ошибка в команде admin: {str(e)}")
        if update and update.message:
            await update.message.reply_text("Произошла ошибка при обработке команды. Попробуйте позже.")

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список ожидающих заказов"""
    query = update.callback_query
    if query.from_user.username not in ADMIN_USERNAMES:
        await query.answer("Доступ запрещен", show_alert=True)
        return

    with Database() as db:
        # Получаем как ожидающие, так и оплаченные заказы
        orders = db.get_pending_orders()

    if not orders:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]]
        await query.edit_message_text("Нет заказов на подтверждение", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    message = "📋 Заказы на подтверждение:\n\n"
    keyboard = []
    
    for order in orders:
        status_emoji = "💰" if order['status'] == 'paid' else "⏳"
        message += (
            f"{status_emoji} Заказ #{order['id']}\n"
            f"Товар: {order['product_names']}\n"
            f"Клиент: @{order['username']}\n"
            f"Статус: {'Оплачен' if order['status'] == 'paid' else 'Ожидает'}\n"
            "➖➖➖➖➖➖➖➖➖➖\n"
        )
        keyboard.append([InlineKeyboardButton(
            f"✅ Подтвердить #{order['id']}", 
            callback_data=f"admin_confirm_{order['id']}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")])
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление товарами"""
    query = update.callback_query
    if query.from_user.username not in ADMIN_USERNAMES:
        await query.answer("Доступ запрещен", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton("📝 Изменить наличие", callback_data="admin_edit_stock")],
        [InlineKeyboardButton("❌ Удалить товар", callback_data="admin_delete_product")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
    ]
    await query.edit_message_text("📦 Управление товарами:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику"""
    query = update.callback_query
    if query.from_user.username not in ADMIN_USERNAMES:
        await query.answer("Доступ запрещен", show_alert=True)
        return

    with Database() as db:
        total_orders = len(db.get_all_orders())
        pending_orders = len(db.get_pending_orders())
        total_users = len(db.get_all_users())
        
    message = (
        "📊 Статистика магазина:\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📦 Всего заказов: {total_orders}\n"
        f"⏳ Ожидают обработки: {pending_orders}\n"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение заказа администратором"""
    query = update.callback_query
    order_id = int(query.data.split('_')[2])
    
    with Database() as db:
        db.update_order_status(order_id, "confirmed")
        order = db.get_order(order_id)
        
        # Отправляем уведомление пользователю
        try:
            await context.bot.send_message(
                chat_id=order['user_telegram_id'],
                text=f"✅ Ваш заказ #{order_id} подтвержден!\n\n"
                     f"📦 Как получить заказ:\n\n"
                     f"1️⃣ Закажите доставку через приложение:\n"
                     f"   • Яндекс Go\n"
                     f"   • InDriver\n\n"
                     f"2️⃣ Процесс доставки:\n"
                     f"   • Водитель приедет к нашей точке\n"
                     f"   • Мы передадим ему ваш заказ\n"
                     f"   • Он доставит его прямо к вам домой\n\n"
                     f"💡 Преимущества такой доставки:\n"
                     f"   • Быстро и надежно\n"
                     f"   • Вы сами выбираете удобное время\n"
                     f"   • Отслеживание заказа в реальном времени\n"
                     f"   • Конфиденциальность гарантирована\n\n"
                     f"📞 Наш менеджер свяжется с вами для:\n"
                     f"   • Подтверждения готовности заказа\n"
                     f"   • Координации процесса доставки\n"
                     f"   • Ответов на ваши вопросы"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю: {str(e)}")
    
    # Обновляем список заказов
    await admin_orders(update, context)

async def paid_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения оплаты от пользователя"""
    query = update.callback_query
    order_id = int(query.data.split('_')[1])
    
    with Database() as db:
        db.update_order_status(order_id, "paid")
        
        # Получаем информацию о заказе
        order = db.get_order(order_id)
        
        # Отправляем уведомление администраторам
        for admin_username in ADMIN_USERNAMES:
            try:
                await context.bot.send_message(
                    chat_id=f"@{admin_username}",
                    text=f"💰 Новый оплаченный заказ #{order_id}\n"
                         f"От пользователя: @{query.from_user.username or 'Без username'}\n"
                         "Ожидает подтверждения оплаты"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления админу {admin_username}: {str(e)}")
    
    await query.edit_message_text(
        "✅ Спасибо за оплату!\n"
        "Администратор проверит оплату и подтвердит ваш заказ.\n"
        "Вы получите уведомление, когда заказ будет подтвержден."
    )

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса на отправку обратной связи"""
    query = update.callback_query
    
    await query.edit_message_text(
        "📝 Отправьте ваше сообщение (отзыв, пожелание или описание проблемы):\n\n"
        "❗️ Сообщение будет передано администраторам магазина",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Отмена", callback_data="main_menu")
        ]])
    )
    context.user_data['awaiting_feedback'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    if context.user_data.get('awaiting_feedback'):
        feedback_text = update.message.text
        user = update.effective_user
        
        with Database() as db:
            feedback_id = db.save_feedback(user.id, feedback_text)
        
        # Отправляем подтверждение пользователю
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]]
        await update.message.reply_text(
            "✅ Спасибо за ваш отзыв! Мы обязательно его рассмотрим.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Уведомляем администраторов
        for admin in ADMIN_USERNAMES:
            try:
                await context.bot.send_message(
                    chat_id=f"@{admin}",
                    text=f"📬 Новый отзыв!\n\n"
                         f"От: @{user.username}\n"
                         f"ID: {user.id}\n"
                         f"Текст: {feedback_text}\n"
                         f"ID отзыва: #{feedback_id}"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления админу {admin}: {str(e)}")
        
        context.user_data['awaiting_feedback'] = False
        return

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Админские callback
    if query.data.startswith("admin_"):
        if query.from_user.username not in ADMIN_USERNAMES:
            await query.answer("Доступ запрещен", show_alert=True)
            return
            
        if query.data == "admin_menu":
            keyboard = [
                [InlineKeyboardButton("📋 Ожидающие заказы", callback_data="admin_orders")],
                [InlineKeyboardButton("📦 Управление товарами", callback_data="admin_products")],
                [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")]
            ]
            await query.edit_message_text("🔐 Админ-панель:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif query.data == "admin_orders":
            await admin_orders(update, context)
        elif query.data == "admin_products":
            await admin_products(update, context)
        elif query.data == "admin_stats":
            await admin_stats(update, context)
        elif query.data.startswith("admin_confirm_"):
            await admin_confirm_order(update, context)
        return

    # Обычные callback
    if query.data == "main_menu":
        await show_main_menu(update, context)
    elif query.data == "check_subscription":
        await check_subscription(update, context)
    elif query.data == "show_categories":
        await show_categories(update, context)
    elif query.data.startswith("category_list_"):
        await show_categories(update, context)
    elif query.data.startswith("category_"):
        # Получаем ID категории и показываем её содержимое
        category_id = int(query.data.split('_')[1])
        await show_categories(update, context)
    elif query.data.startswith("product_"):
        await show_product(update, context)
    elif query.data.startswith("buy_"):
        await process_buy(update, context)
    elif query.data.startswith("confirm_"):
        await confirm_order(update, context)
    elif query.data.startswith("paid_"):
        await paid_order(update, context)
    elif query.data == "profile":
        await profile(update, context)
    elif query.data == "show_language_menu":
        await show_language_menu(update, context)
    elif query.data.startswith("lang_"):
        await change_language(update, context)
    elif query.data == "show_statistics":
        await show_statistics(update, context)
    elif query.data.startswith("stats_"):
        period = query.data.split("_")[1]
        with Database() as db:
            stats = db.get_statistics(period=period)
        await show_statistics(update, context, stats)
    elif query.data.startswith("complete_cart_"):
        cart_id = int(query.data.split('_')[2])
        with Database() as db:
            cart = db.get_cart(cart_id)
            if cart:
                order_id = db.create_order_from_cart(cart_id)
                await send_order_status_notification(context, order_id, 'created')
                await query.edit_message_text(
                    get_text('order_created', context.user_data.get('language', 'ru')).format(order_id=order_id),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(get_text('view_order_btn', context.user_data.get('language', 'ru')), 
                        callback_data=f"view_order_{order_id}")
                    ]])
                )
    elif query.data.startswith("cancel_cart_"):
        cart_id = int(query.data.split('_')[2])
        with Database() as db:
            db.delete_cart(cart_id)
        await query.edit_message_text(
            get_text('cart_cancelled', context.user_data.get('language', 'ru')),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_text('back_to_menu_btn', context.user_data.get('language', 'ru')), 
                callback_data="main_menu")
            ]])
        )
    elif query.data.startswith("status_"):
        await update_order_status(update, context)

async def setup_commands(application: Application):
    try:
        logger.info("Настройка команд бота...")
        
        # Установка имени бота
        await application.bot.set_my_name("PUFF SMOKE")
        
        # Установка описания бота
        await application.bot.set_my_description(
            "Официальный бот магазина PUFF SMOKE в Тольятти. "
            "Здесь вы можете:\n"
            "- Узнать цены на товары\n"
            "- Проверить наличие в магазинах\n"
            "- Оформить заказ с доставкой\n"
            "Работаем ежедневно!"
        )
        
        # Установка короткого описания
        await application.bot.set_my_short_description(
            "Магазин электронных сигарет PUFF SMOKE в Тольятти"
        )
        
        # Установка команд
        commands = [
            ("start", "🚀 Запустить бота"),
            ("help", "❓ Помощь и информация"),
            ("menu", "📋 Главное меню"),
        ]
        await application.bot.set_my_commands(commands)
        
        logger.info("Команды и описание бота настроены успешно")
    except Exception as e:
        logger.error(f"Ошибка при настройке команд бота: {str(e)}")

async def forward_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылка постов из канала всем пользователям бота"""
    try:
        # Проверяем, что сообщение из нашего канала
        if update.channel_post and update.channel_post.chat.username == CHANNEL_USERNAME[1:]:
            logger.info("Получено новое сообщение из канала")
            
            # Получаем всех пользователей
            with Database() as db:
                users = db.get_all_users()
            
            # Счетчики для статистики
            successful_sends = 0
            failed_sends = 0
            
            # Пересылаем сообщение каждому пользователю
            for user in users:
                try:
                    await context.bot.forward_message(
                        chat_id=user['telegram_id'],
                        from_chat_id=update.channel_post.chat_id,
                        message_id=update.channel_post.message_id
                    )
                    successful_sends += 1
                    await asyncio.sleep(0.1)  # Небольшая задержка между отправками
                except Exception as e:
                    logger.error(f"Ошибка при пересылке сообщения пользователю {user['telegram_id']}: {str(e)}")
                    failed_sends += 1
            
            logger.info(f"Рассылка завершена. Успешно: {successful_sends}, Ошибок: {failed_sends}")
            
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения из канала: {str(e)}")

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверяет, является ли пользователь администратором"""
    user = update.effective_user
    return user.username in ADMIN_USERNAMES

async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE, stats=None):
    """Показывает статистику магазина"""
    if not await is_admin(update, context):
        return
    
    if stats is None:
        with Database() as db:
            stats = db.get_statistics()
    
    message = (
        "📊 *Статистика магазина*\n\n"
        f"📦 Всего заказов: {stats['total_orders']}\n"
        f"✅ Выполнено заказов: {stats['completed_orders']}\n"
        f"💰 Общая сумма продаж: {stats['total_sales']}₽\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🆕 Новых за 24 часа: {stats['new_users_24h']}\n\n"
        f"📈 Топ товаров (за неделю):\n"
    )
    
    for product in stats['top_products']:
        message += f"• {product['name']}: {product['count']} шт.\n"
    
    message += "\n📊 График продаж за неделю:\n"
    for day in stats['sales_by_day']:
        bar_length = int(day['sales'] / stats['max_daily_sales'] * 20)
        message += f"{day['date']}: {'█' * bar_length} ({day['sales']}₽)\n"
    
    keyboard = [
        [
            InlineKeyboardButton("📅 За день", callback_data="stats_day"),
            InlineKeyboardButton("📅 За неделю", callback_data="stats_week"),
            InlineKeyboardButton("📅 За месяц", callback_data="stats_month")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает админ-панель"""
    if not await is_admin(update, context):
        return
        
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="show_statistics")],
        [InlineKeyboardButton("📝 Отзывы", callback_data="show_feedback")],
        [InlineKeyboardButton("📦 Управление товарами", callback_data="manage_products")],
        [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
    ]
    
    message = "👨‍💼 *Панель администратора*\n\nВыберите нужный раздел:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает профиль пользователя"""
    user = update.effective_user
    user_lang = context.user_data.get('language', 'ru')
    
    with Database() as db:
        user_data = db.get_user(user.id)
        orders_count = db.get_user_orders_count(user.id)
    
    message = (
        f"👤 *Профиль*\n\n"
        f"🆔 ID: `{user.id}`\n"
        f"👤 Имя: {user.first_name}\n"
        f"📝 Никнейм: @{user.username or 'Не указан'}\n"
        f"🛍 Заказов: {orders_count}\n"
        f"🌐 Язык: {LANGUAGES[user_lang]}"
    )
    
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить никнейм", callback_data="change_nickname")],
        [InlineKeyboardButton("🌐 Сменить язык", callback_data="show_language_menu")],
        [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

async def show_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню выбора языка"""
    user = update.effective_user
    
    with Database() as db:
        current_language = db.get_user_language(user.id)
    
    keyboard = []
    for code, name in LANGUAGES.items():
        # Добавляем галочку к текущему языку
        button_text = f"✅ {name}" if code == current_language else name
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"lang_{code}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="profile")])
    
    message = get_text('select_language', current_language)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка смены языка"""
    query = update.callback_query
    if query:
        lang = query.data.split('_')[1]
        user_id = update.effective_user.id
        
        with Database() as db:
            if db.update_user_language(user_id, lang):
                await query.answer(get_text('language_changed', lang))
                await show_profile(update, context)
            else:
                await query.answer(get_text('error', lang), show_alert=True)

async def send_abandoned_cart_notification(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет уведомления о брошенных корзинах"""
    with Database() as db:
        abandoned_carts = db.get_abandoned_carts()
        
    for cart in abandoned_carts:
        user_lang = db.get_user_language(cart['user_id'])
        message = get_text('abandoned_cart', user_lang).format(
            product_name=cart['product_name'],
            price=cart['price']
        )
        
        keyboard = [
            [InlineKeyboardButton(get_text('complete_order_btn', user_lang), callback_data=f"complete_cart_{cart['id']}")],
            [InlineKeyboardButton(get_text('cancel_order_btn', user_lang), callback_data=f"cancel_cart_{cart['id']}")]
        ]
        
        try:
            await context.bot.send_message(
                chat_id=cart['user_id'],
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о брошенной корзине: {str(e)}")

async def send_order_status_notification(context: ContextTypes.DEFAULT_TYPE, order_id: int, new_status: str):
    """Отправляет уведомление об изменении статуса заказа"""
    with Database() as db:
        order = db.get_order(order_id)
        if not order:
            return
        
        user_lang = db.get_user_language(order['user_id'])
        message = get_text(f'order_status_{new_status}', user_lang).format(
            order_id=order['id'],
            product_name=order['product_name']
        )
        
        keyboard = [[InlineKeyboardButton(get_text('view_order_btn', user_lang), callback_data=f"view_order_{order['id']}")]]
        
        try:
            await context.bot.send_message(
                chat_id=order['user_id'],
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о статусе заказа: {str(e)}")

def setup_notifications(application: Application):
    """Настраивает периодические задачи для уведомлений"""
    job_queue = application.job_queue
    
    # Проверка брошенных корзин каждые 6 часов
    job_queue.run_repeating(send_abandoned_cart_notification, interval=21600)

async def update_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет статус заказа и отправляет уведомление"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(update, context):
        return
    
    try:
        _, order_id, new_status = query.data.split('_')
        order_id = int(order_id)
        
        with Database() as db:
            success = db.update_order_status(order_id, new_status)
            if success:
                await send_order_status_notification(context, order_id, new_status)
                await query.edit_message_text(
                    get_text('status_updated', context.user_data.get('language', 'ru')).format(
                        order_id=order_id,
                        status=new_status
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            get_text('back_btn', context.user_data.get('language', 'ru')), 
                            callback_data="admin_panel"
                        )
                    ]])
                )
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса заказа: {str(e)}")
        await query.edit_message_text(
            get_text('status_update_error', context.user_data.get('language', 'ru')),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    get_text('back_btn', context.user_data.get('language', 'ru')), 
                    callback_data="admin_panel"
                )
            ]])
        )

async def main():
    try:
        logger.info("Запуск бота...")
        application = Application.builder().token(BOT_TOKEN).build()

        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", start))
        application.add_handler(CommandHandler("menu", show_main_menu))
        application.add_handler(CommandHandler("admin", admin_command))
        application.add_handler(CallbackQueryHandler(handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Добавляем обработчик сообщений из канала
        application.add_handler(MessageHandler(
            filters.ChatType.CHANNEL & filters.UpdateType.CHANNEL_POST,
            forward_channel_post
        ))
        
        # Настраиваем команды и описание бота
        application.job_queue.run_once(lambda ctx: setup_commands(application), when=1)
        
        # Настраиваем периодические задачи для уведомлений
        setup_notifications(application)
        
        logger.info("Бот успешно настроен и запускается...")
        
        # Получаем порт из переменных окружения (для Render)
        port = int(os.getenv("PORT", 8080))
        logger.info(f"Используемый порт: {port}")
        
        # Проверяем переменную окружения WEBHOOK_URL
        webhook_url = os.getenv("WEBHOOK_URL")
        
        # Инициализация приложения
        await application.initialize()
        
        # Если задан WEBHOOK_URL, используем webhook, иначе polling
        if webhook_url and webhook_url.strip():
            logger.info(f"Запуск через webhook: {webhook_url}")
            
            # Сначала удаляем предыдущий webhook, если он был (с await)
            await application.bot.delete_webhook(drop_pending_updates=True)
            
            # Устанавливаем webhook
            await application.start()
            await application.updater.start_webhook(
                listen="0.0.0.0",
                port=port,
                webhook_url=webhook_url,
                drop_pending_updates=True
            )
            
            # Печатаем сообщение, что бот запущен и слушает порт
            logger.info(f"Бот запущен в режиме webhook и слушает порт {port}")
            
            # Ждем, пока не будет остановлено
            await application.updater.start_webhook_task
        else:
            logger.info("Webhook URL не установлен. Запуск через long polling.")
            # Удаляем webhook перед запуском long polling (с await)
            await application.bot.delete_webhook(drop_pending_updates=True)
            
            # Запускаем через polling
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
            
            # Ждем, пока не будет остановлено
            await application.updater.stop()
            
        # Корректно останавливаем приложение при завершении
        await application.stop()
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    # Используем asyncio для запуска асинхронной main()
    asyncio.run(main()) 