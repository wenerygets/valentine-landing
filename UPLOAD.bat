@echo off
chcp 65001 >nul
color 0A
echo.
echo ================================================
echo    ЗАГРУЗКА ФАЙЛОВ НА ХОСТИНГ
echo ================================================
echo.
echo ВАЖНО: Перед запуском отредактируйте этот файл
echo и укажите данные вашего хостинга ниже:
echo.
echo После этого просто запустите этот файл
echo.
pause
echo.

REM ================================================
REM УКАЖИТЕ ДАННЫЕ ВАШЕГО ХОСТИНГА ЗДЕСЬ:
REM ================================================
set SERVER=your-server.com
set USER=your-username
set REMOTE_PATH=/var/www/html

REM ================================================

echo Проверка наличия scp...
where scp >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] SCP не найден!
    echo.
    echo Установите Git Bash: https://git-scm.com/downloads
    echo Или используйте WinSCP: https://winscp.net/
    echo.
    pause
    exit /b 1
)

echo Подключение к серверу: %SERVER%
echo Пользователь: %USER%
echo Удаленная папка: %REMOTE_PATH%
echo.

cd /d D:\Wildberries

echo Создание папок на сервере...
ssh %USER%@%SERVER% "mkdir -p %REMOTE_PATH%/css/v2 %REMOTE_PATH%/js %REMOTE_PATH%/images %REMOTE_PATH%/favicons"

echo.
echo Загрузка файлов...
echo.

echo [1/8] index_sber.html
scp index_sber.html %USER%@%SERVER%:%REMOTE_PATH%/

echo [2/8] css/v2/main.css
scp css\v2\main.css %USER%@%SERVER%:%REMOTE_PATH%/css/v2/

echo [3/8] css/v2/style.css
scp css\v2\style.css %USER%@%SERVER%:%REMOTE_PATH%/css/v2/

echo [4/8] js/core.min.js
scp js\core.min.js %USER%@%SERVER%:%REMOTE_PATH%/js/

echo [5/8] js/base_v2.js
scp js\base_v2.js %USER%@%SERVER%:%REMOTE_PATH%/js/

echo [6/8] images/sberbank-logo.befb25b6.svg
scp images\sberbank-logo.befb25b6.svg %USER%@%SERVER%:%REMOTE_PATH%/images/

echo [7/8] images/logo.png
scp images\logo.png %USER%@%SERVER%:%REMOTE_PATH%/images/

echo [8/8] favicons/favicon_sber.ico
scp favicons\favicon_sber.ico %USER%@%SERVER%:%REMOTE_PATH%/favicons/

echo.
echo ================================================
echo    ЗАГРУЗКА ЗАВЕРШЕНА!
echo ================================================
echo.
echo Проверьте страницу: http://your-domain.com/index_sber.html
echo.
pause
