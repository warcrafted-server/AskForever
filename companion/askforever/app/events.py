"""Friendly activity events and technical logging for AskForever App."""

from __future__ import annotations

import logging
import os
import sys
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler

from askforever.paths import user_data_dir


_KINDS = {'status', 'question', 'answer', 'error', 'data', 'update', 'info'}
_STATUS_KEYS = {'game', 'ai', 'data', 'app'}


@dataclass(frozen=True)
class Event:
    time: datetime
    kind: str
    es: str
    en: str
    detail: str = ''


def _log_path():
    return user_data_dir().parent / 'logs' / 'app.log'


class EventBus:
    """Thread-safe event history, subscribers, status cards, and technical log."""

    def __init__(self) -> None:
        self._events = deque(maxlen=200)
        self._subscribers = []
        self._statuses = {
            key: {'es': '', 'en': '', 'ok': None} for key in _STATUS_KEYS
        }
        self._lock = threading.RLock()
        self._logger_lock = threading.Lock()
        self._logger = None
        self.subscribe(_print_console_event)

    def _get_logger(self):
        with self._logger_lock:
            if self._logger is not None:
                return self._logger
            try:
                path = _log_path()
                path.parent.mkdir(parents=True, exist_ok=True)
                logger = logging.Logger(f'askforever.app.events.{id(self)}')
                logger.setLevel(logging.INFO)
                logger.propagate = False
                handler = RotatingFileHandler(
                    path, maxBytes=1_000_000, backupCount=3, encoding='utf-8')
                handler.setFormatter(logging.Formatter('%(message)s'))
                logger.addHandler(handler)
                self._logger = logger
            except OSError:
                return None
            return self._logger

    def _log(self, line: str) -> None:
        logger = self._get_logger()
        if logger is not None:
            try:
                logger.info(line)
            except OSError:
                pass

    def emit(self, kind: str, es: str, en: str, detail: str = '') -> Event:
        if kind not in _KINDS:
            raise ValueError(f'unknown event kind: {kind}')
        event = Event(datetime.now(), kind, str(es), str(en), str(detail))
        with self._lock:
            self._events.append(event)
            subscribers = tuple(self._subscribers)
        self._log(
            f'{event.time.isoformat(timespec="seconds")} [{kind}] '
            f'es={event.es} | en={event.en} | detail={event.detail}')
        for callback in subscribers:
            try:
                callback(event)
            except Exception as error:
                self._log(f'{datetime.now().isoformat(timespec="seconds")} '
                          f'[subscriber-error] {error!r}')
        return event

    def subscribe(self, callback) -> None:
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback) -> None:
        with self._lock:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

    def recent(self) -> list[Event]:
        with self._lock:
            return list(self._events)

    def set_status(self, key: str, es: str, en: str, ok=None) -> Event:
        if key not in _STATUS_KEYS:
            raise ValueError(f'unknown status key: {key}')
        status = {'es': str(es), 'en': str(en), 'ok': ok}
        with self._lock:
            self._statuses[key] = status
        return self.emit('status', es, en, detail=f'key={key} ok={ok}')

    def statuses(self) -> dict:
        with self._lock:
            return {key: value.copy() for key, value in self._statuses.items()}


def _console_enabled() -> bool:
    if os.environ.get('ASKFOREVER_CONSOLE') == '1':
        return True
    try:
        return bool(sys.stdout and sys.stdout.isatty())
    except (AttributeError, OSError, ValueError):
        return False


def _print_console_event(event: Event) -> None:
    if _console_enabled():
        print(f'[{event.time:%H:%M:%S}] {event.es}', file=sys.stdout, flush=True)


_bus_lock = threading.Lock()
_default_bus = None


def get_bus() -> EventBus:
    global _default_bus
    with _bus_lock:
        if _default_bus is None:
            _default_bus = EventBus()
        return _default_bus


def emit(kind: str, es: str, en: str, detail: str = '') -> Event:
    return get_bus().emit(kind, es, en, detail)


def set_status(key: str, es: str, en: str, ok=None) -> Event:
    return get_bus().set_status(key, es, en, ok)


def log_detail(detail: str) -> None:
    """Write technical-only activity without adding it to the friendly history."""
    get_bus()._log(f'{datetime.now().isoformat(timespec="seconds")} [detail] {detail}')
