"""Enrutador de preguntas generales al índice de la guía."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from askforever.engine.guide import build_toc
from askforever.providers.openai_compat import ProviderError

ROUTER_SYSTEM = {
    'es': (
        'Eres el índice de una guía de WoW Forever. Devuelve SOLO un JSON '
        '{"ids": [...]} con los identificadores (hasta 3) de las secciones del índice '
        'que responden a la pregunta del jugador, de la más a la menos útil, o '
        '{"ids": []} si ninguna. No respondas a la pregunta.'
    ),
    'en': (
        'You are the index of a WoW Forever guide. Return ONLY a JSON '
        '{"ids": [...]} with the identifiers (up to 3) of the index sections that '
        'answer the player question, from most to least useful, or {"ids": []} if '
        'none. Do not answer the question.'
    ),
}
MAX_IDS = 3


def _spanish(lang) -> bool:
    return str(lang).lower().startswith('es')


def _player_line(ctx, spanish: bool) -> str:
    if not isinstance(ctx, dict):
        return ''
    parts = []
    level = ctx.get('lvl')
    if level is not None and str(level).strip():
        parts.append(('nivel ' if spanish else 'level ') + str(level).strip())
    for key in ('race', 'class'):
        value = str(ctx.get(key) or '').strip()
        if value:
            parts.append(value)
    if not parts:
        return ''
    return ('Jugador: ' if spanish else 'Player: ') + ', '.join(parts) + '.'


def _previous_question(history) -> str:
    if not history:
        return ''
    last = history[-1]
    if isinstance(last, dict):
        return str(last.get('question') or '').strip()
    return str(getattr(last, 'question', '') or '').strip()


def _user_message(question, lang, ctx, history, toc) -> str:
    spanish = _spanish(lang)
    parts = []
    player = _player_line(ctx, spanish)
    if player:
        parts.append(player)
    previous = _previous_question(history)
    if previous:
        parts.append(('Pregunta anterior: ' if spanish else 'Previous question: ')
                     + previous)
    parts.append(('Pregunta: ' if spanish else 'Question: ') + str(question or '').strip())
    parts.append('ÍNDICE:' if spanish else 'INDEX:')
    parts.extend(line for _identifier, line in toc)
    return '\n'.join(parts)


def _first_json_object(text):
    if not isinstance(text, str):
        return None
    decoder = json.JSONDecoder()
    for match in re.finditer(r'\{', text):
        try:
            value, _end = decoder.raw_decode(text[match.start():])
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def route(provider, question, lang, ctx, history=None, timeout=8.0) -> list[str] | None:
    """Pide al modelo que elija secciones; nunca lanza y devuelve None si falla."""
    try:
        return _route(provider, question, lang, ctx, history, timeout)
    except Exception:
        return None


def _route(provider, question, lang, ctx, history, timeout) -> list[str] | None:
    try:
        toc = build_toc(lang, ctx, question)
    except Exception:
        return None
    if not toc:
        return None
    if timeout is None:
        timeout = 8.0

    spanish = _spanish(lang)
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        provider.chat, ROUTER_SYSTEM['es' if spanish else 'en'],
        _user_message(question, lang, ctx, history, toc),
        max_tokens=60, temperature=0,
    )
    try:
        response = future.result(timeout=timeout)
    except (FutureTimeout, ProviderError):
        future.cancel()
        return None
    except Exception:
        future.cancel()
        return None
    finally:
        executor.shutdown(wait=False)

    payload = _first_json_object(response)
    if not isinstance(payload, dict) or not isinstance(payload.get('ids'), list):
        return None
    known = {identifier for identifier, _line in toc}
    ids = []
    for value in payload['ids']:
        if isinstance(value, str) and value in known and value not in ids:
            ids.append(value)
            if len(ids) >= MAX_IDS:
                break
    return ids
