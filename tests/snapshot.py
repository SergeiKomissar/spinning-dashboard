"""Эталонные снимки страниц дашборда (golden master).

Прогоняет каждую страницу через streamlit.testing.AppTest на зафиксированных
данных, перебирает значения селекторов и сохраняет всё, что страница вывела
(тексты, таблицы, графики), в JSON. Сравнение до/после рефакторинга
показывает любое изменение поведения.

    python tests/snapshot.py record  [data.pkl]   # записать эталон
    python tests/snapshot.py compare [data.pkl]   # сравнить с эталоном

Данные: tests/.snapshot/real_df.pkl — выгрузка из Google Sheets, сделанная
локально этим же проектом (доверенный файл, в git не попадает). Если файла нет,
используются синтетические данные из tests/fixtures.py.
"""
import difflib
import glob
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, 'app')
SNAP_DIR = os.path.join(ROOT, 'tests', '.snapshot')
sys.path.insert(0, APP)
sys.path.insert(0, os.path.join(ROOT, 'tests'))

import pandas as pd  # noqa: E402
from google.protobuf.json_format import MessageToDict  # noqa: E402
from streamlit.elements.widgets import button as st_button  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402
from streamlit.testing.v1 import element_tree as et  # noqa: E402

import utils.data_processing as dp  # noqa: E402
import utils.domain_knowledge as dk  # noqa: E402
import utils.ai_summary as ai  # noqa: E402
import utils.auth as auth  # noqa: E402

MAX_OPTIONS_PER_WIDGET = 3


def load_df(path=None):
    path = path or os.path.join(SNAP_DIR, 'real_df.pkl')
    if os.path.exists(path):
        return pd.read_pickle(path)
    import fixtures
    return fixtures.make_df()


class FakeLoad:
    def __init__(self, df):
        self.df = df

    def __call__(self):
        df = self.df.copy()
        df.attrs['loaded_at'] = datetime(2026, 1, 1, 12, 0)
        return df

    def clear(self):
        pass


def _patch_index(cls):
    """AppTest не умеет select_index для селекторов с format_func над
    нестроковыми опциями: value хранится отформатированной строкой."""
    orig = cls.index

    def index(self):
        v = self._value if getattr(self, '_value', None) is not None else None
        if isinstance(v, str) and v in self.options:
            return self.options.index(v)
        return orig.fget(self)
    return mock.patch.object(cls, 'index', property(index))


def _fake_page_link(self, page, *, label=None, icon=None, **kwargs):
    return self.markdown(f'[page_link] {icon} {label} -> {page}')


class FakeResp:
    def raise_for_status(self):
        pass

    def json(self):
        return {'choices': [{'message': {'content': 'ТЕСТОВАЯ СВОДКА'}}],
                'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'cost': 0.001}}


TS_RE = re.compile(r'\d{2}\.\d{2}\.\d{4}( \d{2}:\d{2})?')
ID_RE = re.compile(r'\$\$ID-[0-9a-f]+-')


def _norm(obj):
    if isinstance(obj, dict):
        return {k: _norm(v) for k, v in obj.items() if k not in ('id', 'formId')}
    if isinstance(obj, list):
        return [_norm(v) for v in obj]
    if isinstance(obj, str):
        s = TS_RE.sub('<TS>', obj)
        s = ID_RE.sub('$$ID-', s)
        if s.startswith('{') and '"data"' in s:  # plotly spec — канонизируем JSON
            try:
                return _norm(json.loads(s))
            except ValueError:
                pass
        return s
    if isinstance(obj, float):
        return round(obj, 9)
    return obj


def dump_tree(at):
    out = []

    def walk(node, depth):
        p = getattr(node, 'proto', None)
        entry = {'t': type(node).__name__, 'd': depth}
        if p is not None:
            entry['p'] = _norm(MessageToDict(p))
        out.append(entry)
        children = getattr(node, 'children', None)
        if isinstance(children, dict):
            for c in children.values():
                walk(c, depth + 1)

    walk(at._tree, 0)
    return out


def new_app(page_path, session, secrets):
    at = AppTest.from_file(page_path, default_timeout=300)
    for k, v in session.items():
        at.session_state[k] = v
    for k, v in secrets.items():
        at.secrets[k] = v
    return at


def _pick(n):
    if n <= MAX_OPTIONS_PER_WIDGET:
        return list(range(n))
    return [0, n // 2, n - 1]


def snapshot_page(page_path, session, secrets):
    """Возвращает {сценарий: дерево элементов}."""
    result = {}
    at = new_app(page_path, session, secrets)
    at.run()
    result['default'] = dump_tree(at)

    # Перебор селекторов: каждый виджет отдельно от состояния по умолчанию
    widgets = []
    for kind in ('selectbox', 'radio', 'select_slider'):
        for w in getattr(at, kind):
            widgets.append((kind, w.key, w.label, list(w.options)))
    for kind, key, label, options in widgets:
        for i in _pick(len(options)):
            at2 = new_app(page_path, session, secrets)
            at2.run()
            coll = getattr(at2, kind)
            target = None
            for w in coll:
                if (key and w.key == key) or (not key and w.label == label):
                    target = w
                    break
            if target is None:
                continue
            if hasattr(target, 'select_index'):
                target.select_index(i).run()
            else:
                target.set_value(options[i]).run()
            result[f'{kind}:{key or label}={options[i]}'] = dump_tree(at2)
    return result


def run_all(df):
    tmp = tempfile.mkdtemp()
    session = {'authenticated': True, 'username': 'tester', 'visit_id': None,
               'user_info': {'name': 'Тестер', 'role': 'admin'}}
    patches = [
        mock.patch.object(dp, 'load_data', FakeLoad(df)),
        mock.patch.object(st_button.ButtonMixin, 'page_link', _fake_page_link),
        mock.patch.object(dk, '_load_blocks_from_sheet', lambda: {}),
        mock.patch.object(ai, 'DB_PATH', Path(tmp) / 'summaries.db'),
        mock.patch.object(auth, 'DB_PATH', Path(tmp) / 'visits.db'),
        mock.patch.object(ai.requests, 'post', lambda *a, **k: FakeResp()),
        _patch_index(et.Selectbox),
        _patch_index(et.Radio),
    ]
    for p in patches:
        p.start()
    try:
        results = {}
        pages = sorted(glob.glob(os.path.join(APP, 'pages', '*.py')))
        for page in pages:
            name = os.path.basename(page)
            print('  ', name, flush=True)
            results[name] = snapshot_page(page, session, {})
            if name.startswith('6_'):
                # Резюме технолога с ключом: генерация (заглушка), затем из кэша
                results[name + '#with_key'] = snapshot_page(
                    page, session, {'OPENROUTER_API_KEY': 'test-key'})
            if name.startswith(('1_', '7_')):
                user = dict(session, user_info={'name': 'Пользователь', 'role': 'user'})
                results[name + '#user'] = {'default': snapshot_page(page, user, {})['default']}
        return results
    finally:
        for p in patches:
            p.stop()


def _lines(tree):
    return [json.dumps(e, ensure_ascii=False, sort_keys=True) for e in tree]


def compare(old, new):
    problems = 0
    for page in sorted(set(old) | set(new)):
        if page not in new or page not in old:
            print(f'!! страница {page}: есть только в {"эталоне" if page in old else "новом снимке"}')
            problems += 1
            continue
        for sc in sorted(set(old[page]) | set(new[page])):
            a, b = old[page].get(sc), new[page].get(sc)
            if a == b:
                continue
            problems += 1
            print(f'!! {page} [{sc}] отличается')
            if a is None or b is None:
                print('   сценарий отсутствует в', 'новом снимке' if b is None else 'эталоне')
                continue
            diff = list(difflib.unified_diff(_lines(a), _lines(b), lineterm='', n=0))
            for line in diff[:30]:
                print('   ', line[:400])
    return problems


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'compare'
    df = load_df(sys.argv[2] if len(sys.argv) > 2 else None)
    os.makedirs(SNAP_DIR, exist_ok=True)
    golden = os.path.join(SNAP_DIR, 'golden.json')
    print(f'Данные: {df.shape}. Прогон страниц...')
    res = run_all(df)
    n = sum(len(v) for v in res.values())
    if mode == 'record':
        with open(golden, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False)
        print(f'Эталон записан: {n} сценариев')
        return 0
    with open(golden, encoding='utf-8') as f:
        old = json.load(f)
    problems = compare(old, res)
    print(f'Сценариев: {n}. Отличий: {problems}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
