"""Контрольные карты Шухарта (ГОСТ ISO 7870-2): расчёт и отрисовка.

Общие для страниц контрольных карт крутки 100 и 50 кр/м. Параметр offset —
смещение номера партии для отображения (см. TWIST*_PARTY_OFFSET в constants).
"""
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import COLORS, CHART_CONFIG


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

def calc_xbar_r_data(df, metric_col, party_col='№ партии', offset=0):
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
        party_labels.append(int(party) - offset)
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


def calc_p_chart_data(df, metric_col, threshold, mode='less', party_col='№ партии', offset=0):
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
        party_labels.append(int(party) - offset)
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


def calc_xmr_data(df, machine_num, metric_col, party_col='№ партии', pm_col='№ ПМ', offset=0):
    machine_data = df[df[pm_col] == machine_num].sort_values(party_col)
    values = machine_data[metric_col].dropna().values
    parties = machine_data.loc[machine_data[metric_col].notna(), party_col].values

    if len(values) < 3:
        return None

    party_labels = [int(p) - offset for p in parties]
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
                  annotation_text=f"Средний уровень {cl:.2f}", annotation_position="right",
                  annotation_font=dict(color='#22c55e', size=11))

    fig.add_hline(y=ucl, line=dict(color='#ef4444', width=2, dash='dash'),
                  annotation_text=f"Верх. граница {ucl:.2f}", annotation_position="right",
                  annotation_font=dict(color='#ef4444', size=11))

    fig.add_hline(y=lcl, line=dict(color='#ef4444', width=2, dash='dash'),
                  annotation_text=f"Ниж. граница {lcl:.2f}", annotation_position="right",
                  annotation_font=dict(color='#ef4444', size=11))

    if zone_lines and sigma and sigma > 0:
        fig.add_hline(y=cl + 2 * sigma, line=dict(color='#f59e0b', width=1, dash='dot'))
        fig.add_hline(y=cl - 2 * sigma, line=dict(color='#f59e0b', width=1, dash='dot'))

    if spec_limit is not None:
        fig.add_hline(y=spec_limit, line=dict(color='#a78bfa', width=2, dash='dashdot'),
                      annotation_text=spec_label or f"Допуск {spec_limit}",
                      annotation_position="top left",
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
                   gridcolor=COLORS['grid'], showgrid=True, dtick=1, showticklabels=(len(data_x) <= 30)),
        yaxis=dict(title=y_title, title_font=dict(size=12, color=COLORS['text_secondary']),
                   tickfont=dict(color=COLORS['text_secondary']),
                   gridcolor=COLORS['grid'], showgrid=True, range=[y_min, y_max]),
        height=420, hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=50, l=60, r=150), showlegend=False,
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
                  annotation_text=f"Средний уровень {data['p_bar']*100:.1f}%", annotation_position="right",
                  annotation_font=dict(color='#22c55e', size=11))

    fig.add_trace(go.Scatter(
        x=x, y=data['ucl'] * 100, mode='lines', name='Верх. граница',
        line=dict(color='#ef4444', width=1.5, dash='dash'), hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=x, y=data['lcl'] * 100, mode='lines', name='Ниж. граница',
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
                   gridcolor=COLORS['grid'], showgrid=True, dtick=1, showticklabels=(len(x) <= 30)),
        yaxis=dict(title='Доля несоответствующих, %',
                   title_font=dict(size=12, color=COLORS['text_secondary']),
                   tickfont=dict(color=COLORS['text_secondary']),
                   gridcolor=COLORS['grid'], showgrid=True),
        height=420, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=50, l=60, r=150), showlegend=False,
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
