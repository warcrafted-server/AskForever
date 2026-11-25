"""Entorno para los programas del sistema que arranca la app empaquetada."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from typing import Optional


def external_env(environ=None, platform: Optional[str] = None,
                 frozen: Optional[bool] = None) -> Optional[dict]:
    """Entorno con el que lanzar un programa externo: el del sistema, no el del paquete.

    PyInstaller en Linux pone en LD_LIBRARY_PATH la carpeta `_internal` del paquete y
    guarda el valor original en LD_LIBRARY_PATH_ORIG. Un programa del sistema arrancado
    con esa ruta carga bibliotecas incompatibles. Devuelve None (heredar el entorno tal
    cual) fuera de Linux empaquetado, y nunca modifica os.environ: el hijo de
    multiprocessing del overlay sí necesita el entorno del paquete.
    """
    if platform is None:
        platform = sys.platform
    if frozen is None:
        frozen = bool(getattr(sys, 'frozen', False))
    if not platform.startswith('linux') or not frozen:
        return None
    env = dict(os.environ if environ is None else environ)
    original = env.get('LD_LIBRARY_PATH_ORIG')
    if original:
        env['LD_LIBRARY_PATH'] = original
    else:
        env.pop('LD_LIBRARY_PATH', None)
    return env


def open_url(url: str) -> bool:
    """Abre una dirección en el navegador sin pasarle las bibliotecas del paquete."""
    env = external_env()
    if env is not None:
        try:
            subprocess.Popen(['xdg-open', url], env=env)
            return True
        except OSError:
            pass
    return webbrowser.open(url)
