import os
from unittest import mock

import pytest
from streamlit.testing.v1 import AppTest

import fixtures
import snapshot
from utils import auth

USERS = {'credentials': {'usernames': {
    'boss': {'name': 'Начальник', 'password': 'secret', 'role': 'admin'},
}}}
PAGE = os.path.join(snapshot.APP, 'pages', sorted(os.listdir(os.path.join(snapshot.APP, 'pages')))[0])


@pytest.fixture
def app(tmp_path):
    with mock.patch.object(auth, 'load_users', lambda: USERS), \
         mock.patch.object(auth, 'DB_PATH', tmp_path / 'visits.db'), \
         mock.patch.object(snapshot.dp, 'load_data', snapshot.FakeLoad(fixtures.make_df(5, 5))), \
         mock.patch.object(snapshot.st_button.ButtonMixin, 'page_link', snapshot._fake_page_link):
        at = AppTest.from_file(PAGE, default_timeout=120)
        at.run()
        yield at


def _login(at, user, pwd):
    at.text_input[0].input(user)
    at.text_input[1].input(pwd)
    [btn] = [b for b in at.button if b.label == 'Войти']
    btn.click().run()


def test_wrong_password_rejected(app):
    _login(app, 'boss', 'nope')
    assert not app.session_state['authenticated']
    assert any('Неверный логин или пароль' in e.value for e in app.error)


def test_login_logs_visit_and_shows_dashboard(app):
    _login(app, 'boss', 'secret')
    assert app.session_state['authenticated']
    assert app.session_state['user_info']['role'] == 'admin'
    assert auth.get_visit_stats()['visits'][0][0] == 'boss'
    assert not app.exception
