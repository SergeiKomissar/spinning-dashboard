import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys
import os

# Конфигурация страницы - должна быть первой командой Streamlit
st.set_page_config(
    page_title="Отчёт | Качество нити",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from components.charts import create_gauge_chart, create_trend_chart, create_heatmap, create_problem_machines_chart, create_quality_scatter, create_sparkline, create_plastification_comparison, create_cv_plastification_comparison
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
    
    # Ссылка на статистику для админа
    if is_admin():
        st.sidebar.markdown("### 📊 Навигация")
        st.sidebar.page_link("dashboard.py", label="📋 Отчёт", icon="📋")
        st.sidebar.markdown("### 🔧 Админ-панель")
        st.sidebar.page_link("pages/1_admin_stats.py", label="📈 Статистика посещений")

    
    # Загружаем данные
    with st.spinner('Загрузка данных...'):
        if 'df' not in st.session_state:
            st.session_state.df = load_data()
        df = st.session_state.df
    
    if df is None:
        st.error("❌ Не удалось загрузить данные. Проверьте подключение к Google Sheets.")
        return
    
    # Кнопка обновления данных
    col_refresh, col_space = st.columns([1, 5])
    with col_refresh:
        if st.button('🔄 Обновить данные', key="refresh_button"):
            with st.spinner('Обновление...'):
                load_data.clear()
                new_data = load_data()
                if new_data is not None:
                    st.session_state.df = new_data
                    st.success('✅ Данные обновлены!')
                    st.rerun()
                else:
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
        
        # --- ГРАФИК 2: Карта качества ---
        st.markdown(f"""
            <div class="info-block">
                <h4>🗺️ Карта качества партии</h4>
                <p>Каждая точка — машина. По X — разрывная нагрузка (↑ лучше), 
                по Y — коэф. вариации (↓ лучше). Зелёная зона — норма.</p>
            </div>
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

        # --- ГРАФИК 3: Сравнение пластификационной вытяжки ---
        st.markdown(f"""
            <div class="info-block">
                <h4>🔬 Влияние пластификационной вытяжки на прочность</h4>
                <p>Сравнение разрывной нагрузки между машинами с вытяжкой 60% и 65%.
                Box plot показывает медиану, квартили и выбросы.</p>
            </div>
        """, unsafe_allow_html=True)

        plastification_chart, plastification_stats = create_plastification_comparison(df, last_n_parties=10)
        st.plotly_chart(plastification_chart, use_container_width=True, config={'displayModeBar': False})

        st.markdown("<br>", unsafe_allow_html=True)

        # --- ГРАФИК 4: CV по пластификационной вытяжке ---
        st.markdown(f"""
            <div class="info-block">
                <h4>📊 Влияние пластификационной вытяжки на коэф. вариации</h4>
                <p>Сравнение CV между машинами с вытяжкой 60% и 65%.
                Чем ниже CV - тем стабильнее качество.</p>
            </div>
        """, unsafe_allow_html=True)

        cv_plastification_chart, cv_plastification_stats = create_cv_plastification_comparison(df, last_n_parties=10)
        st.plotly_chart(cv_plastification_chart, use_container_width=True, config={'displayModeBar': False})

        st.markdown("<br>", unsafe_allow_html=True)

        # === РЕЗУЛЬТАТЫ ПО МАШИНАМ ===
        st.markdown(f"""
            <div class="section-header">
                <span class="icon">🔧</span>Результаты по машинам
            </div>
            <p style="color: {COLORS['text_secondary']}; margin-bottom: 16px; font-size: 13px;">
                Последние 5 партий. Нажмите на машину для детального просмотра.
            </p>
        """, unsafe_allow_html=True)
        
        # Функции для цветовой раскраски
        def get_strength_color(val):
            if val < 260:
                return '#ef4444'  # красный
            elif val < 270:
                return '#f97316'  # оранжевый
            elif val < 280:
                return '#eab308'  # жёлтый
            else:
                return '#22c55e'  # зелёный
        
        def get_cv_color(val):
            if val < 6:
                return '#22c55e'  # зелёный
            elif val < 9:
                return '#f97316'  # оранжевый
            else:
                return '#ef4444'  # красный
        
        # Данные за последние 10 партий (для детального просмотра)
        last_10_parties_list = sorted(df['№ партии'].dropna().unique())[-10:]
        df_last10 = df[df['№ партии'].isin(last_10_parties_list)]
        
        # Данные за последние 5 партий (для превью)
        last_5_parties_list = sorted(df['№ партии'].dropna().unique())[-5:]
        df_last5 = df[df['№ партии'].isin(last_5_parties_list)]
        
        machines = sorted(df_last10['№ ПМ'].dropna().unique())
        
        # Заголовки (без линейной плотности)
        header_cols = st.columns([1, 3, 3])
        headers = ['Машина', '⚡ Разрывная нагрузка (последние 5)', '📊 Коэф. вариации (последние 5)']
        for col, header in zip(header_cols, headers):
            with col:
                st.markdown(f"<div style='text-align:center; font-weight:bold; color:{COLORS['text']}; font-size:13px;'>{header}</div>", unsafe_allow_html=True)
        
        st.markdown("<hr style='margin: 5px 0; border-color: #334155'>", unsafe_allow_html=True)
        
        # Строки машин
        for machine in machines:
            machine_data_full = df_last10[df_last10['№ ПМ'] == machine].sort_values('№ партии')
            machine_data_5 = df_last5[df_last5['№ ПМ'] == machine].sort_values('№ партии')
            parties = machine_data_full['№ партии'].values
            
            with st.expander(f"№ {int(machine)}", expanded=False):
                # Развёрнутый вид с графиками (только 2 колонки)
                st.markdown(f"<h4 style='color:{COLORS['text']}'>Машина № {int(machine)} — детальный анализ</h4>", unsafe_allow_html=True)
                
                detail_cols = st.columns(2)
                
                # Разрывная нагрузка - детально
                with detail_cols[0]:
                    strength_vals = machine_data_full['Относительная разрывная нагрузка, сН/текс'].values
                    if len(strength_vals) > 0:
                        mean_s = np.mean(strength_vals)
                        fig = go.Figure()
                        party_labels = [int(p) - 714 for p in parties]
                        colors = [get_strength_color(v) for v in strength_vals]
                        
                        fig.add_trace(go.Scatter(x=party_labels, y=strength_vals, mode='lines+markers+text',
                            line=dict(color=COLORS['text_secondary'], width=2),
                            marker=dict(size=10, color=colors),
                            text=[f"{v:.1f}" for v in strength_vals], textposition='top center',
                            textfont=dict(size=10, color=COLORS['text']), name='Значение'))
                        fig.add_hline(y=270, line=dict(color=COLORS['danger'], width=2, dash='dash'),
                            annotation_text="Мин: 270", annotation_position="right")
                        fig.add_hline(y=mean_s, line=dict(color=COLORS['success'], width=2),
                            annotation_text=f"Ср: {mean_s:.1f}", annotation_position="right")
                        fig.update_layout(title='Разрывная нагрузка, сН/текс', height=300,
                            xaxis=dict(title='Партия', tickfont=dict(color=COLORS['text_secondary'])),
                            yaxis=dict(range=[min(min(strength_vals)-10, 250), max(max(strength_vals)+15, 300)],
                                tickfont=dict(color=COLORS['text_secondary'])),
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color=COLORS['text']), showlegend=False, margin=dict(t=40,b=40,l=40,r=60))
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                # Коэф. вариации - детально
                with detail_cols[1]:
                    cv_vals = machine_data_full['Коэффициент вариации, %'].values
                    if len(cv_vals) > 0:
                        mean_c = np.mean(cv_vals)
                        fig = go.Figure()
                        colors = [get_cv_color(v) for v in cv_vals]
                        
                        fig.add_trace(go.Scatter(x=party_labels, y=cv_vals, mode='lines+markers+text',
                            line=dict(color=COLORS['text_secondary'], width=2),
                            marker=dict(size=10, color=colors),
                            text=[f"{v:.1f}" for v in cv_vals], textposition='top center',
                            textfont=dict(size=10, color=COLORS['text']), name='Значение'))
                        fig.add_hline(y=9, line=dict(color=COLORS['danger'], width=2, dash='dash'),
                            annotation_text="Макс: 9", annotation_position="right")
                        fig.add_hline(y=mean_c, line=dict(color=COLORS['success'], width=2),
                            annotation_text=f"Ср: {mean_c:.1f}", annotation_position="right")
                        fig.update_layout(title='Коэф. вариации, %', height=300,
                            xaxis=dict(title='Партия', tickfont=dict(color=COLORS['text_secondary'])),
                            yaxis=dict(range=[0, max(max(cv_vals)+3, 12)], tickfont=dict(color=COLORS['text_secondary'])),
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color=COLORS['text']), showlegend=False, margin=dict(t=40,b=40,l=40,r=60))
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # Компактная строка с цветными цифрами
            cols = st.columns([1, 3, 3])
            with cols[0]:
                pass  # Номер уже в expander
            
            # Разрывная нагрузка - цветные цифры
            with cols[1]:
                strength_vals = machine_data_5['Относительная разрывная нагрузка, сН/текс'].values[-5:]
                if len(strength_vals) > 0:
                    html_parts = []
                    for v in strength_vals:
                        color = get_strength_color(v)
                        html_parts.append(f"<span style='color:{color}; font-weight:bold; font-size:14px; margin:0 4px;'>{v:.0f}</span>")
                    st.markdown(f"<div style='text-align:center; padding:8px 0;'>{''.join(html_parts)}</div>", unsafe_allow_html=True)
            
            # Коэф. вариации - цветные цифры
            with cols[2]:
                cv_vals = machine_data_5['Коэффициент вариации, %'].values[-5:]
                if len(cv_vals) > 0:
                    html_parts = []
                    for v in cv_vals:
                        color = get_cv_color(v)
                        html_parts.append(f"<span style='color:{color}; font-weight:bold; font-size:14px; margin:0 4px;'>{v:.1f}</span>")
                    st.markdown(f"<div style='text-align:center; padding:8px 0;'>{''.join(html_parts)}</div>", unsafe_allow_html=True)
        
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
