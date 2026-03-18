import streamlit as st
import sys
import os
from datetime import datetime
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.auth import is_admin, get_visit_stats, logout_button
from utils.constants import COLORS

st.set_page_config(
    page_title="Статистика для администратора",
    page_icon="📊",
    layout="wide"
)

def main():

    # --- Кастомная навигация с русскими названиями ---
    st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)
    st.sidebar.markdown("### Дашборды")
    st.sidebar.page_link("dashboard.py", label="Нить с круткой 100 кр/м", icon="🏭")
    st.sidebar.page_link("pages/1_Дашборд_нити_с_круткой_50_крм.py", label="Нить с круткой 50 кр/м", icon="🧵")
    st.sidebar.markdown("### Контрольные карты")
    st.sidebar.page_link("pages/2_Контрольные_карты_100_крм.py", label="Контрольные карты 100 кр/м", icon="📊")
    st.sidebar.page_link("pages/3_Контрольные_карты_50_крм.py", label="Контрольные карты 50 кр/м", icon="📈")
    st.sidebar.markdown("### Администратор")
    st.sidebar.page_link("pages/5_Статистика_для_администратора.py", label="Статистика посещений", icon="👤")

    if not st.session_state.get('authenticated'):
        st.warning("Необходима авторизация. Перейдите на главную страницу.")
        st.stop()
    
    if not is_admin():
        st.error("Доступ запрещён. Только для администраторов.")
        st.stop()
    
    logout_button()
    
    st.title("📊 Статистика посещений")
    st.markdown(f"Администратор: **{st.session_state.user_info['name']}**")
    st.markdown("---")
    
    stats = get_visit_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Всего посещений", len(stats['visits']))
    with col2:
        st.metric("🟢 Активных сессий", len(stats['active_sessions']))
    with col3:
        total_minutes = sum([v[3] or 0 for v in stats['user_stats']])
        st.metric("⏱️ Общее время (мин)", total_minutes)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.subheader("🟢 Сейчас онлайн")
    if stats['active_sessions']:
        for session in stats['active_sessions']:
            login_time = datetime.fromisoformat(session[2])
            duration = int((datetime.now() - login_time).total_seconds() / 60)
            st.markdown(f"**{session[1]}** ({session[0]}) — {duration} мин")
    else:
        st.info("Нет активных сессий")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.subheader("👥 Статистика по пользователям")
    if stats['user_stats']:
        df_users = pd.DataFrame(stats['user_stats'], 
            columns=['Логин', 'Имя', 'Посещений', 'Всего минут', 'Последний визит'])
        df_users['Последний визит'] = pd.to_datetime(df_users['Последний визит']).dt.strftime('%d.%m.%Y %H:%M')
        st.dataframe(df_users, use_container_width=True, hide_index=True)
    else:
        st.info("Нет данных")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.subheader("📋 Последние посещения")
    if stats['visits']:
        df_visits = pd.DataFrame(stats['visits'],
            columns=['Логин', 'Имя', 'Вход', 'Выход', 'Длительность (мин)'])
        df_visits['Вход'] = pd.to_datetime(df_visits['Вход']).dt.strftime('%d.%m.%Y %H:%M')
        df_visits['Выход'] = df_visits['Выход'].apply(
            lambda x: datetime.fromisoformat(x).strftime('%d.%m.%Y %H:%M') if x else '🟢 Онлайн'
        )
        st.dataframe(df_visits, use_container_width=True, hide_index=True)
    else:
        st.info("Нет данных")

if __name__ == "__main__":
    main()
