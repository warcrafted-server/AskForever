import contextlib
import ctypes
import sys
import types

import pytest

from askforever.capture import x11


def _attributes(map_state: int, width: int, height: int) -> x11.XWindowAttributes:
    attributes = x11.XWindowAttributes()
    attributes.map_state = map_state
    attributes.width = width
    attributes.height = height
    return attributes


def _display() -> x11.X11Display:
    display = object.__new__(x11.X11Display)
    display._display = ctypes.c_void_p(1)
    display._xlib = None
    display._root = 1
    display._atoms = {}
    display._closed = False
    display.clock = lambda: 0.0
    display._game_exists = None
    display._game_exists_at = 0.0
    return display


def test_is_game_matches_class_case_insensitively():
    assert x11.is_game(('wow.exe',), '')
    assert x11.is_game(('WOW.EXE',), 'cualquier título')
    assert x11.is_game(('wine', 'WoW.exe'), '')


def test_is_game_accepts_exact_title_for_proton():
    assert x11.is_game(('wine-preloader',), 'World of Warcraft')
    assert not x11.is_game(('wine-preloader',), 'World of Warcraft - 1.12')
    assert not x11.is_game((), '')
    assert not x11.is_game(('wow.exe.bak',), 'World')


def test_xwindow_keeps_root_coordinates():
    window = x11.XWindow(42, 10, 20, 1920, 1080)
    assert (window.window_id, window.x, window.y) == (42, 10, 20)
    assert (window.width, window.height) == (1920, 1080)


def test_open_display_returns_none_off_linux(monkeypatch):
    monkeypatch.setattr(x11, 'sys', types.SimpleNamespace(platform='win32'))
    assert x11.open_display() is None


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='X11 solo en Linux')
def test_open_display_returns_none_without_xlib(monkeypatch):
    monkeypatch.setattr(x11, '_load_library', lambda name, fallback: None)
    assert x11.open_display() is None


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='X11 solo en Linux')
def test_open_display_returns_none_without_display(monkeypatch):
    monkeypatch.delenv('DISPLAY', raising=False)
    assert x11.open_display() is None


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='X11 solo en Linux')
def test_open_display_returns_none_if_xopen_fails(monkeypatch):
    fake_xlib = types.SimpleNamespace(XOpenDisplay=lambda name: None)
    monkeypatch.setattr(x11, '_load_library', lambda name, fallback: fake_xlib)
    monkeypatch.setattr(x11, '_configure_xlib', lambda xlib: None)
    assert x11.open_display() is None


def test_find_game_window_picks_largest_viewable_match(monkeypatch):
    display = _display()
    children = {1: [2, 3], 2: [], 3: [4, 5], 4: [], 5: []}
    attributes = {
        2: _attributes(x11.IS_VIEWABLE, 800, 600),
        3: _attributes(0, 4000, 4000),
        4: _attributes(x11.IS_VIEWABLE, 1920, 1080),
        5: _attributes(x11.IS_VIEWABLE, 2560, 1440),
    }
    classes = {2: ('terminal',), 3: ('wow.exe',), 4: ('wow.exe',), 5: ('wine',)}
    titles = {2: 'Terminal', 3: 'World of Warcraft', 4: 'WoW', 5: 'World of Warcraft'}
    titles_queried: set[int] = set()

    monkeypatch.setattr(display, '_protected', lambda: contextlib.nullcontext())
    monkeypatch.setattr(display, '_children', lambda window: children[window])
    monkeypatch.setattr(display, '_attributes', lambda window: attributes[window])
    monkeypatch.setattr(display, '_window_classes', lambda window: classes[window])

    def title(window):
        titles_queried.add(window)
        return titles[window]

    monkeypatch.setattr(display, '_window_title', title)
    monkeypatch.setattr(display, '_translate', lambda window: (window * 10, window * 20))

    window = display.find_game_window()
    assert window == x11.XWindow(5, 50, 100, 2560, 1440)
    assert 3 not in titles_queried


def test_find_game_window_returns_none_without_game(monkeypatch):
    display = _display()
    monkeypatch.setattr(display, '_protected', lambda: contextlib.nullcontext())
    monkeypatch.setattr(display, '_children', lambda window: {1: [2], 2: []}[window])
    monkeypatch.setattr(
        display, '_attributes', lambda window: _attributes(x11.IS_VIEWABLE, 800, 600))
    monkeypatch.setattr(display, '_window_classes', lambda window: ('terminal',))
    monkeypatch.setattr(display, '_window_title', lambda window: 'Terminal')
    assert display.find_game_window() is None


def test_game_is_active_reads_active_window(monkeypatch):
    display = _display()
    state = {'active': None}
    walks = []
    monkeypatch.setattr(display, '_protected', lambda: contextlib.nullcontext())
    monkeypatch.setattr(display, '_atom', lambda name: 1)
    monkeypatch.setattr(display, '_property', lambda window, atom: state['active'])
    monkeypatch.setattr(
        display, '_window_classes', lambda window: ('wow.exe',) if window == 42 else ('konsole',))
    monkeypatch.setattr(display, '_window_title', lambda window: '')
    # Sin ventana X del juego, el foco no depende de X y es desconocido.
    monkeypatch.setattr(display, '_find_game_window', lambda: walks.append(1) or None)

    assert display.game_is_active() is None
    assert walks == []

    state['active'] = 0
    assert display.game_is_active() is None
    assert len(walks) == 1

    state['active'] = 43
    assert display.game_is_active() is None
    assert len(walks) == 1

    state['active'] = 42
    assert display.game_is_active() is True
    assert len(walks) == 1


def test_game_is_active_is_false_when_game_window_is_not_in_front(monkeypatch):
    display = _display()
    monkeypatch.setattr(display, '_protected', lambda: contextlib.nullcontext())
    monkeypatch.setattr(display, '_atom', lambda name: 1)
    monkeypatch.setattr(display, '_property', lambda window, atom: 43)
    monkeypatch.setattr(display, '_window_classes', lambda window: ('konsole',))
    monkeypatch.setattr(display, '_window_title', lambda window: '')
    monkeypatch.setattr(
        display, '_find_game_window', lambda: x11.XWindow(42, 0, 0, 1920, 1080))
    assert display.game_is_active() is False


def test_game_is_active_does_not_walk_tree_when_game_is_active(monkeypatch):
    display = _display()
    walks = []
    monkeypatch.setattr(display, '_protected', lambda: contextlib.nullcontext())
    monkeypatch.setattr(display, '_atom', lambda name: 1)
    monkeypatch.setattr(display, '_property', lambda window, atom: 42)
    monkeypatch.setattr(display, '_window_classes', lambda window: ('wow.exe',))
    monkeypatch.setattr(display, '_window_title', lambda window: '')
    monkeypatch.setattr(display, '_find_game_window', lambda: walks.append(1) or None)
    assert display.game_is_active() is True
    assert walks == []


def test_game_is_active_caches_the_game_window_tree_walk(monkeypatch):
    display = _display()
    now = [100.0]
    display.clock = lambda: now[0]
    walks = []
    monkeypatch.setattr(display, '_protected', lambda: contextlib.nullcontext())
    monkeypatch.setattr(display, '_atom', lambda name: 1)
    monkeypatch.setattr(display, '_property', lambda window, atom: 43)
    monkeypatch.setattr(display, '_window_classes', lambda window: ('konsole',))
    monkeypatch.setattr(display, '_window_title', lambda window: '')
    monkeypatch.setattr(display, '_find_game_window', lambda: walks.append(1) or None)

    assert display.game_is_active() is None
    now[0] += 1.9
    assert display.game_is_active() is None
    assert len(walks) == 1

    now[0] += 0.2
    assert display.game_is_active() is None
    assert len(walks) == 2


def test_set_input_passthrough_handles_windows(monkeypatch):
    display = _display()
    calls: list[tuple] = []

    class FakeXext:
        def __init__(self):
            self.XShapeQueryExtension = lambda *args: 1
            self.XShapeCombineRectangles = lambda *args: calls.append(args)

    fake_xext = FakeXext()
    monkeypatch.setattr(x11, '_load_library', lambda name, fallback: fake_xext)
    monkeypatch.setattr(display, '_xlib', types.SimpleNamespace(XFlush=lambda *args: 0))
    monkeypatch.setattr(display, '_protected', lambda: contextlib.nullcontext())
    monkeypatch.setattr(
        display, '_append_with_parents',
        lambda window, targets: targets.append(window))

    assert display.set_input_passthrough([2, 3]) is True
    assert [call[1] for call in calls] == [2, 3]
    assert all(call[2] == x11.SHAPE_INPUT for call in calls)


def test_set_input_passthrough_is_false_without_xext(monkeypatch):
    display = _display()
    monkeypatch.setattr(x11, '_load_library', lambda name, fallback: None)
    assert display.set_input_passthrough([2]) is False


def test_context_manager_closes_display(monkeypatch):
    display = _display()
    monkeypatch.setattr(display, '_xlib', types.SimpleNamespace(
        XSync=lambda *args: 0, XCloseDisplay=lambda *args: 0))
    with display as opened:
        assert opened is display
    assert display._closed is True
