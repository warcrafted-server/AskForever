"""Captura de la tira en Wayland con el portal ScreenCast (D-Bus) y PipeWire.

El portal pide al usuario qué monitor compartir (una vez; el `restore_token` guardado
evita volver a preguntar). El flujo de PipeWire lo recorta y convierte `gst-launch-1.0`
a RGB crudo de la esquina superior izquierda, que llega por una tubería.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from PIL import Image

from askforever.system_env import external_env

LOGGER = logging.getLogger('askforever.capture.portal')

STRIP_WIDTH = 512
STRIP_HEIGHT = 32
FRAME_BYTES = STRIP_WIDTH * STRIP_HEIGHT * 3
FPS = 15
RESPONSE_TIMEOUT = 120.0
RETRY_AFTER = 30.0

PORTAL_BUS = 'org.freedesktop.portal.Desktop'
PORTAL_PATH = '/org/freedesktop/portal/desktop'
SCREENCAST = 'org.freedesktop.portal.ScreenCast'
SOURCE_MONITOR = 1
CURSOR_HIDDEN = 1
PERSIST_UNTIL_REVOKED = 2


class PortalError(Exception):
    """El portal no está disponible, el usuario canceló o falló GStreamer."""


@dataclass
class PortalStream:
    fd: int
    node_id: int
    width: int
    height: int
    restore_token: Optional[str] = None
    connection: object = None  # la sesión del portal vive lo que dure la conexión


def parse_start_results(results: dict) -> tuple[int, int, int, Optional[str]]:
    """Extrae (nodo, ancho, alto, restore_token) del resultado de Start.

    Cada valor llega como (firma, valor), tal como lo devuelve jeepney.
    """
    streams = results.get('streams', (None, []))[1]
    if not streams:
        raise PortalError('El portal no devolvió ningún flujo de pantalla')
    node_id, props = streams[0]
    size = props.get('size')
    if not size:
        raise PortalError('El portal no indicó el tamaño del monitor')
    width, height = size[1]
    token = results.get('restore_token', (None, None))[1]
    return int(node_id), int(width), int(height), token


def crop_margins(width: int, height: int) -> tuple[int, int]:
    """Píxeles a recortar a la derecha y abajo para quedarse con la esquina de la tira."""
    if width < STRIP_WIDTH or height < STRIP_HEIGHT:
        raise PortalError(f'El monitor ({width}x{height}) es menor que la tira')
    return width - STRIP_WIDTH, height - STRIP_HEIGHT


def gst_command(stream: PortalStream, fps: int = FPS) -> list[str]:
    right, bottom = crop_margins(stream.width, stream.height)
    return [
        'gst-launch-1.0', '-q', 'pipewiresrc', f'fd={stream.fd}', f'path={stream.node_id}',
        '!', 'videocrop', f'right={right}', f'bottom={bottom}',
        '!', 'videorate', '!', f'video/x-raw,framerate={fps}/1',
        '!', 'videoconvert', '!', 'video/x-raw,format=RGB',
        '!', 'fdsink', 'fd=1',
    ]


def open_portal_session(token_path: Optional[Path] = None) -> PortalStream:
    """Negocia con el portal y devuelve el flujo; bloquea mientras el usuario elige."""
    from jeepney import DBusAddress, MatchRule, MessageType, new_method_call
    from jeepney.bus_messages import message_bus
    from jeepney.io.blocking import open_dbus_connection
    from jeepney.wrappers import Proxy

    try:
        connection = open_dbus_connection(bus='SESSION', enable_fds=True)
    except Exception as error:
        raise PortalError(f'No hay bus de sesión D-Bus: {error}') from error

    address = DBusAddress(PORTAL_PATH, bus_name=PORTAL_BUS, interface=SCREENCAST)
    sender = connection.unique_name.lstrip(':').replace('.', '_')
    counter = [0]
    bus_proxy = Proxy(message_bus, connection)

    def call(method, signature, body):
        reply = connection.send_and_get_reply(new_method_call(address, method, signature, body))
        if reply.header.message_type == MessageType.error:
            raise PortalError(f'{method}: {reply.header.fields} {reply.body}')
        return reply

    def request(method, build):
        """Llama a un método de petición y espera su señal Response."""
        counter[0] += 1
        token = f'askforever_{os.getpid()}_{counter[0]}'
        path = f'/org/freedesktop/portal/desktop/request/{sender}/{token}'
        rule = MatchRule(type='signal', interface='org.freedesktop.portal.Request',
                         member='Response', path=path)
        bus_proxy.AddMatch(rule)
        with connection.filter(rule) as queue:
            signature, body = build(token)
            call(method, signature, body)
            try:
                message = connection.recv_until_filtered(queue, timeout=RESPONSE_TIMEOUT)
            except TimeoutError as error:
                raise PortalError(f'{method}: sin respuesta del usuario') from error
        code, results = message.body
        if code != 0:
            raise PortalError(f'{method}: cancelado o denegado (código {code})')
        return results

    try:
        created = request('CreateSession', lambda token: ('a{sv}', ({
            'handle_token': ('s', token),
            'session_handle_token': ('s', f'askforever_s{os.getpid()}'),
        },)))
        session = created['session_handle'][1]

        select = {
            'types': ('u', SOURCE_MONITOR),
            'cursor_mode': ('u', CURSOR_HIDDEN),
            'persist_mode': ('u', PERSIST_UNTIL_REVOKED),
        }
        if token_path is not None and token_path.is_file():
            select['restore_token'] = ('s', token_path.read_text(encoding='utf-8').strip())
        request('SelectSources', lambda token: ('oa{sv}', (
            session, {'handle_token': ('s', token), **select})))

        started = request('Start', lambda token: ('osa{sv}', (
            session, '', {'handle_token': ('s', token)})))
        node_id, width, height, restore = parse_start_results(started)
        if restore and token_path is not None:
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(restore, encoding='utf-8')

        reply = call('OpenPipeWireRemote', 'oa{sv}', (session, {}))
        fd = reply.body[0].to_raw_fd()
    except PortalError:
        connection.close()
        raise
    except Exception as error:
        connection.close()
        raise PortalError(str(error)) from error

    return PortalStream(fd, node_id, width, height, restore, connection)


class PortalCapture:
    """Callable para `Grabber(capture_fn=...)`: devuelve la esquina de la tira o None."""

    def __init__(self, token_path: Optional[Path] = None,
                 open_session: Callable[..., PortalStream] = open_portal_session,
                 spawn: Callable[..., subprocess.Popen] = subprocess.Popen,
                 clock: Callable[[], float] = time.monotonic,
                 on_error: Optional[Callable[[Exception], None]] = None) -> None:
        self.token_path = token_path
        self._open_session = open_session
        self._spawn = spawn
        self._clock = clock
        self._on_error = on_error
        self._stream: Optional[PortalStream] = None
        self._process: Optional[subprocess.Popen] = None
        self._retry_at = 0.0
        self._lock = threading.Lock()

    def __call__(self) -> Optional[Image.Image]:
        if self._process is None and not self._start():
            return None
        data = self._read(FRAME_BYTES)
        if data is None:
            self.close()
            self._retry_at = self._clock() + RETRY_AFTER
            return None
        return Image.frombytes('RGB', (STRIP_WIDTH, STRIP_HEIGHT), data)

    def _start(self) -> bool:
        if self._clock() < self._retry_at:
            time.sleep(0.2)
            return False
        try:
            self._stream = self._open_session(self.token_path)
            env = external_env()
            extra = {} if env is None else {'env': env}
            self._process = self._spawn(gst_command(self._stream), stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, pass_fds=[self._stream.fd],
                                        **extra)
        except FileNotFoundError as error:
            self._fail(PortalError(f'Falta gst-launch-1.0 (gstreamer): {error}'))
            return False
        except Exception as error:
            self._fail(error)
            return False
        return True

    def _fail(self, error: Exception) -> None:
        LOGGER.warning('captura por portal: %s', error)
        self.close()
        self._retry_at = self._clock() + RETRY_AFTER
        if self._on_error is not None:
            self._on_error(error)

    def _read(self, size: int) -> Optional[bytes]:
        process = self._process
        if process is None or process.stdout is None:
            return None
        chunks = []
        missing = size
        while missing > 0:
            chunk = process.stdout.read(missing)
            if not chunk:
                return None
            chunks.append(chunk)
            missing -= len(chunk)
        return b''.join(chunks)

    def close(self) -> None:
        with self._lock:
            process, self._process = self._process, None
            stream, self._stream = self._stream, None
        if process is not None:
            try:
                process.kill()
                process.wait(timeout=2)
            except Exception:
                pass
        if stream is not None:
            for closer in (lambda: os.close(stream.fd),
                           lambda: stream.connection.close()):
                try:
                    closer()
                except Exception:
                    pass


def wants_portal(environ=os.environ, platform: str = None) -> bool:
    """True en una sesión Wayland de Linux (la captura por X11 no ve el juego)."""
    import sys

    platform = platform or sys.platform
    return platform.startswith('linux') and environ.get('XDG_SESSION_TYPE') == 'wayland'
