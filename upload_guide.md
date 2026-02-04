# 📤 Загрузка через терминал сервера

## Если вы УЖЕ подключены к серверу через SSH:

### Вариант 1: Загрузить файлы с локальной машины на сервер

На **локальной машине** (Windows) выполните:

```powershell
# Перейдите в папку с файлами
cd D:\Wildberries

# Загрузите файлы через SCP (замените данные)
scp index_sber.html user@your-server.com:/var/www/html/
scp -r css user@your-server.com:/var/www/html/
scp -r js user@your-server.com:/var/www/html/
scp -r images user@your-server.com:/var/www/html/
scp -r favicons user@your-server.com:/var/www/html/
```

### Вариант 2: Создать файлы прямо на сервере

Если вы **уже на сервере**, создайте файлы:

```bash
# 1. Перейдите в папку сайта
cd /var/www/html  # или /public_html, или другая папка

# 2. Создайте структуру папок
mkdir -p css/v2 js images favicons

# 3. Создайте файлы через nano/vim
nano index_sber.html
# Скопируйте содержимое из локального файла и вставьте

# Или используйте cat для создания файла:
cat > index_sber.html << 'EOF'
[вставьте содержимое файла]
EOF
```

### Вариант 3: Загрузить архив и распаковать

На **локальной машине**:
```powershell
# Создайте архив
Compress-Archive -Path index_sber.html, css, js, images, favicons -DestinationPath site.zip
```

На **сервере**:
```bash
# Загрузите архив через SCP (с локальной машины)
# scp site.zip user@server.com:/tmp/

# Распакуйте
cd /var/www/html
unzip /tmp/site.zip
```

### Вариант 4: Использовать Git (если есть репозиторий)

```bash
git clone your-repo-url
cd your-repo
# Файлы уже на сервере
```

---

## 📋 Минимальный набор команд для быстрой загрузки:

**На локальной машине (PowerShell):**
```powershell
cd D:\Wildberries
scp index_sber.html user@server.com:/var/www/html/
scp css/v2/main.css user@server.com:/var/www/html/css/v2/
scp css/v2/style.css user@server.com:/var/www/html/css/v2/
scp js/core.min.js user@server.com:/var/www/html/js/
scp js/base_v2.js user@server.com:/var/www/html/js/
scp images/sberbank-logo.befb25b6.svg user@server.com:/var/www/html/images/
scp images/logo.png user@server.com:/var/www/html/images/
scp favicons/favicon_sber.ico user@server.com:/var/www/html/favicons/
```

---

## ❓ Какой вариант вам подходит?

1. **Вы на сервере** → используйте Вариант 2 (создание файлов)
2. **Вы на локальной машине** → используйте Вариант 1 (SCP)
3. **Нужно быстро** → используйте Вариант 3 (архив)

Скажите, где вы сейчас (на сервере или локально), и я дам точные команды!
