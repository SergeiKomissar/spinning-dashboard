import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys
import os

# Конфигурация страницы - должна быть первой командой Streamlit
st.set_page_config(
    page_title="Дашборд | Нить 50 кр/м",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.charts import create_trend_chart, create_problem_machines_chart, create_quality_scatter
from components.metrics import calculate_party_metrics
from components.layout import render_page_header, render_metrics_section, render_top_bar, render_sidebar_nav, get_session_df
from utils.constants import QUALITY_THRESHOLDS_50 as QUALITY_THRESHOLDS, COLORS, TWIST50_PARTY_OFFSET
from utils.auth import login_form


def main():
    # Проверка авторизации
    if not login_form():
        return

    render_page_header(subtitle='Нить с круткой 50 кр/м')

    render_sidebar_nav()
    render_top_bar(refresh_key="refresh_button_50")





    df = get_session_df()

    if df is None:
        st.error("Не удалось загрузить данные. Проверьте подключение к Google Sheets.")
        return

    try:
        if df.empty:
            st.warning("Данные отсутствуют")
            return

        # Фильтрация по крутке 50
        if 'Крутка' in df.columns:
            df = df[df['Крутка'] == 50].copy()

        # Получаем данные последней партии
        last_party_series = df['№ партии'].dropna()
        if last_party_series.empty:
            st.warning("Нет данных о номерах партий")
            return

        twist50_offset = TWIST50_PARTY_OFFSET

        last_party = last_party_series.max()
        last_party_data = df[df['№ партии'] == last_party]

        # Заголовок партии (с offset для крутки 50)
        st.markdown(f'''
            <div class="party-header">
                <span>Текущая партия</span>
                <span class="party-badge">№ {int(last_party) - twist50_offset}</span>
            </div>
        ''', unsafe_allow_html=True)

        # Расчет метрик
        metrics = calculate_party_metrics(last_party_data, thresholds=QUALITY_THRESHOLDS)

        # Предыдущая партия для сравнения
        all_parties_sorted = sorted(df['№ партии'].dropna().unique())
        prev_metrics = None
        if len(all_parties_sorted) >= 2:
            prev_party = all_parties_sorted[-2]
            prev_party_data = df[df['№ партии'] == prev_party]
            prev_metrics = calculate_party_metrics(prev_party_data, thresholds=QUALITY_THRESHOLDS)

        # Секция метрик
        render_metrics_section(metrics, prev_metrics, strength_min=QUALITY_THRESHOLDS["strength_min"])

        # Alert banner если много отклонений
        total_issues = metrics['low_strength_count'] + metrics['high_cv_count'] + metrics['bad_density_count']
        if total_issues >= 5:
            st.markdown(f"""
                <div class="alert-banner">
                    Внимание: обнаружено {total_issues} отклонений в текущей партии
                    (прочность: {metrics['low_strength_count']}, CV: {metrics['high_cv_count']}, плотность: {metrics['bad_density_count']})
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        # === ПОКАЗАТЕЛИ КАЧЕСТВА - ПРОГРЕСС БАРЫ ===
        st.markdown(f'<div class="section-header">Показатели качества</div>', unsafe_allow_html=True)

        def progress_bar(label, value, min_val, max_val, threshold, mode='greater', good_count=None, total=None):
            pct = min(100, max(0, (value - min_val) / (max_val - min_val) * 100))
            if mode == 'greater':
                is_good = value >= threshold
            elif mode == 'less':
                is_good = value <= threshold
            else:
                is_good = threshold[0] <= value <= threshold[1]
            color = '#22c55e' if is_good else '#ef4444'
            count_text = f"<span style='color:#94a3b8;font-size:12px;'>{good_count}/{total} в норме</span>" if good_count is not None else ""
            return f"""
            <div style="background:#1e293b;padding:16px;border-radius:8px;border:1px solid #334155;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="color:#e2e8f0;font-size:14px;font-weight:600;">{label}</span>
                    <span style="color:{color};font-size:20px;font-weight:700;">{value}</span>
                </div>
                <div style="background:#334155;border-radius:4px;height:8px;overflow:hidden;">
                    <div style="background:{color};height:100%;width:{pct}%;border-radius:4px;transition:width 0.5s;"></div>
                </div>
                <div style="margin-top:4px;text-align:right;">{count_text}</div>
            </div>
            """

        bar_cols = st.columns(3)
        with bar_cols[0]:
            good_s = metrics['total_machines'] - metrics['low_strength_count']
            st.markdown(progress_bar("Разрывная нагрузка, сН/текс", metrics['avg_strength'], 200, 350, 260, 'greater', good_s, metrics['total_machines']), unsafe_allow_html=True)
        with bar_cols[1]:
            good_c = metrics['total_machines'] - metrics['high_cv_count']
            st.markdown(progress_bar("Коэф. вариации, %", metrics['avg_cv'], 0, 15, 9.0, 'less', good_c, metrics['total_machines']), unsafe_allow_html=True)
        with bar_cols[2]:
            good_d = metrics['total_machines'] - metrics['bad_density_count']
            density_val = metrics['avg_density'] if metrics['avg_density'] > 0 else 28.9
            st.markdown(progress_bar("Лин. плотность, текс", density_val, 27, 31, (28.3, 29.5), 'range', good_d, metrics['total_machines']), unsafe_allow_html=True)

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        # === ГРАФИК ТРЕНДА ===
        st.markdown(f"""
            <div class="section-header">Динамика по партиям</div>
        """, unsafe_allow_html=True)

        last_10_parties = (
            df.groupby('№ партии')
            .agg({'Относительная разрывная нагрузка, сН/текс': 'mean'})
            .round(1)
            .tail(10)
        )

        # Ищем колонку скорости для графика
        trend_speed_col = None
        for col in df.columns:
            if 'Скорость' in col and 'формования' in col:
                trend_speed_col = col
                break

        trend_fig = create_trend_chart(last_10_parties, df=df, speed_col=trend_speed_col, strength_min=QUALITY_THRESHOLDS["strength_min"], party_offset=twist50_offset)
        st.plotly_chart(trend_fig, width='stretch', config={'displayModeBar': False}, key='twist50_trend')

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        # === АНАЛИТИКА КАЧЕСТВА ===
        st.markdown(f"""
            <div class="section-header">Аналитика качества</div>
        """, unsafe_allow_html=True)

        # --- ГРАФИК 1: Проблемные машины ---
        st.markdown(f"""
            <div class="info-block">
                <h4>Топ проблемных машин</h4>
                <p>Машины с наибольшим количеством отклонений за последние 10 партий.
                Красный — критично (4+), оранжевый — требует внимания.</p>
            </div>
        """, unsafe_allow_html=True)

        problem_chart = create_problem_machines_chart(df, last_n_parties=10, strength_min=QUALITY_THRESHOLDS['strength_min'])
        st.plotly_chart(problem_chart, width='stretch', config={'displayModeBar': False}, key='twist50_problem')

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        # --- ГРАФИК 2: Карта качества ---
        st.markdown(f"""
            <div class="info-block">
                <h4>Карта качества партии</h4>
                <p>Каждая точка — машина. По X — разрывная нагрузка (↑ лучше),
                по Y — коэф. вариации (↓ лучше). Зелёная зона — норма.</p>
            </div>
        """, unsafe_allow_html=True)

        # Выбор партии
        all_parties = sorted(df['№ партии'].dropna().unique(), reverse=True)
        display_parties = [f"Партия {int(p) - twist50_offset}" for p in all_parties[:20]]

        selected_idx = st.selectbox(
            "Выберите партию для анализа:",
            range(len(display_parties)),
            format_func=lambda x: display_parties[x],
            key="party_selector_50"
        )
        selected_party = all_parties[selected_idx]

        scatter_chart = create_quality_scatter(df, selected_party, strength_min=QUALITY_THRESHOLDS["strength_min"], party_offset=twist50_offset)
        st.plotly_chart(scatter_chart, width='stretch', config={'displayModeBar': False}, key='twist50_scatter')


        # === РЕЗУЛЬТАТЫ ПО МАШИНАМ ===
        st.markdown(f"""
            <div class="section-header">Результаты по машинам</div>
            <p style="color: {COLORS['text_secondary']}; margin-bottom: 16px; font-size: 13px;">
                Последние 5 значений по каждой машине. Сверху — машины с отклонениями от нормы.
            </p>
        """, unsafe_allow_html=True)

        # Функции для цветовой раскраски
        def get_strength_color(val):
            if val < 260:
                return '#ef4444'  # красный — ниже нормы
            elif val < 265:
                return '#f97316'  # оранжевый — пограничная зона
            else:
                return '#22c55e'  # зелёный — в норме

        def get_cv_color(val):
            if val < 7:
                return '#22c55e'  # зелёный
            elif val < 9:
                return '#f97316'  # оранжевый
            else:
                return '#ef4444'  # красный

        strength_col = 'Относительная разрывная нагрузка, сН/текс'
        cv_col = 'Коэффициент вариации, %'

        # Данные за последние 10 партий (для детального просмотра)
        last_10_parties_list = sorted(df['№ партии'].dropna().unique())[-10:]
        df_last10 = df[df['№ партии'].isin(last_10_parties_list)]

        # Данные за последние 5 партий (для таблицы)
        last_5_parties_list = sorted(df['№ партии'].dropna().unique())[-5:]
        df_last5 = df[df['№ партии'].isin(last_5_parties_list)]

        # Сводка по машинам: последние 5 значений и число выходов за норму
        machine_rows = []
        for machine in sorted(df_last10['№ ПМ'].dropna().unique()):
            m5 = df_last5[df_last5['№ ПМ'] == machine].sort_values('№ партии')
            s_vals = m5[strength_col].values[-5:]
            c_vals = m5[cv_col].values[-5:]
            issues = int((s_vals < QUALITY_THRESHOLDS['strength_min']).sum() + (c_vals > QUALITY_THRESHOLDS['cv_max']).sum())
            mean_s = float(np.mean(s_vals)) if len(s_vals) else float('inf')
            machine_rows.append((machine, s_vals, c_vals, issues, mean_s))
        # Сначала машины с отклонениями, внутри — по возрастанию средней прочности
        machine_rows.sort(key=lambda r: (-r[3], r[4], r[0]))

        def colored(vals, color_fn, fmt):
            return ''.join(
                f"<span style='color:{color_fn(v)}; font-weight:bold; font-size:14px; margin:0 4px;'>{v:{fmt}}</span>"
                for v in vals)

        rows_html = []
        for machine, s_vals, c_vals, issues, _ in machine_rows:
            badge = (f"<span style='color:#ef4444; font-size:12px;'>{issues} вне нормы</span>" if issues
                     else "<span style='color:#64748b; font-size:12px;'>норма</span>")
            rows_html.append(
                f"<tr><td style='font-weight:600;'>ПМ {int(machine)}</td><td>{badge}</td>"
                f"<td>{colored(s_vals, get_strength_color, '.0f')}</td>"
                f"<td>{colored(c_vals, get_cv_color, '.1f')}</td></tr>")
        st.markdown(f"""
            <div style="max-height:520px; overflow-y:auto; border:1px solid #334155; border-radius:8px;">
            <table class="machines-table" style="width:100%; border-collapse:collapse; font-size:13px;">
                <thead><tr style="position:sticky; top:0; background:#1e293b;">
                    <th style="padding:10px; text-align:left;">Машина</th>
                    <th style="padding:10px; text-align:left;">Статус</th>
                    <th style="padding:10px; text-align:center;">Разрывная нагрузка (последние 5)</th>
                    <th style="padding:10px; text-align:center;">Коэф. вариации (последние 5)</th>
                </tr></thead>
                <tbody>{''.join(rows_html)}</tbody>
            </table></div>
            <style>
                .machines-table td {{ padding:6px 10px; border-top:1px solid #334155; }}
            </style>
        """, unsafe_allow_html=True)

        # Детальный просмотр — графики строятся только для выбранной машины
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        detail_options = [r[0] for r in machine_rows]
        machine = st.selectbox(
            "Детальный анализ машины (последние 10 партий):", detail_options,
            format_func=lambda m: f"ПМ {int(m)}", key="machine_detail_50"
        )
        machine_data_full = df_last10[df_last10['№ ПМ'] == machine].sort_values('№ партии')
        parties = machine_data_full['№ партии'].values
        party_labels = [int(p) - twist50_offset for p in parties]

        detail_cols = st.columns(2)

        # Разрывная нагрузка - детально
        with detail_cols[0]:
            strength_vals = machine_data_full[strength_col].values
            if len(strength_vals) > 0:
                mean_s = np.mean(strength_vals)
                fig = go.Figure()
                colors = [get_strength_color(v) for v in strength_vals]

                fig.add_trace(go.Scatter(x=party_labels, y=strength_vals, mode='lines+markers+text',
                    line=dict(color=COLORS['text_secondary'], width=2),
                    marker=dict(size=10, color=colors),
                    text=[f"{v:.1f}" for v in strength_vals], textposition='top center',
                    textfont=dict(size=10, color=COLORS['text']), name='Значение'))
                fig.add_hline(y=260, line=dict(color=COLORS['danger'], width=2, dash='dash'),
                    annotation_text="Мин: 260", annotation_position="right")
                fig.add_hline(y=mean_s, line=dict(color=COLORS['success'], width=2),
                    annotation_text=f"Ср: {mean_s:.1f}", annotation_position="right")
                fig.update_layout(title=f'ПМ {int(machine)}: разрывная нагрузка, сН/текс', height=300,
                    xaxis=dict(title='Партия', tickfont=dict(color=COLORS['text_secondary'])),
                    yaxis=dict(range=[min(min(strength_vals)-10, 230), max(max(strength_vals)+15, 280)],
                        tickfont=dict(color=COLORS['text_secondary'])),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['text']), showlegend=False, margin=dict(t=40,b=40,l=40,r=60))
                st.plotly_chart(fig, width='stretch', config={'displayModeBar': False}, key="twist50_strength_detail")

        # Коэф. вариации - детально
        with detail_cols[1]:
            cv_vals = machine_data_full[cv_col].values
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
                fig.update_layout(title=f'ПМ {int(machine)}: коэф. вариации, %', height=300,
                    xaxis=dict(title='Партия', tickfont=dict(color=COLORS['text_secondary'])),
                    yaxis=dict(range=[0, max(max(cv_vals)+3, 12)], tickfont=dict(color=COLORS['text_secondary'])),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['text']), showlegend=False, margin=dict(t=40,b=40,l=40,r=60))
                st.plotly_chart(fig, width='stretch', config={'displayModeBar': False}, key="twist50_cv_detail")

        # Футер
        st.markdown(f"""
            <div style="text-align: center; margin-top: 40px; padding: 20px; color: {COLORS['text_secondary']};">
                <small>Дашборд прядильного цеха. Данные обновляются из Google Sheets</small>
            </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Ошибка при обработке данных: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
