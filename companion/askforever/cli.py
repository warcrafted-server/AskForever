"""Interfaz de línea de comandos del companion de AskForever."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import threading
import time
from datetime import datetime
from typing import Optional, Sequence

from askforever import config
from askforever.capture.grabber import Grabber, ReceivedMessage
from askforever.capture.window import find_game_window, set_dpi_awareness
from askforever.engine.answer import answer_message
from askforever.providers.openai_compat import ProviderError, provider_from_config


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

    provider = None
    provider_failed = False

    def ensure_provider():
        nonlocal provider, provider_failed
        if provider is not None or provider_failed:
            return provider
        try:
            provider = provider_from_config()
            return provider
        except ProviderError as error:
            provider_failed = True
            print(error.user_message('esES'))
            if error.detail:
                print(f'Detalle: {error.detail}')
            print('Guía: docs/CLAVE_GEMINI.md')
            return None

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

        if not args.ask:
            return
        active = ensure_provider()
        if active is None:
            return

        def answer_in_background():
            result = answer_message(message.data, active)
            if result.ok:
                print(f'Respuesta ({result.elapsed_ms} ms):')
                print(result.text)
            else:
                print(result.text)
            print()

        threading.Thread(target=answer_in_background, daemon=True).start()

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


def _set_key() -> int:
    key = os.environ.get('AF_KEY')
    if key is None:
        key = getpass.getpass('Clave de la API de Gemini: ')
    key = (key or '').strip()
    if not key:
        print('La clave está vacía; no se ha guardado nada.')
        return 1
    try:
        config.set_api_key(key)
    except ValueError:
        print('La clave está vacía; no se ha guardado nada.')
        return 1
    except Exception:
        print('No se pudo guardar la clave en el Administrador de credenciales de Windows.')
        return 1
    print(f'Clave guardada: {config.mask_key(key)}')
    return 0


def _test_key() -> int:
    try:
        provider = provider_from_config()
    except ProviderError as error:
        print(error.user_message('esES'))
        if error.detail:
            print(f'Detalle: {error.detail}')
        print('Guía: docs/CLAVE_GEMINI.md')
        return 1

    started = time.monotonic()
    try:
        answer = provider.chat('Responde solo con la palabra OK.', 'ping', max_tokens=256)
    except ProviderError as error:
        print(error.user_message('esES'))
        if error.detail:
            print(f'Detalle: {error.detail}')
        return 1
    elapsed_ms = (time.monotonic() - started) * 1000.0
    print(f'Modelo: {provider.model}')
    print(f'Tiempo: {elapsed_ms:.0f} ms')
    print(f'Respuesta: {answer[:60]}')
    return 0


def _ask(args: argparse.Namespace) -> int:
    context = {}
    if args.level is not None:
        context['lvl'] = args.level
    if args.race:
        context['race'] = args.race
    if args.klass:
        context['class'] = args.klass
    if args.faction:
        context['fac'] = args.faction
    if args.zone:
        context['zone'] = args.zone

    message = {
        'v': 1,
        'lang': args.lang,
        'q': ' '.join(args.question).strip(),
        'ctx': context,
    }
    data = json.dumps(message, ensure_ascii=False).encode('utf-8')

    try:
        provider = provider_from_config()
    except ProviderError as error:
        print(error.user_message(args.lang))
        return 1

    result = answer_message(data, provider)
    if result.ok:
        print(f'Tiempo: {result.elapsed_ms} ms')
        print(result.text)
        return 0
    print(result.text)
    return 1


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
    listen.add_argument('--ask', action='store_true',
                        help='pregunta a la IA por cada mensaje recibido')
    subparsers.add_parser('set-key', help='guarda la clave de la API de Gemini')
    subparsers.add_parser('test-key', help='prueba la clave y el proveedor de IA')
    ask = subparsers.add_parser('ask', help='pregunta a la IA desde la consola')
    ask.add_argument('question', nargs='+', help='pregunta, entre comillas')
    ask.add_argument('--lang', default='esES', help='idioma de la respuesta (por defecto esES)')
    ask.add_argument('--level', type=int, help='nivel del personaje')
    ask.add_argument('--zone', help='zona del personaje')
    ask.add_argument('--race', help='raza del personaje')
    ask.add_argument('--class', dest='klass', help='clase del personaje')
    ask.add_argument('--faction', help='facción del personaje')

    args = parser.parse_args(argv)
    if args.command == 'listen':
        return _listen(args)
    if args.command == 'set-key':
        return _set_key()
    if args.command == 'test-key':
        return _test_key()
    if args.command == 'ask':
        return _ask(args)
    parser.print_help()
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
