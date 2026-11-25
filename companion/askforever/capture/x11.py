"""Ventanas X11 (XWayland) de WoW en Linux mediante ctypes.

Wine/Proton dibuja el juego en una ventana XWayland, así que Xlib sigue siendo la
única vía para conocer su geometría y su estado de foco. No hay dependencia nueva:
se cargan libX11/libXext en tiempo de ejecución y en Windows este módulo se puede
importar sin que falte ninguna biblioteca.
"""

from __future__ import annotations

import contextlib
import ctypes
import ctypes.util
import functools
import sys
import threading
from dataclasses import dataclass
from typing import Iterator, Optional

GAME_CLASS = 'wow.exe'
GAME_TITLE = 'World of Warcraft'

IS_VIEWABLE = 2
SHAPE_INPUT = 2
SHAPE_SET = 0

_LOCK = threading.Lock()


class XWindowAttributes(ctypes.Structure):
    """XWindowAttributes de Xlib, hasta `screen` para que el tamaño sea correcto."""

    _fields_ = [
        ('x', ctypes.c_int),
        ('y', ctypes.c_int),
        ('width', ctypes.c_int),
        ('height', ctypes.c_int),
        ('border_width', ctypes.c_int),
        ('depth', ctypes.c_int),
        ('visual', ctypes.c_void_p),
        ('root', ctypes.c_ulong),
        ('class_', ctypes.c_int),
        ('bit_gravity', ctypes.c_int),
        ('win_gravity', ctypes.c_int),
        ('backing_store', ctypes.c_int),
        ('backing_planes', ctypes.c_ulong),
        ('backing_pixel', ctypes.c_ulong),
        ('save_under', ctypes.c_int),
        ('colormap', ctypes.c_ulong),
        ('map_installed', ctypes.c_int),
        ('map_state', ctypes.c_int),
        ('all_event_masks', ctypes.c_long),
        ('your_event_mask', ctypes.c_long),
        ('do_not_propagate_mask', ctypes.c_long),
        ('override_redirect', ctypes.c_int),
        ('screen', ctypes.c_void_p),
    ]


class XClassHint(ctypes.Structure):
    _fields_ = [('res_name', ctypes.c_void_p), ('res_class', ctypes.c_void_p)]


# Xlib mata el proceso con su manejador de errores por defecto cuando una ventana
# desaparece entre dos llamadas, así que cada método público lo sustituye por este.
_ERROR_HANDLER = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
_IGNORE_ERROR = _ERROR_HANDLER(lambda display, event: 0)


@dataclass
class XWindow:
    """Ventana X con su rectángulo en coordenadas de la ventana raíz."""

    window_id: int
    x: int
    y: int
    width: int
    height: int


def is_game(wm_class_names: tuple[str, ...], title: str) -> bool:
    """¿La ventana es la del juego? Proton a veces pone otra clase, de ahí el título."""
    if any(name.lower() == GAME_CLASS for name in wm_class_names):
        return True
    return title == GAME_TITLE


@functools.lru_cache(maxsize=None)
def _load_library(name: str, fallback: str):
    try:
        return ctypes.CDLL(ctypes.util.find_library(name) or fallback)
    except OSError:
        return None


def _configure_xlib(xlib) -> None:
    """Declara tipos de todas las funciones usadas: punteros y XID de 64 bits."""
    xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
    xlib.XOpenDisplay.restype = ctypes.c_void_p
    xlib.XCloseDisplay.argtypes = [ctypes.c_void_p]
    xlib.XCloseDisplay.restype = ctypes.c_int
    xlib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    xlib.XDefaultRootWindow.restype = ctypes.c_ulong
    xlib.XQueryTree.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
        ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)),
        ctypes.POINTER(ctypes.c_uint),
    ]
    xlib.XQueryTree.restype = ctypes.c_int
    xlib.XGetWindowAttributes.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(XWindowAttributes)]
    xlib.XGetWindowAttributes.restype = ctypes.c_int
    xlib.XGetClassHint.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(XClassHint)]
    xlib.XGetClassHint.restype = ctypes.c_int
    xlib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    xlib.XInternAtom.restype = ctypes.c_ulong
    xlib.XGetWindowProperty.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_long, ctypes.c_long,
        ctypes.c_int, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_ulong),
        ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
    ]
    xlib.XGetWindowProperty.restype = ctypes.c_int
    xlib.XFree.argtypes = [ctypes.c_void_p]
    xlib.XFree.restype = ctypes.c_int
    xlib.XTranslateCoordinates.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_ulong),
    ]
    xlib.XTranslateCoordinates.restype = ctypes.c_int
    xlib.XFlush.argtypes = [ctypes.c_void_p]
    xlib.XFlush.restype = ctypes.c_int
    xlib.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
    xlib.XSync.restype = ctypes.c_int
    xlib.XSetErrorHandler.argtypes = [ctypes.c_void_p]
    xlib.XSetErrorHandler.restype = ctypes.c_void_p


def _configure_xext(xext) -> None:
    xext.XShapeQueryExtension.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
    xext.XShapeQueryExtension.restype = ctypes.c_int
    xext.XShapeCombineRectangles.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ]
    xext.XShapeCombineRectangles.restype = None


def open_display() -> Optional['X11Display']:
    """Abre la pantalla X o devuelve None; nunca lanza (sin Linux, libX11 o DISPLAY)."""
    if not sys.platform.startswith('linux'):
        return None
    try:
        xlib = _load_library('X11', 'libX11.so.6')
        if xlib is None:
            return None
        _configure_xlib(xlib)
        display = xlib.XOpenDisplay(None)
        if not display:
            return None
        return X11Display(display, xlib)
    except Exception:
        return None


class X11Display:
    """Pantalla X abierta: localiza la ventana del juego y su estado."""

    def __init__(self, display: int, xlib) -> None:
        self._display = ctypes.c_void_p(display)
        self._xlib = xlib
        _configure_xlib(xlib)
        self._root = int(xlib.XDefaultRootWindow(self._display))
        self._atoms: dict[bytes, int] = {}
        self._closed = False

    @contextlib.contextmanager
    def _protected(self) -> Iterator[None]:
        """Ignora errores de ventanas que desaparecen y restaura el manejador."""
        with _LOCK:
            previous = self._xlib.XSetErrorHandler(
                ctypes.cast(_IGNORE_ERROR, ctypes.c_void_p))
            try:
                yield
            finally:
                try:
                    self._xlib.XSync(self._display, False)
                finally:
                    # None restaura el manejador por defecto de Xlib.
                    self._xlib.XSetErrorHandler(previous)

    def _atom(self, name: bytes) -> int:
        atom = self._atoms.get(name)
        if atom is None:
            atom = int(self._xlib.XInternAtom(self._display, name, False))
            self._atoms[name] = atom
        return atom

    def _children(self, window: int) -> list[int]:
        root = ctypes.c_ulong()
        parent = ctypes.c_ulong()
        children = ctypes.POINTER(ctypes.c_ulong)()
        count = ctypes.c_uint()
        if not self._xlib.XQueryTree(
                self._display, window, ctypes.byref(root), ctypes.byref(parent),
                ctypes.byref(children), ctypes.byref(count)):
            return []
        try:
            return [int(children[index]) for index in range(count.value)]
        finally:
            if children:
                self._xlib.XFree(ctypes.cast(children, ctypes.c_void_p))

    def _attributes(self, window: int) -> Optional[XWindowAttributes]:
        attributes = XWindowAttributes()
        if not self._xlib.XGetWindowAttributes(
                self._display, window, ctypes.byref(attributes)):
            return None
        return attributes

    def _property(self, window: int, atom: int, req_type: int = 0):
        actual_type = ctypes.c_ulong()
        actual_format = ctypes.c_int()
        items = ctypes.c_ulong()
        after = ctypes.c_ulong()
        data = ctypes.POINTER(ctypes.c_ubyte)()
        status = self._xlib.XGetWindowProperty(
            self._display, window, atom, 0, 1024, False, req_type,
            ctypes.byref(actual_type), ctypes.byref(actual_format), ctypes.byref(items),
            ctypes.byref(after), ctypes.byref(data))
        if status != 0 or not data:
            if data:
                self._xlib.XFree(ctypes.cast(data, ctypes.c_void_p))
            return None
        try:
            if actual_format.value == 8:
                return ctypes.string_at(data, items.value)
            if actual_format.value == 32 and items.value:
                return int(ctypes.cast(data, ctypes.POINTER(ctypes.c_ulong))[0])
            return None
        finally:
            self._xlib.XFree(ctypes.cast(data, ctypes.c_void_p))

    def _window_title(self, window: int) -> str:
        name = self._property(
            window, self._atom(b'_NET_WM_NAME'), self._atom(b'UTF8_STRING'))
        if name is None:
            name = self._property(window, self._atom(b'WM_NAME'))
        if isinstance(name, bytes):
            return name.decode('utf-8', 'replace')
        return ''

    def _window_classes(self, window: int) -> tuple[str, ...]:
        hint = XClassHint()
        if not self._xlib.XGetClassHint(
                self._display, window, ctypes.byref(hint)):
            return ()
        names: list[str] = []
        try:
            for pointer in (hint.res_name, hint.res_class):
                if pointer:
                    names.append(ctypes.string_at(pointer).decode('utf-8', 'replace'))
        finally:
            if hint.res_name:
                self._xlib.XFree(hint.res_name)
            if hint.res_class:
                self._xlib.XFree(hint.res_class)
        return tuple(names)

    def _translate(self, window: int) -> tuple[int, int]:
        x = ctypes.c_int()
        y = ctypes.c_int()
        child = ctypes.c_ulong()
        if not self._xlib.XTranslateCoordinates(
                self._display, window, self._root, 0, 0,
                ctypes.byref(x), ctypes.byref(y), ctypes.byref(child)):
            return 0, 0
        return x.value, y.value

    def _find_game_window(self) -> Optional[XWindow]:
        best: Optional[XWindow] = None
        best_area = 0
        pending = [self._root]
        while pending:
            window = pending.pop()
            pending.extend(self._children(window))
            if window == self._root:
                continue
            attributes = self._attributes(window)
            if attributes is None or attributes.map_state != IS_VIEWABLE:
                # Sin consultar título ni clase: la mayoría de ventanas no son visibles.
                continue
            if attributes.width <= 0 or attributes.height <= 0:
                continue
            if not is_game(self._window_classes(window), self._window_title(window)):
                continue
            area = attributes.width * attributes.height
            if best is not None and area <= best_area:
                continue
            x, y = self._translate(window)
            best = XWindow(int(window), x, y, attributes.width, attributes.height)
            best_area = area
        return best

    def find_game_window(self) -> Optional[XWindow]:
        """Ventana visible del juego de mayor área, o None si no está abierta."""
        if self._closed:
            return None
        try:
            with self._protected():
                return self._find_game_window()
        except Exception:
            return None

    def game_is_active(self) -> Optional[bool]:
        """True si la ventana activa es la del juego; None si no hay propiedad."""
        if self._closed:
            return None
        try:
            with self._protected():
                active = self._property(
                    self._root, self._atom(b'_NET_ACTIVE_WINDOW'))
                if not isinstance(active, int):
                    return None
                if active == 0:
                    return False
                game = self._find_game_window()
                return game is not None and game.window_id == active
        except Exception:
            return None

    def _append_with_parents(self, window: int, targets: list[int]) -> None:
        while window and window != self._root and window not in targets:
            targets.append(window)
            root = ctypes.c_ulong()
            parent = ctypes.c_ulong()
            children = ctypes.POINTER(ctypes.c_ulong)()
            count = ctypes.c_uint()
            if not self._xlib.XQueryTree(
                    self._display, window, ctypes.byref(root), ctypes.byref(parent),
                    ctypes.byref(children), ctypes.byref(count)):
                return
            if children:
                self._xlib.XFree(ctypes.cast(children, ctypes.c_void_p))
            if parent.value == root.value:
                return
            window = int(parent.value)

    def set_input_passthrough(self, window_ids: list[int]) -> bool:
        """Vacía la región de entrada XShape de las ventanas y sus padres (sin raíz)."""
        if self._closed:
            return False
        try:
            xext = _load_library('Xext', 'libXext.so.6')
            if xext is None:
                return False
            _configure_xext(xext)
            with self._protected():
                event_base = ctypes.c_int()
                error_base = ctypes.c_int()
                if not xext.XShapeQueryExtension(
                        self._display, ctypes.byref(event_base),
                        ctypes.byref(error_base)):
                    return False
                targets: list[int] = []
                for window in window_ids:
                    self._append_with_parents(int(window), targets)
                for window in targets:
                    xext.XShapeCombineRectangles(
                        self._display, window, SHAPE_INPUT, 0, 0, None, 0,
                        SHAPE_SET, 0)
                self._xlib.XFlush(self._display)
                return True
        except Exception:
            return False

    def close(self) -> None:
        if self._closed or not self._display:
            return
        self._closed = True
        try:
            with _LOCK:
                self._xlib.XSync(self._display, False)
                self._xlib.XCloseDisplay(self._display)
        except Exception:
            pass
        self._display = ctypes.c_void_p()

    def __enter__(self) -> 'X11Display':
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False
