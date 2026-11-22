#!/usr/bin/env python3
"""Comprueba la captura por portal de extremo a extremo (Linux/Wayland).

Con WoW abierto, ejecuta el script, elige el monitor del juego si el portal lo pide y,
dentro del juego, escribe /af pattern (dura 10 s; repítelo si hace falta). Muestra
cuántas capturas y cuántos marcos válidos del protocolo se leen en SECONDS segundos.

    python tools/check_portal_capture.py [--seconds 30]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from askforever.capture.portal import PortalCapture  # noqa: E402
from askforever.protocol.codec import decode_image  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--token', type=Path, default=Path('spike-linux/portal-token'))
    args = parser.parse_args()
    args.token.parent.mkdir(parents=True, exist_ok=True)

    errors = []
    capture = PortalCapture(token_path=args.token, on_error=errors.append)
    captures = valid = 0
    deadline = None
    print('Abriendo el portal (puede salir el diálogo de KDE)...')
    try:
        while deadline is None or time.monotonic() < deadline:
            image = capture()
            if image is None:
                if errors:
                    print('Error:', errors[-1])
                    return 1
                continue
            if deadline is None:
                deadline = time.monotonic() + args.seconds
                print(f'Capturando {args.seconds:g} s: escribe /af pattern en el juego.')
            captures += 1
            if decode_image(image) is not None:
                valid += 1
    finally:
        capture.close()
    print(f'Capturas: {captures} · marcos válidos: {valid}')
    print('OK' if valid else 'Sin marcos válidos: ¿WoW en el monitor elegido y /af pattern activo?')
    return 0 if valid else 2


if __name__ == '__main__':
    sys.exit(main())
