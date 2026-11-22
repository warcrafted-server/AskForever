import sys

import pytest

from askforever import config, paths, uninstall

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='rutas de Linux')


def test_default_root_is_xdg_data_home(monkeypatch, tmp_path):
    monkeypatch.delenv('LOCALAPPDATA', raising=False)
    monkeypatch.delenv('ASKFOREVER_HOME', raising=False)
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    assert paths.app_root() == tmp_path / 'askforever'
    assert paths.user_data_dir() == tmp_path / 'askforever' / 'data'


def test_frozen_linux_uses_program_folder(monkeypatch, tmp_path):
    monkeypatch.delenv('LOCALAPPDATA', raising=False)
    monkeypatch.delenv('ASKFOREVER_HOME', raising=False)
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'AskForever' / 'askforever'))
    assert paths.is_portable()
    assert paths.app_root() == tmp_path / 'AskForever'


def test_home_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv('ASKFOREVER_HOME', str(tmp_path / 'x'))
    assert paths.app_root() == tmp_path / 'x'


def test_portable_uninstall_keeps_program_folder(monkeypatch, tmp_path):
    root = tmp_path / 'AskForever'
    (root / 'data').mkdir(parents=True)
    (root / 'logs').mkdir()
    (root / 'askforever').write_text('bin')
    monkeypatch.setenv('ASKFOREVER_HOME', str(root))
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(uninstall, '_keyring_backend', lambda: type('K', (), {
        'delete_password': staticmethod(lambda *a: None)})())
    assert uninstall.uninstall(yes=True, game_addons_dir=tmp_path / 'AddOns') == 0
    assert not (root / 'data').exists()
    assert not (root / 'logs').exists()
    assert (root / 'askforever').exists()
