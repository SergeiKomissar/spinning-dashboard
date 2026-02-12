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
from components.charts import create_gauge_chart, create_trend_chart, create_heatmap, create_problem_machines_chart, create_quality_scatter, create_sparkline
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

        # --- ТАБЛИЦА: Сравнение пластификационной вытяжки ---
        st.markdown(f"""
            <div class="info-block">
                <h4>🔬 Сравнение: вытяжка 60% vs 65%</h4>
                <p>Средние показатели прочности и CV для машин с разной пластификационной вытяжкой.</p>
            </div>
        """, unsafe_allow_html=True)
        
        stretch_col = 'Пласт. вытяжка, %'
        
        if stretch_col in df.columns:
            # Функция для расчёта статистики
            def calc_stats(data, stretch_val):
                filtered = data[pd.to_numeric(data[stretch_col], errors='coerce') == stretch_val]
                if len(filtered) == 0:
                    return {'strength': '-', 'cv': '-', 'count': 0}
                return {
                    'strength': f"{filtered['Относительная разрывная нагрузка, сН/текс'].mean():.1f}",
                    'cv': f"{filtered['Коэффициент вариации, %'].mean():.1f}",
                    'count': len(filtered)
                }
            
            # Получаем партии
            all_parties = sorted(df['№ партии'].dropna().unique())
            last_1 = df[df['№ партии'] == all_parties[-1]] if len(all_parties) >= 1 else pd.DataFrame()
            last_3 = df[df['№ партии'].isin(all_parties[-3:])] if len(all_parties) >= 3 else pd.DataFrame()
            last_10 = df[df['№ партии'].isin(all_parties[-10:])] if len(all_parties) >= 10 else pd.DataFrame()
            
            # Считаем количество машин на каждой вытяжке (в последней партии)
            last_party_plast = df[df['№ партии'] == all_parties[-1]]
            machines_60 = len(last_party_plast[pd.to_numeric(last_party_plast[stretch_col], errors='coerce') == 60]['№ ПМ'].unique())
            machines_65 = len(last_party_plast[pd.to_numeric(last_party_plast[stretch_col], errors='coerce') == 65]['№ ПМ'].unique())
            
            # Статистика
            stats_1_60 = calc_stats(last_1, 60)
            stats_1_65 = calc_stats(last_1, 65)
            stats_3_60 = calc_stats(last_3, 60)
            stats_3_65 = calc_stats(last_3, 65)
            stats_10_60 = calc_stats(last_10, 60)
            stats_10_65 = calc_stats(last_10, 65)
            
            # Функция для цвета разницы
            def diff_color(val60, val65, metric='strength'):
                try:
                    v60 = float(val60)
                    v65 = float(val65)
                    diff = v65 - v60
                    if metric == 'strength':
                        color = '#22c55e' if diff > 0 else '#ef4444' if diff < 0 else '#94a3b8'
                    else:  # CV - меньше лучше
                        color = '#22c55e' if diff < 0 else '#ef4444' if diff > 0 else '#94a3b8'
                    sign = '+' if diff > 0 else ''
                    return f"<span style='color:{color};font-weight:bold'>{sign}{diff:.1f}</span>"
                except:
                    return '-'
            
            # HTML таблица
            table_html = f"""
            <style>
                .compare-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                .compare-table th, .compare-table td {{ padding: 12px 8px; text-align: center; border-bottom: 1px solid #334155; }}
                .compare-table th {{ background: #1e293b; color: #e2e8f0; font-weight: bold; }}
                .compare-table td {{ color: #cbd5e1; }}
                .compare-table tr:hover {{ background: #1e293b; }}
                .val-60 {{ color: #00d4ff !important; font-weight: bold; }}
                .val-65 {{ color: #8b5cf6 !important; font-weight: bold; }}
                .header-row {{ background: #0f172a !important; }}
            </style>
            <table class="compare-table">
                <tr class="header-row">
                    <th rowspan="2">Период</th>
                    <th colspan="3">Разрывная нагрузка, сН/текс</th>
                    <th colspan="3">Коэф. вариации, %</th>
                </tr>
                <tr class="header-row">
                    <th><span class="val-60">60%</span></th>
                    <th><span class="val-65">65%</span></th>
                    <th>Δ</th>
                    <th><span class="val-60">60%</span></th>
                    <th><span class="val-65">65%</span></th>
                    <th>Δ</th>
                </tr>
                <tr style="background:#1e293b;">
                    <td colspan="7" style="text-align:left;padding:8px 12px;">
                        <b>Машин на вытяжке:</b> 
                        <span class="val-60">60% — {machines_60} шт.</span> | 
                        <span class="val-65">65% — {machines_65} шт.</span>
                    </td>
                </tr>
                <tr>
                    <td><b>Последняя партия</b><br><small>(n: {stats_1_60['count']} / {stats_1_65['count']})</small></td>
                    <td class="val-60">{stats_1_60['strength']}</td>
                    <td class="val-65">{stats_1_65['strength']}</td>
                    <td>{diff_color(stats_1_60['strength'], stats_1_65['strength'], 'strength')}</td>
                    <td class="val-60">{stats_1_60['cv']}</td>
                    <td class="val-65">{stats_1_65['cv']}</td>
                    <td>{diff_color(stats_1_60['cv'], stats_1_65['cv'], 'cv')}</td>
                </tr>
                <tr>
                    <td><b>3 последние партии</b><br><small>(n: {stats_3_60['count']} / {stats_3_65['count']})</small></td>
                    <td class="val-60">{stats_3_60['strength']}</td>
                    <td class="val-65">{stats_3_65['strength']}</td>
                    <td>{diff_color(stats_3_60['strength'], stats_3_65['strength'], 'strength')}</td>
                    <td class="val-60">{stats_3_60['cv']}</td>
                    <td class="val-65">{stats_3_65['cv']}</td>
                    <td>{diff_color(stats_3_60['cv'], stats_3_65['cv'], 'cv')}</td>
                </tr>
                <tr>
                    <td><b>10 последних партий</b><br><small>(n: {stats_10_60['count']} / {stats_10_65['count']})</small></td>
                    <td class="val-60">{stats_10_60['strength']}</td>
                    <td class="val-65">{stats_10_65['strength']}</td>
                    <td>{diff_color(stats_10_60['strength'], stats_10_65['strength'], 'strength')}</td>
                    <td class="val-60">{stats_10_60['cv']}</td>
                    <td class="val-65">{stats_10_65['cv']}</td>
                    <td>{diff_color(stats_10_60['cv'], stats_10_65['cv'], 'cv')}</td>
                </tr>
            </table>
            """
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.warning("Колонка 'Пласт. вытяжка, %' не найдена в данных")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- ТАБЛИЦА: Сравнение скорости формования ---
        st.markdown(f"""
            <div class="info-block">
                <h4>⚡ Сравнение: скорость 16.4 vs 18.8 м/мин</h4>
                <p>Средние показатели прочности и CV для машин с разной скоростью формования.</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Ищем колонку скорости динамически
        speed_col = None
        for col in df.columns:
            if 'Скорость' in col and 'формования' in col:
                speed_col = col
                break
        
        if speed_col is not None:
            # Функция для расчёта статистики по скорости
            def calc_speed_stats(data, speed_val):
                filtered = data[data[speed_col] == speed_val]
                if len(filtered) == 0:
                    return {'strength': '-', 'cv': '-', 'count': 0}
                return {
                    'strength': f"{filtered['Относительная разрывная нагрузка, сН/текс'].mean():.1f}",
                    'cv': f"{filtered['Коэффициент вариации, %'].mean():.1f}",
                    'count': len(filtered)
                }
            
            # Считаем количество машин на каждой скорости (в последней партии)
            last_party_speed = df[df['№ партии'] == all_parties[-1]]
            machines_164 = len(last_party_speed[last_party_speed[speed_col] == 164]['№ ПМ'].unique())
            machines_188 = len(last_party_speed[last_party_speed[speed_col] == 188]['№ ПМ'].unique())
            
            # Статистика по скоростям
            speed_stats_1_164 = calc_speed_stats(last_1, 16.4)
            speed_stats_1_188 = calc_speed_stats(last_1, 18.8)
            speed_stats_3_164 = calc_speed_stats(last_3, 16.4)
            speed_stats_3_188 = calc_speed_stats(last_3, 18.8)
            speed_stats_10_164 = calc_speed_stats(last_10, 16.4)
            speed_stats_10_188 = calc_speed_stats(last_10, 18.8)
            
            # Функция для цвета разницы (такая же)
            def speed_diff_color(val164, val188, metric='strength'):
                try:
                    v164 = float(val164)
                    v188 = float(val188)
                    diff = v188 - v164
                    if metric == 'strength':
                        color = '#22c55e' if diff > 0 else '#ef4444' if diff < 0 else '#94a3b8'
                    else:  # CV - меньше лучше
                        color = '#22c55e' if diff < 0 else '#ef4444' if diff > 0 else '#94a3b8'
                    sign = '+' if diff > 0 else ''
                    return f"<span style='color:{color};font-weight:bold'>{sign}{diff:.1f}</span>"
                except:
                    return '-'
            
            # HTML таблица для скорости
            speed_table_html = f"""
            <table class="compare-table">
                <tr class="header-row">
                    <th rowspan="2">Период</th>
                    <th colspan="3">Разрывная нагрузка, сН/текс</th>
                    <th colspan="3">Коэф. вариации, %</th>
                </tr>
                <tr class="header-row">
                    <th><span style="color:#f59e0b;font-weight:bold">16.4</span></th>
                    <th><span style="color:#06b6d4;font-weight:bold">18.8</span></th>
                    <th>Δ</th>
                    <th><span style="color:#f59e0b;font-weight:bold">16.4</span></th>
                    <th><span style="color:#06b6d4;font-weight:bold">18.8</span></th>
                    <th>Δ</th>
                </tr>
                <tr style="background:#1e293b;">
                    <td colspan="7" style="text-align:left;padding:8px 12px;">
                        <b>Машин на скорости:</b> 
                        <span style="color:#f59e0b;font-weight:bold">16.4 м/мин — {machines_164} шт.</span> | 
                        <span style="color:#06b6d4;font-weight:bold">18.8 м/мин — {machines_188} шт.</span>
                    </td>
                </tr>
                <tr>
                    <td><b>Последняя партия</b><br><small>(n: {speed_stats_1_164['count']} / {speed_stats_1_188['count']})</small></td>
                    <td style="color:#f59e0b;font-weight:bold">{speed_stats_1_164['strength']}</td>
                    <td style="color:#06b6d4;font-weight:bold">{speed_stats_1_188['strength']}</td>
                    <td>{speed_diff_color(speed_stats_1_164['strength'], speed_stats_1_188['strength'], 'strength')}</td>
                    <td style="color:#f59e0b;font-weight:bold">{speed_stats_1_164['cv']}</td>
                    <td style="color:#06b6d4;font-weight:bold">{speed_stats_1_188['cv']}</td>
                    <td>{speed_diff_color(speed_stats_1_164['cv'], speed_stats_1_188['cv'], 'cv')}</td>
                </tr>
                <tr>
                    <td><b>3 последние партии</b><br><small>(n: {speed_stats_3_164['count']} / {speed_stats_3_188['count']})</small></td>
                    <td style="color:#f59e0b;font-weight:bold">{speed_stats_3_164['strength']}</td>
                    <td style="color:#06b6d4;font-weight:bold">{speed_stats_3_188['strength']}</td>
                    <td>{speed_diff_color(speed_stats_3_164['strength'], speed_stats_3_188['strength'], 'strength')}</td>
                    <td style="color:#f59e0b;font-weight:bold">{speed_stats_3_164['cv']}</td>
                    <td style="color:#06b6d4;font-weight:bold">{speed_stats_3_188['cv']}</td>
                    <td>{speed_diff_color(speed_stats_3_164['cv'], speed_stats_3_188['cv'], 'cv')}</td>
                </tr>
                <tr>
                    <td><b>10 последних партий</b><br><small>(n: {speed_stats_10_164['count']} / {speed_stats_10_188['count']})</small></td>
                    <td style="color:#f59e0b;font-weight:bold">{speed_stats_10_164['strength']}</td>
                    <td style="color:#06b6d4;font-weight:bold">{speed_stats_10_188['strength']}</td>
                    <td>{speed_diff_color(speed_stats_10_164['strength'], speed_stats_10_188['strength'], 'strength')}</td>
                    <td style="color:#f59e0b;font-weight:bold">{speed_stats_10_164['cv']}</td>
                    <td style="color:#06b6d4;font-weight:bold">{speed_stats_10_188['cv']}</td>
                    <td>{speed_diff_color(speed_stats_10_164['cv'], speed_stats_10_188['cv'], 'cv')}</td>
                </tr>
            </table>
            """
            st.markdown(speed_table_html, unsafe_allow_html=True)
        else:
            st.warning("Колонка 'Скорость формования, м/мин' не найдена в данных")

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
