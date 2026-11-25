"""Pruebas de la carpeta de WoW Forever y de la traducción de rutas de Wine."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from askforever import cli, wow_dir
from askforever.capture import _window_linux
from askforever.capture import window as capture_window

pytestmark = pytest.mark.skipif(
    sys.platform == 'win32', reason='rutas y enlaces simbólicos de Linux')


def _forever(drive_c: Path) -> Path:
    """Crea una carpeta _forever_ con Wow.exe dentro de ese drive_c."""
    folder = drive_c / 'Program Files (x86)' / 'World of Warcraft' / '_forever_'
    folder.mkdir(parents=True)
    (folder / 'Wow.exe').write_bytes(b'MZ')
    return folder


def _proc(tmp_path: Path, pid: int, argv0: str, environ=None, maps=None) -> Path:
    """Árbol /proc falso con cmdline, environ y maps del proceso."""
    proc = tmp_path / 'proc'
    directory = proc / str(pid)
    directory.mkdir(parents=True)
    (directory / 'cmdline').write_bytes(argv0.encode() + b'\0')
    content = ''.join(f'{key}={value}\0' for key, value in (environ or {}).items())
    (directory / 'environ').write_bytes(content.encode())
    if maps is not None:
        (directory / 'maps').write_text(maps, encoding='utf-8')
    return proc


def test_finds_lutris_prefix_layout(tmp_path):
    expected = _forever(tmp_path / 'Games' / 'battlenet' / 'prefix' / 'drive_c')
    assert wow_dir.find_wow_dirs(home=tmp_path, environ={}) == [expected]


def test_finds_lutris_game_drive_layout(tmp_path):
    expected = _forever(tmp_path / 'Games' / 'wow' / 'drive_c')
    assert wow_dir.find_wow_dirs(home=tmp_path, environ={}) == [expected]


def test_env_override_accepts_world_or_forever_folder(tmp_path):
    forever = _forever(tmp_path / 'Games' / 'a' / 'drive_c')
    world = forever.parent
    other = _forever(tmp_path / 'Games' / 'b' / 'drive_c')

    assert wow_dir.find_wow_dirs(
        home=tmp_path, environ={'ASKFOREVER_WOW_DIR': str(world)}) == [forever]
    assert wow_dir.find_wow_dirs(
        home=tmp_path, environ={'ASKFOREVER_WOW_DIR': str(forever)}) == [forever]
    assert other not in wow_dir.find_wow_dirs(
        home=tmp_path, environ={'ASKFOREVER_WOW_DIR': str(world)})


def test_env_override_without_game_returns_empty(tmp_path):
    _forever(tmp_path / 'Games' / 'a' / 'drive_c')
    empty = tmp_path / 'vacio'
    empty.mkdir()
    assert wow_dir.find_wow_dirs(
        home=tmp_path, environ={'ASKFOREVER_WOW_DIR': str(empty)}) == []


def test_finds_steam_flatpak_and_bottles_layouts(tmp_path):
    steam = _forever(
        tmp_path / '.local' / 'share' / 'Steam' / 'steamapps'
        / 'compatdata' / '42' / 'pfx' / 'drive_c')
    flatpak_steam = _forever(
        tmp_path / '.var' / 'app' / 'com.valvesoftware.Steam'
        / '.local' / 'share' / 'Steam' / 'steamapps'
        / 'compatdata' / '7' / 'pfx' / 'drive_c')
    flatpak_lutris = _forever(
        tmp_path / '.var' / 'app' / 'net.lutris.Lutris' / 'Games'
        / 'wow' / 'prefix' / 'drive_c')
    bottle = _forever(
        tmp_path / '.local' / 'share' / 'bottles' / 'bottles' / 'Juegos' / 'drive_c')

    found = wow_dir.find_wow_dirs(home=tmp_path, environ={})
    assert found == sorted([steam, flatpak_steam, flatpak_lutris, bottle], key=str)


def test_dedupes_same_resolved_folder(tmp_path):
    real = _forever(tmp_path / 'Games' / 'juego' / 'prefix' / 'drive_c')
    game = tmp_path / 'Games' / 'juego'
    (game / 'drive_c').symlink_to(real.parent)

    found = wow_dir.find_wow_dirs(home=tmp_path, environ={})
    assert len(found) == 1
    assert found[0].resolve() == real.resolve()


def test_ignores_folders_without_wow_exe(tmp_path):
    folder = tmp_path / 'Games' / 'vacio' / 'drive_c' / 'World of Warcraft' / '_forever_'
    folder.mkdir(parents=True)
    assert wow_dir.find_wow_dirs(home=tmp_path, environ={}) == []


def test_resolves_c_drive_with_spaces_and_case(tmp_path):
    prefix = tmp_path / 'prefix'
    wow = _forever(prefix / 'drive_c') / 'Wow.exe'
    (prefix / 'dosdevices').mkdir(parents=True)
    (prefix / 'dosdevices' / 'c:').symlink_to(prefix / 'drive_c')
    proc = _proc(
        tmp_path, 30,
        'C:\\Program Files (x86)\\World of Warcraft\\_forever_\\Wow.exe',
        {'WINEPREFIX': str(prefix)})

    resolved = _window_linux.resolve_windows_path(
        30, 'C:\\Program Files (x86)\\World of Warcraft\\_forever_\\WOW.EXE',
        proc_root=proc)
    assert resolved == str(wow)


def test_resolves_c_drive_without_dosdevices(tmp_path):
    prefix = tmp_path / 'prefix'
    wow = _forever(prefix / 'drive_c') / 'Wow.exe'
    proc = _proc(
        tmp_path, 36,
        'C:\\Program Files (x86)\\World of Warcraft\\_forever_\\Wow.exe',
        {'WINEPREFIX': str(prefix)})

    assert _window_linux.resolve_windows_path(
        36, 'C:\\Program Files (x86)\\World of Warcraft\\_forever_\\Wow.exe',
        proc_root=proc) == str(wow)


def test_resolves_with_default_wine_prefix(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    wow = _forever(tmp_path / '.wine' / 'drive_c') / 'Wow.exe'
    proc = _proc(
        tmp_path, 36,
        'C:\\Program Files (x86)\\World of Warcraft\\_forever_\\Wow.exe', {})

    assert _window_linux.resolve_windows_path(
        36, 'C:\\Program Files (x86)\\World of Warcraft\\_forever_\\Wow.exe',
        proc_root=proc) == str(wow)


def test_resolves_drive_through_dosdevices(tmp_path):
    prefix = tmp_path / 'prefix'
    drive = tmp_path / 'juegos' / 'wine'
    wow = _forever(drive) / 'Wow.exe'
    (prefix / 'dosdevices').mkdir(parents=True)
    (prefix / 'dosdevices' / 'd:').symlink_to(drive)
    proc = _proc(
        tmp_path, 31,
        'D:\\Program Files (x86)\\World of Warcraft\\_forever_\\Wow.exe',
        {'WINEPREFIX': str(prefix)})

    assert _window_linux.resolve_windows_path(
        31, 'D:\\Program Files (x86)\\World of Warcraft\\_forever_\\Wow.exe',
        proc_root=proc) == str(wow)


def test_resolves_steam_compat_data_path(tmp_path):
    compat = tmp_path / 'compatdata' / '42'
    wow = _forever(compat / 'pfx' / 'drive_c') / 'Wow.exe'
    proc = _proc(
        tmp_path, 32,
        'C:\\Program Files (x86)\\World of Warcraft\\_forever_\\Wow.exe',
        {'STEAM_COMPAT_DATA_PATH': str(compat)})

    assert _window_linux.resolve_windows_path(
        32, 'C:\\Program Files (x86)\\World of Warcraft\\_forever_\\Wow.exe',
        proc_root=proc) == str(wow)


def test_resolves_z_drive(tmp_path):
    prefix = tmp_path / 'prefix'
    root = tmp_path / 'zroot'
    wow = _forever(root / 'home' / 'u' / 'Games' / 'wow') / 'Wow.exe'
    windows = ('Z:\\home\\u\\Games\\wow\\Program Files (x86)\\'
               'World of Warcraft\\_forever_\\Wow.exe')
    (prefix / 'dosdevices').mkdir(parents=True)
    (prefix / 'dosdevices' / 'z:').symlink_to(root)
    proc = _proc(tmp_path, 33, windows, {'WINEPREFIX': str(prefix)})

    assert _window_linux.resolve_windows_path(33, windows, proc_root=proc) == str(wow)


def test_maps_fallback_handles_spaces(tmp_path):
    wow = _forever(tmp_path / 'juego') / 'Wow.exe'
    maps = (f'7f00-7f01 r-xp 00000000 08:01 1234 {wow}\n'
            '7f02-7f03 r--p 00000000 08:01 1234 /usr/lib/libc.so\n')
    proc = _proc(tmp_path, 34, 'Z:\\perdido\\Wow.exe', {}, maps)
    # Sin prefijo, la ruta no existe: la pista válida es el archivo mapeado.
    assert _window_linux.resolve_windows_path(
        34, 'Z:\\perdido\\Wow.exe', proc_root=proc) == str(wow)


def test_unresolvable_path_returns_none(tmp_path):
    proc = _proc(tmp_path, 35, 'C:\\Wow.exe', {})
    assert _window_linux.resolve_windows_path(
        35, 'C:\\Wow.exe', proc_root=proc) is None


def test_find_game_window_uses_resolved_path(tmp_path):
    prefix = tmp_path / 'prefix'
    wow = _forever(prefix / 'drive_c') / 'Wow.exe'
    proc = _proc(
        tmp_path, 40,
        'C:\\Program Files (x86)\\World of Warcraft\\_forever_\\Wow.exe',
        {'WINEPREFIX': str(prefix)})

    found = capture_window.find_game_window(
        proc_root=proc, open_display=lambda: None,
        geometry_path=tmp_path / 'no-geometry.json')
    assert found is not None
    assert found.exe_path == str(wow)


def test_find_wow_cli_prints_folders(monkeypatch, capsys):
    folder = Path('/juegos/wow/_forever_')
    monkeypatch.setattr(wow_dir, 'find_wow_dirs', lambda: [folder])

    assert cli.main(['find-wow']) == 0
    assert capsys.readouterr().out == f'{folder}\n'


def test_find_wow_cli_reports_when_missing(monkeypatch, capsys):
    monkeypatch.setattr(wow_dir, 'find_wow_dirs', lambda: [])

    assert cli.main(['find-wow']) == 1
    captured = capsys.readouterr()
    assert captured.out == ''
    assert 'No se encontró la carpeta de WoW Forever' in captured.err
