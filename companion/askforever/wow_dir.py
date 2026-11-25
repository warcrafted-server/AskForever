"""Localiza la carpeta de WoW Forever en los prefijos de Wine del equipo."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

GAME_DIR_NAME = 'World of Warcraft'
FOREVER_DIR_NAME = '_forever_'
ENV_VAR = 'ASKFOREVER_WOW_DIR'

_GAME_SUBPATHS = (
    ('Program Files (x86)', GAME_DIR_NAME, FOREVER_DIR_NAME),
    ('Program Files', GAME_DIR_NAME, FOREVER_DIR_NAME),
    (GAME_DIR_NAME, FOREVER_DIR_NAME),
)


def _has_wow_exe(folder: Path) -> bool:
    """True si la carpeta contiene Wow.exe (el nombre no distingue mayúsculas)."""
    try:
        if not folder.is_dir():
            return False
        return any(entry.is_file() and entry.name.lower() == 'wow.exe'
                   for entry in folder.iterdir())
    except OSError:
        return False


def _children(folder: Path) -> list[Path]:
    """Subcarpetas de `folder`, ordenadas; vacío si no existe o no se puede leer."""
    try:
        return sorted(entry for entry in folder.iterdir() if entry.is_dir())
    except OSError:
        return []


def _drive_roots(home: Path) -> Iterable[Path]:
    """Raíces drive_c de los prefijos de Wine/Lutris/Steam/Bottles habituales."""
    for game in _children(home / 'Games'):
        yield game / 'drive_c'
        yield game / 'prefix' / 'drive_c'

    yield home / '.wine' / 'drive_c'

    steam_roots = (
        home / '.local' / 'share' / 'Steam' / 'steamapps',
        home / '.steam' / 'steam' / 'steamapps',
        home / '.var' / 'app' / 'com.valvesoftware.Steam'
        / '.local' / 'share' / 'Steam' / 'steamapps',
    )
    for steamapps in steam_roots:
        for compat in _children(steamapps / 'compatdata'):
            yield compat / 'pfx' / 'drive_c'

    for game in _children(home / '.var' / 'app' / 'net.lutris.Lutris' / 'Games'):
        yield game / 'drive_c'
        yield game / 'prefix' / 'drive_c'

    for bottle in _children(home / '.local' / 'share' / 'bottles' / 'bottles'):
        yield bottle / 'drive_c'


def _folders_in(drive_c: Path) -> list[Path]:
    """Carpetas _forever_ con Wow.exe dentro de una raíz drive_c."""
    found = []
    for parts in _GAME_SUBPATHS:
        folder = drive_c.joinpath(*parts)
        if _has_wow_exe(folder):
            found.append(folder)
    return found


def _from_override(path: Path) -> list[Path]:
    """Carpeta indicada por ASKFOREVER_WOW_DIR, sea _forever_ o su carpeta padre."""
    for candidate in (path, path / FOREVER_DIR_NAME):
        if _has_wow_exe(candidate):
            return [candidate]
    return []


def _unique(folders: list[Path]) -> list[Path]:
    """Quita duplicados por ruta resuelta y devuelve un orden estable."""
    seen: dict[Path, Path] = {}
    for folder in folders:
        try:
            key = folder.resolve()
        except (OSError, RuntimeError):
            key = folder
        seen.setdefault(key, folder)
    return [seen[key] for key in sorted(seen, key=str)]


def find_wow_dirs(home=None, environ=os.environ) -> list[Path]:
    """Carpetas _forever_ con Wow.exe en los prefijos de Wine del equipo.

    Si ASKFOREVER_WOW_DIR está definida, solo se comprueba esa carpeta. Nunca
    recorre el árbol entero ni falla por permisos: simplemente devuelve lo que
    encuentra.
    """
    home = Path.home() if home is None else Path(home)

    override = environ.get(ENV_VAR)
    if override:
        return _unique(_from_override(Path(override)))

    folders = []
    for drive_c in _drive_roots(home):
        folders.extend(_folders_in(drive_c))
    return _unique(folders)
