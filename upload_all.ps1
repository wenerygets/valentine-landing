# PowerShell скрипт для загрузки всех файлов на сервер
# Использование: .\upload_all.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Загрузка файлов на хостинг" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========================================
# НАСТРОЙКИ - ЗАПОЛНИТЕ СВОИ ДАННЫЕ
# ========================================
$SERVER = Read-Host "Введите адрес сервера (например: your-server.com или IP)"
$USER = Read-Host "Введите ваш логин на сервере"
$REMOTE_PATH = Read-Host "Введите путь к папке сайта (например: /var/www/html или /public_html)"

# Локальная папка
$LOCAL_DIR = "D:\Wildberries"

Write-Host ""
Write-Host "Подключение к серверу..." -ForegroundColor Yellow
Write-Host "Сервер: $SERVER" -ForegroundColor Gray
Write-Host "Пользователь: $USER" -ForegroundColor Gray
Write-Host "Удаленная папка: $REMOTE_PATH" -ForegroundColor Gray
Write-Host ""

# Проверка наличия scp
$scpPath = Get-Command scp -ErrorAction SilentlyContinue

if (-not $scpPath) {
    Write-Host "ОШИБКА: SCP не найден!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Варианты решения:" -ForegroundColor Yellow
    Write-Host "1. Установите Git Bash: https://git-scm.com/downloads" -ForegroundColor White
    Write-Host "2. Используйте WinSCP: https://winscp.net/" -ForegroundColor White
    Write-Host "3. Используйте FileZilla: https://filezilla-project.org/" -ForegroundColor White
    pause
    exit
}

# Список файлов для загрузки
$files = @(
    @{Local="index_sber.html"; Remote="index_sber.html"},
    @{Local="css\v2\main.css"; Remote="css/v2/main.css"},
    @{Local="css\v2\style.css"; Remote="css/v2/style.css"},
    @{Local="js\core.min.js"; Remote="js/core.min.js"},
    @{Local="js\base_v2.js"; Remote="js/base_v2.js"},
    @{Local="images\sberbank-logo.befb25b6.svg"; Remote="images/sberbank-logo.befb25b6.svg"},
    @{Local="images\logo.png"; Remote="images/logo.png"},
    @{Local="favicons\favicon_sber.ico"; Remote="favicons/favicon_sber.ico"}
)

Write-Host "Создание структуры папок на сервере..." -ForegroundColor Yellow
ssh "${USER}@${SERVER}" "mkdir -p ${REMOTE_PATH}/css/v2 ${REMOTE_PATH}/js ${REMOTE_PATH}/images ${REMOTE_PATH}/favicons"

Write-Host ""
Write-Host "Загрузка файлов..." -ForegroundColor Green
Write-Host ""

$successCount = 0
$failCount = 0

foreach ($file in $files) {
    $localPath = Join-Path $LOCAL_DIR $file.Local
    $remotePath = "${USER}@${SERVER}:${REMOTE_PATH}/$($file.Remote)"
    
    if (Test-Path $localPath) {
        Write-Host "Загружаю: $($file.Remote)" -ForegroundColor Yellow
        
        scp $localPath $remotePath
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Успешно" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "  ✗ Ошибка" -ForegroundColor Red
            $failCount++
        }
    } else {
        Write-Host "⚠ Файл не найден: $localPath" -ForegroundColor Yellow
        $failCount++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Результат:" -ForegroundColor Cyan
Write-Host "  Успешно: $successCount" -ForegroundColor Green
Write-Host "  Ошибок: $failCount" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Green" })
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($successCount -gt 0) {
    Write-Host "Проверьте страницу: http://your-domain.com/index_sber.html" -ForegroundColor Green
}

pause
