import numpy as np
import pandas as pd

from components.spc import calc_xbar_r_data, calc_xmr_data, detect_out_of_control, get_shewhart_constants
from components.metrics import calculate_party_metrics
from utils.constants import QUALITY_THRESHOLDS_50


def test_point_beyond_limits():
    sig = detect_out_of_control([0, 0, 5, 0], cl=0, ucl=3, lcl=-3)
    assert 'За контр. границей (3σ)' in sig[2]
    assert set(sig) == {2}


def test_nine_points_below_center():
    sig = detect_out_of_control([-1] * 9, cl=0, ucl=3, lcl=-3)
    assert all('9 точек ниже CL' in sig[i] for i in range(9))


def test_trend_six_points():
    sig = detect_out_of_control([0, 0.1, 0.2, 0.3, 0.4, 0.5], cl=0.25, ucl=3, lcl=-3)
    assert 'Тренд ↗ (6 точек)' in sig[5]


def test_stable_process_has_no_signals():
    assert detect_out_of_control([0.5, -0.5] * 10, cl=0, ucl=3, lcl=-3) == {}


def test_shewhart_constants_lookup():
    assert get_shewhart_constants(5)[0] == 0.577
    assert get_shewhart_constants(1) == get_shewhart_constants(2)
    assert get_shewhart_constants(40) == get_shewhart_constants(25)


def _df(parties, values_per_party):
    rows = [{'№ партии': p, '№ ПМ': i + 1, 'X': v}
            for p, vals in zip(parties, values_per_party) for i, v in enumerate(vals)]
    return pd.DataFrame(rows)


def test_xbar_r_applies_offset_and_limits():
    df = _df([846, 847, 848], [[1, 3], [2, 4], [3, 5]])
    d = calc_xbar_r_data(df, 'X', offset=845)
    assert d['party_labels'] == [1, 2, 3]
    assert np.allclose(d['x_bars'], [2, 3, 4])
    assert d['r_bar'] == 2
    assert np.isclose(d['x_ucl'], 3 + 1.880 * 2)


def test_xbar_r_needs_three_subgroups():
    assert calc_xbar_r_data(_df([1, 2], [[1, 2], [3, 4]]), 'X') is None


def test_xmr_for_machine():
    df = _df([10, 11, 12, 13, 14], [[1], [2], [4], [3], [5]])
    d = calc_xmr_data(df, 1, 'X', offset=9)
    assert d is not None
    assert list(d['party_labels']) == [1, 2, 3, 4, 5]


def test_party_metrics_counts_out_of_spec():
    party = pd.DataFrame({
        'Относительная разрывная нагрузка, сН/текс': [255, 262, 270],
        'Коэффициент вариации, %': [7.0, 9.5, 8.0],
        'Линейная плотность, текс': [28.0, 28.9, 29.6],
    })
    m = calculate_party_metrics(party, thresholds=QUALITY_THRESHOLDS_50)
    assert m['low_strength_count'] == 1
    assert m['high_cv_count'] == 1
    assert m['bad_density_count'] == 2
    assert m['avg_strength'] == 262.3
