"""Memoria de las preguntas encadenadas de una misma conversación."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

DEFAULT_KEY = 'default'
MAX_TURNS = 4
DEFAULT_TTL = 1800.0


@dataclass
class Turn:
    """Una pregunta con su respuesta y los datos verificados que se usaron."""

    question: str
    answer: str
    facts_text: str = ''


class ConversationStore:
    """Guarda los últimos turnos de la conversación activa."""

    def __init__(self, max_turns: int = MAX_TURNS, ttl: float = DEFAULT_TTL,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.max_turns = max(1, int(max_turns))
        self.ttl = float(ttl)
        self.clock = clock
        self._lock = threading.Lock()
        self._key = None
        self._turns: list[Turn] = []
        self._last = 0.0

    @staticmethod
    def key(message) -> str:
        """Clave de conversación; los mensajes antiguos comparten 'default'."""
        if not isinstance(message, dict):
            return DEFAULT_KEY
        conv = message.get('conv')
        if isinstance(conv, bool):
            return DEFAULT_KEY
        if isinstance(conv, int):
            return str(conv)
        if isinstance(conv, str):
            if conv.strip():
                return conv
        return DEFAULT_KEY

    def _expired(self, now: float) -> bool:
        return bool(self._turns) and (now - self._last) >= self.ttl

    def history(self, key: str) -> list[Turn]:
        """Turnos de la conversación activa, del más antiguo al más reciente."""
        with self._lock:
            if key != self._key:
                return []
            if self._expired(self.clock()):
                self._turns = []
                return []
            return list(self._turns)

    def add(self, key: str, question: str, answer: str, facts_text: str = '') -> None:
        """Añade un turno; cambiar de clave empieza una conversación nueva."""
        with self._lock:
            now = self.clock()
            if key != self._key or self._expired(now):
                self._turns = []
            self._key = key
            self._last = now
            self._turns.append(Turn(str(question), str(answer), str(facts_text or '')))
            if len(self._turns) > self.max_turns:
                self._turns = self._turns[-self.max_turns:]
