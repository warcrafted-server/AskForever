"""Ventana overlay sin bordes, siempre encima y que no roba el foco."""

from __future__ import annotations

import logging
import queue
import time
from dataclasses import dataclass
from typing import Optional

from askforever.capture.window import find_game_window

LOGGER = logging.getLogger('askforever.overlay')

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

SW_SHOWNOACTIVATE = 4
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
GAME_REFRESH_SECONDS = 2.0
FOREGROUND_CHECK_SECONDS = 0.2


def _load_user32():
    """Carga user32 con los tipos que usa el overlay."""
    import ctypes

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.GetParent.argtypes = [ctypes.c_void_p]
    user32.GetParent.restype = ctypes.c_void_p
    user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                         ctypes.c_ssize_t]
    user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.ShowWindow.restype = ctypes.c_bool
    user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_uint]
    user32.SetWindowPos.restype = ctypes.c_bool
    user32.IsWindow.argtypes = [ctypes.c_void_p]
    user32.IsWindow.restype = ctypes.c_bool
    user32.IsIconic.argtypes = [ctypes.c_void_p]
    user32.IsIconic.restype = ctypes.c_bool
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    return user32


def game_in_front(hwnd, foreground_hwnd, is_window, is_iconic) -> bool:
    """True solo si la ventana del juego existe, no está minimizada y está delante."""
    try:
        if not hwnd or not is_window(hwnd):
            return False
        if is_iconic(hwnd):
            return False
        return foreground_hwnd == hwnd
    except Exception:
        return False


class OverlayUnavailable(Exception):
    """No se pudo crear la ventana tkinter del overlay."""


@dataclass
class OverlayState:
    """Contenido que debe mostrar el overlay."""

    kind: str
    title: str
    body: str
    expires_at: Optional[float]


@dataclass(frozen=True)
class ChatState:
    """Vista de chat lista para cruzar el proceso del overlay."""

    entries: tuple[tuple[str, str], ...]
    rect: Optional[tuple[int, int, int, int]]
    visible: bool
    scroll: int = 0


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

    def __init__(self, ttl=30.0, window_fn=find_game_window, clock=time.monotonic,
                 state_queue=None, heartbeat=None, user32=None):
        self.ttl = float(ttl)
        self.window_fn = window_fn
        self.clock = clock
        self.queue = state_queue if state_queue is not None else queue.Queue()
        self.heartbeat = heartbeat
        self._user32 = user32
        self._user32_loaded = user32 is not None
        self._user32_injected = user32 is not None
        self._root = None
        self._inner = None
        self._title_label = None
        self._body_label = None
        self._chat_text = None
        self._rendered_chat_entries = None
        self._title_visible = False
        self._expires_at = None
        self._state_active = False
        self._visible_requested = False
        self._chat_mode = False
        self._chat_rect = None
        self._chat_layout = False
        self._mapped = False
        self._shown = False
        self._game_client = None
        self._game_hwnd = None
        self._last_window_refresh = None
        self._last_foreground_check = None
        self._foreground_allowed = False
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

    def show_chat(self, view):
        """Encola una vista del chat anclado al panel del addon."""
        if view is None:
            return
        state = ChatState(tuple(view.entries), view.rect, bool(view.visible),
                          getattr(view, 'scroll', 0))
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
        self._inner = inner

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

        self._chat_text = tk.Text(
            inner,
            wrap='word',
            bg=BG,
            fg=TEXT_COLOUR,
            font=('Segoe UI', 10),
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=8,
            state='disabled',
            cursor='arrow',
            takefocus=0,
        )
        self._chat_text.tag_configure('question', foreground=TITLE_COLOUR,
                                      font=('Segoe UI', 10, 'bold'))
        self._chat_text.tag_configure('thinking', foreground=DIM_COLOUR)
        self._chat_text.tag_configure('answer', foreground=TEXT_COLOUR)
        self._chat_text.tag_configure('answer_bold', foreground=TEXT_COLOUR,
                                      font=('Segoe UI', 10, 'bold'))
        self._chat_text.tag_configure('bullet', foreground=TEXT_COLOUR,
                                      font=('Segoe UI', 10), lmargin1=0, lmargin2=14)
        self._chat_text.tag_configure('error', foreground=ERROR_COLOUR)

        if self._close_requested:
            root.destroy()
            return

        self._map_invisible()
        root.after(50, self._poll)
        root.mainloop()

    def _poll(self):
        try:
            if self.heartbeat is not None:
                self.heartbeat()
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

            if self._state_active and self._expired():
                self._hide_window()
            allowed = self._visible_allowed()
            # Solo se actúa al cambiar: recolocar y reafirmar «siempre encima» cada 50 ms
            # costaría rendimiento al juego.
            should_show = self._state_active and self._visible_requested and allowed
            if self._state_active and should_show != self._shown:
                if should_show:
                    self._show_window()
                else:
                    self._set_alpha(0.0)
        except Exception:
            LOGGER.exception('Error en el bucle del overlay')

        if not self._closed:
            try:
                self._root.after(50, self._poll)
            except Exception:
                LOGGER.exception('No se pudo reprogramar el bucle del overlay')

    def _shutdown(self):
        self._closed = True
        try:
            self._root.destroy()
        except Exception:
            pass

    def _apply(self, state):
        try:
            if state is None:
                self._hide_window()
                return

            if self._is_chat_state(state):
                self._apply_chat(state)
                return

            self._chat_mode = False
            self._chat_rect = None
            self._visible_requested = True
            self._use_chat_layout(False)
            self._state_active = True
            self._expires_at = state.expires_at
            if state.title:
                if not self._title_visible:
                    self._title_label.pack(fill='x', padx=12, pady=(12, 2),
                                           before=self._body_label)
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
        except Exception:
            LOGGER.exception('Error al aplicar el estado del overlay')

    @staticmethod
    def _is_chat_state(state) -> bool:
        if isinstance(state, ChatState):
            return True
        return (hasattr(state, 'entries') and hasattr(state, 'rect')
                and hasattr(state, 'visible') and not hasattr(state, 'kind'))

    def _apply_chat(self, state) -> None:
        entries = tuple(getattr(state, 'entries', ()) or ())
        rect = getattr(state, 'rect', None)
        visible = bool(getattr(state, 'visible', False)) and rect is not None
        self._chat_mode = True
        self._chat_rect = rect
        self._state_active = True
        self._visible_requested = visible
        self._expires_at = None
        self._use_chat_layout(True)
        scroll = getattr(state, 'scroll', 0)
        if scroll and entries == self._rendered_chat_entries and self._chat_text is not None:
            self._chat_text.yview_scroll(scroll, 'units')
        else:
            self._render_chat(entries)
        if visible:
            self._show_window()
        else:
            self._set_alpha(0.0)

    def _use_chat_layout(self, chat: bool) -> None:
        if self._chat_layout == chat:
            return
        self._chat_layout = chat
        if chat:
            if self._title_label is not None:
                self._title_label.pack_forget()
            if self._body_label is not None:
                self._body_label.pack_forget()
            if self._chat_text is not None:
                self._chat_text.pack(fill='both', expand=True)
        else:
            if self._chat_text is not None:
                self._chat_text.pack_forget()
            if self._body_label is not None:
                self._body_label.pack(fill='x', padx=12, pady=(10, 12))
            if self._title_visible and self._title_label is not None:
                self._title_label.pack(fill='x', padx=12, pady=(12, 2),
                                       before=self._body_label)

    def _render_chat(self, entries) -> None:
        widget = self._chat_text
        if widget is None:
            return
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        roles = ('question', 'thinking', 'answer', 'error')
        previous = None
        last_question_index = None
        for role, text in entries:
            if role == 'question' and previous is not None:
                widget.insert('end', '\n\n')
            elif previous is not None:
                widget.insert('end', '\n')
            tag = role if role in roles else 'answer'
            text = '' if text is None else str(text)
            if role == 'question':
                last_question_index = widget.index('end-1c')
            if role == 'answer':
                self._insert_answer(widget, text)
            else:
                widget.insert('end', text, tag)
            previous = role
        widget.configure(state='disabled')
        self._rendered_chat_entries = tuple(entries)
        if last_question_index is None:
            widget.see('end')
        else:
            widget.yview(last_question_index)

    @staticmethod
    def _insert_answer(widget, text) -> None:
        lines = text.splitlines(keepends=True)
        if not lines:
            widget.insert('end', '', 'answer')
            return
        for line in lines:
            content = line.rstrip('\r\n')
            ending = line[len(content):]
            if content.startswith('• '):
                widget.insert('end', content + ending, 'bullet')
                continue
            colon = content.find(':')
            label = content[:colon + 1] if colon >= 0 else ''
            if label and len(label) <= 40 and '.' not in label:
                widget.insert('end', label, 'answer_bold')
                widget.insert('end', content[len(label):] + ending, 'answer')
            else:
                widget.insert('end', content + ending, 'answer')

    def _expired(self):
        return (self._expires_at is not None
                and self.clock() >= self._expires_at)

    def _show_window(self):
        try:
            if not self._mapped:
                return
            root = self._root
            root.update_idletasks()
            self._ensure_game_window()
            if self._chat_mode and self._chat_rect:
                rect = self._chat_rect
                client = self._game_client
                left = int(getattr(client, 'x', 0))
                top = int(getattr(client, 'y', 0))
                client_width = max(1, int(getattr(client, 'width', DEFAULT_CLIENT_WIDTH)))
                client_height = max(1, int(getattr(client, 'height', DEFAULT_CLIENT_HEIGHT)))
                width = max(1, min(int(rect[2]), client_width))
                height = max(1, min(int(rect[3]), client_height))
                x = left + int(rect[0])
                y = top + int(rect[1])
                max_x = left + max(0, client_width - width)
                max_y = top + max(0, client_height - height)
                x = max(left, min(x, max_x))
                y = max(top, min(y, max_y))
                self._place(x, y, width, height)
            else:
                height = max(60, root.winfo_reqheight())
                x, y = compute_position(self._game_client, WINDOW_WIDTH, height)
                self._place(x, y, WINDOW_WIDTH, height)
            self._set_topmost()
            if (self._state_active and self._visible_requested
                    and not self._expired() and self._visible_allowed()):
                self._set_alpha(VISIBLE_ALPHA)
            else:
                self._set_alpha(0.0)
        except Exception:
            LOGGER.exception('Error al mostrar la ventana del overlay')

    def _hide_window(self):
        self._expires_at = None
        self._state_active = False
        self._visible_requested = False
        self._set_alpha(0.0)

    def _set_alpha(self, alpha):
        self._shown = alpha > 0
        try:
            self._root.attributes('-alpha', alpha)
        except Exception:
            pass

    def _get_user32(self):
        if self._user32_loaded:
            return self._user32
        self._user32_loaded = True
        try:
            self._user32 = _load_user32()
        except Exception:
            self._user32 = None
        return self._user32

    def _frame_hwnd(self):
        try:
            win_id = self._root.winfo_id()
        except Exception:
            return 0
        user32 = self._get_user32()
        if user32 is None:
            return win_id
        try:
            return int(user32.GetParent(win_id) or win_id)
        except Exception:
            return win_id

    def _is_window(self, hwnd):
        user32 = self._get_user32()
        if user32 is None:
            return False
        try:
            return bool(user32.IsWindow(hwnd))
        except Exception:
            return False

    def _is_iconic(self, hwnd):
        user32 = self._get_user32()
        if user32 is None:
            return False
        try:
            return bool(user32.IsIconic(hwnd))
        except Exception:
            return False

    def _get_foreground_window(self):
        user32 = self._get_user32()
        if user32 is None:
            return None
        try:
            return user32.GetForegroundWindow()
        except Exception:
            return None

    def _ensure_game_window(self):
        now = self.clock()
        invalid = False
        user32 = self._get_user32()
        if self._game_hwnd and user32 is not None:
            try:
                invalid = not bool(user32.IsWindow(self._game_hwnd))
            except Exception:
                invalid = False
        if (self._last_window_refresh is not None and not invalid
                and now - self._last_window_refresh < GAME_REFRESH_SECONDS):
            return
        self._last_window_refresh = now
        try:
            client = self.window_fn()
        except Exception:
            LOGGER.exception('No se pudo localizar la ventana del juego')
            client = None
        self._game_client = client
        self._game_hwnd = getattr(client, 'hwnd', None)

    def _visible_allowed(self):
        now = self.clock()
        if (self._last_foreground_check is not None
                and now - self._last_foreground_check < FOREGROUND_CHECK_SECONDS):
            return self._foreground_allowed
        self._last_foreground_check = now
        self._ensure_game_window()
        hwnd = self._game_hwnd
        if not hwnd:
            self._foreground_allowed = False
        else:
            foreground = self._get_foreground_window()
            self._foreground_allowed = game_in_front(
                hwnd, foreground, self._is_window, self._is_iconic)
        return self._foreground_allowed

    def _place(self, x, y, width, height):
        # Tk ignora la posición de geometry() en una ventana que mostró Windows sin activarla
        # (cree que sigue oculta) y la dejaba en (0, 0), encima de la tira de píxeles: la
        # posición se fija con SetWindowPos, también sin activar.
        self._root.geometry(f'{width}x{height}+{x}+{y}')
        user32 = self._get_user32()
        if user32 is None:
            return False
        try:
            hwnd = self._frame_hwnd()
            topmost = HWND_TOPMOST
            if not self._user32_injected:
                import ctypes
                topmost = ctypes.c_void_p(HWND_TOPMOST)
            user32.SetWindowPos(hwnd, topmost, int(x), int(y), int(width), int(height),
                                SWP_NOACTIVATE)
            return True
        except Exception:
            return False

    def _set_topmost(self, hwnd=None):
        user32 = self._get_user32()
        if user32 is None:
            return False
        try:
            hwnd = hwnd or self._frame_hwnd()
            topmost = HWND_TOPMOST
            if not self._user32_injected:
                import ctypes
                topmost = ctypes.c_void_p(HWND_TOPMOST)
            user32.SetWindowPos(hwnd, topmost, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
            return True
        except Exception:
            return False

    def _show_no_activate(self, hwnd):
        user32 = self._get_user32()
        if user32 is None:
            return False
        try:
            user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
            return True
        except Exception:
            return False

    def _map_invisible(self):
        try:
            root = self._root
            root.update_idletasks()
            hwnd = self._frame_hwnd()
            self._apply_native_styles(hwnd)
            self._set_alpha(0.0)
            if not self._show_no_activate(hwnd):
                try:
                    root.deiconify()
                    root.update_idletasks()
                except Exception:
                    pass
            self._set_topmost(hwnd)
            self._mapped = True
        except Exception:
            LOGGER.exception('No se pudo mapear la ventana del overlay')

    def _apply_native_styles(self, hwnd=None):
        try:
            if hwnd is None:
                hwnd = self._frame_hwnd()
            user32 = self._get_user32()
            if user32 is None:
                return False
            return self.apply_click_through(hwnd, user32)
        except Exception:
            return False

    @staticmethod
    def apply_click_through(hwnd, user32=None):
        """Marca la ventana como transparente a los clics y sin activación."""
        try:
            if user32 is None:
                user32 = _load_user32()
            get_long = user32.GetWindowLongPtrW
            set_long = user32.SetWindowLongPtrW

            gwl_exstyle = -20
            ex_style = get_long(hwnd, gwl_exstyle)
            ex_style |= 0x00080000  # WS_EX_LAYERED
            ex_style |= 0x00000020  # WS_EX_TRANSPARENT
            ex_style |= 0x08000000  # WS_EX_NOACTIVATE
            ex_style |= 0x00000080  # WS_EX_TOOLWINDOW
            set_long(hwnd, gwl_exstyle, ex_style)
            return True
        except Exception:
            return False
