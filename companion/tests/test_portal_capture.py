import io
import json
import sys

import pytest

from askforever.capture import portal

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='captura de Linux')


def _stream(width=1920, height=1080, x=0, y=0):
    return portal.PortalStream(
        fd=7, node_id=74, width=width, height=height, x=x, y=y)


def test_parse_start_results_reads_node_size_and_token():
    results = {
        'streams': ('a(ua{sv})', [(74, {'size': ('(ii)', (1920, 1080))})]),
        'restore_token': ('s', 'abc'),
    }
    assert portal.parse_start_results(results) == (74, 1920, 1080, 'abc')


def test_parse_stream_position_reads_monitor_offset():
    results = {'streams': ('a(ua{sv})',
                           [(74, {'position': ('(ii)', (1920, 20))})])}
    assert portal.parse_stream_position(results) == (1920, 20)


def test_parse_stream_position_returns_none_when_missing_or_invalid():
    assert portal.parse_stream_position({}) is None
    assert portal.parse_stream_position({'streams': ('x', [(1, {})])}) is None
    assert portal.parse_stream_position(
        {'streams': ('x', [(1, {'position': ('(ii)', 'x')})])}) is None


def test_parse_start_results_rejects_missing_stream_or_size():
    with pytest.raises(portal.PortalError):
        portal.parse_start_results({})
    with pytest.raises(portal.PortalError):
        portal.parse_start_results({'streams': ('x', [(1, {})])})


def test_gst_command_crops_to_the_strip_corner():
    command = portal.gst_command(_stream(1920, 1080), fps=15)
    assert 'right=1408' in command and 'bottom=1048' in command
    assert command[:3] == ['gst-launch-1.0', '-q', 'pipewiresrc']
    assert 'fd=7' in command and 'path=74' in command
    assert 'video/x-raw,framerate=15/1' in command


def test_crop_margins_rejects_tiny_monitor():
    with pytest.raises(portal.PortalError):
        portal.crop_margins(400, 1080)


class _FakeProcess:
    def __init__(self, payload):
        self.stdout = io.BytesIO(payload)
        self.killed = False

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        return 0


def test_capture_returns_strip_image_and_none_at_end_of_stream(monkeypatch):
    frame = bytes([10, 20, 30]) * (portal.STRIP_WIDTH * portal.STRIP_HEIGHT)
    process = _FakeProcess(frame)
    capture = portal.PortalCapture(
        open_session=lambda token_path: _stream(),
        spawn=lambda *args, **kwargs: process,
        clock=lambda: 0.0)
    monkeypatch.setattr(portal.os, 'close', lambda fd: None)
    image = capture()
    assert image.size == (portal.STRIP_WIDTH, portal.STRIP_HEIGHT)
    assert image.getpixel((0, 0)) == (10, 20, 30)
    assert capture() is None
    assert process.killed


def test_capture_writes_monitor_geometry_for_the_overlay(monkeypatch, tmp_path):
    frame = bytes([10, 20, 30]) * (portal.STRIP_WIDTH * portal.STRIP_HEIGHT)
    geometry = tmp_path / 'data' / 'portal-geometry.json'
    capture = portal.PortalCapture(
        geometry_path=geometry,
        open_session=lambda token_path: _stream(2560, 1440, x=1920, y=20),
        spawn=lambda *args, **kwargs: _FakeProcess(frame),
        clock=lambda: 0.0)
    monkeypatch.setattr(portal.os, 'close', lambda fd: None)

    assert capture() is not None
    assert json.loads(geometry.read_text(encoding='utf-8')) == {
        'x': 1920, 'y': 20, 'width': 2560, 'height': 1440}
    assert not (geometry.parent / 'portal-geometry.json.tmp').exists()


def test_capture_ignores_geometry_write_errors(monkeypatch, tmp_path):
    frame = bytes([10, 20, 30]) * (portal.STRIP_WIDTH * portal.STRIP_HEIGHT)
    blocker = tmp_path / 'blocked'
    blocker.write_text('', encoding='utf-8')
    capture = portal.PortalCapture(
        geometry_path=blocker / 'portal-geometry.json',
        open_session=lambda token_path: _stream(),
        spawn=lambda *args, **kwargs: _FakeProcess(frame),
        clock=lambda: 0.0)
    monkeypatch.setattr(portal.os, 'close', lambda fd: None)

    assert capture() is not None


def test_capture_reports_error_and_backs_off(monkeypatch):
    errors = []
    now = [100.0]

    def failing(token_path):
        raise portal.PortalError('cancelado')

    capture = portal.PortalCapture(open_session=failing, clock=lambda: now[0],
                                   on_error=errors.append)
    monkeypatch.setattr(portal.time, 'sleep', lambda seconds: None)
    assert capture() is None
    assert len(errors) == 1
    assert capture() is None
    assert len(errors) == 1
    now[0] += portal.RETRY_AFTER + 1
    assert capture() is None
    assert len(errors) == 2


def test_capture_never_opens_portal_while_game_is_closed(monkeypatch):
    opened = []
    slept = []
    capture = portal.PortalCapture(
        open_session=lambda token_path: opened.append(1) or _stream(),
        is_game_running=lambda: False,
        sleep=slept.append)
    monkeypatch.setattr(portal.os, 'close', lambda fd: None)
    assert capture() is None
    assert opened == []
    assert slept == [0.2]


def test_capture_treats_game_check_error_as_not_running():
    def failing():
        raise RuntimeError('sin ventana')

    capture = portal.PortalCapture(
        open_session=lambda token_path: pytest.fail('no debe abrir el portal'),
        is_game_running=failing, sleep=lambda seconds: None)
    assert capture() is None


def test_capture_releases_stream_and_resumes_when_game_reopens(monkeypatch):
    frame = bytes([10, 20, 30]) * (portal.STRIP_WIDTH * portal.STRIP_HEIGHT)
    opened = []
    now = [0.0]
    running = [True]

    def open_session(token_path):
        opened.append(1)
        return _stream()

    processes = []

    def spawn(*args, **kwargs):
        process = _FakeProcess(frame)
        processes.append(process)
        return process

    capture = portal.PortalCapture(
        open_session=open_session, spawn=spawn, clock=lambda: now[0],
        is_game_running=lambda: running[0], check_every=1.0,
        sleep=lambda seconds: None)
    monkeypatch.setattr(portal.os, 'close', lambda fd: None)

    assert capture() is not None
    assert len(opened) == 1

    running[0] = False
    now[0] += 2.0
    assert capture() is None
    assert processes[0].killed

    running[0] = True
    now[0] += 2.0
    assert capture() is not None
    assert len(opened) == 2


def test_capture_resets_backoff_when_game_reopens():
    errors = []
    now = [0.0]
    running = [True]

    def failing(token_path):
        raise portal.PortalError('cancelado')

    capture = portal.PortalCapture(
        open_session=failing, clock=lambda: now[0],
        is_game_running=lambda: running[0], on_error=errors.append,
        sleep=lambda seconds: None)
    assert capture() is None
    assert len(errors) == 1

    running[0] = False
    now[0] += 2.0
    assert capture() is None

    running[0] = True
    now[0] += 2.0
    assert capture() is None
    # Aún dentro del back-off, pero al reabrirse el juego se reinicia y reintenta.
    assert len(errors) == 2


def test_wants_portal_only_on_wayland_linux():
    assert portal.wants_portal({'XDG_SESSION_TYPE': 'wayland'}, 'linux')
    assert not portal.wants_portal({'XDG_SESSION_TYPE': 'x11'}, 'linux')
    assert not portal.wants_portal({'XDG_SESSION_TYPE': 'wayland'}, 'win32')
