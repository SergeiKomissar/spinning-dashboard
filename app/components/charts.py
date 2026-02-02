import plotly.graph_objects as go
import plotly.express as px
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import COLORS, CHART_CONFIG, QUALITY_THRESHOLDS, GAUGE_CONFIG
import numpy as np


def create_gauge_chart(value, config_key, good_count=None, total_count=None):
    """Создание анимированного gauge-индикатора в стиле спидометра"""
    config = GAUGE_CONFIG[config_key]
    
    # Определяем статус (хорошо/плохо)
    if config_key == 'cv':
        is_good = value <= config['threshold']
    elif config_key == 'density':
        is_good = config['range'][0] <= value <= config['range'][1]
    else:
        is_good = value >= config['threshold']
    
    # Цвет стрелки в зависимости от статуса
    needle_color = COLORS['success'] if is_good else COLORS['danger']
    
    # Создаём gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={
            'font': {'size': 28, 'color': COLORS['text'], 'family': CHART_CONFIG['font_family']},
            'suffix': ''
        },
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
        title={
            'text': f"<b>{config['title']}</b>",
            'font': {'size': 16, 'color': COLORS['text'], 'family': CHART_CONFIG['font_family']}
        }
    ))
    
    # Добавляем счётчик хороших/всего если передан
    if good_count is not None and total_count is not None:
        status_text = f"{good_count}/{total_count} в норме"
        status_color = COLORS['success'] if good_count == total_count else COLORS['warning'] if good_count > total_count/2 else COLORS['danger']
        fig.add_annotation(
            x=0.5, y=-0.15,
            text=f"<b>{status_text}</b>",
            font=dict(size=14, color=status_color, family=CHART_CONFIG['font_family']),
            showarrow=False,
            xref="paper", yref="paper"
        )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=60, l=20, r=20),
        height=280,
        font={'family': CHART_CONFIG['font_family']}
    )
    
    return fig


def create_heatmap(df, metric_column, title, threshold_config):
    """Создание тепловой карты качества по машинам и партиям"""
    
    # Получаем последние N партий
    parties = sorted(df['№ партии'].dropna().unique())[-15:]
    machines = sorted(df['№ ПМ'].dropna().unique())
    
    # Создаём матрицу данных
    matrix = []
    hover_text = []
    
    for machine in machines:
        row = []
        hover_row = []
        for party in parties:
            value = df[(df['№ ПМ'] == machine) & (df['№ партии'] == party)][metric_column]
            if len(value) > 0:
                val = value.values[0]
                row.append(val)
                hover_row.append(f"Машина: {int(machine)}<br>Партия: {int(party)}<br>Значение: {val:.1f}")
            else:
                row.append(None)
                hover_row.append("")
        matrix.append(row)
        hover_text.append(hover_row)
    
    # Определяем цветовую шкалу в зависимости от типа метрики
    if 'range' in threshold_config:
        # Для линейной плотности - отклонение от центра диапазона
        center = sum(threshold_config['range']) / 2
        colorscale = [
            [0, COLORS['danger']],
            [0.3, COLORS['warning']],
            [0.5, COLORS['success']],
            [0.7, COLORS['warning']],
            [1, COLORS['danger']]
        ]
        zmin = threshold_config['range'][0] - 1
        zmax = threshold_config['range'][1] + 1
    elif threshold_config.get('inverse'):
        # Для CV - меньше лучше
        colorscale = [
            [0, COLORS['success']],
            [0.5, COLORS['warning']],
            [1, COLORS['danger']]
        ]
        zmin = 0
        zmax = threshold_config['threshold'] * 1.5
    else:
        # Для разрывной нагрузки - больше лучше
        colorscale = [
            [0, COLORS['danger']],
            [0.5, COLORS['warning']],
            [1, COLORS['success']]
        ]
        zmin = threshold_config['threshold'] * 0.85
        zmax = threshold_config['threshold'] * 1.15
    
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=[f"П{int(p)}" for p in parties],
        y=[f"М{int(m)}" for m in machines],
        hovertext=hover_text,
        hovertemplate="%{hovertext}<extra></extra>",
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        showscale=True,
        colorbar=dict(
            title=dict(text=title, font=dict(color=COLORS['text'])),
            tickfont=dict(color=COLORS['text_secondary']),
            bgcolor='rgba(0,0,0,0)'
        ),
        xgap=2,
        ygap=2
    ))
    
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=16, color=COLORS['text'], family=CHART_CONFIG['font_family']),
            x=0.5
        ),
        xaxis=dict(
            title="Партия",
            title_font=dict(color=COLORS['text_secondary'], size=12),
            tickfont=dict(color=COLORS['text_secondary'], size=10),
            side='bottom'
        ),
        yaxis=dict(
            title="Машина",
            title_font=dict(color=COLORS['text_secondary'], size=12),
            tickfont=dict(color=COLORS['text_secondary'], size=10),
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=60, l=60, r=20),
        height=400
    )
    
    return fig


def create_trend_chart(last_10_parties):
    """Создание графика тенденций с тёмной темой"""
    fig = go.Figure()
    
    x_raw = np.array(last_10_parties.index)
    y_values = last_10_parties['Относительная разрывная нагрузка, сН/текс'].values
    
    # Смещённые значения X для отображения (номер партии 2026 года)
    x_display = x_raw - 714

    if len(x_raw) == 0:
        fig.update_layout(
            title='Динамика разрывной нагрузки',
            height=400,
            plot_bgcolor=COLORS['background'],
            paper_bgcolor=COLORS['background']
        )
        return fig
    
    # Градиентная заливка под линией
    fig.add_trace(go.Scatter(
        x=x_display,
        y=y_values,
        fill='tozeroy',
        fillcolor='rgba(0, 212, 255, 0.1)',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Основная линия с точками и значениями
    fig.add_trace(go.Scatter(
        x=x_display,
        y=y_values,
        name='Разрывная нагрузка',
        line=dict(color=COLORS['primary'], width=3, shape='spline'),
        mode='lines+markers+text',
        marker=dict(
            size=12,
            color=COLORS['primary'],
            line=dict(color=COLORS['background'], width=2),
            symbol='circle'
        ),
        text=[f"{v:.1f}" for v in y_values],
        textposition='top center',
        textfont=dict(size=11, color=COLORS['text']),
        hovertemplate="Партия %{x}<br>Нагрузка: %{y:.1f} сН/текс<extra></extra>"
    ))
    
    if len(x_raw) > 1:
        # Линия тренда
        coefficients = np.polyfit(x_raw, y_values, 1)
        trend_line = np.poly1d(coefficients)
        y_trend = trend_line(x_raw)
        
        trend_direction = "↗" if coefficients[0] > 0 else "↘"
        trend_color = COLORS['success'] if coefficients[0] > 0 else COLORS['danger']
        
        fig.add_trace(go.Scatter(
            x=x_display,
            y=y_trend,
            name=f'Тренд {trend_direction}',
            line=dict(color=trend_color, width=2, dash='dash'),
            mode='lines',
            hoverinfo='skip'
        ))

    # Пороговая линия (используем смещённые x)
    fig.add_shape(
        type="line",
        x0=min(x_display), x1=max(x_display),
        y0=QUALITY_THRESHOLDS['strength_min'], 
        y1=QUALITY_THRESHOLDS['strength_min'],
        line=dict(color=COLORS['danger'], dash="dot", width=2)
    )
    
    fig.add_annotation(
        x=max(x_display), y=QUALITY_THRESHOLDS['strength_min'],
        text=f"Мин: {QUALITY_THRESHOLDS['strength_min']}",
        font=dict(color=COLORS['danger'], size=11),
        showarrow=False,
        xanchor='left',
        xshift=10
    )
    
    fig.update_layout(
        title=dict(
            text='<b>Динамика разрывной нагрузки</b>',
            font=dict(size=20, color=COLORS['text'], family=CHART_CONFIG['font_family']),
            x=0.5
        ),
        xaxis=dict(
            title='Партия 2026',
            title_font=dict(size=12, color=COLORS['text_secondary']),
            tickfont=dict(color=COLORS['text_secondary']),
            gridcolor=COLORS['grid'],
            showgrid=True,
            gridwidth=1,
            zeroline=False,
            range=[min(x_display) - 0.5, max(x_display) + 0.5],
            dtick=1
        ),
        yaxis=dict(
            range=[min(y_values) - 10, max(y_values) + 10],
            title='Разрывная нагрузка, сН/текс',
            title_font=dict(size=12, color=COLORS['text_secondary']),
            tickfont=dict(color=COLORS['text_secondary']),
            gridcolor=COLORS['grid'],
            showgrid=True,
            gridwidth=1,
            zeroline=False
        ),
        height=400,
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=80, b=60, l=60, r=80),
        showlegend=True,
        legend=dict(
            yanchor="top", y=0.99,
            xanchor="left", x=0.01,
            bgcolor='rgba(30, 41, 59, 0.8)',
            font=dict(color=COLORS['text'])
        )
    )
    
    return fig


def create_pie_chart(total, bad, title, good_label, bad_label):
    """Создание круговой диаграммы (legacy)"""
    colors = [COLORS['success'], COLORS['danger']]
    
    fig = go.Figure(data=[go.Pie(
        labels=[good_label, bad_label],
        values=[total - bad, bad],
        hole=.7,
        marker_colors=colors,
        textinfo='percent',
        textfont=dict(size=CHART_CONFIG['label_size'], family=CHART_CONFIG['font_family']),
        rotation=90
    )])
    
    fig.add_annotation(
        text=f"{total-bad}/{total}",
        x=0.5, y=0.5,
        font=dict(size=CHART_CONFIG['label_size'], color=COLORS['text'], family=CHART_CONFIG['font_family']),
        showarrow=False
    )
    
    fig.update_layout(
        title=dict(text=title, y=0.95, x=0.5, xanchor='center', yanchor='top',
                   font=dict(size=16, color=COLORS['text'], family=CHART_CONFIG['font_family'])),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, b=0, l=0, r=0),
        height=300, width=300, autosize=False
    )
    
    return fig




def create_problem_machines_chart(df, last_n_parties=10):
    """Топ проблемных машин - простой горизонтальный bar chart"""
    
    recent_parties = sorted(df['№ партии'].dropna().unique())[-last_n_parties:]
    recent_data = df[df['№ партии'].isin(recent_parties)]
    
    machines = recent_data['№ ПМ'].dropna().unique()
    problems = []
    
    for machine in machines:
        machine_data = recent_data[recent_data['№ ПМ'] == machine]
        
        low_strength = (machine_data['Относительная разрывная нагрузка, сН/текс'] < QUALITY_THRESHOLDS['strength_min']).sum()
        high_cv = (machine_data['Коэффициент вариации, %'] > QUALITY_THRESHOLDS['cv_max']).sum()
        
        total = low_strength + high_cv
        
        if total > 0:
            problems.append({
                'machine': f"М{int(machine)}",
                'total': total
            })
    
    problems = sorted(problems, key=lambda x: x['total'], reverse=True)[:10]
    
    if not problems:
        fig = go.Figure()
        fig.add_annotation(x=0.5, y=0.5, text="Все машины в норме",
            font=dict(size=18, color=COLORS['success']), showarrow=False, xref="paper", yref="paper")
        fig.update_layout(height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig
    
    machines_list = [p['machine'] for p in problems]
    values = [p['total'] for p in problems]
    colors = [COLORS['danger'] if v >= 4 else COLORS['warning'] if v >= 2 else COLORS['accent'] for v in values]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=machines_list, x=values, orientation='h', marker_color=colors,
        text=values, textposition='outside', textfont=dict(color=COLORS['text'], size=12),
        hovertemplate="<b>%{y}</b><br>Отклонений: %{x}<extra></extra>"
    ))
    
    fig.update_layout(
        title=dict(text='Проблемные машины', font=dict(size=16, color=COLORS['text']), x=0.5, xanchor='center'),
        xaxis=dict(title='Отклонений', title_font=dict(size=11, color=COLORS['text_secondary']),
            tickfont=dict(color=COLORS['text_secondary'], size=10), gridcolor=COLORS['grid'], showgrid=True),
        yaxis=dict(tickfont=dict(color=COLORS['text'], size=11), autorange='reversed'),
        height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=50, l=50, r=30), showlegend=False
    )
    
    return fig



def create_quality_scatter(df, party_number=None):
    """Scatter: Нагрузка vs CV - данные выбранной партии"""
    
    # Если партия не указана - берём последнюю
    if party_number is None:
        party_number = df['№ партии'].max()
    
    party_data = df[df['№ партии'] == party_number].copy()
    
    # Статус каждой машины
    def get_color(row):
        s_ok = row['Относительная разрывная нагрузка, сН/текс'] >= QUALITY_THRESHOLDS['strength_min']
        c_ok = row['Коэффициент вариации, %'] <= QUALITY_THRESHOLDS['cv_max']
        if s_ok and c_ok:
            return COLORS['success']
        elif s_ok or c_ok:
            return COLORS['warning']
        return COLORS['danger']
    
    party_data['color'] = party_data.apply(get_color, axis=1)
    
    fig = go.Figure()
    
    # Зона нормы (зелёная)
    fig.add_shape(type="rect",
        x0=QUALITY_THRESHOLDS['strength_min'], x1=350, y0=0, y1=QUALITY_THRESHOLDS['cv_max'],
        fillcolor="rgba(16, 185, 129, 0.15)", line=dict(width=0), layer="below")
    
    # Зона критично (красная)
    fig.add_shape(type="rect",
        x0=200, x1=QUALITY_THRESHOLDS['strength_min'], y0=QUALITY_THRESHOLDS['cv_max'], y1=20,
        fillcolor="rgba(239, 68, 68, 0.15)", line=dict(width=0), layer="below")
    
    # Пороговые линии
    fig.add_vline(x=QUALITY_THRESHOLDS['strength_min'], line=dict(color=COLORS['danger'], dash='dash', width=1.5))
    fig.add_hline(y=QUALITY_THRESHOLDS['cv_max'], line=dict(color=COLORS['danger'], dash='dash', width=1.5))
    
    # Точки машин
    fig.add_trace(go.Scatter(
        x=party_data['Относительная разрывная нагрузка, сН/текс'],
        y=party_data['Коэффициент вариации, %'],
        mode='markers',
        marker=dict(size=12, color=party_data['color'], line=dict(width=1, color=COLORS['background'])),
        text=[f"М{int(m)}" for m in party_data['№ ПМ']],
        textposition='top center',
        textfont=dict(size=8, color=COLORS['text']),
        hovertemplate="<b>Машина %{text}</b><br>Нагрузка: %{x:.1f} сН/текс<br>CV: %{y:.1f}%<extra></extra>"
    ))
    
    # Считаем статистику
    good_count = (party_data['color'] == COLORS['success']).sum()
    warn_count = (party_data['color'] == COLORS['warning']).sum()
    bad_count = (party_data['color'] == COLORS['danger']).sum()
    
    fig.update_layout(
        title=dict(
            text=f'Карта качества (партия {int(party_number) - 714})',
            font=dict(size=16, color=COLORS['text']),
            x=0.5, xanchor='center'
        ),
        xaxis=dict(
            title='Разрывная нагрузка, сН/текс',
            title_font=dict(size=11, color=COLORS['text_secondary']),
            tickfont=dict(color=COLORS['text_secondary'], size=10),
            gridcolor=COLORS['grid'],
            showgrid=True,
            range=[min(party_data['Относительная разрывная нагрузка, сН/текс'].min() - 5, 250), 
                   max(party_data['Относительная разрывная нагрузка, сН/текс'].max() + 5, 310)],
        ),
        yaxis=dict(
            title='CV, % (меньше лучше)',
            title_font=dict(size=11, color=COLORS['text_secondary']),
            tickfont=dict(color=COLORS['text_secondary'], size=10),
            gridcolor=COLORS['grid'],
            showgrid=True,
            range=[0, max(party_data['Коэффициент вариации, %'].max() + 2, 12)],
        ),
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=50, l=50, r=30),
        showlegend=False,
        annotations=[
            dict(x=0.02, y=0.98, xref='paper', yref='paper', showarrow=False,
                 text=f"✅ {good_count}  ⚠️ {warn_count}  ❌ {bad_count}",
                 font=dict(size=11, color=COLORS['text']),
                 bgcolor=COLORS['card'], borderpad=4)
        ]
    )
    
    return fig




def create_sparkline(values, parties, metric_type='strength', height=50):
    """Компактный мини-график без подписей"""
    
    if len(values) == 0:
        return None
    
    mean_val = np.mean(values)
    
    # Настройки по типу метрики
    if metric_type == 'strength':
        threshold = QUALITY_THRESHOLDS['strength_min']
        colors = [COLORS['success'] if v >= mean_val else COLORS['danger'] if v < threshold else COLORS['warning'] for v in values]
        y_range = [min(min(values) - 10, 250), max(max(values) + 10, 300)]
    elif metric_type == 'cv':
        threshold = QUALITY_THRESHOLDS['cv_max']
        colors = [COLORS['success'] if v <= mean_val else COLORS['danger'] if v > threshold else COLORS['warning'] for v in values]
        y_range = [0, max(max(values) + 2, 12)]
    else:
        thresh_min, thresh_max = QUALITY_THRESHOLDS['density_range']
        colors = [COLORS['success'] if thresh_min <= v <= thresh_max else COLORS['danger'] for v in values]
        y_range = [min(min(values) - 0.5, 27.5), max(max(values) + 0.5, 30)]
    
    fig = go.Figure()
    
    # Только линия и точки
    fig.add_trace(go.Scatter(
        x=list(range(len(values))),
        y=values,
        mode='lines+markers',
        line=dict(color=COLORS['text_secondary'], width=1),
        marker=dict(size=5, color=colors),
        hoverinfo='skip',
        showlegend=False
    ))
    
    # Красная линия порога
    if metric_type == 'density':
        thresh_min, thresh_max = QUALITY_THRESHOLDS['density_range']
        fig.add_hline(y=thresh_min, line=dict(color=COLORS['danger'], width=1, dash='dot'))
        fig.add_hline(y=thresh_max, line=dict(color=COLORS['danger'], width=1, dash='dot'))
    else:
        fig.add_hline(y=threshold, line=dict(color=COLORS['danger'], width=1, dash='dot'))
    
    # Зелёная линия среднего
    fig.add_hline(y=mean_val, line=dict(color=COLORS['success'], width=1))
    
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=y_range),
        height=height,
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    
    return fig


def create_plastification_comparison(df, last_n_parties=10):
    """Сравнение прочности - Strip plot с точками и линией среднего"""
    stretch_col = 'Пласт. вытяжка, %'

    if stretch_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(x=0.5, y=0.5, text="Колонка не найдена", font=dict(size=16, color=COLORS['warning']), showarrow=False, xref="paper", yref="paper")
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig, None

    recent_parties = sorted(df['№ партии'].dropna().unique())[-last_n_parties:]
    recent_data = df[df['№ партии'].isin(recent_parties)].copy()
    recent_data[stretch_col] = pd.to_numeric(recent_data[stretch_col], errors='coerce')

    data_60 = recent_data[recent_data[stretch_col] == 60]['Относительная разрывная нагрузка, сН/текс'].dropna()
    data_65 = recent_data[recent_data[stretch_col] == 65]['Относительная разрывная нагрузка, сН/текс'].dropna()

    if len(data_60) == 0 and len(data_65) == 0:
        fig = go.Figure()
        fig.add_annotation(x=0.5, y=0.5, text="Нет данных", font=dict(size=16, color=COLORS['warning']), showarrow=False, xref="paper", yref="paper")
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig, None

    stats = {}
    fig = go.Figure()

    # Точки для 60%
    if len(data_60) > 0:
        stats['60%'] = {'mean': data_60.mean(), 'std': data_60.std(), 'count': len(data_60)}
        jitter_60 = np.random.uniform(-0.15, 0.15, len(data_60))
        fig.add_trace(go.Scatter(
            x=jitter_60,
            y=data_60.values,
            mode='markers',
            name='60%',
            marker=dict(color=COLORS['primary'], size=8, opacity=0.6, line=dict(width=1, color='white')),
            hovertemplate="60%%<br>Нагрузка: %{y:.1f}<extra></extra>"
        ))
        # Линия среднего для 60%
        fig.add_shape(type="line", x0=-0.3, x1=0.3, y0=data_60.mean(), y1=data_60.mean(),
            line=dict(color=COLORS['primary'], width=3))
        fig.add_annotation(x=0, y=data_60.mean(), text=f"<b>{data_60.mean():.1f}</b>",
            showarrow=False, yshift=15, font=dict(size=14, color=COLORS['primary']))

    # Точки для 65%
    if len(data_65) > 0:
        stats['65%'] = {'mean': data_65.mean(), 'std': data_65.std(), 'count': len(data_65)}
        jitter_65 = np.random.uniform(0.85, 1.15, len(data_65))
        fig.add_trace(go.Scatter(
            x=jitter_65,
            y=data_65.values,
            mode='markers',
            name='65%',
            marker=dict(color=COLORS['secondary'], size=8, opacity=0.6, line=dict(width=1, color='white')),
            hovertemplate="65%%<br>Нагрузка: %{y:.1f}<extra></extra>"
        ))
        # Линия среднего для 65%
        fig.add_shape(type="line", x0=0.7, x1=1.3, y0=data_65.mean(), y1=data_65.mean(),
            line=dict(color=COLORS['secondary'], width=3))
        fig.add_annotation(x=1, y=data_65.mean(), text=f"<b>{data_65.mean():.1f}</b>",
            showarrow=False, yshift=15, font=dict(size=14, color=COLORS['secondary']))

    # Пороговая линия
    fig.add_hline(y=QUALITY_THRESHOLDS['strength_min'], line=dict(color=COLORS['danger'], dash='dash', width=2),
        annotation_text=f"Мин: {QUALITY_THRESHOLDS['strength_min']}", annotation_position="right",
        annotation_font=dict(color=COLORS['danger'], size=11))

    # Разница
    diff_text = ""
    if '60%' in stats and '65%' in stats:
        diff = stats['65%']['mean'] - stats['60%']['mean']
        diff_text = f"Разница: {'+' if diff > 0 else ''}{diff:.1f} сН/текс"

    fig.update_layout(
        title=dict(text=f'<b>Прочность: вытяжка 60% vs 65%</b><br><span style="font-size:12px;color:#94a3b8">{diff_text}</span>',
            font=dict(size=16, color=COLORS['text']), x=0.5),
        xaxis=dict(
            tickmode='array', tickvals=[0, 1], ticktext=['Вытяжка 60%', 'Вытяжка 65%'],
            tickfont=dict(size=13, color=COLORS['text']), range=[-0.5, 1.5], showgrid=False
        ),
        yaxis=dict(title='Разрывная нагрузка, сН/текс', gridcolor=COLORS['grid'],
            title_font=dict(size=11, color=COLORS['text_secondary']),
            tickfont=dict(color=COLORS['text_secondary'])),
        height=420,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        annotations=[
            dict(x=0, y=-0.12, xref='paper', yref='paper', text=f"n={stats.get('60%', {}).get('count', 0)}", showarrow=False, font=dict(size=11, color=COLORS['text_secondary'])),
            dict(x=1, y=-0.12, xref='paper', yref='paper', text=f"n={stats.get('65%', {}).get('count', 0)}", showarrow=False, font=dict(size=11, color=COLORS['text_secondary']))
        ] if stats else []
    )

    return fig, stats


def create_cv_plastification_comparison(df, last_n_parties=10):
    """Сравнение CV - Strip plot с точками и линией среднего"""
    stretch_col = 'Пласт. вытяжка, %'

    if stretch_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(x=0.5, y=0.5, text="Колонка не найдена", font=dict(size=16, color=COLORS['warning']), showarrow=False, xref="paper", yref="paper")
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig, None

    recent_parties = sorted(df['№ партии'].dropna().unique())[-last_n_parties:]
    recent_data = df[df['№ партии'].isin(recent_parties)].copy()
    recent_data[stretch_col] = pd.to_numeric(recent_data[stretch_col], errors='coerce')

    data_60 = recent_data[recent_data[stretch_col] == 60]['Коэффициент вариации, %'].dropna()
    data_65 = recent_data[recent_data[stretch_col] == 65]['Коэффициент вариации, %'].dropna()

    if len(data_60) == 0 and len(data_65) == 0:
        fig = go.Figure()
        fig.add_annotation(x=0.5, y=0.5, text="Нет данных", font=dict(size=16, color=COLORS['warning']), showarrow=False, xref="paper", yref="paper")
        fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        return fig, None

    stats = {}
    fig = go.Figure()

    # Точки для 60%
    if len(data_60) > 0:
        stats['60%'] = {'mean': data_60.mean(), 'std': data_60.std(), 'count': len(data_60)}
        jitter_60 = np.random.uniform(-0.15, 0.15, len(data_60))
        fig.add_trace(go.Scatter(
            x=jitter_60,
            y=data_60.values,
            mode='markers',
            name='60%',
            marker=dict(color=COLORS['primary'], size=8, opacity=0.6, line=dict(width=1, color='white')),
            hovertemplate="60%%<br>CV: %{y:.1f}%<extra></extra>"
        ))
        # Линия среднего для 60%
        fig.add_shape(type="line", x0=-0.3, x1=0.3, y0=data_60.mean(), y1=data_60.mean(),
            line=dict(color=COLORS['primary'], width=3))
        fig.add_annotation(x=0, y=data_60.mean(), text=f"<b>{data_60.mean():.1f}</b>",
            showarrow=False, yshift=-15, font=dict(size=14, color=COLORS['primary']))

    # Точки для 65%
    if len(data_65) > 0:
        stats['65%'] = {'mean': data_65.mean(), 'std': data_65.std(), 'count': len(data_65)}
        jitter_65 = np.random.uniform(0.85, 1.15, len(data_65))
        fig.add_trace(go.Scatter(
            x=jitter_65,
            y=data_65.values,
            mode='markers',
            name='65%',
            marker=dict(color=COLORS['secondary'], size=8, opacity=0.6, line=dict(width=1, color='white')),
            hovertemplate="65%%<br>CV: %{y:.1f}%<extra></extra>"
        ))
        # Линия среднего для 65%
        fig.add_shape(type="line", x0=0.7, x1=1.3, y0=data_65.mean(), y1=data_65.mean(),
            line=dict(color=COLORS['secondary'], width=3))
        fig.add_annotation(x=1, y=data_65.mean(), text=f"<b>{data_65.mean():.1f}</b>",
            showarrow=False, yshift=-15, font=dict(size=14, color=COLORS['secondary']))

    # Пороговая линия (максимальный допустимый CV)
    fig.add_hline(y=QUALITY_THRESHOLDS['cv_max'], line=dict(color=COLORS['danger'], dash='dash', width=2),
        annotation_text=f"Макс: {QUALITY_THRESHOLDS['cv_max']}", annotation_position="right",
        annotation_font=dict(color=COLORS['danger'], size=11))

    # Разница
    diff_text = ""
    if '60%' in stats and '65%' in stats:
        diff = stats['65%']['mean'] - stats['60%']['mean']
        diff_text = f"Разница: {'+' if diff > 0 else ''}{diff:.2f}%"

    fig.update_layout(
        title=dict(text=f'<b>Коэф. вариации: вытяжка 60% vs 65%</b><br><span style="font-size:12px;color:#94a3b8">{diff_text}</span>',
            font=dict(size=16, color=COLORS['text']), x=0.5),
        xaxis=dict(
            tickmode='array', tickvals=[0, 1], ticktext=['Вытяжка 60%', 'Вытяжка 65%'],
            tickfont=dict(size=13, color=COLORS['text']), range=[-0.5, 1.5], showgrid=False
        ),
        yaxis=dict(title='Коэф. вариации, %', gridcolor=COLORS['grid'],
            title_font=dict(size=11, color=COLORS['text_secondary']),
            tickfont=dict(color=COLORS['text_secondary']),
            range=[0, max(data_60.max() if len(data_60) > 0 else 10, data_65.max() if len(data_65) > 0 else 10) + 2]),
        height=420,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        annotations=[
            dict(x=0, y=-0.12, xref='paper', yref='paper', text=f"n={stats.get('60%', {}).get('count', 0)}", showarrow=False, font=dict(size=11, color=COLORS['text_secondary'])),
            dict(x=1, y=-0.12, xref='paper', yref='paper', text=f"n={stats.get('65%', {}).get('count', 0)}", showarrow=False, font=dict(size=11, color=COLORS['text_secondary']))
        ] if stats else []
    )

    return fig, stats
