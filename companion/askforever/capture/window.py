"""Localiza la ventana del juego de WoW Forever y calcula su región de captura."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
# DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2: coordenadas en píxeles físicos.
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ClientToScreen.restype = wintypes.BOOL

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL


def set_dpi_awareness() -> None:
    """Marca el proceso como DPI-aware para que las coordenadas sean físicas."""
    try:
        if user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
            return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.WinDLL('shcore').SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass


set_dpi_awareness()


@dataclass
class GameWindow:
    """Ventana del juego con su área cliente en coordenadas de pantalla."""

    hwnd: int
    title: str
    x: int
    y: int
    width: int
    height: int
    exe_path: str = ''


def _process_image_path(hwnd: int) -> Optional[str]:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value
        return None
    finally:
        kernel32.CloseHandle(handle)


def _client_area(hwnd: int) -> Optional[tuple[int, int, int, int]]:
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None
    point = wintypes.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(point)):
        return None
    return point.x, point.y, width, height


def find_game_window(process_name: str = 'Wow.exe') -> Optional[GameWindow]:
    """Devuelve la ventana visible del proceso con mayor área cliente, o None."""
    target = process_name.lower()
    found: list[GameWindow] = []

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        path = _process_image_path(hwnd)
        if not path or os.path.basename(path).lower() != target:
            return True
        area = _client_area(hwnd)
        if area is None:
            return True
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, 512)
        found.append(GameWindow(int(hwnd), title.value, *area, path))
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    if not found:
        return None
    return max(found, key=lambda window: window.width * window.height)


def client_region_for(window: GameWindow, width_px: int, height_px: int) -> dict:
    """Región lista para mss: esquina superior izquierda del área cliente, recortada."""
    width = max(1, min(int(width_px), window.width))
    height = max(1, min(int(height_px), window.height))
    return {'left': window.x, 'top': window.y, 'width': width, 'height': height}
