"""Синтетические данные в формате листа «СтатПряд2025» для тестов.

Детерминированы (фиксированный seed), содержат обе крутки, номера ВТВ,
пластификационную вытяжку и несколько «проблемных» машин, чтобы задействовать
ветки с алертами.
"""
import numpy as np
import pandas as pd


def make_df(n_parties_100=30, n_parties_50=40, machines=36, seed=7):
    rng = np.random.default_rng(seed)
    rows = []

    def add(party, twist, base):
        polymer = rng.normal(0, 3)
        for pm in range(1, machines + 1):
            weak = 12 if pm in (5, 17) else 0
            rows.append({
                'Месяц': 46000 + party // 10,
                '№ партии': party,
                '№ ПМ': pm,
                'Скорость формования, м/мин': float(rng.choice([12.5, 18.8])),
                'Относительная разрывная нагрузка, сН/текс': int(round(base + polymer - weak + rng.normal(0, 6))),
                'Коэффициент вариации, %': round(float(abs(rng.normal(6.5, 1.5))) + (2.5 if pm == 9 else 0), 1),
                'Линейная плотность, текс': round(float(rng.normal(28.9, 0.35)), 1),
                'Проблема': 0,
                'Крутка': twist,
                'Пласт. вытяжка, %': 60 if pm % 2 else 65,
                'Количество витков на сушильном цилиндре, шт': 14,
                '№ ВТВ': str(int(rng.integers(1, 20))) if twist == 50 else '',
                'Конфигурация ПМ, кол-во мест, шт.': '36',
            })

    for p in range(715, 715 + n_parties_100):
        add(p, 100, 278)
    for p in range(846, 846 + n_parties_50):
        add(p, 50, 266)
    return pd.DataFrame(rows)
