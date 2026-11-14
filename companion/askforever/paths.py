"""Rutas de los archivos de desarrollo del companion."""

from __future__ import annotations

import os
from pathlib import Path

REPO_DEV_DIR = Path(__file__).resolve().parents[2] / 'addon' / 'AskForever' / 'dev'


def dev_dir(repo_dev_dir: Path = REPO_DEV_DIR) -> Path:
    """Carpeta de desarrollo del addon en el repo; fuera del repo, la del usuario.

    Todo lo de desarrollo (log, informes) se guarda junto en esa carpeta, que
    el script de release excluye del zip público.
    """
    if repo_dev_dir.is_dir():
        return repo_dev_dir
    local = os.environ.get('LOCALAPPDATA')
    if local:
        return Path(local) / 'AskForever'
    return Path.home() / '.askforever'


def user_data_dir() -> Path:
    """Carpeta donde el actualizador guarda los datos del juego; no la crea."""
    local = os.environ.get('LOCALAPPDATA')
    if local:
        return Path(local) / 'AskForever' / 'data'
    return Path.home() / '.askforever' / 'data'
