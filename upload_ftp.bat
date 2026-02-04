@echo off
echo ========================================
echo Загрузка файлов на FTP хостинг
echo ========================================
echo.
echo ВАЖНО: Отредактируйте этот файл и укажите:
echo   - FTP_SERVER (адрес FTP сервера)
echo   - FTP_USER (ваш логин)
echo   - FTP_PASS (ваш пароль)
echo   - FTP_DIR (папка на сервере, обычно /public_html или /www)
echo.
echo Затем запустите этот файл
echo.
pause

REM Пример команды для WinSCP или FileZilla:
REM Используйте FTP клиент для загрузки файлов

REM Или используйте PowerShell:
REM $ftp = "ftp://your-server.com"
REM $user = "your-username"
REM $pass = "your-password"
REM $webClient = New-Object System.Net.WebClient
REM $webClient.Credentials = New-Object System.Net.NetworkCredential($user, $pass)
REM $webClient.UploadFile("$ftp/index_sber.html", "D:\Wildberries\index_sber.html")
