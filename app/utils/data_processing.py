import pandas as pd
import streamlit as st
import socket
import time

from utils.google_sheets import open_spreadsheet

# Варианты названий колонок в таблице → каноническое имя
COLUMN_ALIASES = {
    'Номер ПМ': '№ ПМ',
}


@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    """Загрузка данных из Google Sheets"""
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            # Увеличиваем таймаут подключения
            socket.setdefaulttimeout(20)
            try:
                spreadsheet = open_spreadsheet()
            except FileNotFoundError as e:
                st.error(str(e))
                return None
            sheet = spreadsheet.sheet1

            # Получаем данные через get_all_values (надёжнее get_all_records для больших таблиц)
            # UNFORMATTED_VALUE — сырые числа без разделителей тысяч (проблема с партиями >999)
            all_values = sheet.get_all_values(value_render_option='UNFORMATTED_VALUE')
            return prepare_dataframe(all_values)

        except (socket.gaierror, socket.timeout) as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            st.error(f"Ошибка сети: Проверьте подключение к интернету. {str(e)}")
            return None
            
        except Exception as e:
            st.error(f"Ошибка при загрузке данных: {str(e)}")
            return None


def prepare_dataframe(all_values):
    """Таблица из get_all_values → DataFrame: имена колонок, числа, масштаб.
    При проблеме с форматом показывает ошибку и возвращает None."""
    if len(all_values) < 2:
        st.error("Таблица пуста")
        return None
    headers = all_values[0]
    rows = all_values[1:]
    df = pd.DataFrame(rows, columns=headers)

    # Убираем полностью пустые строки
    df = df.replace('', pd.NA).dropna(how='all')

    # Проверяем, что таблица не пуста
    if len(df.columns) == 0:
        st.error("Таблица пуста или не содержит данных")
        return None

    # Названия колонок в таблице бывают с лишними пробелами или в старом варианте
    df = df.rename(columns=lambda col: COLUMN_ALIASES.get(col.strip(), col.strip()))

    required_columns = ['№ партии', '№ ПМ', 'Относительная разрывная нагрузка, сН/текс']
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.error(f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}")
        st.warning(f"Доступные колонки в таблице: {', '.join(df.columns.tolist())}")
        return None

    # Находим колонку скорости
    speed_col = None
    for c in df.columns:
        if 'Скорость' in c and 'формования' in c:
            speed_col = c
            break

    numeric_columns = ['№ партии', '№ ПМ', 'Относительная разрывная нагрузка, сН/текс', 'Крутка']
    if speed_col:
        numeric_columns.append(speed_col)

    for col in numeric_columns:
        if col in df.columns:
            # Заменяем запятые на точки перед конвертацией
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'Линейная плотность, текс' in df.columns:
        df['Линейная плотность, текс'] = pd.to_numeric(df['Линейная плотность, текс'], errors='coerce')
        # Если значения > 100 — данные пришли как целые (287 вместо 28.7), делим на 10
        if df['Линейная плотность, текс'].median() > 100:
            df['Линейная плотность, текс'] = df['Линейная плотность, текс'] / 10
    if 'Коэффициент вариации, %' in df.columns:
        df['Коэффициент вариации, %'] = pd.to_numeric(df['Коэффициент вариации, %'], errors='coerce')
        # Если значения > 50 — данные пришли как целые (76 вместо 7.6), делим на 10
        if df['Коэффициент вариации, %'].median() > 50:
            df['Коэффициент вариации, %'] = df['Коэффициент вариации, %'] / 10

    df = df.dropna(subset=required_columns)

    return df
