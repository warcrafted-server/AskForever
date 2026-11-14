"""Pruebas del recuperador ampliado: niveles, jefes, XP, vuelos y rutas."""

from __future__ import annotations

import sqlite3

import pytest

from askforever.data.wowdb import WowDb
from askforever.engine.retriever import retrieve

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
    'CREATE TABLE TaxiNodes (__id INTEGER, ID INTEGER, Name_lang TEXT, '
    'Name_lang_esES TEXT, ContinentID INTEGER, MountCreatureID TEXT)',
    'CREATE TABLE ext_item_l10n (item_id INTEGER, locale TEXT, name TEXT)',
    'CREATE TABLE v_zona_niveles (area_id INTEGER, nombre TEXT, nombre_en TEXT, '
    'nivel_min INTEGER, nivel_max INTEGER, pnj INTEGER, origen TEXT)',
    'CREATE TABLE LFGDungeons (ID INTEGER, Name_lang TEXT, Name_lang_esES TEXT, '
    'TypeID INTEGER, MapID INTEGER, ContentTuningID INTEGER)',
    'CREATE TABLE contenttuning (ID INTEGER, MinLevelSquish INTEGER, '
    'MaxLevelSquish INTEGER, LfgMinLevel INTEGER, LfgMaxLevel INTEGER)',
    'CREATE TABLE v_jefe_mazmorra (encuentro_id INTEGER, map_id INTEGER, '
    'instancia TEXT, dificultad INTEGER, orden INTEGER, nombre TEXT, nombre_en TEXT, '
    'npc_id INTEGER, zone_id INTEGER, x REAL, y REAL)',
    'CREATE TABLE levelexperience (ID INTEGER, Level INTEGER, ContentSetID INTEGER, '
    'Experience INTEGER)',
    'CREATE TABLE v_mision (quest_id INTEGER, titulo TEXT, nivel INTEGER, xp INTEGER, '
    'zona TEXT, objetivo TEXT, texto TEXT, origen TEXT)',
    'CREATE TABLE v_botin (npc_id INTEGER, item_id INTEGER, veces INTEGER, '
    'muertes INTEGER, porcentaje REAL, origen TEXT)',
    'CREATE TABLE v_npc (npc_id INTEGER, nombre TEXT, nombre_en TEXT)',
    'CREATE TABLE v_ruta (ruta_id INTEGER, tipo TEXT, nodo_origen INTEGER, '
    'origen TEXT, nodo_destino INTEGER, destino TEXT, faccion TEXT, coste INTEGER)',
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
        (255, 14, 19),
        (96393, 9, 16),
    ])
    _insert(conn, 'ext_quest_l10n', ['quest_id', 'locale', 'name'], [
        (1338, 'esES', 'Un pedido de Pico Tormenta'),
        (1338, 'enUS', 'A Request from Ironforge'),
        (255, 'esES', 'Mercenarios'),
        (255, 'enUS', 'Mercenaries'),
        (96393, 'esES', 'Incursión en la Antigua Forjaz'),
        (96393, 'enUS', 'Old Ironforge Incursion'),
    ])
    _insert(conn, 'ext_quest_starters', ['quest_id', 'entity_type', 'entity_id'], [
        (1338, 'npc', 1343),
        (96393, 'npc', 264936),
    ])
    _insert(conn, 'ext_quest_finishers', ['quest_id', 'entity_type', 'entity_id'], [
        (1338, 'npc', 5413),
        (96393, 'npc', 2784),
    ])
    _insert(conn, 'ext_npcs', ['npc_id', 'min_level', 'max_level', 'friendly_to_faction'], [
        (1343, 10, 10, 'A'),
        (5413, 30, 30, 'A'),
        (264936, 13, 13, 'A'),
        (2784, 63, 63, 'A'),
        (4991, 60, 60, 'A'),
        (258098, 60, 60, 'A'),
        (7000, 60, 60, 'H'),
        (1163, 5, 6, 'A'),
        (1197, 5, 6, 'A'),
        (1162, 5, 6, 'A'),
    ])
    _insert(conn, 'ext_npc_l10n', ['npc_id', 'locale', 'name', 'sub_name'], [
        (1343, 'esES', 'Montaraz Pico Tormenta', None),
        (5413, 'esES', 'Furen Barbalarga', None),
        (264936, 'esES', 'Videnterra Farsen', None),
        (2784, 'esES', 'Rey Magni Barbabronce', 'Señor\u00a0de\u00a0Forjaz'),
        (4991, 'enUS', 'World Shaman Trainer', 'Shaman Trainer'),
        (4991, 'esES', 'World Shaman Trainer', 'Instructor\u00a0de\u00a0chamanes'),
        (258098, 'enUS', 'Eldrun Rompetormentas', 'Shaman Trainer'),
        (258098, 'esES', 'Eldrun Rompetormentas', ''),
        (7000, 'esES', 'Haromm', 'Instructor\u00a0de\u00a0chamanes'),
        (7000, 'enUS', 'Haromm', 'Shaman Trainer'),
        (1163, 'esES', 'Trog A', None),
        (1197, 'esES', 'Trog B', None),
        (1162, 'esES', 'Trog C', None),
    ])
    _insert(conn, 'ext_npc_spawns', ['npc_id', 'zone_id', 'spawn_idx', 'x', 'y'], [
        (1343, 38, 1, 24.8, 18.4),
        (5413, 1519, 1, 64.6, 37.2),
        (264936, 1, 1, 64.87, 58.47),
        (2784, 1537, 1, 39.09, 56.2),
        (258098, 1537, 1, 47.1, 13.8),
        (7000, 1637, 1, 10.0, 20.0),
        (1163, 38, 1, 10.0, 20.0),
        (1197, 38, 1, 11.0, 21.0),
        (1162, 38, 1, 12.0, 22.0),
    ])
    _insert(conn, 'ext_zones', ['group_id', 'area_id', 'name_enUS', 'name_esES'], [
        (0, 1, 'Dun Morogh', 'Dun Morogh'),
        (0, 38, 'Loch Modan', 'Loch Modan'),
        (0, 40, 'Westfall', 'Páramos de Poniente'),
        (0, 44, 'Redridge Mountains', 'Montañas Crestagrana'),
        (0, 148, 'Darkshore', 'Costa Oscura'),
        (0, 1519, 'Stormwind City', 'Ciudad de Ventormenta'),
        (0, 1537, 'Ironforge', 'Forjaz'),
        (1, 1637, 'Orgrimmar', 'Orgrimmar'),
    ])
    _insert(conn, 'ext_dungeons', ['area_id', 'name_enUS', 'name_esES', 'parent_zone_id'], [
        (1581, 'The Deadmines', 'Las Minas de la Muerte', 40),
        (43, 'Wailing Caverns', 'Cuevas de los Lamentos', 17),
        (721, 'Gnomeregan', 'Gnomeregan', 1),
    ])
    _insert(conn, 'ext_dungeon_entrances', ['area_id', 'idx', 'zone_id', 'x', 'y'], [
        (1581, 1, 40, 42.5, 71.7),
        (43, 1, 17, 11.1, 22.2),
        (721, 1, 1, 24.3, 39.8),
    ])
    _insert(conn, 'v_hechizos_instructor', ['ClassMask', 'Name_enUS', 'Name_esES', 'Level'], [
        (64, 'Flametongue Weapon', 'Arma lengua de Fuego', 18),
        (64, 'Healing Wave', 'Onda de curación', 18),
        (64, 'Tremor Totem', 'Tótem de tremor', 18),
        (64, 'Stoneclaw Totem', 'Tótem Garra de piedra', 18),
        (64, 'Flame Shock', 'Choque de llamas', 18),
        (64, 'Ghost Wolf', 'Lobo fantasmal', 20),
    ])
    _insert(conn, 'TalentTab', ['__id', 'Name_lang', 'OrderIndex', 'ClassMask',
                                'Name_lang_esES'], [
        (261, 'Elemental', 0, 64, 'Elemental'),
        (263, 'Enhancement', 1, 64, 'Mejora'),
        (262, 'Restoration', 2, 64, 'Recuperación'),
    ])
    _insert(conn, 'TaxiNodes', ['__id', 'ID', 'Name_lang', 'Name_lang_esES',
                                'ContinentID', 'MountCreatureID'], [
        (2, 2, 'Stormwind, Elwynn', 'Ventormenta, Elwynn', 0, '[0, 541]'),
        (6, 6, 'Ironforge, Dun Morogh', 'Forjaz, Dun Morogh', 0, '[0, 541]'),
        (8, 8, 'Thelsamar, Loch Modan', 'Thelsamar, Loch Modan', 0, '[0, 541]'),
        (23, 23, 'Orgrimmar, Durotar', 'Orgrimmar, Durotar', 1, '[2224, 0]'),
        (26, 26, 'Auberdine, Darkshore', 'Auberdine, Costa Oscura', 1, '[0, 541]'),
    ])
    _insert(conn, 'ext_item_l10n', ['item_id', 'locale', 'name'], [
        (2536, 'esES', 'Diente de piedra trogg'),
        (2536, 'enUS', 'Trogg Stone Tooth'),
    ])
    _insert(conn, 'v_zona_niveles', ['area_id', 'nombre', 'nombre_en', 'nivel_min',
                                     'nivel_max', 'pnj', 'origen'], [
        (44, 'Montañas Crestagrana', 'Redridge Mountains', 16, 26, 1351, 'deducido'),
        (1519, 'Ciudad de Ventormenta', 'Stormwind City', 1, 60, 3725, 'deducido'),
        (38, 'Loch Modan', 'Loch Modan', 11, 20, 840, 'deducido'),
        (40, 'Páramos de Poniente', 'Westfall', 11, 20, 800, 'deducido'),
        (17, 'Los Baldíos', 'The Barrens', 12, 28, 900, 'deducido'),
        (2437, 'Sima Ígnea', 'Ragefire Chasm', 14, 16, 50, 'deducido'),
    ])
    _insert(conn, 'LFGDungeons', ['ID', 'Name_lang', 'Name_lang_esES', 'TypeID',
                                  'MapID', 'ContentTuningID'], [
        (5, 'Deadmines', 'Minas de la Muerte', 0, 36, 5240),
        (1, 'Wailing Caverns', 'Cuevas de los Lamentos', 0, 43, 5254),
        (13, 'Gnomeregan', 'Gnomeregan', 0, 0, 5242),
    ])
    _insert(conn, 'contenttuning', ['ID', 'MinLevelSquish', 'MaxLevelSquish',
                                    'LfgMinLevel', 'LfgMaxLevel'], [
        (5240, 16, 16, 0, 0),
        (5254, 17, 17, 0, 0),
        (5242, 25, 25, 0, 0),
    ])
    _insert(conn, 'v_jefe_mazmorra', ['encuentro_id', 'map_id', 'instancia', 'dificultad',
                                      'orden', 'nombre', 'nombre_en'], [
        (2741, 36, 'Deadmines', 0, 0, "Rhahk'Zor", "Rhahk'Zor"),
        (2741, 36, 'Deadmines', 1, 0, "Rhahk'Zor", "Rhahk'Zor"),
        (2742, 36, 'Deadmines', 0, 1000, 'Sneed', 'Sneed'),
        (3676, 36, 'Deadmines', 0, 1500, 'Minero Johnson', 'Miner Johnson'),
        (2743, 36, 'Deadmines', 0, 2000, 'Gilnid', 'Gilnid'),
        (2744, 36, 'Deadmines', 0, 3000, 'Capitán Verdetez', 'Captain Greenskin'),
        (2745, 36, 'Deadmines', 0, 4000, 'Don Mamporro', 'Mr. Smite'),
        (2746, 36, 'Deadmines', 0, 5000, 'Cocinitas', 'Cookie'),
        (2747, 36, 'Deadmines', 0, 6000, 'Edwin VanCleef', 'Edwin VanCleef'),
        (3654, 43, 'Wailing Caverns', 0, 0, 'Lady Anacondra', 'Lady Anacondra'),
        (3655, 43, 'Wailing Caverns', 0, 1000, 'Lord Cobrahn', 'Lord Cobrahn'),
        (3656, 43, 'Wailing Caverns', 0, 2000, 'Kresh', 'Kresh'),
        (3657, 43, 'Wailing Caverns', 0, 3000, 'Lord Pythas', 'Lord Pythas'),
        (3658, 43, 'Wailing Caverns', 0, 4000, 'Skum', 'Skum'),
        (3659, 43, 'Wailing Caverns', 0, 5000, 'Lord Serpentis', 'Lord Serpentis'),
        (3660, 43, 'Wailing Caverns', 0, 6000, 'Verdan el Eterno', 'Verdan the Everliving'),
        (3661, 43, 'Wailing Caverns', 0, 7000, 'Mutanus el Devorador', 'Mutanus the Devourer'),
        (3661, 43, 'Wailing Caverns', 1, 7000, 'Mutanus el Devorador', 'Mutanus the Devourer'),
    ])
    _insert(conn, 'levelexperience', ['ID', 'Level', 'ContentSetID', 'Experience'], [
        (16, 16, 0, 16000),
        (17, 17, 0, 17700),
    ])
    _insert(conn, 'v_mision', ['quest_id', 'titulo', 'nivel', 'xp', 'zona', 'objetivo',
                               'texto', 'origen'], [
        (255, 'Mercenarios', 19, 1800, 'Loch Modan', '["Mata 4 ogros."]', None, 'juego'),
        (1338, 'Un pedido de Pico Tormenta', 14, 900, 'Loch Modan',
         '["Habla con Furen."]', None, 'juego'),
    ])
    _insert(conn, 'v_botin', ['npc_id', 'item_id', 'veces', 'muertes', 'porcentaje',
                              'origen'], [
        (1163, 2536, None, None, 50.0, 'questie'),
        (1197, 2536, None, None, 50.0, 'questie'),
        (1162, 2536, 5, 16, 31.25, 'juego'),
    ])
    _insert(conn, 'v_npc', ['npc_id', 'nombre', 'nombre_en'], [
        (1163, 'Trog A', 'Trogg A'),
        (1197, 'Trog B', 'Trogg B'),
        (1162, 'Trog C', 'Trogg C'),
    ])
    _insert(conn, 'v_ruta', ['ruta_id', 'tipo', 'nodo_origen', 'origen',
                             'nodo_destino', 'destino', 'faccion', 'coste'], [
        (12, 'vuelo', 6, 'Ironforge, Dun Morogh', 2, 'Stormwind, Elwynn', 'Alianza', 50),
        (16, 'vuelo', 6, 'Ironforge, Dun Morogh', 8, 'Thelsamar, Loch Modan', 'Alianza', 110),
        (400, 'vuelo', 6, 'Ironforge, Dun Morogh', 23, 'Orgrimmar, Durotar', 'Horda', 999),
    ])
    conn.commit()
    conn.close()

    database = WowDb(path)
    yield database
    database.close()


def _message(question, lang='esES', ctx=None):
    return {'v': 1, 'lang': lang, 'q': question, 'ctx': dict(ctx or CTX)}


def _text(facts):
    return '\n'.join(facts.lines)


def test_zone_levels_question(db):
    facts = retrieve(_message('¿De qué nivel es Montañas Crestagrana?'), db)
    text = _text(facts)
    assert 'Montañas Crestagrana' in text
    assert '16-26' in text
    assert 'rangos de nivel de mazmorras' not in facts.missing


def test_zones_for_my_level(db):
    facts = retrieve(_message('¿Qué zonas me tocan a mi nivel?'), db)
    text = _text(facts)
    assert 'Zonas para nivel 16:' in text
    assert 'Montañas Crestagrana (16-26)' in text
    assert 'Ciudad de Ventormenta' not in text
    assert 'zones:16' in facts.sources


def test_dungeon_level_question(db):
    facts = retrieve(_message('¿A qué nivel puedo hacer Las Minas de la Muerte?'), db)
    text = _text(facts)
    assert 'niveles 17-26' in text
    assert facts.missing == []
    assert 'dungeon_level:1581' in facts.sources


def test_dungeons_for_my_level(db):
    facts = retrieve(_message('¿Qué mazmorras puedo hacer a mi nivel?'), db)
    text = _text(facts)
    assert 'Mazmorras cerca de tu nivel:' in text
    assert 'Sima Ígnea (13-18)' in text
    assert 'Cuevas de los Lamentos (15-24)' in text
    assert 'Minas de la Muerte' not in text
    assert 'dungeons:16' in facts.sources


def test_dungeon_bosses_question(db):
    facts = retrieve(_message('¿Qué jefes tiene Cuevas de los Lamentos?'), db)
    text = _text(facts)
    assert 'Jefes de Cuevas de los Lamentos, en orden:' in text
    assert 'Lady Anacondra' in text
    assert 'Mutanus el Devorador' in text
    assert text.count('Mutanus el Devorador') == 1


def test_final_boss_question(db):
    facts = retrieve(_message('¿Quién es el jefe final de las Minas de la Muerte?'), db)
    text = _text(facts)
    assert 'Jefe final: Edwin VanCleef' in text

    only_final = retrieve(_message('¿Cuál es el final de las Minas de la Muerte?'), db)
    assert 'Jefe final: Edwin VanCleef' in _text(only_final)


def test_xp_to_level_question(db):
    facts = retrieve(_message('¿Cuánta experiencia necesito para subir al nivel 17?'), db)
    text = _text(facts)
    assert 'del nivel 16 al 17: 16000' in text
    assert facts.missing == []
    assert 'xp:16' in facts.sources


def test_quest_xp_question(db):
    facts = retrieve(_message('¿Cuánta experiencia da la misión Mercenarios?'), db)
    text = _text(facts)
    assert 'Mercenarios' in text
    assert '1800' in text
    assert not any(line.startswith('Experiencia para pasar') for line in facts.lines)


def test_quest_objective_question(db):
    facts = retrieve(_message('¿Qué tengo que hacer en la misión Mercenarios?'), db)
    assert 'Mata 4 ogros' in _text(facts)


def test_item_loot_question(db):
    facts = retrieve(_message('¿Dónde consigo Diente de piedra trogg?'), db)
    text = _text(facts)
    assert 'botín:' in text
    assert '50 %' in text
    assert 'Loch Modan' in text


def test_flights_from_question(db):
    facts = retrieve(_message('¿Adónde puedo volar desde Forjaz?'), db)
    text = _text(facts)
    assert 'Vuelos desde Forjaz, Dun Morogh:' in text
    assert 'Thelsamar, Loch Modan (1 de plata y 10 de cobre)' in text
    assert 'Orgrimmar' not in text
    assert any(source.startswith('flights_from:') for source in facts.sources)


def test_flight_cost_question(db):
    facts = retrieve(_message('¿Cuánto cuesta volar de Forjaz a Thelsamar?'), db)
    text = _text(facts)
    assert 'Vuelo Forjaz, Dun Morogh -> Thelsamar, Loch Modan: 1 de plata y 10 de cobre' in text
    assert facts.missing == []
    assert any(source.startswith('flight_cost:') for source in facts.sources)


def test_route_question_declares_missing(db):
    facts = retrieve(_message('¿Cómo voy de Forjaz a Auberdine?'), db)
    text = _text(facts)
    assert 'Vuelos desde' not in text
    assert 'transporte' not in text.lower()
    assert 'ruta completa entre Forjaz y Auberdine (aún no está en la base)' in facts.missing


def test_english_zone_question(db):
    facts = retrieve(_message('What level is Westfall?', lang='enUS'), db)
    text = _text(facts)
    assert 'Zone Westfall: levels 11-20' in text


def test_old_battery_still_works(db):
    quest = retrieve(_message('¿Dónde entrego Un pedido de Pico Tormenta?'), db)
    assert 'Furen Barbalarga' in _text(quest)

    spells = retrieve(_message('¿Qué hechizos nuevos aprendo a nivel 18?'), db)
    assert 'Arma lengua de Fuego' in _text(spells)

    trainer = retrieve(_message('¿Dónde está el instructor de chamanes en Forjaz?'), db)
    assert trainer.lines
    assert 'Eldrun Rompetormentas' in trainer.lines[0]

    dungeon = retrieve(_message('¿Dónde está la entrada de Las Minas de la Muerte?'), db)
    assert 'Páramos de Poniente (42.5, 71.7)' in _text(dungeon)


def test_render_limit_keeps_priority(db):
    facts = retrieve(_message('¿Qué zonas me tocan a mi nivel?'), db)
    rendered = facts.render('esES')
    assert rendered.startswith('DATOS VERIFICADOS')
    assert len(rendered) <= 1600
