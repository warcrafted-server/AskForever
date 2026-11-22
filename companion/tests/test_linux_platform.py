import sys

import pytest

from askforever.app import main as app_main
from askforever.capture import window as capture_window

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='ruta específica de Linux')


def _fake_proc(tmp_path, entries):
    for pid, args in entries.items():
        directory = tmp_path / str(pid)
        directory.mkdir()
        (directory / 'cmdline').write_bytes(b'\0'.join(a.encode() for a in args) + b'\0')
    (tmp_path / 'self').mkdir()
    return tmp_path


def test_find_game_window_detects_wine_wow_process(tmp_path):
    proc = _fake_proc(tmp_path, {
        10: ['/usr/bin/bash'],
        20: ['Z:\\home\\u\\Games\\wow\\_forever_\\Wow.exe', '-console'],
    })
    window = capture_window.find_game_window(proc_root=proc)
    assert window is not None
    assert window.hwnd == 20
    assert window.exe_path.endswith('Wow.exe')
    assert (window.x, window.y) == (0, 0)


def test_find_game_window_returns_none_without_game(tmp_path):
    proc = _fake_proc(tmp_path, {10: ['/usr/bin/bash']})
    assert capture_window.find_game_window(proc_root=proc) is None


def test_process_image_path_reads_first_argument(monkeypatch):
    from askforever.capture import _window_linux

    monkeypatch.setattr(_window_linux, '_read_cmdline', lambda pid: ['C:\\Wow.exe', 'x'])
    assert capture_window._process_image_path(1) == 'C:\\Wow.exe'


def test_single_instance_lock_detects_second_holder(monkeypatch, tmp_path):
    monkeypatch.setattr(app_main, '_lock_path', lambda: tmp_path / 'app.lock')
    first, first_exists = app_main.acquire_single_instance()
    second, second_exists = app_main.acquire_single_instance()
    try:
        assert first_exists is False
        assert second_exists is True
    finally:
        app_main._release_instance_mutex(second, already_exists=True)
        app_main._release_instance_mutex(first)
    third, third_exists = app_main.acquire_single_instance()
    assert third_exists is False
    app_main._release_instance_mutex(third)
