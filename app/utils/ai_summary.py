"""Диагностический движок + генерация технологической сводки через OpenRouter.

Принцип: вся статистика считается детерминированно в Python (build_facts),
LLM только превращает структурированные факты в связный текст и
не имеет права придумывать цифры.
"""
import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st

from utils import domain_knowledge

STRENGTH_COL = 'Относительная разрывная нагрузка, сН/текс'
CV_COL = 'Коэффициент вариации, %'
DENSITY_COL = 'Линейная плотность, текс'

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'summaries.db'

# Модели OpenRouter: (id, цена $/1M входных, $/1M выходных) — для оценки стоимости
MODELS = {
    'anthropic/claude-haiku-4.5': {'label': 'Claude Haiku 4.5 (рекомендуется)', 'in': 1.0, 'out': 5.0},
    'anthropic/claude-sonnet-4.6': {'label': 'Claude Sonnet 4.6 (максимум качества)', 'in': 3.0, 'out': 15.0},
    'google/gemini-2.5-flash': {'label': 'Gemini 2.5 Flash (самый дешёвый)', 'in': 0.30, 'out': 2.50},
}
DEFAULT_MODEL = 'anthropic/claude-haiku-4.5'

SYSTEM_PROMPT = """Ты — главный технолог прядильного производства арамидной нити.
Тебе передают структурированные факты диагностики последней партии термообработанной нити
с круткой 50 кр/м (норма прочности: не менее 260 сН/текс, CV не более 10%,
плотность 28.3–29.5 текс).

Напиши краткую технологическую сводку на русском языке (200–350 слов) в Markdown:

1. Первая строка — общая оценка: 🔴 (критично — требуется вмешательство),
   🟡 (есть локальные проблемы) или 🟢 (процесс в норме), с пояснением в одну фразу.
2. Затем разделы по приоритету (только те, где есть что сказать):
   полимер / машины / аппараты ВТВ / статистическая управляемость / динамика.
3. Каждая проблема — с конкретной рекомендацией, куда смотреть технологу.

ВАЖНО — сводку читают люди, далёкие от статистических методов управления качеством.
Каждый специальный термин и каждую аббревиатуру ОБЯЗАТЕЛЬНО поясняй в скобках
простыми словами при первом упоминании. Примеры обязательных пояснений:
- CV (коэффициент вариации — мера разброса прочности между бобинами: чем выше, тем нестабильнее нить)
- SPC (статистическое управление процессом — метод раннего обнаружения проблем по контрольным картам)
- CL (центральная линия — средний уровень показателя за последние партии)
- сигнал «8 точек подряд по одну сторону от CL» (показатель уже 8 партий подряд стабильно
  выше/ниже обычного уровня — это не случайность, а системный сдвиг)
- Cpk (индекс воспроизводимости — запас прочности процесса относительно нормы:
  больше 1.33 — хорошо, меньше 1.0 — процесс не держит допуск)
- σ/сигма (стандартное отклонение — типичный размах колебаний показателя)
Так же поясняй любые другие термины: разладка, тренд, зона A, скользящее среднее и т.п.

Вместе с фактами тебе передают СПРАВОЧНИК ПРОИЗВОДСТВА (глоссарий и чек-листы причин
из рабочих инструкций цеха). Опирайся на него:
- рекомендации давай точечные, с конкретными узлами и нормами из справочника
  (например: «проверить уровень промывных жидкостей — норма не менее 30% диаметра роликов»,
  а не «проверить технологический режим»);
- адресуй рекомендации исполнителям: аппаратчик формования, оператор кручения,
  помощник мастера, сменный мастер — как указано в справочнике;
- термины поясняй формулировками из глоссария;
- НЕ называй нормы и узлы, которых нет в справочнике или фактах.

Правила:
- Используй ТОЛЬКО цифры из переданных фактов, ничего не вычисляй и не придумывай.
- Если общего снижения нет — так и скажи, что полимер вне подозрений.
- Не пересказывай все факты подряд — выбери важное, расставь приоритеты.
- Пиши по-деловому, но доступно. Номера машин — «ПМ 23», аппаратов — «ВТВ №18»."""

# Версия промпта — входит в ключ кэша: смена промпта обновляет сводки
PROMPT_VERSION = "v4"



# ============================================================
# ДИАГНОСТИЧЕСКИЙ ДВИЖОК
# ============================================================

def _nelson_signals(values):
    """Правила Нельсона 1, 2, 3, 5 на ряде средних по партиям (X-MR оценка sigma)."""
    out = []
    v = np.asarray(values, dtype=float)
    if len(v) < 5:
        return out, None, None
    mr = np.abs(np.diff(v))
    mr_bar = mr.mean()
    sigma = mr_bar / 1.128 if mr_bar > 0 else v.std() or 1e-9
    cl = v.mean()

    # П1: точка за 3 сигма
    for i, x in enumerate(v):
        if abs(x - cl) > 3 * sigma:
            out.append(f"точка {i - len(v)} за 3σ ({x:.1f})")
    # П2: 8 подряд по одну сторону
    side = np.sign(v - cl)
    run, run_side = 0, 0
    for s in side:
        if s == run_side and s != 0:
            run += 1
        else:
            run, run_side = 1, s
        if run == 8:
            out.append("8 точек подряд по одну сторону от CL (устойчивый сдвиг)")
            break
    # П3: 6 подряд монотонно
    diffs = np.sign(np.diff(v))
    run, run_dir = 0, 0
    for d in diffs:
        if d == run_dir and d != 0:
            run += 1
        else:
            run, run_dir = 1, d
        if run == 5:
            out.append("6 точек подряд монотонный " + ("рост" if d > 0 else "спад"))
            break
    # П5: 2 из 3 за 2 сигма по одну сторону
    for i in range(len(v) - 2):
        w = v[i:i + 3] - cl
        if sum(w > 2 * sigma) >= 2 or sum(w < -2 * sigma) >= 2:
            out.append(f"2 из 3 точек за 2σ (партии в конце ряда: {i - len(v)}…)")
            break
    return out, cl, sigma


def build_facts(df, thresholds, offset):
    """Детерминированный расчёт всех диагностических критериев. df — крутка 50."""
    smin = thresholds['strength_min']
    cvmax = thresholds['cv_max']
    dmin, dmax = thresholds['density_range']

    parties = sorted(df['№ партии'].dropna().unique())
    cur = parties[-1]
    cur_df = df[df['№ партии'] == cur]
    hist20 = parties[-21:-1]  # 20 партий до текущей

    f = {'партия': int(cur) - offset, 'дата_генерации': datetime.now().strftime('%d.%m.%Y %H:%M')}

    # --- Текущая партия ---
    s = cur_df[STRENGTH_COL].dropna()
    c = cur_df[CV_COL].dropna()
    d = cur_df[DENSITY_COL].dropna() if DENSITY_COL in cur_df.columns else pd.Series(dtype=float)
    f['текущая_партия'] = {
        'машин': int(cur_df['№ ПМ'].nunique()),
        'средняя_прочность': float(round(s.mean(), 1)),
        'мин_прочность': float(round(s.min(), 1)),
        'ниже_нормы_прочность_шт': int((s < smin).sum()),
        'ниже_нормы_прочность_%': round((s < smin).mean() * 100, 1),
        'средний_CV': float(round(c.mean(), 1)),
        'выше_нормы_CV_шт': int((c > cvmax).sum()),
        'средняя_плотность': float(round(d.mean(), 2)) if len(d) else None,
        'плотность_вне_допуска_шт': int(((d < dmin) | (d > dmax)).sum()) if len(d) else 0,
    }

    # --- История по партиям ---
    pm = df[df['№ партии'].isin(hist20 + [cur])].groupby('№ партии').agg(
        s_mean=(STRENGTH_COL, 'mean'),
        cv_mean=(CV_COL, 'mean'),
        fail=(STRENGTH_COL, lambda x: (x < smin).mean() * 100),
    )

    # --- SPC: правила Нельсона ---
    sig_s, cl_s, sigma_s = _nelson_signals(pm['s_mean'].values)
    sig_c, cl_c, _ = _nelson_signals(pm['cv_mean'].values)
    f['SPC'] = {
        'окно_партий': len(pm),
        'CL_прочность': round(cl_s, 1) if cl_s else None,
        'сигналы_прочность': sig_s or 'нет',
        'сигналы_CV': sig_c or 'нет',
    }

    # --- Полимер: общий сдвиг широким фронтом ---
    cur_mean = pm['s_mean'].iloc[-1]
    drop_vs_cl = cur_mean - cl_s if cl_s else 0
    prev5 = parties[-6:-1]
    prev_df = df[df['№ партии'].isin(prev5)]
    pm_prev = prev_df.groupby('№ ПМ')[STRENGTH_COL].mean()
    pm_cur = cur_df.groupby('№ ПМ')[STRENGTH_COL].mean()
    common = pm_cur.index.intersection(pm_prev.index)
    dropped_share = float((pm_cur[common] < pm_prev[common]).mean() * 100) if len(common) else 0
    f['полимер'] = {
        'текущее_среднее_минус_CL': round(drop_vs_cl, 2),
        'доля_машин_упавших_к_своему_среднему_%': round(dropped_share, 0),
        'подозрение': bool(sigma_s and drop_vs_cl < -sigma_s and dropped_share > 70),
    }

    # --- Машины ---
    dev = cur_df.set_index('№ ПМ')[STRENGTH_COL] - s.mean()
    std_w = s.std()
    worst_now = dev[dev < -2 * std_w].sort_values()
    # Хроника: средняя по машине < нормы в каждой из 3 последних партий
    last3 = parties[-3:]
    chronic = []
    pm3 = df[df['№ партии'].isin(last3)].groupby(['№ ПМ', '№ партии'])[STRENGTH_COL].mean().unstack()
    for m, row in pm3.iterrows():
        vals = row.dropna()
        if len(vals) == 3 and (vals < smin).all():
            chronic.append(int(m))
    cv3 = df[df['№ партии'].isin(last3)].groupby(['№ ПМ', '№ партии'])[CV_COL].mean().unstack()
    cv_chronic = [int(m) for m, row in cv3.iterrows()
                  if (row.dropna() > cvmax).sum() >= 2]
    f['машины'] = {
        'резко_ниже_партии_сейчас': {f"ПМ {int(m)}": round(v, 1) for m, v in worst_now.head(6).items()},
        'хронически_ниже_нормы_3_партии': chronic[:10],
        'хронический_высокий_CV': cv_chronic[:10],
    }

    # --- Аппараты ВТВ ---
    vtv_block = {}
    if '№ ВТВ' in df.columns:
        dv = df.copy()
        dv['ВТВ'] = pd.to_numeric(dv['№ ВТВ'], errors='coerce')
        dv = dv[dv['ВТВ'].between(1, 19)]
        dv['dev'] = dv[STRENGTH_COL] - dv.groupby('№ партии')[STRENGTH_COL].transform('mean')
        recent = dv[dv['№ партии'].isin(parties[-5:])]
        g = recent.groupby('ВТВ')['dev'].agg(['mean', 'count'])
        g = g[g['count'] >= 10]
        alerts = g[g['mean'] <= -2.0]
        vtv_block = {
            'требуют_настройки_откл_за_5_партий': {f"ВТВ №{int(i)}": round(r['mean'], 1) for i, r in alerts.iterrows()},
            'худший': (f"ВТВ №{int(g['mean'].idxmin())}: {g['mean'].min():+.1f} сН/текс" if len(g) else None),
            'лучший': (f"ВТВ №{int(g['mean'].idxmax())}: {g['mean'].max():+.1f} сН/текс" if len(g) else None),
        }
    f['ВТВ'] = vtv_block or 'нет данных'

    # --- Способность процесса и динамика ---
    last10_df = df[df['№ партии'].isin(parties[-10:])][STRENGTH_COL].dropna()
    cpk = (last10_df.mean() - smin) / (3 * last10_df.std()) if last10_df.std() > 0 else None
    fail5 = (df[df['№ партии'].isin(parties[-5:])][STRENGTH_COL] < smin).mean() * 100
    fail5p = (df[df['№ партии'].isin(parties[-10:-5])][STRENGTH_COL] < smin).mean() * 100
    f['динамика'] = {
        'Cpk_за_10_партий': round(cpk, 2) if cpk else None,
        'брак_последние_5_партий_%': round(fail5, 1),
        'брак_предыдущие_5_партий_%': round(fail5p, 1),
    }
    return f


# ============================================================
# КЭШ (SQLite)
# ============================================================

def _db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS summaries (
        party INTEGER, model TEXT, facts_hash TEXT, summary TEXT,
        in_tokens INTEGER, out_tokens INTEGER, cost_usd REAL, created TEXT,
        PRIMARY KEY (party, model, facts_hash))""")
    return conn


def get_cached(party, model, facts_hash):
    conn = _db()
    row = conn.execute(
        "SELECT summary, in_tokens, out_tokens, cost_usd, created FROM summaries WHERE party=? AND model=? AND facts_hash=?",
        (party, model, facts_hash)).fetchone()
    conn.close()
    return row


def save_summary(party, model, facts_hash, summary, in_t, out_t, cost):
    conn = _db()
    conn.execute("INSERT OR REPLACE INTO summaries VALUES (?,?,?,?,?,?,?,?)",
                 (party, model, facts_hash, summary, in_t, out_t, cost,
                  datetime.now().strftime('%d.%m.%Y %H:%M')))
    conn.commit()
    conn.close()


def total_spend():
    conn = _db()
    row = conn.execute("SELECT COALESCE(SUM(cost_usd),0), COUNT(*) FROM summaries").fetchone()
    conn.close()
    return row[0], row[1]


def facts_hash(facts):
    clean = {k: v for k, v in facts.items() if k != 'дата_генерации'}
    clean['_prompt'] = PROMPT_VERSION
    return hashlib.md5(json.dumps(clean, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:12]


# ============================================================
# OPENROUTER
# ============================================================

def get_api_key():
    try:
        if 'OPENROUTER_API_KEY' in st.secrets:
            return st.secrets['OPENROUTER_API_KEY']
        # Частая ошибка: ключ вставлен внутрь секции [gcp_service_account]
        for section in st.secrets:
            try:
                val = st.secrets[section]
                if hasattr(val, 'get') and val.get('OPENROUTER_API_KEY'):
                    return val['OPENROUTER_API_KEY']
            except Exception:
                continue
    except Exception:
        pass
    return os.getenv('OPENROUTER_API_KEY')


def generate(facts, model):
    """Вызов OpenRouter. Возвращает (text, in_tokens, out_tokens, cost_usd)."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("no_key")

    facts_text = json.dumps(facts, ensure_ascii=False, indent=1, default=str)
    knowledge = domain_knowledge.select_knowledge(facts)
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 1200,
            "usage": {"include": True},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"СПРАВОЧНИК ПРОИЗВОДСТВА:\n{knowledge}\n\nФакты диагностики:\n```json\n{facts_text}\n```"},
            ],
        },
        timeout=90,
    )
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        raise RuntimeError(data['error'].get('message', str(data['error'])))
    text = data['choices'][0]['message']['content']
    usage = data.get('usage', {}) or {}
    in_t = usage.get('prompt_tokens', 0)
    out_t = usage.get('completion_tokens', 0)
    cost = usage.get('cost')
    if cost is None:
        p = MODELS.get(model, {'in': 3.0, 'out': 15.0})
        cost = in_t / 1e6 * p['in'] + out_t / 1e6 * p['out']
    return text, in_t, out_t, float(cost)


# ============================================================
# ФОЛБЭК БЕЗ LLM
# ============================================================

def render_fallback(f):
    """Детерминированная сводка-чеклист, если API недоступен."""
    t = f['текущая_партия']
    lines = [f"**Партия №{f['партия']}** — {t['машин']} машин, "
             f"прочность {t['средняя_прочность']} сН/текс, CV {t['средний_CV']}%, "
             f"ниже нормы {t['ниже_нормы_прочность_шт']} ({t['ниже_нормы_прочность_%']}%)."]
    if f['полимер']['подозрение']:
        lines.append(f"🔴 **Полимер:** общее снижение ({f['полимер']['текущее_среднее_минус_CL']:+} к CL), "
                     f"упало {f['полимер']['доля_машин_упавших_к_своему_среднему_%']:.0f}% машин.")
    m = f['машины']
    if m['резко_ниже_партии_сейчас']:
        lines.append("🟡 **Машины ниже партии:** " + ", ".join(f"{k} ({v:+})" for k, v in m['резко_ниже_партии_сейчас'].items()))
    if m['хронически_ниже_нормы_3_партии']:
        lines.append("🔴 **Хроника (3 партии ниже нормы):** ПМ " + ", ".join(map(str, m['хронически_ниже_нормы_3_партии'])))
    if isinstance(f['ВТВ'], dict) and f['ВТВ'].get('требуют_настройки_откл_за_5_партий'):
        lines.append("🔴 **ВТВ требуют настройки:** " + ", ".join(f"{k} ({v})" for k, v in f['ВТВ']['требуют_настройки_откл_за_5_партий'].items()))
    spc = f['SPC']
    if spc['сигналы_прочность'] != 'нет' or spc['сигналы_CV'] != 'нет':
        sp = spc['сигналы_прочность']
        sc = spc['сигналы_CV']
        sp = '; '.join(sp) if isinstance(sp, list) else sp
        sc = '; '.join(sc) if isinstance(sc, list) else sc
        lines.append(f"🟡 **SPC:** прочность — {sp}; CV — {sc}")
    else:
        lines.append("🟢 **SPC:** процесс статистически управляем.")
    dyn = f['динамика']
    lines.append(f"**Динамика:** Cpk={dyn['Cpk_за_10_партий']}, брак {dyn['брак_предыдущие_5_партий_%']}% → {dyn['брак_последние_5_партий_%']}%.")
    return "\n\n".join(lines)
