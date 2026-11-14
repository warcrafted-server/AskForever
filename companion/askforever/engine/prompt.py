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
        'Markdown, sin asteriscos ni listas largas. Si la pregunta continúa una conversación '
        'previa, interprétala con ese contexto (pronombres como «la», «allí» o «¿y…?»). Sé '
        'concreto y útil: si piden recomendaciones, recomienda opciones concretas sacadas de '
        'los DATOS y del contexto del personaje (zonas, mazmorras o misiones con sus niveles). '
        'Usa el panorama de zonas y mazmorras como referencia para recomendar adónde ir. No '
        'copies literalmente los encabezados ni las etiquetas de los bloques de datos (como '
        '«DATOS VERIFICADOS» o «SIN DATOS EN LA BASE»): redacta con naturalidad. Si usas la '
        'fuente externa, menciónalo con brevedad («según la wiki…»). Si contradice los datos '
        'verificados, mandan los datos verificados. Si la fuente externa tampoco responde, dilo '
        'en una frase. Con fuente externa sí puedes nombrar lugares, PNJ u objetos que aparezcan '
        'en ella. Usa SOLO los datos verificados y el contexto para nombres de lugares, PNJ, '
        'misiones, objetos, niveles y coordenadas. Si falta un dato o aparece en «SIN DATOS EN '
        'LA BASE», dilo en UNA frase y responde igualmente con lo que sí sabes. No inventes '
        'rutas, distancias, niveles, nombres ni coordenadas. Nunca remitas a guías, webs, foros '
        'ni a otros jugadores. Nunca menciones lugares, PNJ ni objetos que no aparezcan en los '
        'datos, el contexto o la fuente externa.'
    ),
    'en': (
        "You are a World of Warcraft Forever assistant. Answer in the language the question is "
        'written in, with a short reply of 2 to 5 lines. Use plain text, without Markdown, '
        'asterisks or long bullet lists. If the question continues a previous conversation, '
        'interpret it with that context (pronouns such as "it", "there" or "and...?"). Be '
        'concrete and useful: if asked for recommendations, recommend concrete options taken '
        'from the DATA and the character context (zones, dungeons or quests with their levels). '
        'Use the zone and dungeon panorama as the reference for recommending where to go. Do '
        'not copy the headers or labels of the data blocks literally (such as "VERIFIED DATA" '
        'or "NOT IN THE DATABASE"): write naturally. If you use the external source, mention it '
        'briefly ("according to the wiki..."). If it contradicts the verified data, the '
        'verified data wins. If the external source does not answer either, say so in one '
        'sentence. With an external source you may name places, NPCs or items that appear in '
        'it. Use ONLY the verified data and the context for names of places, NPCs, quests, '
        'items, levels and coordinates. If a piece of data is missing or appears under "NOT IN '
        'THE DATABASE", say it in ONE sentence and still answer with what you do know. Do not '
        'invent routes, distances, levels, names or coordinates. Never refer to guides, '
        'websites, forums or other players. Never mention places, NPCs or items that do not '
        'appear in the data, the context or the external source.'
    ),
}

_HISTORY = {
    'es': {
        'title': 'CONVERSACIÓN PREVIA (de la más antigua a la más reciente):',
        'user': 'Jugador',
        'assistant': 'Asistente',
    },
    'en': {
        'title': 'PREVIOUS CONVERSATION (oldest first):',
        'user': 'Player',
        'assistant': 'Assistant',
    },
}

MAX_HISTORY_ANSWER = 300

_WEB_HEADER = {
    'es': ('FUENTE EXTERNA (warcraft.wiki.gg; puede describir otra versión del juego, '
           'los datos de la base de Forever mandan):'),
    'en': ('EXTERNAL SOURCE (warcraft.wiki.gg; may describe another game version, '
           'the Forever database takes priority):'),
}

_NO_INFO = {
    'es': ('No hay datos en la base de datos ni en la wiki para esta pregunta: dilo en una '
           'sola frase y NO menciones lugares, PNJ, objetos ni cifras concretas; puedes '
           'sugerir reformular la pregunta.'),
    'en': ('There is no data in the database or the wiki for this question: say it in one '
           'sentence and do NOT mention specific places, NPCs, objects or figures; you may '
           'suggest rephrasing the question.'),
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


def _system_prompt(client_language: str, question_language: str, no_info: bool = False) -> str:
    text = _SYSTEM[client_language]
    language_name = _LANGUAGE_NAMES[client_language][question_language]
    if client_language == 'es':
        text += (f' La pregunta está escrita en {language_name}: responde en {language_name} '
                 'aunque el contexto esté en otro idioma.')
    else:
        text += (f' The question is written in {language_name}: answer in {language_name} even '
                 'if the context is in another language.')
    if no_info:
        text += ' ' + _NO_INFO[client_language]
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


def _turn_value(turn, name: str) -> str:
    if isinstance(turn, dict):
        value = turn.get(name)
    else:
        value = getattr(turn, name, None)
    return '' if value is None else str(value)


def _history_lines(history, language: str) -> list[str]:
    """Bloque de conversación previa, del turno más antiguo al más reciente."""
    if not history:
        return []
    labels = _HISTORY[language]
    lines = [labels['title']]
    for turn in history:
        question = _turn_value(turn, 'question').strip()
        answer = _turn_value(turn, 'answer').strip()
        if not question and not answer:
            continue
        lines.append(f"{labels['user']}: {question}")
        lines.append(f"{labels['assistant']}: {answer[:MAX_HISTORY_ANSWER]}")
    return lines


def _excerpt_field(excerpt, name: str) -> str:
    if isinstance(excerpt, dict):
        value = excerpt.get(name)
    else:
        value = getattr(excerpt, name, None)
    return '' if value is None else str(value)


def _web_lines(web_excerpts, language: str) -> list[str]:
    """Bloque de fuentes externas, con título, URL y texto de cada extracto."""
    if not web_excerpts:
        return []
    lines = [_WEB_HEADER[language]]
    for index, excerpt in enumerate(web_excerpts):
        if index:
            lines.append('')
        title = _excerpt_field(excerpt, 'title')
        url = _excerpt_field(excerpt, 'url')
        text = _excerpt_field(excerpt, 'text')
        lines.append(f'[{title}] {url}')
        if text:
            lines.append(text)
    return lines


def build_prompt(message: dict, facts_text: str = '', history=None,
                 web_excerpts=None, no_info: bool = False) -> tuple[str, str]:
    """Devuelve (system, user) con el idioma, la memoria y las fuentes."""
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
    lines.extend(_history_lines(history, language))
    if facts_text:
        lines.append(str(facts_text).strip())
    lines.extend(_web_lines(web_excerpts, language))
    lines.append(f'{labels["question"]}: {question}')

    system = _system_prompt(language, question_language, no_info)
    return system, '\n'.join(lines)
