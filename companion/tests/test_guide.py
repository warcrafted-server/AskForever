"""Pruebas del índice de textos oficiales y de su uso en el recuperador."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from askforever.engine import guide as guide_module
from askforever.engine.guide import (GuideIndex, clean_text, load_sections,
                                     tokenize)
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
                   if line.startswith('En el juego:')]
    assert guide_lines
    assert not any('TUTORIAL7' in line for line in guide_lines)
    assert 'guide:TUTORIAL7' in facts.sources


def test_retrieve_adds_english_guide_lines(db):
    facts = retrieve(_message('how do I loot a corpse?', lang='enUS'), db)
    assert any(line.startswith('In game:') for line in facts.lines)
    assert 'guide:TUTORIAL7' in facts.sources


def test_travel_question_does_not_add_guide_lines(db):
    facts = retrieve(_message('¿Cómo voy a Ventormenta?'), db)
    assert not any(line.startswith('En el juego:')
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


DEATH_ES = 'Ahora eres un fantasma. Podrás volver a la vida si encuentras tu cuerpo.'
DEATH_EN = 'You are now a ghost. You can return to life if you find your body.'
PET_HUNTER_ES = ('Ahora tienes una barra de acción de mascota para controlarla y la '
                 'facultad para domesticar bestias.')
PET_HUNTER_EN = 'You now have a pet action bar and the ability to tame beasts.'
PET_WARLOCK_ES = ('Ahora tienes una barra de acción de mascota para controlar mejor a '
                  'tu demonio.')
GREY_ITEMS_ES = ('Los objetos con el nombre en color gris son de calidad inferior y se '
                 'pueden vender.')


@pytest.fixture
def rich_db(db):
    conn = db.conn
    conn.executemany(
        'INSERT INTO GlobalStrings (ID, BaseTag, TagText_lang, TagText_lang_esES, '
        'Flags) VALUES (?, ?, ?, ?, ?)',
        [
            (25, 'TUTORIAL25', DEATH_EN, DEATH_ES, 0),
            (26, 'TUTORIAL_TITLE25', 'Death', 'Muerte', 0),
            (27, 'TUTORIAL61_HUNTER', PET_HUNTER_EN, PET_HUNTER_ES, 0),
            (28, 'TUTORIAL_TITLE61_HUNTER', 'Pet Action Bar', 'Barra de acción de mascota', 0),
            (29, 'TUTORIAL61_WARLOCK', 'You now have a pet action bar for your demon.',
             PET_WARLOCK_ES, 0),
            (30, 'NEWBIE_TOOLTIP_HONORABLE_KILLS',
             'Every honorable kill of a player gives you honor points.',
             'Cada muerte con honor de un jugador te da puntos de honor.', 0),
        ])
    conn.execute('INSERT INTO gametips (ID, Text_lang, Text_lang_esES) VALUES (?, ?, ?)',
                 (223, 'Items with a grey name are of poor quality and can be sold.',
                  GREY_ITEMS_ES))
    conn.commit()
    return db


def test_clean_text_replaces_literal_newlines():
    assert clean_text('Uno.\\nDos.') == 'Uno. Dos.'


def test_tutorial_title_is_joined_and_found(rich_db):
    results = GuideIndex(rich_db).search('He muerto, ¿qué hago?', 'es')
    refs = [ref for ref, _text in results]
    assert refs[0] == 'TUTORIAL25'
    assert dict(results)['TUTORIAL25'].startswith('Muerte: Ahora eres un fantasma')
    assert 'NEWBIE_TOOLTIP_HONORABLE_KILLS' not in refs
    assert not any(ref.startswith('TUTORIAL_TITLE') for ref in refs)


def test_class_tutorial_only_for_that_class(rich_db):
    index = GuideIndex(rich_db)
    question = '¿Cómo consigo una mascota de cazador?'
    hunter = [ref for ref, _text in index.search(
        question, 'es', ctx={'race': 'Humano', 'class': 'Cazador'})]
    assert hunter == ['TUTORIAL61_HUNTER']
    mage = [ref for ref, _text in index.search(
        question, 'es', ctx={'race': 'Humano', 'class': 'Mago'})]
    assert 'TUTORIAL61_HUNTER' not in mage
    assert 'TUTORIAL61_WARLOCK' not in mage
    assert index.search(question, 'es') == []


def test_domain_words_help_general_questions(rich_db):
    results = GuideIndex(rich_db).search('¿Qué significan los colores de los objetos?', 'es')
    assert [ref for ref, _text in results] == ['gametip:223']


def test_retrieve_passes_player_context_to_guide(rich_db):
    ctx = {'race': 'Humano', 'class': 'Cazador', 'fac': 'Alianza', 'lvl': 10}
    facts = retrieve(_message('¿Cómo consigo una mascota de cazador?', ctx=ctx), rich_db)
    assert 'guide:TUTORIAL61_HUNTER' in facts.sources
    assert 'guide:TUTORIAL61_WARLOCK' not in facts.sources


def _section(section_id='nivel-maximo', status='verificado', text_es=None,
             text_en=None):
    return {
        'id': section_id,
        'status': status,
        'keywords_es': ['nivel máximo', 'nivel maximo', 'nivel 60'],
        'keywords_en': ['max level', 'level cap', 'level 60'],
        'text_es': text_es or 'El nivel máximo de WoW Forever es 60.',
        'text_en': text_en or 'The maximum level in WoW Forever is 60.',
        'sources': [{'type': 'cliente', 'ref': 'prueba'}],
        'updated': '2026-11-15',
    }


def _write_sections(path: Path, sections):
    path.write_text(json.dumps({'sections': sections}, ensure_ascii=False,
                               indent=2), encoding='utf-8')


def test_load_sections_only_verified_and_skips_malformed(tmp_path):
    path = tmp_path / 'guide.json'
    _write_sections(path, [
        _section(),
        _section('pendiente', 'pendiente'),
        {'id': 'sin-texto', 'status': 'verificado', 'text_es': '',
         'text_en': 'Text', 'keywords_es': [], 'keywords_en': []},
        {'id': 'keywords-mal', 'status': 'verificado', 'text_es': 'Uno',
         'text_en': 'One', 'keywords_es': 'nivel', 'keywords_en': []},
    ])
    sections = load_sections(path)
    assert [section['id'] for section in sections] == ['nivel-maximo']
    assert load_sections(tmp_path / 'missing.json') == []
    path.write_text('{no json', encoding='utf-8')
    assert load_sections(path) == []


def test_verified_sections_are_found_in_both_languages(tmp_path, db):
    path = tmp_path / 'guide.json'
    _write_sections(path, [_section(), _section('pendiente', 'pendiente')])
    index = GuideIndex(db, sections_path=path)
    try:
        spanish = index.search('¿Cuál es el nivel máximo en WoW Forever?', 'es')
        assert spanish[0] == (
            'section:nivel-maximo', 'El nivel máximo de WoW Forever es 60.')
        english = index.search('What is the level cap?', 'en')
        assert english[0] == (
            'section:nivel-maximo', 'The maximum level in WoW Forever is 60.')
        # Las claves de varias palabras solo valen como frase completa.
        assert not any(ref.startswith('section:')
                       for ref, _text in index.search('máximo', 'es'))
        assert index.search('¿nivel máximo?', 'es')[0][0] == 'section:nivel-maximo'
        assert index.search('nivel 60', 'es')[0][0] == 'section:nivel-maximo'
        assert not any(ref.startswith('section:pendiente')
                       for ref, _text in index.search('nivel máximo', 'es',
                                                      limit=20))
    finally:
        guide_module._CACHE.clear()


def test_malformed_sections_do_not_crash(tmp_path, db):
    path = tmp_path / 'guide.json'
    path.write_text('[', encoding='utf-8')
    index = GuideIndex(db, sections_path=path)
    try:
        assert load_sections(path) == []
        assert index.search('¿Cuál es el nivel máximo?', 'es') == []
    finally:
        guide_module._CACHE.clear()


def test_retrieve_uses_verified_section(monkeypatch, tmp_path, db):
    path = tmp_path / 'guide.json'
    _write_sections(path, [_section()])
    monkeypatch.setattr(guide_module, 'GUIDE_SECTIONS_PATH', path)
    guide_module._CACHE.clear()
    facts = retrieve(_message('¿Cuál es el nivel máximo en WoW Forever?'), db)
    assert ('En WoW Forever: '
            'El nivel máximo de WoW Forever es 60.') in facts.lines
    assert 'guide:section:nivel-maximo' in facts.sources


def test_real_guide_json_loads_verified_max_level():
    sections = load_sections()
    max_level = next(section for section in sections
                     if section['id'] == 'nivel-maximo')
    assert max_level['status'] == 'verificado'
    assert '60' in max_level['text_es']
    assert '60' in max_level['text_en']


def test_editorial_sections_from_folder_are_used_with_their_label(tmp_path, db):
    folder = tmp_path / 'guide'
    folder.mkdir()
    editorial = _section('monturas', 'editorial', 'Las monturas se aprenden a nivel 40.',
                         'Riding is learned at level 40.')
    editorial['keywords_es'] = ['montura', 'monturas']
    editorial['keywords_en'] = ['mount', 'riding']
    hunter = _section('mascotas-cazador', 'editorial', 'Las mascotas del cazador comen.',
                      'Hunter pets eat.')
    hunter['keywords_es'] = ['mascota']
    hunter['keywords_en'] = ['pet']
    hunter['tags'] = ['hunter']
    warlock = _section('demonios-brujo', 'editorial', 'Los demonios del brujo no comen.',
                       'Warlock demons do not eat.')
    warlock['keywords_es'] = ['mascota']
    warlock['keywords_en'] = ['pet']
    warlock['tags'] = ['warlock']
    _write_sections(folder / '09-viajes.json', [editorial])
    _write_sections(folder / '04-clases.json', [hunter, warlock])
    index = GuideIndex(db, sections_path=folder)
    try:
        assert index.search('¿A qué nivel tengo montura?', 'es')[0][0] == 'section:monturas'
        assert index.status('section:monturas') == 'editorial'
        hunter_hits = index.search('¿Qué come mi mascota?', 'es',
                                   ctx={'race': 'Humano', 'class': 'Cazador'})
        assert hunter_hits[0][0] == 'section:mascotas-cazador'
        warlock_hits = index.search('¿Qué come mi mascota?', 'es',
                                    ctx={'race': 'Humano', 'class': 'Brujo'})
        assert warlock_hits[0][0] == 'section:demonios-brujo'
    finally:
        guide_module._CACHE.clear()


def test_verified_section_wins_over_editorial_with_same_id(tmp_path, monkeypatch):
    main = tmp_path / 'guide.json'
    folder = tmp_path / 'guide'
    folder.mkdir()
    _write_sections(main, [_section()])
    _write_sections(folder / '01.json', [
        _section('nivel-maximo', 'editorial', 'Otro texto.', 'Other text.'),
        _section('otra', 'editorial'),
        _section('borrador', 'pendiente'),
    ])
    monkeypatch.setattr(guide_module, 'GUIDE_SECTIONS_PATH', main)
    monkeypatch.setattr(guide_module, 'GUIDE_SECTIONS_DIR', folder)
    sections = guide_module.load_sections()
    assert [(item['id'], item['status']) for item in sections] == [
        ('nivel-maximo', 'verificado'), ('otra', 'editorial')]


def test_other_race_sections_only_when_named(tmp_path, db):
    path = tmp_path / 'guide.json'
    orc = _section('raza-orco-raciales', 'editorial', 'Ordenar mejora el daño de las mascotas.',
                   'Command increases pet damage.')
    orc['keywords_es'] = ['mascotas', 'raciales orco']
    orc['keywords_en'] = ['pets', 'orc racials']
    orc['tags'] = ['ORC']
    _write_sections(path, [orc])
    index = GuideIndex(db, sections_path=path)
    try:
        human = {'race': 'Humano', 'class': 'Cazador'}
        assert index.search('¿qué daño hacen las mascotas?', 'es', ctx=human) == []
        named = index.search('¿qué raciales tienen los orcos para las mascotas?', 'es', ctx=human)
        assert named and named[0][0] == 'section:raza-orco-raciales'
    finally:
        guide_module._CACHE.clear()
