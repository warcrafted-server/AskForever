import sys

import pytest

from askforever import config, paths, uninstall
from askforever.data import patch

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


def _portable(monkeypatch, tmp_path):
    """Monta el diseño empaquetado: <juego>/AskForever/AskForeverApp."""
    game = tmp_path / 'WoW Forever'
    program = game / 'AskForever' / 'AskForeverApp'
    program.parent.mkdir(parents=True)
    monkeypatch.delenv('ASKFOREVER_HOME', raising=False)
    monkeypatch.delenv('LOCALAPPDATA', raising=False)
    monkeypatch.delenv('ASKFOREVER_ADDON_DIR', raising=False)
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(program))
    return game, program


def _fake_keyring(monkeypatch):
    monkeypatch.setattr(uninstall, '_keyring_backend', lambda: type('K', (), {
        'delete_password': staticmethod(lambda *a: None)})())


def test_portable_game_dir_uses_program_location(monkeypatch, tmp_path):
    game, _ = _portable(monkeypatch, tmp_path)
    (game / 'WOW.EXE').write_text('')
    assert paths.portable_game_dir() == game


def test_portable_game_dir_accepts_interface_folder(monkeypatch, tmp_path):
    game, _ = _portable(monkeypatch, tmp_path)
    (game / 'Interface').mkdir()
    assert paths.portable_game_dir() == game


def test_portable_game_dir_needs_game_marker(monkeypatch, tmp_path):
    _portable(monkeypatch, tmp_path)
    assert paths.portable_game_dir() is None


def test_portable_game_dir_none_from_source(monkeypatch, tmp_path):
    game = tmp_path / 'game'
    (game / 'AskForever').mkdir(parents=True)
    (game / 'Wow.exe').write_text('')
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.setattr(sys, 'executable', str(game / 'AskForever' / 'askforever'))
    assert paths.portable_game_dir() is None


def test_portable_addon_data_found_with_game_closed(monkeypatch, tmp_path):
    game, _ = _portable(monkeypatch, tmp_path)
    (game / 'Wow.exe').write_text('')
    addon = game / 'Interface' / 'AddOns' / 'AskForever'
    (addon / 'data').mkdir(parents=True)
    (addon / 'data' / 'manifest.lua').write_text('')
    assert patch.find_addon_data_dir(None) == addon / 'data'


def test_portable_uninstall_removes_addon_with_game_closed(monkeypatch, tmp_path):
    game, program = _portable(monkeypatch, tmp_path)
    addon = game / 'Interface' / 'AddOns' / 'AskForever'
    (addon / 'data').mkdir(parents=True)
    monkeypatch.setenv('ASKFOREVER_HOME', str(program.parent))
    monkeypatch.setattr(uninstall, 'find_game_window', lambda: None)
    _fake_keyring(monkeypatch)
    assert uninstall.uninstall(yes=True, remove_addon=True) == 0
    assert not addon.exists()


def test_portable_uninstall_ignores_game_running_elsewhere(monkeypatch, tmp_path):
    game, program = _portable(monkeypatch, tmp_path)
    own_addon = game / 'Interface' / 'AddOns' / 'AskForever'
    (own_addon / 'data').mkdir(parents=True)
    other = tmp_path / 'other game'
    other_addon = other / 'Interface' / 'AddOns' / 'AskForever'
    (other_addon / 'data').mkdir(parents=True)
    monkeypatch.setenv('ASKFOREVER_HOME', str(program.parent))
    monkeypatch.setattr(uninstall, 'find_game_window', lambda: object())
    monkeypatch.setattr(
        uninstall, '_process_image_path', lambda hwnd: str(other / 'Wow.exe'))
    _fake_keyring(monkeypatch)
    assert uninstall.uninstall(yes=True, remove_addon=True) == 0
    assert not own_addon.exists()
    assert other_addon.is_dir()


def test_portable_uninstall_keeps_program_folder(monkeypatch, tmp_path):
    root = tmp_path / 'AskForever'
    (root / 'data').mkdir(parents=True)
    (root / 'logs').mkdir()
    (root / 'askforever').write_text('bin')
    monkeypatch.setenv('ASKFOREVER_HOME', str(root))
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    _fake_keyring(monkeypatch)
    assert uninstall.uninstall(yes=True, game_addons_dir=tmp_path / 'AddOns') == 0
    assert not (root / 'data').exists()
    assert not (root / 'logs').exists()
    assert (root / 'askforever').exists()
