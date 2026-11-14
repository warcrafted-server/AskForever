"""Pruebas de los rangos de nivel curados de WoW Forever."""

from __future__ import annotations

import sqlite3

import pytest

from askforever.data import wowdb
from askforever.data.wowdb import WowDb
from askforever.engine.retriever import retrieve

SCHEMA = [
    'CREATE TABLE ext_quests (quest_id INTEGER)',
    'CREATE TABLE ext_dungeons (area_id INTEGER, name_enUS TEXT, name_esES TEXT, '
    'parent_zone_id INTEGER)',
    'CREATE TABLE ext_dungeon_entrances (area_id INTEGER, idx INTEGER, zone_id INTEGER, '
    'x REAL, y REAL)',
    'CREATE TABLE ext_zones (group_id INTEGER, area_id INTEGER, name_enUS TEXT, '
    'name_esES TEXT)',
    'CREATE TABLE LFGDungeons (ID INTEGER, Name_lang TEXT, Name_lang_esES TEXT, '
    'TypeID INTEGER, MapID INTEGER, ContentTuningID INTEGER)',
    'CREATE TABLE contenttuning (ID INTEGER, MinLevelSquish INTEGER, '
    'MaxLevelSquish INTEGER, LfgMinLevel INTEGER, LfgMaxLevel INTEGER)',
]

CTX = {'lvl': 16, 'race': 'Enano', 'class': 'Chamán', 'fac': 'Alianza', 'zone': 'Forjaz'}


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'wow.sqlite'
    conn = sqlite3.connect(path)
    for statement in SCHEMA:
        conn.execute(statement)
    conn.executemany(
        'INSERT INTO ext_dungeons (area_id, name_enUS, name_esES, parent_zone_id) '
        'VALUES (?, ?, ?, ?)', [
            (1581, 'The Deadmines', 'Las Minas de la Muerte', 40),
            (718, 'Wailing Caverns', 'Cuevas de los Lamentos', 17),
            (796, 'Scarlet Monastery', 'Monasterio Escarlata', 0),
            (999, 'Test Chamber', 'Cámara de Pruebas', 0),
        ])
    conn.execute(
        'INSERT INTO ext_dungeon_entrances (area_id, idx, zone_id, x, y) '
        'VALUES (1581, 1, 40, 42.5, 71.7)')
    conn.execute(
        "INSERT INTO ext_zones (group_id, area_id, name_enUS, name_esES) "
        "VALUES (0, 40, 'Westfall', 'Páramos de Poniente')")
    conn.executemany(
        'INSERT INTO LFGDungeons (ID, Name_lang, Name_lang_esES, TypeID, MapID, '
        'ContentTuningID) VALUES (?, ?, ?, ?, ?, ?)', [
            (5, 'Deadmines', 'Minas de la Muerte', 0, 36, 5240),
            (1, 'Wailing Caverns', 'Cuevas de los Lamentos', 0, 43, 5254),
            (17, 'Scarlet Monastery', 'Monasterio Escarlata', 0, 0, 5243),
            (39, 'Stratholme', 'Stratholme', 0, 0, 5244),
            (99, 'Test Chamber', 'Cámara de Pruebas', 0, 0, 9999),
        ])
    conn.executemany(
        'INSERT INTO contenttuning (ID, MinLevelSquish, MaxLevelSquish, LfgMinLevel, '
        'LfgMaxLevel) VALUES (?, ?, ?, ?, ?)', [
            (5240, 16, 16, 0, 0),
            (5254, 17, 17, 0, 0),
            (5243, 30, 30, 0, 0),
            (5244, 58, 58, 0, 0),
            (9999, 22, 23, 0, 0),
        ])
    conn.commit()
    conn.close()

    database = WowDb(path)
    yield database
    database.close()


def test_forever_deadmines_spanish(db):
    assert db.dungeon_level('Las Minas de la Muerte') == {
        'name': 'Minas de la Muerte', 'min': 17, 'max': 26, 'source': 'forever'}


def test_forever_deadmines_english(db):
    assert db.dungeon_level('The Deadmines', 'en') == {
        'name': 'Deadmines', 'min': 17, 'max': 26, 'source': 'forever'}


def test_forever_scarlet_monastery_wings(db):
    data = db.dungeon_level('Monasterio Escarlata')
    assert (data['name'], data['min'], data['max'], data['source']) == (
        'Monasterio Escarlata', 30, 45, 'forever')
    assert data['wings'] == [
        {'name': 'Cementerio', 'min': 30, 'max': 38},
        {'name': 'Biblioteca', 'min': 33, 'max': 41},
        {'name': 'Armería', 'min': 34, 'max': 42},
        {'name': 'Catedral', 'min': 36, 'max': 45},
    ]


def test_forever_specific_scarlet_wing(db):
    assert db.dungeon_level('Monasterio Escarlata: Biblioteca') == {
        'name': 'Monasterio Escarlata: Biblioteca', 'min': 33, 'max': 41,
        'source': 'forever'}
    assert db.dungeon_level('Monasterio Escarlata - Cementerio')['min'] == 30
    assert db.dungeon_level('Catedral') == {
        'name': 'Monasterio Escarlata: Catedral', 'min': 36, 'max': 45,
        'source': 'forever'}


def test_forever_stratholme_wings(db):
    data = db.dungeon_level('Stratholme')
    assert (data['min'], data['max']) == (58, 60)
    assert [wing['name'] for wing in data['wings']] == [
        'Entrada principal', 'Entrada de servicio']


def test_hyphenated_dungeon_name_is_not_a_wing(db):
    assert db.dungeon_level('La Masacre - Este') == {
        'name': 'La Masacre - Este', 'min': 55, 'max': 60, 'source': 'forever'}
    assert db.dungeon_level('Dire Maul - East', 'en')['name'] == 'Dire Maul - East'


def test_client_fallback_for_uncurated_dungeon(db):
    assert db.dungeon_level('Cámara de Pruebas') == {
        'name': 'Cámara de Pruebas', 'min': 22, 'max': 23, 'source': 'client'}


def test_dungeons_for_level_uses_forever(db):
    dungeons = db.dungeons_for_level(16)
    assert [(item['name'], item['min'], item['max']) for item in dungeons] == [
        ('Salón de los Feudales', 13, 20),
        ('Sima Ígnea', 13, 18),
        ('Ruinas de Lordaeron', 15, 22),
        ('Cuevas de los Lamentos', 15, 24),
    ]
    assert all(item['source'] == 'forever' for item in dungeons)
    assert 'Minas de la Muerte' not in [item['name'] for item in dungeons]


def test_dungeons_for_level_scarlet_wings(db):
    names = [item['name'] for item in db.dungeons_for_level(35)]
    assert 'Monasterio Escarlata: Cementerio' in names
    assert 'Monasterio Escarlata: Biblioteca' in names
    assert 'Monasterio Escarlata: Armería' in names
    assert 'Monasterio Escarlata: Catedral' not in names


def test_missing_json_uses_client_data(db, monkeypatch, tmp_path):
    monkeypatch.setattr(wowdb, 'FOREVER_LEVELS_PATH', tmp_path / 'missing.json')
    monkeypatch.setattr(wowdb, '_FOREVER_LEVELS', None)
    assert db.dungeon_level('Las Minas de la Muerte') == {
        'name': 'Minas de la Muerte', 'min': 16, 'max': 16, 'source': 'client'}
    assert [item['name'] for item in db.dungeons_for_level(16)] == [
        'Minas de la Muerte', 'Cuevas de los Lamentos']
    assert 'wings' not in db.dungeon_level('Monasterio Escarlata')


def test_retriever_shows_forever_levels(db):
    facts = retrieve({'v': 1, 'lang': 'esES',
                      'q': '¿A qué nivel puedo hacer Las Minas de la Muerte?',
                      'ctx': dict(CTX)}, db)
    text = '\n'.join(facts.lines)
    assert 'niveles 17-26' in text
    assert 'rangos de nivel de mazmorras' not in facts.missing

    wings = retrieve({'v': 1, 'lang': 'esES',
                      'q': '¿A qué nivel puedo hacer Monasterio Escarlata?',
                      'ctx': dict(CTX)}, db)
    text = '\n'.join(wings.lines)
    assert 'niveles 30-45' in text
    assert ('Alas: Cementerio 30-38, Biblioteca 33-41, Armería 34-42, '
            'Catedral 36-45') in text
