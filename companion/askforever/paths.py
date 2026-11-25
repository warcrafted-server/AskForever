"""Rutas de los archivos de desarrollo del companion."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

REPO_DEV_DIR = Path(__file__).resolve().parents[2] / 'addon' / 'AskForever' / 'dev'


def is_portable() -> bool:
    """True en el ejecutable congelado de Linux: datos y logs junto al programa."""
    return sys.platform != 'win32' and bool(getattr(sys, 'frozen', False))


def app_root() -> Path:
    """Carpeta que agrupa los datos (data/) y los logs (logs/) del companion.

    En Linux congelado es la carpeta del programa dentro de la del juego, para que
    desinstalar sea borrar una sola carpeta. ASKFOREVER_HOME la fuerza.
    """
    override = os.environ.get('ASKFOREVER_HOME')
    if override:
        return Path(override)
    local = os.environ.get('LOCALAPPDATA')
    if local:
        return Path(local) / 'AskForever'
    if is_portable():
        return Path(sys.executable).resolve().parent
    if sys.platform != 'win32':
        data_home = os.environ.get('XDG_DATA_HOME')
        return (Path(data_home) if data_home else Path.home() / '.local' / 'share') / 'askforever'
    return Path.home() / '.askforever'


def portable_game_dir() -> Optional[Path]:
    """Carpeta del juego alrededor del programa empaquetado, si está ahí.

    Ninguna variable de entorno la altera: desinstalar debe apuntar siempre a la
    instalación que contiene este programa y no a otra partida del juego.
    """
    if not is_portable():
        return None
    game_dir = Path(sys.executable).resolve().parent.parent
    try:
        entries = list(game_dir.iterdir())
    except OSError:
        return None
    if any(entry.name.lower() == 'wow.exe' for entry in entries):
        return game_dir
    if any(entry.name.lower() == 'interface' and entry.is_dir() for entry in entries):
        return game_dir
    return None


def dev_dir(repo_dev_dir: Path = REPO_DEV_DIR) -> Path:
    """Carpeta de desarrollo del addon en el repo; fuera del repo, la del usuario.

    Todo lo de desarrollo (log, informes) se guarda junto en esa carpeta, que
    el script de release excluye del zip público.
    """
    if repo_dev_dir.is_dir():
        return repo_dev_dir
    return app_root()


def user_data_dir() -> Path:
    """Carpeta donde el actualizador guarda los datos del juego; no la crea."""
    return app_root() / 'data'
