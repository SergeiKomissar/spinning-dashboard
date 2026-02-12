import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import socket
import time

from utils.constants import DEFAULT_SHEET_ID

@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    """Загрузка данных из Google Sheets"""
    max_retries = 3
    retry_delay = 2

    sheet_id = os.getenv('GOOGLE_SHEET_ID', DEFAULT_SHEET_ID)
    
    for attempt in range(max_retries):
        try:
            # Настройка доступа к Google Sheets
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            
            # Пробуем использовать Streamlit Secrets (для Streamlit Cloud)
            if "gcp_service_account" in st.secrets:
                credentials = Credentials.from_service_account_info(
                    st.secrets["gcp_service_account"],
                    scopes=scope
                )
            else:
                # Fallback на файл credentials.json (для локального запуска)
                from oauth2client.service_account import ServiceAccountCredentials
                credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if not credentials_path:
                    local_path = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
                    root_path = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
                    if os.path.exists(local_path):
                        credentials_path = local_path
                    elif os.path.exists(root_path):
                        credentials_path = root_path
                    else:
                        st.error("Не найден файл credentials.json")
                        return None
                credentials = ServiceAccountCredentials.from_json_keyfile_name(
                    credentials_path,
                    scope
                )
            
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
            columns_list = df.columns.tolist()
            rename_dict = {}
            
            for col in columns_list:
                if col.strip() == 'Линейная плотность, текс ':
                    rename_dict[col] = 'Линейная плотность, текс'
                elif col.strip() == 'Номер ПМ':
                    rename_dict[col] = '№ ПМ'
                elif col.strip() == '№ ПМ ':
                    rename_dict[col] = '№ ПМ'
                elif col.strip() == '№ ПМ':
                    rename_dict[col] = '№ ПМ'
            
            if rename_dict:
                df = df.rename(columns=rename_dict)
            
            if 'Номер ПМ' in df.columns and '№ ПМ' not in df.columns:
                df.columns = [col if col != 'Номер ПМ' else '№ ПМ' for col in df.columns]
            
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
            
            numeric_columns = ['№ партии', '№ ПМ', 'Относительная разрывная нагрузка, сН/текс']
            if speed_col:
                numeric_columns.append(speed_col)
            
            for col in numeric_columns:
                if col in df.columns:
                    # Заменяем запятые на точки перед конвертацией
                    df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            if 'Линейная плотность, текс' in df.columns:
                df['Линейная плотность, текс'] = pd.to_numeric(df['Линейная плотность, текс'], errors='coerce') / 10
            if 'Коэффициент вариации, %' in df.columns:
                df['Коэффициент вариации, %'] = pd.to_numeric(df['Коэффициент вариации, %'], errors='coerce') / 10

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
