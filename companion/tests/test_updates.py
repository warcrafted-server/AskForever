"""Pruebas del actualizador de datos del juego."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile

import pytest

from askforever import cli, config, paths
from askforever.updates import (
    UpdateError,
    check_and_update,
    install_data,
    installed_version,
    latest_data_release,
    parse_data_version,
)


def _database_bytes(tmp_path, name='origen.sqlite'):
    path = tmp_path / name
    connection = sqlite3.connect(path)
    connection.execute('CREATE TABLE prueba (valor TEXT)')
    connection.execute("INSERT INTO prueba VALUES ('hola')")
    connection.commit()
    connection.close()
    return path.read_bytes()


def _zip_bytes(tmp_path, entries, name='wow.sqlite.zip'):
    path = tmp_path / name
    with zipfile.ZipFile(path, 'w') as archive:
        for entry_name, payload in entries.items():
            archive.writestr(entry_name, payload)
    return path.read_bytes()


def _downloader(zip_payload, sha_text, calls=None):
    def download(url, target, progress=None):
        payload = (sha_text.encode('utf-8') if url.endswith('.sha256')
                   else zip_payload)
        target.write_bytes(payload)
        if calls is not None:
            calls.append(url)
        if progress is not None:
            progress(len(payload), len(payload))

    return download


def _release(zip_payload, tag='data-2026.11.14', size=None):
    return {
        'version_tag': tag,
        'version': parse_data_version(tag) or (),
        'zip_url': 'https://example.test/wow.sqlite.zip',
        'sha_url': 'https://example.test/wow.sqlite.zip.sha256',
        'size': len(zip_payload) if size is None else size,
    }


def _api_release(tag, draft=False, assets=None):
    if assets is None:
        assets = [
            {
                'name': 'wow.sqlite.zip',
                'size': 123,
                'browser_download_url': (
                    f'https://example.test/{tag}/wow.sqlite.zip'),
            },
            {
                'name': 'wow.sqlite.zip.sha256',
                'size': 64,
                'browser_download_url': (
                    f'https://example.test/{tag}/wow.sqlite.zip.sha256'),
            },
        ]
    return {
        'tag_name': tag,
        'draft': draft,
        'prerelease': False,
        'assets': assets,
    }


def _valid_payload(tmp_path):
    database = _database_bytes(tmp_path)
    archive = _zip_bytes(tmp_path, {'wow.sqlite': database})
    digest = hashlib.sha256(archive).hexdigest()
    return database, archive, digest


def test_parse_data_version():
    assert parse_data_version('data-2026.11.14') == (2026, 11, 14)
    assert parse_data_version('data-2026.11.14.2') == (2026, 11, 14, 2)
    for tag in ('2026.11.14', 'data-2026.11', 'data-2026.11.14.',
                'data-2026.11.14.x', 'data-2026.11.14.2.1', '', None):
        assert parse_data_version(tag) is None


def test_latest_data_release_chooses_highest_valid():
    releases = [
        _api_release('data-2026.11.16', draft=True),
        _api_release('data-vieja'),
        _api_release('data-2026.11.13'),
        _api_release('data-2026.11.14.2'),
        _api_release('data-2026.11.15', assets=[
            {
                'name': 'wow.sqlite.zip',
                'size': 99,
                'browser_download_url': 'https://example.test/solo.zip',
            },
        ]),
    ]

    release = latest_data_release(fetch_json=lambda _url: releases)

    assert release == {
        'version_tag': 'data-2026.11.14.2',
        'version': (2026, 11, 14, 2),
        'zip_url': 'https://example.test/data-2026.11.14.2/wow.sqlite.zip',
        'sha_url': (
            'https://example.test/data-2026.11.14.2/wow.sqlite.zip.sha256'),
        'size': 123,
    }


def test_latest_data_release_accepts_fetch_without_url():
    releases = [_api_release('data-2026.11.14')]
    assert latest_data_release(fetch_json=lambda: releases) is not None


def test_latest_data_release_returns_none_on_error():
    def fail(_url):
        raise OSError('sin red')

    assert latest_data_release(fetch_json=fail) is None
    assert latest_data_release(fetch_json=lambda _url: {'error': 'x'}) is None


def test_installed_version(tmp_path):
    assert installed_version(tmp_path) is None
    (tmp_path / 'version.json').write_text('{malo', encoding='utf-8')
    assert installed_version(tmp_path) is None
    (tmp_path / 'version.json').write_text('[1]', encoding='utf-8')
    assert installed_version(tmp_path) is None
    good = {'version_tag': 'data-2026.11.14', 'sha256': 'abc',
            'installed_at': '2026-11-14T12:00:00+00:00'}
    (tmp_path / 'version.json').write_text(json.dumps(good), encoding='utf-8')
    assert installed_version(tmp_path) == good


def test_install_data_installs_and_backs_up(tmp_path):
    data_dir = tmp_path / 'datos'
    database, archive, digest = _valid_payload(tmp_path)
    download = _downloader(archive, digest)

    tag = install_data(_release(archive), data_dir, download=download)

    current = data_dir / 'wow.sqlite'
    assert tag == 'data-2026.11.14'
    assert current.read_bytes() == database
    version = json.loads((data_dir / 'version.json').read_text(encoding='utf-8'))
    assert version['version_tag'] == tag
    assert version['sha256'] == digest
    assert version['installed_at']
    assert not (data_dir / 'wow.sqlite.bak').exists()
    assert not list(data_dir.glob('.wow-*'))

    database2 = _database_bytes(tmp_path, 'origen2.sqlite')
    archive2 = _zip_bytes(tmp_path, {'wow.sqlite': database2}, name='dos.zip')
    digest2 = hashlib.sha256(archive2).hexdigest()

    tag2 = install_data(_release(archive2, tag='data-2026.11.15'), data_dir,
                        download=_downloader(archive2, digest2))

    assert tag2 == 'data-2026.11.15'
    assert current.read_bytes() == database2
    assert (data_dir / 'wow.sqlite.bak').read_bytes() == database
    version2 = json.loads((data_dir / 'version.json').read_text(encoding='utf-8'))
    assert version2['version_tag'] == tag2
    assert version2['sha256'] == digest2
    assert not list(data_dir.glob('.wow-*'))


def test_install_data_reports_progress(tmp_path):
    _, archive, digest = _valid_payload(tmp_path)
    calls = []

    def download(url, target, progress=None):
        payload = digest.encode('utf-8') if url.endswith('.sha256') else archive
        target.write_bytes(payload)
        if progress is not None:
            progress(50, 100)
            progress(100, 100)

    def record(downloaded, total):
        calls.append((downloaded, total))

    install_data(_release(archive), tmp_path / 'datos', download=download,
                 progress=record)
    assert calls == [(50, 100), (100, 100)]


def test_install_data_accepts_two_argument_downloader(tmp_path):
    _, archive, digest = _valid_payload(tmp_path)

    def download(url, target):
        target.write_bytes(digest.encode('utf-8') if url.endswith('.sha256')
                           else archive)

    tag = install_data(_release(archive), tmp_path / 'datos', download=download)
    assert tag == 'data-2026.11.14'
    assert (tmp_path / 'datos' / 'wow.sqlite').is_file()


def test_install_data_accepts_returning_downloader(tmp_path):
    _, archive, digest = _valid_payload(tmp_path)
    payloads = {
        'https://example.test/wow.sqlite.zip': archive,
        'https://example.test/wow.sqlite.zip.sha256': digest,
    }

    tag = install_data(_release(archive), tmp_path / 'datos',
                       download=lambda url: payloads[url])
    assert tag == 'data-2026.11.14'
    assert (tmp_path / 'datos' / 'wow.sqlite').is_file()


def test_install_data_hash_mismatch_keeps_existing(tmp_path):
    data_dir = tmp_path / 'datos'
    data_dir.mkdir()
    current = data_dir / 'wow.sqlite'
    current.write_bytes(b'base anterior')
    version = data_dir / 'version.json'
    version.write_text('{"version_tag": "data-2026.01.01"}', encoding='utf-8')
    old_version = version.read_bytes()
    _, archive, _ = _valid_payload(tmp_path)

    with pytest.raises(UpdateError) as error:
        install_data(_release(archive), data_dir,
                     download=_downloader(archive, '0' * 64))

    assert error.value.kind == 'hash'
    assert current.read_bytes() == b'base anterior'
    assert version.read_bytes() == old_version
    assert not (data_dir / 'wow.sqlite.bak').exists()
    assert not list(data_dir.glob('.wow-*'))


@pytest.mark.parametrize('extra_name', ['../x', 'otra.sqlite', 'carpeta/wow.sqlite'])
def test_install_data_rejects_extra_zip_entries(tmp_path, extra_name):
    data_dir = tmp_path / 'datos'
    data_dir.mkdir()
    current = data_dir / 'wow.sqlite'
    current.write_bytes(b'base anterior')
    database = _database_bytes(tmp_path)
    archive = _zip_bytes(tmp_path, {'wow.sqlite': database, extra_name: b'x'})
    digest = hashlib.sha256(archive).hexdigest()

    with pytest.raises(UpdateError) as error:
        install_data(_release(archive), data_dir,
                     download=_downloader(archive, digest))

    assert error.value.kind == 'zip'
    assert current.read_bytes() == b'base anterior'
    assert not (data_dir / 'wow.sqlite.bak').exists()


def test_install_data_rejects_zip_without_database(tmp_path):
    database = _database_bytes(tmp_path)
    archive = _zip_bytes(tmp_path, {'otra.sqlite': database})
    digest = hashlib.sha256(archive).hexdigest()

    with pytest.raises(UpdateError) as error:
        install_data(_release(archive), tmp_path / 'datos',
                     download=_downloader(archive, digest))

    assert error.value.kind == 'zip'
    assert not (tmp_path / 'datos' / 'wow.sqlite').exists()


def test_install_data_rejects_corrupt_database(tmp_path):
    data_dir = tmp_path / 'datos'
    data_dir.mkdir()
    current = data_dir / 'wow.sqlite'
    current.write_bytes(b'base anterior')
    archive = _zip_bytes(tmp_path, {'wow.sqlite': b'esto no es sqlite'})
    digest = hashlib.sha256(archive).hexdigest()

    with pytest.raises(UpdateError) as error:
        install_data(_release(archive), data_dir,
                     download=_downloader(archive, digest))

    assert error.value.kind == 'database'
    assert current.read_bytes() == b'base anterior'
    assert not (data_dir / 'wow.sqlite.bak').exists()
    assert not list(data_dir.glob('.wow-*'))


def test_check_and_update_offline_without_network(tmp_path):
    def fail(_url):
        raise OSError('sin red')

    assert check_and_update(tmp_path, fetch_json=fail) == ('offline', None)

    (tmp_path / 'version.json').write_text(
        json.dumps({'version_tag': 'data-2026.11.13'}), encoding='utf-8')
    assert check_and_update(tmp_path, fetch_json=fail) == (
        'offline', 'data-2026.11.13')


def test_check_and_update_current(tmp_path):
    (tmp_path / 'version.json').write_text(
        json.dumps({'version_tag': 'data-2026.11.14'}), encoding='utf-8')
    releases = [_api_release('data-2026.11.14')]

    assert check_and_update(tmp_path, fetch_json=lambda _url: releases) == (
        'current', 'data-2026.11.14')
    assert check_and_update(tmp_path, current='data-2026.11.14',
                            fetch_json=lambda _url: releases) == (
        'current', 'data-2026.11.14')


def test_check_and_update_installs_new_version(tmp_path):
    _, archive, digest = _valid_payload(tmp_path)
    releases = [_api_release('data-2026.11.14')]

    status, tag = check_and_update(
        tmp_path / 'datos',
        fetch_json=lambda _url: releases,
        download=_downloader(archive, digest),
    )

    assert (status, tag) == ('updated', 'data-2026.11.14')
    assert (tmp_path / 'datos' / 'wow.sqlite').is_file()
    assert installed_version(tmp_path / 'datos')['version_tag'] == tag


def test_check_and_update_returns_error_without_raising(tmp_path):
    _, archive, _ = _valid_payload(tmp_path)
    releases = [_api_release('data-2026.11.14')]

    status, message = check_and_update(
        tmp_path / 'datos',
        fetch_json=lambda _url: releases,
        download=_downloader(archive, '0' * 64),
    )

    assert (status, message) == ('error', 'hash')
    assert not (tmp_path / 'datos' / 'wow.sqlite').exists()


def test_update_data_command_reports_result(monkeypatch, capsys):
    def fake_check(_data_dir, progress=None):
        progress(50, 100)
        progress(100, 100)
        return ('updated', 'data-2026.11.14')

    monkeypatch.setattr(cli, 'user_data_dir', lambda: 'datos')
    monkeypatch.setattr(cli, 'check_and_update', fake_check)

    assert cli.main(['update-data']) == 0
    output = capsys.readouterr().out
    assert 'Comprobando datos del juego...' in output
    assert 'Descargando datos: 50 %' in output
    assert 'Descargando datos: 100 %' in output
    assert 'Datos actualizados a data-2026.11.14' in output


def test_update_data_command_offline_without_data(monkeypatch, capsys):
    monkeypatch.setattr(cli, 'user_data_dir', lambda: 'datos')
    monkeypatch.setattr(cli, 'check_and_update',
                        lambda *_args, **_kwargs: ('offline', None))

    assert cli.main(['update-data']) == 1
    output = capsys.readouterr().out
    assert ('Sin datos del juego: las respuestas tendran menos informacion'
            in output)


def test_user_data_dir_uses_localappdata(monkeypatch, tmp_path):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    target = paths.user_data_dir()
    assert target == tmp_path / 'AskForever' / 'data'
    assert not target.exists()


def test_managed_wowdata_path(monkeypatch, tmp_path):
    monkeypatch.setattr(config, 'user_data_dir', lambda: tmp_path)
    assert config.managed_wowdata_path() == tmp_path / 'wow.sqlite'
    assert not config.managed_wowdata_path().exists()


def test_data_is_managed(monkeypatch, tmp_path):
    monkeypatch.delenv(config.WOWDATA_ENV, raising=False)
    monkeypatch.setattr(config, '_sibling_wowdata_path',
                        lambda: tmp_path / 'no-existe.sqlite')
    assert config.data_is_managed() is True

    monkeypatch.setenv(config.WOWDATA_ENV, str(tmp_path / 'entorno.sqlite'))
    assert config.data_is_managed() is False

    monkeypatch.delenv(config.WOWDATA_ENV, raising=False)
    sibling = tmp_path / 'hermana.sqlite'
    sibling.write_bytes(b'')
    monkeypatch.setattr(config, '_sibling_wowdata_path', lambda: sibling)
    assert config.data_is_managed() is False


def test_get_wowdata_path_order(monkeypatch, tmp_path):
    managed_dir = tmp_path / 'gestionada'
    managed_dir.mkdir()
    managed = managed_dir / 'wow.sqlite'
    managed.write_bytes(b'')
    sibling = tmp_path / 'hermana.sqlite'
    env_path = tmp_path / 'entorno.sqlite'
    env_path.write_bytes(b'')
    monkeypatch.setattr(config, 'user_data_dir', lambda: managed_dir)
    monkeypatch.setattr(config, '_sibling_wowdata_path',
                        lambda: tmp_path / 'no-existe.sqlite')
    monkeypatch.delenv(config.WOWDATA_ENV, raising=False)

    assert config.get_wowdata_path() == managed

    sibling.write_bytes(b'')
    monkeypatch.setattr(config, '_sibling_wowdata_path', lambda: sibling)
    assert config.get_wowdata_path() == sibling

    monkeypatch.setenv(config.WOWDATA_ENV, str(env_path))
    assert config.get_wowdata_path() == env_path

    monkeypatch.setenv(config.WOWDATA_ENV, str(tmp_path / 'sin.sqlite'))
    assert config.get_wowdata_path() == sibling

    monkeypatch.delenv(config.WOWDATA_ENV, raising=False)
    monkeypatch.setattr(config, '_sibling_wowdata_path',
                        lambda: tmp_path / 'no-existe.sqlite')
    managed.unlink()
    assert config.get_wowdata_path() is None
