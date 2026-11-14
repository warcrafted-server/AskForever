"""Receptor continuo de la tira de píxeles que dibuja el addon en el juego."""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from PIL import Image

from askforever.capture.window import GameWindow, client_region_for, find_game_window
from askforever.protocol.codec import Assembler, Frame, decode_image

STRIP_WIDTH = 512
STRIP_HEIGHT = 32
FIRST_SEEN_TTL = 60.0


@dataclass
class ReceivedMessage:
    """Mensaje completo recibido por la tira."""

    msg_id: int
    pages: int
    data: bytes
    first_seen: float
    completed: float


class Grabber:
    """Captura la esquina del juego, decodifica la tira y entrega los mensajes."""

    def __init__(
        self,
        on_message: Callable[[ReceivedMessage], None],
        fps: float = 30.0,
        window_fn: Callable[[], Optional[GameWindow]] = find_game_window,
        capture_fn: Optional[Callable[[], Optional[Image.Image]]] = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        relocate_every: float = 1.0,
    ) -> None:
        self.on_message = on_message
        self.fps = float(fps) if fps and fps > 0 else 30.0
        self.window_fn = window_fn
        self.capture_fn = capture_fn
        self.clock = clock
        self.sleep = sleep
        self.relocate_every = float(relocate_every)

        self.captures = 0
        self.valid_frames = 0
        self.messages = 0
        self.errors = 0

        self._assembler = Assembler(clock=clock)
        self._window: Optional[GameWindow] = None
        self._region: Optional[dict] = None
        self._last_relocate = -math.inf
        self._first_seen: dict[int, float] = {}
        self._mss = None

    def step(self) -> None:
        """Un intento de captura y decodificación."""
        now = self.clock()

        if self.capture_fn is None:
            if now - self._last_relocate >= self.relocate_every:
                self._relocate()
            if self._window is None:
                return

        try:
            image = self._capture()
        except Exception:
            self.errors += 1
            self._window = None
            self._region = None
            self._last_relocate = -math.inf
            return

        if image is None:
            return
        self.captures += 1

        try:
            frame = decode_image(image)
        except Exception:
            self.errors += 1
            return

        if frame is None:
            return
        self.valid_frames += 1
        self._handle_frame(frame, now)

    def run(self, stop_event: threading.Event) -> None:
        """Repite step() a ~fps hasta que el evento de parada esté activado."""
        interval = 1.0 / self.fps
        try:
            while not stop_event.is_set():
                started = self.clock()
                self.step()
                remaining = interval - (self.clock() - started)
                if remaining > 0:
                    self.sleep(remaining)
        finally:
            self._close_mss()

    def _relocate(self) -> None:
        self._last_relocate = self.clock()
        self._window = self.window_fn()
        if self._window is None:
            self._region = None
        else:
            self._region = client_region_for(self._window, STRIP_WIDTH, STRIP_HEIGHT)

    def _capture(self) -> Optional[Image.Image]:
        if self.capture_fn is not None:
            return self.capture_fn()
        if self._window is None or self._region is None:
            return None
        if self._mss is None:
            import mss

            factory = getattr(mss, 'MSS', None) or mss.mss
            self._mss = factory()
        shot = self._mss.grab(self._region)
        return Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')

    def _close_mss(self) -> None:
        if self._mss is not None:
            try:
                self._mss.close()
            except Exception:
                pass
            self._mss = None

    def _handle_frame(self, frame: Frame, now: float) -> None:
        first_seen = self._first_seen.get(frame.msg_id)
        if first_seen is None:
            first_seen = now
            self._first_seen[frame.msg_id] = first_seen
        self._purge_first_seen(now)

        data = self._assembler.add(frame)
        if data is None:
            return

        first_seen = self._first_seen.pop(frame.msg_id, first_seen)
        self.messages += 1
        self.on_message(ReceivedMessage(frame.msg_id, frame.pages, data, first_seen, now))

    def _purge_first_seen(self, now: float) -> None:
        stale = [msg_id for msg_id, stamp in self._first_seen.items() if now - stamp > FIRST_SEEN_TTL]
        for msg_id in stale:
            del self._first_seen[msg_id]
