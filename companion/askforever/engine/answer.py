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

_WEB_SEARCH_SYSTEM = (
    'You generate search queries for the World of Warcraft wiki. Return ONLY a JSON object '
    'with the shape {"queries": ["..."], "keywords": ["..."]}. Give 1 to 3 short searches of '
    '2 to 4 words each, using English in-game names as they would appear in page titles (for '
    'example "Expert Fishing", "Fishing trainer", "Darkshore", "Expert First Aid"). Do not use '
    'words such as "Classic", "where", "how" or "best", and do not write full sentences. Add a '
    'few short keywords.'
)
_ROUTE_PHRASES = ('cómo voy', 'como voy', 'cómo llego', 'como llego', 'cómo ir',
                  'como ir', 'how do i get', 'how to get', 'route')
_WEB_MAX_EXCERPTS = 3


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
    facts_text: str = ''
    web_titles: list[str] = field(default_factory=list)


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


def _is_route_question(question: str) -> bool:
    text = (question or '').lower()
    return any(phrase in text for phrase in _ROUTE_PHRASES)


def _is_route_missing(missing) -> bool:
    for item in missing or []:
        text = str(item).lower()
        if 'ruta' in text or 'route' in text:
            return True
    return False


def needs_web(facts, question, history=None) -> bool:
    """True si conviene buscar en la wiki para completar la respuesta."""
    text = str(question or '').strip()
    if _is_route_question(text):
        return False
    if len(text.split()) < 3 and not history:
        return False
    if facts is None:
        return True
    missing = list(getattr(facts, 'missing', None) or [])
    if _is_route_missing(missing):
        return False
    if missing:
        return True
    lines = list(getattr(facts, 'lines', None) or [])
    if not lines:
        return True
    sources = list(getattr(facts, 'sources', None) or [])
    if sources and all(str(source).startswith('panorama:') for source in sources):
        return True
    return False


def _past_question(previous_question, history) -> str:
    if previous_question:
        return str(previous_question).strip()
    if history:
        last = history[-1]
        if isinstance(last, dict):
            return str(last.get('question') or '').strip()
        return str(getattr(last, 'question', '') or '').strip()
    return ''


def _search_user(message, question, previous_question, history) -> str:
    parts = []
    past = _past_question(previous_question, history)
    if past:
        parts.append(f'Previous question: {past}')
    parts.append(f'Question: {question}')
    ctx = message.get('ctx') if isinstance(message, dict) else None
    if isinstance(ctx, dict):
        for key, label in (('class', 'Class'), ('race', 'Race'),
                           ('fac', 'Faction'), ('lvl', 'Level')):
            value = ctx.get(key)
            if value is not None and value != '':
                parts.append(f'{label}: {value}')
    return '\n'.join(parts)


def _parse_search_plan(text):
    """Extrae el primer objeto JSON del texto del proveedor."""
    if not isinstance(text, str):
        return None
    start = text.find('{')
    while start >= 0:
        depth = 0
        for index in range(start, len(text)):
            char = text[index]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    try:
                        plan = json.loads(text[start:index + 1])
                    except (json.JSONDecodeError, TypeError, ValueError):
                        break
                    return plan if isinstance(plan, dict) else None
        start = text.find('{', start + 1)
    return None


def _search_plan(text, question):
    plan = _parse_search_plan(text)
    queries = []
    keywords = []
    if isinstance(plan, dict):
        raw_queries = plan.get('queries')
        if isinstance(raw_queries, str):
            raw_queries = [raw_queries]
        if isinstance(raw_queries, list):
            queries = [str(item).strip() for item in raw_queries
                       if isinstance(item, str) and item.strip()][:3]
        raw_keywords = plan.get('keywords')
        if isinstance(raw_keywords, str):
            raw_keywords = [raw_keywords]
        if isinstance(raw_keywords, list):
            keywords = [str(item).strip() for item in raw_keywords
                        if isinstance(item, str) and item.strip()]
    if not queries:
        queries = [question]
    return queries, keywords


def _excerpt_value(excerpt, name: str) -> str:
    if isinstance(excerpt, dict):
        value = excerpt.get(name)
    else:
        value = getattr(excerpt, name, None)
    return '' if value is None else str(value)


def web_fallback(web, provider, message, facts, question, *, history=None,
                 previous_question=None):
    """Consulta la wiki si hace falta; devuelve (extractos, títulos) y nunca lanza."""
    if web is None:
        return [], []
    try:
        if not needs_web(facts, question, history):
            return [], []
        user = _search_user(message, question, previous_question, history)
        response = provider.chat(_WEB_SEARCH_SYSTEM, user, max_tokens=150,
                                 temperature=0.0)
        queries, keywords = _search_plan(response, question)
        excerpts = []
        seen = set()
        for query in queries:
            try:
                found = web.lookup(query, keywords) or []
            except Exception:
                continue
            for excerpt in found:
                title = _excerpt_value(excerpt, 'title').strip()
                key = title.lower()
                if not title or key in seen:
                    continue
                seen.add(key)
                excerpts.append(excerpt)
        excerpts.sort(key=lambda item: 0 if 'forever' in
                      _excerpt_value(item, 'title').lower() else 1)
        excerpts = excerpts[:_WEB_MAX_EXCERPTS]
        titles = [_excerpt_value(item, 'title').strip() for item in excerpts]
        return excerpts, titles
    except Exception:
        return [], []


def answer_message(data: bytes, provider, *, max_tokens=None, db=None, temperature=None,
                   history=None, previous_question=None, web=None) -> Answer:
    """Responde a un mensaje de la tira; nunca lanza."""
    message = parse_message(data)
    if message is None:
        lang = _detect_lang(data)
        text = _INVALID_TEXT['es' if _is_spanish(lang) else 'en']
        return Answer(False, text, lang, detail='invalid')

    lang = message.get('lang') or 'enUS'
    question = str(message.get('q')).strip()

    facts = None
    facts_lines = []
    sources = []
    facts_text = ''
    if db is not None:
        try:
            facts = retrieve(message, db)
            previous = str(previous_question).strip() if previous_question else ''
            if not facts.lines and not facts.missing and previous:
                follow_message = dict(message)
                follow_message['q'] = f'{previous} {question}'.strip()
                follow = retrieve(follow_message, db)
                if follow.lines or follow.missing:
                    facts = follow
            facts_lines = list(facts.lines)
            sources = list(facts.sources)
            facts_text = facts.render(lang)
        except Exception:
            facts = None
            facts_lines, sources, facts_text = [], [], []

    web_excerpts = []
    web_titles = []
    if web is not None:
        web_excerpts, web_titles = web_fallback(
            web, provider, message, facts, question, history=history,
            previous_question=previous_question)
        for title in web_titles:
            source = f'wiki:{title}'
            if source not in sources:
                sources.append(source)

    system, user = build_prompt(message, facts_text, history=history,
                                web_excerpts=web_excerpts or None)
    if temperature is None:
        temperature = config.get_temperature()

    started = time.monotonic()
    try:
        response = provider.chat(system, user, max_tokens=max_tokens, temperature=temperature)
    except ProviderError as error:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return Answer(False, error.user_message(lang), lang, detail=error.kind,
                      elapsed_ms=elapsed_ms, question=question, facts=facts_lines,
                      sources=sources, facts_text=facts_text, web_titles=web_titles)
    except Exception:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        text = _UNKNOWN_TEXT['es' if _is_spanish(lang) else 'en']
        return Answer(False, text, lang, detail='unknown', elapsed_ms=elapsed_ms,
                      question=question, facts=facts_lines, sources=sources,
                      facts_text=facts_text, web_titles=web_titles)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    return Answer(True, _clean_answer(response), lang, detail='', elapsed_ms=elapsed_ms,
                  question=question, facts=facts_lines, sources=sources,
                  facts_text=facts_text, web_titles=web_titles)
