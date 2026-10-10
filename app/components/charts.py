import plotly.graph_objects as go
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import COLORS, CHART_CONFIG, QUALITY_THRESHOLDS, TWIST100_PARTY_OFFSET
import numpy as np


def create_trend_chart(last_10_parties, df=None, speed_col=None, strength_min=None, party_offset=TWIST100_PARTY_OFFSET):
    """Создание графика тенденций с разделением по скоростям"""
    fig = go.Figure()
    
    x_raw = np.array(last_10_parties.index)
    y_values = last_10_parties['Относительная разрывная нагрузка, сН/текс'].values
    
    # Смещённые значения X для отображения (номер партии 2026 года)
    x_display = x_raw - party_offset

    if len(x_raw) == 0:
        fig.update_layout(
            title='Динамика разрывной нагрузки',
            height=550,
            plot_bgcolor=COLORS['background'],
            paper_bgcolor=COLORS['background']
        )
        return fig
    
    # Если есть данные по скоростям — рисуем раздельно
    if df is not None and speed_col is not None:
        parties_list = last_10_parties.index.tolist()
        
        speed_configs = {
            188: {'name': '18,8 м/мин', 'color': '#06b6d4', 'symbol': 'circle'},
            164: {'name': '16,4 м/мин', 'color': '#f59e0b', 'symbol': 'square'},
            203: {'name': '20,3 м/мин', 'color': '#a78bfa', 'symbol': 'diamond'},
        }
        
        speed_values = sorted(df[speed_col].dropna().unique())
        
        for speed_val in speed_values:
            speed_data = df[(df['№ партии'].isin(parties_list)) & (df[speed_col] == speed_val)]
            if len(speed_data) == 0:
                continue
            
            grouped = speed_data.groupby('№ партии')['Относительная разрывная нагрузка, сН/текс'].mean()
            
            x_s = np.array(grouped.index)
            y_s = grouped.values
            x_s_display = x_s - party_offset
            
            config = speed_configs.get(int(speed_val), {'name': f'{speed_val}', 'color': '#94a3b8', 'symbol': 'circle'})
            mean_val = np.mean(y_s)
            
            # Основная линия с точками и значениями
            fig.add_trace(go.Scatter(
                x=x_s_display,
                y=y_s,
                name=config['name'],
                line=dict(color=config['color'], width=3),
                mode='lines+markers+text',
                marker=dict(size=10, color=config['color'], symbol=config['symbol'],
                    line=dict(color=COLORS['background'], width=2)),
                text=[f"{v:.1f}" for v in y_s],
                textposition='top center',
                textfont=dict(size=10, color=config['color']),
                hovertemplate=f"<b>{config['name']}</b><br>Партия %{{x}}<br>Нагрузка: %{{y:.1f}}<extra></extra>"
            ))
            
            # Линия среднего
            fig.add_shape(
                type="line",
                x0=min(x_s_display) - 0.3, x1=max(x_s_display) + 0.3,
                y0=mean_val, y1=mean_val,
                line=dict(color=config['color'], width=1.5, dash='dot'),
            )
            fig.add_annotation(
                x=max(x_s_display) + 0.5, y=mean_val,
                text=f"μ={mean_val:.1f}",
                font=dict(color=config['color'], size=10),
                showarrow=False, xanchor='left'
            )
            
            # Линия тренда
            if len(x_s) > 1:
                coefficients = np.polyfit(x_s, y_s, 1)
                trend_line = np.poly1d(coefficients)
                y_trend = trend_line(x_s)
                
                trend_direction = "↗" if coefficients[0] > 0 else "↘"
                
                fig.add_trace(go.Scatter(
                    x=x_s_display,
                    y=y_trend,
                    name=f'Тренд {config["name"]} {trend_direction}',
                    line=dict(color=config['color'], width=2, dash='dash'),
                    mode='lines',
                    showlegend=False,
                    hoverinfo='skip'
                ))
    else:
        # Градиентная заливка
        fig.add_trace(go.Scatter(
            x=x_display, y=y_values,
            fill='tozeroy', fillcolor='rgba(0, 212, 255, 0.1)',
            line=dict(color='rgba(0,0,0,0)'), showlegend=False, hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=x_display, y=y_values,
            name='Разрывная нагрузка',
            line=dict(color=COLORS['primary'], width=3, shape='spline'),
            mode='lines+markers+text',
            marker=dict(size=12, color=COLORS['primary'],
                line=dict(color=COLORS['background'], width=2), symbol='circle'),
            text=[f"{v:.1f}" for v in y_values],
            textposition='top center',
            textfont=dict(size=11, color=COLORS['text']),
            hovertemplate="Партия %{x}<br>Нагрузка: %{y:.1f} сН/текс<extra></extra>"
        ))

    # Пороговая линия
    _strength_min = strength_min if strength_min is not None else QUALITY_THRESHOLDS['strength_min']
    fig.add_shape(
        type="line",
        x0=min(x_display) - 0.5, x1=max(x_display) + 0.5,
        y0=_strength_min, 
        y1=_strength_min,
        line=dict(color=COLORS['danger'], dash="dot", width=2)
    )
    
    fig.add_annotation(
        x=max(x_display), y=_strength_min,
        text=f"Мин: {_strength_min}",
        font=dict(color=COLORS['danger'], size=11),
        showarrow=False,
        xanchor='left',
        xshift=10
    )
    
    fig.update_layout(
        title=dict(
            text='<b>Динамика разрывной нагрузки по скоростям</b>',
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
            range=[min(x_display) - 0.5, max(x_display) + 1.5],
            dtick=1
        ),
        yaxis=dict(
            title='Разрывная нагрузка, сН/текс',
            title_font=dict(size=12, color=COLORS['text_secondary']),
            tickfont=dict(color=COLORS['text_secondary']),
            gridcolor=COLORS['grid'],
            showgrid=True,
            gridwidth=1,
            zeroline=False
        ),
        height=550,
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=80, b=60, l=60, r=100),
        showlegend=True,
        legend=dict(
            yanchor="top", y=0.99,
            xanchor="left", x=0.01,
            bgcolor='rgba(30, 41, 59, 0.8)',
            font=dict(color=COLORS['text'])
        )
    )
    
    return fig


def create_problem_machines_chart(df, last_n_parties=10, strength_min=None):
    """Топ проблемных машин - простой горизонтальный bar chart"""
    
    recent_parties = sorted(df['№ партии'].dropna().unique())[-last_n_parties:]
    recent_data = df[df['№ партии'].isin(recent_parties)]
    
    machines = recent_data['№ ПМ'].dropna().unique()
    problems = []
    
    for machine in machines:
        machine_data = recent_data[recent_data['№ ПМ'] == machine]
        
        _s_min = strength_min if strength_min is not None else QUALITY_THRESHOLDS['strength_min']
        low_strength = (machine_data['Относительная разрывная нагрузка, сН/текс'] < _s_min).sum()
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



def create_quality_scatter(df, party_number=None, strength_min=None, party_offset=TWIST100_PARTY_OFFSET):
    """Scatter: Нагрузка vs CV - данные выбранной партии"""
    
    # Если партия не указана - берём последнюю
    if party_number is None:
        party_number = df['№ партии'].max()
    
    _strength_min = strength_min if strength_min is not None else QUALITY_THRESHOLDS['strength_min']

    party_data = df[df['№ партии'] == party_number].copy()
    
    # Статус каждой машины
    def get_color(row):
        s_ok = row['Относительная разрывная нагрузка, сН/текс'] >= _strength_min
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
        x0=_strength_min, x1=350, y0=0, y1=QUALITY_THRESHOLDS['cv_max'],
        fillcolor="rgba(16, 185, 129, 0.15)", line=dict(width=0), layer="below")
    
    # Зона критично (красная)
    fig.add_shape(type="rect",
        x0=200, x1=_strength_min, y0=QUALITY_THRESHOLDS['cv_max'], y1=20,
        fillcolor="rgba(239, 68, 68, 0.15)", line=dict(width=0), layer="below")
    
    # Пороговые линии
    fig.add_vline(x=_strength_min, line=dict(color=COLORS['danger'], dash='dash', width=1.5))
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
            text=f'Карта качества (партия {int(party_number) - party_offset})',
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



