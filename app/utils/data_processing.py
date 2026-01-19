import os
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import socket
import time

from utils.constants import DEFAULT_SHEET_ID


def get_google_credentials():
    """Получение Google credentials (поддержка Streamlit Cloud и локального запуска)"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    # 1. Сначала пробуем Streamlit Cloud secrets
    try:
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials_dict = dict(st.secrets['gcp_service_account'])
            return ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    except Exception:
        pass

    # 2. Пробуем переменную окружения
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if credentials_path and os.path.exists(credentials_path):
        return ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)

    # 3. Пробуем локальные файлы
    local_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
    root_path = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')

    if os.path.exists(local_path):
        return ServiceAccountCredentials.from_json_keyfile_name(local_path, scope)
    elif os.path.exists(root_path):
        return ServiceAccountCredentials.from_json_keyfile_name(root_path, scope)

    return None


@st.cache_data(ttl=1800, show_spinner=False)
def load_data():
    """Загрузка данных из Google Sheets (кэш 30 мин)"""
    max_retries = 3
    retry_delay = 2

    credentials = get_google_credentials()
    if not credentials:
        st.error("Не найдены учётные данные Google. Проверьте credentials.json или secrets.")
        return None

    sheet_id = os.getenv('GOOGLE_SHEET_ID', DEFAULT_SHEET_ID)

    for attempt in range(max_retries):
        try:
            
            # Увеличиваем таймаут подключения
            socket.setdefaulttimeout(20)

            client = gspread.authorize(credentials)
            sheet = client.open_by_key(sheet_id).sheet1
            
            # Получаем и обрабатываем данные
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            # Проверяем, что таблица не пуста
            if len(df.columns) == 0:
                st.error("Таблица пуста или не содержит данных")
                return None
            
            # Обработка данных - исправляем возможные проблемы с названиями колонок
            # Переименовываем колонки вручную, проверяя точное соответствие
            columns_list = df.columns.tolist()
            rename_dict = {}
            
            # Переименовываем колонки по точному совпадению
            for col in columns_list:
                if col.strip() == 'Линейная плотность, текс ':
                    rename_dict[col] = 'Линейная плотность, текс'
                elif col.strip() == 'Номер ПМ':
                    rename_dict[col] = '№ ПМ'  # Переименовываем "Номер ПМ" в "№ ПМ"
                elif col.strip() == '№ ПМ ':
                    rename_dict[col] = '№ ПМ'
                elif col.strip() == '№ ПМ':
                    rename_dict[col] = '№ ПМ'  # На случай если уже есть
            
            # Применяем переименование
            if rename_dict:
                df = df.rename(columns=rename_dict)
            
            # Дополнительная проверка: если "Номер ПМ" все еще есть, переименовываем напрямую
            if 'Номер ПМ' in df.columns and '№ ПМ' not in df.columns:
                df.columns = [col if col != 'Номер ПМ' else '№ ПМ' for col in df.columns]
            
            # Проверяем наличие обязательных колонок после переименования
            required_columns = ['№ партии', '№ ПМ', 'Относительная разрывная нагрузка, сН/текс']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}")
                st.warning(f"Доступные колонки в таблице (после переименования): {', '.join(df.columns.tolist())}")
                return None
            
            # Конвертируем числовые столбцы (только если они существуют)
            numeric_columns = ['№ партии', '№ ПМ', 'Скорость формования, м/мин', 
                             'Относительная разрывная нагрузка, сН/текс']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Делим на 10 линейную плотность и коэффициент вариации (если они существуют)
            if 'Линейная плотность, текс' in df.columns:
                df['Линейная плотность, текс'] = pd.to_numeric(df['Линейная плотность, текс'], errors='coerce') / 10
            if 'Коэффициент вариации, %' in df.columns:
                df['Коэффициент вариации, %'] = pd.to_numeric(df['Коэффициент вариации, %'], errors='coerce') / 10

            # Убираем строки без обязательных данных после конвертации
            df = df.dropna(subset=required_columns)
            
            return df
            
        except (socket.gaierror, socket.timeout) as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            st.error(f"Ошибка сети: Проверьте подключение к интернету. {str(e)}")
            return None
            
        except Exception as e:
            st.error(f"Ошибка при загрузке данных: {str(e)}")
            return None 
