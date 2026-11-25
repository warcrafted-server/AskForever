import io
import sys

import pytest

from askforever import system_env
from askforever.capture import portal

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='captura de Linux')


def test_external_env_inherits_outside_frozen_linux():
    environ = {'LD_LIBRARY_PATH': '/app/_internal', 'LD_LIBRARY_PATH_ORIG': '/usr/lib'}
    assert system_env.external_env(environ, 'linux', frozen=False) is None
    assert system_env.external_env(environ, 'win32', frozen=True) is None
    assert system_env.external_env(environ, 'darwin', frozen=True) is None


def test_external_env_restores_original_library_path():
    environ = {'LD_LIBRARY_PATH': '/app/_internal', 'LD_LIBRARY_PATH_ORIG': '/usr/lib'}
    env = system_env.external_env(environ, 'linux', frozen=True)
    assert env == {'LD_LIBRARY_PATH': '/usr/lib', 'LD_LIBRARY_PATH_ORIG': '/usr/lib'}
    assert environ['LD_LIBRARY_PATH'] == '/app/_internal'


def test_external_env_removes_bundle_library_path_without_original():
    environ = {'LD_LIBRARY_PATH': '/app/_internal', 'PATH': '/usr/bin'}
    env = system_env.external_env(environ, 'linux', frozen=True)
    assert env == {'PATH': '/usr/bin'}
    environ['LD_LIBRARY_PATH_ORIG'] = ''
    assert 'LD_LIBRARY_PATH' not in system_env.external_env(environ, 'linux', frozen=True)


class _FakeProcess:
    def __init__(self, payload):
        self.stdout = io.BytesIO(payload)
        self.killed = False

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        return 0


def test_portal_capture_passes_cleaned_env_to_spawn_when_frozen(monkeypatch):
    calls = []
    process = _FakeProcess(bytes(portal.FRAME_BYTES))
    cleaned = {'LD_LIBRARY_PATH': '/usr/lib'}

    def spawn(*args, **kwargs):
        calls.append(kwargs)
        return process

    monkeypatch.setattr(portal, 'external_env', lambda: cleaned)
    monkeypatch.setattr(portal.os, 'close', lambda fd: None)
    capture = portal.PortalCapture(
        open_session=lambda token_path: portal.PortalStream(
            fd=7, node_id=74, width=1920, height=1080),
        spawn=spawn, clock=lambda: 0.0)
    assert capture() is not None
    assert calls[0]['env'] == cleaned


def test_portal_capture_does_not_pass_env_when_not_frozen(monkeypatch):
    calls = []
    process = _FakeProcess(bytes(portal.FRAME_BYTES))

    def spawn(*args, **kwargs):
        calls.append(kwargs)
        return process

    monkeypatch.setattr(portal, 'external_env', lambda: None)
    monkeypatch.setattr(portal.os, 'close', lambda fd: None)
    capture = portal.PortalCapture(
        open_session=lambda token_path: portal.PortalStream(
            fd=7, node_id=74, width=1920, height=1080),
        spawn=spawn, clock=lambda: 0.0)
    assert capture() is not None
    assert 'env' not in calls[0]
