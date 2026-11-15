"""Pruebas de las consultas ampliadas de wowdata (zonas, mazmorras, rutas y botín)."""

from __future__ import annotations

import sqlite3

import pytest

from askforever.data.wowdb import WowDb, normalize, resolve_talent_text, talent_detail

NBSP = chr(0xA0)

SCHEMA = [
    'CREATE TABLE v_zona_niveles (area_id INTEGER, nombre TEXT, nombre_en TEXT, '
    'nivel_min INTEGER, nivel_max INTEGER, pnj INTEGER, origen TEXT)',
    'CREATE TABLE LFGDungeons (ID INTEGER, Name_lang TEXT, Name_lang_esES TEXT, '
    'TypeID INTEGER, MapID INTEGER, ContentTuningID INTEGER)',
    'CREATE TABLE contenttuning (ID INTEGER, MinLevelSquish INTEGER, '
    'MaxLevelSquish INTEGER, LfgMinLevel INTEGER, LfgMaxLevel INTEGER)',
    'CREATE TABLE ext_dungeons (area_id INTEGER, name_enUS TEXT, name_esES TEXT, '
    'parent_zone_id INTEGER)',
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
    'CREATE TABLE ext_npc_l10n (npc_id INTEGER, locale TEXT, name TEXT, sub_name TEXT)',
    'CREATE TABLE ext_npc_spawns (npc_id INTEGER, zone_id INTEGER, spawn_idx INTEGER, '
    'x REAL, y REAL)',
    'CREATE TABLE ext_zones (group_id INTEGER, area_id INTEGER, name_enUS TEXT, '
    'name_esES TEXT)',
    'CREATE TABLE v_ruta (ruta_id INTEGER, tipo TEXT, nodo_origen INTEGER, '
    'origen TEXT, nodo_destino INTEGER, destino TEXT, continente_origen INTEGER, '
    'continente_destino INTEGER, faccion TEXT, coste INTEGER, puntos INTEGER, '
    'longitud REAL, inicio_x REAL, inicio_y REAL, fin_x REAL, fin_y REAL, '
    'cerca_del_inicio TEXT, cerca_del_fin TEXT, visto_en_juego INTEGER, '
    'viajes_vistos INTEGER)',
    'CREATE TABLE TaxiNodes (__id INTEGER, ID INTEGER, Name_lang TEXT, '
    'Name_lang_esES TEXT, ContinentID INTEGER, MountCreatureID TEXT)',
    'CREATE TABLE ext_item_l10n (item_id INTEGER, locale TEXT, name TEXT)',
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
    'CREATE TABLE v_talentos_forever (NodeID INTEGER, TreeID INTEGER, SpellID INTEGER, '
    'nombre_es TEXT, nombre_en TEXT, class_id INTEGER, clase_es TEXT, clase_en TEXT, '
    'class_slug TEXT, rama_es TEXT, rama_en TEXT, tree_slug TEXT, '
    'puntos_requeridos INTEGER, talento_previo_node_id INTEGER, talento_previo_es TEXT, '
    'talento_previo_en TEXT, max_rank INTEGER, max_rank_cliente INTEGER, cambio TEXT, '
    'descripcion_es TEXT, descripcion_en_cliente TEXT, PosX INTEGER, PosY INTEGER, '
    'version TEXT, build TEXT)',
    'CREATE TABLE ext_icy_talento_rangos (node_id INTEGER, rank INTEGER, '
    'spell_id INTEGER, description_en TEXT)',
]


def _insert(conn, table, columns, rows):
    placeholders = ', '.join('?' for _ in columns)
    conn.executemany(f'INSERT INTO {table} ({", ".join(columns)}) VALUES ({placeholders})', rows)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'wow.sqlite'
    conn = sqlite3.connect(path)
    for statement in SCHEMA:
        conn.execute(statement)

    _insert(conn, 'v_zona_niveles', ['area_id', 'nombre', 'nombre_en', 'nivel_min',
                                     'nivel_max', 'pnj', 'origen'], [
        (44, 'Montañas Crestagrana', 'Redridge Mountains', 16, 26, 1351, 'deducido'),
        (1519, 'Ciudad de Ventormenta', 'Stormwind City', 1, 60, 3725, 'deducido'),
        (38, 'Loch Modan', 'Loch Modan', 11, 20, 840, 'deducido'),
        (40, 'Páramos de Poniente', 'Westfall', 11, 20, 800, 'deducido'),
        (17, 'Los Baldíos', 'The Barrens', 12, 28, 900, 'deducido'),
        (2437, 'Sima Ígnea', 'Ragefire Chasm', 14, 16, 50, 'deducido'),
        (406, 'Sierra Espolón', 'Stonetalon Mountains', 15, 28, 700, 'deducido'),
        (130, 'Bosque de Argénteos', 'Silverpine Forest', 12, 25, 600, 'deducido'),
        (148, 'Costa Oscura', 'Darkshore', 12, 21, 500, 'deducido'),
    ])
    _insert(conn, 'LFGDungeons', ['ID', 'Name_lang', 'Name_lang_esES', 'TypeID',
                                  'MapID', 'ContentTuningID'], [
        (5, 'Deadmines', 'Minas de la Muerte', 0, 36, 5240),
        (1, 'Wailing Caverns', 'Cuevas de los Lamentos', 0, 43, 5254),
        (11, 'Stormwind Stockades', 'Mazmorras de Ventormenta', 0, 34, 5250),
        (13, 'Gnomeregan', 'Gnomeregan', 0, 0, 5242),
        (47, 'Molten Core', 'Núcleo de Magma', 0, 409, 4509),
    ])
    _insert(conn, 'contenttuning', ['ID', 'MinLevelSquish', 'MaxLevelSquish',
                                    'LfgMinLevel', 'LfgMaxLevel'], [
        (5240, 16, 16, 0, 0),
        (5254, 17, 17, 0, 0),
        (5250, 0, 0, 23, 23),
        (5242, 25, 25, 0, 0),
        (4509, 60, 60, 0, 0),
    ])
    _insert(conn, 'ext_dungeons', ['area_id', 'name_enUS', 'name_esES', 'parent_zone_id'], [
        (1581, 'The Deadmines', 'Las Minas de la Muerte', 40),
        (43, 'Wailing Caverns', 'Cuevas de los Lamentos', 17),
        (34, 'Stormwind Stockades', 'Mazmorras de Ventormenta', 1519),
        (721, 'Gnomeregan', 'Gnomeregan', 1),
        (2437, 'Ragefire Chasm', 'Sima Ígnea', 1637),
        (9998, 'Shadowfang Keep', 'Castillo de Colmillo Oscuro', 130),
        (9999, 'Razorfen Kraul', 'Horado Rajacieno', 17),
    ])
    _insert(conn, 'v_jefe_mazmorra', ['encuentro_id', 'map_id', 'instancia', 'dificultad',
                                      'orden', 'nombre', 'nombre_en', 'npc_id', 'zone_id',
                                      'x', 'y'], [
        (2741, 36, 'Deadmines', 0, 0, "Rhahk'Zor", "Rhahk'Zor", 644, 1581, -1.0, -1.0),
        (2741, 36, 'Deadmines', 1, 0, "Rhahk'Zor", "Rhahk'Zor", 274298, None, None, None),
        (2742, 36, 'Deadmines', 0, 1000, 'Sneed', 'Sneed', 643, 1581, -1.0, -1.0),
        (2742, 36, 'Deadmines', 1, 1000, 'Sneed', 'Sneed', 643, 1581, -1.0, -1.0),
        (3676, 36, 'Deadmines', 0, 1500, 'Minero Johnson', 'Miner Johnson', 3586, 1581, -1.0, -1.0),
        (2743, 36, 'Deadmines', 0, 2000, 'Gilnid', 'Gilnid', 1763, 1581, -1.0, -1.0),
        (2744, 36, 'Deadmines', 0, 3000, 'Capitán Verdetez', 'Captain Greenskin', 647, 1581, -1.0, -1.0),
        (2745, 36, 'Deadmines', 0, 4000, 'Don Mamporro', 'Mr. Smite', 646, 1581, -1.0, -1.0),
        (2746, 36, 'Deadmines', 0, 5000, 'Cocinitas', 'Cookie', 645, 1581, -1.0, -1.0),
        (2747, 36, 'Deadmines', 0, 6000, 'Edwin VanCleef', 'Edwin VanCleef', 639, 1581, -1.0, -1.0),
        (3654, 43, 'Wailing Caverns', 0, 0, 'Lady Anacondra', 'Lady Anacondra', 3671, 718, -1.0, -1.0),
        (3655, 43, 'Wailing Caverns', 0, 1000, 'Lord Cobrahn', 'Lord Cobrahn', 3669, 718, -1.0, -1.0),
        (3656, 43, 'Wailing Caverns', 0, 2000, 'Kresh', 'Kresh', 3653, 718, -1.0, -1.0),
        (3657, 43, 'Wailing Caverns', 0, 3000, 'Lord Pythas', 'Lord Pythas', 3670, 718, -1.0, -1.0),
        (3658, 43, 'Wailing Caverns', 0, 4000, 'Skum', 'Skum', 3674, 718, -1.0, -1.0),
        (3659, 43, 'Wailing Caverns', 0, 5000, 'Lord Serpentis', 'Lord Serpentis', 3673, 718, -1.0, -1.0),
        (3660, 43, 'Wailing Caverns', 0, 6000, 'Verdan el Eterno', 'Verdan the Everliving', 5775, 718, -1.0, -1.0),
        (3661, 43, 'Wailing Caverns', 0, 7000, 'Mutanus el Devorador', 'Mutanus the Devourer', 3654, 718, -1.0, -1.0),
        (3661, 43, 'Wailing Caverns', 1, 7000, 'Mutanus el Devorador', 'Mutanus the Devourer', 3654, 718, -1.0, -1.0),
        (5000, 0, 'Gnomeregan', 0, 0, "Grubbis", 'Grubbis', 7361, 721, -1.0, -1.0),
        (5001, 0, 'Gnomeregan', 0, 1000, 'Viscous Fallout', 'Viscous Fallout', 7079, 721, -1.0, -1.0),
    ])
    _insert(conn, 'levelexperience', ['ID', 'Level', 'ContentSetID', 'Experience'], [
        (15, 15, 0, 14400),
        (16, 16, 0, 16000),
        (17, 17, 0, 17700),
    ])
    _insert(conn, 'v_mision', ['quest_id', 'titulo', 'nivel', 'xp', 'zona', 'objetivo',
                               'texto', 'origen'], [
        (255, 'Mercenarios', 19, 1800, 'Loch Modan', '["Mata 4 ogros."]', None, 'juego'),
        (256, 'Otra misión', 10, 500, 'Loch Modan', 'texto no JSON', None, 'juego'),
    ])
    _insert(conn, 'v_botin', ['npc_id', 'item_id', 'veces', 'muertes', 'porcentaje',
                              'origen'], [
        (1163, 2536, None, None, 50.0, 'questie'),
        (1197, 2536, None, None, 50.0, 'questie'),
        (1162, 2536, 5, 16, 31.25, 'juego'),
        (1161, 2536, 1, 12, 8.333333, 'juego'),
        (1163, 2536, 1, 10, 12.5, 'juego'),
    ])
    _insert(conn, 'v_npc', ['npc_id', 'nombre', 'nombre_en'], [
        (1163, 'Trog A', 'Trogg A'),
        (1197, 'Trog B', 'Trogg B'),
        (1162, 'Trog C', 'Trogg C'),
        (1161, 'Trog D', 'Trogg D'),
    ])
    _insert(conn, 'ext_npc_l10n', ['npc_id', 'locale', 'name', 'sub_name'], [
        (1163, 'esES', 'Trog A', None),
        (1162, 'esES', 'Trog C', None),
        (5001, 'esES', 'Olivia Ladoquemao', 'Banquero'),
        (5001, 'enUS', 'Olivia Ladoquemao', 'Banker'),
        (5002, 'esES', 'Newton Ladoquemao', 'Banquero'),
        (5002, 'enUS', 'Newton Ladoquemao', 'Banker'),
        (5003, 'esES', 'Horgar Ladoquemao', 'Banquero'),
        (5003, 'enUS', 'Horgar Ladoquemao', 'Banker'),
        (5004, 'esES', 'Arnold Leland', f'Instructor{NBSP}de{NBSP}pesca'),
        (5004, 'enUS', 'Arnold Leland', 'Fishing Trainer'),
        (7001, 'esES', 'Jabalí montés', None),
        (7001, 'enUS', 'Mountain Boar', None),
        (7002, 'esES', 'Rondador del bosque', None),
        (7002, 'enUS', 'Forest Stalker', None),
        (7003, 'esES', 'Lobo superior', None),
        (7003, 'enUS', 'Greater Wolf', None),
        (7004, 'esES', 'Bestia sin familia', None),
        (7004, 'enUS', 'Familyless Beast', None),
    ])
    _insert(conn, 'ext_npc_spawns', ['npc_id', 'zone_id', 'spawn_idx', 'x', 'y'], [
        (1163, 38, 1, 10.0, 20.0),
        (1197, 38, 1, 11.0, 21.0),
        (1162, 38, 1, 12.0, 22.0),
        (1161, 38, 1, 13.0, 23.0),
        (5001, 1519, 1, 78.1, 19.2),
        (5002, 1519, 1, 77.8, 18.9),
        (5003, 1519, 1, 70.0, 10.0),
        (5004, 1519, 1, 55.1, 56.2),
        (7001, 12, 1, 45.0, 67.0),
        (7002, 12, 1, 51.0, 72.0),
        (7003, 12, 1, 60.0, 80.0),
        (7004, 12, 1, 62.0, 82.0),
    ])
    _insert(conn, 'ext_zones', ['group_id', 'area_id', 'name_enUS', 'name_esES'], [
        (0, 12, 'Elwynn Forest', 'Bosque de Elwynn'),
        (0, 38, 'Loch Modan', 'Loch Modan'),
        (0, 40, 'Westfall', 'Páramos de Poniente'),
        (0, 1519, 'Stormwind City', 'Ciudad de Ventormenta'),
    ])
    _insert(conn, 'AreaTable', ['ID', 'AreaName_lang', 'ParentAreaID',
                                'FactionGroupMask'], [
        (12, 'Elwynn Forest', 0, 2),
        (14, 'Durotar', 0, 4),
        (33, 'Stranglethorn Vale', 0, 0),
        (85, 'Tirisfal Glades', 0, 4),
        (141, 'Teldrassil', 0, 2),
    ])
    _insert(conn, 'CreatureFamily', ['ID', 'Name_lang', 'Name_lang_esES'], [
        (1, 'Boar', 'Jabalí'),
        (2, 'Spider', 'Araña'),
        (3, 'Wolf', 'Lobo'),
    ])
    _insert(conn, 'obs_wdc_npc',
            ['npc_id', 'nombre', 'nivel_min', 'nivel_max', 'clasificacion',
             'tipo', 'familia', 'vida', 'reaccion'], [
        (7001, 'Jabalí montés', 10, 11, 'Normal', 'Bestia', 'Jabalí', 100, 'Neutral'),
        (7002, 'Rondador del bosque', 10, 11, 'Normal', 'Bestia', 'Araña', 90, 'Neutral'),
        (7003, 'Lobo superior', 12, 13, 'Normal', 'Bestia', 'Lobo', 110, 'Neutral'),
        (7004, 'Bestia sin familia', 1, 2, 'Normal', 'Bestia', '', 50, 'Neutral'),
    ])
    _insert(conn, 'TaxiNodes', ['__id', 'ID', 'Name_lang', 'Name_lang_esES',
                                'ContinentID', 'MountCreatureID'], [
        (2, 2, 'Stormwind, Elwynn', 'Ventormenta, Elwynn', 0, '[0, 541]'),
        (6, 6, 'Ironforge, Dun Morogh', 'Forjaz, Dun Morogh', 0, '[0, 541]'),
        (7, 7, 'Menethil Harbor, Wetlands', 'Puerto de Menethil, Los Humedales', 0, '[0, 541]'),
        (8, 8, 'Thelsamar, Loch Modan', 'Thelsamar, Loch Modan', 0, '[0, 541]'),
        (16, 16, 'Refuge Pointe, Arathi', 'Refugio de la Zaga, Arathi', 0, '[0, 541]'),
        (23, 23, 'Orgrimmar, Durotar', 'Orgrimmar, Durotar', 1, '[2224, 0]'),
        (26, 26, 'Auberdine, Darkshore', 'Auberdine, Costa Oscura', 1, '[0, 541]'),
        (27, 27, "Rut'theran Village, Teldrassil", "Aldea Rut'theran, Teldrassil", 1, '[0, 541]'),
        (36, 36, 'Generic, World target', 'Generic, World target', 0, '[0, 0]'),
        (50, 50, 'Transport, Menethil Ships', 'Transporte, Barcos de Menethil', 0, '[0, 0]'),
        (46, 46, 'Southshore Ferry, Hillsbrad', 'Embarcadero de Costasur, Trabalomas', 0, '[0, 0]'),
    ])
    _insert(conn, 'v_ruta', ['ruta_id', 'tipo', 'nodo_origen', 'origen', 'nodo_destino',
                             'destino', 'faccion', 'coste'], [
        (12, 'vuelo', 6, 'Ironforge, Dun Morogh', 2, 'Stormwind, Elwynn', 'Alianza', 50),
        (16, 'vuelo', 6, 'Ironforge, Dun Morogh', 8, 'Thelsamar, Loch Modan', 'Alianza', 110),
        (18, 'vuelo', 6, 'Ironforge, Dun Morogh', 7, 'Menethil Harbor, Wetlands', 'Alianza', 330),
        (31, 'vuelo', 6, 'Ironforge, Dun Morogh', 16, 'Refuge Pointe, Arathi', 'Alianza', 530),
        (400, 'vuelo', 6, 'Ironforge, Dun Morogh', 23, 'Orgrimmar, Durotar', 'Horda', 999),
        (401, 'vuelo', 6, 'Ironforge, Dun Morogh', 26, 'Auberdine, Darkshore', None, 0),
        (101, 'transporte (barco, zepelín, transbordador)', 26, 'Auberdine, Darkshore',
         27, "Rut'theran Village, Teldrassil", 'Alianza', 0),
        (102, 'transporte (barco, zepelín, transbordador)', 27, "Rut'theran Village, Teldrassil",
         26, 'Auberdine, Darkshore', 'Alianza', 0),
        (285, 'transporte (barco, zepelín, transbordador)', 23, 'Orgrimmar, Durotar',
         36, 'Generic, World target', 'Horda', 0),
        (290, 'transporte (barco, zepelín, transbordador)', 50, 'Transport, Menethil Ships',
         46, 'Southshore Ferry, Hillsbrad', None, 0),
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
    ])
    _insert(conn, 'ext_object_spawns', ['object_id', 'zone_id', 'spawn_idx', 'x', 'y',
                                        'phase'], [
        (900001, 40, 1, 42.5, 71.7, 0),
        (900002, 40, 1, -1.0, -1.0, 0),
    ])
    _insert(conn, 'ext_quests', ['quest_id', 'required_level', 'quest_level'], [
        (91775, 10, 12),
        (91776, 10, 12),
        (92001, 10, 10),
        (92002, 10, 20),
    ])
    _insert(conn, 'ext_quest_l10n', ['quest_id', 'locale', 'name'], [
        (91775, 'esES', 'Devolución de libros'),
        (91775, 'enUS', 'Book Return'),
        (91776, 'esES', 'Matar troggs'),
        (91776, 'enUS', 'Kill Troggs'),
        (92001, 'esES', 'Eco repetido'),
        (92001, 'enUS', 'Echo Repeat'),
        (92002, 'esES', 'Eco repetido'),
        (92002, 'enUS', 'Echo Repeat'),
    ])
    _insert(conn, 'ext_quest_starters', ['quest_id', 'entity_type', 'entity_id'], [
        (92001, 'npc', 7000),
        (92002, 'npc', 258098),
    ])
    _insert(conn, 'ext_npcs', ['npc_id', 'min_level', 'max_level', 'friendly_to_faction'], [
        (7000, 60, 60, 'H'),
        (258098, 60, 60, 'A'),
        (5001, 60, 60, 'A'),
        (5002, 60, 60, 'A'),
        (5003, 60, 60, 'H'),
        (5004, 60, 60, 'A'),
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
    ])
    _insert(conn, 'v_talentos_forever', [
        'NodeID', 'TreeID', 'SpellID', 'nombre_es', 'nombre_en', 'class_id',
        'clase_es', 'clase_en', 'class_slug', 'rama_es', 'rama_en', 'tree_slug',
        'puntos_requeridos', 'talento_previo_node_id', 'talento_previo_es',
        'talento_previo_en', 'max_rank', 'max_rank_cliente', 'cambio',
        'descripcion_es', 'descripcion_en_cliente', 'PosX', 'PosY', 'version', 'build',
    ], [
        (1, 1, 101, 'Entrenamiento en aguante', 'Endurance Training', 4,
         'Cazador', 'Hunter', 'hunter', 'Dominio de bestias', 'Beast Mastery',
         'beast-mastery', 0, None, None, None, 5, 5, 'changed',
         'Aumenta un $s1% la salud y la armadura de tus mascotas.',
         'Increases the Health and Armor of your pets by $s1%.', 10, 10, '1', '1'),
        (2, 2, 102, 'Tiro mortal', 'Mortal Shots', 4,
         'Cazador', 'Hunter', 'hunter', 'Puntería', 'Marksmanship',
         'marksmanship', 0, None, None, None, 5, 5, 'new',
         'Reduce un $s2% el daño y añade $s1 de daño.',
         'Adds $s1 damage and reduces damage by $s2%.', 20, 10, '1', '1'),
        (3, 3, 103, 'Flecha de la muerte', 'Kill Shot', 4,
         'Cazador', 'Hunter', 'hunter', 'Supervivencia', 'Survival',
         'survival', 0, None, None, None, 3, 3, 'new',
         'Aumenta un $s1% el daño.', 'Increases damage by $s1%.',
         30, 10, '1', '1'),
        (4, 2, 104, 'Puntería certera', 'True Shot', 4,
         'Cazador', 'Hunter', 'hunter', 'Puntería', 'Marksmanship',
         'marksmanship', 5, 2, 'Tiro mortal', 'Mortal Shots', 2, 2, None,
         'Aumenta un $s1% y reduce un $s2%.',
         'Increases $s1% and reduces $s2%.', 25, 20, '1', '1'),
    ])
    _insert(conn, 'ext_icy_talento_rangos',
            ['node_id', 'rank', 'spell_id', 'description_en'], [
        (1, 1, 101, 'Increases the Health and Armor of your pets by 3%.'),
        (1, 5, 101, 'Increases the Health and Armor of your pets by 15%.'),
        (2, 1, 102, 'Adds 10 damage and reduces damage by 5%.'),
        (2, 5, 102, 'Adds 20 damage and reduces damage by 10%.'),
        (3, 1, 103, 'Increases damage by 4%.'),
        (3, 3, 103, 'Increases damage by 12%.'),
        (4, 1, 104, 'Increases 10%.'),
        (4, 2, 104, 'Increases 10% and reduces 5%.'),
    ])
    conn.commit()
    conn.close()

    database = WowDb(path)
    yield database
    database.close()


def test_format_money(db):
    assert db.format_money(0) == '0 de cobre'
    assert db.format_money(50) == '50 de cobre'
    assert db.format_money(110) == '1 de plata y 10 de cobre'
    assert db.format_money(330) == '3 de plata y 30 de cobre'
    assert db.format_money(10230) == '1 de oro y 2 de plata'
    assert db.format_money(25000) == '2 de oro y 50 de plata'

    assert db.format_money(0, 'en') == '0 copper'
    assert db.format_money(50, 'en') == '50 copper'
    assert db.format_money(110, 'en') == '1 silver 10 copper'
    assert db.format_money(330, 'en') == '3 silver 30 copper'
    assert db.format_money(10230, 'en') == '1 gold 2 silver'
    assert db.format_money(25000, 'en') == '2 gold 50 silver'


def test_zone_levels(db):
    spanish = db.zone_levels('Montañas Crestagrana')
    assert spanish == {'area_id': 44, 'name': 'Montañas Crestagrana', 'min': 16, 'max': 26}
    assert db.zone_levels('Redridge Mountains', 'en')['name'] == 'Redridge Mountains'
    assert db.zone_levels(44)['name'] == 'Montañas Crestagrana'
    assert db.zone_levels('No existe') is None


def test_zones_for_level(db):
    zones = db.zones_for_level(16)
    assert zones[0]['name'] == 'Montañas Crestagrana'
    names = [zone['name'] for zone in zones]
    assert 'Ciudad de Ventormenta' not in names
    assert 'Los Baldíos' not in names
    assert len(zones) <= 8
    english = db.zones_for_level(16, 'en')
    assert english[0]['name'] == 'Redridge Mountains'


def test_dungeon_level(db):
    assert db.dungeon_level('Las Minas de la Muerte') == {
        'name': 'Minas de la Muerte', 'min': 17, 'max': 26, 'source': 'forever'}
    assert db.dungeon_level('The Deadmines', 'en') == {
        'name': 'Deadmines', 'min': 17, 'max': 26, 'source': 'forever'}
    assert db.dungeon_level('Mazmorras de Ventormenta')['min'] == 24
    assert db.dungeon_level('Gnomeregan')['max'] == 38
    assert db.dungeon_level('No existe') is None


def test_dungeons_for_level(db):
    dungeons = db.dungeons_for_level(16)
    assert [(item['name'], item['min'], item['max']) for item in dungeons] == [
        ('Salón de los Feudales', 13, 20),
        ('Sima Ígnea', 13, 18),
        ('Ruinas de Lordaeron', 15, 22),
        ('Cuevas de los Lamentos', 15, 24),
    ]


def test_dungeon_capital_faction(db):
    assert db.dungeon_capital_faction('Sima Ígnea') == 'H'
    assert db.dungeon_capital_faction('Ragefire Chasm') == 'H'
    assert db.dungeon_capital_faction('Mazmorras de Ventormenta') == 'A'
    assert db.dungeon_capital_faction('Cuevas de los Lamentos') is None
    assert db.dungeon_capital_faction('Castillo de Colmillo Oscuro') is None
    assert db.dungeon_capital_faction('No existe') is None


def test_dungeons_for_level_filters_capital_factions(db):
    alliance = [item['name'] for item in db.dungeons_for_level(16, faction='A')]
    assert 'Sima Ígnea' not in alliance
    assert 'Cuevas de los Lamentos' in alliance
    assert 'Ruinas de Lordaeron' in alliance
    horde = [item['name'] for item in db.dungeons_for_level(16, faction='H')]
    assert 'Sima Ígnea' in horde
    unknown = [item['name'] for item in db.dungeons_for_level(16)]
    assert 'Sima Ígnea' in unknown


def test_next_dungeons_filters_and_sorts(db):
    alliance = db.next_dungeons(9, faction='A', limit=3)
    assert len(alliance) == 3
    assert all(item['min'] > 9 for item in alliance)
    assert 'Sima Ígnea' not in [item['name'] for item in alliance]
    assert [item['min'] for item in alliance] == sorted(
        item['min'] for item in alliance)
    horde = [item['name'] for item in db.next_dungeons(9, faction='H', limit=3)]
    assert 'Sima Ígnea' in horde
    unknown = [item['name'] for item in db.next_dungeons(9, limit=3)]
    assert 'Sima Ígnea' in unknown


def test_dungeon_bosses(db):
    wailing = db.dungeon_bosses('Cuevas de los Lamentos')
    assert wailing['name'] == 'Cuevas de los Lamentos'
    assert wailing['bosses'] == [
        'Lady Anacondra', 'Lord Cobrahn', 'Kresh', 'Lord Pythas', 'Skum',
        'Lord Serpentis', 'Verdan el Eterno', 'Mutanus el Devorador',
    ]
    deadmines = db.dungeon_bosses('Las Minas de la Muerte')
    assert deadmines['bosses'] == [
        "Rhahk'Zor", 'Sneed', 'Minero Johnson', 'Gilnid', 'Capitán Verdetez',
        'Don Mamporro', 'Cocinitas', 'Edwin VanCleef',
    ]
    assert db.dungeon_bosses('Gnomeregan')['bosses'] == ['Grubbis', 'Viscous Fallout']
    assert db.dungeon_bosses('No existe') is None


def test_xp_to_next_level(db):
    assert db.xp_to_next_level(16) == 16000
    assert db.xp_to_next_level(17) == 17700
    assert db.xp_to_next_level(99) is None
    assert db.xp_to_next_level('texto') is None


def test_quest_details(db):
    details = db.quest_details(255)
    assert details['xp'] == 1800
    assert details['zone'] == 'Loch Modan'
    assert details['objectives'] == ['Mata 4 ogros.']

    plain = db.quest_details(256)
    assert plain['objectives'] == ['texto no JSON']
    assert db.quest_details(999) is None


def test_quest_objective_item_ids(db):
    quest = db.find_quest(91775)
    assert quest['objective_items'] == ['Álbum de fotos', 'Libro perdido']
    assert quest['objective_item_ids'] == [248001, 248002]


def test_quest_objective_creatures(db):
    quest = db.find_quest(91776)
    assert quest['objective_creatures'] == [
        {'id': 1162, 'name': 'Trog C'},
        {'id': 900003, 'name': 'Criatura sin posición'},
    ]


def test_find_quest_prefers_active_same_name(db):
    assert db.find_quest('Eco repetido')['id'] == 92001
    assert db.find_quest('Eco repetido', prefer_ids=[])['id'] == 92001
    assert db.find_quest('Eco repetido', prefer_ids=[92002])['id'] == 92002


def test_find_quest_prefers_same_faction_variant(db):
    assert db.find_quest('Eco repetido', faction='A')['id'] == 92002
    assert db.find_quest('Eco repetido', faction='H')['id'] == 92001
    assert db.find_quest('Eco repetido')['id'] == 92001
    starter = db.find_quest(92001)['starters'][0]
    assert starter['type'] == 'npc'
    assert starter['faction'] == 'H'


def test_item_sources_from_v_botin(db):
    item = db.item_sources('Diente de piedra trogg')
    assert item['name'] == 'Diente de piedra trogg'
    rates = [drop['rate'] for drop in item['drops']]
    assert rates == [50, 50, 31]
    assert item['drops'][0]['zone'] == 'Loch Modan'
    assert item['drops'][0]['npc'] in ('Trog A', 'Trog B')
    trog_a = next(drop for drop in item['drops'] if drop['npc'] == 'Trog A')
    assert (trog_a['x'], trog_a['y']) == (10.0, 20.0)


def test_item_sources_objects(db):
    item = db.item_sources(248003)
    assert item['vendors'] == []
    assert item['drops'] == []
    assert item['objects'] == [{
        'object': 'Cofre de libros',
        'zone': 'Páramos de Poniente',
        'x': 42.5,
        'y': 71.7,
    }]


def test_object_locations_drops_negative_coordinates(db):
    assert db.object_locations(900002) == [{
        'zone': 'Páramos de Poniente',
        'zone_id': 40,
        'x': None,
        'y': None,
    }]


def test_service_npcs_filters_zone_faction_and_nbsp(db):
    alliance = db.service_npcs(('banquer', 'banker'), zone_id=1519, lang='es',
                               faction='A')
    assert [npc['name'] for npc in alliance] == [
        'Newton Ladoquemao', 'Olivia Ladoquemao']
    assert all(npc['sub_name'] == 'Banquero' for npc in alliance)
    assert all(npc['locations'][0]['zone_id'] == 1519 for npc in alliance)

    horde = db.service_npcs(('banquer', 'banker'), zone_id=1519, lang='es',
                            faction='H')
    assert [npc['name'] for npc in horde] == ['Horgar Ladoquemao']

    everyone = db.service_npcs(('banquer', 'banker'), zone_id=1519, lang='es')
    assert [npc['name'] for npc in everyone] == [
        'Horgar Ladoquemao', 'Newton Ladoquemao', 'Olivia Ladoquemao']
    assert len(db.service_npcs(('banquer',), zone_id=1519, limit=2)) == 2
    assert db.service_npcs(('banquer',), zone_id=40) == []

    english = db.service_npcs(('fishing trainer',), zone_id=1519, lang='en',
                              faction='A')
    assert english[0]['sub_name'] == 'Fishing Trainer'
    spanish = db.service_npcs(('instructor de pesca',), zone_id=1519, lang='es',
                              faction='A')
    assert spanish[0]['name'] == 'Arnold Leland'
    assert spanish[0]['sub_name'] == 'Instructor de pesca'


def test_zone_faction(db):
    assert db.zone_faction(12) == 'A'
    assert db.zone_faction(14) == 'H'
    assert db.zone_faction(33) is None
    assert db.zone_faction(999) is None


def test_tameable_beasts_filters_level_family_and_zone(db):
    beasts = db.tameable_beasts(12, 10, 'es')
    assert [beast['name'] for beast in beasts] == [
        'Jabalí montés', 'Rondador del bosque']
    assert [beast['family'] for beast in beasts] == ['Jabalí', 'Araña']
    assert all(beast['min_level'] == 10 for beast in beasts)
    assert all(beast['max_level'] == 11 for beast in beasts)
    assert all(beast['locations'][0]['zone_id'] == 12 for beast in beasts)
    assert all(beast['name'] not in ('Lobo superior', 'Bestia sin familia')
               for beast in beasts)

    english = {beast['id']: beast for beast in db.tameable_beasts(12, 10, 'en')}
    assert english[7001]['name'] == 'Mountain Boar'
    assert english[7001]['family'] == 'Boar'
    assert english[7002]['family'] == 'Spider'

    higher = db.tameable_beasts(12, 13, 'es')
    assert any(beast['name'] == 'Lobo superior' for beast in higher)
    assert all(beast['name'] != 'Bestia sin familia' for beast in higher)
    assert db.tameable_beasts(38, 13, 'es') == []


def test_flights_from(db):
    flights = db.flights_from('Forjaz', 'A')
    assert flights['origin'] == 'Forjaz'
    destinations = [flight['destination'] for flight in flights['flights']]
    assert 'Ventormenta' in destinations
    assert 'Thelsamar, Loch Modan' in destinations
    assert 'Orgrimmar, Durotar' not in destinations
    assert 'Auberdine, Costa Oscura' in destinations
    thelsamar = next(flight for flight in flights['flights']
                     if flight['destination'] == 'Thelsamar, Loch Modan')
    assert thelsamar['cost_copper'] == 110
    assert thelsamar['cost'] == '1 de plata y 10 de cobre'
    assert [flight['cost_copper'] for flight in flights['flights']] == sorted(
        flight['cost_copper'] for flight in flights['flights'])


def test_flight_cost(db):
    cost = db.flight_cost('Forjaz', 'Thelsamar', 'A')
    assert cost['origin'] == 'Forjaz'
    assert cost['destination'] == 'Thelsamar, Loch Modan'
    assert cost['cost_copper'] == 110
    assert cost['cost'] == '1 de plata y 10 de cobre'
    assert db.flight_cost('Forjaz', 'Orgrimmar', 'A') is None
    assert db.flight_cost('Forjaz', 'Thelsamar', 'H') is None


def test_transports(db):
    transports = db.transports('A')
    assert len(transports) == 2
    assert not any('Generic' in item['origin'] or 'Generic' in item['destination']
                   for item in transports)
    assert not any('Orgrimmar' in item['origin'] or 'Orgrimmar' in item['destination']
                   for item in transports)
    pairs = {tuple(sorted((item['origin'], item['destination']))) for item in transports}
    assert len(pairs) == len(transports)


def test_empty_database_is_tolerated(tmp_path):
    path = tmp_path / 'empty.sqlite'
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE ext_quests (quest_id INTEGER)')
    conn.commit()
    conn.close()

    database = WowDb(path)
    assert database.zone_levels('Montañas Crestagrana') is None
    assert database.zones_for_level(16) == []
    # Los niveles curados viven en el paquete y no necesitan tablas de mazmorras.
    assert database.dungeon_level('Las Minas de la Muerte')['source'] == 'forever'
    assert database.dungeons_for_level(16)
    assert database.dungeon_bosses('Las Minas de la Muerte') is None
    assert database.xp_to_next_level(16) is None
    assert database.quest_details(255) is None
    assert database.flights_from('Forjaz', 'A') is None
    assert database.flight_cost('Forjaz', 'Thelsamar', 'A') is None
    assert database.transports('A') == []
    database.close()


def test_resolve_talent_text_single_variable():
    assert resolve_talent_text(
        'Aumenta un $s1% la salud y la armadura de tus mascotas.',
        'Increases the Health and Armor of your pets by $s1%.',
        'Increases the Health and Armor of your pets by 15%.') == (
        'Aumenta un 15% la salud y la armadura de tus mascotas.')


def test_resolve_talent_text_multiple_variables_in_any_order():
    assert resolve_talent_text(
        'Reduce un $s2% el daño y añade $s1 de daño.',
        'Adds $s1 damage and reduces damage by $s2%.',
        'Adds 10 damage and reduces damage by 5%.') == (
        'Reduce un 5% el daño y añade 10 de daño.')


def test_resolve_talent_text_mismatch_or_missing_variable():
    assert resolve_talent_text(
        'Aumenta un $s1% el daño.', 'Increases damage by $s1%.',
        'Increases damage by a lot.') is None
    assert resolve_talent_text(
        'Hace $s1 y $s2.', 'Does $s1.', 'Does 5.') is None


def test_resolve_talent_text_duration_units():
    assert resolve_talent_text('Dura $d.', 'Lasts $d.',
                               'Lasts 12 sec.') == 'Dura 12 s.'
    assert resolve_talent_text('Dura $d.', 'Lasts $d.',
                               'Lasts 3 minutes.') == 'Dura 3 min.'
    assert resolve_talent_text('Dura $d.', 'Lasts $d.',
                               'Lasts 1 hour.') is None


def test_forever_talents_loads_ranks_and_caches(db):
    talents = db.forever_talents()
    assert len(talents) == 4
    assert db.forever_talents() is talents
    endurance = next(talent for talent in talents if talent['NodeID'] == 1)
    assert endurance['ranks'][1].endswith('3%.')
    assert endurance['ranks'][5].endswith('15%.')


def test_talents_in_text_prefers_long_names(db):
    found = db.talents_in_text(normalize('¿Qué hace Entrenamiento en aguante?'), 'es')
    assert [talent['NodeID'] for talent in found] == [1]
    found = db.talents_in_text(normalize('Endurance Training y Tiro mortal'), 'en')
    assert {talent['NodeID'] for talent in found} == {1, 2}


def test_talent_detail_resolves_spanish_ranks(db):
    talent = next(talent for talent in db.forever_talents()
                  if talent['NodeID'] == 1)
    detail = db.talent_detail(talent, 'es')
    assert detail['name'] == 'Entrenamiento en aguante'
    assert detail['other_name'] == 'Endurance Training'
    assert detail['class'] == 'Cazador'
    assert detail['tree'] == 'Dominio de bestias'
    assert detail['required_points'] == 0
    assert detail['max_rank'] == 5
    assert detail['change'] == 'changed'
    assert '3%' in detail['rank1_text']
    assert '15%' in detail['max_text']
    assert talent_detail(talent, 'en')['rank1_text'].endswith('3%.')


def test_talent_detail_keeps_unresolved_text_as_none(db):
    talent = next(talent for talent in db.forever_talents()
                  if talent['NodeID'] == 4)
    detail = db.talent_detail(talent, 'es')
    assert detail['prerequisite'] == 'Tiro mortal'
    assert detail['rank1_text'] is None
    assert '10%' in detail['max_text']
