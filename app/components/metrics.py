import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import COLORS, QUALITY_THRESHOLDS
import streamlit as st

def calculate_party_metrics(party_data):
    """Расчет метрик для партии"""
    strength_min = QUALITY_THRESHOLDS['strength_min']
    cv_max = QUALITY_THRESHOLDS['cv_max']
    density_min, density_max = QUALITY_THRESHOLDS['density_range']
    
    metrics = {
        'avg_strength': round(party_data['Относительная разрывная нагрузка, сН/текс'].mean(), 1),
        'avg_cv': round(party_data['Коэффициент вариации, %'].mean(), 1),
        'avg_density': round(party_data['Линейная плотность, текс'].mean(), 2) if 'Линейная плотность, текс' in party_data.columns else 0,
        'total_machines': len(party_data),
        'low_strength_count': len(party_data[
            party_data['Относительная разрывная нагрузка, сН/текс'] < strength_min
        ]),
        'high_cv_count': len(party_data[
            party_data['Коэффициент вариации, %'] > cv_max
        ]),
        'bad_density_count': len(party_data[
            (party_data['Линейная плотность, текс'] < density_min) |
            (party_data['Линейная плотность, текс'] > density_max)
        ]) if 'Линейная плотность, текс' in party_data.columns else 0
    }
    return metrics


def get_status_indicator(value, threshold, mode='greater'):
    """Создание индикатора статуса с новым дизайном"""
    if pd.isna(value):
        return f'<span class="status-indicator" style="color: {COLORS["muted"]};">◯</span>'
    
    if mode == 'greater':
        is_good = value >= threshold
    elif mode == 'less':
        is_good = value <= threshold
    elif mode == 'range':
        min_val, max_val = threshold
        is_good = min_val <= value <= max_val
    else:
        is_good = True
    
    if is_good:
        return f'<span style="color: {COLORS["success"]}; font-size: 20px; text-shadow: 0 0 10px {COLORS["success"]};">●</span>'
    else:
        return f'<span style="color: {COLORS["danger"]}; font-size: 20px; text-shadow: 0 0 10px {COLORS["danger"]};">●</span>'


def get_quality_score(party_data):
    """Расчёт общего индекса качества партии (0-100)"""
    metrics = calculate_party_metrics(party_data)
    
    # Веса для каждого показателя
    weights = {'strength': 0.4, 'cv': 0.35, 'density': 0.25}
    
    # Расчёт баллов
    strength_score = min(100, max(0, (metrics['avg_strength'] - 200) / (350 - 200) * 100))
    cv_score = min(100, max(0, (15 - metrics['avg_cv']) / 15 * 100))
    
    if metrics['avg_density'] > 0:
        center = sum(QUALITY_THRESHOLDS['density_range']) / 2
        deviation = abs(metrics['avg_density'] - center)
        density_score = max(0, 100 - deviation * 50)
    else:
        density_score = 50
    
    total_score = (
        strength_score * weights['strength'] +
        cv_score * weights['cv'] +
        density_score * weights['density']
    )
    
    return round(total_score, 1)
