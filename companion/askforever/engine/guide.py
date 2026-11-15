"""Índice de textos oficiales del juego para preguntas generales."""

from __future__ import annotations

import json
import re
from collections import namedtuple
from pathlib import Path

from askforever.data.wowdb import normalize
from askforever.engine.retriever import QUEST_REFERENCE_STOP_WORDS

GUIDE_SECTIONS_PATH = Path(__file__).resolve().parents[1] / 'data' / 'guide.json'
# Un archivo por capítulo para que se redacten por separado sin pisarse.
GUIDE_SECTIONS_DIR = Path(__file__).resolve().parents[1] / 'data' / 'guide'
# 'verificado': Blizzard, el juego o Marc. 'editorial': guías de terceros sin confirmar; la IA
# las usa sin citarlas y los jugadores reportan los errores.
USED_STATUSES = ('verificado', 'editorial')
MIN_GLOBAL_LENGTH = 40
EXTRA_STOP_WORDS = {
    'como', 'puedo', 'juego', 'personaje', 'hacer', 'para', 'quiero', 'saber',
    'significa', 'significan', 'tener', 'sigo', 'recomiendas', 'recomienda',
    'hola', 'gracias', 'vale', 'adios', 'perfecto', 'genial', 'forever', 'warcraft', 'world',
    'how', 'game', 'character', 'what', 'does', 'mean', 'means', 'thanks', 'hello',
}
# Las palabras de dominio que el buscador de misiones descarta aquí sí distinguen textos:
# «colores de los objetos» frente a «colores de las misiones».
DOMAIN_WORDS = {
    'mision', 'misiones', 'quest', 'quests', 'objeto', 'objetos', 'item', 'items',
    'npc', 'pnj', 'matar', 'mato', 'kill', 'drop', 'drops', 'zona',
}
STOP_WORDS = (set(QUEST_REFERENCE_STOP_WORDS) - DOMAIN_WORDS) | EXTRA_STOP_WORDS
_CACHE = {}
_TOC_CACHE = {}
GuideEntry = namedtuple('GuideEntry',
                        'ref text_es text_en tokens_es tokens_en requires heads tags status',
                        defaults=(frozenset(), frozenset(), frozenset(), ''))
RACE_TAGS = {
    'humano': 'HUMAN', 'humana': 'HUMAN', 'human': 'HUMAN',
    'orco': 'ORC', 'orca': 'ORC', 'orc': 'ORC',
    'enano': 'DWARF', 'enana': 'DWARF', 'dwarf': 'DWARF',
    'elfo de la noche': 'NIGHTELF', 'elfa de la noche': 'NIGHTELF', 'night elf': 'NIGHTELF',
    'no muerto': 'SCOURGE', 'no muerta': 'SCOURGE', 'undead': 'SCOURGE',
    'tauren': 'TAUREN', 'gnomo': 'GNOME', 'gnoma': 'GNOME', 'gnome': 'GNOME',
    'trol': 'TROLL', 'troll': 'TROLL',
}
CLASS_TAGS = {
    'guerrero': 'WARRIOR', 'guerrera': 'WARRIOR', 'warrior': 'WARRIOR',
    'paladin': 'PALADIN', 'cazador': 'HUNTER', 'cazadora': 'HUNTER', 'hunter': 'HUNTER',
    'picaro': 'ROGUE', 'picara': 'ROGUE', 'rogue': 'ROGUE',
    'sacerdote': 'PRIEST', 'sacerdotisa': 'PRIEST', 'priest': 'PRIEST',
    'chaman': 'SHAMAN', 'shaman': 'SHAMAN', 'mago': 'MAGE', 'maga': 'MAGE', 'mage': 'MAGE',
    'brujo': 'WARLOCK', 'bruja': 'WARLOCK', 'warlock': 'WARLOCK',
    'druida': 'DRUID', 'druid': 'DRUID',
}
# Skyborne no está en RACE_TAGS porque el cliente no usa esa raza para los tutoriales,
# pero sus secciones de guía sí llevan la etiqueta.
_EXTRA_TAGS = {
    'cielonato': 'SKYBORNE', 'cielonata': 'SKYBORNE', 'skyborne': 'SKYBORNE',
}
_TAG_WORDS = {**RACE_TAGS, **_EXTRA_TAGS, **CLASS_TAGS}
_KNOWN_TAGS = set(_TAG_WORDS.values())


_COLOUR_RE = re.compile(r'\|c[0-9a-fA-F]{8}|\|r', re.IGNORECASE)
_NEWLINE_RE = re.compile(r'\|n', re.IGNORECASE)
_TIP_RE = re.compile(r'^\s*(?:Consejo|Tip)\s*:\s*', re.IGNORECASE)
# Solo tutoriales numerados y ayudas de novato: los TUTORIAL_<NOMBRE> (TOKEN, HERO_TALENT...)
# son de versiones modernas que no existen en Forever.
_ALLOWED_TAG_RE = re.compile(r'^(?:TUTORIAL\d+|TUTORIAL_TITLE\d+|NEWBIE_TOOLTIP_)')
_TITLE_RE = re.compile(r'^TUTORIAL_TITLE(\d+(?:_[A-Z_]+)?)$')
_SUFFIX_RE = re.compile(r'^TUTORIAL\d+_([A-Z_]+)$')


def _section_files(path):
    if path is None:
        files = [GUIDE_SECTIONS_PATH]
        try:
            files += sorted(GUIDE_SECTIONS_DIR.glob('*.json'))
        except OSError:
            pass
        return files
    path = Path(path)
    if path.is_dir():
        return sorted(path.glob('*.json'))
    return [path]


def load_sections(path=None):
    """Secciones usables de la guía (verificadas y editoriales); nunca lanza.

    Sin ruta lee guide.json y la carpeta data/guide; un id repetido se queda con la primera
    aparición, así que guide.json (lo verificado) manda.
    """
    sections = []
    seen = set()
    for file in _section_files(path):
        for item in _load_section_file(file):
            if item['id'] in seen:
                continue
            seen.add(item['id'])
            sections.append(item)
    return sections


def _load_section_file(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, TypeError, ValueError):
        return []
    items = data.get('sections') if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    sections = []
    for item in items:
        if not isinstance(item, dict) or item.get('status') not in USED_STATUSES:
            continue
        section_id = item.get('id')
        text_es = item.get('text_es')
        text_en = item.get('text_en')
        if not isinstance(section_id, str) or not section_id.strip():
            continue
        if not isinstance(text_es, str) or not text_es.strip():
            continue
        if not isinstance(text_en, str) or not text_en.strip():
            continue
        keywords_ok = True
        for key in ('keywords_es', 'keywords_en'):
            values = item.get(key, [])
            if not isinstance(values, list) or any(
                    not isinstance(value, str) for value in values):
                keywords_ok = False
                break
        if keywords_ok:
            sections.append(item)
    return sections


def clean_text(value) -> str:
    """Quita códigos de color, saltos de texto y la etiqueta inicial."""
    text = _COLOUR_RE.sub('', str(value or ''))
    text = _NEWLINE_RE.sub(' ', text)
    text = text.replace('\\n', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return _TIP_RE.sub('', text).strip()


def player_tags_from_ctx(ctx) -> frozenset:
    """Etiquetas de raza y clase del jugador (HUMAN, HUNTER...) según el contexto."""
    if not isinstance(ctx, dict):
        return frozenset()
    tags = set()
    for key, table in (('race', RACE_TAGS), ('class', CLASS_TAGS)):
        value = ' '.join(re.findall(r'[a-z]+', normalize(ctx.get(key) or '')))
        if value in table:
            tags.add(table[value])
    return frozenset(tags)


def _toc_player_tags(ctx) -> frozenset:
    if not isinstance(ctx, dict):
        return frozenset()
    cleaned = dict(ctx)
    for key in ('race', 'class'):
        value = cleaned.get(key)
        if isinstance(value, str):
            cleaned[key] = re.sub(r'[-_]', ' ', value)
    tags = set(player_tags_from_ctx(cleaned))
    race = ' '.join(re.findall(r'[a-z]+', normalize(cleaned.get('race') or '')))
    if race in _EXTRA_TAGS:
        tags.add(_EXTRA_TAGS[race])
    return frozenset(tags)


def _toc_named_tags(question) -> frozenset:
    text = normalize(re.sub(r'[-_]', ' ', str(question or '')))
    tags = set()
    for phrase, tag in _TAG_WORDS.items():
        pattern = r'(?<![a-z0-9])' + re.escape(phrase) + r'(?:s|es)?(?![a-z0-9])'
        if re.search(pattern, text):
            tags.add(tag)
    return frozenset(tags)


def _section_tags(section) -> frozenset:
    raw = section.get('tags') or []
    if isinstance(raw, str):
        raw = [raw]
    return frozenset(str(tag).upper() for tag in raw if isinstance(tag, str))


def _chapter_order(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0 if value is None else 9999


def _one_line(value) -> str:
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def build_toc(lang, ctx=None, question='') -> list[tuple[str, str]]:
    """Índice compacto de secciones usables, filtrado por clase y raza del jugador."""
    spanish = str(lang).lower().startswith('es')
    allowed = set(_toc_player_tags(ctx)) | set(_toc_named_tags(question))
    sections = list(load_sections())
    fingerprint = tuple(
        (section['id'], section.get('chapter'),
         section.get('title_es'), section.get('title_en'),
         section.get('summary_es'), section.get('summary_en'),
         tuple(sorted(_section_tags(section))))
        for section in sections
    )
    key = (spanish, frozenset(allowed), fingerprint)
    cached = _TOC_CACHE.get(key)
    if cached is not None:
        return list(cached)

    rows = []
    for section in sections:
        tags = _section_tags(section)
        restricted = tags & _KNOWN_TAGS
        if restricted and not restricted <= allowed:
            continue
        title = _one_line(section.get('title_es' if spanish else 'title_en')
                          or section.get('title_es') or section.get('title_en'))
        if not title:
            continue
        summary = _one_line(section.get('summary_es' if spanish else 'summary_en')
                            or section.get('summary_es') or section.get('summary_en'))
        identifier = section['id']
        rows.append((_chapter_order(section.get('chapter')), identifier,
                     f'{identifier} | {title} | {summary}'))
    rows.sort(key=lambda row: (row[0], row[1]))
    lines = tuple((identifier, line) for _chapter, identifier, line in rows)
    _TOC_CACHE[key] = lines
    return list(lines)


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

    def __new__(cls, db, sections_path=None):
        selected_path = (sections_path if sections_path is not None
                         else GUIDE_SECTIONS_PATH)
        key = (id(db), str(selected_path))
        cached = _CACHE.get(key)
        if cached is not None and getattr(cached, 'db', None) is db:
            return cached
        instance = super().__new__(cls)
        _CACHE[key] = instance
        return instance

    def __init__(self, db, sections_path=None):
        if getattr(self, '_ready', False):
            return
        self.db = db
        self.sections_path = Path(sections_path) if sections_path is not None else None
        self._entries = None
        self._section_phrases = {}
        self._status = {}
        self._ready = True
        try:
            setattr(db, '_guide_index', self)
        except Exception:
            pass

    @classmethod
    def for_db(cls, db, sections_path=None):
        return cls(db, sections_path)

    def status(self, ref) -> str:
        """Estado de una sección ('verificado', 'editorial') o '' si no es sección."""
        self.entries
        return self._status.get(ref, '')

    @property
    def entries(self):
        if self._entries is None:
            self._entries = self._load()
        return self._entries

    def _load(self):
        entries = []
        seen_refs = set()
        self._section_phrases = {}
        for section in load_sections(self.sections_path):
            ref = f'section:{section["id"]}'
            if ref in seen_refs:
                continue
            text_es = section['text_es']
            text_en = section['text_en']
            keywords_es = [normalize(value)
                           for value in section.get('keywords_es', [])]
            keywords_en = [normalize(value)
                           for value in section.get('keywords_en', [])]
            keywords_es = [value for value in keywords_es if value]
            keywords_en = [value for value in keywords_en if value]
            token_text_es = ' '.join([text_es] + keywords_es)
            token_text_en = ' '.join([text_en] + keywords_en)
            # Solo las claves de una palabra valen sueltas; las de varias, como frase entera
            # («no muerto paladín» no debe responder a «he muerto»).
            heads = frozenset(tokenize(' '.join(
                value for value in keywords_es + keywords_en if ' ' not in value)))
            tags = frozenset(str(tag).upper() for tag in section.get('tags') or []
                             if isinstance(tag, str))
            entries.append(GuideEntry(
                ref, text_es, text_en,
                frozenset(tokenize(token_text_es)),
                frozenset(tokenize(token_text_en)),
                frozenset(), heads, tags, section['status']))
            self._section_phrases[ref] = frozenset(keywords_es + keywords_en)
            self._status[ref] = section['status']
            seen_refs.add(ref)
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
        rows = [row for row in self.db._rows(
            'SELECT BaseTag, TagText_lang, TagText_lang_esES FROM GlobalStrings') or []
            if _ALLOWED_TAG_RE.match(str(row['BaseTag'] or ''))]
        # El título va aparte del texto («Muerte» / «Ahora eres un fantasma…»): se unen para
        # que la pregunta encuentre el texto por su título.
        titles = {}
        for row in rows:
            match = _TITLE_RE.match(str(row['BaseTag']))
            if match:
                titles['TUTORIAL' + match.group(1)] = (
                    clean_text(row['TagText_lang_esES'] or row['TagText_lang']),
                    clean_text(row['TagText_lang']))
        for row in rows:
            ref = str(row['BaseTag'])
            if ref in seen_refs or _TITLE_RE.match(ref):
                continue
            text_en = clean_text(row['TagText_lang'])
            text_es = clean_text(row['TagText_lang_esES'] or row['TagText_lang'])
            if max(len(text_es), len(text_en)) < MIN_GLOBAL_LENGTH:
                continue
            title_es, title_en = titles.get(ref, ('', ''))
            if title_es and text_es:
                text_es = f'{title_es}: {text_es}'
            if title_en and text_en:
                text_en = f'{title_en}: {text_en}'
            suffix = _SUFFIX_RE.match(ref)
            requires = frozenset(suffix.group(1).split('_')) if suffix else frozenset()
            heads = frozenset(tokenize(title_es)) | frozenset(tokenize(title_en))
            seen_refs.add(ref)
            entries.append(self._entry(ref, text_es, text_en, requires, heads))
        return entries

    @staticmethod
    def _entry(ref, text_es, text_en, requires=frozenset(), heads=frozenset()):
        return GuideEntry(ref, text_es, text_en,
                          frozenset(tokenize(text_es)),
                          frozenset(tokenize(text_en)), requires, heads)

    def search(self, question, lang, limit=3, ctx=None):
        spanish = str(lang).lower().startswith('es')
        player_tags = player_tags_from_ctx(ctx)
        section_player_tags = _toc_player_tags(ctx)
        named_tags = _toc_named_tags(question)
        normalized_question = normalize(question)
        question_tokens = set(tokenize(question))
        if not question_tokens and not normalized_question:
            return []
        single_token = next(iter(question_tokens)) if len(question_tokens) == 1 else ''
        question_tags = {token: RACE_TAGS.get(token) or CLASS_TAGS.get(token)
                         for token in question_tokens}
        ranked = []
        for entry in self.entries:
            text = entry.text_es if spanish else entry.text_en
            if not text:
                continue
            # Los tutoriales de una raza o clase nombran PNJ y facultades de esa raza o clase.
            if entry.requires and not entry.requires <= player_tags:
                continue
            # Las secciones de otra clase o raza solo salen si la pregunta la nombra: a un humano
            # cazador no le sirven las raciales del orco aunque hablen de mascotas.
            if (entry.tags and not entry.tags & section_player_tags
                    and not entry.tags & named_tags):
                continue
            phrases = getattr(self, '_section_phrases', {}).get(entry.ref, ())
            # Frases completas: «rol» no debe coincidir dentro de «controlar».
            phrase_hit = bool(phrases) and any(
                re.search(r'(?<![a-z0-9])' + re.escape(phrase) + r'(?![a-z0-9])',
                          normalized_question)
                for phrase in phrases)
            if not question_tokens and not phrase_hit:
                continue
            entry_tokens = entry.tokens_es if spanish else entry.tokens_en
            # «cazador» cuenta para el tutorial de cazador aunque su texto no lo diga.
            score = sum(1 for token in question_tokens
                        if question_tags[token] in entry.requires
                        or any(_token_match(token, candidate)
                               for candidate in entry_tokens))
            if phrase_hit:
                score += 2
            # Con una sola palabra útil, solo coincidencia exacta o con el título: «muerto»
            # trae el tutorial «Muerte», no los textos de «muertes con honor».
            # En las secciones, una palabra suelta solo vale si es una de sus claves.
            in_text = (single_token in entry_tokens
                       and not entry.ref.startswith('section:'))
            single_hit = (len(question_tokens) == 1 and len(single_token) >= 4
                          and (in_text
                               or any(_token_match(single_token, head)
                                      for head in entry.heads)))
            if score < 2 and not single_hit:
                continue
            # La sección de la clase o raza del jugador gana a las demás, pero solo al ordenar:
            # no debe colar secciones que no superan el umbral por sí mismas.
            if entry.tags & player_tags:
                score += 1
            # Lo verificado para Forever va delante de los textos del cliente al empatar.
            if entry.status == 'verificado':
                priority = 0
            elif entry.ref.startswith(('TUTORIAL', 'NEWBIE_TOOLTIP')):
                priority = 1
            elif entry.status:
                priority = 2
            else:
                priority = 3
            ranked.append((-score, priority, len(text), entry.ref, text))
        ranked.sort()
        return [(ref, text) for _score, _priority, _length, ref, text
                in ranked[:limit]]
