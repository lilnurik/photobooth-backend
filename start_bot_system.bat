@echo off
echo ============================================================
echo   ЗАПУСК СИСТЕМЫ PHOTOBOOTH
echo ============================================================
echo.

REM Проверка токена бота
if not defined TELEGRAM_BOT_TOKEN (
    echo [!] ВНИМАНИЕ: Не установлен TELEGRAM_BOT_TOKEN
    echo.
    echo Установите токен:
    echo   set TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
    echo.
    echo Затем перезапустите этот скрипт
    echo.
    pause
    exit /b 1
)

echo ✅ Токен бота установлен
echo.

REM Проверка зависимостей
echo Проверка зависимостей...
pip show pyTelegramBotAPI >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] Telegram Bot API не установлен
    echo Установка зависимостей...
    pip install -r requirements.txt
    echo.
)

echo.
echo 🚀 Запуск Backend + Telegram Bot...
echo.
echo Flask API будет доступен на: http://localhost:5000
echo Telegram Bot запустится автоматически
echo.
echo ============================================================
echo Нажмите Ctrl+C для остановки
echo ============================================================
echo.

python app.py

pause
