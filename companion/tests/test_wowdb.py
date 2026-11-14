"""Pruebas de la capa de solo lectura sobre la base de datos de WoW Forever."""

from __future__ import annotations

import sqlite3

import pytest

import askforever.cli as cli
from askforever.data.wowdb import WowDb, class_mask_from_name, normalize

SCHEMA = [
    'CREATE TABLE ext_quests (quest_id INTEGER, required_level INTEGER, quest_level INTEGER)',
    'CREATE TABLE ext_quest_l10n (quest_id INTEGER, locale TEXT, name TEXT)',
    'CREATE TABLE ext_quest_starters (quest_id INTEGER, entity_type TEXT, entity_id INTEGER)',
    'CREATE TABLE ext_quest_finishers (quest_id INTEGER, entity_type TEXT, entity_id INTEGER)',
    'CREATE TABLE ext_quest_objective_items (quest_id INTEGER, position INTEGER, '
    'item_id INTEGER, text TEXT, icon_type INTEGER)',
    'CREATE TABLE ext_npcs (npc_id INTEGER, min_level INTEGER, max_level INTEGER, rank INTEGER, '
    'zone_id INTEGER, faction_template_id INTEGER, friendly_to_faction TEXT, npc_flags INTEGER)',
    'CREATE TABLE ext_npc_l10n (npc_id INTEGER, locale TEXT, name TEXT, sub_name TEXT)',
    'CREATE TABLE ext_npc_spawns (npc_id INTEGER, zone_id INTEGER, spawn_idx INTEGER, '
    'x REAL, y REAL, phase INTEGER)',
    'CREATE TABLE ext_object_l10n (object_id INTEGER, locale TEXT, name TEXT)',
    'CREATE TABLE ext_zones (group_id INTEGER, area_id INTEGER, name_enUS TEXT, name_esES TEXT)',
    'CREATE TABLE ext_continents (continent_id INTEGER, name_enUS TEXT, name_esES TEXT)',
    'CREATE TABLE ext_dungeons (area_id INTEGER, name_enUS TEXT, name_esES TEXT, '
    'parent_zone_id INTEGER)',
    'CREATE TABLE ext_dungeon_entrances (area_id INTEGER, idx INTEGER, zone_id INTEGER, '
    'x REAL, y REAL)',
    'CREATE TABLE TaxiNodes (__id INTEGER, Name_lang TEXT, Pos TEXT, MapOffset TEXT, '
    'FlightMapOffset TEXT, ID INTEGER, ContinentID INTEGER, ConditionID INTEGER, '
    'CharacterBitNumber INTEGER, Flags INTEGER, UiTextureKitID INTEGER, '
    'MinimapAtlasMemberID INTEGER, Facing INTEGER, SpecialIconConditionID INTEGER, '
    'VisibilityConditionID INTEGER, MountCreatureID TEXT, Name_lang_esES TEXT)',
    'CREATE TABLE v_hechizos_instructor (ClassMask INTEGER, SkillLine INTEGER, '
    'SpellID INTEGER, Name_enUS TEXT, Name_esES TEXT, Level INTEGER, AcquireMethod INTEGER)',
    'CREATE TABLE TalentTab (__id INTEGER, ID INTEGER, Name_lang TEXT, BackgroundFile TEXT, '
    'OrderIndex INTEGER, ClassMask INTEGER, Name_lang_esES TEXT)',
    'CREATE TABLE ext_item_l10n (item_id INTEGER, locale TEXT, name TEXT)',
    'CREATE TABLE ext_item_vendors (item_id INTEGER, position INTEGER, npc_id INTEGER)',
    'CREATE TABLE ext_item_npc_drops (item_id INTEGER, position INTEGER, npc_id INTEGER)',
    'CREATE TABLE ext_item_drop_rates (source TEXT, item_id INTEGER, npc_id INTEGER, '
    'rate_percent REAL)',
    'CREATE TABLE ext_item_quest_rewards (item_id INTEGER, position INTEGER, quest_id INTEGER)',
]


def _insert(conn, table, columns, rows):
    placeholders = ', '.join('?' for _ in columns)
    conn.executemany(f'INSERT INTO {table} ({", ".join(columns)}) VALUES ({placeholders})', rows)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / 'wow.sqlite'
    conn = sqlite3.connect(path)
    for statement in SCHEMA:
        conn.execute(statement)

    _insert(conn, 'ext_quests', ['quest_id', 'required_level', 'quest_level'], [
        (267, 10, 12),
        (96393, 9, 16),
        (500, 8, 10),
        (501, 8, 20),
        (1234, 10, 14),
    ])
    _insert(conn, 'ext_quest_l10n', ['quest_id', 'locale', 'name'], [
        (267, 'esES', 'La amenaza trogg'),
        (267, 'enUS', 'The Trogg Threat'),
        (96393, 'esES', 'Incursión en la Antigua Forjaz'),
        (96393, 'enUS', 'Old Ironforge Incursion'),
        (500, 'esES', 'Eco repetido'),
        (500, 'enUS', 'Repeated Echo'),
        (501, 'esES', 'Eco repetido'),
        (501, 'enUS', 'Repeated Echo'),
        (1234, 'esES', 'Un pedido de Pico Tormenta'),
        (1234, 'enUS', 'A Request from Ironforge'),
    ])
    _insert(conn, 'ext_quest_starters', ['quest_id', 'entity_type', 'entity_id'], [
        (267, 'npc', 1092),
        (96393, 'npc', 264936),
        (500, 'npc', 9001),
        (501, 'npc', 9002),
        (1234, 'npc', 1092),
    ])
    _insert(conn, 'ext_quest_finishers', ['quest_id', 'entity_type', 'entity_id'], [
        (267, 'npc', 1092),
        (96393, 'npc', 2784),
    ])
    _insert(conn, 'ext_quest_objective_items',
            ['quest_id', 'position', 'item_id', 'text', 'icon_type'], [
                (267, 1, 2536, None, 0),
                (96393, 1, 274286, None, 0),
            ])

    _insert(conn, 'ext_npcs', ['npc_id', 'min_level', 'max_level', 'rank', 'zone_id',
                               'faction_template_id', 'friendly_to_faction', 'npc_flags'], [
        (1092, 40, 40, 0, 38, 0, 'A', 0),
        (264936, 13, 13, 0, 1, 0, 'A', 0),
        (2784, 63, 63, 0, 1537, 0, 'A', 0),
        (7000, 60, 60, 0, 1, 0, 'H', 0),
        (7001, 30, 30, 0, 1537, 0, 'A', 0),
        (7002, 30, 30, 0, 38, 0, 'A', 0),
        (9001, 10, 10, 0, 1, 0, 'A', 0),
        (9002, 20, 20, 0, 1, 0, 'A', 0),
    ])
    _insert(conn, 'ext_npc_l10n', ['npc_id', 'locale', 'name', 'sub_name'], [
        (1092, 'esES', 'Capitán Rugelfuss', None),
        (1092, 'enUS', 'Captain Rugelfuss', None),
        (264936, 'esES', 'Videnterra Farsen', None),
        (264936, 'enUS', 'Earthseer Farsen', None),
        (2784, 'esES', 'Rey Magni Barbabronce', 'Señor\u00a0de\u00a0Forjaz'),
        (2784, 'enUS', 'King Magni Bronzebeard', 'Lord of Ironforge'),
        (7000, 'esES', 'Haromm', 'Instructor\u00a0de\u00a0chamanes'),
        (7000, 'enUS', 'Haromm', 'Shaman Trainer'),
        (7001, 'esES', 'Vendedor', 'Mercader'),
        (7001, 'enUS', 'Vendor', 'Merchant'),
        (7002, 'esES', 'Jefe', None),
        (7002, 'enUS', 'Boss', None),
        (9001, 'esES', 'Iniciador Uno', None),
        (9002, 'esES', 'Iniciador Dos', None),
    ])
    _insert(conn, 'ext_npc_spawns', ['npc_id', 'zone_id', 'spawn_idx', 'x', 'y', 'phase'], [
        (1092, 38, 1, 23.23, 73.68, 0),
        (264936, 1, 1, 64.87, 58.47, 0),
        (2784, 1537, 1, 39.09, 56.2, 0),
        (7000, 1, 1, 10.0, 20.0, 0),
        (7001, 1537, 1, 30.0, 40.0, 0),
        (7002, 38, 1, 50.0, 60.0, 0),
    ])
    _insert(conn, 'ext_object_l10n', ['object_id', 'locale', 'name'], [
        (31, 'esES', 'Estatua de león antigua'),
        (31, 'enUS', 'Old Lion Statue'),
    ])
    _insert(conn, 'ext_zones', ['group_id', 'area_id', 'name_enUS', 'name_esES'], [
        (0, 0, 'Eastern Kingdoms', 'Reinos del Este'),
        (0, 1, 'Dun Morogh', 'Dun Morogh'),
        (0, 38, 'Loch Modan', 'Loch Modan'),
        (0, 40, 'Westfall', 'Páramos de Poniente'),
        (0, 1537, 'Ironforge', 'Forjaz'),
        (0, 999, 'Minas de la Muerte', 'Minas de la Muerte'),
        (0, 901, 'Zona Alfa', 'Zona Alfa'),
        (0, 902, 'Zona Beta', 'Zona Beta'),
        (0, 903, 'Zona Gamma', 'Zona Gamma'),
        (0, 904, 'Zona Delta', 'Zona Delta'),
        (0, 905, 'Zona Epsilon', 'Zona Epsilon'),
        (0, 906, 'Zona Zeta', 'Zona Zeta'),
        (0, 907, 'Zona Eta', 'Zona Eta'),
        (0, 908, 'Zona Theta', 'Zona Theta'),
    ])
    _insert(conn, 'ext_continents', ['continent_id', 'name_enUS', 'name_esES'], [
        (0, 'Eastern Kingdoms', 'Reinos del Este'),
        (1, 'Kalimdor', 'Kalimdor'),
    ])
    _insert(conn, 'ext_dungeons', ['area_id', 'name_enUS', 'name_esES', 'parent_zone_id'], [
        (1581, 'The Deadmines', 'Las Minas de la Muerte', 40),
        (721, 'Gnomeregan', 'Gnomeregan', 1),
    ])
    _insert(conn, 'ext_dungeon_entrances', ['area_id', 'idx', 'zone_id', 'x', 'y'], [
        (1581, 1, 40, 42.5, 71.7),
        (721, 1, 1, 24.3, 39.8),
    ])
    _insert(conn, 'TaxiNodes', ['__id', 'Name_lang', 'ContinentID', 'MountCreatureID',
                                'Name_lang_esES'], [
        (6, 'Ironforge, Dun Morogh', 0, '[0, 541]', 'Forjaz, Dun Morogh'),
        (7, 'Menethil Harbor, Wetlands', 0, '[0, 541]', 'Puerto de Menethil, Los Humedales'),
        (8, 'Thelsamar, Loch Modan', 0, '[0, 541]', 'Thelsamar, Loch Modan'),
        (100, 'Stormwind, Elwynn', 0, '[0, 0, 541]', 'Ventormenta, Elwynn'),
        (50, 'The Sepulcher, Silverpine Forest', 0, '[3574, 0]', 'Sepulcro, Bosque de Argénteos'),
        (23, 'Orgrimmar, Durotar', 1, '[2224, 0]', 'Orgrimmar, Durotar'),
        (30, 'Auberdine, Darkshore', 1, '[0, 541]', 'Auberdine, Costa Oscura'),
        (34, 'Transport, Booty Bay - Ratchet', 0, '[0, 0]', 'Transporte, Bahía del Botín'),
    ])
    _insert(conn, 'v_hechizos_instructor', ['ClassMask', 'SkillLine', 'SpellID',
                                            'Name_enUS', 'Name_esES', 'Level',
                                            'AcquireMethod'], [
        (64, 373, 8027, 'Flametongue Weapon', 'Arma lengua de Fuego', 18, 0),
        (64, 373, 913, 'Healing Wave', 'Onda de curación', 18, 0),
        (64, 373, 8143, 'Tremor Totem', 'Tótem de tremor', 18, 0),
        (64, 373, 6390, 'Stoneclaw Totem', 'Tótem Garra de piedra', 18, 0),
        (64, 373, 8052, 'Flame Shock', 'Choque de llamas', 18, 0),
        (64, 373, 8052, 'Flame Shock', 'Choque de llamas', 18, 0),
        (64, 373, 2645, 'Ghost Wolf', 'Lobo fantasmal', 20, 0),
        (64, 373, 8056, 'Frost Shock', 'Choque de Escarcha', 20, 0),
        (1, 26, 100, 'Charge', 'Cargar', 18, 0),
    ])
    _insert(conn, 'TalentTab', ['__id', 'ID', 'Name_lang', 'OrderIndex', 'ClassMask',
                                'Name_lang_esES'], [
        (261, 261, 'Elemental', 0, 64, 'Elemental'),
        (262, 262, 'Restoration', 2, 64, 'Recuperación'),
        (263, 263, 'Enhancement', 1, 64, 'Mejora'),
        (100, 100, 'Arms', 0, 1, 'Armas'),
    ])
    _insert(conn, 'ext_item_l10n', ['item_id', 'locale', 'name'], [
        (85, 'esES', 'Jubón de cuero sucio'),
        (85, 'enUS', 'Dirty Leather Vest'),
        (2536, 'esES', 'Diente de piedra trogg'),
        (2536, 'enUS', 'Trogg Stone Tooth'),
        (274286, 'esES', 'Cabeza de Durgen'),
        (274286, 'enUS', 'Durgen Head'),
        (900, 'esES', 'carne'),
        (900, 'enUS', 'carne'),
    ])
    _insert(conn, 'ext_item_vendors', ['item_id', 'position', 'npc_id'], [
        (85, 1, 7001),
    ])
    _insert(conn, 'ext_item_npc_drops', ['item_id', 'position', 'npc_id'], [
        (85, 1, 7002),
    ])
    _insert(conn, 'ext_item_drop_rates', ['source', 'item_id', 'npc_id', 'rate_percent'], [
        ('npc', 85, 7002, 12.5),
    ])
    _insert(conn, 'ext_item_quest_rewards', ['item_id', 'position', 'quest_id'], [
        (85, 1, 96393),
    ])
    conn.commit()
    conn.close()
    return path


def test_normalize():
    assert normalize('  ¡Aúllaescarcha!  ') == 'aullaescarcha'
    assert normalize('Señor\u00a0de   Forjaz') == 'senor de forjaz'
    assert normalize("Sian'tsu") == 'siantsu'
    assert normalize(None) == ''
    assert normalize('') == ''


def test_class_mask_from_name():
    assert class_mask_from_name('Chamán') == 64
    assert class_mask_from_name('chamana') == 64
    assert class_mask_from_name('Shaman') == 64
    assert class_mask_from_name('guerrera') == 1
    assert class_mask_from_name('desconocido') is None


def test_find_quest_by_name_es(db_path):
    db = WowDb(db_path)
    quest = db.find_quest('La amenaza trogg')
    assert quest['id'] == 267
    assert quest['level'] == 12
    assert quest['required_level'] == 10
    assert quest['starters'][0]['id'] == 1092
    assert quest['finishers'][0]['id'] == 1092
    assert quest['starters'][0]['locations'][0]['zone'] == 'Loch Modan'
    assert quest['starters'][0]['locations'][0]['x'] == 23.2
    assert quest['objective_items'] == ['Diente de piedra trogg']
    assert quest['variants'] == 1
    db.close()


def test_find_quest_by_name_en(db_path):
    db = WowDb(db_path)
    quest = db.find_quest('The Trogg Threat', lang='en')
    assert quest['id'] == 267
    assert quest['name'] == 'The Trogg Threat'
    assert quest['starters'][0]['name'] == 'Captain Rugelfuss'
    db.close()


def test_find_quest_by_id(db_path):
    db = WowDb(db_path)
    quest = db.find_quest(96393)
    assert quest['id'] == 96393
    assert quest['name'] == 'Incursión en la Antigua Forjaz'
    assert quest['finishers'][0]['name'] == 'Rey Magni Barbabronce'
    db.close()


def test_find_quest_missing(db_path):
    db = WowDb(db_path)
    assert db.find_quest('No existe') is None
    assert db.find_quest(999999) is None
    db.close()


def test_find_quest_variants_prefers_closest_level(db_path):
    db = WowDb(db_path)
    quest = db.find_quest('Eco repetido', player_level=19)
    assert quest['variants'] == 2
    assert quest['id'] == 501
    db.close()


def test_find_npc(db_path):
    db = WowDb(db_path)
    npc = db.find_npc('Rey Magni Barbabronce')
    assert npc['id'] == 2784
    assert npc['sub_name'] == 'Señor de Forjaz'
    assert npc['locations'][0]['zone'] == 'Forjaz'
    assert npc['locations'][0]['x'] == 39.1
    assert npc['locations'][0]['y'] == 56.2
    assert npc['friendly_to'] == 'A'

    english = db.find_npc('King Magni Bronzebeard', lang='en')
    assert english['name'] == 'King Magni Bronzebeard'
    assert english['sub_name'] == 'Lord of Ironforge'
    db.close()


def test_class_spells(db_path):
    db = WowDb(db_path)
    spells = db.class_spells(64, 18, 18)
    names = [spell['name'] for spell in spells]
    assert len(names) == 5
    assert 'Arma lengua de Fuego' in names
    assert 'Onda de curación' in names
    assert all(spell['level'] == 18 for spell in spells)

    level_20 = db.class_spells(64, 20, 20)
    assert {spell['name'] for spell in level_20} == {'Lobo fantasmal', 'Choque de Escarcha'}
    db.close()


def test_class_trainers(db_path):
    db = WowDb(db_path)
    assert db.class_trainers(64, 'A') == []
    trainers = db.class_trainers(64, 'H')
    assert [trainer['id'] for trainer in trainers] == [7000]
    assert trainers[0]['sub_name'] == 'Instructor de chamanes'
    db.close()


def test_dungeon(db_path):
    db = WowDb(db_path)
    dungeon = db.dungeon('Las Minas de la Muerte')
    assert dungeon['id'] == 1581
    assert dungeon['zone'] == 'Páramos de Poniente'
    assert dungeon['entrances'] == [
        {'zone': 'Páramos de Poniente', 'x': 42.5, 'y': 71.7},
    ]

    english = db.dungeon('The Deadmines', lang='en')
    assert english['name'] == 'The Deadmines'
    assert english['zone'] == 'Westfall'

    gnomeregan = db.dungeon(721)
    assert gnomeregan['name'] == 'Gnomeregan'
    db.close()


def test_flight_points(db_path):
    db = WowDb(db_path)
    alliance = db.flight_points(0, 'A')
    names = [point['name'] for point in alliance]
    assert 'Forjaz' in names
    assert 'Thelsamar, Loch Modan' in names
    assert 'Puerto de Menethil, Los Humedales' in names
    assert 'Ventormenta' in names
    assert 'Sepulcro, Bosque de Argénteos' not in names
    assert not any(name.startswith('Transporte') for name in names)
    assert 'Auberdine, Costa Oscura' not in names

    horde = db.flight_points(0, 'H')
    horde_names = [point['name'] for point in horde]
    assert 'Sepulcro, Bosque de Argénteos' in horde_names
    assert 'Forjaz' not in horde_names
    db.close()


def test_talent_trees(db_path):
    db = WowDb(db_path)
    assert db.talent_trees(64) == ['Elemental', 'Mejora', 'Recuperación']
    db.close()


def test_item_sources(db_path):
    db = WowDb(db_path)
    item = db.item_sources(85)
    assert item['name'] == 'Jubón de cuero sucio'
    assert item['vendors'][0]['npc'] == 'Vendedor'
    assert item['vendors'][0]['locations'][0]['zone'] == 'Forjaz'
    assert item['drops'][0]['npc'] == 'Jefe'
    assert item['drops'][0]['zone'] == 'Loch Modan'
    assert item['drops'][0]['rate'] == 12.5
    assert item['quest_rewards'] == ['Incursión en la Antigua Forjaz']

    english = db.item_sources('Dirty Leather Vest', lang='en')
    assert english['id'] == 85
    assert english['name'] == 'Dirty Leather Vest'
    assert db.item_sources('No existe') is None
    db.close()


def test_match_entities_quest(db_path):
    db = WowDb(db_path)
    matches = db.match_entities('¿Dónde entrego Un pedido de Pico Tormenta?')
    assert any(match['kind'] == 'quest' and match['id'] == 1234 for match in matches)
    db.close()


def test_match_entities_dungeon_es_and_en(db_path):
    db = WowDb(db_path)
    spanish = db.match_entities('¿Dónde está la entrada de Las Minas de la Muerte?')
    dungeons = [match for match in spanish if match['kind'] == 'dungeon']
    assert [match['id'] for match in dungeons] == [1581]
    assert not any(match['kind'] == 'zone' and match['id'] == 999 for match in spanish)

    english = db.match_entities('Where is the entrance to the Deadmines?', lang='en')
    english_dungeons = [match for match in english if match['kind'] == 'dungeon']
    assert [match['name'] for match in english_dungeons] == ['The Deadmines']
    db.close()


def test_match_entities_stop_words_and_boundaries(db_path):
    db = WowDb(db_path)
    assert db.match_entities('Quiero carne y agua', kinds=('item',)) == []
    assert db.match_entities('Gnomeregana', kinds=('dungeon',)) == []
    assert db.match_entities('', kinds=('dungeon',)) == []
    db.close()


def test_match_entities_no_overlap_and_max(db_path):
    db = WowDb(db_path)
    phrase = ('Zona Alfa Zona Beta Zona Gamma Zona Delta Zona Epsilon Zona Zeta '
              'Zona Eta Zona Theta')
    matches = db.match_entities(phrase, kinds=('zone',))
    assert len(matches) == 6

    phrase = 'Las Minas de la Muerte'
    matches = db.match_entities(phrase)
    assert any(match['kind'] == 'dungeon' and match['id'] == 1581 for match in matches)
    assert not any(match['kind'] == 'zone' and match['id'] == 999 for match in matches)
    db.close()


def test_available_missing_file(tmp_path):
    db = WowDb(tmp_path / 'no_existe.sqlite')
    assert db.available() is False
    assert db.zone_name(1) == ''
    assert db.find_quest('La amenaza trogg') is None
    db.close()


def test_missing_tables_return_empty(tmp_path):
    path = tmp_path / 'minimal.sqlite'
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE ext_quests (quest_id INTEGER, required_level INTEGER, '
                 'quest_level INTEGER)')
    conn.commit()
    conn.close()

    db = WowDb(path)
    assert db.available() is True
    assert db.zone_name(1) == ''
    assert db.find_quest('x') is None
    assert db.class_spells(64, 1, 60) == []
    assert db.talent_trees(64) == []
    assert db.match_entities('La amenaza trogg') == []
    db.close()


def test_database_is_read_only(db_path):
    db = WowDb(db_path)
    with pytest.raises(sqlite3.OperationalError):
        db.open().execute('INSERT INTO ext_quests (quest_id) VALUES (99999)')
    db.close()


def test_cli_data_check(db_path, capsys):
    assert cli.main(['data-check', '--db', str(db_path)]) == 0
    output = capsys.readouterr().out
    assert 'La amenaza trogg' in output
    assert 'Capitán Rugelfuss' in output
    assert 'Indice de nombres' in output


def test_cli_data_check_missing_db(tmp_path, capsys):
    assert cli.main(['data-check', '--db', str(tmp_path / 'no.sqlite')]) == 1
    assert 'No se encontro la base de datos' in capsys.readouterr().out
