"""Localiza la ventana del juego de WoW Forever y calcula su región de captura."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional

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


def client_region_for(window: GameWindow, width_px: int, height_px: int) -> dict:
    """Región lista para mss: esquina superior izquierda del área cliente, recortada."""
    width = max(1, min(int(width_px), window.width))
    height = max(1, min(int(height_px), window.height))
    return {'left': window.x, 'top': window.y, 'width': width, 'height': height}


if sys.platform == 'win32':
    from askforever.capture._window_win import (  # noqa: E402,F401
        _process_image_path, find_game_window, set_dpi_awareness)
else:
    from askforever.capture._window_linux import (  # noqa: E402,F401
        _process_image_path, find_game_window, set_dpi_awareness)
