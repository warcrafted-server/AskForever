#!/usr/bin/env python3
"""Spike Linux/Wayland: captura la pantalla y guarda la esquina superior izquierda.

Sirve para saber si la tira de píxeles de AskForever sobrevive a la captura
(colores exactos, sin compresión ni escalado). Con WoW abierto en ventana sin
bordes y `/af pattern` (o el mensaje pendiente) activo, ejecuta:

    python tools/spike_capture_linux.py --backend spectacle
    python tools/spike_capture_linux.py --backend portal

Requisitos del sistema (Arch): python-pillow; spectacle (KDE) para el backend
spectacle; python-gobject, gstreamer y gst-plugin-pipewire para el portal.
Con venv: python -m venv --system-site-packages .venv-linux
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from PIL import Image

STRIP_WIDTH = 512
STRIP_HEIGHT = 32
RESTORE_TOKEN_FILE = Path.home() / '.cache' / 'askforever-spike-portal-token'


def capture_spectacle(out: Path, delay: float = 0) -> None:
    """KDE: captura de pantalla completa sin interfaz ni aviso."""
    time.sleep(delay)
    subprocess.run(['spectacle', '-b', '-n', '-f', '-o', str(out)], check=True, timeout=30)


def capture_portal(out: Path, delay: float = 0) -> None:
    """xdg-desktop-portal ScreenCast + PipeWire: un fotograma del monitor."""
    import gi

    gi.require_version('Gio', '2.0')
    from gi.repository import Gio, GLib

    bus = Gio.bus_get_sync(Gio.BusType.SESSION)
    sender = bus.get_unique_name().lstrip(':').replace('.', '_')
    loop = GLib.MainLoop()
    counter = [0]

    def call(method, params, fd_list=None):
        return bus.call_with_unix_fd_list_sync(
            'org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop',
            'org.freedesktop.portal.ScreenCast', method, params, None,
            Gio.DBusCallFlags.NONE, -1, fd_list, None)

    def request(method, build):
        """Llama a un método con handle_token y espera su señal Response."""
        counter[0] += 1
        token = f'af{os.getpid()}_{counter[0]}'
        path = f'/org/freedesktop/portal/desktop/request/{sender}/{token}'
        result = {}

        def on_response(_c, _s, _p, _i, _n, params):
            result['code'], result['data'] = params.unpack()
            loop.quit()

        sub = bus.signal_subscribe(
            'org.freedesktop.portal.Desktop', 'org.freedesktop.portal.Request',
            'Response', path, None, Gio.DBusSignalFlags.NONE, on_response)
        call(method, build(token))
        GLib.timeout_add_seconds(120, loop.quit)
        loop.run()
        bus.signal_unsubscribe(sub)
        if result.get('code') != 0:
            raise RuntimeError(f'{method}: respuesta {result.get("code")} (¿cancelado?)')
        return result['data']

    def opts(**values):
        return values

    created = request('CreateSession', lambda token: GLib.Variant('(a{sv})', (opts(
        handle_token=GLib.Variant('s', token),
        session_handle_token=GLib.Variant('s', f'afs{os.getpid()}')),)))
    session = created['session_handle']

    select_opts = {
        'types': GLib.Variant('u', 1),
        'cursor_mode': GLib.Variant('u', 1),
        'persist_mode': GLib.Variant('u', 2),
    }
    if RESTORE_TOKEN_FILE.is_file():
        select_opts['restore_token'] = GLib.Variant('s', RESTORE_TOKEN_FILE.read_text().strip())
    request('SelectSources', lambda token: GLib.Variant('(oa{sv})', (session, opts(
        handle_token=GLib.Variant('s', token), **select_opts))))

    started = request('Start', lambda token: GLib.Variant('(osa{sv})', (session, '', opts(
        handle_token=GLib.Variant('s', token)))))
    if 'restore_token' in started:
        RESTORE_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        RESTORE_TOKEN_FILE.write_text(started['restore_token'])
    streams = started['streams']
    if not streams:
        raise RuntimeError('El portal no devolvió ningún flujo')
    node_id = streams[0][0]

    _reply, fds = call('OpenPipeWireRemote', GLib.Variant('(oa{sv})', (session, opts())))
    fd = fds.get(0)
    print(f'Portal listo. Captura en {delay:g} s: ve a WoW y escribe /af pattern.')
    time.sleep(delay)
    subprocess.run(
        ['gst-launch-1.0', '-q', 'pipewiresrc', f'fd={fd}', f'path={node_id}',
         'num-buffers=3', '!', 'videoconvert', '!', 'pngenc', 'snapshot=true', '!',
         'filesink', f'location={out}'],
        check=True, pass_fds=[fd], timeout=30)
    bus.call_sync('org.freedesktop.portal.Desktop', session,
                  'org.freedesktop.portal.Session', 'Close', None, None,
                  Gio.DBusCallFlags.NONE, -1, None)


def describe(strip: Image.Image) -> None:
    pixels = strip.get_flattened_data() if hasattr(strip, 'get_flattened_data') else strip.getdata()
    colors = Counter(pixels)
    print(f'Tira {strip.width}x{strip.height}: {len(colors)} colores distintos')
    print('Más frecuentes:', colors.most_common(6))
    first_row = [strip.getpixel((x, 0)) for x in range(0, 64, 8)]
    print('Fila superior (cada 8 px):', first_row)
    if len(colors) <= 1:
        print('AVISO: la zona es de un solo color; no hay tira (¿pantalla negra por Wayland, o WoW sin /af pattern?).')
    off_palette = [c for c in colors if any(v not in (0, 85, 170, 255) for v in c)]
    if off_palette:
        print(f'AVISO: {len(off_palette)} colores fuera de la paleta 0/85/170/255; hay compresión o escalado.')
    else:
        print('OK: todos los colores están en la paleta 0/85/170/255 (sin distorsión).')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--backend', choices=('spectacle', 'portal'), default='spectacle')
    parser.add_argument('--out', type=Path, default=Path('spike-linux'))
    parser.add_argument('--delay', type=float, default=0, help='segundos de espera antes de capturar')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    full = args.out / f'{args.backend}-full.png'
    capture = capture_spectacle if args.backend == 'spectacle' else capture_portal
    capture(full, args.delay)

    image = Image.open(full).convert('RGB')
    print(f'Captura completa: {image.width}x{image.height} -> {full}')
    strip = image.crop((0, 0, STRIP_WIDTH, STRIP_HEIGHT))
    strip_path = args.out / f'{args.backend}-strip.png'
    strip.save(strip_path)
    print(f'Esquina {STRIP_WIDTH}x{STRIP_HEIGHT} -> {strip_path}')
    describe(strip)
    return 0


if __name__ == '__main__':
    sys.exit(main())
