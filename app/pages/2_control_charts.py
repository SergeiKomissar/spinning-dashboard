import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_processing import load_data
from utils.constants import COLORS, CHART_CONFIG, QUALITY_THRESHOLDS
from utils.auth import login_form, logout_button
from components.layout import inject_custom_css

st.set_page_config(
    page_title="Контрольные карты | SPC",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# КОНСТАНТЫ ШУХАРТА (ГОСТ ISO 7870-2)
# ============================================================
SHEWHART_CONSTANTS = {
    # n: (A2, D3, D4, B3, B4, d2, c4)
    2:  (1.880, 0,     3.267, 0,     3.267, 1.128, 0.798),
    3:  (1.023, 0,     2.575, 0,     2.568, 1.693, 0.886),
    4:  (0.729, 0,     2.282, 0,     2.266, 2.059, 0.921),
    5:  (0.577, 0,     2.114, 0,     2.089, 2.326, 0.940),
    6:  (0.483, 0,     2.004, 0.030, 1.970, 2.534, 0.952),
    7:  (0.419, 0.076, 1.924, 0.118, 1.882, 2.704, 0.959),
    8:  (0.373, 0.136, 1.864, 0.185, 1.815, 2.847, 0.965),
    9:  (0.337, 0.184, 1.816, 0.239, 1.761, 2.970, 0.969),
    10: (0.308, 0.223, 1.777, 0.284, 1.716, 3.078, 0.973),
    15: (0.223, 0.348, 1.652, 0.428, 1.572, 3.472, 0.982),
    20: (0.180, 0.414, 1.586, 0.510, 1.490, 3.735, 0.987),
    25: (0.153, 0.459, 1.541, 0.565, 1.435, 3.931, 0.990),
}


def get_shewhart_constants(n):
    if n in SHEWHART_CONSTANTS:
        return SHEWHART_CONSTANTS[n]
    keys = sorted(SHEWHART_CONSTANTS.keys())
    if n < keys[0]:
        return SHEWHART_CONSTANTS[keys[0]]
    if n > keys[-1]:
        return SHEWHART_CONSTANTS[keys[-1]]
    closest = min(keys, key=lambda x: abs(x - n))
    return SHEWHART_CONSTANTS[closest]


# ============================================================
# ФУНКЦИИ РАСЧЁТА КОНТРОЛЬНЫХ КАРТ
# ============================================================

def calc_xbar_r_data(df, metric_col, party_col='№ партии'):
    parties = sorted(df[party_col].dropna().unique())
    x_bars = []
    ranges = []
    stds = []
    party_labels = []
    subgroup_sizes = []

    for party in parties:
        party_data = df[df[party_col] == party][metric_col].dropna()
        if len(party_data) < 2:
            continue
        x_bars.append(party_data.mean())
        ranges.append(party_data.max() - party_data.min())
        stds.append(party_data.std(ddof=1))
        party_labels.append(int(party) - 714)
        subgroup_sizes.append(len(party_data))

    if len(x_bars) < 3:
        return None

    x_bars = np.array(x_bars)
    ranges = np.array(ranges)
    stds = np.array(stds)

    avg_n = int(round(np.mean(subgroup_sizes)))
    A2, D3, D4, B3, B4, d2, c4 = get_shewhart_constants(avg_n)

    x_bar_bar = np.mean(x_bars)
    r_bar = np.mean(ranges)
    s_bar = np.mean(stds)

    x_ucl = x_bar_bar + A2 * r_bar
    x_lcl = x_bar_bar - A2 * r_bar
    r_ucl = D4 * r_bar
    r_lcl = D3 * r_bar
    s_ucl = B4 * s_bar
    s_lcl = B3 * s_bar
    sigma_x = (A2 * r_bar) / 3

    return {
        'party_labels': party_labels, 'x_bars': x_bars,
        'ranges': ranges, 'stds': stds,
        'x_bar_bar': x_bar_bar, 'r_bar': r_bar, 's_bar': s_bar,
        'x_ucl': x_ucl, 'x_lcl': x_lcl,
        'r_ucl': r_ucl, 'r_lcl': r_lcl,
        's_ucl': s_ucl, 's_lcl': s_lcl,
        'sigma_x': sigma_x, 'avg_n': avg_n, 'subgroup_sizes': subgroup_sizes,
        'A2': A2, 'D3': D3, 'D4': D4, 'B3': B3, 'B4': B4,
    }


def calc_p_chart_data(df, metric_col, threshold, mode='less', party_col='№ партии'):
    parties = sorted(df[party_col].dropna().unique())
    proportions = []
    party_labels = []
    subgroup_sizes = []

    for party in parties:
        party_data = df[df[party_col] == party][metric_col].dropna()
        n = len(party_data)
        if n < 2:
            continue
        if mode == 'less':
            defects = (party_data < threshold).sum()
        else:
            defects = (party_data > threshold).sum()
        proportions.append(defects / n)
        party_labels.append(int(party) - 714)
        subgroup_sizes.append(n)

    if len(proportions) < 3:
        return None

    proportions = np.array(proportions)
    subgroup_sizes = np.array(subgroup_sizes)
    p_bar = np.mean(proportions)
    ucl = p_bar + 3 * np.sqrt(p_bar * (1 - p_bar) / subgroup_sizes)
    lcl = np.maximum(0, p_bar - 3 * np.sqrt(p_bar * (1 - p_bar) / subgroup_sizes))

    return {
        'party_labels': party_labels, 'proportions': proportions,
        'p_bar': p_bar, 'ucl': ucl, 'lcl': lcl,
        'subgroup_sizes': subgroup_sizes,
    }


def calc_xmr_data(df, machine_num, metric_col, party_col='№ партии', pm_col='№ ПМ'):
    machine_data = df[df[pm_col] == machine_num].sort_values(party_col)
    values = machine_data[metric_col].dropna().values
    parties = machine_data.loc[machine_data[metric_col].notna(), party_col].values

    if len(values) < 3:
        return None

    party_labels = [int(p) - 714 for p in parties]
    mr = np.abs(np.diff(values))
    x_bar = np.mean(values)
    mr_bar = np.mean(mr)
    d2 = 1.128
    sigma_est = mr_bar / d2
    x_ucl = x_bar + 3 * sigma_est
    x_lcl = x_bar - 3 * sigma_est
    mr_ucl = 3.267 * mr_bar
    mr_lcl = 0

    return {
        'party_labels': party_labels, 'values': values,
        'mr': mr, 'mr_parties': party_labels[1:],
        'x_bar': x_bar, 'mr_bar': mr_bar,
        'x_ucl': x_ucl, 'x_lcl': x_lcl,
        'mr_ucl': mr_ucl, 'mr_lcl': mr_lcl,
        'sigma_est': sigma_est,
    }


# ============================================================
# ПРАВИЛА ВЫХОДА ИЗ УПРАВЛЕНИЯ (ГОСТ ISO 7870-2)
# ============================================================

def detect_out_of_control(values, cl, ucl, lcl):
    signals = {}
    n = len(values)
    sigma = (ucl - cl) / 3 if ucl != cl else 1

    for i, v in enumerate(values):
        if v > ucl or v < lcl:
            signals.setdefault(i, []).append("За контр. границей (3σ)")

    count_above = 0
    count_below = 0
    for i, v in enumerate(values):
        if v > cl:
            count_above += 1
            count_below = 0
        elif v < cl:
            count_below += 1
            count_above = 0
        else:
            count_above = 0
            count_below = 0
        if count_above >= 9:
            for j in range(i - 8, i + 1):
                signals.setdefault(j, []).append("9 точек выше CL")
        if count_below >= 9:
            for j in range(i - 8, i + 1):
                signals.setdefault(j, []).append("9 точек ниже CL")

    if n >= 6:
        inc = 0
        dec = 0
        for i in range(1, n):
            if values[i] > values[i-1]:
                inc += 1
                dec = 0
            elif values[i] < values[i-1]:
                dec += 1
                inc = 0
            else:
                inc = 0
                dec = 0
            if inc >= 5:
                for j in range(i - 4, i + 1):
                    signals.setdefault(j, []).append("Тренд ↗ (6 точек)")
            if dec >= 5:
                for j in range(i - 4, i + 1):
                    signals.setdefault(j, []).append("Тренд ↘ (6 точек)")

    zone_2sigma_upper = cl + 2 * sigma
    zone_2sigma_lower = cl - 2 * sigma
    if n >= 3:
        for i in range(2, n):
            window = values[i-2:i+1]
            above_2s = sum(1 for v in window if v > zone_2sigma_upper)
            below_2s = sum(1 for v in window if v < zone_2sigma_lower)
            if above_2s >= 2:
                signals.setdefault(i, []).append("2 из 3 за +2σ")
            if below_2s >= 2:
                signals.setdefault(i, []).append("2 из 3 за -2σ")

    return signals


# ============================================================
# ФУНКЦИИ ВИЗУАЛИЗАЦИИ
# ============================================================

def create_control_chart(data_x, data_y, cl, ucl, lcl, title, y_title,
                          signals=None, spec_limit=None, spec_label=None,
                          zone_lines=True, sigma=None):
    fig = go.Figure()

    if zone_lines and sigma and sigma > 0:
        zones = [
            (cl + 2 * sigma, cl + 3 * sigma, 'rgba(239, 68, 68, 0.08)', 'Зона A+'),
            (cl + sigma, cl + 2 * sigma, 'rgba(245, 158, 11, 0.08)', 'Зона B+'),
            (cl, cl + sigma, 'rgba(16, 185, 129, 0.05)', 'Зона C+'),
            (cl - sigma, cl, 'rgba(16, 185, 129, 0.05)', 'Зона C-'),
            (cl - 2 * sigma, cl - sigma, 'rgba(245, 158, 11, 0.08)', 'Зона B-'),
            (cl - 3 * sigma, cl - 2 * sigma, 'rgba(239, 68, 68, 0.08)', 'Зона A-'),
        ]
        for y0, y1, color, name in zones:
            fig.add_shape(type="rect", x0=data_x[0] - 0.5, x1=data_x[-1] + 0.5,
                         y0=y0, y1=y1, fillcolor=color, line=dict(width=0), layer="below")

    if signals:
        colors = []
        sizes = []
        for i in range(len(data_y)):
            if i in signals:
                colors.append('#ef4444')
                sizes.append(14)
            else:
                colors.append(COLORS['primary'])
                sizes.append(9)
    else:
        colors = [COLORS['primary']] * len(data_y)
        sizes = [9] * len(data_y)

    fig.add_trace(go.Scatter(
        x=data_x, y=data_y, mode='lines+markers', name='Данные',
        line=dict(color=COLORS['primary'], width=2),
        marker=dict(size=sizes, color=colors, line=dict(width=1, color=COLORS['background'])),
        hovertemplate="Партия %{x}<br>Значение: %{y:.2f}<extra></extra>"
    ))

    fig.add_hline(y=cl, line=dict(color='#22c55e', width=2),
                  annotation_text=f"CL = {cl:.2f}", annotation_position="right",
                  annotation_font=dict(color='#22c55e', size=11))

    fig.add_hline(y=ucl, line=dict(color='#ef4444', width=2, dash='dash'),
                  annotation_text=f"UCL = {ucl:.2f}", annotation_position="right",
                  annotation_font=dict(color='#ef4444', size=11))

    fig.add_hline(y=lcl, line=dict(color='#ef4444', width=2, dash='dash'),
                  annotation_text=f"LCL = {lcl:.2f}", annotation_position="right",
                  annotation_font=dict(color='#ef4444', size=11))

    if zone_lines and sigma and sigma > 0:
        fig.add_hline(y=cl + 2 * sigma, line=dict(color='#f59e0b', width=1, dash='dot'))
        fig.add_hline(y=cl - 2 * sigma, line=dict(color='#f59e0b', width=1, dash='dot'))

    if spec_limit is not None:
        fig.add_hline(y=spec_limit, line=dict(color='#a78bfa', width=2, dash='dashdot'),
                      annotation_text=spec_label or f"Spec = {spec_limit}",
                      annotation_position="left",
                      annotation_font=dict(color='#a78bfa', size=11))

    if signals:
        signal_x = [data_x[i] for i in signals]
        signal_y = [data_y[i] for i in signals]
        signal_text = ["; ".join(signals[i]) for i in signals]
        fig.add_trace(go.Scatter(
            x=signal_x, y=signal_y, mode='markers', name='Сигнал',
            marker=dict(size=16, color='rgba(0,0,0,0)',
                       line=dict(width=3, color='#ef4444'), symbol='circle-open'),
            text=signal_text,
            hovertemplate="<b>СИГНАЛ</b><br>Партия %{x}<br>Значение: %{y:.2f}<br>%{text}<extra></extra>"
        ))

    y_padding = (ucl - lcl) * 0.15 if ucl != lcl else 1
    y_min = min(lcl, min(data_y)) - y_padding
    y_max = max(ucl, max(data_y)) + y_padding
    if spec_limit is not None:
        y_min = min(y_min, spec_limit - y_padding)
        y_max = max(y_max, spec_limit + y_padding)

    fig.update_layout(
        title=dict(text=f'<b>{title}</b>',
                   font=dict(size=16, color=COLORS['text'], family=CHART_CONFIG['font_family']), x=0.5),
        xaxis=dict(title='Партия', title_font=dict(size=12, color=COLORS['text_secondary']),
                   tickfont=dict(color=COLORS['text_secondary']),
                   gridcolor=COLORS['grid'], showgrid=True, dtick=1),
        yaxis=dict(title=y_title, title_font=dict(size=12, color=COLORS['text_secondary']),
                   tickfont=dict(color=COLORS['text_secondary']),
                   gridcolor=COLORS['grid'], showgrid=True, range=[y_min, y_max]),
        height=420, hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=50, l=60, r=120), showlegend=False,
        font=dict(family=CHART_CONFIG['font_family'])
    )
    return fig


def create_p_chart(data, title):
    fig = go.Figure()
    x = data['party_labels']
    y = data['proportions']

    signals = {}
    for i, (p, u, l) in enumerate(zip(y, data['ucl'], data['lcl'])):
        if p > u or p < l:
            signals.setdefault(i, []).append("За контр. границей")

    colors = ['#ef4444' if i in signals else COLORS['primary'] for i in range(len(y))]
    sizes = [14 if i in signals else 9 for i in range(len(y))]

    fig.add_trace(go.Scatter(
        x=x, y=y * 100, mode='lines+markers', name='p',
        line=dict(color=COLORS['primary'], width=2),
        marker=dict(size=sizes, color=colors, line=dict(width=1, color=COLORS['background'])),
        hovertemplate="Партия %{x}<br>Доля: %{y:.1f}%<br>n=%{customdata}<extra></extra>",
        customdata=data['subgroup_sizes']
    ))

    fig.add_hline(y=data['p_bar'] * 100, line=dict(color='#22c55e', width=2),
                  annotation_text=f"CL = {data['p_bar']*100:.1f}%", annotation_position="right",
                  annotation_font=dict(color='#22c55e', size=11))

    fig.add_trace(go.Scatter(
        x=x, y=data['ucl'] * 100, mode='lines', name='UCL',
        line=dict(color='#ef4444', width=1.5, dash='dash'), hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=x, y=data['lcl'] * 100, mode='lines', name='LCL',
        line=dict(color='#ef4444', width=1.5, dash='dash'),
        fill='tonexty', fillcolor='rgba(16, 185, 129, 0.05)', hoverinfo='skip'
    ))

    if signals:
        signal_x = [x[i] for i in signals]
        signal_y = [y[i] * 100 for i in signals]
        fig.add_trace(go.Scatter(
            x=signal_x, y=signal_y, mode='markers', name='Сигнал',
            marker=dict(size=16, color='rgba(0,0,0,0)',
                       line=dict(width=3, color='#ef4444'), symbol='circle-open'),
            hoverinfo='skip'
        ))

    fig.update_layout(
        title=dict(text=f'<b>{title}</b>', font=dict(size=16, color=COLORS['text']), x=0.5),
        xaxis=dict(title='Партия', title_font=dict(size=12, color=COLORS['text_secondary']),
                   tickfont=dict(color=COLORS['text_secondary']),
                   gridcolor=COLORS['grid'], showgrid=True, dtick=1),
        yaxis=dict(title='Доля несоответствующих, %',
                   title_font=dict(size=12, color=COLORS['text_secondary']),
                   tickfont=dict(color=COLORS['text_secondary']),
                   gridcolor=COLORS['grid'], showgrid=True),
        height=420, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=50, l=60, r=120), showlegend=False,
        font=dict(family=CHART_CONFIG['font_family'])
    )
    return fig, signals


def render_spc_summary(data, signals, metric_name):
    n_points = len(data['x_bars']) if 'x_bars' in data else len(data.get('proportions', []))
    n_signals = len(signals)

    if n_signals == 0:
        status_color = '#22c55e'
        status_text = 'УПРАВЛЯЕМ'
        status_icon = '✅'
    else:
        status_color = '#ef4444'
        status_text = 'ТРЕБУЕТ ВНИМАНИЯ'
        status_icon = '⚠️'

    st.markdown(f"""
        <div style="background:#1e293b; padding:16px 20px; border-radius:8px;
                    border-left:4px solid {status_color}; margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:15px; font-weight:600; color:{status_color};">
                        {status_icon} {metric_name}: {status_text}
                    </span>
                </div>
                <div style="display:flex; gap:24px;">
                    <span style="color:#94a3b8; font-size:13px;">
                        Точек: <b style="color:#e2e8f0">{n_points}</b>
                    </span>
                    <span style="color:#94a3b8; font-size:13px;">
                        Сигналов: <b style="color:{status_color}">{n_signals}</b>
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# ============================================================
# ГЛАВНАЯ СТРАНИЦА
# ============================================================

def main():
    if not login_form():
        return

    inject_custom_css()

    st.markdown(
        '<div class="dashboard-header">Контрольные карты Шухарта (ГОСТ ISO 7870-2)</div>',
        unsafe_allow_html=True
    )

    header_cols = st.columns([3, 2, 1, 1])
    with header_cols[0]:
        st.markdown(f"<span style='color:#94a3b8;font-size:13px;'>Пользователь: <b>{st.session_state.user_info['name']}</b></span>", unsafe_allow_html=True)
    with header_cols[1]:
        st.markdown(f"<span style='color:#64748b;font-size:12px;'>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</span>", unsafe_allow_html=True)
    with header_cols[2]:
        if st.button('Обновить', key="spc_refresh"):
            load_data.clear()
            st.rerun()
    with header_cols[3]:
        logout_button()

    with st.spinner('Загрузка данных...'):
        if 'df' not in st.session_state:
            st.session_state.df = load_data()
        df = st.session_state.df

    if df is None or df.empty:
        st.error("Не удалось загрузить данные.")
        return

    st.markdown("""
        <div class="info-block">
            <h4>Статистическое управление процессом (SPC)</h4>
            <p>Контрольные карты построены по ГОСТ ISO 7870-2.
            Подгруппа = все машины одной партии. Красные точки — сигналы выхода из управляемого состояния.
            Жёлтые пунктирные линии — предупредительные границы (±2σ).</p>
        </div>
    """, unsafe_allow_html=True)

    settings_cols = st.columns([2, 2, 2])
    with settings_cols[0]:
        n_parties = st.selectbox(
            "Количество партий для анализа:",
            [10, 15, 20, 25, 30, 50, 100, 200, 500, 1000, "Все"], index=2, key="spc_n_parties"
        )

    all_parties = sorted(df['№ партии'].dropna().unique())
    if n_parties == "Все":
        selected_parties = all_parties
    else:
        selected_parties = all_parties[-n_parties:] if len(all_parties) > n_parties else all_parties
    df_filtered = df[df['№ партии'].isin(selected_parties)]

    strength_col = 'Относительная разрывная нагрузка, сН/текс'
    cv_col = 'Коэффициент вариации, %'

    # ============================================================
    # 1. X-BAR - R КАРТА ПРОЧНОСТИ
    # ============================================================
    st.markdown('<div class="section-header">X\u0304-R карта: Разрывная нагрузка</div>', unsafe_allow_html=True)

    xbar_r_data = calc_xbar_r_data(df_filtered, strength_col)

    if xbar_r_data:
        signals_xbar = detect_out_of_control(
            xbar_r_data['x_bars'], xbar_r_data['x_bar_bar'],
            xbar_r_data['x_ucl'], xbar_r_data['x_lcl']
        )
        render_spc_summary(xbar_r_data, signals_xbar, "Среднее прочности (X\u0304)")

        fig_xbar = create_control_chart(
            xbar_r_data['party_labels'], xbar_r_data['x_bars'],
            xbar_r_data['x_bar_bar'], xbar_r_data['x_ucl'], xbar_r_data['x_lcl'],
            title='X\u0304-карта: Средняя разрывная нагрузка по партии',
            y_title='Средняя нагрузка, сН/текс',
            signals=signals_xbar,
            spec_limit=QUALITY_THRESHOLDS['strength_min'],
            spec_label=f"Мин. допуск: {QUALITY_THRESHOLDS['strength_min']}",
            sigma=xbar_r_data['sigma_x']
        )
        st.plotly_chart(fig_xbar, use_container_width=True, config={'displayModeBar': False})

        signals_r = detect_out_of_control(
            xbar_r_data['ranges'], xbar_r_data['r_bar'],
            xbar_r_data['r_ucl'], xbar_r_data['r_lcl']
        )
        render_spc_summary({'x_bars': xbar_r_data['ranges']}, signals_r, "Размах (R)")

        fig_r = create_control_chart(
            xbar_r_data['party_labels'], xbar_r_data['ranges'],
            xbar_r_data['r_bar'], xbar_r_data['r_ucl'], xbar_r_data['r_lcl'],
            title='R-карта: Размах разрывной нагрузки в партии',
            y_title='Размах, сН/текс', signals=signals_r, zone_lines=False
        )
        st.plotly_chart(fig_r, use_container_width=True, config={'displayModeBar': False})

        with st.expander("Параметры расчёта X\u0304-R карты"):
            param_cols = st.columns(4)
            with param_cols[0]:
                st.markdown(f"**Средний размер подгруппы (n):** {xbar_r_data['avg_n']}")
                st.markdown(f"**Число подгрупп (k):** {len(xbar_r_data['x_bars'])}")
            with param_cols[1]:
                st.markdown(f"**X\u0304\u0304 (grand mean):** {xbar_r_data['x_bar_bar']:.2f}")
                st.markdown(f"**R\u0304 (mean range):** {xbar_r_data['r_bar']:.2f}")
            with param_cols[2]:
                st.markdown(f"**A2:** {xbar_r_data['A2']}")
                st.markdown(f"**D3:** {xbar_r_data['D3']}")
                st.markdown(f"**D4:** {xbar_r_data['D4']}")
            with param_cols[3]:
                st.markdown(f"**UCL (X\u0304):** {xbar_r_data['x_ucl']:.2f}")
                st.markdown(f"**LCL (X\u0304):** {xbar_r_data['x_lcl']:.2f}")
                st.markdown(f"**UCL (R):** {xbar_r_data['r_ucl']:.2f}")
    else:
        st.warning("Недостаточно данных для построения X\u0304-R карты")

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ============================================================
    # 2. X-BAR - S КАРТА CV
    # ============================================================
    st.markdown('<div class="section-header">X\u0304-S карта: Коэффициент вариации</div>', unsafe_allow_html=True)

    xbar_s_data = calc_xbar_r_data(df_filtered, cv_col)

    if xbar_s_data:
        signals_xbar_cv = detect_out_of_control(
            xbar_s_data['x_bars'], xbar_s_data['x_bar_bar'],
            xbar_s_data['x_ucl'], xbar_s_data['x_lcl']
        )
        render_spc_summary(xbar_s_data, signals_xbar_cv, "Среднее CV (X\u0304)")

        fig_xbar_cv = create_control_chart(
            xbar_s_data['party_labels'], xbar_s_data['x_bars'],
            xbar_s_data['x_bar_bar'], xbar_s_data['x_ucl'], xbar_s_data['x_lcl'],
            title='X\u0304-карта: Средний CV по партии',
            y_title='Средний CV, %', signals=signals_xbar_cv,
            spec_limit=QUALITY_THRESHOLDS['cv_max'],
            spec_label=f"Макс. допуск: {QUALITY_THRESHOLDS['cv_max']}%",
            sigma=xbar_s_data['sigma_x']
        )
        st.plotly_chart(fig_xbar_cv, use_container_width=True, config={'displayModeBar': False})

        signals_s = detect_out_of_control(
            xbar_s_data['stds'], xbar_s_data['s_bar'],
            xbar_s_data['s_ucl'], xbar_s_data['s_lcl']
        )
        render_spc_summary({'x_bars': xbar_s_data['stds']}, signals_s, "Стандартное отклонение CV (S)")

        fig_s = create_control_chart(
            xbar_s_data['party_labels'], xbar_s_data['stds'],
            xbar_s_data['s_bar'], xbar_s_data['s_ucl'], xbar_s_data['s_lcl'],
            title='S-карта: Стандартное отклонение CV в партии',
            y_title='Стд. отклонение CV, %', signals=signals_s, zone_lines=False
        )
        st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})

        with st.expander("Параметры расчёта X\u0304-S карты"):
            param_cols = st.columns(4)
            with param_cols[0]:
                st.markdown(f"**Средний размер подгруппы (n):** {xbar_s_data['avg_n']}")
            with param_cols[1]:
                st.markdown(f"**X\u0304\u0304:** {xbar_s_data['x_bar_bar']:.2f}%")
                st.markdown(f"**S\u0304:** {xbar_s_data['s_bar']:.2f}")
            with param_cols[2]:
                st.markdown(f"**B3:** {xbar_s_data['B3']}")
                st.markdown(f"**B4:** {xbar_s_data['B4']}")
            with param_cols[3]:
                st.markdown(f"**UCL (S):** {xbar_s_data['s_ucl']:.2f}")
                st.markdown(f"**LCL (S):** {xbar_s_data['s_lcl']:.2f}")
    else:
        st.warning("Недостаточно данных для построения X\u0304-S карты")

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ============================================================
    # 3. P-КАРТА
    # ============================================================
    st.markdown('<div class="section-header">p-карта: Доля несоответствующих машин</div>', unsafe_allow_html=True)

    p_chart_col1, p_chart_col2 = st.columns(2)

    with p_chart_col1:
        p_data_strength = calc_p_chart_data(
            df_filtered, strength_col,
            threshold=QUALITY_THRESHOLDS['strength_min'], mode='less'
        )
        if p_data_strength:
            fig_p_str, sig_p_str = create_p_chart(
                p_data_strength,
                f'p-карта: прочность < {QUALITY_THRESHOLDS["strength_min"]}'
            )
            render_spc_summary(p_data_strength, sig_p_str, "Доля слабых")
            st.plotly_chart(fig_p_str, use_container_width=True, config={'displayModeBar': False})

    with p_chart_col2:
        p_data_cv = calc_p_chart_data(
            df_filtered, cv_col,
            threshold=QUALITY_THRESHOLDS['cv_max'], mode='greater'
        )
        if p_data_cv:
            fig_p_cv, sig_p_cv = create_p_chart(
                p_data_cv,
                f'p-карта: CV > {QUALITY_THRESHOLDS["cv_max"]}%'
            )
            render_spc_summary(p_data_cv, sig_p_cv, "Доля нестабильных")
            st.plotly_chart(fig_p_cv, use_container_width=True, config={'displayModeBar': False})

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ============================================================
    # 4. X-MR КАРТА ПО ОТДЕЛЬНОЙ МАШИНЕ
    # ============================================================
    st.markdown('<div class="section-header">X-MR карта: Мониторинг отдельной машины</div>', unsafe_allow_html=True)

    st.markdown("""
        <div class="info-block">
            <h4>Индивидуальная контрольная карта</h4>
            <p>Выберите машину для отслеживания её разрывной нагрузки от партии к партии.
            X-карта показывает индивидуальные значения, MR-карта — скользящие размахи между соседними партиями.</p>
        </div>
    """, unsafe_allow_html=True)

    machines = sorted(df_filtered['№ ПМ'].dropna().unique())
    machine_cols = st.columns([2, 2, 2])

    with machine_cols[0]:
        selected_machine = st.selectbox(
            "Выберите машину:", machines,
            format_func=lambda x: f"ПМ {int(x)}", key="spc_machine"
        )

    with machine_cols[1]:
        xmr_metric = st.selectbox(
            "Метрика:", [strength_col, cv_col],
            format_func=lambda x: "Разрывная нагрузка" if "нагрузка" in x else "Коэф. вариации",
            key="spc_xmr_metric"
        )

    if selected_machine:
        xmr_data = calc_xmr_data(df_filtered, selected_machine, xmr_metric)

        if xmr_data:
            signals_xmr = detect_out_of_control(
                xmr_data['values'], xmr_data['x_bar'],
                xmr_data['x_ucl'], xmr_data['x_lcl']
            )
            metric_label = "Прочность" if "нагрузка" in xmr_metric else "CV"
            render_spc_summary({'x_bars': xmr_data['values']}, signals_xmr, f"ПМ {int(selected_machine)} — {metric_label}")

            xmr_cols = st.columns(2)

            with xmr_cols[0]:
                spec = QUALITY_THRESHOLDS['strength_min'] if "нагрузка" in xmr_metric else QUALITY_THRESHOLDS['cv_max']
                spec_lbl = f"Мин: {spec}" if "нагрузка" in xmr_metric else f"Макс: {spec}"
                fig_x = create_control_chart(
                    xmr_data['party_labels'], xmr_data['values'],
                    xmr_data['x_bar'], xmr_data['x_ucl'], xmr_data['x_lcl'],
                    title=f'X-карта: ПМ {int(selected_machine)}',
                    y_title=xmr_metric.split(',')[0], signals=signals_xmr,
                    spec_limit=spec, spec_label=spec_lbl, sigma=xmr_data['sigma_est']
                )
                st.plotly_chart(fig_x, use_container_width=True, config={'displayModeBar': False})

            with xmr_cols[1]:
                signals_mr = detect_out_of_control(
                    xmr_data['mr'], xmr_data['mr_bar'],
                    xmr_data['mr_ucl'], xmr_data['mr_lcl']
                )
                fig_mr = create_control_chart(
                    xmr_data['mr_parties'], xmr_data['mr'],
                    xmr_data['mr_bar'], xmr_data['mr_ucl'], xmr_data['mr_lcl'],
                    title=f'MR-карта: ПМ {int(selected_machine)}',
                    y_title='Скользящий размах', signals=signals_mr, zone_lines=False
                )
                st.plotly_chart(fig_mr, use_container_width=True, config={'displayModeBar': False})

            with st.expander(f"Параметры X-MR карты для ПМ {int(selected_machine)}"):
                param_cols = st.columns(3)
                with param_cols[0]:
                    st.markdown(f"**Точек:** {len(xmr_data['values'])}")
                    st.markdown(f"**X\u0304:** {xmr_data['x_bar']:.2f}")
                with param_cols[1]:
                    st.markdown(f"**MR\u0304:** {xmr_data['mr_bar']:.2f}")
                    st.markdown(f"**sigma (MR\u0304/d2):** {xmr_data['sigma_est']:.2f}")
                with param_cols[2]:
                    st.markdown(f"**UCL (X):** {xmr_data['x_ucl']:.2f}")
                    st.markdown(f"**LCL (X):** {xmr_data['x_lcl']:.2f}")
                    st.markdown(f"**UCL (MR):** {xmr_data['mr_ucl']:.2f}")
        else:
            st.warning(f"Недостаточно данных для машины ПМ {int(selected_machine)}")

    st.markdown(f"""
        <div style="text-align: center; margin-top: 40px; padding: 20px; color: {COLORS['text_secondary']};">
            <small>Контрольные карты по ГОСТ ISO 7870-2 | Данные из Google Sheets</small>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()