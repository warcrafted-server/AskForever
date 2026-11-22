"""Desinstalación de AskForever: claves, datos y addons."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, Optional

import keyring

from askforever import config, paths
from askforever.capture.window import _process_image_path, find_game_window

_ORIGINAL_KEYRING = keyring


def _keyring_backend():
    """Respeta un keyring sustituido tanto en config como en este módulo."""
    if config.keyring is not _ORIGINAL_KEYRING:
        return config.keyring
    return keyring


def _user_root() -> Path:
    """Carpeta que el companion deja en el equipo del jugador."""
    return paths.app_root()


def _inside(path: Path, root: Path) -> bool:
    """True si la ruta resuelta queda dentro de la carpeta esperada."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def _remove(path: Path, root: Path) -> bool:
    if not _inside(path, root):
        print(f'Se omite una ruta fuera de la carpeta esperada: {path}')
        return False
    try:
        if path.is_symlink():
            path.unlink()
        elif getattr(path, 'is_junction', lambda: False)():
            os.rmdir(path)
        elif path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        else:
            return False
    except OSError as error:
        print(f'No se pudo borrar {path}: {error}')
        return False
    print(f'Borrado: {path}')
    return True


def _addons_dir(game_addons_dir) -> Optional[Path]:
    if game_addons_dir is not None:
        return Path(game_addons_dir)
    try:
        window = find_game_window()
        if window is None:
            return None
        executable = _process_image_path(window.hwnd)
    except Exception:
        return None
    if not executable:
        return None
    return Path(executable).parent / 'Interface' / 'AddOns'


def _confirm(input_fn) -> bool:
    try:
        answer = (input_fn('¿Desinstalar AskForever y borrar sus datos? [s/N]: ') or '')
        answer = answer.strip().lower()
    except (EOFError, KeyboardInterrupt, OSError):
        print()
        return False
    return answer in ('s', 'si', 'sí', 'y', 'yes')


def uninstall(yes: bool = False, remove_addon: bool = False,
              input_fn: Callable[[str], str] = input,
              game_addons_dir=None) -> int:
    """Borra claves, datos y addons de AskForever; 0 si termina."""
    root = _user_root()
    addons_dir = _addons_dir(game_addons_dir)
    slot_paths = []
    addon_path = None

    if addons_dir is not None and addons_dir.is_dir():
        for child in sorted(addons_dir.glob('AskForever_Slot*'), key=str):
            if (child.is_symlink() or child.exists()) and _inside(child, addons_dir):
                slot_paths.append(child)
        if remove_addon:
            candidate = addons_dir / 'AskForever'
            if (candidate.is_symlink() or candidate.exists()) and _inside(candidate, addons_dir):
                addon_path = candidate

    providers = sorted(config.PROVIDERS)
    print('Se borrarán:')
    print('  - Claves de API de: ' + ', '.join(providers))
    # Congelado en Linux, root es la carpeta del propio programa: se borran solo sus datos
    # y logs, y la carpeta entera la borra uninstall.sh cuando el programa ha terminado.
    owned = [root / 'data', root / 'logs'] if paths.is_portable() else [root]
    for folder in owned:
        if folder.is_symlink() or folder.exists():
            print(f'  - Carpeta de datos: {folder}')
    for path in slot_paths:
        print(f'  - Addon: {path}')
    if addon_path is not None:
        print(f'  - Addon: {addon_path}')

    if not yes and not _confirm(input_fn):
        print('Desinstalación cancelada.')
        return 0

    failed = False
    backend = _keyring_backend()
    for name in providers:
        preset = config.PROVIDERS[name]
        try:
            backend.delete_password(config.KEYRING_SERVICE, preset.keyring_user)
        except Exception:
            continue
        print(f'Clave de API borrada: {name}')

    for folder in owned:
        if folder.is_symlink() or folder.exists():
            if not _remove(folder, root):
                failed = True
    for path in slot_paths:
        if not _remove(path, addons_dir):
            failed = True
    if addon_path is not None:
        if not _remove(addon_path, addons_dir):
            failed = True

    if failed:
        print('La desinstalación terminó con errores.')
        return 1
    print('AskForever desinstalado.')
    return 0
