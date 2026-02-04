#!/bin/bash
# Команды для загрузки файлов на сервер через терминал
# Выполните эти команды на вашем сервере

# 1. Создайте структуру папок на сервере
mkdir -p css/v2
mkdir -p js
mkdir -p images
mkdir -p favicons

# 2. Если вы на ЛОКАЛЬНОЙ машине (Windows), используйте SCP для загрузки:
# scp index_sber.html user@server.com:/path/to/public_html/
# scp css/v2/main.css user@server.com:/path/to/public_html/css/v2/
# scp css/v2/style.css user@server.com:/path/to/public_html/css/v2/
# scp js/core.min.js user@server.com:/path/to/public_html/js/
# scp js/base_v2.js user@server.com:/path/to/public_html/js/
# scp images/sberbank-logo.befb25b6.svg user@server.com:/path/to/public_html/images/
# scp images/logo.png user@server.com:/path/to/public_html/images/
# scp favicons/favicon_sber.ico user@server.com:/path/to/public_html/favicons/

# 3. ИЛИ если вы УЖЕ на сервере, создайте файлы через nano/vim:
# nano index_sber.html
# (скопируйте содержимое файла)

# 4. ИЛИ загрузите через wget/curl если файлы на временном хостинге:
# wget https://your-temp-host.com/index_sber.html

# 5. ИЛИ используйте rsync (если установлен):
# rsync -avz --progress /local/path/ user@server.com:/remote/path/
