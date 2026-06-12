"""Паспорт машин: накопительные характеристики и автоматический диагноз.

Логика диагнозов:
- «обслуживание»     — низкая прочность И высокий CV одновременно
- «техсостояние»     — устойчиво низкая прочность при нормальном CV
- «кручение/намотка» — только высокий CV (натяжение, бегунок, веретено)
- «деградация»       — показатели в норме, но устойчивый тренд вниз
- «норма»            — всё в порядке

Прочность машины оценивается по отклонению от среднего партии —
это очищает оценку от влияния полимера.
"""
import numpy as np
import pandas as pd

STRENGTH_COL = 'Относительная разрывная нагрузка, сН/текс'
CV_COL = 'Коэффициент вариации, %'

# Пороги диагностики (сН/текс, %, доли)
DEV_LOW = -1.5        # отклонение от среднего партии: ниже = «низкая прочность»
CV_WARN = 8.0         # предупредительный уровень CV (норма 10)
STABLE_SHARE = 0.6    # доля партий окна в минусе, чтобы считать «устойчиво»
TREND_DELTA = 2.5     # сдвиг последних 5 партий vs предыдущих = «тренд» (ниже — шум)
RECENT_ACTIVE = 5     # активна = была хотя бы в одной из последних N партий

DIAG_ICON = {
    'обслуживание': '🔴',
    'техсостояние': '🟠',
    'кручение/намотка': '🟡',
    'деградация': '🔵',
    'норма': '🟢',
}
DIAG_ORDER = {'обслуживание': 0, 'техсостояние': 1, 'кручение/намотка': 2, 'деградация': 3, 'норма': 4}


def compute_registry(df, n_parties, thresholds):
    """Сводная ведомость: одна строка на машину за окно из n_parties партий."""
    smin = thresholds['strength_min']
    cvmax = thresholds['cv_max']

    parties = sorted(df['№ партии'].dropna().unique())
    window = parties[-n_parties:] if n_parties else parties
    recent_parties = set(parties[-RECENT_ACTIVE:])

    d = df[df['№ партии'].isin(window)].copy()
    d['dev'] = d[STRENGTH_COL] - d.groupby('№ партии')[STRENGTH_COL].transform('mean')
    active_machines = set(d[d['№ партии'].isin(recent_parties)]['№ ПМ'].dropna().unique())

    rows = []
    for pm, g in d.groupby('№ ПМ'):
        by_party = g.groupby('№ партии').agg(
            dev=('dev', 'mean'), cv=(CV_COL, 'mean')).sort_index()
        n_p = len(by_party)
        if n_p == 0:
            continue
        n_meas = len(g)
        mean_dev = float(g['dev'].mean())
        mean_s = float(g[STRENGTH_COL].mean())
        mean_cv = float(g[CV_COL].mean())
        fail_n = int((g[STRENGTH_COL] < smin).sum())
        cvfail_n = int((g[CV_COL] > cvmax).sum())
        neg_share = float((by_party['dev'] < 0).mean())

        # Тренд: последние 5 партий присутствия vs предыдущие
        if n_p >= 8:
            trend_diff = float(by_party['dev'].iloc[-5:].mean() - by_party['dev'].iloc[:-5].mean())
        else:
            trend_diff = None

        low_strength = mean_dev <= DEV_LOW and neg_share >= STABLE_SHARE
        high_cv = mean_cv > CV_WARN
        trend_down = trend_diff is not None and trend_diff <= -TREND_DELTA

        if low_strength and high_cv:
            diag = 'обслуживание'
        elif low_strength:
            diag = 'техсостояние'
        elif high_cv:
            diag = 'кручение/намотка'
        elif trend_down:
            diag = 'деградация'
        else:
            diag = 'норма'

        # Индекс здоровья 0–100
        score = 100.0
        if mean_dev < 0:
            score += mean_dev * 8
        if mean_cv > CV_WARN:
            score -= (mean_cv - CV_WARN) * 8
        score -= fail_n / n_meas * 100 * 0.6
        score -= cvfail_n / n_meas * 100 * 0.3
        if trend_down:
            score -= 10
        score = float(np.clip(score, 0, 100))

        rows.append({
            'машина': int(pm),
            'активна': pm in active_machines,
            'партий': n_p,
            'измерений': n_meas,
            'прочность_средняя': round(mean_s, 1),
            'откл_от_партии': round(mean_dev, 2),
            'cv_средний': round(mean_cv, 1),
            'ниже_нормы_шт': fail_n,
            'ниже_нормы_%': round(fail_n / n_meas * 100, 1),
            'cv_выше_нормы_шт': cvfail_n,
            'cv_выше_нормы_%': round(cvfail_n / n_meas * 100, 1),
            'тренд': round(trend_diff, 2) if trend_diff is not None else None,
            'диагноз': diag,
            'здоровье': round(score, 0),
        })

    reg = pd.DataFrame(rows)
    if reg.empty:
        return reg
    reg['_diag_order'] = reg['диагноз'].map(DIAG_ORDER)
    reg = reg.sort_values(['активна', '_diag_order', 'здоровье'],
                          ascending=[False, True, True]).drop(columns='_diag_order')
    return reg.reset_index(drop=True)


def machine_history(df, pm, n_parties):
    """История машины по партиям: прочность, отклонение, CV."""
    parties = sorted(df['№ партии'].dropna().unique())
    window = parties[-n_parties:] if n_parties else parties
    d = df[df['№ партии'].isin(window)].copy()
    d['dev'] = d[STRENGTH_COL] - d.groupby('№ партии')[STRENGTH_COL].transform('mean')
    g = d[d['№ ПМ'] == pm]
    return g.groupby('№ партии').agg(
        s=(STRENGTH_COL, 'mean'),
        dev=('dev', 'mean'),
        cv=(CV_COL, 'mean'),
        n=(STRENGTH_COL, 'count'),
    ).sort_index().reset_index()
