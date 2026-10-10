"""Подключение к Google Таблице «СтатПряд2025».

Учётные данные сервисного аккаунта:
- Streamlit Cloud: секция [gcp_service_account] в Secrets;
- локально: файл из GOOGLE_APPLICATION_CREDENTIALS, app/credentials.json
  или credentials.json в корне проекта.
"""
import os

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

from utils.constants import DEFAULT_SHEET_ID

SCOPES = ['https://spreadsheets.google.com/feeds',
          'https://www.googleapis.com/auth/drive']

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_CANDIDATES = (
    os.path.join(_APP_DIR, 'credentials.json'),
    os.path.join(os.path.dirname(_APP_DIR), 'credentials.json'),
)


def _secret(key):
    """Значение из st.secrets или None. Без secrets.toml (локальный запуск)
    обращение к st.secrets бросает исключение — это не ошибка."""
    try:
        return st.secrets[key] if key in st.secrets else None
    except Exception:
        return None


def find_credentials_file():
    path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if path:
        return path
    for cand in CREDENTIALS_CANDIDATES:
        if os.path.exists(cand):
            return cand
    return None


def get_credentials():
    info = _secret('gcp_service_account')
    if info:
        return Credentials.from_service_account_info(info, scopes=SCOPES)
    path = find_credentials_file()
    if not path:
        raise FileNotFoundError("Не найден файл credentials.json")
    return Credentials.from_service_account_file(path, scopes=SCOPES)


def open_spreadsheet():
    client = gspread.authorize(get_credentials())
    return client.open_by_key(os.getenv('GOOGLE_SHEET_ID', DEFAULT_SHEET_ID))
