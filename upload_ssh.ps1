# PowerShell скрипт для загрузки через SCP/SSH
# Использование: .\upload_ssh.ps1

# ========================================
# НАСТРОЙКИ - ЗАПОЛНИТЕ СВОИ ДАННЫЕ
# ========================================
$SSH_HOST = "your-server.com"           # Адрес сервера
$SSH_USER = "your-username"             # Ваш логин
$SSH_KEY = "C:\path\to\your\key.pem"    # Путь к SSH ключу (или используйте пароль)
$REMOTE_DIR = "/var/www/html"           # Папка на сервере

# Локальная папка с файлами
$LOCAL_DIR = "D:\Wildberries"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Загрузка файлов на хостинг через SCP" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка наличия scp (обычно в Git Bash или WSL)
$scpPath = Get-Command scp -ErrorAction SilentlyContinue

if (-not $scpPath) {
    Write-Host "ОШИБКА: SCP не найден!" -ForegroundColor Red
    Write-Host "Установите Git Bash или используйте WinSCP/FileZilla" -ForegroundColor Yellow
    pause
    exit
}

# Список файлов для загрузки
$files = @(
    "index_sber.html",
    "css\v2\main.css",
    "css\v2\style.css",
    "js\core.min.js",
    "js\base_v2.js",
    "images\sberbank-logo.befb25b6.svg",
    "images\logo.png",
    "favicons\favicon_sber.ico"
)

Write-Host "Загрузка файлов..." -ForegroundColor Green

foreach ($file in $files) {
    $localPath = Join-Path $LOCAL_DIR $file
    $remotePath = "$SSH_USER@${SSH_HOST}:$REMOTE_DIR/$file"
    
    if (Test-Path $localPath) {
        Write-Host "Загружаю: $file" -ForegroundColor Yellow
        
        # Создаём папки на сервере если нужно
        $remoteDir = Split-Path $file -Parent
        if ($remoteDir) {
            ssh "$SSH_USER@${SSH_HOST}" "mkdir -p $REMOTE_DIR/$remoteDir"
        }
        
        # Загружаем файл
        scp -i $SSH_KEY $localPath $remotePath
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ $file загружен" -ForegroundColor Green
        } else {
            Write-Host "✗ Ошибка загрузки $file" -ForegroundColor Red
        }
    } else {
        Write-Host "⚠ Файл не найден: $localPath" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Готово!" -ForegroundColor Green
pause
