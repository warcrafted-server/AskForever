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

# find_game_window se llama con frecuencia; recordar la traducción evita releer
# /proc/<pid>/environ y /proc/<pid>/maps en cada vuelta.
_PATH_CACHE: dict[tuple[str, int, str], Optional[str]] = {}
_CACHE_LIMIT = 64


def set_dpi_awareness() -> None:
    """En Linux no hace falta."""


def _read_cmdline(pid: int) -> list[str]:
    try:
        raw = (Path('/proc') / str(pid) / 'cmdline').read_bytes()
    except OSError:
        return []
    return [part.decode('utf-8', 'replace') for part in raw.split(b'\0') if part]


def _read_environ(pid: int, proc_root: Path) -> dict[str, str]:
    """Variables de entorno del proceso (separadas por NUL), o vacío si no se puede."""
    try:
        raw = (proc_root / str(pid) / 'environ').read_bytes()
    except OSError:
        return {}
    values = {}
    for part in raw.split(b'\0'):
        key, sep, value = part.partition(b'=')
        if not sep:
            continue
        values[key.decode('utf-8', 'replace')] = value.decode('utf-8', 'replace')
    return values


def _basename(path: str) -> str:
    """Nombre de archivo de una ruta de Windows (Z:\\...) o de Unix."""
    return path.replace('\\', '/').rsplit('/', 1)[-1]


def _wine_prefix(pid: int, proc_root: Path) -> Optional[Path]:
    """Prefijo de Wine del proceso, deducido de su entorno."""
    environ = _read_environ(pid, proc_root)
    prefix = environ.get('WINEPREFIX')
    if prefix:
        return Path(prefix)
    compat_data = environ.get('STEAM_COMPAT_DATA_PATH')
    if compat_data:
        return Path(compat_data) / 'pfx'
    # Sin variables: solo sirve para resolver unidades, así que ~/.wine basta.
    fallback = Path.home() / '.wine'
    return fallback if fallback.is_dir() else None


def _match_child(parent: Path, name: str) -> Optional[Path]:
    """Hijo de `parent` con ese nombre, sin distinguir mayúsculas."""
    candidate = parent / name
    try:
        if candidate.exists():
            return candidate
        lowered = name.lower()
        for entry in parent.iterdir():
            if entry.name.lower() == lowered:
                return entry
    except OSError:
        return None
    return None


def _walk_components(root: Path, components: list[str]) -> Optional[Path]:
    """Recorre componentes bajo `root`, aceptando diferencias de mayúsculas."""
    current = root
    for name in components:
        current = _match_child(current, name)
        if current is None:
            return None
    return current if current.exists() else None


def _resolve_from_maps(pid: int, executable: str,
                       proc_root: Path) -> Optional[str]:
    """Ruta Unix del ejecutable según los archivos mapeados por el proceso."""
    wanted = _basename(executable).lower()
    if not wanted:
        return None
    try:
        text = (proc_root / str(pid) / 'maps').read_text(
            encoding='utf-8', errors='replace')
    except OSError:
        return None
    for line in text.splitlines():
        # La ruta es la sexta columna y puede contener espacios.
        parts = line.split(maxsplit=5)
        if len(parts) != 6:
            continue
        candidate = parts[5]
        if _basename(candidate).lower() != wanted:
            continue
        try:
            if Path(candidate).exists():
                return candidate
        except OSError:
            continue
    return None


def resolve_windows_path(pid: int, path: str,
                         proc_root: Path = Path('/proc')) -> Optional[str]:
    """Traduce a una ruta real de Unix la ruta del ejecutable que da Wine.

    Acepta rutas de Unix ya válidas y rutas con unidad de Windows (C:\\...), que
    se resuelven con dosdevices o drive_c del prefijo del proceso. Si no hay
    manera directa, busca el ejecutable entre los archivos mapeados del proceso.
    Devuelve None si no se puede averiguar; nunca lanza por errores de lectura.
    """
    if not path:
        return None
    try:
        direct = Path(path)
        if direct.is_absolute() and direct.exists():
            return str(direct)
    except (OSError, ValueError):
        pass

    text = path.replace('\\', '/')
    drive, sep, rest = text.partition(':')
    if sep and len(drive) == 1 and drive.isalpha():
        drive = drive.lower()
        prefix = _wine_prefix(int(pid), proc_root)
        root = None
        if prefix is not None:
            link = prefix / 'dosdevices' / f'{drive}:'
            try:
                if link.exists() or link.is_symlink():
                    root = link.resolve()
            except (OSError, RuntimeError):
                root = None
            if root is None or not root.is_dir():
                if drive == 'c':
                    root = prefix / 'drive_c'
                elif drive == 'z':
                    root = Path('/')
        if root is not None:
            components = [part for part in rest.split('/') if part]
            found = _walk_components(root, components)
            if found is not None:
                return str(found)
    return _resolve_from_maps(int(pid), path, proc_root)


def _cached_resolve(pid: int, path: str,
                    proc_root: Path = Path('/proc')) -> Optional[str]:
    """resolve_windows_path con una caché pequeña por proceso y ruta."""
    key = (str(proc_root), int(pid), path)
    if key in _PATH_CACHE:
        return _PATH_CACHE[key]
    resolved = resolve_windows_path(pid, path, proc_root)
    if len(_PATH_CACHE) >= _CACHE_LIMIT:
        _PATH_CACHE.clear()
    _PATH_CACHE[key] = resolved
    return resolved


def _resolved_or_raw(pid: int, executable: str,
                     proc_root: Path = Path('/proc')) -> str:
    """Ruta Unix del ejecutable si se puede traducir; si no, la que dio Wine."""
    return _cached_resolve(pid, executable, proc_root) or executable


def _process_image_path(pid: int) -> Optional[str]:
    """Ruta del ejecutable del proceso, ya traducida a Unix bajo Wine."""
    args = _read_cmdline(int(pid))
    if not args:
        return None
    return _resolved_or_raw(int(pid), args[0])


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
            exe_path = _resolved_or_raw(pid, args[0], proc_root)
            found = _x11_window(open_display)
            if found is not None:
                return GameWindow(
                    pid, process_name, found.x, found.y,
                    found.width, found.height, exe_path)
            return GameWindow(
                pid, process_name, 0, 0, DEFAULT_WIDTH, DEFAULT_HEIGHT, exe_path)
    return None
