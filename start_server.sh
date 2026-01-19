#!/bin/bash
# Запуск дашборда как сервера

cd "$(dirname "$0")"
source venv/bin/activate

echo "🚀 Запуск дашборда..."
echo "📍 Локальный доступ: http://localhost:8501"
echo "📍 Сетевой доступ: http://$(ipconfig getifaddr en0):8501"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo ""

streamlit run app/dashboard.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
