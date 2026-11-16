"""Pruebas de los nombres oficiales por ID y del descodificador de builds del calculador de talentos."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / 'tools'
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location('kb_names', TOOLS / 'kb_names.py')
kb_names = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kb_names)

TREE = [  # (tree_slug, rama_es, nombre_en, nombre_es, max_rank, PosY, PosX)
    ('beast-mastery', 'Dominio de bestias', 'Deadly Aspects', 'Aspectos letales', 5, 1, 1),
    ('beast-mastery', 'Dominio de bestias', 'Endurance Training', 'Entrenamiento en aguante', 5, 1, 2),
    ('beast-mastery', 'Dominio de bestias', 'Focused Fire', 'Fuego enfocado', 2, 2, 1),
    ('marksmanship', 'Puntería', 'Hawk Eye', 'Ojo de halcón', 3, 1, 1),
    ('marksmanship', 'Puntería', 'Lethal Attacks', 'Ataques letales', 5, 1, 2),
]


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE v_talentos_forever (class_slug, tree_slug, rama_es, nombre_en, nombre_es, '
                 'max_rank, PosY, PosX)')
    conn.executemany('INSERT INTO v_talentos_forever VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                     [('hunter',) + row for row in TREE])
    conn.execute('CREATE TABLE SpellName (ID, Name_lang, Name_lang_esES)')
    conn.execute('CREATE TABLE SkillLine (ID, DisplayName_lang, DisplayName_lang_esES, CategoryID)')
    conn.execute("INSERT INTO SpellName VALUES (19574, 'Bestial Wrath', 'Ira de bestias')")
    conn.execute("INSERT INTO SpellName VALUES (2567, 'Thrown', 'Lanzado')")
    conn.execute("INSERT INTO SkillLine VALUES (176, 'Thrown', 'Armas arrojadizas', 6)")
    return conn


def test_decode_build_in_position_order():
    builds = kb_names.TalentBuilds(_conn())
    assert builds.decode('hunter', '502-04') == [
        ('Dominio de bestias', [('Deadly Aspects', 'Aspectos letales', 5, 5),
                                ('Focused Fire', 'Fuego enfocado', 2, 2)]),
        ('Puntería', [('Lethal Attacks', 'Ataques letales', 4, 5)]),
    ]


def test_decode_rejects_points_above_max_rank_and_too_many_trees():
    builds = kb_names.TalentBuilds(_conn())
    assert builds.decode('hunter', '503') is None
    assert builds.decode('hunter', '5-0-0-1') is None


def test_annotate_markdown_link_keeps_link_intact():
    builds = kb_names.TalentBuilds(_conn())
    url = 'https://www.wowhead.com/forever/talent-calc/hunter/v2502-04_t0_r2/0AC1cccc'
    text = builds.annotate(f'[Talent Build]({url}) and more')
    assert text.startswith(f'[Talent Build]({url}) {{build: Dominio de bestias: Deadly Aspects')
    assert text.endswith('Ataques letales 4/5} and more')


def test_official_name_by_id_and_weapon_skill_name():
    names = kb_names.OfficialNames.__new__(kb_names.OfficialNames)
    names.conn, names.cache = _conn(), {}
    assert names.es('spell', 19574) == 'Ira de bestias'
    assert names.es('spell', 2567) == 'Armas arrojadizas'
    annotated = names.annotate('[Bestial Wrath](https://www.wowhead.com/forever/spell=19574)')
    assert annotated.endswith('{esES: Ira de bestias}')
