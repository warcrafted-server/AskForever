"""Ventana overlay sin bordes, siempre encima y que no roba el foco."""

from __future__ import annotations

import queue
import time
from dataclasses import dataclass
from typing import Optional

from askforever.capture.window import find_game_window

STRIP_WIDTH = 512
STRIP_HEIGHT = 32
DEFAULT_CLIENT_WIDTH = 1920
DEFAULT_CLIENT_HEIGHT = 1080
WINDOW_WIDTH = 460
BODY_WRAP = 428
MARGIN = 24
TOP_RATIO = 0.18
TITLE_MAX = 90

BG = '#15100b'
BORDER = '#5a4630'
TITLE_COLOUR = '#e6b84a'
TEXT_COLOUR = '#e9dfc8'
DIM_COLOUR = '#a3957c'
ERROR_COLOUR = '#ff6b62'


VISIBLE_ALPHA = 0.94

class OverlayUnavailable(Exception):
    """No se pudo crear la ventana tkinter del overlay."""


@dataclass
class OverlayState:
    """Contenido que debe mostrar el overlay."""

    kind: str
    title: str
    body: str
    expires_at: Optional[float]


def _truncate_question(question) -> str:
    text = '' if question is None else str(question)
    text = text.strip()
    if len(text) > TITLE_MAX:
        return text[:TITLE_MAX].rstrip() + '…'
    return text


def build_state(kind: str, lang, question='', text='', now=0.0, ttl=30.0) -> OverlayState:
    """Crea el estado para uno de los tipos thinking, answer o error."""
    spanish = lang in ('esES', 'esMX')
    title = _truncate_question(question)

    if kind == 'thinking':
        body = 'Pensando…' if spanish else 'Thinking…'
        return OverlayState('thinking', title, body, None)

    expires_at = now + ttl
    body = '' if text is None else str(text)
    if kind == 'error':
        return OverlayState('error', title, body, expires_at)
    return OverlayState('answer', title, body, expires_at)


def compute_position(client, width, height, margin=MARGIN, top_ratio=TOP_RATIO):
    """Coloca la ventana a la derecha del área cliente sin tapar la tira de píxeles."""
    if client is None:
        left, top = 0, 0
        client_width, client_height = DEFAULT_CLIENT_WIDTH, DEFAULT_CLIENT_HEIGHT
    else:
        left = int(getattr(client, 'x', 0))
        top = int(getattr(client, 'y', 0))
        client_width = int(getattr(client, 'width', DEFAULT_CLIENT_WIDTH))
        client_height = int(getattr(client, 'height', DEFAULT_CLIENT_HEIGHT))

    width = max(1, int(width))
    height = max(1, int(height))

    x = left + client_width - width - margin
    y = top + int(client_height * top_ratio)

    max_x = left + max(0, client_width - width)
    max_y = top + max(0, client_height - height)
    x = max(left, min(x, max_x))
    y = max(top, min(y, max_y))

    strip_right = left + STRIP_WIDTH
    strip_bottom = top + STRIP_HEIGHT
    if x < strip_right and y < strip_bottom:
        y = min(strip_bottom, max_y) if max_y >= top else top
        if y < strip_bottom and x < strip_right:
            x = min(strip_right, max_x) if max_x >= left else left
    return x, y


def wrap_estimate(text, max_chars=60) -> int:
    """Número de líneas estimadas de un texto a un ancho dado."""
    text = '' if text is None else str(text)
    max_chars = max(1, int(max_chars))
    if not text:
        return 1
    lines = 0
    for paragraph in text.split('\n'):
        if paragraph:
            lines += (len(paragraph) + max_chars - 1) // max_chars
        else:
            lines += 1
    return max(1, lines)


class Overlay:
    """Ventana que muestra el estado de la IA sin interferir con el juego."""

    def __init__(self, ttl=30.0, window_fn=find_game_window, clock=time.monotonic):
        self.ttl = float(ttl)
        self.window_fn = window_fn
        self.clock = clock
        self.queue = queue.Queue()
        self._root = None
        self._title_label = None
        self._body_label = None
        self._title_visible = False
        self._expires_at = None
        self._mapped = False
        self._stop = None
        self._close_requested = False
        self._closed = False

    def show_thinking(self, question, lang):
        """Encola el aviso de que se está pensando la respuesta."""
        state = build_state('thinking', lang, question=question, now=self.clock())
        self.queue.put(state)

    def show_answer(self, question, text, lang):
        """Encola una respuesta de la IA."""
        state = build_state('answer', lang, question=question, text=text,
                            now=self.clock(), ttl=self.ttl)
        self.queue.put(state)

    def show_error(self, text, lang):
        """Encola un aviso de error."""
        state = build_state('error', lang, text=text, now=self.clock(), ttl=self.ttl)
        self.queue.put(state)

    def hide(self):
        """Encola el ocultado de la ventana."""
        self.queue.put(None)

    def close(self):
        """Pide terminar el bucle del overlay."""
        self._close_requested = True

    def run(self, stop_event=None):
        """Crea la ventana y procesa la cola hasta que se pida parar."""
        self._stop = stop_event
        try:
            import tkinter as tk
        except Exception as exc:
            raise OverlayUnavailable('tkinter no está disponible') from exc
        try:
            self._root = tk.Tk()
        except Exception as exc:
            raise OverlayUnavailable('no se pudo crear la ventana del overlay') from exc

        root = self._root
        root.withdraw()
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.attributes('-alpha', 0.0)
        root.configure(bg=BORDER)

        inner = tk.Frame(root, bg=BG)
        inner.pack(fill='both', expand=True, padx=2, pady=2)

        self._title_label = tk.Label(
            inner,
            text='',
            font=('Segoe UI', 10, 'bold'),
            fg=TITLE_COLOUR,
            bg=BG,
            wraplength=BODY_WRAP,
            justify='left',
            anchor='w',
        )
        self._body_label = tk.Label(
            inner,
            text='',
            font=('Segoe UI', 11),
            fg=TEXT_COLOUR,
            bg=BG,
            wraplength=BODY_WRAP,
            justify='left',
            anchor='w',
        )
        self._body_label.pack(fill='x', padx=12, pady=(10, 12))

        if self._close_requested:
            root.destroy()
            return

        root.after(50, self._poll)
        root.mainloop()

    def _poll(self):
        try:
            if self._closed:
                return
            if self._close_requested or (self._stop is not None and self._stop.is_set()):
                self._shutdown()
                return

            try:
                while True:
                    self._apply(self.queue.get_nowait())
            except queue.Empty:
                pass

            if self._expires_at is not None and self.clock() >= self._expires_at:
                self._hide_window()
        except Exception:
            pass

        if not self._closed:
            self._root.after(50, self._poll)

    def _shutdown(self):
        self._closed = True
        try:
            self._root.destroy()
        except Exception:
            pass

    def _apply(self, state):
        if state is None:
            self._hide_window()
            return

        self._expires_at = state.expires_at
        if state.title:
            if not self._title_visible:
                self._title_label.pack(fill='x', padx=12, pady=(12, 2), before=self._body_label)
                self._title_visible = True
            self._title_label.configure(text=state.title)
        elif self._title_visible:
            self._title_label.pack_forget()
            self._title_visible = False

        if state.kind == 'error':
            colour = ERROR_COLOUR
        elif state.kind == 'thinking':
            colour = DIM_COLOUR
        else:
            colour = TEXT_COLOUR
        self._body_label.configure(text=state.body, fg=colour)
        self._show_window()

    def _show_window(self):
        root = self._root
        root.update_idletasks()
        height = max(60, root.winfo_reqheight())
        try:
            client = self.window_fn()
        except Exception:
            client = None
        x, y = compute_position(client, WINDOW_WIDTH, height)
        root.geometry(f'{WINDOW_WIDTH}x{height}+{x}+{y}')
        if not self._mapped:
            # Se mapea una sola vez: ocultar y mostrar con withdraw/deiconify una ventana siempre
            # encima y transparente a los clics producía destellos sobre el juego.
            root.attributes('-alpha', 0.0)
            root.deiconify()
            root.update_idletasks()
            self._apply_native_styles()
            self._mapped = True
        root.update_idletasks()
        root.attributes('-alpha', VISIBLE_ALPHA)

    def _hide_window(self):
        self._expires_at = None
        try:
            self._root.attributes('-alpha', 0.0)
        except Exception:
            pass

    def _apply_native_styles(self):
        try:
            import ctypes

            user32 = ctypes.WinDLL('user32')
            user32.GetParent.argtypes = [ctypes.c_void_p]
            user32.GetParent.restype = ctypes.c_void_p
            hwnd = user32.GetParent(ctypes.c_void_p(self._root.winfo_id()))
            self.apply_click_through(hwnd or self._root.winfo_id())
        except Exception:
            pass

    @staticmethod
    def apply_click_through(hwnd):
        """Marca la ventana como transparente a los clics y sin activación."""
        try:
            import ctypes

            user32 = ctypes.WinDLL('user32', use_last_error=True)
            get_long = user32.GetWindowLongPtrW
            set_long = user32.SetWindowLongPtrW
            get_long.argtypes = [ctypes.c_void_p, ctypes.c_int]
            get_long.restype = ctypes.c_ssize_t
            set_long.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
            set_long.restype = ctypes.c_ssize_t

            gwl_exstyle = -20
            ex_style = get_long(ctypes.c_void_p(hwnd), gwl_exstyle)
            ex_style |= 0x00080000  # WS_EX_LAYERED
            ex_style |= 0x00000020  # WS_EX_TRANSPARENT
            ex_style |= 0x08000000  # WS_EX_NOACTIVATE
            ex_style |= 0x00000080  # WS_EX_TOOLWINDOW
            set_long(ctypes.c_void_p(hwnd), gwl_exstyle, ex_style)
            return True
        except Exception:
            return False
