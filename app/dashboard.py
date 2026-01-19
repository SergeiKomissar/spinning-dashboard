import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys
import os
import time

# Конфигурация страницы - должна быть первой командой Streamlit
st.set_page_config(
    page_title="Отчёт | Качество нити",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from components.charts import create_gauge_chart, create_trend_chart, create_heatmap, create_problem_machines_chart, create_quality_scatter, create_sparkline, create_mini_indicator
from components.metrics import calculate_party_metrics, get_status_indicator, get_quality_score
from components.layout import render_page_header, render_party_header, render_metrics_section
from utils.data_processing import load_data
from utils.constants import QUALITY_THRESHOLDS, COLORS, GAUGE_CONFIG
from utils.auth import login_form, logout_button, is_admin
import pandas as pd


def main():
    # Проверка авторизации
    if not login_form():
        return

    render_page_header()
    
    # Приветствие и кнопка выхода
    col_user, col_logout = st.columns([5, 1])
    with col_user:
        st.markdown(f"Добро пожаловать, **{st.session_state.user_info['name']}**!")
    with col_logout:
        logout_button()
    
    # Ссылка на статистику для админа (в сайдбаре)
    if is_admin():
        st.sidebar.markdown("### 📊 Навигация")
        st.sidebar.page_link("dashboard.py", label="📋 Отчёт")
        st.sidebar.markdown("### 🔧 Админ-панель")
        st.sidebar.page_link("pages/1_admin_stats.py", label="📈 Статистика посещений")

    
    # Загружаем данные с прогресс-баром
    if 'df' not in st.session_state or st.session_state.df is None:
        # Показываем заглушку пока грузятся данные
        loading_placeholder = st.empty()
        with loading_placeholder.container():
            st.markdown("""
                <div style="text-align:center; padding: 60px 20px;">
                    <h2 style="color: #F1F5F9;">🔄 Загрузка дашборда...</h2>
                    <p style="color: #94A3B8;">Подключение к Google Sheets</p>
                </div>
            """, unsafe_allow_html=True)
            progress_bar = st.progress(0)

            progress_bar.progress(10, text="📡 Подключение...")
            st.session_state.df = load_data()
            progress_bar.progress(100, text="✅ Готово!")
            time.sleep(0.2)

        loading_placeholder.empty()

    df = st.session_state.df

    if df is None:
        st.error("❌ Не удалось загрузить данные. Проверьте подключение к Google Sheets.")
        return
    
    # Кнопка обновления данных
    col_refresh, col_space = st.columns([1, 5])
    with col_refresh:
        if st.button('🔄 Обновить данные', key="refresh_button"):
            progress_bar = st.progress(0, text="🔄 Очистка кэша...")
            load_data.clear()
            progress_bar.progress(30, text="📊 Загрузка новых данных...")
            new_data = load_data()
            if new_data is not None:
                progress_bar.progress(90, text="✅ Обработка...")
                st.session_state.df = new_data
                progress_bar.progress(100, text="✅ Данные обновлены!")
                time.sleep(0.5)
                st.rerun()
            else:
                progress_bar.empty()
                st.error('❌ Ошибка обновления')

    try:
        if df.empty:
            st.warning("⚠️ Данные отсутствуют")
            return

        # Получаем данные последней партии
        last_party_series = df['№ партии'].dropna()
        if last_party_series.empty:
            st.warning("⚠️ Нет данных о номерах партий")
            return
        
        last_party = last_party_series.max()
        last_party_data = df[df['№ партии'] == last_party]
        
        # Заголовок партии
        render_party_header(last_party)
        
        # Расчет метрик
        metrics = calculate_party_metrics(last_party_data)
        
        # Секция метрик
        render_metrics_section(metrics)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # === GAUGE ИНДИКАТОРЫ ===
        st.markdown(f"""
            <div class="section-header">
                <span class="icon">📊</span>Показатели качества
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            good_count = metrics['total_machines'] - metrics['low_strength_count']
            fig1 = create_gauge_chart(
                metrics['avg_strength'], 
                'strength',
                good_count,
                metrics['total_machines']
            )
            st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
        
        with col2:
            good_count = metrics['total_machines'] - metrics['high_cv_count']
            fig2 = create_gauge_chart(
                metrics['avg_cv'], 
                'cv',
                good_count,
                metrics['total_machines']
            )
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
        
        with col3:
            good_count = metrics['total_machines'] - metrics['bad_density_count']
            fig3 = create_gauge_chart(
                metrics['avg_density'] if metrics['avg_density'] > 0 else 28.9, 
                'density',
                good_count,
                metrics['total_machines']
            )
            st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # === ГРАФИК ТРЕНДА ===
        st.markdown(f"""
            <div class="section-header">
                <span class="icon">📈</span>Динамика по партиям
            </div>
        """, unsafe_allow_html=True)
        
        last_10_parties = (
            df.groupby('№ партии')
            .agg({'Относительная разрывная нагрузка, сН/текс': 'mean'})
            .round(1)
            .tail(10)
        )
        
        trend_fig = create_trend_chart(last_10_parties)
        st.plotly_chart(trend_fig, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # === АНАЛИТИКА КАЧЕСТВА ===
        st.markdown(f"""
            <div class="section-header">
                <span class="icon">🎯</span>Аналитика качества
            </div>
        """, unsafe_allow_html=True)
        
        # --- ГРАФИК 1: Проблемные машины ---
        st.markdown(f"""
            <div class="info-block">
                <h4>📊 Топ проблемных машин</h4>
                <p>Машины с наибольшим количеством отклонений за последние 10 партий. 
                Красный — критично (4+), оранжевый — требует внимания.</p>
            </div>
        """, unsafe_allow_html=True)
        
        problem_chart = create_problem_machines_chart(df, last_n_parties=10)
        st.plotly_chart(problem_chart, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- ГРАФИК 2: Карта качества (в сворачиваемом блоке для скорости) ---
        with st.expander("🗺️ Карта качества партии", expanded=False):
            st.markdown(f"""
                <p style="color:{COLORS['text_secondary']}; font-size:13px; margin-bottom:12px;">
                Каждая точка — машина. По X — разрывная нагрузка (↑ лучше),
                по Y — коэф. вариации (↓ лучше). Зелёная зона — норма.</p>
            """, unsafe_allow_html=True)

            # Выбор партии
            all_parties = sorted(df['№ партии'].dropna().unique(), reverse=True)
            display_parties = [f"Партия {int(p) - 714}" for p in all_parties[:20]]

            selected_idx = st.selectbox(
                "Выберите партию для анализа:",
                range(len(display_parties)),
                format_func=lambda x: display_parties[x],
                key="party_selector"
            )
            selected_party = all_parties[selected_idx]

            scatter_chart = create_quality_scatter(df, selected_party)
            st.plotly_chart(scatter_chart, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # === РЕЗУЛЬТАТЫ ПО МАШИНАМ ===
        st.markdown(f"""
            <div class="section-header">
                <span class="icon">🔧</span>Результаты по машинам
            </div>
            <p style="color: {COLORS['text_secondary']}; margin-bottom: 16px; font-size: 13px;">
                Среднее значение за последние 5 партий. Нажмите на машину для детального просмотра.
            </p>
        """, unsafe_allow_html=True)

        # Данные за последние 5 партий
        last_5_parties_list = sorted(df['№ партии'].dropna().unique())[-5:]
        df_last5 = df[df['№ партии'].isin(last_5_parties_list)]
        machines = sorted(df_last5['№ ПМ'].dropna().unique())

        # Пагинация - показываем по 10 машин
        MACHINES_PER_PAGE = 10
        total_machines = len(machines)

        # Инициализация состояния пагинации
        if 'machines_page' not in st.session_state:
            st.session_state.machines_page = 1

        total_pages = (total_machines + MACHINES_PER_PAGE - 1) // MACHINES_PER_PAGE
        current_page = st.session_state.machines_page

        # Вычисляем диапазон машин для текущей страницы
        start_idx = (current_page - 1) * MACHINES_PER_PAGE
        end_idx = min(start_idx + MACHINES_PER_PAGE, total_machines)
        machines_to_show = machines[start_idx:end_idx]

        # Заголовки (без линейной плотности)
        header_cols = st.columns([1, 3, 3])
        headers = ['№', '⚡ Разрывная нагрузка (ср. за 5 партий)', '📊 Коэф. вариации (ср. за 5 партий)']
        for col, header in zip(header_cols, headers):
            with col:
                st.markdown(f"<div style='text-align:center; font-weight:bold; color:{COLORS['text']}; font-size:13px;'>{header}</div>", unsafe_allow_html=True)

        # Легенда
        st.markdown(f"""
            <div style="text-align:center; color:{COLORS['text_secondary']}; font-size:11px; margin-bottom:10px;">
                🟢 отлично | 🟠 норма | 🔴 требует внимания &nbsp;&nbsp;|&nbsp;&nbsp; ↑ улучшение | ↓ ухудшение | → стабильно
            </div>
        """, unsafe_allow_html=True)

        # Информация о пагинации
        st.markdown(f"""
            <div style="text-align:center; color:{COLORS['text']}; font-size:12px; margin-bottom:10px;">
                Показано {start_idx + 1}–{end_idx} из {total_machines} машин (стр. {current_page}/{total_pages})
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr style='margin: 5px 0; border-color: #334155'>", unsafe_allow_html=True)

        # Строки машин (только для текущей страницы)
        for machine in machines_to_show:
            machine_data = df_last5[df_last5['№ ПМ'] == machine].sort_values('№ партии')
            parties = machine_data['№ партии'].values

            with st.expander(f"№ {int(machine)}", expanded=False):
                # Развёрнутый вид с графиками за 5 партий
                st.markdown(f"<h4 style='color:{COLORS['text']}'>Машина № {int(machine)} — последние 5 партий</h4>", unsafe_allow_html=True)

                detail_cols = st.columns(2)
                party_labels = [int(p) - 714 for p in parties]

                # Разрывная нагрузка - детально
                with detail_cols[0]:
                    strength_vals = machine_data['Относительная разрывная нагрузка, сН/текс'].values
                    if len(strength_vals) > 0:
                        fig = go.Figure()
                        colors = [COLORS['success'] if v >= 280 else COLORS['warning'] if v >= 270 else COLORS['danger'] for v in strength_vals]

                        fig.add_trace(go.Scatter(x=party_labels, y=strength_vals, mode='lines+markers+text',
                            line=dict(color=COLORS['text_secondary'], width=2),
                            marker=dict(size=12, color=colors),
                            text=[f"{v:.1f}" for v in strength_vals], textposition='top center',
                            textfont=dict(size=10, color=COLORS['text']), name='Значение'))
                        fig.add_hline(y=270, line=dict(color=COLORS['danger'], width=2, dash='dash'),
                            annotation_text="270 (мин)", annotation_position="right")
                        fig.add_hline(y=280, line=dict(color=COLORS['success'], width=2, dash='dash'),
                            annotation_text="280 (отл)", annotation_position="right")
                        fig.update_layout(title='Разрывная нагрузка, сН/текс', height=300,
                            xaxis=dict(title='Партия', tickfont=dict(color=COLORS['text_secondary'])),
                            yaxis=dict(range=[min(min(strength_vals)-10, 250), max(max(strength_vals)+15, 300)],
                                tickfont=dict(color=COLORS['text_secondary'])),
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color=COLORS['text']), showlegend=False, margin=dict(t=40,b=40,l=40,r=60))
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                # Коэф. вариации - детально
                with detail_cols[1]:
                    cv_vals = machine_data['Коэффициент вариации, %'].values
                    if len(cv_vals) > 0:
                        fig = go.Figure()
                        colors = [COLORS['success'] if v < 6.5 else COLORS['warning'] if v <= 9 else COLORS['danger'] for v in cv_vals]

                        fig.add_trace(go.Scatter(x=party_labels, y=cv_vals, mode='lines+markers+text',
                            line=dict(color=COLORS['text_secondary'], width=2),
                            marker=dict(size=12, color=colors),
                            text=[f"{v:.1f}" for v in cv_vals], textposition='top center',
                            textfont=dict(size=10, color=COLORS['text']), name='Значение'))
                        fig.add_hline(y=6.5, line=dict(color=COLORS['success'], width=2, dash='dash'),
                            annotation_text="6.5 (отл)", annotation_position="right")
                        fig.add_hline(y=9, line=dict(color=COLORS['danger'], width=2, dash='dash'),
                            annotation_text="9 (макс)", annotation_position="right")
                        fig.update_layout(title='Коэф. вариации, %', height=300,
                            xaxis=dict(title='Партия', tickfont=dict(color=COLORS['text_secondary'])),
                            yaxis=dict(range=[0, max(max(cv_vals)+3, 12)], tickfont=dict(color=COLORS['text_secondary'])),
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color=COLORS['text']), showlegend=False, margin=dict(t=40,b=40,l=40,r=60))
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            # Компактная строка с индикаторами
            cols = st.columns([1, 3, 3])
            with cols[0]:
                pass  # Номер уже в expander
            with cols[1]:
                strength_vals = machine_data['Относительная разрывная нагрузка, сН/текс'].values
                if len(strength_vals) > 0:
                    st.markdown(f"<div style='text-align:center; font-size:16px; padding:5px;'>{create_mini_indicator(strength_vals, 'strength')}</div>", unsafe_allow_html=True)
            with cols[2]:
                cv_vals = machine_data['Коэффициент вариации, %'].values
                if len(cv_vals) > 0:
                    st.markdown(f"<div style='text-align:center; font-size:16px; padding:5px;'>{create_mini_indicator(cv_vals, 'cv')}</div>", unsafe_allow_html=True)

        # Кнопки пагинации
        st.markdown("<br>", unsafe_allow_html=True)

        if total_pages > 1:
            col_prev, col_info, col_next = st.columns([1, 2, 1])

            with col_prev:
                if current_page > 1:
                    if st.button("◀ Предыдущие 10", key="prev_machines"):
                        st.session_state.machines_page -= 1
                        st.rerun()

            with col_info:
                st.markdown(f"""
                    <div style="text-align:center; color:{COLORS['text']}; padding-top:8px;">
                        Страница {current_page} из {total_pages}
                    </div>
                """, unsafe_allow_html=True)

            with col_next:
                if current_page < total_pages:
                    if st.button("Следующие 10 ▶", key="next_machines"):
                        st.session_state.machines_page += 1
                        st.rerun()

        # Футер
        st.markdown(f"""
            <div style="text-align: center; margin-top: 40px; padding: 20px; color: {COLORS['text_secondary']};">
                <small>Дашборд прядильного цеха • Данные обновляются из Google Sheets</small>
            </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"❌ Ошибка при обработке данных: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
