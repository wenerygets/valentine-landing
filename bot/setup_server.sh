#!/bin/bash
# ============================================
# Скрипт установки бота на сервер
# ============================================

echo "🚀 Установка Valentine Sale Bot..."

# Создаём директорию
sudo mkdir -p /opt/valentine-bot
sudo mkdir -p /opt/valentine-bot/data

# Копируем файлы
sudo cp -r ./* /opt/valentine-bot/

# Создаём виртуальное окружение
cd /opt/valentine-bot
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install --upgrade pip
pip install -r requirements.txt

# Создаём systemd сервис
sudo tee /etc/systemd/system/valentine-bot.service > /dev/null <<EOF
[Unit]
Description=Valentine Sale Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/valentine-bot
ExecStart=/opt/valentine-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Перезагружаем systemd
sudo systemctl daemon-reload
sudo systemctl enable valentine-bot
sudo systemctl start valentine-bot

echo "✅ Бот установлен и запущен!"
echo "📋 Проверка статуса: systemctl status valentine-bot"
echo "📋 Логи: journalctl -u valentine-bot -f"
