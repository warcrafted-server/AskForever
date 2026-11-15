"""Pruebas del índice de textos oficiales y de su uso en el recuperador."""

from __future__ import annotations

import sqlite3

import pytest

from askforever.engine.guide import GuideIndex, clean_text, tokenize
from askforever.engine.retriever import Facts, _detect_guide, retrieve

TUTORIAL7_ES = (
    '|cffffd100Consejo:|r Si derrotas a un enemigo y ves que su cuerpo brilla, '
    'quiere decir que tiene botín.|n|nHaz |cffffd200clic derecho|r en el cadáver '
    'de una criatura para despojarlo.'
)
TUTORIAL7_EN = (
    '|cffffd100Tip:|r If you defeat an enemy and see its body sparkle, it has '
    'loot.|n|nRight-click the corpse of a creature to loot it.'
)
SPELLBOOK_ES = (
    '|cffffd100Consejo:|r Para preparar un hechizo o facultad, abre la ventana '
    'del libro de hechizos y arrastra el icono a la barra de acción.'
)
SPELLBOOK_EN = (
    '|cffffd100Tip:|r To prepare a spell or ability, open the spellbook window '
    'and drag the icon to your action bar.'
)
GAMETIP_ES = (
    '|cffffd100Consejo:|r Puedes cancelar el lanzamiento de un hechizo '
    'moviéndote, saltando o pulsando la tecla Escape.'
)
GAMETIP_EN = (
    '|cffffd100Tip:|r You can cancel the casting of a spell by moving, jumping '
    'or pressing the Escape key.'
)


class GuideDb:
    def __init__(self, conn):
        self.conn = conn

    def _rows(self, sql, params=()):
        try:
            return self.conn.execute(sql, params).fetchall()
        except sqlite3.Error:
            return []

    def available(self):
        return True

    def match_entities(self, *_args, **_kwargs):
        return []

    def zones_for_level(self, *_args, **_kwargs):
        return []

    def find_quest(self, *_args, **_kwargs):
        return None

    def xp_to_next_level(self, *_args, **_kwargs):
        return None

    def dungeons_for_level(self, *_args, **_kwargs):
        return []

    def zone_continent(self, *_args, **_kwargs):
        return None

    def flight_points(self, *_args, **_kwargs):
        return []


@pytest.fixture
def db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE gametips (ID INTEGER, Text_lang TEXT, '
                 'Text_lang_esES TEXT)')
    conn.execute('CREATE TABLE GlobalStrings (ID INTEGER, BaseTag TEXT, '
                 'TagText_lang TEXT, TagText_lang_esES TEXT, Flags INTEGER)')
    conn.executemany(
        'INSERT INTO gametips (ID, Text_lang, Text_lang_esES) VALUES (?, ?, ?)',
        [
            (201, GAMETIP_EN, GAMETIP_ES),
            (202, 'Enemy loot is highlighted in the world.', 'El botín enemigo se ve.'),
        ])
    conn.executemany(
        'INSERT INTO GlobalStrings (ID, BaseTag, TagText_lang, TagText_lang_esES, '
        'Flags) VALUES (?, ?, ?, ?, ?)',
        [
            (7, 'TUTORIAL7', TUTORIAL7_EN, TUTORIAL7_ES, 0),
            (8, 'TUTORIAL8', 'Enemy loot and despawning are explained here.',
             'El botín enemigo y el despojo se explican aquí.', 0),
            (9, 'TUTORIAL9', 'Enemy loot can be collected from a corpse.',
             'El botín enemigo se recoge de un cadáver.', 0),
            (10, 'NEWBIE_TOOLTIP_SPELLBOOK', SPELLBOOK_EN, SPELLBOOK_ES, 0),
            (11, 'OPTION_TOOLTIP_TEST', 'Enemy loot despawning spellbook option.',
             'Botín enemigo despojo libro de hechizos opción.', 0),
        ])
    conn.commit()
    yield GuideDb(conn)
    conn.close()


def _message(question, lang='esES', ctx=None):
    return {'v': 1, 'lang': lang, 'q': question, 'ctx': dict(ctx or {})}


def test_clean_text_removes_colours_lines_and_tip_label():
    text = clean_text(TUTORIAL7_ES)
    assert '|c' not in text
    assert '|r' not in text
    assert '|n' not in text
    assert not text.startswith('Consejo:')
    assert 'clic derecho' in text
    assert 'despojarlo' in text


def test_tokenizer_discards_short_and_stop_words():
    tokens = tokenize('¿Cómo puedo hacer esto para el personaje?')
    assert tokens == ['esto']


def test_search_finds_spanish_tutorial(db):
    index = GuideIndex(db)
    results = index.search('¿cómo despojo a un enemigo?', 'es')
    refs = [ref for ref, _text in results]
    assert 'TUTORIAL7' in refs
    text = dict(results)['TUTORIAL7']
    assert 'despojarlo' in text
    assert 'Consejo:' not in text
    assert '|c' not in text


def test_search_uses_english_column(db):
    index = GuideIndex(db)
    results = index.search('how do I loot a corpse?', 'en')
    assert results
    assert any(ref == 'TUTORIAL7' for ref, _text in results)
    text = dict(results)['TUTORIAL7']
    assert 'Right-click the corpse' in text
    assert 'Consejo:' not in text


def test_search_never_returns_other_globalstrings(db):
    index = GuideIndex(db)
    refs = [ref for ref, _text in index.search('despojo enemigo', 'es', limit=10)]
    assert 'OPTION_TOOLTIP_TEST' not in refs


def test_search_ignores_unrelated_question(db):
    index = GuideIndex(db)
    assert index.search('hola', 'es') == []


def test_search_limit_and_tutorial_priority(db):
    index = GuideIndex(db)
    results = index.search('botín enemigo despojo', 'es', limit=3)
    assert len(results) == 3
    assert all(ref.startswith('TUTORIAL') for ref, _text in results)


def test_index_is_cached_per_database(db):
    assert GuideIndex(db) is GuideIndex.for_db(db)


def test_retrieve_adds_guide_lines(db):
    facts = retrieve(_message('¿cómo despojo a un enemigo?'), db)
    guide_lines = [line for line in facts.lines
                   if line.startswith('Texto oficial del juego:')]
    assert guide_lines
    assert not any('TUTORIAL7' in line for line in guide_lines)
    assert 'guide:TUTORIAL7' in facts.sources


def test_retrieve_adds_english_guide_lines(db):
    facts = retrieve(_message('how do I loot a corpse?', lang='enUS'), db)
    assert any(line.startswith('Official game text:') for line in facts.lines)
    assert 'guide:TUTORIAL7' in facts.sources


def test_travel_question_does_not_add_guide_lines(db):
    facts = retrieve(_message('¿Cómo voy a Ventormenta?'), db)
    assert not any(line.startswith('Texto oficial del juego:')
                   for line in facts.lines)
    assert not any(source.startswith('guide:') for source in facts.sources)


def test_specific_facts_do_not_add_guide_lines(db):
    for source in ('quest:1', 'dungeons:16', 'route:A>B'):
        facts = Facts(sources=[source])
        _detect_guide(facts, db, 'despojo enemigo', 'es', {})
        assert facts.lines == []

    facts = Facts(lines=['Misión «Una prueba» (nivel 10)'])
    _detect_guide(facts, db, 'despojo enemigo', 'es', {})
    assert facts.lines == ['Misión «Una prueba» (nivel 10)']
