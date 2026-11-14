"""Interfaz de línea de comandos del companion de AskForever."""

from __future__ import annotations

import argparse
import json
import threading
from datetime import datetime
from typing import Optional, Sequence

from askforever.capture.grabber import Grabber, ReceivedMessage
from askforever.capture.window import find_game_window, set_dpi_awareness


def _context_summary(ctx) -> str:
    """Resumen de una línea del contexto del mensaje."""
    if not isinstance(ctx, dict):
        return ''
    parts = []
    level = ctx.get('lvl')
    if level is not None:
        parts.append(f'nivel {level}')
    race = ctx.get('race')
    klass = ctx.get('class')
    if race and klass:
        parts.append(f'{race} {klass}')
    elif race:
        parts.append(str(race))
    elif klass:
        parts.append(str(klass))
    faction = ctx.get('fac')
    if faction:
        parts.append(str(faction))
    zone = ctx.get('zone')
    if zone:
        parts.append(str(zone))
    quests = ctx.get('quests')
    if isinstance(quests, list):
        parts.append(f'{len(quests)} misiones')
    return ' · '.join(parts)


def format_message(data: bytes) -> str:
    """Formatea el mensaje JSON de la tira o muestra el texto si no lo es."""
    try:
        parsed = json.loads(data.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return data.decode('utf-8', errors='replace')

    if not isinstance(parsed, dict):
        return data.decode('utf-8', errors='replace')

    lines = []
    question = parsed.get('q')
    if question is not None:
        lines.append(f'Pregunta: {question}')
    language = parsed.get('lang')
    if language is not None:
        lines.append(f'Idioma: {language}')
    summary = _context_summary(parsed.get('ctx'))
    if summary:
        lines.append(f'Contexto: {summary}')
    if not lines:
        return data.decode('utf-8', errors='replace')
    return '\n'.join(lines)


def _listen(args: argparse.Namespace) -> int:
    set_dpi_awareness()
    window = find_game_window()
    if window is None:
        print('Esperando a que se abra el juego…')
    else:
        print(f'Ventana del juego: {window.title} ({window.width}x{window.height})')
    print('Escuchando la tira de píxeles (Ctrl+C para salir).')

    def on_message(message: ReceivedMessage) -> None:
        stamp = datetime.now().strftime('%H:%M:%S')
        elapsed_ms = (message.completed - message.first_seen) * 1000.0
        print(
            f'[{stamp}] msg_id={message.msg_id} páginas={message.pages} '
            f'bytes={len(message.data)} recepción={elapsed_ms:.0f} ms'
        )
        if args.raw:
            print(message.data.decode('utf-8', errors='replace'))
        else:
            print(format_message(message.data))
        print()

    grabber = Grabber(on_message, fps=args.fps)
    stop_event = threading.Event()
    try:
        grabber.run(stop_event)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        print()
        print(
            f'Capturas: {grabber.captures} · marcos válidos: {grabber.valid_frames} · '
            f'mensajes: {grabber.messages} · errores: {grabber.errors}'
        )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog='askforever',
        description='Companion de AskForever para WoW Forever.',
    )
    subparsers = parser.add_subparsers(dest='command')
    listen = subparsers.add_parser('listen', help='escucha la tira de píxeles del juego')
    listen.add_argument('--fps', type=float, default=30.0,
                        help='capturas por segundo (por defecto 30)')
    listen.add_argument('--raw', action='store_true',
                        help='imprime los bytes decodificados sin formatear')

    args = parser.parse_args(argv)
    if args.command != 'listen':
        parser.print_help()
        return 2
    return _listen(args)


if __name__ == '__main__':
    raise SystemExit(main())
