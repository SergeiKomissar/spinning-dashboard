from unittest import mock

import pandas as pd
import pytest

from utils import google_sheets
from utils.data_processing import prepare_dataframe

STRENGTH = 'Относительная разрывная нагрузка, сН/текс'


class _Secrets(dict):
    pass


def test_cloud_uses_secrets_section():
    secrets = _Secrets(gcp_service_account={'type': 'service_account'})
    with mock.patch.object(google_sheets.st, 'secrets', secrets), \
         mock.patch.object(google_sheets.Credentials, 'from_service_account_info', return_value='C') as info:
        assert google_sheets.get_credentials() == 'C'
    info.assert_called_once_with({'type': 'service_account'}, scopes=google_sheets.SCOPES)


def test_local_without_secrets_toml_uses_file(tmp_path, monkeypatch):
    class NoSecrets:
        def __contains__(self, key):
            raise FileNotFoundError('No secrets found')
    key = tmp_path / 'credentials.json'
    key.write_text('{}')
    monkeypatch.setenv('GOOGLE_APPLICATION_CREDENTIALS', str(key))
    with mock.patch.object(google_sheets.st, 'secrets', NoSecrets()), \
         mock.patch.object(google_sheets.Credentials, 'from_service_account_file', return_value='F') as f:
        assert google_sheets.get_credentials() == 'F'
    f.assert_called_once_with(str(key), scopes=google_sheets.SCOPES)


def test_no_credentials_at_all(monkeypatch):
    monkeypatch.delenv('GOOGLE_APPLICATION_CREDENTIALS', raising=False)
    with mock.patch.object(google_sheets.st, 'secrets', _Secrets()), \
         mock.patch.object(google_sheets, 'CREDENTIALS_CANDIDATES', ()):
        with pytest.raises(FileNotFoundError):
            google_sheets.get_credentials()


def _sheet(rows, density='Линейная плотность, текс ', pm=' Номер ПМ'):
    header = ['№ партии', pm, STRENGTH, 'Коэффициент вариации, %', density, 'Крутка']
    return [header] + rows


def test_prepare_renames_and_converts():
    df = prepare_dataframe(_sheet([
        [1238, 73, 267, 55, 287, 50],
        [1238, 74, '282', '6,6', 289, 50],
        ['', '', '', '', '', ''],
    ]))
    assert list(df.columns) == ['№ партии', '№ ПМ', STRENGTH, 'Коэффициент вариации, %',
                                'Линейная плотность, текс', 'Крутка']
    assert len(df) == 2
    # плотность пришла целыми (287) → делится на 10; CV медиана < 50 → не делится
    assert df['Линейная плотность, текс'].tolist() == [28.7, 28.9]
    assert df[STRENGTH].tolist() == [267, 282]


def test_prepare_scales_cv_given_as_integers():
    df = prepare_dataframe(_sheet([[1, 1, 270, 76, 28.7, 50], [1, 2, 270, 81, 28.8, 50]]))
    assert df['Коэффициент вариации, %'].tolist() == [7.6, 8.1]


def test_prepare_reports_missing_columns():
    errors = []
    with mock.patch('utils.data_processing.st.error', errors.append), \
         mock.patch('utils.data_processing.st.warning'):
        assert prepare_dataframe([['A', 'B'], [1, 2]]) is None
    assert 'Отсутствуют обязательные колонки' in errors[0]
