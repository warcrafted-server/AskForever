"""Glosario de nombres oficiales en español para los extractos de la wiki."""

from __future__ import annotations

import re

_TABLES = (
    ('SpellName', 'Name_lang', 'Name_lang_esES'),
    ('GameObjects', 'Name_lang', 'Name_lang_esES'),
    ('Creature', 'Name_lang', 'Name_lang_esES'),
    ('AreaTable', 'AreaName_lang', 'AreaName_lang_esES'),
    ('Faction', 'Name_lang', 'Name_lang_esES'),
    ('ItemSet', 'Name_lang', 'Name_lang_esES'),
    ('TaxiNodes', 'Name_lang', 'Name_lang_esES'),
    ('ChrClasses', 'Name_lang', 'Name_lang_esES'),
    ('SkillLine', 'DisplayName_lang', 'DisplayName_lang_esES'),
    ('Map', 'MapName_lang', 'MapName_lang_esES'),
)

_CONNECTORS = frozenset({
    'of', 'the', 'de', 'del', 'la', 'el', 'los', 'las', 'and', 'or', 'y',
    'a', 'an', 'in', 'on', 'for', 'to', 'from', 'with', 'by', 'at',
})

_TOKEN = re.compile(r"[^\W\d_][\w'’\-]*", re.UNICODE)


def _candidates(texts) -> list[tuple[str, int, int]]:
    if isinstance(texts, str):
        texts = [texts]
    elif texts is None:
        texts = []
    found = {}
    position = 0
    for text in texts:
        if not isinstance(text, str):
            continue
        tokens = _TOKEN.findall(text)
        for start, first in enumerate(tokens):
            if not first[:1].isupper():
                continue
            end = start
            length = 0
            while end < len(tokens) and length < 5:
                token = tokens[end]
                if end > start:
                    if not token[:1].isupper() and token.casefold() not in _CONNECTORS:
                        break
                length += 1
                end += 1
                if tokens[end - 1].casefold() in _CONNECTORS:
                    continue
                if length == 1 and len(tokens[start]) < 4:
                    continue
                phrase = ' '.join(tokens[start:end])
                key = phrase.casefold()
                if key not in found:
                    found[key] = (phrase, length, position)
                    position += 1
    return list(found.values())


def _search(db, phrase: str):
    for table, english_column, spanish_column in _TABLES:
        sql = (f'SELECT {english_column}, {spanish_column} FROM {table} '
               f'WHERE {english_column} = ? COLLATE NOCASE LIMIT 1')
        try:
            rows = db._rows(sql, (phrase,))
        except Exception:
            continue
        if not rows:
            continue
        try:
            row = rows[0]
            english = '' if row[0] is None else str(row[0]).strip()
            spanish = '' if row[1] is None else str(row[1]).strip()
        except (IndexError, TypeError):
            continue
        if not english or not spanish:
            continue
        if spanish.casefold() == english.casefold():
            continue
        return english, spanish
    return None


def spanish_names(db, texts, limit=25) -> list[tuple[str, str]]:
    """Pares (inglés, español) de los nombres oficiales que aparecen en los textos."""
    try:
        if db is None or not callable(getattr(db, '_rows', None)):
            return []
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 25
        if limit <= 0:
            return []
        ordered = sorted(_candidates(texts), key=lambda item: (-item[1], item[2]))
        results = []
        seen = set()
        for phrase, _length, _position in ordered:
            if len(results) >= limit:
                break
            pair = _search(db, phrase)
            if pair is None:
                continue
            english, spanish = pair
            key = english.casefold()
            if key in seen:
                continue
            seen.add(key)
            results.append((english, spanish))
        return results
    except Exception:
        return []
