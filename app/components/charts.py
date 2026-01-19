import plotly.graph_objects as go
import plotly.express as px
import sys
import os
import pandas as pd
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import COLORS, CHART_CONFIG, QUALITY_THRESHOLDS, GAUGE_CONFIG
import numpy as np


def create_gauge_chart(value, config_key, good_count=None, total_count=None):
    """Создание gauge-индикатора (оптимизировано)"""
    config = GAUGE_CONFIG[config_key]

    # Определяем статус
    if config_key == 'cv':
        is_good = value <= config['threshold']
    elif config_key == 'density':
        is_good = config['range'][0] <= value <= config['range'][1]
    else:
        is_good = value >= config['threshold']

    needle_color = COLORS['success'] if is_good else COLORS['danger']

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'font': {'size': 28, 'color': COLORS['text']}, 'suffix': ''},
        gauge={
            'axis': {
                'range': [config['min'], config['max']],
                'tickwidth': 2,
                'tickcolor': COLORS['text_secondary'],
                'tickfont': {'size': 10, 'color': COLORS['text_secondary']},
            },
            'bar': {'color': needle_color, 'thickness': 0.3},
            'bgcolor': COLORS['card'],
            'borderwidth': 0,
            'steps': [
                {'range': [config['min'], config.get('threshold', config.get('range', [0, 0])[0])],
                 'color': 'rgba(239, 68, 68, 0.2)' if config_key != 'cv' else 'rgba(16, 185, 129, 0.2)'},
                {'range': [config.get('threshold', config.get('range', [0, 0])[1]), config['max']],
                 'color': 'rgba(16, 185, 129, 0.2)' if config_key != 'cv' else 'rgba(239, 68, 68, 0.2)'},
            ],
            'threshold': {
                'line': {'color': COLORS['warning'], 'width': 3},
                'thickness': 0.8,
                'value': config.get('threshold', sum(config.get('range', [0, 0]))/2)
            }
        },
        title={'text': f"<b>{config['title']}</b>", 'font': {'size': 16, 'color': COLORS['text']}}
    ))

    if good_count is not None and total_count is not None:
        status_text = f"{good_count}/{total_count} в норме"
        status_color = COLORS['success'] if good_count == total_count else COLORS['warning'] if good_count > total_count/2 else COLORS['danger']
        fig.add_annotation(x=0.5, y=-0.15, text=f"<b>{status_text}</b>",
            font=dict(size=14, color=status_color), showarrow=False, xref="paper", yref="paper")

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=60, l=20, r=20), height=280
    )

    return fig


@st.cache_data(ttl=1800, show_spinner=False)
def create_trend_chart_cached(parties_index, values, threshold):
    """Кэшированный график тренда (30 мин кэш)"""
    return _create_trend_chart_impl(parties_index, values, threshold)


def create_trend_chart(last_10_parties):
    """Создание графика тенденций (обёртка для кэширования)"""
    x_raw = tuple(last_10_parties.index.tolist())
    y_values = tuple(last_10_parties['Относительная разрывная нагрузка, сН/текс'].values.tolist())
    return create_trend_chart_cached(x_raw, y_values, QUALITY_THRESHOLDS['strength_min'])


def _create_trend_chart_impl(x_raw, y_values, threshold):
    """Реализация графика тренда"""
    fig = go.Figure()

    x_raw = np.array(x_raw)
    y_values = np.array(y_values)
    x_display = x_raw - 714

    if len(x_raw) == 0:
        fig.update_layout(title='Динамика разрывной нагрузки', height=400,
            plot_bgcolor=COLORS['background'], paper_bgcolor=COLORS['background'])
        return fig

    # Градиентная заливка
    fig.add_trace(go.Scatter(
        x=x_display, y=y_values, fill='tozeroy', fillcolor='rgba(0, 212, 255, 0.1)',
        line=dict(color='rgba(0,0,0,0)'), showlegend=False, hoverinfo='skip'
    ))

    # Основная линия
    fig.add_trace(go.Scatter(
        x=x_display, y=y_values, name='Разрывная нагрузка',
        line=dict(color=COLORS['primary'], width=3, shape='spline'),
        mode='lines+markers',
        marker=dict(size=12, color=COLORS['primary'], line=dict(color=COLORS['background'], width=2)),
        hovertemplate="Партия %{x}<br>Нагрузка: %{y:.1f} сН/текс<extra></extra>"
    ))

    if len(x_raw) > 1:
        coefficients = np.polyfit(x_raw, y_values, 1)
        y_trend = np.poly1d(coefficients)(x_raw)
        trend_direction = "↗" if coefficients[0] > 0 else "↘"
        trend_color = COLORS['success'] if coefficients[0] > 0 else COLORS['danger']

        fig.add_trace(go.Scatter(
            x=x_display, y=y_trend, name=f'Тренд {trend_direction}',
            line=dict(color=trend_color, width=2, dash='dash'), mode='lines', hoverinfo='skip'
        ))

    fig.add_shape(type="line", x0=min(x_display), x1=max(x_display),
        y0=threshold, y1=threshold, line=dict(color=COLORS['danger'], dash="dot", width=2))

    fig.add_annotation(x=max(x_display), y=threshold, text=f"Мин: {threshold}",
        font=dict(color=COLORS['danger'], size=11), showarrow=False, xanchor='left', xshift=10)

    fig.update_layout(
        title=dict(text='<b>Динамика разрывной нагрузки</b>', font=dict(size=20, color=COLORS['text']), x=0.5),
        xaxis=dict(title='Партия 2026', title_font=dict(size=12, color=COLORS['text_secondary']),
            tickfont=dict(color=COLORS['text_secondary']), gridcolor=COLORS['grid'], showgrid=True,
            range=[min(x_display) - 0.5, max(x_display) + 0.5], dtick=1),
        yaxis=dict(range=[min(y_values) - 10, max(y_values) + 10], title='Разрывная нагрузка, сН/текс',
            title_font=dict(size=12, color=COLORS['text_secondary']), tickfont=dict(color=COLORS['text_secondary']),
            gridcolor=COLORS['grid'], showgrid=True),
        height=400, hovermode='x unified', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=80, b=60, l=60, r=80), showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01,
            bgcolor='rgba(30, 41, 59, 0.8)', font=dict(color=COLORS['text']))
    )

    return fig


def create_heatmap(df, metric_column, title, threshold_config):
    """Создание тепловой карты (оптимизировано)"""
    parties = sorted(df['№ партии'].dropna().unique())[-15:]
    machines = sorted(df['№ ПМ'].dropna().unique())

    matrix = []
    for machine in machines:
        row = []
        for party in parties:
            value = df[(df['№ ПМ'] == machine) & (df['№ партии'] == party)][metric_column]
            row.append(value.values[0] if len(value) > 0 else None)
        matrix.append(row)

    if 'range' in threshold_config:
        colorscale = [[0, COLORS['danger']], [0.3, COLORS['warning']], [0.5, COLORS['success']], [0.7, COLORS['warning']], [1, COLORS['danger']]]
        zmin, zmax = threshold_config['range'][0] - 1, threshold_config['range'][1] + 1
    elif threshold_config.get('inverse'):
        colorscale = [[0, COLORS['success']], [0.5, COLORS['warning']], [1, COLORS['danger']]]
        zmin, zmax = 0, threshold_config['threshold'] * 1.5
    else:
        colorscale = [[0, COLORS['danger']], [0.5, COLORS['warning']], [1, COLORS['success']]]
        zmin, zmax = threshold_config['threshold'] * 0.85, threshold_config['threshold'] * 1.15

    fig = go.Figure(data=go.Heatmap(
        z=matrix, x=[f"П{int(p)}" for p in parties], y=[f"М{int(m)}" for m in machines],
        colorscale=colorscale, zmin=zmin, zmax=zmax, showscale=True, xgap=2, ygap=2
    ))

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=16, color=COLORS['text']), x=0.5),
        xaxis=dict(title="Партия", tickfont=dict(color=COLORS['text_secondary'], size=10)),
        yaxis=dict(title="Машина", tickfont=dict(color=COLORS['text_secondary'], size=10)),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=60, l=60, r=20), height=400
    )

    return fig


@st.cache_data(ttl=1800, show_spinner=False)
def create_problem_machines_chart_cached(problems_data):
    """Кэшированный график проблемных машин (30 мин кэш)"""
    return _create_problem_machines_impl(problems_data)


def create_problem_machines_chart(df, last_n_parties=10):
    """Топ 5 проблемных машин (обёртка для кэширования)"""
    recent_parties = sorted(df['№ партии'].dropna().unique())[-last_n_parties:]
    recent_data = df[df['№ партии'].isin(recent_parties)]

    problems = []
    for machine in recent_data['№ ПМ'].dropna().unique():
        machine_data = recent_data[recent_data['№ ПМ'] == machine]
        low_strength = (machine_data['Относительная разрывная нагрузка, сН/текс'] < QUALITY_THRESHOLDS['strength_min']).sum()
        high_cv = (machine_data['Коэффициент вариации, %'] > QUALITY_THRESHOLDS['cv_max']).sum()
        total = low_strength + high_cv
        if total > 0:
            problems.append((f"М{int(machine)}", total))

    problems = sorted(problems, key=lambda x: x[1], reverse=True)[:5]
    return create_problem_machines_chart_cached(tuple(problems))


def _create_problem_machines_impl(problems):
    """Реализация графика проблемных машин (топ 5)"""
    if not problems:
        fig = go.Figure()
        fig.add_annotation(x=0.5, y=0.5, text="Все машины в норме",
            font=dict(size=18, color=COLORS['success']), showarrow=False, xref="paper", yref="paper")
        fig.update_layout(height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig

    machines_list = [p[0] for p in problems]
    values = [p[1] for p in problems]
    colors = [COLORS['danger'] if v >= 4 else COLORS['warning'] if v >= 2 else COLORS['accent'] for v in values]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=machines_list, x=values, orientation='h', marker_color=colors,
        text=values, textposition='outside', textfont=dict(color=COLORS['text'], size=12),
        hovertemplate="<b>%{y}</b><br>Отклонений: %{x}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(text='Топ 5 проблемных машин', font=dict(size=16, color=COLORS['text']), x=0.5, xanchor='center'),
        xaxis=dict(title='Отклонений', tickfont=dict(color=COLORS['text_secondary'], size=10), gridcolor=COLORS['grid']),
        yaxis=dict(tickfont=dict(color=COLORS['text'], size=11), autorange='reversed'),
        height=280, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=50, l=50, r=30), showlegend=False
    )

    return fig


@st.cache_data(ttl=1800, show_spinner=False)
def create_quality_scatter_cached(strength_values, cv_values, machines, party_number):
    """Кэшированный scatter график (30 мин кэш)"""
    return _create_quality_scatter_impl(strength_values, cv_values, machines, party_number)


def create_quality_scatter(df, party_number=None):
    """Scatter: Нагрузка vs CV (обёртка для кэширования)"""
    if party_number is None:
        party_number = df['№ партии'].max()

    party_data = df[df['№ партии'] == party_number]

    strength = tuple(party_data['Относительная разрывная нагрузка, сН/текс'].values.tolist())
    cv = tuple(party_data['Коэффициент вариации, %'].values.tolist())
    machines = tuple(party_data['№ ПМ'].values.tolist())

    return create_quality_scatter_cached(strength, cv, machines, party_number)


def _create_quality_scatter_impl(strength_values, cv_values, machines, party_number):
    """Реализация scatter графика"""
    strength_values = np.array(strength_values)
    cv_values = np.array(cv_values)

    # Определяем цвета
    colors = []
    for s, c in zip(strength_values, cv_values):
        s_ok = s >= QUALITY_THRESHOLDS['strength_min']
        c_ok = c <= QUALITY_THRESHOLDS['cv_max']
        if s_ok and c_ok:
            colors.append(COLORS['success'])
        elif s_ok or c_ok:
            colors.append(COLORS['warning'])
        else:
            colors.append(COLORS['danger'])

    fig = go.Figure()

    # Зоны
    fig.add_shape(type="rect", x0=QUALITY_THRESHOLDS['strength_min'], x1=350, y0=0, y1=QUALITY_THRESHOLDS['cv_max'],
        fillcolor="rgba(16, 185, 129, 0.15)", line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=200, x1=QUALITY_THRESHOLDS['strength_min'], y0=QUALITY_THRESHOLDS['cv_max'], y1=20,
        fillcolor="rgba(239, 68, 68, 0.15)", line=dict(width=0), layer="below")

    # Пороги
    fig.add_vline(x=QUALITY_THRESHOLDS['strength_min'], line=dict(color=COLORS['danger'], dash='dash', width=1.5))
    fig.add_hline(y=QUALITY_THRESHOLDS['cv_max'], line=dict(color=COLORS['danger'], dash='dash', width=1.5))

    # Точки
    fig.add_trace(go.Scatter(
        x=strength_values, y=cv_values, mode='markers',
        marker=dict(size=12, color=colors, line=dict(width=1, color=COLORS['background'])),
        text=[f"М{int(m)}" for m in machines],
        hovertemplate="<b>Машина %{text}</b><br>Нагрузка: %{x:.1f} сН/текс<br>CV: %{y:.1f}%<extra></extra>"
    ))

    good = sum(1 for c in colors if c == COLORS['success'])
    warn = sum(1 for c in colors if c == COLORS['warning'])
    bad = sum(1 for c in colors if c == COLORS['danger'])

    fig.update_layout(
        title=dict(text=f'Карта качества (партия {int(party_number) - 714})', font=dict(size=16, color=COLORS['text']), x=0.5),
        xaxis=dict(title='Разрывная нагрузка, сН/текс', tickfont=dict(color=COLORS['text_secondary'], size=10), gridcolor=COLORS['grid'],
            range=[min(min(strength_values) - 5, 250), max(max(strength_values) + 5, 310)]),
        yaxis=dict(title='CV, % (меньше лучше)', tickfont=dict(color=COLORS['text_secondary'], size=10), gridcolor=COLORS['grid'],
            range=[0, max(max(cv_values) + 2, 12)]),
        height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=50, l=50, r=30), showlegend=False,
        annotations=[dict(x=0.02, y=0.98, xref='paper', yref='paper', showarrow=False,
            text=f"✅ {good}  ⚠️ {warn}  ❌ {bad}", font=dict(size=11, color=COLORS['text']),
            bgcolor=COLORS['card'], borderpad=4)]
    )

    return fig


def create_pie_chart(total, bad, title, good_label, bad_label):
    """Создание круговой диаграммы (legacy)"""
    colors = [COLORS['success'], COLORS['danger']]

    fig = go.Figure(data=[go.Pie(
        labels=[good_label, bad_label], values=[total - bad, bad], hole=.7,
        marker_colors=colors, textinfo='percent', textfont=dict(size=CHART_CONFIG['label_size']), rotation=90
    )])

    fig.add_annotation(text=f"{total-bad}/{total}", x=0.5, y=0.5,
        font=dict(size=CHART_CONFIG['label_size'], color=COLORS['text']), showarrow=False)

    fig.update_layout(
        title=dict(text=title, y=0.95, x=0.5, xanchor='center', yanchor='top', font=dict(size=16, color=COLORS['text'])),
        showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, b=0, l=0, r=0), height=300, width=300, autosize=False
    )

    return fig


def create_sparkline(values, parties, metric_type='strength', height=50):
    """Компактный мини-график (СИЛЬНО ОПТИМИЗИРОВАН)"""
    if len(values) == 0:
        return None

    mean_val = np.mean(values)

    # Настройки
    if metric_type == 'strength':
        threshold = QUALITY_THRESHOLDS['strength_min']
        line_color = COLORS['success'] if mean_val >= threshold else COLORS['danger']
        y_range = [min(min(values) - 10, 250), max(max(values) + 10, 300)]
    elif metric_type == 'cv':
        threshold = QUALITY_THRESHOLDS['cv_max']
        line_color = COLORS['success'] if mean_val <= threshold else COLORS['danger']
        y_range = [0, max(max(values) + 2, 12)]
    else:
        thresh_min, thresh_max = QUALITY_THRESHOLDS['density_range']
        line_color = COLORS['success'] if thresh_min <= mean_val <= thresh_max else COLORS['danger']
        y_range = [min(min(values) - 0.5, 27.5), max(max(values) + 0.5, 30)]

    fig = go.Figure()

    # Только одна линия - без точек для скорости
    fig.add_trace(go.Scatter(
        x=list(range(len(values))), y=values,
        mode='lines', line=dict(color=line_color, width=2),
        hoverinfo='skip', showlegend=False
    ))

    # Одна линия порога
    if metric_type == 'density':
        fig.add_hline(y=(thresh_min + thresh_max) / 2, line=dict(color=COLORS['text_secondary'], width=1, dash='dot'))
    else:
        fig.add_hline(y=threshold, line=dict(color=COLORS['text_secondary'], width=1, dash='dot'))

    fig.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False, range=y_range),
        height=height, margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False
    )

    return fig


# === ИНДИКАТОР СО СРЕДНИМ ЗНАЧЕНИЕМ ===

def create_mini_indicator(values, metric_type='strength'):
    """Индикатор со средним значением за последние 5 партий + тренд"""
    if len(values) == 0:
        return "—"

    # Берём последние 5 значений
    values = list(values)[-5:]
    avg_val = np.mean(values)

    # Определяем цвет по среднему значению
    if metric_type == 'strength':
        # Разрывная нагрузка: <270 красный, 270-280 оранжевый, >280 зелёный
        if avg_val < 270:
            dot = "🔴"
        elif avg_val < 280:
            dot = "🟠"
        else:
            dot = "🟢"
    elif metric_type == 'cv':
        # CV: >9 красный, 6.5-9 оранжевый, <6.5 зелёный
        if avg_val > 9:
            dot = "🔴"
        elif avg_val >= 6.5:
            dot = "🟠"
        else:
            dot = "🟢"

    # Тренд по последним 3 значениям (простые стрелки)
    if len(values) >= 3:
        recent = values[-3:]
        if metric_type == 'strength':
            # Для разрывной нагрузки: рост = хорошо
            if recent[-1] > recent[0] + 2:
                trend = "↑"
            elif recent[-1] < recent[0] - 2:
                trend = "↓"
            else:
                trend = "→"
        else:
            # Для CV: снижение = хорошо
            if recent[-1] < recent[0] - 0.3:
                trend = "↑"
            elif recent[-1] > recent[0] + 0.3:
                trend = "↓"
            else:
                trend = "→"
    else:
        trend = "→"

    return f"{dot} <b>{avg_val:.1f}</b> {trend}"
