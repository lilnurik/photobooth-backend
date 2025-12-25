@echo off
echo.
echo ═══════════════════════════════════════════════════════════
echo   БЫСТРЫЙ ЗАПУСК BACKEND + BOT
echo ═══════════════════════════════════════════════════════════
echo.

REM Проверка токена
if "%TELEGRAM_BOT_TOKEN%"=="" (
    echo ❌ ОШИБКА: Токен не установлен!
    echo.
    echo Выполните сначала:
    echo   set TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
    echo.
    echo Затем запустите этот файл снова
    echo.
    pause
    exit /b 1
)

echo ✅ Токен установлен
echo.
echo Запуск системы...
echo.

python app.py

pause
