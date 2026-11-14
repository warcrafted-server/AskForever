"""Motor de respuesta: mensaje de la tira -> respuesta breve de la IA."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional

from askforever import config
from askforever.engine.prompt import build_prompt
from askforever.engine.retriever import retrieve
from askforever.providers.openai_compat import ProviderError

MAX_ANSWER = 900

_INVALID_TEXT = {
    'es': 'No se entendió la pregunta recibida.',
    'en': 'The received question could not be read.',
}
_UNKNOWN_TEXT = {
    'es': 'No se pudo obtener la respuesta de la IA. Inténtalo de nuevo.',
    'en': 'Could not get an answer from the AI. Try again.',
}


@dataclass
class Answer:
    """Respuesta del motor con su estado y metadatos."""

    ok: bool
    text: str
    lang: str
    detail: str = ''
    elapsed_ms: int = 0
    question: str = ''
    facts: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


def _is_spanish(lang) -> bool:
    return lang in ('esES', 'esMX')


def _document(data) -> Optional[dict]:
    try:
        document = json.loads(bytes(data).decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return document if isinstance(document, dict) else None


def parse_message(data: bytes) -> Optional[dict]:
    """Valida el mensaje JSON de la tira; None si no sirve."""
    message = _document(data)
    if message is None:
        return None
    if message.get('v') != 1:
        return None
    question = message.get('q')
    if not isinstance(question, str) or not question.strip():
        return None
    return message


def _detect_lang(data) -> str:
    message = _document(data)
    if isinstance(message, dict) and _is_spanish(message.get('lang')):
        return 'esES'
    return 'enUS'


def _clean_answer(text) -> str:
    text = '' if text is None else str(text)
    text = text.replace('**', '').replace('```', '')

    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        while stripped.startswith('#'):
            stripped = stripped[1:].lstrip()
        lines.append(stripped)
    text = '\n'.join(lines).strip()

    if len(text) > MAX_ANSWER:
        cut = text[:MAX_ANSWER - 1]
        space = cut.rfind(' ')
        if space > 0:
            cut = cut[:space]
        text = cut.rstrip() + '…'
    return text


def answer_message(data: bytes, provider, *, max_tokens=None, db=None, temperature=None) -> Answer:
    """Responde a un mensaje de la tira; nunca lanza."""
    message = parse_message(data)
    if message is None:
        lang = _detect_lang(data)
        text = _INVALID_TEXT['es' if _is_spanish(lang) else 'en']
        return Answer(False, text, lang, detail='invalid')

    lang = message.get('lang') or 'enUS'
    question = str(message.get('q')).strip()

    facts_lines = []
    sources = []
    facts_text = ''
    if db is not None:
        try:
            facts = retrieve(message, db)
            facts_lines = list(facts.lines)
            sources = list(facts.sources)
            facts_text = facts.render(lang)
        except Exception:
            facts_lines, sources, facts_text = [], [], []

    system, user = build_prompt(message, facts_text)
    if temperature is None:
        temperature = config.get_temperature()

    started = time.monotonic()
    try:
        response = provider.chat(system, user, max_tokens=max_tokens, temperature=temperature)
    except ProviderError as error:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return Answer(False, error.user_message(lang), lang, detail=error.kind,
                      elapsed_ms=elapsed_ms, question=question, facts=facts_lines,
                      sources=sources)
    except Exception:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        text = _UNKNOWN_TEXT['es' if _is_spanish(lang) else 'en']
        return Answer(False, text, lang, detail='unknown', elapsed_ms=elapsed_ms,
                      question=question, facts=facts_lines, sources=sources)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    return Answer(True, _clean_answer(response), lang, detail='', elapsed_ms=elapsed_ms,
                  question=question, facts=facts_lines, sources=sources)
