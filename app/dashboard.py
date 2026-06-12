import streamlit as st

# Конфигурация страницы - должна быть первой командой Streamlit
st.set_page_config(
    page_title="Качество термообработанной нити",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Главная страница сразу открывает основной дашборд (нить с круткой 50 кр/м).
# Дашборд нити с круткой 100 кр/м перенесён в Архив:
# pages/7_Архив_Дашборд_100_крм.py
st.switch_page("pages/1_Дашборд_нити_с_круткой_50_крм.py")
