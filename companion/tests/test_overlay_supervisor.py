"""Pruebas del supervisor del overlay sin procesos reales ni tkinter."""

from __future__ import annotations

import logging
import queue
import threading
import time
from logging.handlers import RotatingFileHandler

import pytest

from askforever.overlay.chat import ChatView
from askforever.overlay.supervisor import (
    HANG_SECONDS,
    STARTUP_GRACE,
    OverlaySupervisor,
)
from askforever.overlay.window import Overlay


class FakeClock:
    def __init__(self, now=1000.0):
        self.now = float(now)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeProcess:
    def __init__(self):
        self.started = False
        self.alive = False
        self.terminated = False
        self.killed = False
        self.joins = []

    def start(self):
        self.started = True
        self.alive = True

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminated = True
        self.alive = False

    def kill(self):
        self.killed = True
        self.alive = False

    def join(self, timeout=None):
        self.joins.append(timeout)


class FakeFactory:
    def __init__(self):
        self.processes = []
        self.queues = []
        self.heartbeats = []

    def __call__(self, state_queue, heartbeat_value):
        process = FakeProcess()
        self.processes.append(process)
        self.queues.append(state_queue)
        self.heartbeats.append(heartbeat_value)
        return process


class FakeRoot:
    def __init__(self):
        self.after_calls = []
        self.attribute_calls = []

    def after(self, delay, callback):
        self.after_calls.append((delay, callback))

    def attributes(self, *args):
        self.attribute_calls.append(args)


@pytest.fixture(autouse=True)
def _clean_logging():
    yield
    logger = logging.getLogger('askforever')
    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            logger.removeHandler(handler)
            handler.close()


def _supervisor(tmp_path, factory, clock, ttl=30.0, check_interval=0.0):
    return OverlaySupervisor(ttl=ttl, process_factory=factory, clock=clock,
                             check_interval=check_interval,
                             log_path=tmp_path / 'companion.log')


def test_restarts_when_child_dies(tmp_path):
    factory = FakeFactory()
    clock = FakeClock()
    supervisor = _supervisor(tmp_path, factory, clock)
    supervisor._start_child()
    old = factory.processes[0]
    old.alive = False
    clock.advance(1.0)

    supervisor._watch()

    assert len(factory.processes) == 2
    assert factory.processes[1].started
    assert old.joins


def test_does_not_restart_during_startup_grace(tmp_path):
    factory = FakeFactory()
    clock = FakeClock()
    supervisor = _supervisor(tmp_path, factory, clock)
    supervisor._start_child()
    clock.advance(STARTUP_GRACE - 1.0)
    factory.heartbeats[0].value = clock.now - 100.0

    supervisor._watch()

    assert len(factory.processes) == 1


def test_restarts_when_heartbeat_is_stale(tmp_path):
    factory = FakeFactory()
    clock = FakeClock()
    supervisor = _supervisor(tmp_path, factory, clock)
    supervisor._start_child()
    clock.advance(STARTUP_GRACE + 1.0)
    factory.heartbeats[0].value = clock.now - HANG_SECONDS - 1.0

    supervisor._watch()

    assert len(factory.processes) == 2
    assert factory.processes[0].terminated


def test_forwards_last_state_on_restart(tmp_path):
    factory = FakeFactory()
    clock = FakeClock()
    supervisor = _supervisor(tmp_path, factory, clock)
    supervisor.show_answer('pregunta', 'respuesta', 'esES')
    supervisor._start_child()
    first = factory.queues[0].get(timeout=1.0)
    assert first.kind == 'answer'

    factory.processes[0].alive = False
    clock.advance(1.0)
    supervisor._watch()

    second = factory.queues[1].get(timeout=1.0)
    assert second.kind == 'answer'
    assert second.body == 'respuesta'


def test_does_not_forward_expired_state(tmp_path):
    factory = FakeFactory()
    clock = FakeClock()
    supervisor = _supervisor(tmp_path, factory, clock, ttl=10.0)
    supervisor.show_answer('pregunta', 'respuesta', 'esES')
    supervisor._start_child()
    factory.processes[0].alive = False
    clock.advance(11.0)

    supervisor._watch()

    with pytest.raises(queue.Empty):
        factory.queues[1].get(timeout=0.2)
    assert supervisor._last_state is None


def test_forwards_hidden_chat_state_on_restart(tmp_path):
    factory = FakeFactory()
    clock = FakeClock()
    supervisor = _supervisor(tmp_path, factory, clock)
    view = ChatView(entries=(('question', 'pregunta'),), rect=(1, 2, 3, 4),
                    visible=False)
    supervisor.show_chat(view)
    supervisor._start_child()
    first = factory.queues[0].get(timeout=1.0)
    assert first.visible is False

    factory.processes[0].alive = False
    clock.advance(1.0)
    supervisor._watch()

    second = factory.queues[1].get(timeout=1.0)
    assert second.visible is False
    assert second.entries == (('question', 'pregunta'),)


def test_disables_after_five_restarts(tmp_path, capsys):
    factory = FakeFactory()
    clock = FakeClock()
    supervisor = _supervisor(tmp_path, factory, clock)
    supervisor._start_child()

    for _ in range(5):
        factory.processes[-1].alive = False
        clock.advance(1.0)
        supervisor._watch()

    assert len(factory.processes) == 6
    assert not supervisor._disabled

    factory.processes[-1].alive = False
    clock.advance(1.0)
    supervisor._watch()

    assert supervisor._disabled
    assert len(factory.processes) == 6
    assert 'Overlay desactivado' in capsys.readouterr().out


def test_stop_event_terminates_child(tmp_path):
    factory = FakeFactory()
    clock = FakeClock()
    supervisor = _supervisor(tmp_path, factory, clock, check_interval=0.01)
    stop_event = threading.Event()
    thread = threading.Thread(target=supervisor.run, args=(stop_event,), daemon=True)
    thread.start()

    deadline = time.time() + 2.0
    while not factory.processes and time.time() < deadline:
        time.sleep(0.01)
    assert factory.processes
    process = factory.processes[0]
    assert process.alive

    stop_event.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert process.terminated
    assert process.joins


def test_overlay_uses_injected_queue_and_heartbeat():
    state_queue = queue.Queue()
    state_queue.put(None)
    beats = []
    overlay = Overlay(state_queue=state_queue, heartbeat=lambda: beats.append(1))
    overlay._root = FakeRoot()

    overlay._poll()

    assert overlay.queue is state_queue
    assert beats == [1]
    assert overlay._root.after_calls
    assert overlay._root.attribute_calls


def test_overlay_poll_logs_errors(monkeypatch, caplog):
    overlay = Overlay()
    overlay._root = FakeRoot()
    overlay.queue.put(None)

    def fail(_state):
        raise RuntimeError('fallo')

    monkeypatch.setattr(overlay, '_apply', fail)
    with caplog.at_level(logging.ERROR, logger='askforever.overlay'):
        overlay._poll()

    assert 'Error en el bucle del overlay' in caplog.text
