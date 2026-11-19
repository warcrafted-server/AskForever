"""Pruebas del equipo BiS: WowDb.bis_gear / bis_specs y el detector del recuperador."""

from __future__ import annotations

import sqlite3

import pytest

from askforever.data.wowdb import WowDb, normalize
from askforever.engine.retriever import Facts, _detect_bis


def _build(path, with_bis=True):
    conn = sqlite3.connect(path)
    conn.executescript(
        'CREATE TABLE ext_item_l10n (item_id INTEGER, locale TEXT, name TEXT);'
        'CREATE TABLE ext_npc_l10n (npc_id INTEGER, locale TEXT, name TEXT, sub_name TEXT);'
        'CREATE TABLE ext_quest_l10n (quest_id INTEGER, locale TEXT, name TEXT);'
        'CREATE TABLE SpellName (__id INTEGER, ID INTEGER, Name_lang TEXT, Name_lang_esES TEXT);'
        'CREATE TABLE v_talentos_forever (NodeID INTEGER, class_id INTEGER, class_slug TEXT, '
        'rama_es TEXT, rama_en TEXT, tree_slug TEXT);')
    if with_bis:
        conn.execute(
            'CREATE TABLE ext_wh_bis (clase TEXT, espec TEXT, ranura TEXT, rango TEXT, '
            'item_id INTEGER, fuente_tipo TEXT, fuente_id INTEGER, guide_key TEXT, '
            'section_hash TEXT)')
        rows = [
            ('mage', 'arcane', 'Shoulder', 'BiS', 3, 'npc', 50),
            ('mage', 'arcane', 'Head', 'BiS', 1, 'quest', 60),
            ('mage', 'arcane', 'Head', 'Great', 2, None, None),
            ('mage', 'arcane', 'Ring 1', 'BiS', 4, 'spell', 70),
            ('mage', 'arcane', 'Ring 2', 'BiS', 5, None, None),
            ('mage', 'arcane', 'Ring Jewelry', 'BiS', 6, None, None),
            ('mage', 'arcane', 'Trinkets', 'BIS', 7, 'npc', 50),
            ('mage', 'arcane', 'Wands', 'BiS Realistic', 8, None, None),
            ('druid', 'balance', 'Head', 'BiS', 1, None, None),
            ('druid', 'restoration', 'Head', 'BiS', 2, None, None),
        ]
        conn.executemany(
            'INSERT INTO ext_wh_bis VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [row + ('g', 'h') for row in rows])
    for item_id in range(1, 9):
        conn.execute('INSERT INTO ext_item_l10n VALUES (?, ?, ?)',
                     (item_id, 'esES', f'Objeto {item_id}'))
        conn.execute('INSERT INTO ext_item_l10n VALUES (?, ?, ?)',
                     (item_id, 'enUS', f'Item {item_id}'))
    conn.execute("INSERT INTO ext_npc_l10n VALUES (50, 'esES', 'Jefe', '')")
    conn.execute("INSERT INTO ext_npc_l10n VALUES (50, 'enUS', 'Boss', '')")
    conn.execute("INSERT INTO ext_quest_l10n VALUES (60, 'esES', 'Misión')")
    conn.execute("INSERT INTO SpellName VALUES (1, 70, 'Anillo', 'Anillo')")
    conn.executemany(
        'INSERT INTO v_talentos_forever VALUES (?, ?, ?, ?, ?, ?)',
        [(1, 128, 'mage', 'Arcano', 'Arcane', 'arcane'),
         (2, 128, 'mage', 'Fuego', 'Fire', 'fire'),
         (3, 1024, 'druid', 'Equilibrio', 'Balance', 'balance'),
         (4, 1024, 'druid', 'Recuperación', 'Restoration', 'restoration')])
    conn.commit()
    conn.close()


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'wow.sqlite'
    _build(path)
    database = WowDb(path)
    yield database
    database.close()


def test_bis_gear_orders_slots_and_merges_variants(db):
    items = db.bis_gear('mage', 'arcane', 'es')
    slots = [item['slot'] for item in items]
    assert slots == ['head', 'shoulders', 'rings', 'rings', 'trinkets', 'ranged']
    assert items[0]['name'] == 'Objeto 1'
    assert items[0]['source_name'] == 'Misión'
    assert items[1]['source_name'] == 'Jefe'
    assert items[2]['source_name'] == 'fabricado: Anillo'
    assert items[3]['source_name'] == ''


def test_bis_gear_alternatives_and_language(db):
    plain = db.bis_gear('mage', 'arcane', 'en')
    assert all(item['rank'].lower().startswith('bis') for item in plain)
    assert plain[0]['slot_label'] == 'Head'
    extended = db.bis_gear('mage', 'arcane', 'en', include_alternatives=True)
    heads = [item for item in extended if item['slot'] == 'head']
    assert [item['name'] for item in heads] == ['Item 1', 'Item 2']


def test_bis_specs_and_missing_data(db, tmp_path):
    assert db.bis_specs('druid') == ['balance', 'restoration']
    assert db.bis_specs('mage') == ['arcane']
    assert db.bis_gear('mage', 'fire') == []
    empty = tmp_path / 'empty.sqlite'
    _build(empty, with_bis=False)
    other = WowDb(empty)
    try:
        assert other.bis_specs('mage') == []
        assert other.bis_gear('mage', 'arcane') == []
    finally:
        other.close()


def _facts(db, question, ctx=None, lang='es'):
    facts = Facts()
    _detect_bis(facts, db, normalize(question), lang, ctx or {})
    return facts


def test_detect_bis_named_spec(db):
    facts = _facts(db, 'cual es el mejor equipo bis para mago arcano')
    assert len(facts.lines) == 1
    assert facts.lines[0].startswith('Equipo BiS de Mago Arcano')
    assert 'Cabeza: Objeto 1 (Misión)' in facts.lines[0]
    assert 'bis:mage:arcane' in facts.sources


def test_detect_bis_single_spec_and_class_from_context(db):
    facts = _facts(db, 'mejor equipo bis', {'class': 'Mago'})
    assert facts.lines and 'Arcano' in facts.lines[0]


def test_detect_bis_asks_for_spec_when_several(db):
    facts = _facts(db, 'mejor equipo bis druida')
    assert not facts.lines
    assert 'Equilibrio' in facts.missing[0] and 'Recuperación' in facts.missing[0]


def test_detect_bis_spec_without_data(db):
    facts = _facts(db, 'mejor equipo bis mago fuego')
    assert not facts.lines
    assert 'Arcano' in facts.missing[0]


def test_detect_bis_ignores_other_questions(db):
    assert not _facts(db, 'donde subo de nivel siendo mago').lines
    assert not _facts(db, 'donde subo de nivel siendo mago').missing
