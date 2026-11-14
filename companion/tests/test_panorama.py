"""Pruebas del panorama de zonas y mazmorras del recuperador y del prompt."""

from __future__ import annotations

import sqlite3

import pytest

from askforever.data.wowdb import WowDb
from askforever.engine.prompt import build_prompt
from askforever.engine.retriever import Facts, retrieve

SCHEMA = [
    'CREATE TABLE ext_quests (quest_id INTEGER)',
    'CREATE TABLE ext_zones (group_id INTEGER, area_id INTEGER, name_enUS TEXT, '
    'name_esES TEXT)',
    'CREATE TABLE ext_dungeons (area_id INTEGER, name_enUS TEXT, name_esES TEXT, '
    'parent_zone_id INTEGER)',
    'CREATE TABLE v_zona_niveles (area_id INTEGER, nombre TEXT, nombre_en TEXT, '
    'nivel_min INTEGER, nivel_max INTEGER, pnj INTEGER, origen TEXT)',
]

ZONES = [
    (44, 'Montañas Crestagrana', 'Redridge Mountains', 16, 26),
    (38, 'Loch Modan', 'Loch Modan', 11, 20),
    (40, 'Páramos de Poniente', 'Westfall', 11, 20),
    (36, 'Sierra Espolón', 'Hillsbrad Foothills', 15, 28),
    (267, 'Bosque de Argénteos', 'Silverpine Forest', 12, 25),
    (148, 'Costa Oscura', 'Darkshore', 12, 21),
    (1519, 'Ciudad de Ventormenta', 'Stormwind City', 1, 60),
    (3, 'Los Humedales', 'Wetlands', 22, 32),
]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'wow.sqlite'
    conn = sqlite3.connect(path)
    for statement in SCHEMA:
        conn.execute(statement)
    for area_id, name_es, name_en, low, high in ZONES:
        conn.execute('INSERT INTO ext_zones (group_id, area_id, name_enUS, name_esES) '
                     'VALUES (0, ?, ?, ?)', (area_id, name_en, name_es))
        conn.execute('INSERT INTO v_zona_niveles (area_id, nombre, nombre_en, nivel_min, '
                     'nivel_max, pnj, origen) VALUES (?, ?, ?, ?, ?, 0, ?)',
                     (area_id, name_es, name_en, low, high, 'prueba'))
    conn.commit()
    conn.close()

    database = WowDb(path)
    yield database
    database.close()


def _message(question, lvl=16, lang='esES'):
    ctx = {'race': 'Enano', 'class': 'Chamán', 'fac': 'Alianza', 'zone': 'Forjaz'}
    if lvl is not None:
        ctx['lvl'] = lvl
    return {'v': 1, 'lang': lang, 'q': question, 'ctx': ctx}


def test_panorama_lines_for_any_question(db):
    facts = retrieve(_message('¿Qué hago ahora?'), db)

    zones = [line for line in facts.panorama
             if line.startswith('Zonas para tu nivel (16):')]
    dungeons = [line for line in facts.panorama
                if line.startswith('Mazmorras para tu nivel (16):')]
    assert len(zones) == 1
    assert len(dungeons) == 1
    for zone in ('Montañas Crestagrana (16-26)', 'Sierra Espolón (15-28)',
                 'Bosque de Argénteos (12-25)', 'Costa Oscura (12-21)',
                 'Loch Modan (11-20)', 'Páramos de Poniente (11-20)'):
        assert zone in zones[0]
    for dungeon in ('Sima Ígnea (13-18)', 'Salón de los Feudales (13-20)',
                    'Ruinas de Lordaeron (15-22)', 'Cuevas de los Lamentos (15-24)'):
        assert dungeon in dungeons[0]

    assert 'panorama:zones:16' in facts.sources
    assert 'panorama:dungeons:16' in facts.sources
    rendered = facts.render('esES')
    assert 'Zonas para tu nivel (16):' in rendered
    assert 'Mazmorras para tu nivel (16):' in rendered


def test_no_panorama_without_level(db):
    for lvl in (None, 'abc'):
        facts = retrieve(_message('¿Qué hago ahora?', lvl=lvl), db)
        assert not any('para tu nivel' in line for line in facts.panorama)
        assert not any(source.startswith('panorama:') for source in facts.sources)


def test_exclusions_remove_zones_and_add_line(db):
    facts = retrieve(_message('¿Puedo ir a alguna zona que no sea Loch Modan ni Páramos?'), db)

    zones = next(line for line in facts.panorama
                 if line.startswith('Zonas para tu nivel (16):'))
    assert 'Loch Modan' not in zones
    assert 'Páramos de Poniente' not in zones
    assert 'Montañas Crestagrana (16-26)' in zones

    excluded = [line for line in facts.panorama
                if line.startswith('Excluidas a petición del jugador:')]
    assert len(excluded) == 1
    assert 'Loch Modan' in excluded[0]
    assert 'Páramos de Poniente' in excluded[0]


def test_exclusion_filters_zone_intent_and_avoids_duplicate(db):
    facts = retrieve(_message('¿Qué zonas me tocan a mi nivel, que no sea Páramo?'), db)

    zone_lines = [line for line in facts.lines if line.startswith('Zonas para ')]
    assert len(zone_lines) == 1
    assert zone_lines[0].startswith('Zonas para nivel 16:')
    assert 'Páramos de Poniente' not in zone_lines[0]
    assert not any(line.startswith('Zonas para tu nivel') for line in facts.panorama)

    excluded = [line for line in facts.panorama
                if line.startswith('Excluidas a petición del jugador:')]
    assert excluded and 'Páramos de Poniente' in excluded[0]


def test_zone_question_does_not_duplicate_line(db):
    facts = retrieve(_message('¿Qué zonas me tocan a mi nivel?'), db)

    zone_lines = [line for line in facts.lines if line.startswith('Zonas para ')]
    assert len(zone_lines) == 1
    assert zone_lines[0].startswith('Zonas para nivel 16:')
    assert not any(line.startswith('Zonas para tu nivel') for line in facts.panorama)
    assert any(line.startswith('Mazmorras para tu nivel (16):')
               for line in facts.panorama)


def test_panorama_is_truncated_before_entities():
    facts = Facts()
    facts.lines = [f'Entidad {index}: ' + 'x' * 120 for index in range(20)]
    facts.panorama = ['Zonas para tu nivel (16): ' + 'z' * 200,
                      'Mazmorras para tu nivel (16): ' + 'm' * 200]

    rendered = facts.render('esES')
    assert 'Entidad 0:' in rendered
    assert 'Entidad 5:' in rendered
    assert 'Zonas para tu nivel' not in rendered
    assert 'Mazmorras para tu nivel' not in rendered
    assert len(rendered) <= 1600


def test_english_panorama(db):
    facts = retrieve(_message('What should I do now?', lang='enUS'), db)

    zones = next(line for line in facts.panorama
                 if line.startswith('Zones for your level (16):'))
    dungeons = next(line for line in facts.panorama
                    if line.startswith('Dungeons for your level (16):'))
    assert 'Redridge Mountains (16-26)' in zones
    assert 'Loch Modan (11-20)' in zones
    assert 'Ragefire Chasm (13-18)' in dungeons
    assert 'Wailing Caverns (15-24)' in dungeons


def test_system_prompt_forbids_copying_headers():
    system, _user = build_prompt({'lang': 'esES', 'q': '¿Qué hago ahora?'})
    assert 'No copies' in system
    assert 'encabezados' in system
    assert 'DATOS VERIFICADOS' in system
    assert 'SIN DATOS EN LA BASE' in system
    assert 'panorama de zonas y mazmorras' in system

    system, _user = build_prompt({'lang': 'enUS', 'q': 'What should I do now?'})
    assert 'Do not copy' in system
    assert 'headers' in system
    assert 'VERIFIED DATA' in system
    assert 'NOT IN THE DATABASE' in system
    assert 'panorama' in system.lower()
