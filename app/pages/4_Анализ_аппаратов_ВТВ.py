import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import sys
import os
from datetime import datetime

# Конфигурация страницы - должна быть первой командой Streamlit
st.set_page_config(
    page_title="Аппараты ВТВ | Нить 50 кр/м",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.layout import inject_custom_css
from utils.data_processing import load_data
from utils.constants import QUALITY_THRESHOLDS_50 as QUALITY_THRESHOLDS, COLORS
from utils.auth import login_form, logout_button

STRENGTH_COL = 'Относительная разрывная нагрузка, сН/текс'
CV_COL = 'Коэффициент вариации, %'

# Пороги отклонения аппарата от среднего партии, сН/текс
DEV_WARN = -1.0    # жёлтая зона
DEV_ALERT = -2.0   # красная зона / алерт


def vtv_color(dev):
    if dev <= DEV_ALERT:
        return COLORS['danger']
    elif dev <= DEV_WARN:
        return COLORS['warning']
    return COLORS['success']


def main():
    # Проверка авторизации
    if not login_form():
        return

    inject_custom_css()

    st.markdown(
        '<div class="dashboard-header">Анализ аппаратов ВТВ — 50 кр/м</div>',
        unsafe_allow_html=True
    )

    # Компактная шапка: имя + timestamp + обновить + выход
    header_cols = st.columns([3, 2, 1, 1])
    with header_cols[0]:
        st.markdown(f"<span style='color:#94a3b8;font-size:13px;'>Пользователь: <b>{st.session_state.user_info['name']}</b></span>", unsafe_allow_html=True)
    with header_cols[1]:
        st.markdown(f"<span style='color:#64748b;font-size:12px;'>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</span>", unsafe_allow_html=True)
    with header_cols[2]:
        if st.button('Обновить', key="vtv_refresh_50"):
            load_data.clear()
            st.rerun()
    with header_cols[3]:
        logout_button()

    # --- Кастомная навигация с русскими названиями ---
    st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)
    st.sidebar.markdown("### Дашборды")
    st.sidebar.page_link("dashboard.py", label="Нить с круткой 100 кр/м", icon="🏭")
    st.sidebar.page_link("pages/1_Дашборд_нити_с_круткой_50_крм.py", label="Нить с круткой 50 кр/м", icon="🧵")
    st.sidebar.markdown("### Контрольные карты")
    st.sidebar.page_link("pages/2_Контрольные_карты_100_крм.py", label="Контрольные карты 100 кр/м", icon="📊")
    st.sidebar.page_link("pages/3_Контрольные_карты_50_крм.py", label="Контрольные карты 50 кр/м", icon="📈")
    st.sidebar.markdown("### Термообработка")
    st.sidebar.page_link("pages/4_Анализ_аппаратов_ВТВ.py", label="Анализ аппаратов ВТВ", icon="🔥")
    st.sidebar.markdown("### Администратор")
    st.sidebar.page_link("pages/5_Статистика_для_администратора.py", label="Статистика посещений", icon="👤")

    # Загружаем данные
    with st.spinner('Загрузка данных...'):
        if 'df' not in st.session_state:
            st.session_state.df = load_data()
        df = st.session_state.df.copy() if st.session_state.df is not None else None

    if df is None or df.empty:
        st.error("Не удалось загрузить данные. Проверьте подключение к Google Sheets.")
        return

    # Фильтрация по крутке 50
    if 'Крутка' in df.columns:
        df = df[df['Крутка'] == 50].copy()

    if '№ ВТВ' not in df.columns:
        st.warning("В таблице нет колонки '№ ВТВ'")
        return

    # Валидация номера аппарата: допустимы 1-19
    df['ВТВ'] = pd.to_numeric(df['№ ВТВ'], errors='coerce')
    df = df[df['ВТВ'].between(1, 19)].copy()
    df['ВТВ'] = df['ВТВ'].astype(int)

    if df.empty:
        st.warning("Нет данных с заполненным номером аппарата ВТВ")
        return

    # Offset для крутки 50: последняя партия на 10.04.2026 = №64
    twist50_offset = 845

    # Отклонение от среднего партии — убирает эффект полимера,
    # остаётся вклад термообработки и машины
    df['Отклонение'] = df[STRENGTH_COL] - df.groupby('№ партии')[STRENGTH_COL].transform('mean')

    st.markdown(f"""
        <div class="info-block">
            <h4>Влияние термообработки на прочность</h4>
            <p>Полимер у всех машин в партии один, поэтому отклонение результата от среднего партии
            показывает вклад аппарата ВТВ и машины. Отклонение усредняется по всем машинам,
            прошедшим через аппарат, — эффект машин взаимно компенсируется, остаётся вклад термообработки.
            Норма — около нуля; устойчивый минус означает, что аппарат «съедает» прочность.</p>
        </div>
    """, unsafe_allow_html=True)

    # Выбор периода анализа
    settings_cols = st.columns([2, 2, 2])
    with settings_cols[0]:
        n_parties = st.selectbox(
            "Количество партий для анализа:",
            [10, 20, 30, 50, 100, "Все"], index=2, key="vtv_n_parties"
        )

    all_parties = sorted(df['№ партии'].dropna().unique())
    if n_parties == "Все":
        selected_parties = all_parties
    else:
        selected_parties = all_parties[-n_parties:] if len(all_parties) > n_parties else all_parties
    df_f = df[df['№ партии'].isin(selected_parties)]

    MIN_N = 20  # минимум измерений для надёжной оценки аппарата

    # Статистика по аппаратам
    vtv_stats = df_f.groupby('ВТВ').agg(
        n=('Отклонение', 'count'),
        mean_dev=('Отклонение', 'mean'),
        fail_pct=(STRENGTH_COL, lambda x: (x < QUALITY_THRESHOLDS['strength_min']).mean() * 100),
        mean_strength=(STRENGTH_COL, 'mean'),
    ).reset_index()
    vtv_ok = vtv_stats[vtv_stats['n'] >= MIN_N].sort_values('mean_dev')

    if vtv_ok.empty:
        st.warning("Недостаточно данных по аппаратам за выбранный период")
        return

    # ============================================================
    # 1. АЛЕРТЫ
    # ============================================================
    ALERT_PARTIES = 5
    recent_parties = all_parties[-ALERT_PARTIES:]
    df_recent = df[df['№ партии'].isin(recent_parties)]
    recent_stats = df_recent.groupby('ВТВ').agg(
        n=('Отклонение', 'count'),
        mean_dev=('Отклонение', 'mean'),
    ).reset_index()
    alert_vtv = recent_stats[(recent_stats['mean_dev'] <= DEV_ALERT) & (recent_stats['n'] >= 10)]

    if not alert_vtv.empty:
        items = ", ".join(
            f"№{int(r['ВТВ'])} ({r['mean_dev']:+.1f} сН/текс)"
            for _, r in alert_vtv.sort_values('mean_dev').iterrows()
        )
        st.markdown(f"""
            <div class="alert-banner">
                Требуют настройки (устойчиво ниже среднего за последние {ALERT_PARTIES} партий): аппараты {items}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid {COLORS['success']};
                 border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;
                 color: {COLORS['success']}; font-size: 14px;">
                За последние {ALERT_PARTIES} партий аппаратов с критичным отклонением (≤ {DEV_ALERT} сН/текс) не выявлено
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ============================================================
    # 2. РЕЙТИНГ АППАРАТОВ
    # ============================================================
    st.markdown('<div class="section-header">Рейтинг аппаратов ВТВ</div>', unsafe_allow_html=True)

    rating_cols = st.columns(2)

    with rating_cols[0]:
        d = vtv_ok.sort_values('mean_dev')
        colors = [vtv_color(v) for v in d['mean_dev']]
        fig = go.Figure(go.Bar(
            x=[f"№{v}" for v in d['ВТВ']], y=d['mean_dev'],
            marker_color=colors,
            text=[f"{v:+.1f}" for v in d['mean_dev']], textposition='outside',
            textfont=dict(size=11, color=COLORS['text']),
            customdata=d['n'],
            hovertemplate="ВТВ %{x}<br>Отклонение: %{y:+.2f} сН/текс<br>Измерений: %{customdata}<extra></extra>",
        ))
        fig.add_hline(y=0, line=dict(color=COLORS['text_secondary'], width=1))
        fig.add_hline(y=DEV_ALERT, line=dict(color=COLORS['danger'], width=1.5, dash='dash'),
                      annotation_text=f"Критично: {DEV_ALERT}", annotation_position="bottom right",
                      annotation_font=dict(color=COLORS['danger'], size=11))
        fig.update_layout(
            title=dict(text='<b>Отклонение прочности от среднего партии</b>',
                       font=dict(size=15, color=COLORS['text']), x=0.5),
            height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            xaxis=dict(title='Аппарат ВТВ', tickfont=dict(color=COLORS['text_secondary']), showgrid=False),
            yaxis=dict(title='сН/текс', tickfont=dict(color=COLORS['text_secondary']),
                       gridcolor=COLORS['grid'], zeroline=False),
            showlegend=False, margin=dict(t=50, b=40, l=50, r=20),
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key='vtv_rating_dev')

    with rating_cols[1]:
        d = vtv_ok.sort_values('fail_pct', ascending=False)
        avg_fail = (df_f[STRENGTH_COL] < QUALITY_THRESHOLDS['strength_min']).mean() * 100
        colors = [COLORS['danger'] if v > avg_fail * 1.3 else COLORS['warning'] if v > avg_fail else COLORS['success'] for v in d['fail_pct']]
        fig = go.Figure(go.Bar(
            x=[f"№{v}" for v in d['ВТВ']], y=d['fail_pct'],
            marker_color=colors,
            text=[f"{v:.1f}%" for v in d['fail_pct']], textposition='outside',
            textfont=dict(size=11, color=COLORS['text']),
            customdata=d['n'],
            hovertemplate="ВТВ %{x}<br>Ниже нормы: %{y:.1f}%<br>Измерений: %{customdata}<extra></extra>",
        ))
        fig.add_hline(y=avg_fail, line=dict(color=COLORS['text_secondary'], width=1.5, dash='dot'),
                      annotation_text=f"Среднее: {avg_fail:.1f}%", annotation_position="top right",
                      annotation_font=dict(color=COLORS['text_secondary'], size=11))
        fig.update_layout(
            title=dict(text=f"<b>Доля результатов ниже {QUALITY_THRESHOLDS['strength_min']} сН/текс</b>",
                       font=dict(size=15, color=COLORS['text']), x=0.5),
            height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            xaxis=dict(title='Аппарат ВТВ', tickfont=dict(color=COLORS['text_secondary']), showgrid=False),
            yaxis=dict(title='% ниже нормы', tickfont=dict(color=COLORS['text_secondary']),
                       gridcolor=COLORS['grid'], rangemode='tozero'),
            showlegend=False, margin=dict(t=50, b=40, l=50, r=20),
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key='vtv_rating_fail')

    excluded = vtv_stats[vtv_stats['n'] < MIN_N]
    if not excluded.empty:
        ex_list = ", ".join(f"№{int(r['ВТВ'])} (n={int(r['n'])})" for _, r in excluded.iterrows())
        st.markdown(f"<span style='color:{COLORS['text_secondary']};font-size:12px;'>Не показаны из-за малого числа измерений (&lt;{MIN_N}): {ex_list}</span>", unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ============================================================
    # 3. ТРЕНД ПО АППАРАТУ
    # ============================================================
    st.markdown('<div class="section-header">Динамика аппарата по партиям</div>', unsafe_allow_html=True)

    st.markdown("""
        <div class="info-block">
            <h4>Раннее обнаружение разладки</h4>
            <p>Среднее отклонение прочности по партиям для выбранного аппарата.
            Устойчивый уход линии вниз — сигнал о деградации термообработки
            (проверить настройки температуры, времени, вакуума).</p>
        </div>
    """, unsafe_allow_html=True)

    trend_cols = st.columns([2, 2, 2])
    with trend_cols[0]:
        vtv_list = sorted(df_f['ВТВ'].unique())
        default_idx = 0
        worst = vtv_ok.iloc[0]['ВТВ'] if not vtv_ok.empty else vtv_list[0]
        if worst in vtv_list:
            default_idx = vtv_list.index(worst)
        selected_vtv = st.selectbox(
            "Аппарат ВТВ:", vtv_list,
            index=default_idx,
            format_func=lambda x: f"ВТВ №{int(x)}", key="vtv_trend_select"
        )

    vtv_df = df_f[df_f['ВТВ'] == selected_vtv]
    by_party = vtv_df.groupby('№ партии').agg(
        dev=('Отклонение', 'mean'),
        n=('Отклонение', 'count'),
    ).reset_index().sort_values('№ партии')

    if len(by_party) >= 2:
        x_labels = [int(p) - twist50_offset for p in by_party['№ партии']]
        rolling = by_party['dev'].rolling(3, min_periods=1).mean()

        fig = go.Figure()
        point_colors = [vtv_color(v) for v in by_party['dev']]
        fig.add_trace(go.Scatter(
            x=x_labels, y=by_party['dev'], mode='lines+markers',
            line=dict(color=COLORS['grid'], width=1.5),
            marker=dict(size=9, color=point_colors),
            customdata=by_party['n'],
            name='Отклонение',
            hovertemplate="Партия %{x}<br>Отклонение: %{y:+.2f} сН/текс<br>Бобин: %{customdata}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=x_labels, y=rolling, mode='lines',
            line=dict(color=COLORS['primary'], width=3),
            name='Скользящее среднее (3 партии)',
            hovertemplate="Партия %{x}<br>Ср. за 3 партии: %{y:+.2f}<extra></extra>",
        ))
        fig.add_hline(y=0, line=dict(color=COLORS['text_secondary'], width=1))
        fig.add_hline(y=DEV_ALERT, line=dict(color=COLORS['danger'], width=1.5, dash='dash'),
                      annotation_text=f"Критично: {DEV_ALERT}", annotation_position="bottom right",
                      annotation_font=dict(color=COLORS['danger'], size=11))
        fig.update_layout(
            title=dict(text=f'<b>ВТВ №{int(selected_vtv)}: отклонение прочности по партиям</b>',
                       font=dict(size=15, color=COLORS['text']), x=0.5),
            height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            xaxis=dict(title='Партия', tickfont=dict(color=COLORS['text_secondary']), gridcolor=COLORS['grid']),
            yaxis=dict(title='Отклонение, сН/текс', tickfont=dict(color=COLORS['text_secondary']),
                       gridcolor=COLORS['grid'], zeroline=False),
            legend=dict(orientation='h', y=1.08, x=0, font=dict(color=COLORS['text_secondary'], size=11)),
            margin=dict(t=70, b=40, l=50, r=20),
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key='vtv_trend_chart')
    else:
        st.warning(f"Недостаточно партий для ВТВ №{int(selected_vtv)} за выбранный период")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ============================================================
    # 4. ТЕПЛОВАЯ КАРТА ПМ x ВТВ
    # ============================================================
    st.markdown('<div class="section-header">Машина × Аппарат</div>', unsafe_allow_html=True)

    st.markdown("""
        <div class="info-block">
            <h4>Поиск неудачных комбинаций</h4>
            <p>Средняя прочность по комбинациям «прядильная машина × аппарат ВТВ».
            Если строка машины зелёная везде, кроме одного столбца, — причина в аппарате, а не в машине.
            Красный столбец сверху донизу — аппарат портит результат любой машины.</p>
        </div>
    """, unsafe_allow_html=True)

    pm_col = '№ ПМ'
    pivot = df_f.pivot_table(index=pm_col, columns='ВТВ', values=STRENGTH_COL, aggfunc='mean')
    counts = df_f.pivot_table(index=pm_col, columns='ВТВ', values=STRENGTH_COL, aggfunc='count')
    # Скрываем ячейки с 1 измерением — ненадёжно
    pivot = pivot.where(counts >= 2)

    if not pivot.empty:
        z = pivot.values
        thr = QUALITY_THRESHOLDS['strength_min']
        fig = go.Figure(go.Heatmap(
            z=z,
            x=[f"№{int(c)}" for c in pivot.columns],
            y=[f"ПМ {int(i)}" for i in pivot.index],
            colorscale=[
                [0.0, '#7f1d1d'], [0.35, COLORS['danger']],
                [0.5, COLORS['warning']], [0.65, COLORS['success']],
                [1.0, '#065f46'],
            ],
            zmin=thr - 8, zmax=thr + 18,
            colorbar=dict(title=dict(text='сН/текс', font=dict(color=COLORS['text_secondary'])),
                          tickfont=dict(color=COLORS['text_secondary'])),
            hovertemplate="%{y} × ВТВ %{x}<br>Средняя прочность: %{z:.1f} сН/текс<extra></extra>",
            hoverongaps=False,
        ))
        fig.update_layout(
            height=max(500, 18 * len(pivot.index)),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            xaxis=dict(title='Аппарат ВТВ', tickfont=dict(color=COLORS['text_secondary'], size=11), side='top'),
            yaxis=dict(title='', tickfont=dict(color=COLORS['text_secondary'], size=10), autorange='reversed'),
            margin=dict(t=60, b=20, l=60, r=20),
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key='vtv_heatmap')
        st.markdown(f"<span style='color:{COLORS['text_secondary']};font-size:12px;'>Пустые ячейки — комбинация не встречалась или меньше 2 измерений.</span>", unsafe_allow_html=True)
    else:
        st.warning("Недостаточно данных для тепловой карты")

    st.markdown(f"""
        <div style="text-align: center; margin-top: 40px; padding: 20px; color: {COLORS['text_secondary']};">
            <small>Анализ аппаратов ВТВ | Нить 50 кр/м | Данные из Google Sheets</small>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
