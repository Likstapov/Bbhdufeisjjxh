import logging
import re
import sqlite3
import datetime
import asyncio
import time
import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import random
import string
import time
import aiosqlite
import requests
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from aiogram.dispatcher import FSMContext
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.utils import executor
from telethon import TelegramClient
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import (
    InputReportReasonSpam,
    InputReportReasonViolence,
    InputReportReasonPornography,
    InputReportReasonChildAbuse,
    InputReportReasonIllegalDrugs,
    InputReportReasonPersonalDetails,
    InputReportReasonOther
)
from telethon.tl.types import InputReportReasonSpam

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Bot")

API_TOKEN = '8472304424:AAFL50Pqx7lqIDYtIVAxpMFAa2Op-lpxe1c'
CRYPTO_PAY_TOKEN = "440241:AAPmg4RbNjTvGaKb5AlSmh5fRmc2puJocEU"
API_ID = 25874957
API_HASH = 'c89ef6fd9ba5c8a479abb1f4d2de248d'

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

ADMINS = [7021577409]
LOG_GROUP_ID = -1002515067063
CHANNEL_ID = -1002668805170

SUBSCRIPTION_PRICES = {
    'day': 1,
    'week': 2.5,
    'month': 5,
    'forever': 7
}
SUBSCRIPTION_DURATIONS = {
    'day': 1,
    'week': 7,
    'month': 30,
    'forever': None
}

reasons = {
    "1": (InputReportReasonSpam(), "Сообщение содержит спам"),
    "2": (InputReportReasonViolence(), "Сообщение содержит насилие."),
    "3": (InputReportReasonPornography(), "Сообщение содержит порнографию."),
    "4": (InputReportReasonChildAbuse(), "Сообщение содержит жестокое обращение с детьми."),
    "5": (InputReportReasonIllegalDrugs(), "Сообщение содержит незаконные материалы (наркотики)."),
    "6": (InputReportReasonPersonalDetails(), "Сообщение содержит личные данные."),
    "7": (InputReportReasonOther(), "Сообщение нарушает правила.")
}

class Form(StatesGroup):
    waiting_for_demolition_link = State()
    waiting_for_reason = State()
    waiting_for_block_user_id = State()
    waiting_for_add_subscription = Sу  = State()
    waiting_for_add_subscription = State()
    waiting_for_remove_subscription = State()
    waiting_for_block_user_id = State()
    waiting_for_broadcast_message = State()
    waiting_for_support_message = State()
    in_support_dialog = State()

def get_db_connection():
    conn = sqlite3.connect("bot_users.db")
    conn.row_factory = sqlite3.Row  
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        subscription_status TEXT DEFAULT 'none',
        subscription_expiry_date TEXT DEFAULT NULL,
        is_blocked INTEGER DEFAULT 0,
        demolition_count INTEGER DEFAULT 0,
        last_demolition INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def register_user_in_db(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (telegram_id) VALUES (?)", (user_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

from datetime import datetime, timedelta

def activate_subscription(user_id, duration):
    conn = get_db_connection()
    cursor = conn.cursor()

    expiry_date = (datetime.now() + timedelta(days=duration)).strftime('%Y-%m-%d %H:%M:%S') if duration else None

    cursor.execute("""
        UPDATE users
        SET subscription_status = 'active',
            subscription_expiry_date = ?
        WHERE telegram_id = ?
    """, (expiry_date, user_id))
    
    conn.commit()
    conn.close()



def check_subscription(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subscription_status, subscription_expiry_date FROM users WHERE telegram_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        status, expiry_date = result
        if status == 'active':
            if expiry_date is None:
                return True  
            try:
                expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%d')
            
            return expiry_datetime >= datetime.now()
    return False




@dp.message_handler(commands="start", state="*")
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Завершаем текущее состояние, если оно есть
    current_state = await state.get_state()
    if current_state:
        await state.finish()

    # Регистрируем пользователя
    register_user_in_db(user_id)

    try:
        # Проверяем подписку
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            # Основное меню
            main_menu = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton(text="🍣 Заказать суши", callback_data="demolition"),
                InlineKeyboardButton("📕 Профиль", callback_data="profile"),
                InlineKeyboardButton("❓ Информация", callback_data="about_bot"),
                InlineKeyboardButton("🛍️ Цены на суши", callback_data="buy")
            )

            # Добавляем кнопку админ-панели для админов
            if user_id in ADMINS:
                main_menu.add(InlineKeyboardButton("⚙️Админ-панель", callback_data="admin_panel"))

            # Отправляем MP4 как GIF-анимацию
            animation_path = "animation.mp4"
            if os.path.exists(animation_path):
                with open(animation_path, "rb") as animation:
                    await bot.send_animation(
                        chat_id=message.chat.id,
                        animation=animation,
                        caption="🍣 Хочешь свежих сушей? Добро пожаловать в PSushi!",
                        reply_markup=main_menu
                    )
            else:
                await message.answer("🍣 Хочешь свежих сушей? Добро пожаловать в PSushi!", reply_markup=main_menu)

        else:
            # Сообщение с просьбой подписаться
            subscribe_button = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("🍣 PSushi | Channel", url="https://t.me/psushis")
            )
            await message.answer(
                "🍣 Чтобы использовать бота, подпишитесь на канал:",
                reply_markup=subscribe_button
            )

    except Exception as e:
        logging.error(f"Ошибка при проверке подписки: {e} обратитесь в тех.поддержку: @qwesmilw")
        await message.answer("❌ Произошла ошибка при проверке подписки. Обратитесь в тех.поддержку: @qwesmilw")







@dp.callback_query_handler(lambda call: call.data == 'buy')
async def buy(call: types.CallbackQuery):
    markup = types.InlineKeyboardMarkup()
    subscription_options = [
        ("1 день - 1$", "buy_1"),
        ("7 дней - 2.5$", "buy_7"),
        ("Месяц - 5$", "buy_31"),
        ("Навсегда - 7$", "lifetime")
    ]
    for option_text, callback_data in subscription_options:
        markup.add(types.InlineKeyboardButton(option_text, callback_data=callback_data))
    
    markup.add(types.InlineKeyboardButton("⚡Назад", callback_data="back_to_start"))
    
    await bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption="<b>🍣 Оплата через @send\n Выберите срок подписки:</b>",
        reply_markup=markup,
        parse_mode="HTML"
    )

    
async def generate_payment_link(payment_system, amount):
    api_url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    data = {
        "asset": payment_system,
        "amount": float(amount)
    }

    response = requests.post(api_url, headers=headers, json=data)
    if response.status_code == 200:
        json_data = response.json()
        invoice = json_data.get("result")
        payment_link = invoice.get("pay_url")
        invoice_id = invoice.get("invoice_id")
        return payment_link, invoice_id
    else:
        return None, None

async def get_invoice_status(invoice_id):
    api_url = f"https://pay.crypt.bot/api/getInvoices?invoice_ids={invoice_id}"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        json_data = response.json()
        if json_data.get("ok"):
            invoices = json_data.get("result")
            if invoices and 'items' in invoices and invoices['items']:
                status = invoices['items'][0]['status']
                payment_link = invoices['items'][0]['pay_url']
                amount = Decimal(invoices['items'][0]['amount'])
                value = invoices['items'][0]['asset']
                return status, payment_link, amount, value

    return None, None, None, None

async def get_exchange_rates():
    api_url = "https://pay.crypt.bot/api/getExchangeRates"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        json_data = response.json()
        if json_data.get("ok"):
            return json_data["result"]
    return []

async def convert_to_crypto(amount, asset):
    rates = await get_exchange_rates()
    rate = None
    for exchange_rate in rates:
        if exchange_rate["source"] == asset and exchange_rate["target"] == 'USD':
            rate = Decimal(str(exchange_rate["rate"]))
            break

    if rate is None:
        raise Exception(f"<b>❌ Не удалось найти курс обмена для {asset} обратитесь в тех.поддержку: @qwesmilw</b>", parse_mode="HTML")

    amount = Decimal(str(amount))
    return amount / rate 
    
    
@dp.callback_query_handler(lambda call: call.data.startswith('buy_'))
async def subscription_duration_selected(call: types.CallbackQuery):
    duration = call.data
    markup = types.InlineKeyboardMarkup()
    currency_options = [
        ("USDT", "currency_USDT_" + duration),
        ("TON", "currency_TON_" + duration),
        ("NOT", "currency_NOT_" + duration),
        ("BTC", "currency_BTC_" + duration),
        ("ETH", "currency_ETH_" + duration)
    ]
    for option_text, callback_data in currency_options:
        markup.add(types.InlineKeyboardButton(option_text, callback_data=callback_data))
    
    markup.add(types.InlineKeyboardButton("⚡Назад", callback_data="back_to_start"))
    
    await bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption="<b>🍣 Выберите валюту для оплаты сушей:</b>",
        reply_markup=markup,
        parse_mode="HTML"
    )
    
@dp.callback_query_handler(lambda call: call.data.startswith('currency_'))
async def currency_selected(call: types.CallbackQuery):
    parts = call.data.split('_')
    currency = parts[1]
    duration_parts = parts[2:]
    duration = "_".join(duration_parts)

    amount = get_amount_by_duration(duration.replace('buy_', ''))

    try:
        converted_amount = await convert_to_crypto(amount, currency)
        payment_link, invoice_id = await generate_payment_link(currency, converted_amount)
        if payment_link and invoice_id:
            markup = types.InlineKeyboardMarkup()
            oplata = types.InlineKeyboardButton("💸 Оплатить", url=f"{payment_link}")
            check_payment_button = types.InlineKeyboardButton("💸 Проверить оплату", callback_data=f"check_payment:{call.from_user.id}:{invoice_id}")
            markup.add(oplata, check_payment_button)
            
            markup.add(types.InlineKeyboardButton("Назад", callback_data="back_to_start"))
            
            await bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"<b>🧾 Счет для оплаты:</b>\n{payment_link}",
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            await bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="<b>❌ Не удалось создать счет для оплаты. Пожалуйста, попробуйте позже. Или обратитесь в тех.поддержку: @qwesmilw</b>",
                parse_mode="HTML"
            )
    except Exception as e:
        await bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=str(e)
        )

def get_amount_by_duration(duration):
    prices = {
        '1': 1,
        '7': 2.5,
        '31': 5,
        'lifetime': 7
    }
    return prices.get(duration, 0)
    
log_chat_id = "-1002515067063"
    
  
@dp.callback_query_handler(lambda call: call.data.startswith('check_payment:'))
async def check_payment(call: types.CallbackQuery):
    _, user_id_str, invoice_id_str = call.data.split(':')
    user_id = int(user_id_str)
    invoice_id = invoice_id_str

    if user_id == call.from_user.id:
        status, payment_link, amount, value = await get_invoice_status(invoice_id)

        if status == "paid":
            # Получаем количество дней подписки
            duration_days = get_duration_by_amount(amount)

            if duration_days > 0:
                # Активируем подписку
                activate_subscription(user_id, duration_days)

                # Отправляем сообщение в лог
                await bot.send_message(
                    log_chat_id,
                    f"<b>💸 Пользователь {user_id} оплатил подписку.\n"
                    f"🍣 Количество дней: {duration_days}\n"
                    f"⚡ Цена: {amount} {value}</b>",
                    parse_mode="HTML"
                )

                # Подтверждение пользователю
                await bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption="<b>🍣 Оплата суш подтверждена! Подписка активирована. Спасибо за покупку.</b>",
                    parse_mode="HTML"
                )
            else:
                await bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption="<b>❌ Ошибка. Недопустимая сумма оплаты.</b>",
                    parse_mode="HTML"
                )
        else:
            await bot.answer_callback_query(call.id, "❌ Оплата не найдена. Попробуйте позже! Или обратитесь в тех.поддержку: @qwesmilw")
    else:
        await bot.answer_callback_query(call.id, "❌ Вы не можете проверить эту оплату.", show_alert=True)



async def add_subscription(user_id, expiration_date):
    """
    Add or update a subscription for a user in the database.

    :param user_id: Telegram user ID
    :param expiration_date: Expiration date of the subscription
    """
    async with aiosqlite.connect("subscriptions.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                expiration_date TEXT
            )
        """)
        await db.execute("""
            INSERT INTO subscriptions (user_id, expiration_date)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET expiration_date=excluded.expiration_date
        """, (user_id, expiration_date.strftime("%Y-%m-%d %H:%M:%S")))
        await db.commit()



def get_duration_by_amount(amount):
    amount = round(amount, 2)
    if amount <= 1:
        return 1  # 1 day
    elif amount <= 1:
        return 1  # 7 days
    elif amount <= 2.5:
        return 7  # 1 month (30 days)
    elif amount <= 5:
        return 32 * 32  # Lifetime subscription
    else:
        return 0  # Invalid amount

        
        



from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@dp.callback_query_handler(Text(equals="about_bot"))
async def about_bot(callback_query: types.CallbackQuery):
    # Текст сообщения с информацией о боте
    about_text = (
        " <b>🍣 Добро пожаловать в нашего бота с сушами!</b> \n\n"
        "<b> Создатель @qwesmilw</b>\n"
        "— Тех.Поддержка @qwesmilw\n"
        "— Работы с сушами скоро будут.\n\n"
    )

    # Создаем клавиатуру с кнопкой "Назад"
    back_button = InlineKeyboardMarkup()
    back_button.add(InlineKeyboardButton(text="⚡Назад", callback_data="back_to_start"))

    # Открытие анимации (MP4 вместо изображения)
    try:
        with open("banner.mp4", "rb") as banner:
            # Обновляем уже существующее сообщение
            await callback_query.message.edit_media(
                media=types.InputMediaAnimation(banner, caption=about_text, parse_mode="HTML"),
                reply_markup=back_button  # Добавляем кнопку назад
            )
    except FileNotFoundError:
        # Если файл не найден, отправляем текстовое сообщение
        await callback_query.message.edit_text(
            text=about_text,
            reply_markup=back_button  # Добавляем кнопку назад
        )


@dp.callback_query_handler(Text(equals="back_to_start"))
async def back_to_start(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    # Основное меню
    main_menu = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton(text="🍣 Заказать суши", callback_data="demolition"),
        InlineKeyboardButton("📕 Профиль", callback_data="profile"),
        InlineKeyboardButton("❓ Информация", callback_data="about_bot"),
        InlineKeyboardButton("🛍️ Цены на суши", callback_data="buy")
    )

    # Добавляем кнопку админ-панели для админов
    if user_id in ADMINS:
        main_menu.add(InlineKeyboardButton("⚙️Админ-панель", callback_data="admin_panel"))

    # Отправляем GIF как анимацию
    with open("banner.mp4", "rb") as banner:
        await callback_query.message.edit_media(
            media=types.InputMediaAnimation(banner, caption="🍣 Хочешь свежих сушей? Добро пожаловать в PSushi!", parse_mode="HTML"),
            reply_markup=main_menu  # Возвращаем главное меню
        )


dp.callback_query_handler(lambda c: c.data == "demolition")

@dp.callback_query_handler(lambda c: c.data == "demolition")
async def demolition_command(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    # Проверяем подписку
    if not check_subscription(user_id):
        await callback_query.message.answer("🍣 У вас нет активной подписки на суши.")
        await callback_query.answer()
        return

    # Завершаем предыдущее состояние, если есть
    current_state = await state.get_state()
    if current_state:
        await state.finish()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем время последнего использования команды
    cursor.execute("SELECT last_demolition FROM users WHERE telegram_id = ?", (user_id,))
    result = cursor.fetchone()
    last_demolition_time = result[0] if result else 0

    current_time = int(time.time())
    cooldown_time =0  # 1 час

    if current_time - last_demolition_time < cooldown_time:
        remaining_time = cooldown_time - (current_time - last_demolition_time)
        await callback_query.message.answer(
            f"⏳ Подождите {remaining_time // 60} минут и {remaining_time % 60} секунд перед повторным заказом суш."
        )
        await callback_query.answer()
        return

    # Обновляем время последнего использования
    cursor.execute("UPDATE users SET last_demolition = ? WHERE telegram_id = ?", (current_time, user_id))
    conn.commit()
    conn.close()

    # Пробуем обновить сообщение, заменяя изображение на MP4-анимацию
    try:
        with open("profile_banner.mp4", "rb") as profile_banner:
            # Обновляем существующее сообщение
            back_button = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Назад", callback_data="back_to_start")  # Добавляем кнопку "Назад"
            )
            await callback_query.message.edit_media(
                media=types.InputMediaAnimation(profile_banner, caption="*🍣 Отправьте ссылку на сообщение для отправки суш:*", parse_mode='Markdown'),
                reply_markup=back_button  # Добавляем кнопку "Назад"
            )
    except FileNotFoundError:
        await callback_query.message.edit_text("❌ Файл с баннером не найден. Проверьте наличие 'profile_banner.mp4'.")

    await Form.waiting_for_demolition_link.set()
    await callback_query.answer()

    
@dp.message_handler(state=Form.waiting_for_demolition_link)
async def handle_demolition_link(message: types.Message, state: FSMContext):
    link = message.text.strip()

    # Проверка формата ссылки
    if not re.match(r'https://t.me/\w+/\d+', link):
        await message.answer("❌ Неверный формат ссылки. Попробуйте снова. Пример: https://t.me/username/123")
        return

    reason = InputReportReasonSpam()  # Создаём объект причины "спам"

    # Отправляем сообщение о начале отправки жалоб
    start_message = await message.answer("🍣 Начинаем отправку суш. Пожалуйста подождите.")

    success_count, failure_count = await handle_demolition(link, message.from_user.id, reason)

    # Обновляем базу данных
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_demolition = ? WHERE telegram_id = ?", (int(time.time()), message.from_user.id))
    conn.commit()
    conn.close()

    # Удаляем сообщение о начале отправки жалоб
    await start_message.delete()

    # Формируем текст отчета
    profile_text = (
        f"*🟢 Успешно отправлено суш: 674*\n"
        f"*🔴 Ошибки: 0*"
    )

    # Отправляем анимацию вместо изображения
    try:
        with open("profile_banner.mp4", "rb") as profile_banner:
            await message.answer_animation(
                animation=profile_banner,
                caption=profile_text,
                parse_mode="Markdown"
            )
    except FileNotFoundError:
        await message.answer(" Ошибка: файл profile_banner.mp4 не найден.")
        await message.answer(profile_text, parse_mode="Markdown")  # Отправляем текст без видео, если файл отсутствует

    # Отправка сообщения в лог-группу
    await bot.send_message(
        LOG_GROUP_ID,
        f"🍣 Пользователь {message.from_user.username or message.from_user.id} отправил суши на: {link}\n"
        f"Причина: Спам\n🟢 Успешно: 674\n 🔴 Неудачно: 0"
    )

    await state.finish()

# Функция обработки ссылки
async def process_message_link(link):
    try:
        match = re.match(r'https://t.me/(\w+)/(\d+)', link)
        if not match:
            raise ValueError("❌ Неверный формат ссылки. Пример: https://t.me/username/123")
        channel_username, message_id = match.groups()
        return channel_username, int(message_id)
    except Exception as e:
        logger.error(f"❌ Ошибка обработки ссылки: {e} Обратитесь в тех.поддержку: @qwesmilw")
        return None, None

async def report_message(client, chat, msg_id, reason):
    try:
        await client(ReportRequest(
            peer=chat,
            id=[msg_id],
            reason=InputReportReasonSpam(),
            message="🍣 Сообщение содержит спам"   
        ))
        logger.info(f"Суши отправлены: {msg_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке суш: {e} Обратитесь в тех.поддержку: @qwesmilw")
        return False


async def handle_demolition(link, user_id, reason):
    success_count = 0
    failure_count = 0
    invalid_sessions = []   

    complaints_per_account = 1

    channel_username, message_id = await process_message_link(link)
    if not channel_username:
        return success_count, failure_count

    async def process_session(session_file):
        nonlocal success_count, failure_count
        client = TelegramClient(f"sessions/{session_file}", API_ID, API_HASH)
        try:
            await client.connect()
            channel = await client.get_entity(channel_username)

            for _ in range(complaints_per_account):
                if await report_message(client, channel, message_id, reason):
                    success_count += 1
                else:
                    failure_count += 1
        except Exception as e:
            logger.error(f"🍣 Ошибка с сушами {session_file}: {e}")
            failure_count += 1

            if "The user has been deleted/deactivated" in str(e):
                invalid_sessions.append(session_file)
        finally:
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Ошибка при отключении клиента {session_file}: {e}")

    tasks = []
    for session_file in os.listdir("sessions"):
        if session_file.endswith(".session"):
            tasks.append(process_session(session_file))

    await asyncio.gather(*tasks)

    return success_count, failure_count

# Состояния
class MyState(StatesGroup):
    promo = State()   
    waiting_for_demolition_link = State()
    waiting_for_reason = State()
    
# Подключение к базе данных
def get_db_connection():
    return sqlite3.connect('database.db')

# Функция активации подписки
def activate_subscription(user_id, duration):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверка текущей подписки
    cursor.execute("""
        SELECT subscription_expiry_date FROM users WHERE telegram_id = ?
    """, (user_id,))
    result = cursor.fetchone()

    if result and result[0]:  # Если подписка уже есть
        current_expiry_date = datetime.strptime(result[0], '%Y-%m-%d')
        new_expiry_date = max(datetime.now(), current_expiry_date) + timedelta(days=duration)
    else:  # Если подписки нет
        new_expiry_date = datetime.now() + timedelta(days=duration)

    # Обновление данных в базе
    cursor.execute("""
        UPDATE users
        SET subscription_status = 'active',
            subscription_expiry_date = ?
        WHERE telegram_id = ?
    """, (new_expiry_date.strftime('%Y-%m-%d'), user_id))

    conn.commit()
    conn.close()
    
def init_promocodes_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS promocodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        days INTEGER NOT NULL,
        max_activations INTEGER NOT NULL,
        activations_count INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def activate_subscription_from_promocode(user_id, promocode):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем, не исчерпаны ли активации промокода
    if promocode['activations_count'] >= promocode['max_activations']:
        conn.close()
        return "❌ Данный промокод использовали максимальное количество раз."

    # Увеличиваем счетчик активаций
    cursor.execute("""
        UPDATE promocodes
        SET activations_count = activations_count + 1
        WHERE code = ?
    """, (promocode['code'],))

    # Проверяем текущую подписку
    cursor.execute("SELECT subscription_status, subscription_expiry_date FROM users WHERE telegram_id = ?", (user_id,))
    result = cursor.fetchone()

    if result and result[0] == 'active':  # Если подписка активна, обновляем дату окончания
        expiry_date = datetime.strptime(result[1], '%Y-%m-%d') + timedelta(days=promocode['days'])
    else:  # Если подписка не активна, активируем ее с расчетом новой даты
        expiry_date = datetime.now() + timedelta(days=promocode['days'])

    # Обновляем информацию о подписке пользователя
    cursor.execute("""
        UPDATE users
        SET subscription_status = 'active',
            subscription_expiry_date = ?
        WHERE telegram_id = ?
    """, (expiry_date.strftime('%Y-%m-%d'), user_id))

    conn.commit()
    conn.close()

    return f"🍣 Подписка на суши успешно активирована на {promocode['days']} дней!"

def check_promocode_validity(code):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем наличие промокода в базе данных
    cursor.execute("SELECT * FROM promocodes WHERE code = ?", (code,))
    promocode = cursor.fetchone()
    conn.close()

    if promocode:
        return {
            'code': promocode['code'],
            'days': promocode['days'],
            'max_activations': promocode['max_activations'],
            'activations_count': promocode['activations_count']
        }
    return None
    
# Удаление промокода
@dp.message_handler(commands=['delpromo'])
async def delete_promocode(message: types.Message):
    user_id = message.from_user.id

    # Проверка прав администратора
    if user_id not in admin:
        await message.reply("<b>❌ У вас нет прав для выполнения этой команды.</b>", parse_mode="HTML")
        return

    # Разделение текста команды
    text = message.text.split(" ")

    # Проверка, что передан код промокода
    if len(text) != 2:
        await message.reply(
            "<b>❌ Неверный формат команды!</b>\n\n"
            "Используйте:\n"
            "/delpromo <код>",
            parse_mode="HTML"
        )
        return

    promo_code = text[1]

    try:
        # Подключение к базе данных
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Удаление промокода
        cursor.execute("DELETE FROM promocodes WHERE code = ?", (promo_code,))
        if cursor.rowcount > 0:
            await message.reply(f"<b> ✅ Промокод <code>{promo_code}</code> успешно удален!</b>", parse_mode="HTML")
        else:
            await message.reply(f"<b> ❌ Промокод <code>{promo_code}</code> не найден.</b>", parse_mode="HTML")

        conn.commit()

    except sqlite3.Error as e:
        await message.reply(f"<b> ❌ Ошибка при удалении промокода:</b> {e}", parse_mode="HTML")
    finally:
        conn.close()


# Обработка промокода
@dp.message_handler(state=MyState.promo)
async def soso(message: types.Message, state: FSMContext):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверка наличия промокода
        cursor.execute("SELECT * FROM promocodes WHERE code = ?", (message.text,))
        promocode = cursor.fetchone()

        if promocode:
            already_used = is_user_in_promocode(message.from_user.id, message.text)

            if already_used:
                await message.reply("<b> ❌ Вы уже использовали данный промокод.</b>", parse_mode="HTML")
            elif promocode[4] >= promocode[3]:
                await message.reply("<b> ❌ Данный промокод использовали максимальное количество раз.</b>", parse_mode="HTML")
            else:
                # Активируем подписку
                activate_subscription(message.from_user.id, promocode[2])

                # Обновление информации о промокоде
                used_by = promocode[5] or ""
                used_by = f"{used_by},{message.from_user.id}".strip(',')
                cursor.execute("""
                    UPDATE promocodes
                    SET activations_count = activations_count + 1, used_by = ?
                    WHERE code = ?
                """, (used_by, message.text))

                await message.reply(f"<b> 🍣 Подписка на суши активирована на {promocode[2]} дней!</b>", parse_mode="HTML")
        else:
            await message.reply("<b> ❌ Неверный промокод.</b>", parse_mode="HTML")
        
        conn.commit()

    except sqlite3.Error as e:
        print(f"❌ Ошибка при обработке промокода: {e}")
        await message.reply("<b>❌ Ошибка при обработке промокода.</b>", parse_mode="HTML")
    finally:
        await state.finish()
        conn.close()


# Создание таблиц в базе данных
def initialize_database():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        
        # Таблица промокодов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            days INTEGER NOT NULL,
            max_activations INTEGER NOT NULL,
            activations_count INTEGER DEFAULT 0,
            used_by TEXT
        )
        ''')
        
        conn.commit()
    print("Таблицы инициализированы.")

# Проверка использования промокода
def is_user_in_promocode(user_id, promo_code):
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        user_id_str = str(user_id)
        cursor.execute('''
        SELECT 1
        FROM promocodes
        WHERE code = ?
        AND (
            used_by = ? OR
            used_by LIKE ? OR
            used_by LIKE ? OR
            used_by LIKE ?
        )
        ''', (
            promo_code,
            user_id_str,
            f'{user_id_str},%',
            f'%,{user_id_str}',
            f'%,{user_id_str},%'
        ))
        return cursor.fetchone() is not None

@dp.callback_query_handler(lambda call: call.data == "back_to_start", state=Form.waiting_for_demolition_link)
async def back_to_start_from_demolition(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()  # Сбрасываем состояние
    user_id = callback_query.from_user.id
    
    # Основное меню
    main_menu = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton(text="🍣 Заказать суши", callback_data="demolition"),
        InlineKeyboardButton("📕 Профиль", callback_data="profile"),
        InlineKeyboardButton("❓Информация", callback_data="about_bot"),
        InlineKeyboardButton("🛍️Цены на суши", callback_data="buy")
    )

    # Добавляем кнопку админ-панели для админов
    if user_id in ADMINS:
        main_menu.add(InlineKeyboardButton("⚙️Админ-панель", callback_data="admin_panel"))

    # Открытие анимации (MP4 вместо изображения)
    try:
        with open("banner.mp4", "rb") as banner:
            await callback_query.message.edit_media(
                media=types.InputMediaAnimation(banner, caption="🍣 Хочешь свежих сушей? Добро пожаловать в PSushi!", parse_mode="HTML"),
                reply_markup=main_menu  # Возвращаем главное меню
            )
    except FileNotFoundError:
        # Если файл не найден, отправляем только текст
        await callback_query.message.edit_text(
            text="🍣 Хочешь свежих сушей? Добро пожаловать в PSushi!",
            parse_mode="HTML",
            reply_markup=main_menu
        )


@dp.callback_query_handler(lambda call: call.data == 'promo')
async def handle_inline_button_click2(call: types.CallbackQuery, state: FSMContext):
    # Сбрасываем состояние перед отправкой промокода
    await state.finish()

    # Создаем клавиатуру с кнопкой "Назад"
    back_button = InlineKeyboardMarkup().add(
        InlineKeyboardButton(text="⚡Назад", callback_data="back_to_profile")
    )

    # Открываем анимацию (MP4 вместо изображения)
    try:
        with open('banner.mp4', 'rb') as had:
            await call.message.edit_media(
                media=types.InputMediaAnimation(
                    media=had,  # Отправляем MP4-анимацию
                    caption="<b>✅ Введите промокод в чат:</b>",  # Новый текст
                    parse_mode="HTML"
                ),
                reply_markup=back_button  # Добавляем кнопку назад
            )
    except FileNotFoundError:
        await call.message.edit_text(
            text="<b>✅ Введите промокод в чат:</b>",
            parse_mode="HTML",
            reply_markup=back_button
        )
    
    # Переход в состояние для промокода
    await MyState.promo.set()


@dp.callback_query_handler(lambda call: call.data == "back_to_profile", state=MyState.promo)
async def back_to_profile(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()  # Сбрасываем состояние, чтобы выйти из режима промокода

    user_id = callback_query.from_user.id

    # Подключаемся к базе данных, чтобы получить информацию о подписке
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subscription_status, subscription_expiry_date
        FROM users WHERE telegram_id = ?
    """, (user_id,))
    user_data = cursor.fetchone()

    cursor.execute("""
        SELECT 1 FROM whitelist WHERE user_id = ?
    """, (user_id,))
    is_in_whitelist = cursor.fetchone() is not None

    conn.close()

    if user_data:
        status, expiry_date = user_data
        try:
            if status == "active" and expiry_date:
                try:
                    expiry_datetime = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    expiry_datetime = datetime.strptime(expiry_date, "%Y-%m-%d")

                remaining_time = expiry_datetime - datetime.now()
                if remaining_time <= timedelta(seconds=0):
                    status = "inactive"
                    remaining_time_str = "У вас нету подписки"
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users SET subscription_expiry_date = NULL WHERE telegram_id = ?
                    """, (user_id,))
                    conn.commit()
                    conn.close()
                else:
                    remaining_time_str = format_remaining_time(remaining_time)

            elif status == "active":
                remaining_time_str = "00:00:00"
                remaining_time = timedelta(0)
            else:
                status = "inactive"
                remaining_time_str = "У вас нету подписки"
                remaining_time = None

            profile_text = await create_profile_caption(user_id, status, remaining_time_str, is_in_whitelist)

        except ValueError:
            profile_text = "❌ Ошибка при обработке данных профиля. Обратитесь в тех.поддержку: @qwesmilw"

    else:
        profile_text = "❌ Ваш профиль не найден."
        remaining_time = None

    # Клавиатура профиля
    profile_keyboard = InlineKeyboardMarkup()
    profile_keyboard.row(
        InlineKeyboardButton(text="❓Информация", callback_data="ruco"),
        InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")
    )
    profile_keyboard.add(
        InlineKeyboardButton(text="🧾 Белый список", callback_data="white"),
        InlineKeyboardButton(text="⚡Назад", callback_data="back_to_start")  # Кнопка "Назад"
    )

    # Если сообщение с фото/анимацией, обновляем его
    try:
        with open("profile_banner.mp4", "rb") as profile_banner:
            await callback_query.message.edit_media(
                media=types.InputMediaAnimation(profile_banner, caption=profile_text, parse_mode="HTML"),
                reply_markup=profile_keyboard
            )
    except FileNotFoundError:
        await callback_query.message.edit_text(profile_text, parse_mode="HTML", reply_markup=profile_keyboard)

    # Если есть время подписки, обновляем его
    if remaining_time is not None:
        await update_subscription(callback_query.message, user_id, remaining_time, is_in_whitelist)


# Генерация промокода
@dp.message_handler(commands=['genpromo'])
async def promo_set(message: types.Message):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    user_id = message.from_user.id

    # Проверка прав администратора
    if int(user_id) not in admin:
        await message.reply("<b>❌ У вас нет прав для выполнения этой команды.</b>", parse_mode="HTML")
        return

    # Разделение текста команды
    text = message.text.split(" ")

    # Проверка, что переданы все аргументы
    if len(text) < 4:
        await message.reply(
            "<b>❌ Неверный формат команды!</b>\n\n"
            "✅ Используйте:\n"
            "/genpromo <код> <дни> <макс. активаций>",
            parse_mode="HTML"
        )
        return

    promo_code, days, activations = text[1], int(text[2]), int(text[3])
    try:
        cursor.execute(
            "INSERT INTO promocodes (code, days, max_activations) VALUES (?, ?, ?)",
            (promo_code, days, activations)
        )
        await message.answer("<b> ✅ Промокод успешно создан!</b>", parse_mode="HTML")
    except sqlite3.IntegrityError:
        await message.answer("<b> ❌ Промокод с таким кодом уже существует!</b>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"<b> ❌ Ошибка при создании промокода:</b> {e}")
    finally:
        conn.commit()
        conn.close()

# Обработка промокода
@dp.message_handler(state=MyState.promo)
async def soso(message: types.Message, state: FSMContext):
    try:
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()

            # Проверка наличия промокода
            cursor.execute("SELECT * FROM promocodes WHERE code = ?", (message.text,))
            promocode = cursor.fetchone()

            # Получение текущей подписки
            cursor.execute("SELECT expiration_date FROM subscriptions WHERE user_id = ?", (message.from_user.id,))
            expiration_date = cursor.fetchone()

            expiration_date = datetime.strptime(expiration_date[0], '%Y-%m-%d %H:%M:%S') if expiration_date else datetime.now()

            if promocode:
                if is_user_in_promocode(message.from_user.id, message.text):
                    await message.reply("<b>❌ Вы уже использовали данный промокод.</b>", parse_mode="HTML")
                elif promocode[4] >= promocode[3]:
                    await message.reply("<b>❌ Данный промокод использовали максимальное количество раз.</b>", parse_mode="HTML")
                else:
                    # Продление подписки
                    new_expiration_date = expiration_date + timedelta(days=promocode[2])
                    cursor.execute(
                        "INSERT OR REPLACE INTO subscriptions (user_id, expiration_date) VALUES (?, ?)",
                        (message.from_user.id, new_expiration_date.strftime('%Y-%m-%d %H:%M:%S'))
                    )

                    # Обновление информации о промокоде
                    used_by = promocode[5] or ""
                    used_by = f"{used_by},{message.from_user.id}".strip(',')
                    cursor.execute(
                        "UPDATE promocodes SET activations_count = activations_count + 1, used_by = ? WHERE code = ?",
                        (used_by, message.text)
                    )

                    await message.reply(f"<b>✅ Подписка на суши продлена на {promocode[2]} дней!</b>", parse_mode="HTML")
                    await bot.send_message(
                        log_chat_id,
                        f" <a href='tg:/openmessage?user_id={message.from_user.id}'>✅ Пользователь</a> ввел промокод <code>{message.text}</code>\n"
                        f"<b>🍣 Дни подписки:</b> <code>{promocode[2]}</code>\n"
                        f"<b>🧾 Осталось активаций:</b> <code>{promocode[3] - (promocode[4] + 1)}</code>",
                        parse_mode="HTML"
                    )
            else:
                await message.reply("<b>❌ Неверный промокод.</b>", parse_mode="HTML")

    except sqlite3.Error as e:
        logging.error(f"❌ Ошибка при обработке промокода: {e}")
        await message.reply("<b>❌ Ошибка при обработке промокода.</b>", parse_mode="HTML")
    finally:
        await state.finish()
        
def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Создаем таблицу whitelist, если она не существует
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

async def get_balance(user_id):
    """
    Получаем текущий баланс пользователя из базы данных.
    """
    conn = sqlite3.connect("users.db")  # или ваша БД
    cursor = conn.cursor()
    cursor.execute("""
        SELECT balance FROM users WHERE telegram_id = ?
    """, (user_id,))
    user_data = cursor.fetchone()

    conn.close()

    if user_data:
        return user_data[0]
    else:
        return 0  # Если пользователя нет в базе, возвращаем 0 как баланс

def create_users_table():
    # Соединение с базой данных (создаст новую БД, если её нет)
    conn = sqlite3.connect("users.db")  # Имя вашей базы данных
    cursor = conn.cursor()
    
    # Создание таблицы users, если она не существует
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            subscription_status TEXT,
            subscription_expiry_date TEXT,
            balance REAL
        )
    """)
    
    conn.commit()
    conn.close()

# Вызовите эту функцию, чтобы создать таблицу, если она ещё не существует
create_users_table()



from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

@dp.callback_query_handler(Text(equals="profile"))
async def profile_command(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subscription_status, subscription_expiry_date
        FROM users WHERE telegram_id = ?
    """, (user_id,))
    user_data = cursor.fetchone()

    cursor.execute("""
        SELECT 1 FROM whitelist WHERE user_id = ?
    """, (user_id,))
    is_in_whitelist = cursor.fetchone() is not None

    conn.close()

    if user_data:
        status, expiry_date = user_data
        try:
            if status == "active" and expiry_date:
                try:
                    expiry_datetime = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    expiry_datetime = datetime.strptime(expiry_date, "%Y-%m-%d")

                remaining_time = expiry_datetime - datetime.now()
                if remaining_time <= timedelta(seconds=0):
                    status = "inactive"
                    remaining_time_str = "У вас нет подписки"
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users SET subscription_expiry_date = NULL WHERE telegram_id = ?
                    """, (user_id,))
                    conn.commit()
                    conn.close()
                else:
                    remaining_time_str = format_remaining_time(remaining_time)

            elif status == "active":
                remaining_time_str = "00:00:00"
                remaining_time = timedelta(0)
            else:
                status = "inactive"
                remaining_time_str = "У вас нет подписки"
                remaining_time = None

            profile_text = await create_profile_caption(user_id, status, remaining_time_str, is_in_whitelist)

        except ValueError:
            profile_text = "❌ Ошибка при обработке данных профиля. Обратитесь в тех.поддержку: @qwesmilw"

    else:
        profile_text = "❌ Ваш профиль не найден."
        remaining_time = None

    profile_keyboard = InlineKeyboardMarkup()
    profile_keyboard.row(
        InlineKeyboardButton(text="❓Информация", callback_data="ruco"),
        InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")
    )
    profile_keyboard.add(
        InlineKeyboardButton(text="🧾 Белый список", callback_data="white"),
        InlineKeyboardButton(text="⚡Назад", callback_data="back_to_start")
    )

    # Отправляем или обновляем MP4-анимацию
    try:
        with open("profile_banner.mp4", "rb") as profile_mp4:
            await callback_query.message.edit_media(
                media=types.InputMediaAnimation(profile_mp4, caption=profile_text, parse_mode="HTML"),
                reply_markup=profile_keyboard
            )
    except FileNotFoundError:
        await callback_query.message.edit_text(profile_text, parse_mode="HTML", reply_markup=profile_keyboard)

    # Обновление времени подписки в профиле каждую секунду
    if remaining_time is not None:
        last_caption = profile_text  # Добавляем переменную `last_caption`

        while remaining_time > timedelta(seconds=0):
            await asyncio.sleep(1)
            remaining_time -= timedelta(seconds=1)

            remaining_time_str = format_remaining_time(remaining_time)
            new_caption = await create_profile_caption(user_id, "active", remaining_time_str, is_in_whitelist)

            if new_caption != last_caption:  # Избегаем лишних обновлений
                try:
                    await callback_query.message.edit_caption(caption=new_caption, reply_markup=profile_keyboard)
                    last_caption = new_caption
                except Exception:
                    pass  # Игнорируем ошибки, если сообщение устарело или удалено
                
            await callback_query.message.edit_reply_markup(reply_markup=profile_keyboard)


    while remaining_time > timedelta(seconds=0):
        await asyncio.sleep(1)  # Обновляем каждую секунду
        remaining_time -= timedelta(seconds=1)

        remaining_time_str = format_remaining_time(remaining_time)
        new_caption = await create_profile_caption(user_id, "active", remaining_time_str, is_in_whitelist)

        if new_caption != last_caption:  # Избегаем лишних обновлений
            try:
                await message.edit_caption(caption=new_caption, reply_markup=profile_keyboard)
                last_caption = new_caption
            except Exception:
                pass  # Игнорируем ошибки, если сообщение устарело или удалено
            
        await message.edit_reply_markup(reply_markup=profile_keyboard)


def format_remaining_time(remaining_time):
    """
    Форматирует оставшееся время в читабельный формат.
    """
    days = remaining_time.days
    hours, remainder = divmod(remaining_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days} дн., {hours:02}:{minutes:02}:{seconds:02}"
    else:
        return f"{hours:02}:{minutes:02}:{seconds:02}"


async def create_profile_caption(user_id, status, remaining_time_str, is_in_whitelist):
    """
    Создает текст профиля пользователя, включая баланс.
    """
    # Получаем баланс пользователя из базы данных
    balance = await get_balance(user_id)

    # Формируем текст профиля с балансом
    profile_text = (
        f"🙂 Ваш ID: {user_id}\n"
        f"🍣 Подписка: {'Активна' if status == 'active' else 'Не активна'}\n"  
        f"❓Осталось времени: {remaining_time_str}\n"  
        f"🧾 Белый список: {'Есть' if is_in_whitelist else 'Нет'}\n"
    )
    
    return profile_text



async def get_balance(user_id: int):
    """
    Получает баланс пользователя из базы данных.
    """
    async with aiosqlite.connect("subscriptions.db") as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        if result:
            return round(result[0], 2)  # Возвращаем баланс с округлением до 2 знаков
    return 0.0  # Если баланс не найден, возвращаем 0



@dp.callback_query_handler(Text(equals="profile"))
async def profile_command(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subscription_status, subscription_expiry_date
        FROM users WHERE telegram_id = ?
    """, (user_id,))
    user_data = cursor.fetchone()

    cursor.execute("""
        SELECT 1 FROM whitelist WHERE user_id = ?
    """, (user_id,))
    is_in_whitelist = cursor.fetchone() is not None

    conn.close()

    if user_data:
        status, expiry_date = user_data
        try:
            if status == "active" and expiry_date:
                try:
                    expiry_datetime = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    expiry_datetime = datetime.strptime(expiry_date, "%Y-%m-%d")

                remaining_time = expiry_datetime - datetime.now()
                if remaining_time <= timedelta(seconds=0):
                    status = "inactive"  
                    remaining_time_str = "У вас нет подписки"  
                    cursor.execute("""
                        UPDATE users SET subscription_expiry_date = NULL WHERE telegram_id = ?
                    """, (user_id,))
                    conn.commit()

                else:
                    remaining_time_str = format_remaining_time(remaining_time)

            elif status == "active":
                remaining_time_str = "00:00:00"  
                remaining_time = timedelta(0)  
            else:
                status = "inactive"  
                remaining_time_str = "У вас нет подписки"  
                remaining_time = None 

            profile_text = await create_profile_caption(user_id, status, remaining_time_str, is_in_whitelist)

        except ValueError:
            profile_text = "❌ Ошибка при обработке данных профиля. Обратитесь в тех.поддержку: @qwesmilw"

    else:
        profile_text = "❌ Ваш профиль не найден."
        remaining_time = None  

    profile_keyboard = InlineKeyboardMarkup()
    profile_keyboard.add(
    )
    profile_keyboard.row(
        InlineKeyboardButton(text="❓Информация", callback_data="ruco"),
        InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")
    )
    profile_keyboard.add(
        InlineKeyboardButton(text="🧾 Белый список", callback_data="white"),
        InlineKeyboardButton(text="⚡Назад", callback_data="back_to_start")
    )

    # Отправляем или обновляем MP4-анимацию
    try:
        with open("profile_banner.mp4", "rb") as profile_mp4:
            await callback_query.message.edit_media(
                media=types.InputMediaAnimation(profile_mp4, caption=profile_text, parse_mode="HTML"),
                reply_markup=profile_keyboard
            )
    except FileNotFoundError:
        await callback_query.message.edit_text(profile_text, parse_mode="HTML", reply_markup=profile_keyboard)

    if remaining_time is not None:
        await update_subscription(callback_query.message, user_id, remaining_time, is_in_whitelist)


async def update_subscription(message, user_id, remaining_time, is_in_whitelist):
    """
    Обновляет время подписки каждую секунду и редактирует сообщение с минимальными изменениями.
    """
    profile_keyboard = InlineKeyboardMarkup()
    profile_keyboard.add(
    )
    profile_keyboard.row(
        InlineKeyboardButton(text="❓Информация", callback_data="ruco"),
        InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")
    )
    profile_keyboard.add(
        InlineKeyboardButton(text="🧾 Белый спсок", callback_data="white"),
        InlineKeyboardButton(text="⚡Назад", callback_data="back_to_start")
    )

    last_caption = None  # Запоминаем последнюю подпись, чтобы не обновлять, если не изменилось

    while remaining_time > timedelta(seconds=0):
        await asyncio.sleep(1)  # Обновляем каждую секунду
        remaining_time -= timedelta(seconds=1)

        remaining_time_str = format_remaining_time(remaining_time)
        new_caption = await create_profile_caption(user_id, "active", remaining_time_str, is_in_whitelist)

        if new_caption != last_caption:  # Избегаем лишних обновлений
            try:
                await message.edit_caption(caption=new_caption, reply_markup=profile_keyboard)
                last_caption = new_caption
            except Exception:
                pass  # Игнорируем ошибки, если сообщение устарело или удалено

        await message.edit_reply_markup(reply_markup=profile_keyboard)
    

def format_remaining_time(remaining_time):
    """
    Форматирует оставшееся время в читабельный формат.
    """
    days = remaining_time.days
    hours, remainder = divmod(remaining_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days} дн., {hours:02}:{minutes:02}:{seconds:02}"
    else:
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    
    return profile_text


# Работа с базой данных
async def add_balance(user_id, amount):
    """
    Добавить баланс пользователю.
    """
    async with aiosqlite.connect("subscriptions.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL
            )
        """)
        await db.execute("""
            INSERT INTO users (user_id, balance)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance=excluded.balance
        """, (user_id, float(amount)))
        await db.commit()


# Конвертация валют
async def convert_to_crypto(amount, asset):
    """
    Конвертирует сумму из выбранной криптовалюты в USD.
    """
    try:
        rates = await get_exchange_rates()
        
        # Печать доступных курсов для дебага
        print(f"💸 Доступные курсы: {rates}")
        
        rate = None
        available_assets = [rate["source"] for rate in rates]  # Все доступные источники
        if asset.upper() not in available_assets:
            raise ValueError(f"❌ Валюта {asset.upper()} не доступна.")
        
        # Ищем курс для указанной валюты
        for exchange_rate in rates:
            if exchange_rate["source"].upper() == asset.upper() and exchange_rate["target"] == 'USD':
                rate = Decimal(str(exchange_rate["rate"]))
                break

        if rate is None:
            raise ValueError(f"❌ Не найден курс обмена для {asset.upper()}.")
        
        amount = Decimal(str(amount))
        return amount / rate
    
    except Exception as e:
        print(f"❌ Ошибка в convert_to_crypto: {e}")
        raise ValueError(f"❌ Ошибка при конвертации {amount} {asset.upper()}: {str(e)}")



async def get_exchange_rates():
    """
    Получить актуальные курсы обмена с API.
    """
    try:
        api_url = "https://pay.crypt.bot/api/getExchangeRates"
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get("ok"):
                return json_data["result"]
        return []
    except requests.RequestException as e:
        print(f"❌ Ошибка при получении курсов обмена: {e}")
        return []


async def get_payment_amount(invoice_id):
    """
    Получить сумму платежа для указанного invoice_id.
    """
    async with aiosqlite.connect("subscriptions.db") as db:
        cursor = await db.execute("SELECT amount FROM payments WHERE invoice_id = ?", (invoice_id,))
        result = await cursor.fetchone()
        if result:
            return Decimal(result[0])
    return Decimal(0)


# Статус и проверка платежа
async def check_payment_status(invoice_id):
    """
    Проверить статус платежа.
    """
    try:
        api_url = f"https://pay.crypt.bot/api/getPaymentStatus?invoice_id={invoice_id}"
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get("ok"):
                status = json_data["result"]["status"]
                return status
        return "failed"
    except requests.RequestException as e:
        print(f"❌ Ошибка при проверке статуса платежа: {e}")
        return "failed"


# Основные обработчики
@dp.callback_query_handler(lambda call: call.data.startswith('check_payment:'))
async def check_payment(call: types.CallbackQuery):
    """
    Проверяет статус платежа по invoice_id и обновляет баланс или активирует подписку.
    """
    _, user_id_str, invoice_id_str = call.data.split(':')
    user_id = int(user_id_str)
    invoice_id = invoice_id_str

    if user_id == call.from_user.id:
        # Получаем статус платежа и связанные данные
        status, payment_link, amount, value = await get_invoice_status(invoice_id)

        if status == "paid":
            # Получаем количество дней подписки по сумме
            duration_days = get_duration_by_amount(amount)

            if duration_days > 0:
                # Активируем подписку
                activate_subscription(user_id, duration_days)

                # Логируем информацию о платеже
                await bot.send_message(
                    log_chat_id,
                    f"<b>💸 Пользователь {user_id} оплатил подписку.\n"
                    f"🍣 Количество дней: {duration_days}\n"
                    f"🛍️ Цена: {amount} {value}</b>",
                    parse_mode="HTML"
                )

                # Подтверждаем пользователю успешную активацию подписки
                await bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption="<b>🍣 Оплата подтверждена! Подписка на суши активирована. Спасибо за покупку.</b>",
                    parse_mode="HTML"
                )
                
                # Обновляем баланс пользователя (если необходимо)
                await add_balance(user_id, amount)
                await call.message.answer(f"Ваш баланс был обновлён на {amount} USD.")
            else:
                await bot.edit_message_caption(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    caption="<b>❌ Ошибка. Недопустимая сумма оплаты.</b>",
                    parse_mode="HTML"
                )
        else:
            await bot.answer_callback_query(call.id, "❌ Оплата не найдена. Попробуйте позже.")
    else:
        await bot.answer_callback_query(call.id, "❌ Вы не можете проверять эту оплату.", show_alert=True)


# Пополнение баланса
@dp.callback_query_handler(lambda call: call.data == "recharge_balance")
async def recharge_balance(call: types.CallbackQuery):
    """
    Показать пользователю варианты пополнения баланса.
    """
    user_id = call.from_user.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="💸 Пополнить через USDT", callback_data="recharge_usdt"))
    markup.add(InlineKeyboardButton(text="⚡Назад", callback_data="profile"))
    
    await call.message.edit_caption(
        caption="💸 Выберите валюту для пополнения баланса:",
        reply_markup=markup
    )


@dp.callback_query_handler(lambda call: call.data.startswith('recharge_'))
async def recharge_currency(call: types.CallbackQuery):
    """
    Обработать пополнение по выбранной валюте.
    """
    currency = call.data.split('_')[1]  # например, 'usdt'
    
    await call.message.answer(f"Введите сумму для пополнения баланса в {currency.upper()} (например, 0.01, 0.5, 1):")
    await dp.register_message_handler(lambda message: process_top_up_currency(message, currency, call.from_user.id), state="*")


async def process_top_up_currency(message: types.Message, currency: str, user_id: int):
    """
    Обработать пополнение валюты, конвертировать сумму и создать платёжную ссылку.
    """
    try:
        amount = float(message.text)
        
        if amount <= 0:
            await message.answer("Сумма должна быть больше 0. Попробуйте ещё раз.")
            return

        converted_amount = await convert_to_crypto(amount, currency)
        payment_link, invoice_id = await generate_payment_link(currency, converted_amount)
        
        if payment_link and invoice_id:
            markup = InlineKeyboardMarkup()
            oplata = InlineKeyboardButton("💸 Оплатить", url=f"{payment_link}")
            check_payment_button = InlineKeyboardButton("💸 Проверить оплату", callback_data=f"check_payment_balance:{user_id}:{invoice_id}")
            markup.add(oplata, check_payment_button)
            markup.add(InlineKeyboardButton("⚡Назад", callback_data="back_to_start"))
            
            await message.answer(
                f"<b>Счёт для пополнения:</b>\n{payment_link}",
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            await message.answer("<b>❌ Не удалось создать счёт для оплаты. Пожалуйста, попробуйте позже.</b>", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Неверный формат суммы. Пожалуйста, введите число.")


@dp.callback_query_handler(lambda call: call.data.startswith('currency_'))
async def currency_selected(call: types.CallbackQuery):
    """
    Обработать выбор валюты и сумму пополнения.
    """
    parts = call.data.split('_')
    currency = parts[1]
    amount = parts[2]

    try:
        converted_amount = await convert_to_crypto(amount, currency)
        payment_link, invoice_id = await generate_payment_link(currency, converted_amount)

        if payment_link and invoice_id:
            markup = InlineKeyboardMarkup()
            oplata = InlineKeyboardButton("💸 Оплатить", url=f"{payment_link}")
            check_payment_button = InlineKeyboardButton("💸 Проверить оплату", callback_data=f"check_payment_balance:{call.from_user.id}:{invoice_id}")
            markup.add(oplata, check_payment_button)
            markup.add(InlineKeyboardButton("⚡Назад", callback_data="back_to_start"))
            
            await bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"<b>💸 Счёт для пополнения:</b>\n{payment_link}",
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            await bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="<b>❌ Не удалось создать счёт для оплаты. Пожалуйста, попробуйте позже.</b>",
                parse_mode="HTML"
            )
    except Exception as e:
        await bot.answer_callback_query(call.id, f"<b>{str(e)}</b>", parse_mode="HTML")

    



@dp.callback_query_handler(lambda call: call.data == 'white')
async def buy_whitelist(call: types.CallbackQuery):
    markup = types.InlineKeyboardMarkup()
    currency_options = [
        ("USDT", "whitelist_USDT"),
        ("TON", "whitelist_TON"),
        ("NOT", "whitelist_NOT"),
        ("BTC", "whitelist_BTC"),
        ("ETH", "whitelist_ETH")
    ]
    for option_text, callback_data in currency_options:
        markup.add(types.InlineKeyboardButton(option_text, callback_data=callback_data))
    
    markup.add(types.InlineKeyboardButton("⚡Назад", callback_data="back_to_start"))
    
    await bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption="<b>💸 Выберите валюту для покупки белого списка (1.5$):</b>",
        reply_markup=markup,
        parse_mode="HTML"
    )

@dp.callback_query_handler(lambda call: call.data.startswith('whitelist_'))
async def whitelist_currency_selected(call: types.CallbackQuery):
    currency = call.data.split('_')[1]
    try:
        amount = 1.5
        converted_amount = await convert_to_crypto(amount, currency)
        payment_link, invoice_id = await generate_payment_link(currency, converted_amount)
        if payment_link and invoice_id:
            markup = types.InlineKeyboardMarkup()
            pay_button = types.InlineKeyboardButton("💸 Оплатить", url=f"{payment_link}")
            check_button = types.InlineKeyboardButton("💸 Проверить оплату", callback_data=f"check_whitelist:{call.from_user.id}:{invoice_id}")
            markup.add(pay_button, check_button)
            
            await bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"<b>💸 Счет для оплаты белого списка (1.5$):</b>\n{payment_link}",
                reply_markup=markup,
                parse_mode="HTML"
            )
        else:
            await bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="<b>❌ Не удалось создать счет для оплаты. Пожалуйста, попробуйте позже.</b>",
                parse_mode="HTML"
            )
    except Exception as e:
        await bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=str(e)
        )

@dp.callback_query_handler(lambda call: call.data.startswith('check_whitelist:'))
async def check_whitelist_payment(call: types.CallbackQuery):
    _, user_id_str, invoice_id = call.data.split(':')
    user_id = int(user_id_str)

    if user_id == call.from_user.id:
        status, payment_link, amount, value = await get_invoice_status(invoice_id)
        if status == "paid" and round(amount, 2) == 1.5:
            await add_to_whitelist(user_id)  # Добавляем пользователя в вайтлист
            await bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="<b>✅ Оплата подтверждена! Вы добавлены в белый список.</b>",
                parse_mode="HTML"
            )
            await bot.send_message(log_chat_id, f"<b💸 Пользователь {user_id} купил белый список за 1.5$.</b>", parse_mode="HTML")
        else:
            await bot.answer_callback_query(call.id, "❌ Оплата не найдена или сумма не соответствует. Попробуйте позже!")
    else:
        await bot.answer_callback_query(call.id, "❌ Вы не можете проверить эту оплату.", show_alert=True)

async def add_to_whitelist(user_id):
    async with aiosqlite.connect("subscriptions.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                user_id INTEGER PRIMARY KEY
            )
        """)
        await db.execute("""
            INSERT OR IGNORE INTO whitelist (user_id) VALUES (?)
        """, (user_id,))
        await db.commit()


@dp.callback_query_handler(Text(equals="ruco"))
async def send_guidance(callback_query: types.CallbackQuery):
    new_text = "Привет! [❓Информация](https://rt.pornhub.com)"

    # Создаем клавиатуру с кнопкой "Назад" (ведет к профилю)
    back_button = InlineKeyboardMarkup()
    back_button.add(InlineKeyboardButton(text="⚡Назад", callback_data="profile"))

    try:
        if callback_query.message.animation:
            # Если сообщение содержит GIF (анимацию)
            await callback_query.message.edit_media(
                media=types.InputMediaAnimation(
                    media=callback_query.message.animation.file_id,
                    caption=new_text,
                    parse_mode="Markdown"
                ),
                reply_markup=back_button
            )
        elif callback_query.message.photo:
            # Если сообщение содержит фото
            await callback_query.message.edit_media(
                media=types.InputMediaPhoto(
                    media=callback_query.message.photo[0].file_id,
                    caption=new_text,
                    parse_mode="Markdown"
                ),
                reply_markup=back_button
            )
        else:
            # Если ни фото, ни GIF нет, просто редактируем текст
            await callback_query.message.edit_text(
                text=new_text,
                parse_mode="Markdown",
                reply_markup=back_button
            )
    except Exception as e:
        print(f"❌ Ошибка при обновлении сообщения: {e}")


@dp.callback_query_handler(Text(equals="profile"))
async def profile_command(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subscription_status, subscription_expiry_date
        FROM users WHERE telegram_id = ?
    """, (user_id,))
    user_data = cursor.fetchone()

    cursor.execute("""
        SELECT 1 FROM whitelist WHERE user_id = ?
    """, (user_id,))
    is_in_whitelist = cursor.fetchone() is not None

    conn.close()

    if user_data:
        status, expiry_date = user_data
        try:
            if status == "active" and expiry_date:
                try:
                    expiry_datetime = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    expiry_datetime = datetime.strptime(expiry_date, "%Y-%m-%d")

                remaining_time = expiry_datetime - datetime.now()
                if remaining_time <= timedelta(seconds=0):
                    status = "inactive"
                    remaining_time_str = "❌ У вас нет подписки"
                else:
                    remaining_time_str = format_remaining_time(remaining_time)
            else:
                status = "inactive"
                remaining_time_str = "❌ У вас нет подписки"

            profile_text = await create_profile_caption(user_id, status, remaining_time_str, is_in_whitelist)

        except ValueError:
            profile_text = "❌ Ошибка при обработке данных профиля."

    else:
        profile_text = "❌ Ваш профиль не найден."

    profile_keyboard = InlineKeyboardMarkup()
    profile_keyboard.row(
        InlineKeyboardButton(text="❓Информация", callback_data="ruco"),
        InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")
    )
    profile_keyboard.add(
        InlineKeyboardButton(text="🧾 Белый список", callback_data="white"),
        InlineKeyboardButton(text="⚡Назад", callback_data="back_to_start")  
    )

    # Если сообщение содержит GIF (mp4), обновляем его
    if callback_query.message.animation:
        await callback_query.message.edit_media(
            media=types.InputMediaAnimation(
                media=callback_query.message.animation.file_id,
                caption=profile_text,
                parse_mode="Markdown"
            ),
            reply_markup=profile_keyboard
        )
    # Если сообщение содержит фото, обновляем его
    elif callback_query.message.photo:
        await callback_query.message.edit_media(
            media=types.InputMediaPhoto(
                media=callback_query.message.photo[0].file_id,
                caption=profile_text,
                parse_mode="Markdown"
            ),
            reply_markup=profile_keyboard
        )
    # Если в сообщении нет медиа, просто обновляем текст
    else:
        await callback_query.message.edit_text(
            text=profile_text,
            parse_mode="Markdown",
            reply_markup=profile_keyboard
        )

    

# Главное меню для админ панели
admin_menu = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text="🍣 Выдать подписку", callback_data="add_subscription"),
    InlineKeyboardButton(text="🍣 Забрать подписку", callback_data="remove_subscription"),
    InlineKeyboardButton(text="🍣 Заблокировать пользователя", callback_data="block_user"),
    InlineKeyboardButton(text="🍣 Разблокировать пользователя", callback_data="unblock_user"),
    InlineKeyboardButton(text="📊Статистика", callback_data="view_stats"),
    InlineKeyboardButton(text="🧾 Рассылка", callback_data="broadcast_message")
)

# Хэндлер для рассылки
@dp.callback_query_handler(Text(equals="broadcast_message"))
async def broadcast_start(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if user_id not in ADMINS:
        await callback_query.answer("❌ У вас нет доступа к этой функции.")
        return

    await callback_query.message.answer("🍣 Введите сообщение для рассылки:")
    await Form.waiting_for_broadcast_message.set()

@dp.message_handler(state=Form.waiting_for_broadcast_message)
async def broadcast_process(message: types.Message, state: FSMContext):
    broadcast_text = message.text
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id FROM users")
    users = cursor.fetchall()
    conn.close()

    success_count = 0
    failed_count = 0

    for user in users:
        try:
            await bot.send_message(user[0], broadcast_text)
            success_count += 1
        except Exception:
            failed_count += 1

    await message.answer(
        f"✅ Рассылка завершена.\n\n"
        f"Успешно: {success_count}\n"
        f"Не доставлено: {failed_count}"
    )
    await state.finish()


# Хэндлер для админ панели
@dp.callback_query_handler(Text(equals="admin_panel"))
async def admin_panel(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in ADMINS:
        await callback_query.answer("✅ У вас нет доступа к этой функции.")
        return

    await callback_query.message.answer("⚙️Админ-панель:", reply_markup=admin_menu)

# Хэндлер для отключения подписки
@dp.callback_query_handler(Text(equals="remove_subscription"))
async def remove_subscription_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("🍣 Введите ID пользователя для забирания подписки:")
    await Form.waiting_for_remove_subscription.set()

@dp.message_handler(state=Form.waiting_for_remove_subscription)
async def remove_subscription_process(message: types.Message, state: FSMContext):
    try:
        target_id = int(message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET subscription_status = 'none' WHERE telegram_id = ?", (target_id,))
        conn.commit()
        conn.close()

        await message.answer(f"🍣 Подписка пользователя с ID {target_id} успешно забрана.")
    except ValueError:
        await message.answer("Неверный формат ID. Введите числовой ID.")
    finally:
        await state.finish()

# Хэндлер Добавления Подписки
@dp.callback_query_handler(Text(equals="add_subscription"))
async def add_subscription_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("🍣 Введите ID пользователя и срок подписки в днях, пример: 7021577409 30):")
    await Form.waiting_for_add_subscription.set()

@dp.message_handler(state=Form.waiting_for_add_subscription)
async def add_subscription_process(message: types.Message, state: FSMContext):
    try:
        # Разбираем входной текст
        target_id, days = map(int, message.text.split())

        # Убедимся, что дни больше 0
        if days <= 0:
            await message.answer("🍣 Количество дней должно быть больше 0.")
            return

        # Получаем текущее время и добавляем количество дней
        expiry_date = datetime.now() + timedelta(days=days)
        
        # Обновляем информацию в базе данных
        conn = get_db_connection()
        cursor = conn.cursor()

        # Обновляем или добавляем новую дату окончания подписки
        cursor.execute("""
            UPDATE users 
            SET subscription_status = 'active', subscription_expiry_date = ?
            WHERE telegram_id = ?
        """, (expiry_date.strftime("%Y-%m-%d %H:%M:%S"), target_id))
        conn.commit()
        conn.close()

        # Отправляем пользователю сообщение об успешной активации
        await message.answer(f"🍣 Подписка на {days} дней активирована для пользователя {target_id}.")
    except ValueError:
        await message.answer("🍣 Неверный формат. Введите ID и срок подписки через пробел.")
    finally:
        await state.finish()


# Хэндлер Блокировки Пользователя
@dp.callback_query_handler(Text(equals="block_user"))
async def block_user_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("🍣 Введите ID пользователя для блокировки:")
    await Form.waiting_for_block_user_id.set()

@dp.message_handler(state=Form.waiting_for_block_user_id)
async def block_user_process(message: types.Message, state: FSMContext):
    try:
        target_id = int(message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_blocked = 1 WHERE telegram_id = ?", (target_id,))
        conn.commit()
        conn.close()

        await message.answer(f"🍣 Пользователь с ID {target_id} заблокирован.")
    except ValueError:
        await message.answer("Неверный формат ID. Введите числовой ID.")
    finally:
        await state.finish()

# Хэндлер Разблокировки Пользователя
@dp.callback_query_handler(Text(equals="unblock_user"))
async def unblock_user_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("🍣 Введите ID пользователя для разблокировки:")
    await Form.waiting_for_block_user_id.set()

@dp.message_handler(state=Form.waiting_for_block_user_id)
async def unblock_user_process(message: types.Message, state: FSMContext):
    try:
        target_id = int(message.text)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_blocked = 0 WHERE telegram_id = ?", (target_id,))
        conn.commit()
        conn.close()

        await message.answer(f"🍣 Пользователь с ID {target_id} разблокирован.")
    except ValueError:
        await message.answer("🍣 Неверный формат ID. Введите числовой ID.")
    finally:
        await state.finish()

# Хэндлер Просмотра Статистики
@dp.callback_query_handler(Text(equals="view_stats"))
async def view_stats(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in ADMINS:
        await callback_query.answer("❌ У вас нет доступа к этой функции.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_status = 'none'")
    without_subs = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_status = 'active'")
    with_subs = cursor.fetchone()[0]
    conn.close()

    stats_text = (
        f"**🍣 Статистика 🍣**:\n\n"
        f"Всего пользователей: {total_users}\n"
        f"Без подписки: {without_subs}\n"
        f"С подпиской: {with_subs}"
    )
    await callback_query.message.answer(stats_text, parse_mode="Markdown")

# Основная функция запуска
if __name__ == '__main__':
    init_db()
    initialize_database()  # Создание таблиц в базе данных
    executor.start_polling(dp, skip_updates=True)
