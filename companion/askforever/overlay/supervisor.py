"""Proceso hijo vigilado para el overlay de AskForever."""

from __future__ import annotations

import logging
import multiprocessing
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from askforever.overlay.window import ChatState, Overlay, build_state
from askforever.paths import dev_dir

LOGGER = logging.getLogger('askforever.overlay.supervisor')

HANG_SECONDS = 10.0
STARTUP_GRACE = 10.0
MAX_RESTARTS = 5
RESTART_WINDOW = 300.0
JOIN_TIMEOUT = 2.0
LOG_MAX_BYTES = 1024 * 1024
LOG_BACKUPS = 3


def companion_log_path() -> Path:
    """Ruta del log del companion."""
    return dev_dir() / 'companion.log'


def configure_logging(log_path=None) -> Path:
    """Configura el log rotativo compartido por el proceso principal y el hijo."""
    path = Path(log_path) if log_path else companion_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS, encoding='utf-8')
    except OSError as exc:
        print(f'No se pudo abrir el log del companion: {exc}')
        return path
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s: %(message)s'))
    logger = logging.getLogger('askforever')
    logger.setLevel(logging.INFO)
    target = path.resolve()
    for existing in logger.handlers:
        if (isinstance(existing, RotatingFileHandler)
                and Path(existing.baseFilename).resolve() == target):
            handler.close()
            return path
    logger.addHandler(handler)
    return path


def _child_main(state_queue, heartbeat_value, ttl, log_path) -> None:
    """Punto de entrada del proceso que dibuja el overlay."""
    configure_logging(log_path)

    def heartbeat():
        heartbeat_value.value = time.time()

    overlay = Overlay(ttl, state_queue=state_queue, heartbeat=heartbeat, clock=time.time)
    try:
        overlay.run()
    except Exception:
        LOGGER.exception('El proceso del overlay ha terminado con error')


class OverlaySupervisor:
    """Mantiene el overlay en un proceso hijo y lo reinicia si se cuelga."""

    def __init__(self, ttl=30.0, process_factory=None, clock=time.time,
                 check_interval=1.0, log_path=None):
        self.ttl = float(ttl)
        self.clock = clock
        self.check_interval = max(0.0, float(check_interval))
        self.log_path = configure_logging(log_path)
        self._context = multiprocessing.get_context('spawn')
        self._factory = process_factory or self._default_process_factory
        self._queue = None
        self._heartbeat = None
        self._process = None
        self._last_state = None
        self._started_at = 0.0
        self._restarts = []
        self._disabled = False
        self._close_requested = False

    def _default_process_factory(self, state_queue, heartbeat_value):
        return self._context.Process(
            target=_child_main,
            args=(state_queue, heartbeat_value, self.ttl, str(self.log_path)),
        )

    def _put(self, state) -> None:
        queue_ = self._queue
        if queue_ is None or self._disabled:
            return
        try:
            queue_.put_nowait(state)
        except Exception:
            LOGGER.exception('No se pudo enviar el estado al overlay')

    def show_thinking(self, question, lang) -> None:
        state = build_state('thinking', lang, question=question, now=self.clock())
        self._last_state = state
        self._put(state)

    def show_answer(self, question, text, lang) -> None:
        state = build_state('answer', lang, question=question, text=text,
                            now=self.clock(), ttl=self.ttl)
        self._last_state = state
        self._put(state)

    def show_error(self, text, lang) -> None:
        state = build_state('error', lang, text=text, now=self.clock(), ttl=self.ttl)
        self._last_state = state
        self._put(state)

    def show_chat(self, view) -> None:
        """Envía una vista del chat anclado y la conserva para reinicios."""
        if view is None:
            return
        state = ChatState(tuple(view.entries), view.rect, bool(view.visible),
                          getattr(view, 'scroll', 0))
        self._last_state = state
        self._put(state)

    def hide(self) -> None:
        self._last_state = None
        self._put(None)

    def close(self) -> None:
        self._close_requested = True

    def _should_stop(self, stop_event) -> bool:
        if self._close_requested:
            return True
        return stop_event is not None and bool(stop_event.is_set())

    @staticmethod
    def _alive(process) -> bool:
        if process is None:
            return False
        try:
            return bool(process.is_alive())
        except Exception:
            LOGGER.exception('No se pudo consultar el proceso del overlay')
            return False

    def _stop_child(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if self._alive(process):
            try:
                process.terminate()
            except Exception:
                LOGGER.exception('No se pudo terminar el proceso del overlay')
        try:
            process.join(timeout=JOIN_TIMEOUT)
        except Exception:
            LOGGER.exception('No se pudo esperar al proceso del overlay')
        if self._alive(process):
            try:
                process.kill()
            except Exception:
                LOGGER.exception('No se pudo matar el proceso del overlay')
            try:
                process.join(timeout=JOIN_TIMEOUT)
            except Exception:
                LOGGER.exception('No se pudo esperar al proceso del overlay')

    def _forward_last_state(self) -> None:
        state = self._last_state
        if state is None:
            return
        expires_at = getattr(state, 'expires_at', None)
        if expires_at is not None and self.clock() >= expires_at:
            self._last_state = None
            return
        self._put(state)

    def _start_child(self) -> bool:
        if self._disabled:
            return False
        try:
            self._queue = self._context.Queue()
            self._heartbeat = self._context.Value('d', 0.0)
            self._process = self._factory(self._queue, self._heartbeat)
            self._process.start()
        except Exception:
            LOGGER.exception('No se pudo arrancar el proceso del overlay')
            self._queue = None
            self._heartbeat = None
            self._process = None
            return False
        self._started_at = self.clock()
        self._forward_last_state()
        return True

    def _heartbeat_value(self) -> float:
        try:
            return float(self._heartbeat.value)
        except Exception:
            LOGGER.exception('No se pudo leer el latido del overlay')
            return 0.0

    def _restart(self, reason: str) -> None:
        if self._disabled:
            return
        now = self.clock()
        self._restarts = [stamp for stamp in self._restarts
                          if now - stamp < RESTART_WINDOW]
        if len(self._restarts) >= MAX_RESTARTS:
            self._disabled = True
            self._stop_child()
            print('Overlay desactivado: demasiados reinicios en 5 minutos.')
            LOGGER.error('Overlay desactivado: demasiados reinicios en 5 minutos.')
            return
        self._restarts.append(now)
        print(f'Overlay reiniciado (motivo: {reason})')
        LOGGER.warning('Overlay reiniciado (motivo: %s)', reason)
        self._stop_child()
        self._start_child()

    def _watch(self) -> None:
        try:
            if self._disabled:
                return
            now = self.clock()
            if not self._alive(self._process):
                self._restart('proceso terminado')
                return
            if now - self._started_at <= STARTUP_GRACE:
                return
            if now - self._heartbeat_value() > HANG_SECONDS:
                self._restart('latido caducado')
        except Exception:
            LOGGER.exception('Error al vigilar el overlay')

    def run(self, stop_event=None) -> None:
        if self._should_stop(stop_event):
            return
        if not self._disabled:
            self._start_child()
        try:
            while not self._should_stop(stop_event):
                self._watch()
                if self._should_stop(stop_event):
                    break
                if stop_event is not None and hasattr(stop_event, 'wait'):
                    stop_event.wait(self.check_interval)
                else:
                    time.sleep(self.check_interval)
        finally:
            self._stop_child()
            self._queue = None
            self._heartbeat = None
