"""Localiza el proceso de WoW bajo Wine/Proton leyendo /proc.

En Linux no hay API de ventanas común (Wayland no expone posiciones), así que solo
se detecta que el juego está en marcha. La geometría es provisional: la captura real
la decide el backend de captura (portal de pantalla) y recorta la esquina del monitor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

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


def find_game_window(process_name: str = 'Wow.exe', proc_root: Path = Path('/proc')) -> Optional[GameWindow]:
    """Devuelve un GameWindow provisional si hay un proceso `process_name`, o None."""
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
            return GameWindow(int(entry.name), process_name, 0, 0, DEFAULT_WIDTH, DEFAULT_HEIGHT, args[0])
    return None
