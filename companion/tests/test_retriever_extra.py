"""Pruebas del recuperador ampliado: niveles, jefes, XP, vuelos y rutas."""

from __future__ import annotations

import sqlite3

import pytest

from askforever.data.wowdb import WowDb, normalize
from askforever.engine.retriever import (Facts, _active_quest_ids, _zone_in_question,
                                         _detect_active_quest_reference, _detect_entities,
                                         _entities_for_player, _item_line, _quest_line, retrieve)

SCHEMA = [
    'CREATE TABLE ext_quests (quest_id INTEGER, required_level INTEGER, quest_level INTEGER)',
    'CREATE TABLE ext_quest_l10n (quest_id INTEGER, locale TEXT, name TEXT)',
    'CREATE TABLE ext_quest_starters (quest_id INTEGER, entity_type TEXT, entity_id INTEGER)',
    'CREATE TABLE ext_quest_finishers (quest_id INTEGER, entity_type TEXT, entity_id INTEGER)',
    'CREATE TABLE ext_quest_objective_items (quest_id INTEGER, position INTEGER, '
    'item_id INTEGER, text TEXT, icon_type INTEGER)',
    'CREATE TABLE ext_item_object_drops (item_id INTEGER, position INTEGER, object_id INTEGER)',
    'CREATE TABLE ext_object_l10n (object_id INTEGER, locale TEXT, name TEXT)',
    'CREATE TABLE ext_object_spawns (object_id INTEGER, zone_id INTEGER, spawn_idx INTEGER, '
    'x REAL, y REAL, phase INTEGER)',
    'CREATE TABLE ext_quest_objective_creatures (quest_id INTEGER, position INTEGER, '
    'npc_id INTEGER, text TEXT, icon_type INTEGER)',
    'CREATE TABLE ext_npcs (npc_id INTEGER, min_level INTEGER, max_level INTEGER, '
    'friendly_to_faction TEXT)',
    'CREATE TABLE AreaTable (ID INTEGER, AreaName_lang TEXT, ParentAreaID INTEGER, '
    'FactionGroupMask INTEGER)',
    'CREATE TABLE obs_wdc_npc (npc_id INTEGER, nombre TEXT, nivel_min INTEGER, '
    'nivel_max INTEGER, clasificacion TEXT, tipo TEXT, familia TEXT, vida INTEGER, '
    'reaccion TEXT)',
    'CREATE TABLE CreatureFamily (ID INTEGER, Name_lang TEXT, Name_lang_esES TEXT)',
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
NBSP = chr(0xA0)


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
        (91775, 10, 12),
        (91776, 10, 12),
        (91777, 10, 12),
        (91778, 10, 12),
        (91779, 10, 12),
        (92001, 10, 10),
        (92002, 10, 20),
        (79092, 9, 9),
    ])
    _insert(conn, 'ext_quest_l10n', ['quest_id', 'locale', 'name'], [
        (1338, 'esES', 'Un pedido de Pico Tormenta'),
        (1338, 'enUS', 'A Request from Ironforge'),
        (255, 'esES', 'Mercenarios'),
        (255, 'enUS', 'Mercenaries'),
        (96393, 'esES', 'Incursión en la Antigua Forjaz'),
        (96393, 'enUS', 'Old Ironforge Incursion'),
        (91775, 'esES', 'Devolución de libros'),
        (91775, 'enUS', 'Book Return'),
        (91776, 'esES', 'Matar troggs'),
        (91776, 'enUS', 'Kill Troggs'),
        (91777, 'esES', 'Amenaza babosa'),
        (91777, 'enUS', 'Slime Threat'),
        (91778, 'esES', 'Amenaza kobold'),
        (91778, 'enUS', 'Kobold Threat'),
        (91779, 'esES', 'Amenaza fúngica'),
        (91779, 'enUS', 'Fungal Threat'),
        (92001, 'esES', 'Eco repetido'),
        (92001, 'enUS', 'Echo Repeat'),
        (92002, 'esES', 'Eco repetido'),
        (92002, 'enUS', 'Echo Repeat'),
        (79092, 'esES', 'Diario de investigación del archimago Theocritus'),
        (79092, 'enUS', 'Archmage Theocritus Research Journal'),
    ])
    _insert(conn, 'ext_quest_starters', ['quest_id', 'entity_type', 'entity_id'], [
        (1338, 'npc', 1343),
        (96393, 'npc', 264936),
        (79092, 'npc', 211022),
        (79092, 'npc', 211033),
        (79092, 'object', 386759),
        (92001, 'npc', 7000),
        (92002, 'npc', 258098),
    ])
    _insert(conn, 'ext_quest_finishers', ['quest_id', 'entity_type', 'entity_id'], [
        (1338, 'npc', 5413),
        (96393, 'npc', 2784),
        (79092, 'npc', 211022),
        (79092, 'npc', 211033),
    ])
    _insert(conn, 'ext_quest_objective_items',
            ['quest_id', 'position', 'item_id', 'text', 'icon_type'], [
        (91775, 0, 248001, 'Álbum de fotos', None),
        (91775, 1, 248002, 'Libro perdido', None),
    ])
    _insert(conn, 'ext_quest_objective_creatures',
            ['quest_id', 'position', 'npc_id', 'text', 'icon_type'], [
        (91776, 0, 1162, 'Trog C', None),
        (91776, 1, 900003, 'Criatura sin posición', None),
        (91776, 2, 900005, 'Criatura viajera', None),
        (91778, 0, 900004, 'Kobold', None),
    ])
    _insert(conn, 'ext_npcs', ['npc_id', 'min_level', 'max_level', 'friendly_to_faction'], [
        (1343, 10, 10, 'A'),
        (5413, 30, 30, 'A'),
        (264936, 13, 13, 'A'),
        (2784, 63, 63, 'A'),
        (4991, 60, 60, 'A'),
        (258098, 60, 60, 'A'),
        (7000, 60, 60, 'H'),
        (211022, 9, 9, 'H'),
        (211033, 9, 9, 'A'),
        (900005, 5, 5, None),
        (6001, 60, 60, 'A'),
        (6002, 60, 60, 'A'),
        (6003, 60, 60, 'H'),
        (6004, 60, 60, 'A'),
        (6005, 60, 60, 'A'),
        (6006, 60, 60, 'A'),
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
        (211022, 'esES', 'Owen Thadd', None),
        (211022, 'enUS', 'Owen Thadd', None),
        (211033, 'esES', 'Garion Wendell', None),
        (211033, 'enUS', 'Garion Wendell', None),
        (900005, 'esES', 'Criatura viajera', None),
        (900005, 'enUS', 'Travelling creature', None),
        (6001, 'esES', 'Olivia Ladoquemao', 'Banquero'),
        (6001, 'enUS', 'Olivia Ladoquemao', 'Banker'),
        (6002, 'esES', 'Newton Ladoquemao', 'Banquero'),
        (6002, 'enUS', 'Newton Ladoquemao', 'Banker'),
        (6003, 'esES', 'Horgar Ladoquemao', 'Banquero'),
        (6003, 'enUS', 'Horgar Ladoquemao', 'Banker'),
        (6004, 'esES', 'Reese Langston', 'Tabernero'),
        (6004, 'enUS', 'Reese Langston', 'Innkeeper'),
        (6005, 'esES', 'Arnold Leland', f'Instructor{NBSP}de{NBSP}pesca'),
        (6005, 'enUS', 'Arnold Leland', 'Fishing Trainer'),
        (6006, 'esES', 'Dungar Tragolargo', f'Maestro{NBSP}de{NBSP}grifos'),
        (6006, 'enUS', 'Dungar Tragolargo', 'Gryphon Master'),
        (8001, 'esES', 'Jabalí montés', None),
        (8001, 'enUS', 'Mountain Boar', None),
        (8002, 'esES', 'Rondador del bosque', None),
        (8002, 'enUS', 'Forest Stalker', None),
        (8003, 'esES', 'Lobo superior', None),
        (8003, 'enUS', 'Greater Wolf', None),
        (8004, 'esES', 'Bestia sin familia', None),
        (8004, 'enUS', 'Familyless Beast', None),
        (1163, 'esES', 'Trog A', None),
        (1197, 'esES', 'Trog B', None),
        (1162, 'esES', 'Trog C', None),
        (900004, 'esES', 'Kobold', None),
        (900004, 'enUS', 'Kobold', None),
    ])
    _insert(conn, 'ext_npc_spawns', ['npc_id', 'zone_id', 'spawn_idx', 'x', 'y'], [
        (1343, 38, 1, 24.8, 18.4),
        (5413, 1519, 1, 64.6, 37.2),
        (264936, 1, 1, 64.87, 58.47),
        (2784, 1537, 1, 39.09, 56.2),
        (258098, 1537, 1, 47.1, 13.8),
        (7000, 1637, 1, 10.0, 20.0),
        (211022, 1497, 1, 60.0, 40.0),
        (211033, 1519, 1, 48.9, 86.5),
        (900005, 40, 1, 20.0, 30.0),
        (900005, 38, 2, 25.0, 35.0),
        (6001, 1519, 1, 78.1, 19.2),
        (6002, 1519, 1, 77.8, 18.9),
        (6003, 1519, 1, 70.0, 10.0),
        (6004, 1519, 1, 60.2, 75.3),
        (6005, 1519, 1, 55.1, 56.2),
        (6006, 1519, 1, 66.3, 77.4),
        (8001, 12, 1, 45.0, 67.0),
        (8002, 12, 1, 51.0, 72.0),
        (8003, 12, 1, 60.0, 80.0),
        (8004, 12, 1, 62.0, 82.0),
        (1163, 38, 1, 10.0, 20.0),
        (1197, 38, 1, 11.0, 21.0),
        (1162, 38, 1, 12.0, 22.0),
        (900004, 38, 1, 15.0, 25.0),
    ])
    _insert(conn, 'ext_zones', ['group_id', 'area_id', 'name_enUS', 'name_esES'], [
        (0, 1, 'Dun Morogh', 'Dun Morogh'),
        (0, 12, 'Elwynn Forest', 'Bosque de Elwynn'),
        (0, 14, 'Durotar', 'Durotar'),
        (0, 38, 'Loch Modan', 'Loch Modan'),
        (0, 40, 'Westfall', 'Páramos de Poniente'),
        (0, 44, 'Redridge Mountains', 'Montañas Crestagrana'),
        (0, 85, 'Tirisfal Glades', 'Claros de Tirisfal'),
        (0, 141, 'Teldrassil', 'Teldrassil'),
        (0, 148, 'Darkshore', 'Costa Oscura'),
        (0, 1519, 'Stormwind City', 'Ciudad de Ventormenta'),
        (0, 1537, 'Ironforge', 'Forjaz'),
        (0, 1497, 'Undercity', 'Entrañas'),
        (0, 16593, 'Zephras Isle', 'Isla de Zephras'),
        (1, 1637, 'Orgrimmar', 'Orgrimmar'),
        (0, 4081, 'The Dawnchaser', 'El Cazador del Albor'),
    ])
    _insert(conn, 'AreaTable', ['ID', 'AreaName_lang', 'ParentAreaID',
                                'FactionGroupMask'], [
        (12, 'Elwynn Forest', 0, 2),
        (14, 'Durotar', 0, 4),
        (85, 'Tirisfal Glades', 0, 4),
        (141, 'Teldrassil', 0, 2),
        (16593, 'Zephras Isle', 0, 0),
        (1519, 'Stormwind City', 0, 2),
        (1537, 'Ironforge', 0, 2),
        (1637, 'Orgrimmar', 0, 4),
    ])
    _insert(conn, 'CreatureFamily', ['ID', 'Name_lang', 'Name_lang_esES'], [
        (1, 'Boar', 'Jabalí'),
        (2, 'Spider', 'Araña'),
        (3, 'Wolf', 'Lobo'),
    ])
    _insert(conn, 'obs_wdc_npc',
            ['npc_id', 'nombre', 'nivel_min', 'nivel_max', 'clasificacion',
             'tipo', 'familia', 'vida', 'reaccion'], [
        (8001, 'Jabalí montés', 10, 11, 'Normal', 'Bestia', 'Jabalí', 100, 'Neutral'),
        (8002, 'Rondador del bosque', 10, 11, 'Normal', 'Bestia', 'Araña', 90, 'Neutral'),
        (8003, 'Lobo superior', 12, 13, 'Normal', 'Bestia', 'Lobo', 110, 'Neutral'),
        (8004, 'Bestia sin familia', 1, 2, 'Normal', 'Bestia', '', 50, 'Neutral'),
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
        (248001, 'esES', 'Álbum de fotos'),
        (248001, 'enUS', 'Photo Album'),
        (248002, 'esES', 'Libro perdido'),
        (248002, 'enUS', 'Lost Book'),
        (248003, 'esES', 'Cofre de libros'),
        (248003, 'enUS', 'Book Chest'),
    ])
    _insert(conn, 'ext_item_object_drops', ['item_id', 'position', 'object_id'], [
        (248003, 0, 900001),
    ])
    _insert(conn, 'ext_object_l10n', ['object_id', 'locale', 'name'], [
        (900001, 'esES', 'Cofre de libros'),
        (900001, 'enUS', 'Book Chest'),
        (900002, 'esES', 'Objeto sin coordenadas'),
        (900002, 'enUS', 'Object without coordinates'),
        (386759, 'esES', 'Library Book'),
        (386759, 'enUS', 'Library Book'),
    ])
    _insert(conn, 'ext_object_spawns', ['object_id', 'zone_id', 'spawn_idx', 'x', 'y',
                                        'phase'], [
        (900001, 40, 1, 42.5, 71.7, 0),
        (900002, 40, 1, -1.0, -1.0, 0),
        (386759, 1519, 1, 50.0, 85.0, 0),
    ])
    _insert(conn, 'v_zona_niveles', ['area_id', 'nombre', 'nombre_en', 'nivel_min',
                                     'nivel_max', 'pnj', 'origen'], [
        (44, 'Montañas Crestagrana', 'Redridge Mountains', 16, 26, 1351, 'deducido'),
        (1519, 'Ciudad de Ventormenta', 'Stormwind City', 1, 60, 3725, 'deducido'),
        (38, 'Loch Modan', 'Loch Modan', 11, 20, 840, 'deducido'),
        (40, 'Páramos de Poniente', 'Westfall', 11, 20, 800, 'deducido'),
        (17, 'Los Baldíos', 'The Barrens', 12, 28, 900, 'deducido'),
        (2437, 'Sima Ígnea', 'Ragefire Chasm', 14, 16, 50, 'deducido'),
        (12, 'Bosque de Elwynn', 'Elwynn Forest', 2, 15, 1200, 'deducido'),
        (14, 'Durotar', 'Durotar', 4, 12, 1000, 'deducido'),
        (85, 'Claros de Tirisfal', 'Tirisfal Glades', 4, 13, 900, 'deducido'),
        (141, 'Teldrassil', 'Teldrassil', 4, 12, 800, 'deducido'),
        (16593, 'Isla de Zephras', 'Zephras Isle', 4, 11, 500, 'deducido'),
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
        (1163, 248001, None, None, 100.0, 'questie'),
        (1197, 248002, None, None, 100.0, 'questie'),
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


def test_quest_objective_item_drops(db):
    facts = retrieve(_message('¿Devolución de libros?'), db)
    text = _text(facts)
    assert 'Devolución de libros' in text
    assert 'Trog A en Loch Modan (10.0, 20.0) (100 %)' in text
    assert 'Trog B en Loch Modan (11.0, 21.0) (100 %)' in text
    assert 'quest:91775' in facts.sources
    assert 'item:248001' in facts.sources
    assert 'item:248002' in facts.sources
    assert text.count('Trog A') == 1


def test_quest_kill_objective(db):
    facts = retrieve(_message('¿Matar troggs?'), db)
    text = _text(facts)
    assert 'matar Trog C en Loch Modan (12.0, 22.0).' in text
    assert 'matar Criatura sin posición (ubicación desconocida en la base).' in text
    assert 'npc:1162' in facts.sources
    assert 'npc:900003' in facts.sources


def test_item_line_with_object_sources(db):
    item = db.item_sources(248003)
    assert item['drops'] == []
    line = _item_line(item, 'es')
    assert 'se recoge de: Cofre de libros en Páramos de Poniente (42.5, 71.7)' in line
    item['objects'][0]['object'] = 'Book Chest'
    item['objects'][0]['zone'] = 'Westfall'
    assert 'gathered from: Book Chest in Westfall (42.5, 71.7)' in _item_line(item, 'en')


class _QuestDbWithoutObjectiveIds:
    def __init__(self):
        self.item_source_calls = []

    def find_quest(self, *args, **kwargs):
        return {
            'id': 7,
            'name': 'Sin objetivos',
            'level': 10,
            'required_level': 10,
            'starters': [],
            'finishers': [],
            'objective_items': [],
        }

    def quest_details(self, *args, **kwargs):
        return None

    def item_sources(self, *args, **kwargs):
        self.item_source_calls.append(args)
        return None


def test_quest_without_objective_item_ids_keeps_working():
    fake = _QuestDbWithoutObjectiveIds()
    facts = Facts()
    _detect_entities(facts, fake, [{'kind': 'quest', 'id': 7, 'name': 'Sin objetivos'}],
                     '', 'es', {})
    assert facts.lines == ['Misión «Sin objetivos» (nivel 10, requiere 10).']
    assert facts.sources == ['quest:7']
    assert fake.item_source_calls == []


def test_item_line_uses_drop_coordinates():
    item = {
        'name': 'Libro perdido',
        'drops': [
            {'npc': 'Nimsy', 'zone': 'Bosque de Elwynn', 'x': 41.6, 'y': 79.9,
             'rate': 100},
        ],
    }
    assert 'Nimsy en Bosque de Elwynn (41.6, 79.9) (100 %)' in _item_line(item, 'es')
    item['drops'][0]['zone'] = 'Elwynn Forest'
    assert 'Nimsy in Elwynn Forest (41.6, 79.9) (100 %)' in _item_line(item, 'en')


def test_item_line_without_coordinates_keeps_current_format():
    item = {
        'name': 'Libro perdido',
        'drops': [{'npc': 'Nimsy', 'zone': 'Bosque de Elwynn', 'rate': 100}],
    }
    line = _item_line(item, 'es')
    assert 'Nimsy en Bosque de Elwynn (100 %)' in line
    assert '(41.6' not in line


def test_active_quest_ids_handles_entries():
    ctx = {'quests': [
        ['A', 10, 0, 123],
        ['B', 10, 0, 456.0],
        ['C', 10, 0, None],
        ['D', 10, 0],
        ['E', 10, 0, 0],
        ['F', 10, 0, 78.5],
        ['G', 10, 0, '123'],
        ['H', 10, 0, True],
    ]}
    assert _active_quest_ids(ctx) == [123, 456]


def test_active_quest_vague_book_reference(db):
    ctx = dict(CTX)
    ctx['quests'] = [
        ['Devolución de libros', 12, 0, 91775],
        ['Amenaza babosa', 12, 0, 91777],
    ]
    facts = retrieve(_message('¿Quién suelta el libro?', ctx=ctx), db)
    text = _text(facts)
    assert 'La pregunta parece referirse a tu misión activa «Devolución de libros».' in text
    assert 'Amenaza babosa' not in text
    assert 'Libro perdido' in text
    assert 'item:248002' in facts.sources


def test_active_quest_reference_uses_title_without_id(db):
    ctx = dict(CTX)
    ctx['quests'] = [['Devolución de libros', 12, 0]]
    facts = retrieve(_message('¿Quién suelta el libro?', ctx=ctx), db)
    assert 'La pregunta parece referirse a tu misión activa «Devolución de libros».' in _text(facts)
    assert 'item:248002' in facts.sources


def test_active_quest_vague_kobold_reference(db):
    ctx = dict(CTX)
    ctx['quests'] = [['Amenaza kobold', 12, 0, 91778]]
    facts = retrieve(_message('¿Dónde están esos kobolds?', ctx=ctx), db)
    text = _text(facts)
    assert 'La pregunta parece referirse a tu misión activa «Amenaza kobold».' in text
    assert 'matar Kobold en Loch Modan (15.0, 25.0).' in text
    assert 'npc:900004' in facts.sources


def test_active_quest_reference_keeps_two_tied(db):
    ctx = dict(CTX)
    ctx['quests'] = [
        ['Amenaza babosa', 12, 0, 91777],
        ['Amenaza kobold', 12, 0, 91778],
    ]
    facts = retrieve(_message('¿Dónde está la amenaza?', ctx=ctx), db)
    text = _text(facts)
    assert 'La pregunta parece referirse a tu misión activa «Amenaza babosa».' in text
    assert 'La pregunta parece referirse a tu misión activa «Amenaza kobold».' in text


def test_active_quest_reference_ignores_common_tokens(db):
    ctx = dict(CTX)
    ctx['quests'] = [
        ['Amenaza babosa', 12, 0, 91777],
        ['Amenaza kobold', 12, 0, 91778],
        ['Amenaza fúngica', 12, 0, 91779],
    ]
    facts = retrieve(_message('¿Dónde está la amenaza?', ctx=ctx), db)
    assert facts.lines == []
    assert not any(source.startswith('quest:') for source in facts.sources)


def test_active_quest_reference_skips_named_quest(db):
    ctx = dict(CTX)
    ctx['quests'] = [['Devolución de libros', 12, 0, 91775]]
    facts = retrieve(_message('¿Dónde entrego Devolución de libros?', ctx=ctx), db)
    assert not any('parece referirse' in line for line in facts.lines)
    assert 'quest:91775' in facts.sources


def test_named_same_quest_prefers_active_id(db):
    ctx = dict(CTX)
    ctx['quests'] = [['Eco repetido', 20, 0, 92002]]
    facts = retrieve(_message('¿Qué es Eco repetido?', ctx=ctx), db)
    assert 'quest:92002' in facts.sources
    assert 'quest:92001' not in facts.sources


def test_active_quest_reference_needs_content_tokens(db):
    facts = retrieve(_message('¿Dónde está eso?'), db)
    assert not any('parece referirse' in line for line in facts.lines)

    ctx = dict(CTX)
    ctx['quests'] = [['Devolución de libros', 12, 0, 91775]]
    facts = retrieve(_message('¿Dónde está eso?', ctx=ctx), db)
    assert not any('parece referirse' in line for line in facts.lines)


def test_flights_from_question(db):
    facts = retrieve(_message('¿Adónde puedo volar desde Forjaz?'), db)
    text = _text(facts)
    assert 'Vuelos desde Forjaz:' in text
    assert 'Thelsamar, Loch Modan (1 de plata y 10 de cobre)' in text
    assert 'Orgrimmar' not in text
    assert any(source.startswith('flights_from:') for source in facts.sources)


def test_flight_cost_question(db):
    facts = retrieve(_message('¿Cuánto cuesta volar de Forjaz a Thelsamar?'), db)
    text = _text(facts)
    assert 'Vuelo Forjaz -> Thelsamar, Loch Modan: 1 de plata y 10 de cobre' in text
    assert facts.missing == []
    assert any(source.startswith('flight_cost:') for source in facts.sources)


def test_route_question_without_route_data_has_no_line(db):
    facts = retrieve(_message('¿Cómo voy de Forjaz a Auberdine?'), db)
    text = _text(facts)
    assert 'Vuelos desde' not in text
    assert 'transporte' not in text.lower()
    assert 'Ruta más rápida' not in text
    assert 'ruta completa entre Forjaz y Auberdine (aún no está en la base)' not in facts.missing


def test_english_zone_question(db):
    facts = retrieve(_message('What level is Westfall?', lang='enUS'), db)
    text = _text(facts)
    assert 'Zone Westfall: levels 11-20' in text


def test_quest_line_filters_starters_and_finishers_by_faction(db):
    quest = db.find_quest(79092)
    alliance = _quest_line(quest, 'es', ctx={'fac': 'Alianza', 'zone': 'Forjaz'})
    assert 'Garion Wendell' in alliance
    assert 'Owen Thadd' not in alliance
    assert 'Library Book' in alliance
    assert 'se entrega a Garion Wendell' in alliance

    horde = _quest_line(quest, 'es', ctx={'fac': 'Horda', 'zone': 'Orgrimmar'})
    assert 'Owen Thadd' in horde
    assert 'Garion Wendell' not in horde
    assert 'Library Book' in horde
    assert 'se entrega a Owen Thadd' in horde

    english = _quest_line(quest, 'en', ctx={'fac': 'Alliance',
                                            'zone': 'Stormwind City'})
    assert 'given by Garion Wendell' in english
    assert ' or Library Book' in english


def test_quest_line_keeps_old_order_without_faction(db):
    quest = db.find_quest(79092)
    line = _quest_line(quest, 'es', ctx={'zone': 'Forjaz'})
    assert 'Owen Thadd' in line
    assert 'Garion Wendell' in line
    assert line.index('Owen Thadd') < line.index('Garion Wendell')
    assert 'Library Book' not in line

    stormwind = _quest_line(quest, 'es', ctx={'zone': 'Ciudad de Ventormenta'})
    assert stormwind.index('Garion Wendell') < stormwind.index('Owen Thadd')


def test_entities_for_player_falls_back_when_everything_is_filtered():
    entities = [{
        'type': 'npc',
        'name': 'Only Horde',
        'faction': 'H',
        'locations': [{'zone': 'Orgrimmar', 'x': 1.0, 'y': 2.0}],
    }]
    selected = _entities_for_player(entities, {'fac': 'Alianza'})
    assert [entity['name'] for entity in selected] == ['Only Horde']


def test_named_quest_variant_follows_faction(db):
    ctx = dict(CTX)
    ctx['fac'] = 'Alianza'
    facts = retrieve(_message('¿Qué es Eco repetido?', ctx=ctx), db)
    assert 'quest:92002' in facts.sources
    assert 'quest:92001' not in facts.sources

    ctx['fac'] = 'Horda'
    facts = retrieve(_message('¿Qué es Eco repetido?', ctx=ctx), db)
    assert 'quest:92001' in facts.sources
    assert 'quest:92002' not in facts.sources


def test_retrieve_quest_giver_follows_faction(db):
    name = 'Diario de investigación del archimago Theocritus'
    ctx = dict(CTX)
    ctx['fac'] = 'Alianza'
    text = _text(retrieve(_message(f'¿Quién da {name}?', ctx=ctx), db))
    assert 'Garion Wendell' in text
    assert 'Owen Thadd' not in text
    assert 'Library Book' in text

    ctx['fac'] = 'Horda'
    text = _text(retrieve(_message(f'¿Quién da {name}?', ctx=ctx), db))
    assert 'Owen Thadd' in text
    assert 'Garion Wendell' not in text


def test_objective_locations_prefer_current_zone(db):
    ctx = dict(CTX)
    ctx['zone'] = 'Loch Modan'
    facts = retrieve(_message('¿Matar troggs?', ctx=ctx), db)
    line = next(line for line in facts.lines if 'Criatura viajera' in line)
    assert 'Loch Modan (25.0, 35.0)' in line
    assert line.index('Loch Modan') < line.index('Páramos de Poniente')


def test_item_line_orders_current_zone_first():
    item = {
        'name': 'Objeto de prueba',
        'drops': [
            {'npc': 'Drop Westfall', 'zone': 'Westfall', 'x': 1.0, 'y': 2.0, 'rate': 1},
            {'npc': 'Drop Loch', 'zone': 'Loch Modan', 'x': 3.0, 'y': 4.0, 'rate': 1},
        ],
        'objects': [
            {'object': 'Object Westfall', 'zone': 'Westfall', 'x': 5.0, 'y': 6.0},
            {'object': 'Object Loch', 'zone': 'Loch Modan', 'x': 7.0, 'y': 8.0},
        ],
    }
    line = _item_line(item, 'es', {'zone': 'Loch Modan'})
    assert line.index('Drop Loch') < line.index('Drop Westfall')
    assert line.index('Object Loch') < line.index('Object Westfall')


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


def test_service_bank_in_current_zone(db):
    ctx = dict(CTX)
    ctx['zone'] = 'Ciudad de Ventormenta'
    facts = retrieve(_message('¿Dónde está el banco?', ctx=ctx), db)
    text = _text(facts)
    assert 'Banquero en Ciudad de Ventormenta:' in text
    assert 'Olivia Ladoquemao (78.1, 19.2)' in text
    assert 'Newton Ladoquemao (77.8, 18.9)' in text
    assert 'Horgar Ladoquemao' not in text
    assert 'service:banquer' in facts.sources


def test_service_fishing_trainer_in_named_city(db):
    facts = retrieve(_message('¿dónde aprendo a pescar en Ventormenta?'), db)
    text = _text(facts)
    assert 'Instructor de pesca en Ciudad de Ventormenta:' in text
    assert 'Arnold Leland (55.1, 56.2)' in text
    assert 'service:instructor de pesca' in facts.sources


def test_service_faction_filter(db):
    ctx = dict(CTX)
    ctx['zone'] = 'Ciudad de Ventormenta'
    ctx['fac'] = 'Horda'
    facts = retrieve(_message('¿Dónde está el banco?', ctx=ctx), db)
    text = _text(facts)
    assert 'Horgar Ladoquemao' in text
    assert 'Olivia Ladoquemao' not in text
    assert 'Newton Ladoquemao' not in text


def test_service_missing_data(db):
    ctx = dict(CTX)
    ctx['zone'] = 'Ciudad de Ventormenta'
    facts = retrieve(_message('¿Dónde está el maestro de establos?', ctx=ctx), db)
    assert any('No hay datos de maestro de establos' in message
               for message in facts.missing)
    assert not any('service:' in source for source in facts.sources)


def test_service_english_question(db):
    ctx = dict(CTX)
    ctx['zone'] = 'Stormwind City'
    facts = retrieve(_message('Where is the bank?', lang='enUS', ctx=ctx), db)
    text = _text(facts)
    assert 'Banker in Stormwind City:' in text
    assert 'Olivia Ladoquemao (78.1, 19.2)' in text


def test_service_flight_master(db):
    ctx = dict(CTX)
    ctx['zone'] = 'Ciudad de Ventormenta'
    facts = retrieve(_message('¿Dónde está el maestro de vuelo?', ctx=ctx), db)
    text = _text(facts)
    assert 'Maestro de vuelo en Ciudad de Ventormenta:' in text
    assert 'Dungar Tragolargo' in text


def test_service_absent_keyword(db):
    facts = retrieve(_message('¿Dónde está el rey?'), db)
    assert not any(source.startswith('service:') for source in facts.sources)
    assert not any('Banquero' in line for line in facts.lines)


def test_panorama_filters_opposite_faction_zones(db):
    ctx = dict(CTX)
    ctx.update(lvl=10, fac='Alianza', zone='Bosque de Elwynn')
    facts = retrieve(_message('¿Qué zonas me tocan a mi nivel?', ctx=ctx), db)
    text = _text(facts)
    assert 'Zonas para nivel 10:' in text
    assert 'Durotar' not in text
    assert 'Claros de Tirisfal' not in text
    assert 'Teldrassil' in text
    assert 'Isla de Zephras' in text
    assert 'Bosque de Elwynn' in text


def test_panorama_keeps_all_zones_without_faction(db):
    ctx = dict(CTX)
    ctx.update(lvl=10, fac=None, zone='Bosque de Elwynn')
    facts = retrieve(_message('¿Qué zonas me tocan a mi nivel?', ctx=ctx), db)
    text = _text(facts)
    assert 'Durotar' in text
    assert 'Claros de Tirisfal' in text


def test_explicit_opposite_zone_is_not_filtered(db):
    ctx = dict(CTX)
    ctx.update(lvl=10, fac='Alianza')
    facts = retrieve(_message('¿Qué nivel tiene Durotar?', ctx=ctx), db)
    assert 'Durotar' in _text(facts)


def test_hunter_pet_question_lists_zone_beasts(db):
    ctx = dict(CTX)
    ctx.update(lvl=10, fac='Alianza', zone='Bosque de Elwynn', **{'class': 'Cazador'})
    facts = retrieve(
        _message('Ya tengo nivel 10 y puedo coger una mascota. ¿Cuál me recomiendas?',
                 ctx=ctx), db)
    text = _text(facts)
    assert 'Bestias domesticables observadas en Bosque de Elwynn hasta tu nivel (10):' in text
    assert 'Jabalí montés (Jabalí, 10-11) (45.0, 67.0)' in text
    assert 'Rondador del bosque (Araña, 10-11) (51.0, 72.0)' in text
    assert 'Lobo superior' not in text
    assert 'Bestia sin familia' not in text
    assert 'pets:12' in facts.sources


def test_hunter_pet_question_english(db):
    ctx = dict(CTX)
    ctx.update(lvl=10, fac='Alianza', zone='Elwynn Forest', **{'class': 'Hunter'})
    facts = retrieve(_message('Which pet should I tame?', lang='enUS', ctx=ctx), db)
    text = _text(facts)
    assert 'Tameable beasts observed in Elwynn Forest up to your level (10):' in text
    assert 'Mountain Boar (Boar, 10-11)' in text
    assert 'Forest Stalker (Spider, 10-11)' in text


def test_non_hunter_pet_question_does_nothing(db):
    ctx = dict(CTX)
    ctx.update(lvl=10, fac='Alianza', zone='Bosque de Elwynn', **{'class': 'Chamán'})
    facts = retrieve(
        _message('Ya tengo nivel 10 y puedo coger una mascota. ¿Cuál me recomiendas?',
                 ctx=ctx), db)
    assert not any('Bestias domesticables' in line for line in facts.lines)
    assert not any(source.startswith('pets:') for source in facts.sources)


def test_hunter_pet_missing_data(db):
    ctx = dict(CTX)
    ctx.update(lvl=10, fac='Alianza', zone='Páramos de Poniente',
               **{'class': 'Cazador'})
    facts = retrieve(_message('¿Qué mascota me recomiendas?', ctx=ctx), db)
    assert any('No hay bestias domesticables observadas en Páramos de Poniente'
               in message for message in facts.missing)
    assert not any(source.startswith('pets:') for source in facts.sources)


def test_render_limit_keeps_priority(db):
    facts = retrieve(_message('¿Qué zonas me tocan a mi nivel?'), db)
    rendered = facts.render('esES')
    assert rendered.startswith('DATOS VERIFICADOS')
    assert len(rendered) <= 1600


class _PlaceQuestDb:
    def find_quest(self, name_or_id, lang='es', player_level=None,
                   prefer_ids=None, faction=None):
        return {'id': 93001, 'name': 'Un envío para Ventormenta', 'level': 7,
                'objective_items': [], 'objective_item_ids': [], 'objective_creatures': []}

    def quest_details(self, quest_id, lang='es'):
        return None


def test_active_quest_reference_ignores_place_names():
    ctx = {'quests': [['Un envío para Ventormenta', 7, 0, 93001]]}
    matches = [{'kind': 'zone', 'id': 1519, 'name': 'Ventormenta'}]
    facts = Facts()
    _detect_active_quest_reference(facts, _PlaceQuestDb(), '¿Cómo voy a Ventormenta?',
                                   'como voy a ventormenta', 'es', ctx, matches)
    assert facts.lines == []

    facts = Facts()
    _detect_active_quest_reference(facts, _PlaceQuestDb(), '¿Dónde dejo el envío?',
                                   'donde dejo el envio', 'es', ctx, [])
    assert any('parece referirse' in line for line in facts.lines)


def test_single_word_zone_match_only_for_main_zones(db):
    zone_id, _name = _zone_in_question(db, normalize('como consigo una mascota de cazador'),
                                       'es')
    assert zone_id is None
    zone_id, _name = _zone_in_question(db, normalize('el banco de ventormenta'), 'es')
    assert zone_id == 1519
