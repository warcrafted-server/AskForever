"""Pruebas del recuperador de datos verificados (batería b03-b19)."""

from __future__ import annotations

import sqlite3

import pytest

from askforever.data.wowdb import WowDb
from askforever.engine.retriever import Facts, retrieve

SCHEMA = [
    'CREATE TABLE ext_quests (quest_id INTEGER, required_level INTEGER, quest_level INTEGER)',
    'CREATE TABLE ext_quest_l10n (quest_id INTEGER, locale TEXT, name TEXT)',
    'CREATE TABLE ext_quest_starters (quest_id INTEGER, entity_type TEXT, entity_id INTEGER)',
    'CREATE TABLE ext_quest_finishers (quest_id INTEGER, entity_type TEXT, entity_id INTEGER)',
    'CREATE TABLE ext_quest_objective_items (quest_id INTEGER, position INTEGER, '
    'item_id INTEGER, text TEXT, icon_type INTEGER)',
    'CREATE TABLE ext_npcs (npc_id INTEGER, min_level INTEGER, max_level INTEGER, '
    'friendly_to_faction TEXT)',
    'CREATE TABLE ext_npc_l10n (npc_id INTEGER, locale TEXT, name TEXT, sub_name TEXT)',
    'CREATE TABLE ext_npc_spawns (npc_id INTEGER, zone_id INTEGER, spawn_idx INTEGER, '
    'x REAL, y REAL)',
    'CREATE TABLE ext_zones (group_id INTEGER, area_id INTEGER, name_enUS TEXT, '
    'name_esES TEXT)',
    'CREATE TABLE ext_dungeons (area_id INTEGER, name_enUS TEXT, name_esES TEXT, '
    'parent_zone_id INTEGER)',
    'CREATE TABLE ext_dungeon_entrances (area_id INTEGER, idx INTEGER, zone_id INTEGER, '
    'x REAL, y REAL)',
    'CREATE TABLE v_hechizos_instructor (ClassMask INTEGER, Name_enUS TEXT, '
    'Name_esES TEXT, Level INTEGER)',
    'CREATE TABLE TalentTab (__id INTEGER, Name_lang TEXT, OrderIndex INTEGER, '
    'ClassMask INTEGER, Name_lang_esES TEXT)',
    'CREATE TABLE TaxiNodes (__id INTEGER, Name_lang TEXT, ContinentID INTEGER, '
    'MountCreatureID TEXT, Name_lang_esES TEXT)',
    'CREATE TABLE ext_item_l10n (item_id INTEGER, locale TEXT, name TEXT)',
]

CTX = {'lvl': 16, 'race': 'Enano', 'class': 'Chamán', 'fac': 'Alianza', 'zone': 'Forjaz'}


def _insert(conn, table, columns, rows):
    placeholders = ', '.join('?' for _ in columns)
    conn.executemany(f'INSERT INTO {table} ({", ".join(columns)}) VALUES ({placeholders})', rows)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'wow.sqlite'
    conn = sqlite3.connect(path)
    for statement in SCHEMA:
        conn.execute(statement)

    _insert(conn, 'ext_quests', ['quest_id', 'required_level', 'quest_level'], [
        (1338, 9, 14),
        (96393, 9, 16),
        (267, 10, 12),
    ])
    _insert(conn, 'ext_quest_l10n', ['quest_id', 'locale', 'name'], [
        (1338, 'esES', 'Un pedido de Pico Tormenta'),
        (1338, 'enUS', 'A Request from Ironforge'),
        (96393, 'esES', 'Incursión en la Antigua Forjaz'),
        (96393, 'enUS', 'Old Ironforge Incursion'),
        (267, 'esES', 'La amenaza trogg'),
        (267, 'enUS', 'The Trogg Threat'),
    ])
    _insert(conn, 'ext_quest_starters', ['quest_id', 'entity_type', 'entity_id'], [
        (1338, 'npc', 1343),
        (96393, 'npc', 264936),
        (267, 'npc', 1092),
    ])
    _insert(conn, 'ext_quest_finishers', ['quest_id', 'entity_type', 'entity_id'], [
        (1338, 'npc', 5413),
        (96393, 'npc', 2784),
        (267, 'npc', 1092),
    ])
    _insert(conn, 'ext_npcs', ['npc_id', 'min_level', 'max_level', 'friendly_to_faction'], [
        (1092, 40, 40, 'A'),
        (1343, 10, 10, 'A'),
        (5413, 30, 30, 'A'),
        (264936, 13, 13, 'A'),
        (2784, 63, 63, 'A'),
        (4991, 60, 60, 'A'),
        (258098, 60, 60, 'A'),
        (7000, 60, 60, 'H'),
    ])
    _insert(conn, 'ext_npc_l10n', ['npc_id', 'locale', 'name', 'sub_name'], [
        (1092, 'esES', 'Capitán Rugelfuss', None),
        (1343, 'esES', 'Montaraz Pico Tormenta', None),
        (5413, 'esES', 'Furen Barbalarga', None),
        (264936, 'esES', 'Videnterra Farsen', None),
        (2784, 'esES', 'Rey Magni Barbabronce', 'Señor\u00a0de\u00a0Forjaz'),
        (2784, 'enUS', 'King Magni Bronzebeard', 'Lord of Ironforge'),
        (4991, 'enUS', 'World Shaman Trainer', 'Shaman Trainer'),
        (4991, 'esES', 'World Shaman Trainer', 'Instructor\u00a0de\u00a0chamanes'),
        (258098, 'enUS', 'Eldrun Rompetormentas', 'Shaman Trainer'),
        (258098, 'esES', 'Eldrun Rompetormentas', ''),
        (7000, 'esES', 'Haromm', 'Instructor\u00a0de\u00a0chamanes'),
        (7000, 'enUS', 'Haromm', 'Shaman Trainer'),
    ])
    _insert(conn, 'ext_npc_spawns', ['npc_id', 'zone_id', 'spawn_idx', 'x', 'y'], [
        (1092, 38, 1, 23.23, 73.68),
        (1343, 38, 1, 24.8, 18.4),
        (5413, 1519, 1, 64.6, 37.2),
        (264936, 1, 1, 64.87, 58.47),
        (2784, 1537, 1, 39.09, 56.2),
        (258098, 1537, 1, 47.1, 13.8),
        (7000, 1637, 1, 10.0, 20.0),
    ])
    _insert(conn, 'ext_zones', ['group_id', 'area_id', 'name_enUS', 'name_esES'], [
        (0, 1, 'Dun Morogh', 'Dun Morogh'),
        (0, 38, 'Loch Modan', 'Loch Modan'),
        (0, 40, 'Westfall', 'Páramos de Poniente'),
        (0, 1519, 'Stormwind City', 'Ciudad de Ventormenta'),
        (0, 1537, 'Ironforge', 'Forjaz'),
        (1, 14, 'Durotar', 'Durotar'),
        (1, 1637, 'Orgrimmar', 'Orgrimmar'),
    ])
    _insert(conn, 'ext_dungeons', ['area_id', 'name_enUS', 'name_esES', 'parent_zone_id'], [
        (1581, 'The Deadmines', 'Las Minas de la Muerte', 40),
        (721, 'Gnomeregan', 'Gnomeregan', 1),
    ])
    _insert(conn, 'ext_dungeon_entrances', ['area_id', 'idx', 'zone_id', 'x', 'y'], [
        (1581, 1, 40, 42.5, 71.7),
        (721, 1, 1, 24.3, 39.8),
    ])
    _insert(conn, 'v_hechizos_instructor', ['ClassMask', 'Name_enUS', 'Name_esES', 'Level'], [
        (64, 'Lightning Shield', 'Escudo de relámpagos', 16),
        (64, 'Rockbiter Weapon', 'Arma comerrocas', 17),
        (64, 'Flametongue Weapon', 'Arma lengua de Fuego', 18),
        (64, 'Healing Wave', 'Onda de curación', 18),
        (64, 'Tremor Totem', 'Tótem de tremor', 18),
        (64, 'Stoneclaw Totem', 'Tótem Garra de piedra', 18),
        (64, 'Flame Shock', 'Choque de llamas', 18),
        (64, 'Ghost Wolf', 'Lobo fantasmal', 20),
        (64, 'Frost Shock', 'Choque de Escarcha', 20),
    ])
    _insert(conn, 'TalentTab', ['__id', 'Name_lang', 'OrderIndex', 'ClassMask',
                                'Name_lang_esES'], [
        (261, 'Elemental', 0, 64, 'Elemental'),
        (263, 'Enhancement', 1, 64, 'Mejora'),
        (262, 'Restoration', 2, 64, 'Recuperación'),
    ])
    _insert(conn, 'TaxiNodes', ['__id', 'Name_lang', 'ContinentID', 'MountCreatureID',
                                'Name_lang_esES'], [
        (6, 'Ironforge, Dun Morogh', 0, '[0, 541]', 'Forjaz, Dun Morogh'),
        (7, 'Menethil Harbor, Wetlands', 0, '[0, 541]', 'Puerto de Menethil, Los Humedales'),
        (8, 'Thelsamar, Loch Modan', 0, '[0, 541]', 'Thelsamar, Loch Modan'),
        (50, 'The Sepulcher, Silverpine Forest', 0, '[3574, 0]', 'Sepulcro, Bosque de Argénteos'),
        (23, 'Orgrimmar, Durotar', 1, '[2224, 0]', 'Orgrimmar, Durotar'),
        (34, 'Transport, Menethil Ships', 0, '[0, 0]', 'Transporte, Barcos de Menethil'),
        (99, 'zzOLDRiverglades', 0, '[0, 541]', 'zzOLDRiverglades'),
    ])
    _insert(conn, 'ext_item_l10n', ['item_id', 'locale', 'name'], [])
    conn.commit()
    conn.close()

    database = WowDb(path)
    yield database
    database.close()


def _message(question, lang='esES', ctx=None):
    return {'v': 1, 'lang': lang, 'q': question, 'ctx': dict(ctx or CTX)}


TALENT_SCHEMA = [
    'CREATE TABLE ext_quests (quest_id INTEGER, required_level INTEGER, quest_level INTEGER)',
    'CREATE TABLE ext_wh_build (build_id TEXT, clase TEXT, espec TEXT, titulo TEXT, '
    'puntos_total INTEGER, puntos_ramas TEXT, enlace TEXT, variante TEXT, '
    'orden_en_seccion INTEGER, guide_key TEXT, section_hash TEXT)',
    'CREATE TABLE ext_wh_talento_orden (build_id TEXT, nivel INTEGER, talento_en TEXT, '
    'talento_es TEXT, node_id INTEGER, rango INTEGER, guide_key TEXT, section_hash TEXT)',
    'CREATE TABLE ext_wh_habilidad_nivel (clase TEXT, nivel INTEGER, hechizo TEXT, '
    'hechizo_es TEXT, spell_id INTEGER, rango TEXT, tipo TEXT, guide_key TEXT, '
    'section_hash TEXT)',
]


@pytest.fixture
def talent_db(tmp_path):
    path = tmp_path / 'talent.sqlite'
    conn = sqlite3.connect(path)
    for statement in TALENT_SCHEMA:
        conn.execute(statement)
    _insert(conn, 'ext_wh_build', ['build_id', 'clase', 'espec', 'titulo',
                                   'puntos_total', 'puntos_ramas', 'enlace', 'variante',
                                   'orden_en_seccion', 'guide_key', 'section_hash'], [
        ('b1', 'shaman', 'elemental', 'Guía Elemental', 5, '{}', 'u1', 'Variante A', 1,
         'g', 'h'),
        ('b2', 'shaman', 'restauracion', 'Guía Restauración', 4, '{}', 'u2',
         'Variante B', 2, 'g', 'h'),
    ])
    _insert(conn, 'ext_wh_talento_orden',
            ['build_id', 'nivel', 'talento_en', 'talento_es', 'node_id', 'rango',
             'guide_key', 'section_hash'], [
        ('b1', 10, 'Convection', 'Convección', 1, 1, 'g', 'h'),
        ('b1', 11, 'Convection', 'Convección', 1, 2, 'g', 'h'),
        ('b1', 12, 'Call of Thunder', 'Llamada del trueno', 2, 1, 'g', 'h'),
        ('b1', 13, 'Convection', 'Convección', 1, 3, 'g', 'h'),
        ('b1', 14, 'Call of Thunder', 'Llamada del trueno', 2, 2, 'g', 'h'),
        ('b1', 34, 'Elemental Mastery', 'Maestría elemental', 3, 1, 'g', 'h'),
        ('b2', 10, 'Improved Healing Wave', 'Onda de curación mejorada', 4, 1, 'g', 'h'),
        ('b2', 11, 'Improved Healing Wave', 'Onda de curación mejorada', 4, 2, 'g', 'h'),
        ('b2', 12, 'Tidal Focus', 'Enfoque de las mareas', 5, 1, 'g', 'h'),
    ])
    _insert(conn, 'ext_wh_habilidad_nivel',
            ['clase', 'nivel', 'hechizo', 'hechizo_es', 'spell_id', 'rango', 'tipo',
             'guide_key', 'section_hash'], [
        ('shaman', 20, 'Ghost Wolf', 'Lobo fantasmal', 2645, None, None, 'g', 'h'),
        ('shaman', 20, 'Water Walking', 'Caminar sobre el agua', 546, None, None, 'g', 'h'),
        ('shaman', 20, 'Stormstrike', 'Golpe de tormenta', 17364, 'Rank 1', None, 'g', 'h'),
        ('shaman', 20, None, None, None, None, None, 'g', 'h'),
        ('shaman', 18, 'Flame Shock', 'Choque de llamas', 8050, None, None, 'g', 'h'),
    ])
    conn.commit()
    conn.close()

    database = WowDb(path)
    yield database
    database.close()


def _talent_ctx(spent=None, level=16):
    ctx = dict(CTX)
    ctx['lvl'] = level
    if spent is not None:
        ctx['pf'] = {'tal': {'list': spent, 'free': 1}}
    return ctx


def _text(facts):
    return '\n'.join(facts.lines)


def test_b03_turn_in_furen(db):
    facts = retrieve(_message('¿Dónde entrego Un pedido de Pico Tormenta?'), db)
    text = _text(facts)
    assert 'Furen Barbalarga' in text
    assert 'Ciudad de Ventormenta (64.6, 37.2)' in text
    assert 'Montaraz Pico Tormenta' in text
    assert 'quest:1338' in facts.sources


def test_b04_old_ironforge_incursion(db):
    facts = retrieve(_message(
        '¿Quién da la misión Incursión en la Antigua Forjaz y dónde la entrego?'), db)
    text = _text(facts)
    assert 'Videnterra Farsen' in text
    assert 'Rey Magni Barbabronce' in text
    assert 'Forjaz (39.1, 56.2)' in text


def test_b06_magni_in_forjaz(db):
    facts = retrieve(_message('¿Dónde está el Rey Magni Barbabronce?'), db)
    text = _text(facts)
    assert 'PNJ Rey Magni Barbabronce (Señor de Forjaz)' in text
    assert 'Forjaz (39.1, 56.2)' in text


def test_b07_spells_at_level_18(db):
    facts = retrieve(_message('¿Qué hechizos nuevos aprendo a nivel 18?'), db)
    text = _text(facts)
    assert 'nivel 18' in text
    assert 'Arma lengua de Fuego' in text
    assert 'Onda de curación' in text
    assert 'spells:64:18' in facts.sources


def test_spells_next_level(db):
    facts = retrieve(_message('¿Qué hechizos aprendo al siguiente nivel?'), db)
    text = _text(facts)
    assert 'nivel 17' in text
    assert 'Arma comerrocas' in text


def test_b09_trainer_in_forjaz(db):
    facts = retrieve(_message('¿Dónde está el instructor de chamanes en Forjaz?'), db)
    assert facts.lines
    assert 'Eldrun Rompetormentas' in facts.lines[0]
    assert 'Forjaz (47.1, 13.8)' in facts.lines[0]
    text = _text(facts)
    assert 'World Shaman Trainer' not in text
    assert 'Haromm' not in text
    assert 'trainers:64:A' in facts.sources


def test_b10_talent_trees(db):
    facts = retrieve(_message('¿Qué ramas de talentos tiene el chamán?'), db)
    text = _text(facts)
    assert 'Elemental' in text
    assert 'Mejora' in text
    assert 'Recuperación' in text
    assert 'talents:64' in facts.sources


def test_talent_path_next_point(talent_db):
    facts = retrieve(_message('¿Dónde gasto el siguiente punto de talento?',
                              ctx=_talent_ctx([['Convección', 1]], level=12)), talent_db)
    text = _text(facts)
    assert 'Guía Elemental' in text
    assert 'nivel 12' in text and '3 puntos esperados' in text
    assert 'Siguientes puntos' in text
    assert 'Convección' in text and 'Llamada del trueno' in text
    assert 'talents:path' in facts.sources


def test_talent_path_without_spent_lists_builds(talent_db):
    facts = retrieve(_message('¿Dónde gasto el siguiente punto de talento?',
                              ctx=_talent_ctx()), talent_db)
    text = _text(facts)
    assert 'Variante A' in text and 'Variante B' in text
    assert 'Elige una de estas builds' in text
    assert 'Siguientes puntos' not in text
    assert 'talents:path' in facts.sources


def test_talent_path_level_from_question(talent_db):
    facts = retrieve(_message('¿Qué talentos debería tener a nivel 34?',
                              ctx=_talent_ctx([['Convección', 2]], level=12)), talent_db)
    text = _text(facts)
    assert 'nivel 34' in text
    assert '25 puntos esperados' in text
    assert 'Siguientes puntos' in text


def test_talent_path_off_route_has_no_steps(talent_db):
    facts = retrieve(_message('¿Dónde gasto el siguiente punto de talento?',
                              ctx=_talent_ctx([['Convección', 1],
                                               ['Talento inventado', 1]], level=12)),
                     talent_db)
    text = _text(facts)
    assert 'no sigue esta build' in text
    assert 'Siguientes puntos' not in text


def test_talent_path_english(talent_db):
    facts = retrieve(_message('Next talent point at level 34?', lang='enUS',
                              ctx=_talent_ctx([['Convección', 2]], level=12)), talent_db)
    text = _text(facts)
    assert 'at level 34' in text and '25 points expected' in text
    assert 'Next points' in text


def test_abilities_at_level(talent_db):
    facts = retrieve(_message('¿Qué aprendo a nivel 20?'), talent_db)
    text = _text(facts)
    assert 'Lobo fantasmal' in text
    assert 'Caminar sobre el agua' in text
    assert 'Golpe de tormenta (Rank 1)' in text
    assert 'Choque de llamas' not in text
    assert 'Ninguno nuevo a nivel 20' not in text
    assert 'abilities:64:20' in facts.sources


def test_b11_dungeon_spanish(db):
    facts = retrieve(_message('¿Dónde está la entrada de Las Minas de la Muerte?'), db)
    text = _text(facts)
    assert 'Mazmorra «Las Minas de la Muerte»' in text
    assert 'Páramos de Poniente (42.5, 71.7)' in text
    assert 'dungeon:1581' in facts.sources


def test_b19_dungeon_english(db):
    facts = retrieve(_message('Where is the entrance to the Deadmines?', lang='enUS'), db)
    text = _text(facts)
    assert 'Dungeon "The Deadmines": entrance in Westfall (42.5, 71.7), levels 17-26.' in text
    rendered = facts.render('enUS')
    assert rendered.startswith('VERIFIED DATA (WoW Forever database):')
    assert 'Mazmorra' not in rendered


def test_b13_dungeon_level_ranges(db):
    facts = retrieve(_message('¿A qué nivel puedo hacer Las Minas de la Muerte?'), db)
    assert any('Mazmorra «Las Minas de la Muerte»' in line for line in facts.lines)
    assert any('niveles 17-26' in line for line in facts.lines)
    assert 'rangos de nivel de mazmorras' not in facts.missing


def test_b14_flight_points(db):
    facts = retrieve(_message('¿Qué puntos de vuelo hay cerca de mí?'), db)
    line = next(line for line in facts.lines if line.startswith('Puntos de vuelo'))
    names = line.split(': ', 1)[1].split('; ')
    assert names[0] == 'Forjaz'
    assert 'Thelsamar, Loch Modan' in names
    assert 'Puerto de Menethil, Los Humedales' in names
    assert not any('Transporte' in name for name in names)
    assert not any(name.startswith('zz') for name in names)
    assert not any('Sepulcro' in name for name in names)
    assert 'flights:0:A' in facts.sources


def test_b17_unknown_npc_has_no_facts(db):
    ctx = dict(CTX)
    del ctx['lvl']
    facts = retrieve(_message('¿Dónde encuentro al PNJ Gruznik el Brillante?', ctx=ctx), db)
    assert facts.lines == []
    assert facts.missing == []
    assert facts.render('esES') == ''


def test_b18_experience_missing(db):
    facts = retrieve(_message('¿Cuánta experiencia necesito exactamente para el nivel 17?'), db)
    assert 'experiencia necesaria por nivel' in facts.missing
    rendered = facts.render('esES')
    assert 'SIN DATOS EN LA BASE:' in rendered
    assert 'experiencia necesaria por nivel' in rendered


def test_quest_list(db):
    ctx = dict(CTX)
    ctx['quests'] = [['Un pedido de Pico Tormenta', 14, 0], ['Misión inventada', 10, 0]]
    facts = retrieve(_message('¿Qué misión de mi lista debería hacer primero?', ctx=ctx), db)
    assert len(facts.lines) == 2
    assert 'la da Montaraz Pico Tormenta' in facts.lines[0]
    assert 'sin datos en la base' in facts.lines[1]


def test_render_limit_and_titles():
    facts = Facts(lines=['x' * 2000], missing=['y' * 100])
    rendered = facts.render('esES')
    assert len(rendered) <= 1600
    assert rendered.endswith('…')
    assert rendered.startswith('DATOS VERIFICADOS (base de WoW Forever):')

    english = Facts(lines=['one line'])
    assert english.render('enUS') == 'VERIFIED DATA (WoW Forever database):\none line'
    assert Facts().render('esES') == ''


def test_render_uses_longer_limit_for_guide_lines():
    guide = Facts(lines=['In WoW Forever: ' + 'x' * 4000])
    rendered = guide.render('enUS')
    assert len(rendered) <= 3200
    assert rendered.endswith('…')

    ordinary = Facts(lines=['x' * 4000])
    assert len(ordinary.render('enUS')) <= 1600


def test_retrieve_without_database(tmp_path):
    assert retrieve(_message('hola'), None).lines == []
    missing = WowDb(tmp_path / 'no.sqlite')
    assert retrieve(_message('hola'), missing).lines == []
    missing.close()


def test_retrieve_with_weird_context(db):
    message = _message('¿Qué hechizos aprendo?', ctx={'lvl': 'texto', 'class': 'Chamán'})
    facts = retrieve(message, db)
    assert 'nivel del personaje' in facts.missing

    broken = {'v': 1, 'lang': 'esES', 'q': 'hola', 'ctx': 'no es un dict'}
    assert retrieve(broken, db).lines == []
    assert retrieve('no es un mensaje', db).lines == []


def test_zone_continent(db):
    assert db.zone_continent('Forjaz') == 0
    assert db.zone_continent('Ironforge') == 0
    assert db.zone_continent('Orgrimmar') == 1
    assert db.zone_continent('Desconocida') is None
