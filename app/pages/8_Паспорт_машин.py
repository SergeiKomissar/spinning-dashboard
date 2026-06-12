import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os
from datetime import datetime

st.set_page_config(
    page_title="Паспорт машин | Нить 50 кр/м",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.layout import inject_custom_css
from utils.data_processing import load_data
from utils.constants import QUALITY_THRESHOLDS_50 as QUALITY_THRESHOLDS, COLORS
from utils.auth import login_form, logout_button
from utils import machine_health as mh


def main():
    if not login_form():
        return

    inject_custom_css()

    st.markdown(
        '<div class="dashboard-header">Паспорт машин — 50 кр/м</div>',
        unsafe_allow_html=True
    )

    header_cols = st.columns([3, 2, 1, 1])
    with header_cols[0]:
        st.markdown(f"<span style='color:#94a3b8;font-size:13px;'>Пользователь: <b>{st.session_state.user_info['name']}</b></span>", unsafe_allow_html=True)
    with header_cols[1]:
        st.markdown(f"<span style='color:#64748b;font-size:12px;'>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</span>", unsafe_allow_html=True)
    with header_cols[2]:
        if st.button('Обновить', key="mh_refresh"):
            load_data.clear()
            st.rerun()
    with header_cols[3]:
        logout_button()

    st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)
    st.sidebar.markdown("### Дашборд")
    st.sidebar.page_link("pages/1_Дашборд_нити_с_круткой_50_крм.py", label="Нить с круткой 50 кр/м", icon="🧵")
    st.sidebar.markdown("### Аналитика")
    st.sidebar.page_link("pages/6_Резюме_технолога.py", label="Резюме технолога", icon="🤖")
    st.sidebar.page_link("pages/8_Паспорт_машин.py", label="Паспорт машин", icon="🩺")
    st.sidebar.markdown("### Контрольные карты")
    st.sidebar.page_link("pages/3_Контрольные_карты_50_крм.py", label="Контрольные карты 50 кр/м", icon="📈")
    st.sidebar.markdown("### Термообработка")
    st.sidebar.page_link("pages/4_Анализ_аппаратов_ВТВ.py", label="Анализ аппаратов ВТВ", icon="🔥")
    st.sidebar.markdown("### Архив")
    st.sidebar.page_link("pages/7_Архив_Дашборд_100_крм.py", label="Дашборд нити 100 кр/м", icon="🗄️")
    st.sidebar.page_link("pages/2_Контрольные_карты_100_крм.py", label="Контрольные карты 100 кр/м", icon="🗄️")
    st.sidebar.markdown("### Администратор")
    st.sidebar.page_link("pages/5_Статистика_для_администратора.py", label="Статистика посещений", icon="👤")

    with st.spinner('Загрузка данных...'):
        if 'df' not in st.session_state:
            st.session_state.df = load_data()
        df = st.session_state.df.copy() if st.session_state.df is not None else None

    if df is None or df.empty:
        st.error("Не удалось загрузить данные.")
        return

    if 'Крутка' in df.columns:
        df = df[df['Крутка'] == 50].copy()
    if df['№ партии'].dropna().empty:
        st.warning("Нет данных по крутке 50")
        return

    twist50_offset = 845
    all_parties = sorted(df['№ партии'].dropna().unique())

    st.markdown(f"""
        <div class="info-block">
            <h4>Накопительная ведомость технического состояния машин</h4>
            <p>Прочность машины оценивается по <b>отклонению от среднего партии</b> — это убирает влияние
            полимера и показывает чистый вклад машины. Диагнозы:
            🔴 <b>обслуживание</b> — низкая прочность и высокий CV одновременно;
            🟠 <b>техсостояние</b> — устойчиво низкая прочность;
            🟡 <b>кручение/намотка</b> — только высокий CV (натяжение, бегунок, веретено);
            🔵 <b>деградация</b> — показатели в норме, но тренд устойчиво вниз;
            🟢 <b>норма</b>. Неактивные машины (нет в последних {mh.RECENT_ACTIVE} партиях) — внизу таблицы.</p>
        </div>
    """, unsafe_allow_html=True)

    sel_cols = st.columns([2, 2, 2])
    with sel_cols[0]:
        window_options = [10, 20, 40, 100]
        window_options = [w for w in window_options if w <= len(all_parties)] or [len(all_parties)]
        n_window = st.selectbox("Глубина анализа (партий):", window_options,
                                index=min(1, len(window_options) - 1), key="mh_window")

    reg = mh.compute_registry(df, n_window, QUALITY_THRESHOLDS)
    if reg.empty:
        st.warning("Недостаточно данных")
        return

    # ============================================================
    # 1. СВОДНАЯ ВЕДОМОСТЬ
    # ============================================================
    st.markdown('<div class="section-header">Сводная ведомость</div>', unsafe_allow_html=True)

    n_problem = int((reg['диагноз'] != 'норма').sum())
    n_active = int(reg['активна'].sum())
    st.markdown(
        f"<span style='color:{COLORS['text_secondary']};font-size:13px;'>"
        f"Машин в окне: {len(reg)} (активных {n_active}) | с диагнозом: {n_problem}</span>",
        unsafe_allow_html=True)

    disp = reg.copy()
    disp['Машина'] = disp.apply(
        lambda r: f"ПМ {r['машина']}" + ("" if r['активна'] else " (не в работе)"), axis=1)
    disp['Диагноз'] = disp['диагноз'].map(lambda d: f"{mh.DIAG_ICON[d]} {d}")
    disp['Тренд'] = disp['тренд'].map(
        lambda t: "—" if t is None or pd.isna(t) else (f"▼ {t:+.1f}" if t <= -mh.TREND_DELTA else (f"▲ {t:+.1f}" if t >= mh.TREND_DELTA else f"→ {t:+.1f}")))
    disp['Ниже 260'] = disp.apply(lambda r: f"{r['ниже_нормы_шт']} ({r['ниже_нормы_%']}%)", axis=1)
    disp['CV выше 10'] = disp.apply(lambda r: f"{r['cv_выше_нормы_шт']} ({r['cv_выше_нормы_%']}%)", axis=1)

    table = disp[['Машина', 'Диагноз', 'здоровье', 'партий', 'прочность_средняя',
                  'откл_от_партии', 'cv_средний', 'Ниже 260', 'CV выше 10', 'Тренд']].rename(columns={
        'здоровье': 'Здоровье',
        'партий': 'Партий',
        'прочность_средняя': 'Прочность ср.',
        'откл_от_партии': 'Откл. от партии',
        'cv_средний': 'CV ср.',
    })

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        height=min(38 * len(table) + 40, 700),
        column_config={
            'Здоровье': st.column_config.ProgressColumn(
                'Здоровье', min_value=0, max_value=100, format='%.0f'),
            'Откл. от партии': st.column_config.NumberColumn(format='%+.2f'),
        },
    )

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ============================================================
    # 2. ПАСПОРТ МАШИНЫ
    # ============================================================
    st.markdown('<div class="section-header">Паспорт машины</div>', unsafe_allow_html=True)

    pm_cols = st.columns([2, 2, 2])
    with pm_cols[0]:
        machines = reg['машина'].tolist()
        selected_pm = st.selectbox(
            "Машина:", machines,
            format_func=lambda m: f"ПМ {m}" + ("" if reg.loc[reg['машина'] == m, 'активна'].iloc[0] else " (не в работе)"),
            key="mh_pm")
    with pm_cols[1]:
        depth_options = [w for w in [10, 40, 100] if w <= len(all_parties)] + ['Все']
        depth = st.selectbox("Глубина истории:", depth_options,
                             index=len(depth_options) - 2 if len(depth_options) > 1 else 0, key="mh_depth")

    n_hist = len(all_parties) if depth == 'Все' else depth
    hist = mh.machine_history(df, selected_pm, n_hist)

    if len(hist) < 2:
        st.warning(f"Недостаточно истории для ПМ {selected_pm}")
        return

    row = reg[reg['машина'] == selected_pm].iloc[0]
    st.markdown(
        f"<span style='font-size:15px;color:{COLORS['text']};'>"
        f"{mh.DIAG_ICON[row['диагноз']]} <b>ПМ {selected_pm}</b> — диагноз: <b>{row['диагноз']}</b>, "
        f"здоровье {row['здоровье']:.0f}/100 (за {n_window} партий)</span>",
        unsafe_allow_html=True)

    x = [int(p) - twist50_offset for p in hist['№ партии']]

    chart_cols = st.columns(2)
    with chart_cols[0]:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=hist['s'].round(1), mode='lines+markers',
            line=dict(color=COLORS['primary'], width=2), marker=dict(size=6),
            name='Прочность', hovertemplate="Партия %{x}<br>%{y:.1f} сН/текс<extra></extra>"))
        fig.add_trace(go.Scatter(x=x, y=hist['s'].rolling(5, min_periods=1).mean().round(1),
            mode='lines', line=dict(color=COLORS['secondary'], width=3),
            name='Скользящее (5 партий)', hovertemplate="Партия %{x}<br>ср. %{y:.1f}<extra></extra>"))
        fig.add_hline(y=QUALITY_THRESHOLDS['strength_min'],
            line=dict(color=COLORS['danger'], dash='dash', width=1.5),
            annotation_text=f"Мин: {QUALITY_THRESHOLDS['strength_min']}", annotation_position="bottom right",
            annotation_font=dict(color=COLORS['danger'], size=11))
        fig.update_layout(title=dict(text='<b>Прочность по партиям</b>', font=dict(size=14, color=COLORS['text']), x=0.5),
            height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']),
            xaxis=dict(title='Партия', tickfont=dict(color=COLORS['text_secondary']), gridcolor=COLORS['grid']),
            yaxis=dict(title='сН/текс', tickfont=dict(color=COLORS['text_secondary']), gridcolor=COLORS['grid']),
            legend=dict(orientation='h', y=1.12, x=0, font=dict(size=10, color=COLORS['text_secondary'])),
            margin=dict(t=60, b=40, l=50, r=20))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key='mh_strength')

    with chart_cols[1]:
        fig = go.Figure()
        dev_colors = [COLORS['danger'] if v <= mh.DEV_LOW else COLORS['success'] if v >= 0 else COLORS['warning'] for v in hist['dev']]
        fig.add_trace(go.Bar(x=x, y=hist['dev'].round(2), marker_color=dev_colors,
            name='Отклонение', hovertemplate="Партия %{x}<br>%{y:+.2f} сН/текс<extra></extra>"))
        fig.add_hline(y=0, line=dict(color=COLORS['text_secondary'], width=1))
        fig.add_hline(y=mh.DEV_LOW, line=dict(color=COLORS['danger'], dash='dash', width=1.5),
            annotation_text=f"Порог: {mh.DEV_LOW}", annotation_position="bottom right",
            annotation_font=dict(color=COLORS['danger'], size=11))
        fig.update_layout(title=dict(text='<b>Отклонение от среднего партии (вклад машины, без полимера)</b>',
            font=dict(size=14, color=COLORS['text']), x=0.5),
            height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']), showlegend=False,
            xaxis=dict(title='Партия', tickfont=dict(color=COLORS['text_secondary']), gridcolor=COLORS['grid']),
            yaxis=dict(title='сН/текс', tickfont=dict(color=COLORS['text_secondary']), gridcolor=COLORS['grid'], zeroline=False),
            margin=dict(t=60, b=40, l=50, r=20))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key='mh_dev')

    chart_cols2 = st.columns(2)
    with chart_cols2[0]:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=hist['cv'].round(1), mode='lines+markers',
            line=dict(color=COLORS['accent'], width=2), marker=dict(size=6),
            name='CV', hovertemplate="Партия %{x}<br>CV %{y:.1f}%<extra></extra>"))
        fig.add_hline(y=QUALITY_THRESHOLDS['cv_max'], line=dict(color=COLORS['danger'], dash='dash', width=1.5),
            annotation_text=f"Макс: {QUALITY_THRESHOLDS['cv_max']:.0f}", annotation_position="top right",
            annotation_font=dict(color=COLORS['danger'], size=11))
        fig.add_hline(y=mh.CV_WARN, line=dict(color=COLORS['warning'], dash='dot', width=1.5),
            annotation_text=f"Предупр.: {mh.CV_WARN:.0f}", annotation_position="bottom right",
            annotation_font=dict(color=COLORS['warning'], size=11))
        fig.update_layout(title=dict(text='<b>Коэффициент вариации по партиям</b>', font=dict(size=14, color=COLORS['text']), x=0.5),
            height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text']), showlegend=False,
            xaxis=dict(title='Партия', tickfont=dict(color=COLORS['text_secondary']), gridcolor=COLORS['grid']),
            yaxis=dict(title='CV, %', tickfont=dict(color=COLORS['text_secondary']), gridcolor=COLORS['grid'], rangemode='tozero'),
            margin=dict(t=60, b=40, l=50, r=20))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key='mh_cv')

    with chart_cols2[1]:
        # Разрез по аппаратам ВТВ для этой машины
        if '№ ВТВ' in df.columns:
            dv = df.copy()
            dv['ВТВ'] = pd.to_numeric(dv['№ ВТВ'], errors='coerce')
            dv = dv[(dv['ВТВ'].between(1, 19)) & (dv['№ ПМ'] == selected_pm)]
            g = dv.groupby('ВТВ')[mh.STRENGTH_COL].agg(['mean', 'count'])
            g = g[g['count'] >= 2].sort_values('mean')
            if len(g) >= 2:
                thr = QUALITY_THRESHOLDS['strength_min']
                bar_colors = [COLORS['danger'] if v < thr else COLORS['warning'] if v < thr + 5 else COLORS['success'] for v in g['mean']]
                fig = go.Figure(go.Bar(
                    x=[f"№{int(i)}" for i in g.index], y=g['mean'].round(1),
                    marker_color=bar_colors, customdata=g['count'],
                    text=[f"{v:.0f}" for v in g['mean']], textposition='outside',
                    textfont=dict(size=10, color=COLORS['text']),
                    hovertemplate="ВТВ %{x}<br>Ср. прочность: %{y:.1f}<br>Измерений: %{customdata}<extra></extra>"))
                fig.add_hline(y=thr, line=dict(color=COLORS['danger'], dash='dash', width=1.5))
                fig.update_layout(title=dict(text=f'<b>ПМ {selected_pm} по аппаратам ВТВ</b>',
                    font=dict(size=14, color=COLORS['text']), x=0.5),
                    height=340, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['text']), showlegend=False,
                    xaxis=dict(title='Аппарат ВТВ', tickfont=dict(color=COLORS['text_secondary']), showgrid=False),
                    yaxis=dict(title='сН/текс', tickfont=dict(color=COLORS['text_secondary']), gridcolor=COLORS['grid'],
                               range=[min(g['mean'].min() - 5, thr - 8), g['mean'].max() + 8]),
                    margin=dict(t=60, b=40, l=50, r=20))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key='mh_vtv')
                st.markdown(f"<span style='color:{COLORS['text_secondary']};font-size:12px;'>Если у машины проседает только один аппарат — причина в аппарате, а не в машине.</span>", unsafe_allow_html=True)
            else:
                st.info("Недостаточно данных по аппаратам ВТВ для этой машины")

    # Динамика по окнам: было/стало
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    win_rows = []
    for w in [10, 40, 100]:
        if w > len(all_parties):
            continue
        r = mh.compute_registry(df, w, QUALITY_THRESHOLDS)
        r = r[r['машина'] == selected_pm]
        if not r.empty:
            rr = r.iloc[0]
            win_rows.append((w, rr['прочность_средняя'], rr['откл_от_партии'], rr['cv_средний'], rr['ниже_нормы_%']))
    if win_rows:
        cells = "".join(
            f"<tr><td><b>Последние {w}</b></td><td>{s}</td><td>{d:+.2f}</td><td>{c}</td><td>{f}%</td></tr>"
            for w, s, d, c, f in win_rows)
        st.markdown(f"""
            <table class="compare-table">
                <tr class="header-row"><th>Окно (партий)</th><th>Прочность ср.</th><th>Откл. от партии</th><th>CV ср.</th><th>Ниже 260</th></tr>
                {cells}
            </table>
        """, unsafe_allow_html=True)

    st.markdown(f"""
        <div style="text-align: center; margin-top: 40px; padding: 20px; color: {COLORS['text_secondary']};">
            <small>Паспорт машин | Нить 50 кр/м | Отклонение от среднего партии изолирует вклад машины от полимера</small>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
