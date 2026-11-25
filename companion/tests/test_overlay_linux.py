"""Pruebas del overlay en Linux con una pantalla X11 simulada, sin servidor X ni juego."""

from __future__ import annotations

import logging
import types

import pytest

from askforever.overlay import window as overlay_window
from askforever.overlay.window import (
    VISIBLE_ALPHA,
    Overlay,
    build_state,
)

WIN_ID = 123
FRAME_ID = 0x2A


class _FakeDisplay:
    """Pantalla X falsa: solo lo que consulta el overlay."""

    def __init__(self, active=True, passthrough=True):
        self.active = active
        self.passthrough_result = passthrough
        self.passthrough_calls = []
        self.active_calls = 0
        self.closed = False

    def game_is_active(self):
        self.active_calls += 1
        return self.active

    def set_input_passthrough(self, window_ids):
        self.passthrough_calls.append(list(window_ids))
        return self.passthrough_result

    def close(self):
        self.closed = True


class _FakeLabel:
    def __init__(self):
        self.text = ''
        self.packed = False

    def pack(self, **_kwargs):
        self.packed = True

    def pack_forget(self):
        self.packed = False

    def configure(self, **kwargs):
        if 'text' in kwargs:
            self.text = kwargs['text']


class _FakeRoot:
    def __init__(self):
        self.alphas = []
        self.geometries = []
        self.attributes_set = []
        self.after_calls = []
        self.deiconify_calls = 0
        self.update_calls = 0
        self.lift_calls = 0
        self.destroyed = False

    def update_idletasks(self):
        return None

    def update(self):
        self.update_calls += 1

    def winfo_id(self):
        return WIN_ID

    def wm_frame(self):
        return hex(FRAME_ID)

    def winfo_reqheight(self):
        return 120

    def attributes(self, name, value=None):
        self.attributes_set.append((name, value))
        if name == '-alpha':
            self.alphas.append(value)
        return None

    def geometry(self, value):
        self.geometries.append(value)

    def lift(self):
        self.lift_calls += 1

    def deiconify(self):
        self.deiconify_calls += 1

    def after(self, milliseconds, callback):
        after_id = f'after-{len(self.after_calls) + 1}'
        self.after_calls.append((after_id, milliseconds, callback))
        return after_id

    def destroy(self):
        self.destroyed = True


class _FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


def _client():
    return types.SimpleNamespace(hwnd=4242, x=100, y=50, width=1920, height=1080)


def _linux_overlay(display, found=True, clock=None):
    window_fn = _client if found else (lambda: None)
    overlay = Overlay(window_fn=window_fn, clock=clock or _FakeClock(),
                      x11_display=display)
    overlay._root = _FakeRoot()
    overlay._title_label = _FakeLabel()
    overlay._body_label = _FakeLabel()
    return overlay


def _answer_state():
    return build_state('answer', 'esES', question='', text='respuesta',
                       now=0.0, ttl=10.0)


@pytest.mark.parametrize('active,found,expected', [
    (True, True, VISIBLE_ALPHA),
    (None, True, VISIBLE_ALPHA),
    (False, True, 0.0),
    (True, False, 0.0),
    (None, False, 0.0),
])
def test_linux_visibility_follows_game_and_focus(active, found, expected):
    display = _FakeDisplay(active=active)
    overlay = _linux_overlay(display, found=found)

    overlay._map_invisible()
    overlay._apply(_answer_state())

    assert overlay._root.alphas[-1] == expected
    assert overlay._shown is (expected > 0)


def test_linux_passthrough_after_mapping_and_after_showing():
    display = _FakeDisplay(active=True)
    overlay = _linux_overlay(display)

    overlay._map_invisible()

    assert overlay._mapped is True
    assert display.passthrough_calls == [[WIN_ID, FRAME_ID]]

    overlay._apply(_answer_state())

    assert display.passthrough_calls[-1] == [WIN_ID, FRAME_ID]
    assert len(display.passthrough_calls) == 2
    # Colocar y mostrar usa geometry y topmost de Tk, nunca SetWindowPos.
    assert overlay._root.geometries[-1] == '460x120+1536+244'
    assert ('-topmost', True) in overlay._root.attributes_set
    assert overlay._root.lift_calls >= 1


def test_linux_reapplies_passthrough_when_game_returns_to_front():
    display = _FakeDisplay(active=False)
    clock = _FakeClock()
    overlay = _linux_overlay(display, clock=clock)

    overlay._map_invisible()
    overlay._apply(build_state('thinking', 'esES', question='p', now=0.0))
    assert overlay._root.alphas[-1] == 0.0

    passthrough_calls = len(display.passthrough_calls)
    display.active = True
    clock.value = 0.3
    overlay._poll()

    assert overlay._root.alphas[-1] == VISIBLE_ALPHA
    assert len(display.passthrough_calls) == passthrough_calls + 1


def test_linux_still_shows_without_passthrough_and_warns_once(caplog):
    caplog.set_level(logging.WARNING, logger='askforever.overlay')
    display = _FakeDisplay(active=True, passthrough=False)
    overlay = _linux_overlay(display)

    overlay._map_invisible()
    overlay._apply(_answer_state())
    overlay._apply(build_state('thinking', 'esES', question='p', now=0.0))

    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert overlay._root.alphas[-1] == VISIBLE_ALPHA


def test_linux_shows_without_display_and_warns_once(caplog):
    caplog.set_level(logging.WARNING, logger='askforever.overlay')
    display = _FakeDisplay(active=True)
    overlay = _linux_overlay(display)
    overlay._x11 = None
    overlay._x11_opened = True

    overlay._map_invisible()
    overlay._apply(_answer_state())

    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert overlay._root.alphas[-1] == VISIBLE_ALPHA


def test_linux_path_never_loads_user32(monkeypatch):
    calls = []
    monkeypatch.setattr(overlay_window, '_load_user32', lambda: calls.append(1) or None)
    display = _FakeDisplay(active=True)
    overlay = _linux_overlay(display)

    overlay._map_invisible()
    overlay._apply(_answer_state())
    overlay._visible_allowed()
    overlay._place(0, 0, 100, 50)
    overlay._set_topmost()
    overlay._apply_passthrough()

    assert calls == []
    assert overlay._user32 is None


def test_linux_display_opens_once_and_closes_on_shutdown(monkeypatch):
    monkeypatch.setattr(overlay_window, 'sys', types.SimpleNamespace(platform='linux'))
    display = _FakeDisplay(active=True)
    opened = []
    monkeypatch.setattr(overlay_window.x11, 'open_display',
                        lambda: opened.append(1) or display)
    overlay = Overlay(window_fn=_client, clock=_FakeClock())
    overlay._root = _FakeRoot()
    overlay._title_label = _FakeLabel()
    overlay._body_label = _FakeLabel()

    assert overlay._linux is True
    assert opened == []

    overlay._map_invisible()
    overlay._apply(_answer_state())
    overlay._visible_allowed()

    assert opened == [1]
    assert display.active_calls >= 1

    overlay._shutdown()

    assert display.closed is True
    assert overlay._root.destroyed is True
