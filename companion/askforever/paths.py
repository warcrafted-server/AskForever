"""Rutas de los archivos de desarrollo del companion."""

from __future__ import annotations

import os
import sys
from pathlib import Path

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
