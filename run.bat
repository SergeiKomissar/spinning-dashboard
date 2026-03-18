@echo off
echo Проверка и установка зависимостей...
pip install -r requirements.txt
if errorlevel 1 (
    echo Ошибка при установке зависимостей
    pause
    exit /b 1
)
echo Starting Streamlit Dashboard...
streamlit run app/dashboard.py
pause 