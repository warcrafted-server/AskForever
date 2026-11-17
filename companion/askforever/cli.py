"""Interfaz de línea de comandos del companion de AskForever."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from askforever import config, setup_wizard, updates
from askforever import uninstall as uninstall_module
from askforever.bench import (
    Target,
    load_questions,
    parse_target,
    render_markdown,
    run_bench,
    save_report,
    summarize,
)
from askforever.capture.grabber import Grabber, ReceivedMessage
from askforever.capture.window import find_game_window, set_dpi_awareness
from askforever.data.wowdb import WowDb
from askforever.devreport import close_report, parse_report, write_report
from askforever.engine.answer import answer_message, parse_message
from askforever.engine.conversation import ConversationStore
from askforever.overlay.chat import ChatSession
from askforever.overlay.supervisor import OverlaySupervisor
from askforever.overlay.window import Overlay, OverlayUnavailable
from askforever.providers.openai_compat import ProviderError, list_models, provider_from_config
from askforever.web.wiki import WIKI_PAGE_URL


def user_data_dir() -> Path:
    """Carpeta de datos gestionados del companion."""
    return config.user_data_dir()


def check_and_update(*args, **kwargs):
    """Comprueba e instala datos; delega para poder sustituirlo en pruebas."""
    return updates.check_and_update(*args, **kwargs)


def run_wizard(*args, **kwargs):
    """Lanza el asistente de configuración de la clave."""
    return setup_wizard.run_wizard(*args, **kwargs)


def uninstall(*args, **kwargs):
    """Desinstala AskForever y sus datos."""
    return uninstall_module.uninstall(*args, **kwargs)


def _stdin_is_interactive() -> bool:
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (AttributeError, OSError, ValueError):
        return False


def _ensure_api_key() -> bool:
    """Comprueba la clave; si falta, lanza el asistente o explica cómo ponerla."""
    try:
        key = config.get_api_key()
    except Exception:
        key = None
    if key:
        return True
    if _stdin_is_interactive():
        try:
            return bool(run_wizard())
        except Exception as error:
            print(f'No se pudo completar la configuración: {error}')
            return False
    print('No hay clave de la API configurada.')
    print('Configúrala con: askforever.exe set-key')
    print(f'Guía: {setup_wizard.GUIDE_URL}')
    return False


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


def _open_data(no_data):
    if no_data:
        print('Base de datos: no disponible (sin datos verificados)')
        return None
    database = config.open_wowdata()
    if database is None:
        print('Base de datos: no disponible (sin datos verificados)')
    else:
        print(f'Base de datos: {database.path}')
    return database


def _open_web(no_web):
    """Abre el cliente de la wiki o informa de que está desactivada."""
    if no_web:
        print('Búsqueda web: desactivada')
        return None
    web = config.open_wiki()
    if web is None:
        print('Búsqueda web: desactivada')
    else:
        print('Búsqueda web: warcraft.wiki.gg')
    return web


def _update_game_data():
    """Comprueba e instala los datos gestionados, con progreso y resultado."""
    print('Comprobando datos del juego...')
    last = {'bucket': -10}

    def progress(downloaded, total):
        if not total:
            return
        percent = min(100, int(downloaded * 100 / total))
        bucket = percent - percent % 10
        if bucket != last['bucket']:
            last['bucket'] = bucket
            print(f'Descargando datos: {bucket} %')

    status, value = check_and_update(user_data_dir(), progress=progress)
    if status == 'updated':
        print(f'Datos actualizados a {value}')
    elif status == 'current':
        print(f'Datos del juego: {value}')
    elif status == 'offline':
        if value:
            print(f'Sin conexion: se usan los datos guardados ({value})')
        else:
            print('Sin datos del juego: las respuestas tendran menos informacion')
    else:
        detail = str(value).encode('ascii', 'replace').decode('ascii')
        print(f'No se pudieron actualizar los datos: {detail}')
    return status, value


def _update_data() -> int:
    status, value = _update_game_data()
    if status in ('updated', 'current'):
        return 0
    if status == 'offline' and value:
        return 0
    return 1


def _handle_report(document, last_exchange, lock, overlay=None) -> None:
    """Gestiona un informe de desarrollo sin pasar por la IA ni la memoria."""
    lang = document.get('lang') or 'enUS'
    if document.get('kind') == 'report-close':
        rid = document.get('rid')
        result = close_report(rid)
        if result == 'closed':
            message = f'Informe cerrado: {rid}'
            print(message)
            if overlay is not None:
                overlay.show_answer('Informe', message, lang)
        elif result == 'missing':
            message = f'El informe {rid} ya no existía'
            print(message)
            if overlay is not None:
                overlay.show_answer('Informe', message, lang)
        else:
            message = 'Identificador de informe no válido'
            print(message)
            if overlay is not None:
                overlay.show_error(message, lang)
        return

    note = str(document.get('q') or '')
    report_ctx = document.get('ctx')
    with lock:
        exchange = dict(last_exchange) if last_exchange else None
    try:
        path = write_report(exchange, note=note, report_ctx=report_ctx,
                            rid=document.get('rid'))
    except Exception as error:
        message = f'No se pudo guardar el informe: {error}'
        print(message)
        if overlay is not None:
            overlay.show_error(message, lang)
        return
    print(f'Informe guardado: {path}')
    if overlay is not None:
        overlay.show_answer('Informe', f'Guardado: {path.name}', lang)


def _listen(args: argparse.Namespace) -> int:
    set_dpi_awareness()
    window = find_game_window()
    if window is None:
        print('Esperando a que se abra el juego…')
    else:
        print(f'Ventana del juego: {window.title} ({window.width}x{window.height})')
    print('Escuchando la tira de píxeles (Ctrl+C para salir).')

    if (args.ask and not args.no_data
            and not getattr(args, 'no_update', False)
            and config.data_is_managed()):
        _update_game_data()
    database = _open_data(args.no_data) if args.ask else None
    web = _open_web(args.no_web) if args.ask else None
    store = ConversationStore()
    last_exchange = {}
    exchange_lock = threading.Lock()
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
        report = parse_report(message.data)
        if report is not None:
            _handle_report(report, last_exchange, exchange_lock)
            return

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

        document = parse_message(message.data)
        conversation_key = store.key(document)
        history = store.history(conversation_key)
        previous_question = history[-1].question if history else None
        question = str(document.get('q') or '') if document is not None else ''
        lang = (document.get('lang') if document is not None else None) or 'enUS'

        def answer_in_background():
            result = answer_message(message.data, active, db=database, history=history,
                                    previous_question=previous_question, web=web)
            exchange = {
                'msg_id': message.msg_id,
                'question': result.question or question,
                'lang': result.lang or lang,
                'conv': document.get('conv') if document is not None else None,
                'ctx': document.get('ctx') if document is not None else None,
                'moment': datetime.now(),
                'model': getattr(active, 'model', ''),
                'ok': result.ok,
                'text': result.text,
                'detail': result.detail,
                'elapsed_ms': result.elapsed_ms,
                'facts': list(result.facts),
                'sources': list(result.sources),
                'facts_text': result.facts_text,
                'web_titles': list(result.web_titles),
                'router': result.router,
            }
            with exchange_lock:
                last_exchange.clear()
                last_exchange.update(exchange)
            if result.ok:
                store.add(conversation_key, question, result.text, result.facts_text)
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
        if database is not None:
            database.close()
        print()
        print(
            f'Capturas: {grabber.captures} · marcos válidos: {grabber.valid_frames} · '
            f'mensajes: {grabber.messages} · errores: {grabber.errors}'
        )
    return 0


def _set_key(args: argparse.Namespace) -> int:
    try:
        provider_name = config.get_provider_name(args.provider)
    except ValueError as error:
        print(error)
        return 1
    key = os.environ.get('AF_KEY')
    if key is None:
        key = getpass.getpass(f'Clave de la API de {provider_name}: ')
    key = (key or '').strip()
    if not key:
        print('La clave está vacía; no se ha guardado nada.')
        return 1
    try:
        config.set_api_key(key, provider_name)
    except ValueError:
        print('La clave está vacía; no se ha guardado nada.')
        return 1
    except Exception:
        print('No se pudo guardar la clave en el Administrador de credenciales de Windows.')
        return 1
    print(f'Proveedor: {provider_name}')
    print(f'Clave guardada: {config.mask_key(key)}')
    return 0


def _test_key(args: argparse.Namespace) -> int:
    try:
        provider_name = config.get_provider_name(args.provider)
    except ValueError as error:
        print(error)
        return 1
    try:
        if args.provider is None and args.model is None:
            provider = provider_from_config()
        else:
            provider = provider_from_config(args.provider, args.model)
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
    print(f'Proveedor: {provider_name}')
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

    database = _open_data(args.no_data)
    web = _open_web(args.no_web)
    try:
        try:
            if args.provider is None and args.model is None:
                provider = provider_from_config()
            else:
                provider = provider_from_config(args.provider, args.model)
        except ValueError as error:
            print(error)
            return 1
        except ProviderError as error:
            print(error.user_message(args.lang))
            return 1

        result = answer_message(data, provider, db=database, temperature=args.temperature,
                                web=web)
    finally:
        if database is not None:
            database.close()

    if result.ok:
        print(f'Tiempo: {result.elapsed_ms} ms')
        print(result.text)
        if args.show_data:
            print('Datos usados:')
            if result.facts:
                for line in result.facts:
                    print(f'- {line}')
            else:
                print('- ninguno')
            if result.web_titles:
                print('Fuente web:')
                for title in result.web_titles:
                    url = WIKI_PAGE_URL + urllib.parse.quote(title.replace(' ', '_'), safe='')
                    print(f'- {title}: {url}')
        return 0
    print(result.text)
    return 1


def _overlay_demo() -> int:
    overlay = Overlay()
    stop_event = threading.Event()
    question = '¿Dónde está Hogger?'
    answer = (
        'Hogger aparece en el Bosque de Elwynn, cerca del campamento de los ríos.\n'
        'Suele merodear al sureste de Villadorada.\n'
        'Si no lo ves, espera un poco: reaparece tras unos minutos.'
    )

    def script():
        time.sleep(2.0)
        overlay.show_answer(question, answer, 'esES')
        time.sleep(6.0)
        stop_event.set()

    overlay.show_thinking(question, 'esES')
    threading.Thread(target=script, daemon=True).start()
    try:
        overlay.run(stop_event)
    except KeyboardInterrupt:
        stop_event.set()
    except OverlayUnavailable as error:
        print(error)
        return 1
    finally:
        overlay.close()
    return 0


def _raw_document(data):
    """Lee un mensaje aunque no tenga pregunta, para distinguir los eventos de UI."""
    try:
        document = json.loads(data.decode('utf-8'))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict) or document.get('v') != 1:
        return None
    return document


def _message_rect(document):
    if not isinstance(document, dict):
        return None
    values = [document.get(key) for key in ('wx', 'wy', 'ww', 'wh')]
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        return None
    return tuple(values)


def _run_companion(args: argparse.Namespace) -> int:
    set_dpi_awareness()
    overlay_class = (Overlay if getattr(args, 'overlay_inprocess', False)
                     else OverlaySupervisor)
    overlay = overlay_class(ttl=args.ttl)
    if (not args.no_data
            and not getattr(args, 'no_update', False)
            and config.data_is_managed()):
        _update_game_data()
    database = _open_data(args.no_data)
    web = _open_web(args.no_web)

    provider = None
    provider_error = None
    if not args.no_ai:
        try:
            provider = provider_from_config()
        except ProviderError as error:
            provider_error = error
            print(error.user_message('esES'))
            if error.detail:
                print(f'Detalle: {error.detail}')
            print('Guía: docs/CLAVE_GEMINI.md')

    stop_event = threading.Event()
    generation = {'value': 0}
    store = ConversationStore()
    last_exchange = {}
    exchange_lock = threading.Lock()
    chat_session = ChatSession()
    chat_lock = threading.Lock()

    def on_message(message: ReceivedMessage) -> None:
        report = parse_report(message.data)
        if report is not None:
            _handle_report(report, last_exchange, exchange_lock, overlay)
            return

        stamp = datetime.now().strftime('%H:%M:%S')
        raw = _raw_document(message.data)
        if raw is not None and raw.get('kind') == 'ui':
            event = str(raw.get('ev') or '')
            conv = raw.get('conv')
            rect = _message_rect(raw)
            sd = raw.get('sd')
            if isinstance(sd, bool) or not isinstance(sd, int):
                sd = 0
            with chat_lock:
                if event == 'scroll':
                    view = chat_session.ui(event, conv, rect, scroll=sd)
                else:
                    view = chat_session.ui(event, conv, rect)
            if view is not None:
                overlay.show_chat(view)
            print(f'[{stamp}] ui {event} conv={conv}')
            return

        document = parse_message(message.data)
        if document is None:
            print(f'[{stamp}] mensaje sin pregunta; ignorado')
            return

        question = str(document.get('q') or '')
        lang = document.get('lang') or 'enUS'
        conv = document.get('conv')
        rect = _message_rect(document)
        conversation_key = store.key(document)
        history = store.history(conversation_key)
        previous_question = history[-1].question if history else None

        generation['value'] += 1
        current = generation['value']

        print(f'[{stamp}] msg_id={message.msg_id} {question}')

        with chat_lock:
            view = chat_session.question(conv, question, rect, lang)
        if view is not None:
            overlay.show_chat(view)
        else:
            overlay.show_thinking(question, lang)
        if args.no_ai:
            return
        if provider is None:
            text = provider_error.user_message(lang) if provider_error else 'No AI provider.'
            if view is not None:
                with chat_lock:
                    error_view = chat_session.error(conv, text)
                if error_view is not None:
                    overlay.show_chat(error_view)
                else:
                    overlay.show_error(text, lang)
            else:
                overlay.show_error(text, lang)
            return

        def answer():
            result = answer_message(message.data, provider, db=database, history=history,
                                    previous_question=previous_question, web=web)
            if current != generation['value']:
                return
            exchange = {
                'msg_id': message.msg_id,
                'question': result.question or question,
                'lang': result.lang or lang,
                'conv': conv,
                'ctx': document.get('ctx'),
                'moment': datetime.now(),
                'model': getattr(provider, 'model', ''),
                'ok': result.ok,
                'text': result.text,
                'detail': result.detail,
                'elapsed_ms': result.elapsed_ms,
                'facts': list(result.facts),
                'sources': list(result.sources),
                'facts_text': result.facts_text,
                'web_titles': list(result.web_titles),
                'router': result.router,
            }
            with exchange_lock:
                last_exchange.clear()
                last_exchange.update(exchange)
            if result.ok:
                store.add(conversation_key, question, result.text, result.facts_text)
                with chat_lock:
                    chat_view = chat_session.answer(conv, result.text)
                if chat_view is not None:
                    overlay.show_chat(chat_view)
                else:
                    overlay.show_answer(question, result.text, lang)
                print(f'Respuesta ({result.elapsed_ms} ms): {result.text}')
            else:
                with chat_lock:
                    chat_view = chat_session.error(conv, result.text)
                if chat_view is not None:
                    overlay.show_chat(chat_view)
                else:
                    overlay.show_error(result.text, lang)
                print(f'Error: {result.text}')

        threading.Thread(target=answer, daemon=True).start()

    print('Deja esta ventana abierta mientras juegas. Ciérrala para detener AskForever.')
    grabber = Grabber(on_message, fps=args.fps)
    grabber_thread = threading.Thread(target=grabber.run, args=(stop_event,), daemon=True)
    grabber_thread.start()

    try:
        overlay.run(stop_event)
    except KeyboardInterrupt:
        stop_event.set()
    except OverlayUnavailable as error:
        print(error)
        stop_event.set()
        return 1
    finally:
        stop_event.set()
        overlay.close()
        grabber_thread.join(timeout=1.0)
        if database is not None:
            database.close()

    print()
    print(
        f'Capturas: {grabber.captures} · marcos válidos: {grabber.valid_frames} · '
        f'mensajes: {grabber.messages} · errores: {grabber.errors}'
    )
    return 0


def _providers() -> int:
    for name in sorted(config.PROVIDERS):
        preset = config.PROVIDERS[name]
        try:
            has_key = bool(config.get_api_key(name))
        except Exception:
            has_key = False
        mark = '[x]' if has_key else '[ ]'
        model = preset.default_model or '(elige con --model)'
        print(f'{mark} {name}: {model} · clave en {preset.key_url}')
    return 0


def _list_models(args: argparse.Namespace) -> int:
    if args.provider is None and not os.environ.get(config.PROVIDER_ENV):
        print('Indica el proveedor: list-models --provider NOMBRE')
        return 1
    try:
        provider_name = config.get_provider_name(args.provider)
    except ValueError as error:
        print(error)
        return 1

    preset = config.get_preset(provider_name)
    api_key = config.get_api_key(provider_name)
    if not api_key:
        print(f'No hay clave guardada para {provider_name}.')
        print(f'Guárdala con: set-key --provider {provider_name}')
        print(f'Consigue una clave en: {preset.key_url}')
        return 1

    try:
        models = list_models(preset.base_url, api_key)
    except ProviderError as error:
        print(error.user_message('esES'))
        if error.detail:
            print(f'Detalle: {error.detail}')
        return 1

    for identifier in models:
        print(identifier)
    print(f'Total: {len(models)} modelos.')
    return 0


def _bench_targets(raw):
    if raw:
        targets = []
        for item in raw.split(','):
            item = item.strip()
            if item:
                targets.append(parse_target(item))
        if not targets:
            raise ValueError('--targets no contiene ningún objetivo válido.')
        return targets

    targets = []
    for name, preset in config.PROVIDERS.items():
        if not config.get_api_key(name):
            continue
        if not preset.default_model:
            print(f'Aviso: {name} no tiene modelo por defecto; indícalo con '
                  f'--targets {name}:MODELO (ver list-models --provider {name}).')
            continue
        targets.append(Target(name))
    return targets


def _ms_text(value) -> str:
    return '-' if value is None else f'{value:.1f}'


def _print_bench_summary(summary) -> None:
    print('')
    print('Objetivo | Respondidas | Errores | Saltadas | Media ms | Mediana ms | Max ms')
    for row in summary:
        print(f"{row['target']} | {row['answered']} | {row['errors']} | {row['skipped']} | "
              f"{_ms_text(row['mean_ms'])} | {_ms_text(row['median_ms'])} | "
              f"{_ms_text(row['max_ms'])}")


def _bench(args: argparse.Namespace) -> int:
    started = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    database = _open_data(args.no_data)
    web = _open_web(args.no_web)
    temperature = args.temperature if args.temperature is not None else config.get_temperature()
    previous_router = os.environ.get(config.GUIDE_ROUTER_ENV)
    if getattr(args, 'no_router', False):
        os.environ[config.GUIDE_ROUTER_ENV] = '0'
    try:
        try:
            targets = _bench_targets(args.targets)
        except ValueError as error:
            print(error)
            return 2
        if not targets:
            print('No hay objetivos con clave. Guarda una clave con: set-key --provider NOMBRE')
            print('Consulta los proveedores y sus claves con: providers')
            return 2

        try:
            questions = load_questions(args.questions)
        except ValueError as error:
            print(error)
            return 2

        if args.only:
            wanted = {item.strip() for item in args.only.split(',') if item.strip()}
            questions = [question for question in questions if question.id in wanted]
            if not questions:
                print('Ninguna pregunta coincide con --only.')
                return 2

        def on_progress(index, total, target, question, result):
            if result.skipped:
                state = f'SALTADA: {result.error_detail or result.error_kind}'
            elif result.ok:
                state = f'OK {result.latency_ms} ms'
            else:
                state = f'ERROR {result.error_kind}'
            print(f'[{index}/{total}] {target} {question.id} {state}')

        results = run_bench(
            questions,
            targets,
            provider_factory=provider_from_config,
            repeat=args.repeat,
            pause=args.pause,
            max_tokens=args.max_tokens,
            db=database,
            web=web,
            temperature=temperature,
            on_progress=on_progress,
        )

        summary = summarize(results)
        _print_bench_summary(summary)
        markdown = render_markdown(questions, targets, results, started,
                                   used_database=database is not None,
                                   temperature=temperature)
        try:
            md_path, json_path = save_report(markdown, results,
                                             used_database=database is not None,
                                             temperature=temperature)
        except OSError as error:
            print(f'No se pudo guardar el informe: {error}')
            return 1
        print(f'Informe: {md_path}')
        print(f'Datos: {json_path}')
        return 0 if any(result.ok for result in results) else 1
    finally:
        if getattr(args, 'no_router', False):
            if previous_router is None:
                os.environ.pop(config.GUIDE_ROUTER_ENV, None)
            else:
                os.environ[config.GUIDE_ROUTER_ENV] = previous_router
        if database is not None:
            database.close()


def _default_wowdb_path() -> Path:
    return Path(__file__).resolve().parents[2].parent / 'wowdata' / 'datos' / 'wow.sqlite'


def _format_locations(locations) -> str:
    parts = []
    for location in locations:
        zone = location.get('zone') or 'zona desconocida'
        parts.append(f"{zone} ({location.get('x')}, {location.get('y')})")
    return '; '.join(parts) or 'sin posicion conocida'


def _print_quest(label: str, quest) -> None:
    if quest is None:
        print(f'{label}: no encontrada')
        return
    print(f"{label}: [{quest['id']}] {quest['name']} "
          f"(nivel {quest['level']}, requiere {quest['required_level']})")
    for starter in quest.get('starters', []):
        print(f"  Inicio: {starter['type']} {starter['id']} {starter['name']} - "
              f"{_format_locations(starter['locations'])}")
    for finisher in quest.get('finishers', []):
        print(f"  Fin: {finisher['type']} {finisher['id']} {finisher['name']} - "
              f"{_format_locations(finisher['locations'])}")
    if quest.get('objective_items'):
        print(f"  Objetivos: {', '.join(quest['objective_items'])}")


def _print_npc(label: str, npc) -> None:
    if npc is None:
        print(f'{label}: no encontrado')
        return
    print(f"{label}: [{npc['id']}] {npc['name']} - {npc['sub_name'] or 'sin subtitulo'} "
          f"(niveles {npc['min_level']}-{npc['max_level']}, faccion {npc['friendly_to']})")
    for location in npc['locations']:
        print(f"  {_format_locations([location])}")


def _print_dungeon(label: str, dungeon) -> None:
    if dungeon is None:
        print(f'{label}: no encontrada')
        return
    print(f"{label}: [{dungeon['id']}] {dungeon['name']} (zona {dungeon['zone']})")
    for entrance in dungeon['entrances']:
        print(f"  Entrada: {entrance['zone']} ({entrance['x']}, {entrance['y']})")


def _data_check(args: argparse.Namespace) -> int:
    if args.db:
        path = args.db
    else:
        resolved = config.get_wowdata_path()
        path = str(resolved) if resolved else str(_default_wowdb_path())
    db = WowDb(path)
    if not db.available():
        print(f'No se encontro la base de datos de WoW Forever: {path}')
        print('Usa --db RUTA o define ASKFOREVER_WOWDATA.')
        db.close()
        return 1

    try:
        print(f'Base: {path}')
        started = time.monotonic()
        db.ensure_index()
        index_ms = int((time.monotonic() - started) * 1000)
        print(f'Indice de nombres: {index_ms} ms')
        print()

        for name in ('La amenaza trogg', 'La excavación de Vetaferro',
                     'Un pedido de Pico Tormenta', 'Incursión en la Antigua Forjaz'):
            _print_quest(f"Mision '{name}'", db.find_quest(name))
        print()

        _print_npc("NPC 'Rey Magni Barbabronce'", db.find_npc('Rey Magni Barbabronce'))
        print()

        print('Hechizos de chaman nivel 18:')
        for spell in db.class_spells(64, 18, 18):
            print(f"  {spell['level']}: {spell['name']}")
        print('Hechizos de chaman nivel 20:')
        for spell in db.class_spells(64, 20, 20):
            print(f"  {spell['level']}: {spell['name']}")
        print()

        trainers = db.class_trainers(64, 'A')
        print(f'Instructores de chamanes (Alianza): {len(trainers)}')
        spanish_in_forjaz = 0
        for trainer in trainers:
            zones = [location['zone'] for location in trainer['locations']]
            if 'Forjaz' in zones and trainer['sub_name'] in (
                    'Instructor de chamanes', 'Instructora de chamanes'):
                spanish_in_forjaz += 1
            print(f"  {trainer['id']}: {trainer['name']} - "
                  f"{trainer['sub_name'] or 'sin subtitulo'} "
                  f"({_format_locations(trainer['locations'])})")
        if trainers and spanish_in_forjaz == 0:
            print("  Hueco conocido: ninguno con sub_name 'Instructor de chamanes' "
                  "en Forjaz.")
        print()

        _print_dungeon("Mazmorra 'Las Minas de la Muerte'", db.dungeon('Las Minas de la Muerte'))
        _print_dungeon("Mazmorra 'Gnomeregan'", db.dungeon('Gnomeregan'))
        print()

        points = db.flight_points(0, 'A')
        print(f'Puntos de vuelo de la Alianza en Reinos del Este: {len(points)}')
        for point in points[:30]:
            print(f"  {point['id']}: {point['name']}")
        print()

        print(f"Ramas de talentos de chaman: {', '.join(db.talent_trees(64))}")
        print()

        item_id = None
        try:
            row = db.open().execute(
                'SELECT item_id FROM ext_item_vendors GROUP BY item_id ORDER BY item_id LIMIT 1'
            ).fetchone()
            item_id = row[0] if row else None
        except Exception:
            item_id = None
        if item_id is not None:
            item = db.item_sources(item_id)
            if item:
                print(f"Objeto con vendedores: [{item['id']}] {item['name']}")
                for vendor in item['vendors']:
                    print(f"  Vendedor: {vendor['npc']} - {vendor['sub_name']} "
                          f"({_format_locations(vendor['locations'])})")
                for drop in item['drops']:
                    print(f"  Botin: {drop['npc']} en {drop['zone']} ({drop['rate']} %)")
                if item['quest_rewards']:
                    print(f"  Recompensa de: {', '.join(item['quest_rewards'])}")
        else:
            print('Objeto con vendedores: no encontrado')
        print()

        phrases = [
            ('¿Dónde entrego Un pedido de Pico Tormenta?', 'es'),
            ('¿Dónde está la entrada de Las Minas de la Muerte?', 'es'),
            ('Where is the entrance to the Deadmines?', 'en'),
        ]
        for phrase, lang in phrases:
            started = time.monotonic()
            matches = db.match_entities(phrase, lang=lang)
            elapsed = int((time.monotonic() - started) * 1000)
            print(f'match_entities({phrase}, {lang}): {len(matches)} resultados '
                  f'en {elapsed} ms')
            for match in matches:
                print(f"  {match['kind']} {match['id']}: {match['name']}")

        print()
        zone = db.zone_levels('Montañas Crestagrana')
        if zone:
            print(f"Niveles de zona: Montañas Crestagrana {zone['min']}-{zone['max']}")
        else:
            print('Niveles de zona: Montañas Crestagrana sin datos')
        zones = db.zones_for_level(16)
        print('Zonas para nivel 16: ' + '; '.join(
            f"{item['name']} ({item['min']}-{item['max']})" for item in zones))
        dungeon = db.dungeon_level('Las Minas de la Muerte')
        if dungeon:
            print(f"Mazmorra: {dungeon['name']} {dungeon['min']}-{dungeon['max']}")
        else:
            print('Mazmorra Las Minas de la Muerte: sin datos de nivel')
        dungeons = db.dungeons_for_level(16)
        print('Mazmorras para nivel 16: ' + '; '.join(
            f"{item['name']} ({item['min']}-{item['max']})" for item in dungeons))
        for name in ('Cuevas de los Lamentos', 'Las Minas de la Muerte'):
            bosses = db.dungeon_bosses(name)
            if bosses:
                print(f"Jefes de {bosses['name']}: " + ', '.join(bosses['bosses']))
            else:
                print(f'Jefes de {name}: sin datos')
        print(f'Experiencia para pasar de nivel 16: {db.xp_to_next_level(16)}')
        details = db.quest_details(255)
        if details:
            print(f"Misión 255: xp {details['xp']}, zona {details['zone']}, "
                  f"objetivos {details['objectives']}")
        else:
            print('Misión 255: sin datos')
        item = db.item_sources('Diente de piedra trogg')
        if item:
            drops = '; '.join(f"{drop['npc']} en {drop['zone']} ({drop['rate']} %)"
                              for drop in item['drops'])
            print(f"Botín de Diente de piedra trogg: {drops or 'sin datos'}")
        else:
            print('Botín de Diente de piedra trogg: sin datos')
        flights = db.flights_from('Forjaz', 'A')
        if flights:
            print(f"Vuelos desde {flights['origin']}: " + '; '.join(
                f"{flight['destination']} {flight['cost']}"
                for flight in flights['flights'][:12]))
        else:
            print('Vuelos desde Forjaz: sin datos')
        cost = db.flight_cost('Forjaz', 'Thelsamar', 'A')
        if cost:
            print(f"Vuelo {cost['origin']} -> {cost['destination']}: "
                  f"{cost['cost_copper']} cobre ({cost['cost']})")
        else:
            print('Vuelo Forjaz -> Thelsamar: sin datos')
        transports = db.transports('A')
        print(f'Transportes (Alianza): {len(transports)}')
        for transport in transports[:10]:
            print(f"  {transport['type']}: {transport['origin']} -> "
                  f"{transport['destination']}")
    finally:
        db.close()
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
    listen.add_argument('--ask', action='store_true',
                        help='pregunta a la IA por cada mensaje recibido')
    listen.add_argument('--no-data', action='store_true',
                        help='no usa la base de datos de WoW')
    listen.add_argument('--no-update', action='store_true',
                        help='no comprueba si hay datos más nuevos')
    listen.add_argument('--no-web', action='store_true',
                        help='no busca en la wiki de warcraft.wiki.gg')
    set_key = subparsers.add_parser('set-key', help='guarda la clave de la API de un proveedor')
    set_key.add_argument('--provider', default=None, help='proveedor del registro')
    subparsers.add_parser('setup', help='configura o cambia la clave de la API')
    test_key = subparsers.add_parser('test-key', help='prueba la clave y el proveedor de IA')
    test_key.add_argument('--provider', default=None, help='proveedor del registro')
    test_key.add_argument('--model', default=None, help='modelo a usar')
    ask = subparsers.add_parser('ask', help='pregunta a la IA desde la consola')
    ask.add_argument('question', nargs='+', help='pregunta, entre comillas')
    ask.add_argument('--lang', default='esES', help='idioma de la respuesta (por defecto esES)')
    ask.add_argument('--level', type=int, help='nivel del personaje')
    ask.add_argument('--zone', help='zona del personaje')
    ask.add_argument('--race', help='raza del personaje')
    ask.add_argument('--class', dest='klass', help='clase del personaje')
    ask.add_argument('--faction', help='facción del personaje')
    ask.add_argument('--provider', default=None, help='proveedor del registro')
    ask.add_argument('--model', default=None, help='modelo a usar')
    ask.add_argument('--temperature', type=float, default=None,
                     help='temperatura de la respuesta (0..2)')
    ask.add_argument('--no-data', action='store_true',
                     help='no usa la base de datos de WoW')
    ask.add_argument('--no-web', action='store_true',
                     help='no busca en la wiki de warcraft.wiki.gg')
    ask.add_argument('--show-data', action='store_true',
                     help='muestra los datos verificados usados')
    list_models_parser = subparsers.add_parser('list-models',
                                               help='lista los modelos del proveedor')
    list_models_parser.add_argument('--provider', default=None, help='proveedor del registro')
    subparsers.add_parser('providers', help='lista los proveedores y si tienen clave')
    bench = subparsers.add_parser('bench', help='compara proveedores y modelos con preguntas fijas')
    bench.add_argument('--targets', default=None,
                       help='proveedor:modelo separados por comas')
    bench.add_argument('--questions', default=None, help='ruta del cuestionario JSON')
    bench.add_argument('--only', default=None, help='ids de pregunta separados por comas')
    bench.add_argument('--repeat', type=int, default=1, help='repeticiones por pregunta')
    bench.add_argument('--pause', type=float, default=1.5, help='segundos entre llamadas')
    bench.add_argument('--max-tokens', type=int, default=None,
                       help='límite de tokens por respuesta')
    bench.add_argument('--temperature', type=float, default=None,
                       help='temperatura de las respuestas (0..2)')
    bench.add_argument('--no-data', action='store_true',
                       help='no usa la base de datos de WoW')
    bench.add_argument('--no-web', action='store_true',
                       help='no busca en la wiki de warcraft.wiki.gg')
    bench.add_argument('--no-router', action='store_true',
                       help='no usa el enrutador de secciones de la guía')
    data_check = subparsers.add_parser('data-check',
                                       help='comprueba la base de datos de WoW Forever')
    data_check.add_argument('--db', default=None, help='ruta de wow.sqlite')
    subparsers.add_parser('update-data',
                          help='descarga la última base de datos del juego')
    uninstall_parser = subparsers.add_parser(
        'uninstall', help='desinstala AskForever y borra sus datos')
    uninstall_parser.add_argument('--yes', action='store_true',
                                  help='no pide confirmación')
    uninstall_parser.add_argument('--addon', action='store_true',
                                  help='borra también el addon AskForever')
    companion = subparsers.add_parser('run', help='escucha el juego y responde en el overlay')
    companion.add_argument('--fps', type=float, default=30.0,
                           help='capturas por segundo (por defecto 30)')
    companion.add_argument('--ttl', type=float, default=30.0,
                           help='segundos que se muestra cada respuesta (por defecto 30)')
    companion.add_argument('--no-ai', action='store_true',
                           help='no llama a la IA; solo muestra la pregunta recibida')
    companion.add_argument('--no-data', action='store_true',
                           help='no usa la base de datos de WoW')
    companion.add_argument('--no-update', action='store_true',
                           help='no comprueba si hay datos más nuevos')
    companion.add_argument('--no-web', action='store_true',
                           help='no busca en la wiki de warcraft.wiki.gg')
    companion.add_argument('--overlay-inprocess', action='store_true',
                           help='usa el overlay en el proceso principal (diagnóstico)')
    subparsers.add_parser('overlay-demo',
                          help='muestra el overlay de ejemplo durante 8 segundos')

    args = parser.parse_args(argv)
    if args.command is None:
        run_args = parser.parse_args(['run'])
        if not _ensure_api_key():
            return 1
        return _run_companion(run_args)
    if args.command == 'listen':
        return _listen(args)
    if args.command == 'set-key':
        return _set_key(args)
    if args.command == 'setup':
        return 0 if run_wizard() else 1
    if args.command == 'uninstall':
        return uninstall(yes=args.yes, remove_addon=args.addon)
    if args.command == 'test-key':
        return _test_key(args)
    if args.command == 'ask':
        return _ask(args)
    if args.command == 'list-models':
        return _list_models(args)
    if args.command == 'providers':
        return _providers()
    if args.command == 'bench':
        return _bench(args)
    if args.command == 'data-check':
        return _data_check(args)
    if args.command == 'update-data':
        return _update_data()
    if args.command == 'run':
        return _run_companion(args)
    if args.command == 'overlay-demo':
        return _overlay_demo()
    parser.print_help()
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
