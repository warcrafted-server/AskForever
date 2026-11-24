"""Pruebas del orden de talentos de las builds y de su comparación con el personaje."""

from __future__ import annotations

import sqlite3

import pytest

from askforever.data.wowdb import WowDb
from askforever.engine.talent_path import next_talent_steps

WRATH_EN = 'Improved Wrath'
WRATH_ES = 'Cólera mejorada'
MOONGLOW_EN = 'Moonglow'
MOONGLOW_ES = 'Brillo lunar'

ORDER = [
    {'nivel': 10, 'talento_en': WRATH_EN, 'talento_es': WRATH_ES, 'rango': 1},
    {'nivel': 11, 'talento_en': WRATH_EN, 'talento_es': WRATH_ES, 'rango': 2},
    {'nivel': 12, 'talento_en': MOONGLOW_EN, 'talento_es': MOONGLOW_ES, 'rango': 1},
    {'nivel': 13, 'talento_en': WRATH_EN, 'talento_es': WRATH_ES, 'rango': 3},
    {'nivel': 14, 'talento_en': MOONGLOW_EN, 'talento_es': MOONGLOW_ES, 'rango': 2},
]


def _build(path, with_order=True):
    conn = sqlite3.connect(path)
    conn.execute(
        'CREATE TABLE ext_wh_build (build_id TEXT, clase TEXT, espec TEXT, titulo TEXT, '
        'puntos_total INTEGER, puntos_ramas TEXT, enlace TEXT, variante TEXT, '
        'orden_en_seccion INTEGER, guide_key TEXT, section_hash TEXT)')
    conn.executemany(
        'INSERT INTO ext_wh_build VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [
            ('b1', 'druid', 'balance', 'Build de equilibrio', 5, '{"Balance": 3}', 'u1',
             'Variante A', 1, 'g', 'h'),
            ('b2', 'druid', 'feral', 'Build feral', 4, '{"Feral Combat": 4}', 'u2',
             'Variante B', 2, 'g', 'h'),
            ('b3', 'mage', 'arcane', 'Build arcana', 5, '{"Arcane": 5}', 'u3',
             'Variante C', 1, 'g', 'h'),
        ])
    if with_order:
        conn.execute(
            'CREATE TABLE ext_wh_talento_orden (build_id TEXT, nivel INTEGER, '
            'talento_en TEXT, talento_es TEXT, node_id INTEGER, rango INTEGER, '
            'guide_key TEXT, section_hash TEXT)')
        conn.executemany(
            'INSERT INTO ext_wh_talento_orden VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            [('b1', row['nivel'], row['talento_en'], row['talento_es'],
              row['nivel'] * 10, row['rango'], 'g', 'h') for row in ORDER])
    conn.commit()
    conn.close()


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'wow.sqlite'
    _build(path)
    database = WowDb(path)
    yield database
    database.close()


def test_talent_builds_matches_spanish_and_english_class(db):
    builds = db.talent_builds('Druida')
    assert [build['build_id'] for build in builds] == ['b1', 'b2']
    assert builds[0]['espec'] == 'balance'
    assert builds[0]['variante'] == 'Variante A'
    assert builds[0]['puntos_total'] == 5
    assert builds[0]['has_order'] is True
    assert builds[1]['has_order'] is False
    assert [build['build_id'] for build in db.talent_builds('druid')] == ['b1', 'b2']
    assert [build['build_id'] for build in db.talent_builds('Mago')] == ['b3']
    assert db.talent_builds('Pícaro') == []
    assert db.talent_builds('') == []


def test_talent_order_rows_and_ordering(db):
    order = db.talent_order('b1')
    assert [row['nivel'] for row in order] == [10, 11, 12, 13, 14]
    assert order[0] == {'nivel': 10, 'talento_en': WRATH_EN,
                        'talento_es': WRATH_ES, 'rango': 1}
    assert order[-1]['rango'] == 2
    assert db.talent_order('unknown') == []
    assert next_talent_steps(order, [[WRATH_ES, 2], [MOONGLOW_ES, 1]], 12)['off_route'] is False


def test_missing_tables_return_empty(tmp_path):
    path = tmp_path / 'empty.sqlite'
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE ext_quests (quest_id INTEGER)')
    conn.commit()
    conn.close()
    database = WowDb(path)
    try:
        assert database.talent_builds('druid') == []
        assert database.talent_order('b1') == []
    finally:
        database.close()


def test_builds_without_order_table(tmp_path):
    path = tmp_path / 'wow.sqlite'
    _build(path, with_order=False)
    database = WowDb(path)
    try:
        builds = database.talent_builds('druida')
        assert [build['build_id'] for build in builds] == ['b1', 'b2']
        assert all(build['has_order'] is False for build in builds)
        assert database.talent_order('b1') == []
    finally:
        database.close()


def test_on_route_character():
    steps = next_talent_steps(ORDER, [[WRATH_ES, 2], [MOONGLOW_ES, 1]], 12)
    assert steps['expected'] == {WRATH_ES: 2, MOONGLOW_ES: 1}
    assert steps['ahead'] == []
    assert steps['behind'] == []
    assert steps['off_route'] is False
    assert steps['next'] == []


def test_english_names_match_order():
    steps = next_talent_steps(ORDER, [[WRATH_EN, 2], [MOONGLOW_EN, 1]], 12)
    assert steps['expected'] == {WRATH_ES: 2, MOONGLOW_ES: 1}
    assert steps['off_route'] is False
    assert steps['behind'] == []


def test_character_ahead():
    steps = next_talent_steps(ORDER, [[WRATH_ES, 3]], 12)
    assert steps['expected'] == {WRATH_ES: 2, MOONGLOW_ES: 1}
    assert steps['ahead'] == [WRATH_ES]
    assert steps['behind'] == [MOONGLOW_ES]
    assert steps['off_route'] is False
    assert steps['next'] == [{'nivel': 12, 'talento': MOONGLOW_ES, 'rango': 1}]


def test_character_behind():
    steps = next_talent_steps(ORDER, [[WRATH_ES, 1]], 12)
    assert steps['ahead'] == []
    assert WRATH_ES in steps['behind'] and MOONGLOW_ES in steps['behind']
    assert steps['off_route'] is False
    assert steps['next'] == [
        {'nivel': 11, 'talento': WRATH_ES, 'rango': 2},
        {'nivel': 12, 'talento': MOONGLOW_ES, 'rango': 1},
    ]
    assert next_talent_steps(ORDER, [], 12, limit=2)['next'] == [
        {'nivel': 10, 'talento': WRATH_ES, 'rango': 1},
        {'nivel': 11, 'talento': WRATH_ES, 'rango': 2},
    ]


def test_off_route_talent_not_in_order():
    steps = next_talent_steps(ORDER, [[WRATH_ES, 1], ['Talento inventado', 2]], 12)
    assert steps['off_route'] is True
    assert steps['next'] == []


def test_off_route_rank_beyond_order():
    steps = next_talent_steps(ORDER, [[WRATH_ES, 4]], 12)
    assert steps['off_route'] is True
    assert steps['ahead'] == [WRATH_ES]
    assert steps['next'] == []


def test_level_below_ten_has_no_points():
    steps = next_talent_steps(ORDER, [], 9)
    assert steps['expected'] == {}
    assert steps['ahead'] == []
    assert steps['behind'] == []
    assert steps['off_route'] is False
    assert steps['next'] == []
