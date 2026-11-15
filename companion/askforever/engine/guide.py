"""Índice de textos oficiales del juego para preguntas generales."""

from __future__ import annotations

import re
from collections import namedtuple

from askforever.data.wowdb import normalize
from askforever.engine.retriever import QUEST_REFERENCE_STOP_WORDS

MIN_GLOBAL_LENGTH = 40
EXTRA_STOP_WORDS = {
    'como', 'puedo', 'juego', 'personaje', 'hacer', 'para', 'quiero', 'saber',
    'how', 'game', 'character', 'what', 'does',
}
STOP_WORDS = set(QUEST_REFERENCE_STOP_WORDS) | EXTRA_STOP_WORDS
_CACHE = {}
GuideEntry = namedtuple('GuideEntry', 'ref text_es text_en tokens_es tokens_en')

_COLOUR_RE = re.compile(r'\|c[0-9a-fA-F]{8}|\|r', re.IGNORECASE)
_NEWLINE_RE = re.compile(r'\|n', re.IGNORECASE)
_TIP_RE = re.compile(r'^\s*(?:Consejo|Tip)\s*:\s*', re.IGNORECASE)
# Solo tutoriales numerados y ayudas de novato: los TUTORIAL_<NOMBRE> (TOKEN, HERO_TALENT...)
# son de versiones modernas que no existen en Forever.
_ALLOWED_TAG_RE = re.compile(r'^(?:TUTORIAL\d+|TUTORIAL_TITLE\d+|NEWBIE_TOOLTIP_)')


def clean_text(value) -> str:
    """Quita códigos de color, saltos de texto y la etiqueta inicial."""
    text = _COLOUR_RE.sub('', str(value or ''))
    text = _NEWLINE_RE.sub(' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return _TIP_RE.sub('', text).strip()


def tokenize(text) -> list[str]:
    """Tokens normalizados, sin palabras vacías ni palabras cortas."""
    normalized = normalize(text)
    tokens = re.findall(r'[a-z0-9]+', normalized)
    return [token for token in tokens
            if len(token) >= 4 and token not in STOP_WORDS]


def _token_match(question_token: str, entry_token: str) -> bool:
    if question_token == entry_token:
        return True
    shorter = min(len(question_token), len(entry_token))
    common = 0
    for left, right in zip(question_token, entry_token):
        if left != right:
            break
        common += 1
    return common >= max(5, shorter - 2)


class GuideIndex:
    """Índice perezoso y cacheado por instancia de base de datos."""

    def __new__(cls, db):
        key = id(db)
        cached = _CACHE.get(key)
        if cached is not None and getattr(cached, 'db', None) is db:
            return cached
        instance = super().__new__(cls)
        _CACHE[key] = instance
        return instance

    def __init__(self, db):
        if getattr(self, '_ready', False):
            return
        self.db = db
        self._entries = None
        self._ready = True
        try:
            setattr(db, '_guide_index', self)
        except Exception:
            pass

    @classmethod
    def for_db(cls, db):
        return cls(db)

    @property
    def entries(self):
        if self._entries is None:
            self._entries = self._load()
        return self._entries

    def _load(self):
        entries = []
        seen_refs = set()
        for row in self.db._rows(
                'SELECT ID, Text_lang, Text_lang_esES FROM gametips') or []:
            ref = f'gametip:{row["ID"]}'
            if ref in seen_refs:
                continue
            text_en = clean_text(row['Text_lang'])
            text_es = clean_text(row['Text_lang_esES'] or row['Text_lang'])
            if not text_es and not text_en:
                continue
            seen_refs.add(ref)
            entries.append(self._entry(ref, text_es, text_en))
        for row in self.db._rows(
                'SELECT BaseTag, TagText_lang, TagText_lang_esES FROM GlobalStrings') or []:
            ref = str(row['BaseTag'] or '')
            if not _ALLOWED_TAG_RE.match(ref) or ref in seen_refs:
                continue
            text_en = clean_text(row['TagText_lang'])
            text_es = clean_text(row['TagText_lang_esES'] or row['TagText_lang'])
            if max(len(text_es), len(text_en)) < MIN_GLOBAL_LENGTH:
                continue
            seen_refs.add(ref)
            entries.append(self._entry(ref, text_es, text_en))
        return entries

    @staticmethod
    def _entry(ref, text_es, text_en):
        return GuideEntry(ref, text_es, text_en,
                          frozenset(tokenize(text_es)),
                          frozenset(tokenize(text_en)))

    def search(self, question, lang, limit=3):
        spanish = str(lang).lower().startswith('es')
        question_tokens = set(tokenize(question))
        if not question_tokens:
            return []
        single_token = next(iter(question_tokens)) if len(question_tokens) == 1 else ''
        ranked = []
        for entry in self.entries:
            text = entry.text_es if spanish else entry.text_en
            if not text:
                continue
            entry_tokens = entry.tokens_es if spanish else entry.tokens_en
            score = sum(1 for token in question_tokens
                        if any(_token_match(token, candidate)
                               for candidate in entry_tokens))
            # Con una sola palabra útil, solo coincidencia exacta: «muerto» no debe traer
            # los textos de «muertes con honor».
            single_hit = (len(question_tokens) == 1 and len(single_token) >= 6
                          and single_token in entry_tokens)
            if score < 2 and not single_hit:
                continue
            priority = (0 if entry.ref.startswith(('TUTORIAL', 'NEWBIE_TOOLTIP'))
                        else 1)
            ranked.append((-score, priority, len(text), entry.ref, text))
        ranked.sort()
        return [(ref, text) for _score, _priority, _length, ref, text
                in ranked[:limit]]
