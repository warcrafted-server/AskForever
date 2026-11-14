"""Construcción del prompt a partir del mensaje JSON de la tira."""

from __future__ import annotations

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
        'Eres un asistente de World of Warcraft Forever. Responde siempre en el idioma del '
        'jugador, con una respuesta corta de 2 a 5 líneas. Usa texto plano, sin Markdown, sin '
        'asteriscos ni listas largas. Usa solo información fiable y los datos del contexto. Si no '
        'estás seguro o faltan datos, dilo claramente y no inventes rutas, distancias, niveles, '
        'nombres ni coordenadas. No hagas preguntas de vuelta salvo que sea imprescindible.'
    ),
    'en': (
        "You are a World of Warcraft Forever assistant. Always answer in the player's language "
        'with a short reply of 2 to 5 lines. Use plain text, without Markdown, asterisks or long '
        'bullet lists. Use only reliable information and the data in the context. If you are not '
        'sure or data is missing, say so clearly and do not invent routes, distances, levels, '
        'names or coordinates. Do not ask follow-up questions unless strictly necessary.'
    ),
}


def _is_spanish(lang) -> bool:
    return lang in ('esES', 'esMX')


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


def build_prompt(message: dict) -> tuple[str, str]:
    """Devuelve (system, user) en el idioma del mensaje."""
    if not isinstance(message, dict):
        message = {}

    language = 'es' if _is_spanish(message.get('lang')) else 'en'
    labels = _LABELS[language]

    question = message.get('q')
    if not isinstance(question, str):
        question = '' if question is None else str(question)
    question = question.strip()

    lines = _context_lines(message.get('ctx'), labels)
    lines.append(f'{labels["question"]}: {question}')

    return _SYSTEM[language], '\n'.join(lines)
