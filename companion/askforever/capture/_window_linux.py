"""Localiza el proceso de WoW bajo Wine/Proton y la ventana que dibuja en XWayland.

El proceso se detecta leyendo /proc; la geometría real se pregunta a X11 cuando hay
pantalla y ventana del juego. Si no la hay (Wayland puro, portal de pantalla) se
mantiene la geometría provisional: la captura real la decide el backend y recorta
la esquina del monitor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from askforever.capture import x11
from askforever.capture.window import GameWindow

DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080


def set_dpi_awareness() -> None:
    """En Linux no hace falta."""


def _read_cmdline(pid: int) -> list[str]:
    try:
        raw = (Path('/proc') / str(pid) / 'cmdline').read_bytes()
    except OSError:
        return []
    return [part.decode('utf-8', 'replace') for part in raw.split(b'\0') if part]


def _basename(path: str) -> str:
    """Nombre de archivo de una ruta de Windows (Z:\\...) o de Unix."""
    return path.replace('\\', '/').rsplit('/', 1)[-1]


def _process_image_path(pid: int) -> Optional[str]:
    """Ruta del ejecutable del proceso tal como la ve Wine (primer argumento)."""
    args = _read_cmdline(int(pid))
    return args[0] if args else None


def _x11_window(open_display) -> Optional[x11.XWindow]:
    """Geometría de la ventana del juego en X11, o None si no se puede consultar."""
    try:
        display = open_display()
        if display is None:
            return None
        try:
            return display.find_game_window()
        finally:
            display.close()
    except Exception:
        return None


def find_game_window(
        process_name: str = 'Wow.exe', proc_root: Path = Path('/proc'),
        open_display=x11.open_display) -> Optional[GameWindow]:
    """GameWindow del proceso `process_name`, con geometría X11 si está disponible."""
    target = process_name.lower()
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / 'cmdline').read_bytes()
        except OSError:
            continue
        args = [part.decode('utf-8', 'replace') for part in raw.split(b'\0') if part]
        if args and _basename(args[0]).lower() == target:
            pid = int(entry.name)
            found = _x11_window(open_display)
            if found is not None:
                return GameWindow(
                    pid, process_name, found.x, found.y,
                    found.width, found.height, args[0])
            return GameWindow(
                pid, process_name, 0, 0, DEFAULT_WIDTH, DEFAULT_HEIGHT, args[0])
    return None
