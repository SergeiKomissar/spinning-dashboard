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


@pytest.mark.parametrize('page', [os.path.basename(p) for p in PAGES if not os.path.basename(p).startswith('5_')])
def test_refresh_button_reloads_data(page):
    """«Обновить» должна заново читать таблицу, а не только чистить кэш."""
    from unittest import mock
    from streamlit.testing.v1 import AppTest
    import utils.data_processing as dp

    df = fixtures.make_df(n_parties_100=12, n_parties_50=12)
    calls = []

    class Load:
        def __call__(self):
            calls.append(1)
            return df.copy()

        def clear(self):
            pass

    with mock.patch.object(dp, 'load_data', Load()), \
         mock.patch.object(snapshot.st_button.ButtonMixin, 'page_link', snapshot._fake_page_link), \
         mock.patch.object(snapshot.dk, '_load_blocks_from_sheet', lambda: {}):
        at = AppTest.from_file(os.path.join(snapshot.APP, 'pages', page), default_timeout=120)
        at.session_state['authenticated'] = True
        at.session_state['user_info'] = {'name': 'Т', 'role': 'admin'}
        at.session_state['visit_id'] = None
        at.run()
        assert len(calls) == 1
        [btn] = [b for b in at.button if b.label == 'Обновить']
        btn.click().run()
        assert len(calls) == 2
        assert not at.exception
