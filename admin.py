from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import Database
from config import ADMIN_USERNAME

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("У вас нет доступа к админ-панели.")
        return

    keyboard = [
        [InlineKeyboardButton("📋 Ожидающие заказы", callback_data="admin_pending_orders")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Админ-панель:", reply_markup=reply_markup)

async def show_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.username != ADMIN_USERNAME:
        await query.answer("У вас нет доступа к этой функции.", show_alert=True)
        return

    with Database() as db:
        orders = db.get_pending_orders()

    if not orders:
        await query.edit_message_text(
            "Нет ожидающих заказов.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]])
        )
        return

    message = "📋 Ожидающие заказы:\n\n"
    keyboard = []
    
    for order in orders:
        message += (
            f"Заказ #{order['id']}\n"
            f"Товар: {order['product_name']}\n"
            f"Пользователь: @{order['username']}\n"
            f"Статус: {order['status']}\n\n"
        )
        keyboard.append([InlineKeyboardButton(
            f"✅ Подтвердить #{order['id']}", 
            callback_data=f"admin_confirm_{order['id']}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup)

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.username != ADMIN_USERNAME:
        await query.answer("У вас нет доступа к этой функции.", show_alert=True)
        return

    order_id = int(query.data.split('_')[2])
    
    with Database() as db:
        db.update_order_status(order_id, 'paid')
        order = db.get_order(order_id)
        
    # Отправляем уведомление пользователю
    try:
        await context.bot.send_message(
            chat_id=order['telegram_id'],
            text=(
                f"✅ Заказ #{order_id} подтвержден!\n\n"
                "Теперь вы можете вызвать доставку. "
                "После получения заказа, пожалуйста, подтвердите получение."
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Заказ получен", callback_data=f"received_{order_id}")],
                [InlineKeyboardButton("❌ Проблема с заказом", callback_data=f"problem_{order_id}")]
            ])
        )
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")

    await show_pending_orders(update, context)

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.username != ADMIN_USERNAME:
        await query.edit_message_text("У вас нет доступа к админ-панели.")
        return

    if query.data == "admin_menu":
        keyboard = [
            [InlineKeyboardButton("📋 Ожидающие заказы", callback_data="admin_pending_orders")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Админ-панель:", reply_markup=reply_markup)
    
    elif query.data == "admin_pending_orders":
        await show_pending_orders(update, context)
    
    elif query.data.startswith("admin_confirm_"):
        await confirm_payment(update, context) 