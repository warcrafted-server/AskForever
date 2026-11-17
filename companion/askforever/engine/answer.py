"""Motor de respuesta: mensaje de la tira -> respuesta breve de la IA."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from askforever import config
from askforever.data.glossary import spanish_names
from askforever.data.wowdb import normalize
from askforever.engine import router
from askforever.engine.prompt import _detect_question_language, build_prompt
from askforever.engine.retriever import (PROFESSION_KEYWORDS, add_guide_sections,
                                         is_profession_question, is_travel_question,
                                         retrieve, _GUIDE_LABELS)
from askforever.providers.openai_compat import ProviderError

MAX_ANSWER = 2500

_INVALID_TEXT = {
    'es': 'No se entendió la pregunta recibida.',
    'en': 'The received question could not be read.',
}
_UNKNOWN_TEXT = {
    'es': 'No se pudo obtener la respuesta de la IA. Inténtalo de nuevo.',
    'en': 'Could not get an answer from the AI. Try again.',
}

_WEB_SEARCH_SYSTEM = (
    "You turn a World of Warcraft player's question into wiki searches. Output ONLY 1 to 3 "
    'search terms, one per line, 2 to 4 words each, in English, using in-game names as wiki '
    'page titles (for example: Expert Fishing, Fishing trainer, Expert First Aid, Darkshore). '
    'No explanations, no numbering, no quotes, no thinking.'
)
_ROUTE_PHRASES = ('cómo voy', 'como voy', 'cómo llego', 'como llego', 'cómo ir',
                  'como ir', 'how do i get', 'how to get', 'route')
_WEB_MAX_EXCERPTS = 3
_WEB_MAX_SEARCHES = 3
_FOLLOW_UP_STARTS = {'y', 'e', 'pero', 'entonces', 'and', 'but', 'so'}
_FOLLOW_UP_POINTERS = {'ese', 'esa', 'eso', 'esos', 'esas', 'alli', 'ahi', 'that', 'those',
                       'there'}
_FOLLOW_UP_MAX_WORDS = 9
_FOLLOW_UP_PHRASES = (
    'mas opciones', 'otra opcion', 'otras opciones', 'hay mas', 'no hay mas',
    'alguna mas', 'algo mas', 'any other', 'more options', 'anything else',
    'what else',
)


def is_follow_up(question) -> bool:
    """Pregunta corta que continúa la anterior («y para subir de nivel, ¿cuál?»)."""
    normalized = normalize(str(question or ''))
    words = re.findall(r'[a-z0-9]+', normalized)
    if not words or len(words) > _FOLLOW_UP_MAX_WORDS:
        return False
    return (words[0] in _FOLLOW_UP_STARTS
            or any(word in _FOLLOW_UP_POINTERS for word in words)
            or any(phrase in normalized for phrase in _FOLLOW_UP_PHRASES))


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
    router: str = 'off'


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

    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        for label in _GUIDE_LABELS:
            if stripped.startswith(label):
                stripped = stripped[len(label):]
                break
        lines.append(stripped)
    text = '\n'.join(lines)
    text = text.replace('**', '').replace('```', '')

    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        while stripped.startswith('#'):
            stripped = stripped[1:].lstrip()
        lines.append(stripped)
    lines = [re.sub(r'^(?:[-*•–]\s+|\d+[.)]\s+)', '• ', line).rstrip()
             for line in lines]
    text = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines).strip())

    if len(text) > MAX_ANSWER:
        cut = text[:MAX_ANSWER - 1]
        space = cut.rfind(' ')
        if space > 0:
            cut = cut[:space]
        text = cut.rstrip() + '…'
    return text


def _is_route_question(question: str) -> bool:
    if is_travel_question(question):
        return True
    text = (question or '').lower()
    return any(phrase in text for phrase in _ROUTE_PHRASES)


def _is_route_missing(missing) -> bool:
    for item in missing or []:
        text = str(item).lower()
        if 'ruta' in text or 'route' in text:
            return True
    return False


_TRANSPORT_WORDS = ('barco', 'zepelin', 'tranvia', 'ferry', 'transbordador', 'boat', 'ship', 'zeppelin',
                    'tram')


def needs_web(facts, question, history=None) -> bool:
    """True si conviene buscar en la wiki para completar la respuesta."""
    text = str(question or '').strip()
    if _is_route_question(text):
        return False
    # Los transportes, como las rutas, salen solo de la base (decisión del mantenedor).
    normalized_text = normalize(text)
    if any(word in normalized_text for word in _TRANSPORT_WORDS):
        return False
    if len(text.split()) < 3 and not history:
        return False
    if facts is None:
        return True
    missing = list(getattr(facts, 'missing', None) or [])
    if _is_route_missing(missing):
        return False
    sources = list(getattr(facts, 'sources', None) or [])
    if any(str(source).startswith(('guide:section:', 'zone_quests:'))
           for source in sources):
        return False
    if missing:
        return True
    lines = list(getattr(facts, 'lines', None) or [])
    if not lines:
        return True
    if sources and all(str(source).startswith('panorama:') for source in sources):
        return True
    if is_profession_question(text):
        normalized = normalize(text)
        terms = [keyword for keyword in PROFESSION_KEYWORDS if keyword in normalized]
        if terms and not any(any(term in normalize(line) for term in terms)
                             for line in lines):
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
    parts = [f'Question: {question}']
    past = _past_question(previous_question, history)
    if past:
        parts.append(f'Previous question: {past}')
    ctx = message.get('ctx') if isinstance(message, dict) else None
    level = None
    race = klass = faction = ''
    if isinstance(ctx, dict):
        level = ctx.get('lvl')
        race = ctx.get('race') or ''
        klass = ctx.get('class') or ''
        faction = ctx.get('fac') or ''
    level_text = '' if level is None else str(level)
    player = f'Player: level {level_text} {race} {klass}, {faction}.'
    parts.append(re.sub(r'\s+', ' ', player))
    return '\n'.join(parts)


def _parse_search_terms(text) -> list[str]:
    """Convierte la respuesta del proveedor en búsquedas cortas de wiki."""
    if not isinstance(text, str):
        return []
    text = re.sub(r'<thought>.*?</thought>', ' ', text, flags=re.IGNORECASE | re.DOTALL)
    terms = []
    seen = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or '```' in line or '<' in line or '>' in line or ':' in line:
            continue
        line = re.sub(r'^\s*(?:[-*•]+|\d+[.)])\s*', '', line)
        line = line.strip(' "\'“”‘’«»')
        line = line.strip()
        if not line or len(line.split()) > 6:
            continue
        if not any(char.isalpha() for char in line):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        terms.append(line)
        if len(terms) >= _WEB_MAX_SEARCHES:
            break
    return terms


def _search_keywords(terms) -> list[str]:
    """Palabras de más de tres letras de las búsquedas, sin repetir."""
    keywords = []
    seen = set()
    for term in terms:
        for word in re.findall(r'[^\W\d_]+', term, flags=re.UNICODE):
            key = word.lower()
            if len(word) > 3 and key not in seen:
                seen.add(key)
                keywords.append(word)
    return keywords


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
        response = provider.chat(_WEB_SEARCH_SYSTEM, user, max_tokens=400,
                                 temperature=0.0)
        queries = _parse_search_terms(response)
        keywords = _search_keywords(queries)
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
    router_outcome = 'off'
    if db is not None:
        try:
            facts = retrieve(message, db)
            previous = str(previous_question).strip() if previous_question else ''
            # Una continuación puede traer datos propios («levear» trae zonas) y aun así
            # referirse al tema anterior (las ramas de talentos): se buscan los dos juntos.
            if previous and ((not facts.lines and not facts.missing)
                             or is_follow_up(question)):
                follow_message = dict(message)
                follow_message['q'] = f'{previous} {question}'.strip()
                follow = retrieve(follow_message, db)
                if follow.lines or follow.missing:
                    facts = follow
            if (getattr(facts, 'guide_eligible', False)
                    and config.get_guide_router_enabled()
                    and provider is not None):
                try:
                    ctx = message.get('ctx')
                    ids = router.route(
                        provider, question, 'es' if _is_spanish(lang) else 'en',
                        ctx if isinstance(ctx, dict) else {}, history)
                    if ids:
                        add_guide_sections(facts, db, ids,
                                           'es' if _is_spanish(lang) else 'en')
                        router_outcome = 'ok:' + ','.join(ids)
                    elif ids == []:
                        router_outcome = 'empty'
                    else:
                        router_outcome = 'fallback'
                except Exception:
                    router_outcome = 'fallback'
            facts_lines = list(facts.lines)
            sources = list(facts.sources)
            facts_text = facts.render(lang)
        except Exception:
            facts = None
            facts_lines, sources, facts_text = [], [], []
            router_outcome = 'off'

    try:
        use_web = web is not None and needs_web(facts, question, history)
    except Exception:
        use_web = False
    web_excerpts = []
    web_titles = []
    if use_web:
        web_excerpts, web_titles = web_fallback(
            web, provider, message, facts, question, history=history,
            previous_question=previous_question)
        for title in web_titles:
            source = f'wiki:{title}'
            if source not in sources:
                sources.append(source)
    no_info = bool(use_web and not web_excerpts)

    glossary = None
    if web_excerpts and db is not None:
        try:
            client_spanish = _is_spanish(lang)
            question_language = _detect_question_language(
                question, 'es' if client_spanish else 'en')
            if client_spanish or question_language == 'es':
                texts = []
                for excerpt in web_excerpts:
                    texts.append(_excerpt_value(excerpt, 'title'))
                    texts.append(_excerpt_value(excerpt, 'text'))
                glossary = spanish_names(db, texts)
        except Exception:
            glossary = None

    system, user = build_prompt(message, facts_text, history=history,
                                web_excerpts=web_excerpts or None, no_info=no_info,
                                glossary=glossary)
    if temperature is None:
        temperature = config.get_temperature()

    started = time.monotonic()
    try:
        response = provider.chat(system, user, max_tokens=max_tokens, temperature=temperature)
    except ProviderError as error:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return Answer(False, error.user_message(lang), lang, detail=error.kind,
                      elapsed_ms=elapsed_ms, question=question, facts=facts_lines,
                      sources=sources, facts_text=facts_text, web_titles=web_titles,
                      router=router_outcome)
    except Exception:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        text = _UNKNOWN_TEXT['es' if _is_spanish(lang) else 'en']
        return Answer(False, text, lang, detail='unknown', elapsed_ms=elapsed_ms,
                      question=question, facts=facts_lines, sources=sources,
                      facts_text=facts_text, web_titles=web_titles,
                      router=router_outcome)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    return Answer(True, _clean_answer(response), lang, detail='', elapsed_ms=elapsed_ms,
                  question=question, facts=facts_lines, sources=sources,
                  facts_text=facts_text, web_titles=web_titles, router=router_outcome)
