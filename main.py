import telebot
from telebot import types
import sqlite3

# =================== КОНСТАНТИ ===================

TOKEN = '8753275176:AAHRra7xuZKbUKC90pxQyZYY6T0L-MHU-y8'
ADMIN_ID = 8720546531

WITHDRAW_AMOUNTS = [15, 25, 50, 100]  # Доступні суми для виводу

# =================== БОТ ===================

bot = telebot.TeleBot(TOKEN)

# =================== БАЗА ДАНИХ ===================

def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_balance(user_id: int) -> int:
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def update_balance(user_id: int, amount: int) -> None:
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, balance) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
    ''', (user_id, amount, amount))
    conn.commit()
    conn.close()

# =================== МЕНЮ ВИВОДУ ===================

@bot.message_handler(commands=['withdraw'])
def withdraw_menu(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    for amount in WITHDRAW_AMOUNTS:
        label = f"⭐️ {amount}" if balance >= amount else f"🔒 {amount}"
        buttons.append(types.InlineKeyboardButton(label, callback_data=f"withdraw_{amount}"))

    keyboard.add(*buttons)
    keyboard.add(types.InlineKeyboardButton("❌ Скасувати", callback_data="withdraw_cancel"))

    bot.send_message(
        message.chat.id,
        f"💰 <b>Виведення зірок</b>\n\n"
        f"Твій баланс: <b>{balance} ⭐️</b>\n\n"
        f"Обери суму для виведення:",
        parse_mode="HTML",
        reply_markup=keyboard
    )

# =================== ОБРОБКА КНОПОК ===================

@bot.callback_query_handler(func=lambda call: call.data == 'withdraw_cancel')
def handle_cancel(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="❌ Виведення скасовано."
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_'))
def handle_withdrawal(call):
    user_id = call.from_user.id

    if call.from_user.username:
        username = f"@{call.from_user.username}"
    else:
        username = f"<a href='tg://user?id={user_id}'>Користувач (без юзернейму)</a>"

    amount = int(call.data.split('_')[1])
    balance = get_balance(user_id)

    if balance >= amount:
        update_balance(user_id, -amount)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                f"✅ <b>Заявку прийнято!</b>\n\n"
                f"💳 Сума: <b>{amount} ⭐️</b>\n"
                f"🕐 З вами зв'яжуться протягом 48 годин.\n\n"
                f"Залишок балансу: <b>{balance - amount} ⭐️</b>"
            ),
            parse_mode="HTML"
        )

        admin_text = (
            f"🔔 <b>Нова заявка на виведення зірок!</b>\n"
            f"👤 Від: {username}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"💳 Сума: <b>{amount} ⭐️</b>\n"
            f"💰 Залишок балансу: <b>{balance - amount} ⭐️</b>"
        )

        try:
            bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        except Exception as e:
            print(f"Помилка відправки адміну: {e}")

    else:
        bot.answer_callback_query(
            call.id,
            f"❌ Недостатньо зірок!\nТвій баланс: {balance} ⭐️",
            show_alert=True
        )

        keyboard = types.InlineKeyboardMarkup(row_width=2)
        buttons = []

        for amt in WITHDRAW_AMOUNTS:
            label = f"⭐️ {amt}" if balance >= amt else f"🔒 {amt}"
            buttons.append(types.InlineKeyboardButton(label, callback_data=f"withdraw_{amt}"))

        keyboard.add(*buttons)
        keyboard.add(types.InlineKeyboardButton("❌ Скасувати", callback_data="withdraw_cancel"))

        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )

# =================== ЗАПУСК ===================

if __name__ == '__main__':
    init_db()
    print("Бот запущено ✅")
    bot.infinity_polling()
