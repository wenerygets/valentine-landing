#!/usr/bin/env python3
"""
Скрипт запуска бота
"""

import uvicorn
from main import app
from config import API_HOST, API_PORT

if __name__ == "__main__":
    print("🚀 Запуск Valentine Sale Bot...")
    print(f"📡 API: http://{API_HOST}:{API_PORT}")
    print(f"💬 Telegram бот запущен")
    
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info"
    )
