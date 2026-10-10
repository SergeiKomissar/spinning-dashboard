"""Каждая страница отрисовывается без исключений на синтетических данных,
для админа и обычного пользователя, со всеми значениями селекторов."""
import glob
import os

import pytest

import fixtures
import snapshot

PAGES = sorted(glob.glob(os.path.join(snapshot.APP, 'pages', '*.py')))


@pytest.fixture(scope='module')
def results():
    return snapshot.run_all(fixtures.make_df())


@pytest.mark.parametrize('page', [os.path.basename(p) for p in PAGES])
def test_page_renders_without_exceptions(results, page):
    scenarios = {k: v for k, v in results.items() if k.split('#')[0] == page}
    assert scenarios, f'страница {page} не прогнана'
    for name, trees in scenarios.items():
        for sc, tree in trees.items():
            errors = [e['p'] for e in tree if e['t'] == 'Exception']
            assert not errors, f'{name} [{sc}]: {errors[0]}'
            assert len(tree) > 5, f'{name} [{sc}]: страница пустая'


def test_main_dashboard_shows_current_party(results):
    tree = results[os.path.basename(PAGES[0])]['default']
    bodies = ' '.join(e['p'].get('body', '') for e in tree if e['t'] == 'Markdown')
    # последняя партия 846+39=885 → №40 при смещении 845
    assert '№ 40' in bodies
