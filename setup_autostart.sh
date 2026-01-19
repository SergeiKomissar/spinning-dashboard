#!/bin/bash
# Настройка автозапуска дашборда при включении Mac

DASHBOARD_DIR="$HOME/DashboardPVV/Dashboard"
PLIST_NAME="com.spinning.dashboard.plist"

echo "🔧 Настройка автозапуска..."

# Проверяем что папка Dashboard в домашней директории
if [ ! -d "$DASHBOARD_DIR" ]; then
    echo "❌ Папка $DASHBOARD_DIR не найдена!"
    echo "   Переместите папку Dashboard в домашнюю директорию: ~/Dashboard"
    exit 1
fi

# Создаём LaunchAgents если не существует
mkdir -p ~/Library/LaunchAgents

# Обновляем путь в plist
sed "s|~/Dashboard|$DASHBOARD_DIR|g" "$DASHBOARD_DIR/$PLIST_NAME" > ~/Library/LaunchAgents/$PLIST_NAME

# Загружаем агент
launchctl unload ~/Library/LaunchAgents/$PLIST_NAME 2>/dev/null
launchctl load ~/Library/LaunchAgents/$PLIST_NAME

echo ""
echo "✅ Автозапуск настроен!"
echo ""
echo "Дашборд будет автоматически запускаться при включении Mac."
echo ""
echo "Команды управления:"
echo "  Остановить:  launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
echo "  Запустить:   launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
echo "  Логи:        tail -f /tmp/dashboard.log"
echo ""
