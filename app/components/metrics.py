import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import QUALITY_THRESHOLDS

def calculate_party_metrics(party_data, thresholds=None):
    """Расчет метрик для партии"""
    if thresholds is None:
        thresholds = QUALITY_THRESHOLDS
    strength_min = thresholds['strength_min']
    cv_max = thresholds['cv_max']
    density_min, density_max = thresholds['density_range']
    
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

