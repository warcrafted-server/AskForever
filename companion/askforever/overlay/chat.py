"""Estado puro del chat anclado al panel de conversación del addon."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

MAX_QUESTIONS = 20
SPANISH = ('esES', 'esMX')


@dataclass(frozen=True)
class ChatView:
    """Vista inmutable que el overlay puede dibujar o ignorar."""

    entries: tuple[tuple[str, str], ...]
    rect: Optional[tuple[int, int, int, int]]
    visible: bool


def _valid_rect(rect):
    if not isinstance(rect, (tuple, list)) or len(rect) != 4:
        return None
    if any(isinstance(value, bool) or not isinstance(value, int) for value in rect):
        return None
    x, y, width, height = rect
    if width <= 0 or height <= 0:
        return None
    return (x, y, width, height)


class ChatSession:
    """Conversación independiente de tkinter; el llamador decide si dibujarla."""

    def __init__(self):
        self.conv = None
        self.entries = []
        self.rect = None
        self.window_open = False

    def _view(self) -> ChatView:
        visible = (self.window_open and self.rect is not None
                   and bool(self.entries))
        return ChatView(tuple(self.entries), self.rect, visible)

    def _trim(self) -> None:
        question_indexes = [index for index, (role, _text) in enumerate(self.entries)
                            if role == 'question']
        if len(question_indexes) > MAX_QUESTIONS:
            del self.entries[:question_indexes[-MAX_QUESTIONS]]

    def _replace_last_thinking(self, role: str, text: str) -> None:
        for index in range(len(self.entries) - 1, -1, -1):
            if self.entries[index][0] == 'thinking':
                self.entries[index] = (role, text)
                return
        self.entries.append((role, text))

    def question(self, conv, text, rect, lang) -> Optional[ChatView]:
        rect = _valid_rect(rect)
        if rect is None:
            self.conv = conv
            self.entries = []
            self.rect = None
            self.window_open = False
            return None
        self.window_open = True
        self.rect = rect
        if conv != self.conv:
            self.entries = []
            self.conv = conv
        self.entries.append(('question', '' if text is None else str(text)))
        thinking = 'Pensando…' if lang in SPANISH else 'Thinking…'
        self.entries.append(('thinking', thinking))
        self._trim()
        return self._view()

    def answer(self, conv, text) -> Optional[ChatView]:
        if self.rect is None or conv != self.conv:
            return None
        self._replace_last_thinking('answer', '' if text is None else str(text))
        return self._view()

    def error(self, conv, text) -> Optional[ChatView]:
        if self.rect is None or conv != self.conv:
            return None
        self._replace_last_thinking('error', '' if text is None else str(text))
        return self._view()

    def ui(self, event, conv, rect) -> ChatView:
        if event == 'close':
            self.window_open = False
            return self._view()
        rect = _valid_rect(rect)
        # Sin posición (p. ej. la ventana aún sin dibujar) se conserva el último recuadro conocido.
        if event == 'open':
            self.window_open = True
            if rect is not None:
                self.rect = rect
            if conv != self.conv:
                self.entries = []
                self.conv = conv
            return self._view()
        if event == 'move' and rect is not None:
            self.rect = rect
        return self._view()
