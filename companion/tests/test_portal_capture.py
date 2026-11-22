import io
import sys

import pytest

from askforever.capture import portal

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='captura de Linux')


def _stream(width=1920, height=1080):
    return portal.PortalStream(fd=7, node_id=74, width=width, height=height)


def test_parse_start_results_reads_node_size_and_token():
    results = {
        'streams': ('a(ua{sv})', [(74, {'size': ('(ii)', (1920, 1080))})]),
        'restore_token': ('s', 'abc'),
    }
    assert portal.parse_start_results(results) == (74, 1920, 1080, 'abc')


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


def test_wants_portal_only_on_wayland_linux():
    assert portal.wants_portal({'XDG_SESSION_TYPE': 'wayland'}, 'linux')
    assert not portal.wants_portal({'XDG_SESSION_TYPE': 'x11'}, 'linux')
    assert not portal.wants_portal({'XDG_SESSION_TYPE': 'wayland'}, 'win32')
