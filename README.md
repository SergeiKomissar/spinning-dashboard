# Дашборд прядильного цеха

Информационная панель для анализа качества нити в прядильном цехе с данными из Google Sheets.

## Установка

1. Создайте виртуальное окружение:
```bash
python3 -m venv venv
source venv/bin/activate  # для Linux/Mac
# или
venv\Scripts\activate  # для Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройка Google Sheets:
- Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
- Включите Google Sheets API
- Создайте сервисный аккаунт и скачайте JSON-ключ
- Переименуйте ключ в `credentials.json` и поместите в корневую папку проекта
- Альтернатива: задайте путь к ключу через `GOOGLE_APPLICATION_CREDENTIALS`
- Предоставьте доступ к вашей таблице для email сервисного аккаунта

4. Настройка таблицы:
- Создайте Google таблицу с нужной структурой
- Поделитесь таблицей с email'ом сервисного аккаунта
- По умолчанию используется встроенный ID таблицы
- Чтобы использовать другую таблицу, задайте переменную окружения `GOOGLE_SHEET_ID`

5. Запуск:
```bash
./run.sh
```

## Быстрый запуск (macOS)

Дважды кликните по `run.command` в корне проекта. Скрипт сам создаст виртуальное окружение, установит зависимости и запустит приложение.

## Структура

```
app/
  dashboard.py            точка входа (Streamlit Cloud) → переход на дашборд крутки 50
  pages/                  страницы; имена файлов = адреса страниц, не переименовывать
  components/
    layout.py             тёмная тема, шапка, боковое меню (NAV_SECTIONS), загрузка данных в сессию
    charts.py             графики дашбордов
    spc.py                контрольные карты Шухарта (ГОСТ ISO 7870-2)
    metrics.py            метрики партии
  utils/
    constants.py          пороги качества, смещения номеров партий, цвета
    google_sheets.py      подключение к Google Таблице (Secrets или credentials.json)
    data_processing.py    загрузка и разбор листа с данными
    machine_health.py     паспорт машин
    ai_summary.py         резюме технолога (диагностика + OpenRouter)
    domain_knowledge.py   справочник производства (лист «Справочник»)
    auth.py               вход по config/users.yaml, журнал посещений
tests/                    тесты и эталонные снимки страниц
```

Новая страница: файл в `app/pages/` + строка в `NAV_SECTIONS` (`components/layout.py`).

## Проверка изменений

```bash
pip install -r requirements-dev.txt
python -m pytest tests
```

Тесты прогоняют все страницы на синтетических данных (без доступа к Google и OpenRouter).

Для рефакторинга есть эталонные снимки: все страницы прогоняются на реальной
выгрузке, перебираются селекторы, и вывод сравнивается до и после изменения.

```bash
python tests/snapshot.py record    # до изменений: записать эталон
python tests/snapshot.py compare   # после: показать, что поменялось на страницах
```

Выгрузка данных для снимков (`tests/.snapshot/real_df.pkl`) хранится только локально.
Версии зависимостей в `requirements.txt` зафиксированы: при обновлении прогоните тесты.
