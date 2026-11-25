import json
import sys

import pytest

from askforever.app import main as app_main
from askforever.capture import window as capture_window
from askforever.capture.x11 import XWindow

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='ruta específica de Linux')


def _fake_proc(tmp_path, entries):
    for pid, args in entries.items():
        directory = tmp_path / str(pid)
        directory.mkdir()
        (directory / 'cmdline').write_bytes(b'\0'.join(a.encode() for a in args) + b'\0')
    (tmp_path / 'self').mkdir()
    return tmp_path


class FakeX11Display:
    def __init__(self, window=None, error=None):
        self.window = window
        self.error = error
        self.closed = False

    def find_game_window(self):
        if self.error:
            raise self.error
        return self.window

    def close(self):
        self.closed = True


def test_find_game_window_detects_wine_wow_process(tmp_path):
    proc = _fake_proc(tmp_path, {
        10: ['/usr/bin/bash'],
        20: ['Z:\\home\\u\\Games\\wow\\_forever_\\Wow.exe', '-console'],
    })
    window = capture_window.find_game_window(
        proc_root=proc, open_display=lambda: None,
        geometry_path=tmp_path / 'no-geometry.json')
    assert window is not None
    assert window.hwnd == 20
    assert window.exe_path.endswith('Wow.exe')
    assert (window.x, window.y) == (0, 0)


def test_find_game_window_uses_x11_geometry(tmp_path):
    proc = _fake_proc(tmp_path, {20: ['C:\\Wow.exe']})
    display = FakeX11Display(XWindow(77, 100, 50, 2560, 1440))
    window = capture_window.find_game_window(
        proc_root=proc, open_display=lambda: display,
        geometry_path=tmp_path / 'no-geometry.json')
    assert display.closed is True
    assert (window.x, window.y) == (100, 50)
    assert (window.width, window.height) == (2560, 1440)


def test_find_game_window_uses_portal_geometry_without_x11(tmp_path):
    proc = _fake_proc(tmp_path, {20: ['C:\\Wow.exe']})
    geometry = tmp_path / 'portal-geometry.json'
    geometry.write_text(json.dumps(
        {'x': 1920, 'y': 20, 'width': 2560, 'height': 1440}), encoding='utf-8')
    window = capture_window.find_game_window(
        proc_root=proc, open_display=lambda: None, geometry_path=geometry)
    assert (window.x, window.y) == (1920, 20)
    assert (window.width, window.height) == (2560, 1440)


def test_find_game_window_prefers_x11_geometry_over_portal(tmp_path):
    proc = _fake_proc(tmp_path, {20: ['C:\\Wow.exe']})
    geometry = tmp_path / 'portal-geometry.json'
    geometry.write_text(json.dumps(
        {'x': 1920, 'y': 20, 'width': 2560, 'height': 1440}), encoding='utf-8')
    display = FakeX11Display(XWindow(77, 100, 50, 1920, 1080))
    window = capture_window.find_game_window(
        proc_root=proc, open_display=lambda: display, geometry_path=geometry)
    assert (window.x, window.y) == (100, 50)
    assert (window.width, window.height) == (1920, 1080)


def test_find_game_window_ignores_invalid_portal_geometry(tmp_path):
    proc = _fake_proc(tmp_path, {20: ['C:\\Wow.exe']})
    geometry = tmp_path / 'portal-geometry.json'
    payloads = (
        'no es json',
        json.dumps({'x': 1, 'y': 2, 'width': 0, 'height': 1080}),
        json.dumps({'x': 1, 'y': 2, 'width': 1920, 'height': -1}),
        json.dumps({'x': 1.5, 'y': 2, 'width': 1920, 'height': 1080}),
        json.dumps({'x': '1', 'y': 2, 'width': 1920, 'height': 1080}),
        json.dumps({'x': 1, 'y': 2, 'width': 1920}),
    )
    for payload in payloads:
        geometry.write_text(payload, encoding='utf-8')
        window = capture_window.find_game_window(
            proc_root=proc, open_display=lambda: None, geometry_path=geometry)
        assert (window.x, window.y) == (0, 0)
        assert (window.width, window.height) == (1920, 1080)


def test_find_game_window_falls_back_to_provisional_geometry(tmp_path):
    proc = _fake_proc(tmp_path, {20: ['C:\\Wow.exe']})
    geometry = tmp_path / 'no-geometry.json'
    for display in (None, FakeX11Display(), FakeX11Display(error=RuntimeError('boom'))):
        window = capture_window.find_game_window(
            proc_root=proc, geometry_path=geometry,
            open_display=lambda display=display: display)
        assert (window.x, window.y) == (0, 0)
        assert (window.width, window.height) == (1920, 1080)


def test_find_game_window_does_not_open_display_without_game(tmp_path):
    proc = _fake_proc(tmp_path, {10: ['/usr/bin/bash']})

    def open_display():
        raise AssertionError('no debe abrirse la pantalla sin juego')

    assert capture_window.find_game_window(
        proc_root=proc, open_display=open_display) is None


def test_find_game_window_returns_none_without_game(tmp_path):
    proc = _fake_proc(tmp_path, {10: ['/usr/bin/bash']})
    assert capture_window.find_game_window(proc_root=proc, open_display=lambda: None) is None


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
