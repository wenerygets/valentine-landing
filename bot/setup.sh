#!/bin/bash
# Скрипт установки бота на сервер

echo "🚀 Установка Valentine Bot..."

# Обновление пакетов
apt update

# Установка Python и pip
apt install -y python3 python3-pip python3-venv

# Создание директории для бота
mkdir -p /opt/valentine-bot
cd /opt/valentine-bot

# Копирование файлов (сделай вручную или через git)
# cp /var/www/site/bot/* /opt/valentine-bot/

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install flask flask-cors python-telegram-bot

# Создание systemd сервиса
cat > /etc/systemd/system/valentine-bot.service << 'EOF'
[Unit]
Description=Valentine Sale Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/valentine-bot
Environment=PATH=/opt/valentine-bot/venv/bin
ExecStart=/opt/valentine-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Запуск сервиса
systemctl daemon-reload
systemctl enable valentine-bot
systemctl start valentine-bot

echo "✅ Бот установлен!"
echo "📊 Проверка статуса: systemctl status valentine-bot"
echo "📜 Логи: journalctl -u valentine-bot -f"
