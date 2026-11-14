"""Construcción del prompt a partir del mensaje JSON de la tira."""

from __future__ import annotations

import re
from typing import Optional

_MAX_QUESTS = 15

_LABELS = {
    'es': {
        'level': 'Nivel',
        'race': 'Raza',
        'class': 'Clase',
        'faction': 'Facción',
        'zone': 'Zona',
        'coords': 'Coordenadas',
        'quests': 'Misiones activas',
        'question': 'Pregunta',
    },
    'en': {
        'level': 'Level',
        'race': 'Race',
        'class': 'Class',
        'faction': 'Faction',
        'zone': 'Zone',
        'coords': 'Coordinates',
        'quests': 'Active quests',
        'question': 'Question',
    },
}

_SYSTEM = {
    'es': (
        'Eres un asistente de World of Warcraft Forever. Responde en el idioma en que está '
        'escrita la pregunta, con una respuesta corta de 2 a 5 líneas. Usa texto plano, sin '
        'Markdown, sin asteriscos ni listas largas. Usa solo información fiable y los datos del '
        'contexto. Si no estás seguro o faltan datos, dilo claramente y no inventes rutas, '
        'distancias, niveles, nombres ni coordenadas. No hagas preguntas de vuelta salvo que sea '
        'imprescindible.'
    ),
    'en': (
        "You are a World of Warcraft Forever assistant. Answer in the language the question is "
        'written in, with a short reply of 2 to 5 lines. Use plain text, without Markdown, '
        'asterisks or long bullet lists. Use only reliable information and the data in the '
        'context. If you are not sure or data is missing, say so clearly and do not invent '
        'routes, distances, levels, names or coordinates. Do not ask follow-up questions unless '
        'strictly necessary.'
    ),
}

_LANGUAGE_NAMES = {
    'es': {'es': 'castellano', 'en': 'inglés'},
    'en': {'es': 'Spanish', 'en': 'English'},
}

_SPANISH_HINTS = set('¿¡ñáéíóú')
_SPANISH_WORDS = {
    'que', 'como', 'donde', 'cuando', 'porque', 'cual', 'quien', 'cuanto', 'mi', 'mis',
    'es', 'de', 'la', 'el', 'en', 'un', 'una', 'del', 'al',
}
_ENGLISH_WORDS = {
    'what', 'where', 'how', 'is', 'the', 'to', 'who', 'when', 'why', 'which', 'can',
    'do', 'does', 'i', 'my',
}

_FACTS_RULES = {
    'es': (
        ' Usa SOLO los datos del bloque «DATOS VERIFICADOS» para nombres de PNJ, misiones, '
        'lugares, niveles y coordenadas; incluye la zona y las coordenadas (x, y) cuando estén. '
        'Si un dato aparece en «SIN DATOS EN LA BASE» o no está en los datos ni en el contexto, '
        'di claramente que no tienes ese dato y no lo completes con suposiciones. No añadas '
        'rutas, PNJ ni lugares que no estén en los datos.'
    ),
    'en': (
        ' Use ONLY the data in the "VERIFIED DATA" block for NPC, quest, place, level and '
        'coordinate names; include the zone and the coordinates (x, y) when present. If a piece '
        'of data appears under "NOT IN THE DATABASE" or is neither in the data nor in the '
        'context, say clearly that you do not have it and do not fill it with guesses. Do not '
        'add routes, NPCs or places that are not in the data.'
    ),
}


def _is_spanish(lang) -> bool:
    return lang in ('esES', 'esMX')


def _detect_question_language(question: str, fallback: str) -> str:
    """Idioma de la pregunta por caracteres y palabras frecuentes."""
    text = (question or '').lower()
    if any(char in text for char in _SPANISH_HINTS):
        return 'es'
    words = set(re.findall(r'[a-záéíóúñü]+', text))
    if words & _SPANISH_WORDS:
        return 'es'
    if words & _ENGLISH_WORDS:
        return 'en'
    return fallback


def _system_prompt(client_language: str, question_language: str, has_facts: bool) -> str:
    text = _SYSTEM[client_language]
    language_name = _LANGUAGE_NAMES[client_language][question_language]
    if client_language == 'es':
        text += (f' La pregunta está escrita en {language_name}: responde en {language_name} '
                 'aunque el contexto esté en otro idioma.')
    else:
        text += (f' The question is written in {language_name}: answer in {language_name} even '
                 'if the context is in another language.')
    if has_facts:
        text += _FACTS_RULES[client_language]
    return text


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _number_text(value) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return f'{value:g}'


def _text(value) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _quest_line(quest) -> Optional[str]:
    if not isinstance(quest, (list, tuple)) or not quest:
        return None
    title = _text(quest[0])
    if title is None:
        return None
    level = quest[1] if len(quest) > 1 else None
    complete = quest[2] if len(quest) > 2 else 0
    line = f'- [{"x" if complete in (1, True) else " "}] {title}'
    if _is_number(level):
        line += f' ({_number_text(level)})'
    return line


def _context_lines(ctx, labels) -> list[str]:
    if not isinstance(ctx, dict):
        return []
    lines = []

    level = ctx.get('lvl')
    if _is_number(level):
        lines.append(f'{labels["level"]}: {_number_text(level)}')

    for key, label in (('race', 'race'), ('class', 'class'), ('fac', 'faction')):
        value = _text(ctx.get(key))
        if value is not None:
            lines.append(f'{labels[label]}: {value}')

    zone = _text(ctx.get('zone'))
    subzone = _text(ctx.get('sub'))
    if zone and subzone and zone != subzone:
        lines.append(f'{labels["zone"]}: {zone} - {subzone}')
    elif zone:
        lines.append(f'{labels["zone"]}: {zone}')
    elif subzone:
        lines.append(f'{labels["zone"]}: {subzone}')

    x = ctx.get('x')
    y = ctx.get('y')
    if _is_number(x) and _is_number(y):
        lines.append(f'{labels["coords"]}: {_number_text(x)}, {_number_text(y)}')

    quests = ctx.get('quests')
    if isinstance(quests, list):
        quest_lines = []
        for quest in quests:
            if len(quest_lines) >= _MAX_QUESTS:
                break
            line = _quest_line(quest)
            if line is not None:
                quest_lines.append(line)
        if quest_lines:
            lines.append(f'{labels["quests"]}:')
            lines.extend(quest_lines)

    return lines


def build_prompt(message: dict, facts_text: str = '') -> tuple[str, str]:
    """Devuelve (system, user) con las reglas del idioma y de los datos verificados."""
    if not isinstance(message, dict):
        message = {}

    language = 'es' if _is_spanish(message.get('lang')) else 'en'
    labels = _LABELS[language]

    question = message.get('q')
    if not isinstance(question, str):
        question = '' if question is None else str(question)
    question = question.strip()

    question_language = _detect_question_language(question, language)

    lines = _context_lines(message.get('ctx'), labels)
    if facts_text:
        lines.append(str(facts_text).strip())
    lines.append(f'{labels["question"]}: {question}')

    system = _system_prompt(language, question_language, bool(facts_text))
    return system, '\n'.join(lines)
