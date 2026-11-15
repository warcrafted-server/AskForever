"""Pruebas de la geometría y los estados del overlay, y de los comandos nuevos."""

from __future__ import annotations

import json
import threading
import time
import types

import pytest

import askforever.cli as cli
from askforever.capture.grabber import ReceivedMessage
from askforever.overlay.window import (
    Overlay,
    OverlayState,
    OverlayUnavailable,
    VISIBLE_ALPHA,
    build_state,
    compute_position,
    game_in_front,
    wrap_estimate,
)


def _client(x, y, width, height):
    return types.SimpleNamespace(x=x, y=y, width=width, height=height)


@pytest.mark.parametrize('area,width,height', [
    (_client(0, 0, 1920, 1080), 460, 200),
    (_client(100, 50, 2560, 1440), 460, 200),
    (_client(0, 0, 1280, 720), 460, 200),
    (_client(0, 0, 800, 600), 460, 200),
])
def test_compute_position_avoids_strip(area, width, height):
    x, y = compute_position(area, width, height)

    assert x >= area.x
    assert y >= area.y
    assert x + width <= area.x + area.width
    assert y + height <= area.y + area.height
    assert x == area.x + area.width - width - 24

    strip_right = area.x + 512
    strip_bottom = area.y + 32
    overlaps = (x < strip_right and x + width > area.x
                and y < strip_bottom and y + height > area.y)
    assert overlaps is False


def test_compute_position_defaults():
    x, y = compute_position(None, 460, 200)
    assert x == 1920 - 460 - 24
    assert y == int(1080 * 0.18)


def test_build_state_thinking():
    state = build_state('thinking', 'esES', question='¿Dónde está Hogger?', now=10.0)
    assert state == OverlayState('thinking', '¿Dónde está Hogger?', 'Pensando…', None)
    assert build_state('thinking', 'enUS', question='Where?').body == 'Thinking…'
    assert build_state('thinking', 'enUS', question='Where?').expires_at is None


def test_build_state_answer_and_error():
    answer = build_state('answer', 'esES', question='p', text='t', now=5.0, ttl=30.0)
    assert answer.kind == 'answer'
    assert answer.body == 't'
    assert answer.expires_at == 35.0

    error = build_state('error', 'enUS', question='p', text='fallo', now=1.0, ttl=4.0)
    assert error.kind == 'error'
    assert error.body == 'fallo'
    assert error.expires_at == 5.0


def test_build_state_truncates_question():
    long_state = build_state('thinking', 'esES', question='a' * 150)
    assert long_state.title.endswith('…')
    assert len(long_state.title) <= 91

    exact = build_state('thinking', 'esES', question='b' * 90)
    assert exact.title == 'b' * 90


def test_wrap_estimate():
    assert wrap_estimate('') == 1
    assert wrap_estimate(None) == 1
    assert wrap_estimate('a' * 60) == 1
    assert wrap_estimate('a' * 61) == 2
    assert wrap_estimate('a' * 120) == 2
    assert wrap_estimate('linea1\nlinea2') == 2
    assert wrap_estimate(12345) == 1


def test_overlay_queues_states_without_tk():
    overlay = Overlay(window_fn=lambda: None)

    overlay.show_thinking('pregunta', 'esES')
    overlay.show_answer('pregunta', 'respuesta', 'esES')
    overlay.show_error('fallo', 'enUS')
    overlay.hide()

    thinking = overlay.queue.get_nowait()
    answer = overlay.queue.get_nowait()
    error = overlay.queue.get_nowait()
    hidden = overlay.queue.get_nowait()

    assert isinstance(thinking, OverlayState)
    assert thinking.kind == 'thinking'
    assert answer.kind == 'answer' and answer.body == 'respuesta'
    assert error.kind == 'error' and error.body == 'fallo'
    assert hidden is None


def test_apply_click_through_does_not_raise():
    result = Overlay.apply_click_through(0)
    assert isinstance(result, bool)


def test_game_in_front_truth_table():
    def is_window(hwnd):
        return hwnd in (11, 12)

    assert game_in_front(11, 11, is_window, lambda _hwnd: False) is True
    assert game_in_front(11, 22, is_window, lambda _hwnd: False) is False
    assert game_in_front(11, 11, is_window, lambda _hwnd: True) is False
    assert game_in_front(99, 99, is_window, lambda _hwnd: False) is False


class _FakeUser32:
    def __init__(self):
        self.foreground = 100
        self.valid = {100, 123}
        self.iconic = set()
        self.events = []
        self.show_calls = []
        self.set_pos_calls = []
        self.style_calls = []
        self.style = 0

    def GetParent(self, hwnd):
        return hwnd + 1000

    def GetWindowLongPtrW(self, hwnd, index):
        return self.style

    def SetWindowLongPtrW(self, hwnd, index, value):
        self.style = value
        self.style_calls.append((hwnd, index, value))
        self.events.append(('style', hwnd))
        return value

    def ShowWindow(self, hwnd, command):
        self.show_calls.append((hwnd, command))
        self.events.append(('show', hwnd))
        return True

    def SetWindowPos(self, hwnd, insert_after, x, y, width, height, flags):
        self.set_pos_calls.append((hwnd, insert_after, x, y, width, height, flags))
        self.events.append(('pos', hwnd))
        return True

    def IsWindow(self, hwnd):
        return hwnd in self.valid

    def IsIconic(self, hwnd):
        return hwnd in self.iconic

    def GetForegroundWindow(self):
        return self.foreground


class _FakeLabel:
    def __init__(self):
        self.text = ''
        self.packed = False
        self.colour = None

    def pack(self, **_kwargs):
        self.packed = True

    def pack_forget(self):
        self.packed = False

    def configure(self, **kwargs):
        if 'text' in kwargs:
            self.text = kwargs['text']
        if 'fg' in kwargs:
            self.colour = kwargs['fg']


class _FakeRoot:
    def __init__(self):
        self.alphas = []
        self.geometries = []
        self.after_calls = []
        self.deiconify_calls = 0
        self.destroyed = False

    def update_idletasks(self):
        return None

    def winfo_id(self):
        return 123

    def winfo_reqheight(self):
        return 120

    def attributes(self, name, value=None):
        if name == '-alpha':
            self.alphas.append(value)
        return None

    def geometry(self, value):
        self.geometries.append(value)

    def after(self, milliseconds, callback):
        self.after_calls.append((milliseconds, callback))

    def deiconify(self):
        self.deiconify_calls += 1

    def destroy(self):
        self.destroyed = True


class _FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


def _fake_overlay(user32, window_fn):
    overlay = Overlay(ttl=10.0, window_fn=window_fn, clock=_FakeClock(), user32=user32)
    overlay._root = _FakeRoot()
    overlay._title_label = _FakeLabel()
    overlay._body_label = _FakeLabel()
    overlay._mapped = True
    return overlay


def test_overlay_maps_without_activation():
    user32 = _FakeUser32()
    overlay = Overlay(user32=user32)
    overlay._root = _FakeRoot()

    overlay._map_invisible()

    hwnd = 1123
    assert overlay._mapped is True
    assert overlay._root.deiconify_calls == 0
    assert user32.show_calls == [(hwnd, 4)]
    assert user32.style_calls[0][0] == hwnd
    assert user32.events.index(('style', hwnd)) < user32.events.index(('show', hwnd))
    assert user32.set_pos_calls[0][1] == -1
    assert overlay._root.alphas == [0.0]


def test_overlay_hides_and_restores_with_foreground():
    user32 = _FakeUser32()
    client = types.SimpleNamespace(hwnd=100, x=0, y=0, width=1920, height=1080)
    calls = []

    def window_fn():
        calls.append(1)
        return client

    overlay = _fake_overlay(user32, window_fn)
    state = build_state('answer', 'esES', question='pregunta', text='respuesta',
                        now=0.0, ttl=10.0)
    overlay._apply(state)
    assert overlay._root.alphas[-1] == VISIBLE_ALPHA
    assert overlay._state_active is True

    expires_at = overlay._expires_at
    user32.foreground = 222
    overlay.clock.value = 0.2
    overlay._poll()
    assert overlay._root.alphas[-1] == 0.0
    assert overlay._state_active is True
    assert overlay._expires_at == expires_at

    user32.foreground = 100
    overlay.clock.value = 0.4
    overlay._poll()
    assert overlay._root.alphas[-1] == VISIBLE_ALPHA

    overlay.clock.value = 10.1
    overlay._poll()
    assert overlay._root.alphas[-1] == 0.0
    assert overlay._state_active is False
    assert len(calls) <= 2


def test_overlay_refreshes_game_window_slowly():
    user32 = _FakeUser32()
    client = types.SimpleNamespace(hwnd=100, x=0, y=0, width=1920, height=1080)
    calls = []
    overlay = _fake_overlay(user32, lambda: calls.append(1) or client)

    for step in range(11):
        overlay.clock.value = step * 0.2
        overlay._visible_allowed()

    assert len(calls) <= 2


def _tk_available() -> bool:
    try:
        import tkinter  # noqa: F401
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _tk_available(), reason='Tk no disponible')
def test_overlay_runs_with_tk():
    overlay = Overlay(ttl=5.0)
    overlay.window_fn = lambda: _client(0, 0, 1920, 1080)
    stop_event = threading.Event()

    overlay.show_thinking('pregunta', 'esES')
    overlay.show_answer('pregunta', 'respuesta', 'esES')

    def stop_later():
        time.sleep(0.3)
        stop_event.set()

    threading.Thread(target=stop_later, daemon=True).start()
    try:
        overlay.run(stop_event)
    except OverlayUnavailable as error:
        pytest.skip(f'No se pudo crear la ventana Tk: {error}')
    finally:
        overlay.close()


def _message_data(question, lang='esES') -> bytes:
    document = {'v': 1, 'lang': lang, 'q': question, 'ctx': {'lvl': 10}}
    return json.dumps(document, ensure_ascii=False).encode('utf-8')


def _fake_grabber(messages):
    class FakeGrabber:
        def __init__(self, on_message, fps=30.0):
            self.on_message = on_message
            self.captures = len(messages)
            self.valid_frames = len(messages)
            self.messages = 0
            self.errors = 0

        def run(self, stop_event):
            for message in messages:
                self.messages += 1
                self.on_message(message)

    return FakeGrabber


def _recording_overlay(events):
    class RecordingOverlay:
        def __init__(self, ttl=30.0):
            self.ttl = ttl

        def show_thinking(self, question, lang):
            events.append(['thinking', question, lang])

        def show_answer(self, question, text, lang):
            events.append(['answer', question, text, lang])

        def show_error(self, text, lang):
            events.append(['error', text, lang])

        def hide(self):
            events.append(['hide'])

        def run(self, stop_event=None):
            return None

        def close(self):
            events.append(['close'])

    return RecordingOverlay


class FakeProvider:
    def chat(self, system, user, *, max_tokens=None, temperature=0.3):
        return 'La respuesta de prueba'


def test_run_command_calls_thinking_then_answer(monkeypatch, capsys):
    events = []
    messages = [ReceivedMessage(1, 1, _message_data('¿Dónde está Hogger?'), 0.0, 0.5)]

    monkeypatch.setattr(cli, 'Grabber', _fake_grabber(messages))
    monkeypatch.setattr(cli, 'OverlaySupervisor', _recording_overlay(events))
    monkeypatch.setattr(cli, 'provider_from_config', lambda: FakeProvider())

    assert cli.main(['run', '--no-data', '--no-web']) == 0
    time.sleep(0.2)

    kinds = [event[0] for event in events]
    assert 'thinking' in kinds
    assert 'answer' in kinds
    assert kinds.index('thinking') < kinds.index('answer')

    answer = next(event for event in events if event[0] == 'answer')
    assert answer[2] == 'La respuesta de prueba'

    output = capsys.readouterr().out
    assert '¿Dónde está Hogger?' in output
    assert 'Respuesta (' in output


def test_run_generation_prevents_stale_answer(monkeypatch):
    events = []
    gate = threading.Event()

    class SlowProvider:
        def chat(self, system, user, *, max_tokens=None, temperature=0.3):
            if 'primera' in user:
                gate.wait(2.0)
                return 'antigua'
            return 'nueva'

    messages = [
        ReceivedMessage(1, 1, _message_data('primera'), 0.0, 0.1),
        ReceivedMessage(2, 1, _message_data('segunda'), 0.0, 0.2),
    ]
    monkeypatch.setattr(cli, 'Grabber', _fake_grabber(messages))
    monkeypatch.setattr(cli, 'OverlaySupervisor', _recording_overlay(events))
    monkeypatch.setattr(cli, 'provider_from_config', lambda: SlowProvider())

    assert cli.main(['run', '--no-data', '--no-web']) == 0
    time.sleep(0.2)
    gate.set()
    time.sleep(0.3)

    answers = [event for event in events if event[0] == 'answer']
    assert any(event[2] == 'nueva' for event in answers)
    assert all(event[2] != 'antigua' for event in answers)


def test_run_no_ai_only_shows_thinking(monkeypatch):
    events = []
    messages = [ReceivedMessage(1, 1, _message_data('hola'), 0.0, 0.1)]

    def forbidden():
        raise AssertionError('no debe crearse el proveedor con --no-ai')

    monkeypatch.setattr(cli, 'Grabber', _fake_grabber(messages))
    monkeypatch.setattr(cli, 'OverlaySupervisor', _recording_overlay(events))
    monkeypatch.setattr(cli, 'provider_from_config', forbidden)

    assert cli.main(['run', '--no-ai', '--no-data', '--no-web']) == 0
    time.sleep(0.1)

    kinds = [event[0] for event in events]
    assert 'thinking' in kinds
    assert 'answer' not in kinds
    assert 'error' not in kinds


def test_run_provider_failure_shows_error(monkeypatch):
    events = []
    messages = [ReceivedMessage(1, 1, _message_data('hola'), 0.0, 0.1)]

    def failing_provider():
        raise cli.ProviderError('auth', 'no key')

    monkeypatch.setattr(cli, 'Grabber', _fake_grabber(messages))
    monkeypatch.setattr(cli, 'OverlaySupervisor', _recording_overlay(events))
    monkeypatch.setattr(cli, 'provider_from_config', failing_provider)

    assert cli.main(['run', '--no-data', '--no-web']) == 0
    time.sleep(0.1)

    errors = [event for event in events if event[0] == 'error']
    assert errors
    assert errors[0][1] == cli.ProviderError('auth').user_message('esES')


def test_overlay_positions_with_set_window_pos():
    # Tk ignoraba la posición tras mostrar la ventana sin activarla: debe fijarse con SetWindowPos.
    user32 = _FakeUser32()
    client = types.SimpleNamespace(hwnd=100, x=0, y=0, width=1920, height=1080)
    overlay = _fake_overlay(user32, lambda: client)
    user32.foreground = 100
    overlay._apply(build_state('answer', 'esES', question='p', text='r', now=0.0, ttl=10.0))
    moves = [call for call in user32.set_pos_calls if not call[6] & 0x0001]
    assert moves, 'la ventana clásica no se colocó con SetWindowPos'
    x, y = moves[-1][2], moves[-1][3]
    assert x > 0 and y > 0
