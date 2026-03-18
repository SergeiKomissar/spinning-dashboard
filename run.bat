@echo off
echo Проверка и установка зависимостей...
pip install -r requirements.txt
if errorlevel 1 (
    echo Ошибка при установке зависимостей
    pause
    exit /b 1
)
echo Starting Streamlit Dashboard...
streamlit run app/Дашборд_нити_с_круткой_100_крм.py
pause 