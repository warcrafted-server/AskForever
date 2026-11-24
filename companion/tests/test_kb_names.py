"""Pruebas de los nombres oficiales por ID y del descodificador de builds del calculador de talentos."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / 'tools'
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location('kb_names', TOOLS / 'kb_names.py')
kb_names = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kb_names)

TREE = [  # (tree_slug, rama_es, nombre_en, nombre_es, max_rank, PosY, PosX, NodeID, puntos_requeridos, previo)
    ('beast-mastery', 'Dominio de bestias', 'Deadly Aspects', 'Aspectos letales', 5, 1, 1, 1, 0, None),
    ('beast-mastery', 'Dominio de bestias', 'Endurance Training', 'Entrenamiento en aguante', 5, 1, 2, 2, 0, None),
    ('beast-mastery', 'Dominio de bestias', 'Focused Fire', 'Fuego enfocado', 2, 2, 1, 3, 5, None),
    ('beast-mastery', 'Dominio de bestias', 'Bestial Wrath', 'Ira de bestias', 1, 3, 1, 4, 5, 3),
    ('marksmanship', 'Puntería', 'Hawk Eye', 'Ojo de halcón', 3, 1, 1, 5, 0, None),
    ('marksmanship', 'Puntería', 'Lethal Attacks', 'Ataques letales', 5, 1, 2, 6, 0, None),
]


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE v_talentos_forever (class_slug, tree_slug, rama_es, nombre_en, nombre_es, '
                 'max_rank, PosY, PosX, NodeID, puntos_requeridos, talento_previo_node_id)')
    conn.executemany('INSERT INTO v_talentos_forever VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                     [('hunter',) + row for row in TREE])
    conn.execute('CREATE TABLE SpellName (ID, Name_lang, Name_lang_esES)')
    conn.execute('CREATE TABLE SkillLine (ID, DisplayName_lang, DisplayName_lang_esES, CategoryID)')
    conn.execute("INSERT INTO SpellName VALUES (19574, 'Bestial Wrath', 'Ira de bestias')")
    conn.execute("INSERT INTO SpellName VALUES (2567, 'Thrown', 'Lanzado')")
    conn.execute("INSERT INTO SkillLine VALUES (176, 'Thrown', 'Armas arrojadizas', 6)")
    return conn


def test_decode_build_in_position_order():
    builds = kb_names.TalentBuilds(_conn(), trees_dir=None)
    assert builds.decode('hunter', '502-04') == [
        ('Dominio de bestias', [('Deadly Aspects', 'Aspectos letales', 5, 5),
                                ('Focused Fire', 'Fuego enfocado', 2, 2)]),
        ('Puntería', [('Lethal Attacks', 'Ataques letales', 4, 5)]),
    ]


def test_decode_rejects_points_above_max_rank_and_too_many_trees():
    builds = kb_names.TalentBuilds(_conn(), trees_dir=None)
    assert builds.decode('hunter', '503') is None
    assert builds.decode('hunter', '5-0-0-1') is None


def test_decode_rejects_talents_without_their_requirements():
    builds = kb_names.TalentBuilds(_conn(), trees_dir=None)
    assert builds.decode('hunter', '002') is None      # Fuego enfocado sin 5 puntos antes en la rama
    assert builds.decode('hunter', '5011') is None     # Ira de bestias sin Fuego enfocado al máximo
    assert builds.decode('hunter', '5021') is not None


def test_annotate_markdown_link_keeps_link_intact():
    builds = kb_names.TalentBuilds(_conn(), trees_dir=None)
    url = 'https://www.wowhead.com/forever/talent-calc/hunter/v2502-04_t0_r2/0AC1cccc'
    text = builds.annotate(f'[Talent Build]({url}) and more')
    assert text.startswith(f'[Talent Build]({url}) {{build: Dominio de bestias: Deadly Aspects')
    assert text.endswith('Ataques letales 4/5} and more')


def _talent(index, name, row, col, max_rank, spell, required=0, previous=None, rank=None):
    return {'index': index, 'name': name, 'row': row, 'column': col, 'max_rank': max_rank, 'spell_ids': [spell],
            'requires_talent_index': previous, 'requires_rank': rank, 'requires_points_in_tree': required}


def _wowhead_dir(tmp_path):
    """Árbol actual con Fuego enfocado antes que Entrenamiento en aguante (orden distinto del de wowdata) y árbol
    antiguo donde «Old Hawk» se renombró (mismo hechizo) y «Gone Talent» ya no existe."""
    current = [
        {'order': 0, 'name': 'Beast Mastery', 'talents': [
            _talent(0, 'Deadly Aspects', 0, 1, 5, 101),
            _talent(1, 'Focused Fire', 0, 2, 2, 103),
            _talent(2, 'Endurance Training', 1, 0, 5, 102, required=5),
            _talent(3, 'Bestial Wrath', 1, 1, 1, 104, required=5, previous=1, rank=2)]},
        {'order': 1, 'name': 'Marksmanship', 'talents': [_talent(0, 'Lethal Attacks', 0, 0, 5, 106)]},
    ]
    legacy = [
        {'order': 0, 'name': 'Beast Mastery', 'talents': [
            _talent(0, 'Deadly Aspects', 0, 1, 5, 101),
            _talent(1, 'Old Hawk', 0, 2, 2, 103),
            _talent(2, 'Gone Talent', 0, 3, 1, 999)]},
        {'order': 1, 'name': 'Marksmanship', 'talents': [_talent(0, 'Lethal Attacks', 0, 0, 5, 106)]},
    ]
    (tmp_path / 'hunter.json').write_text(json.dumps({'class': 'hunter', 'trees': current,
                                                      'legacy_v2_trees': legacy}), encoding='utf-8')
    (tmp_path / 'index.json').write_text('{"classes": []}', encoding='utf-8')
    return tmp_path


def test_wowhead_trees_give_order_requirements_and_spanish_names(tmp_path):
    builds = kb_names.TalentBuilds(_conn(), trees_dir=_wowhead_dir(tmp_path))
    assert builds.decode('hunter', '522-5', version='kndmh') == [
        ('Dominio de bestias', [('Deadly Aspects', 'Aspectos letales', 5, 5),
                                ('Focused Fire', 'Fuego enfocado', 2, 2),
                                ('Endurance Training', 'Entrenamiento en aguante', 2, 5)]),
        ('Puntería', [('Lethal Attacks', 'Ataques letales', 5, 5)]),
    ]
    assert builds.decode('hunter', '0001', version='kndmh') is None   # Ira de bestias sin puntos ni requisito
    assert builds.decode('hunter', '5101', version='kndmh') is None   # Ira de bestias sin Fuego enfocado 2/2


def test_wowhead_v2_link_maps_old_talents_and_drops_retired_ones(tmp_path):
    builds = kb_names.TalentBuilds(_conn(), trees_dir=_wowhead_dir(tmp_path))
    assert builds.decode('hunter', '521-3') == [
        ('Dominio de bestias', [('Deadly Aspects', 'Aspectos letales', 5, 5),
                                ('Focused Fire', 'Fuego enfocado', 2, 2)]),
        ('Puntería', [('Lethal Attacks', 'Ataques letales', 3, 5)]),
        (kb_names.RETIRED, [('Gone Talent', None, 1, 1)]),
    ]
    # Ilegal con el árbol antiguo (Gone Talent 2/1): vale el actual.
    assert builds.decode('hunter', '522-5')[0][1][2] == ('Endurance Training', 'Entrenamiento en aguante', 2, 5)
    url = 'https://www.wowhead.com/forever/talent-calc/hunter/v2521_t0/0AC'
    assert builds.annotate(f'[Talent Build]({url})').endswith(f'{kb_names.RETIRED}: Gone Talent 1/1}}')


def test_official_name_by_id_and_weapon_skill_name():
    names = kb_names.OfficialNames.__new__(kb_names.OfficialNames)
    names.conn, names.cache = _conn(), {}
    assert names.es('spell', 19574) == 'Ira de bestias'
    assert names.es('spell', 2567) == 'Armas arrojadizas'
    annotated = names.annotate('[Bestial Wrath](https://www.wowhead.com/forever/spell=19574)')
    assert annotated.endswith('{esES: Ira de bestias}')


ROGUE = [  # (tree_slug, rama_es, nombre_en, nombre_es, max_rank, PosY, PosX, NodeID, req, previo)
    ('assassination', 'Asesinato', 'Malice', 'Maldad', 5, 1, 1, 10, 0, None),
    ('assassination', 'Asesinato', 'Efficient Strikes', 'Golpes eficaces', 5, 1, 2, 11, 0, None),
    ('assassination', 'Asesinato', 'Blood Splatter', None, 3, 2, 1, 12, 0, None),
    ('assassination', 'Asesinato', 'Same Name', 'Same Name', 1, 3, 1, 13, 0, None),
]


def _rogue_conn():
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE v_talentos_forever (class_slug, tree_slug, rama_es, nombre_en, nombre_es, '
                 'max_rank, PosY, PosX, NodeID, puntos_requeridos, talento_previo_node_id)')
    conn.executemany('INSERT INTO v_talentos_forever VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                     [('rogue',) + row for row in ROGUE])
    return conn


def test_annotate_tables_in_talent_build_and_order_tables():
    builds = kb_names.TalentBuilds(_rogue_conn(), trees_dir=None)
    text = (
        '**Talent Build — Rogue: Assassination 12 / Combat 8 / Subtlety 31 (51 points)**\n\n'
        '#### Assassination (12/51)\n\n'
        '| Talent | Rank |\n'
        '| --- | --- |\n'
        '| Malice | 5/5 |\n'
        '| Desconocido | 2/2 |\n'
        '| Same Name | 1/1 |\n\n'
        '**Talent Order**\n\n'
        '| Level | Talent | Rank |\n'
        '| --- | --- | --- |\n'
        '| 10 | Efficient Strikes | Rank 1 |\n'
        '| 26 | Blood Splatter |  |\n')
    annotated = builds.annotate_tables(text)
    assert '| Malice {esES: Maldad} | 5/5 |' in annotated
    assert '| Desconocido | 2/2 |' in annotated
    assert '| Same Name | 1/1 |' in annotated
    assert '| 10 | Efficient Strikes {esES: Golpes eficaces} | Rank 1 |' in annotated
    assert '| 26 | Blood Splatter |  |' in annotated
    assert '#### Assassination (12/51)' in annotated
    assert annotated.count('{esES:') == 2
    assert builds.annotate_tables(annotated) == annotated


def test_annotate_tables_ignores_tables_outside_a_talent_build_block():
    builds = kb_names.TalentBuilds(_rogue_conn(), trees_dir=None)
    order = ('| Level | Talent | Rank |\n'
             '| --- | --- | --- |\n'
             '| 10 | Efficient Strikes | Rank 1 |\n')
    assert builds.annotate_tables(order) == order

    text = (
        '**Talent Build — Rogue: Assassination 12 (12 points)**\n'
        '| Talent | Rank |\n'
        '| --- | --- |\n'
        '| Malice | 5/5 |\n'
        '## Otra sección\n'
        '| Talent | Rank |\n'
        '| --- | --- |\n'
        '| Malice | 5/5 |\n')
    annotated = builds.annotate_tables(text)
    assert annotated.count('{esES: Maldad}') == 1
    assert annotated.endswith('| Malice | 5/5 |\n')


def test_annotate_tables_keeps_blockquote_prefixes():
    builds = kb_names.TalentBuilds(_rogue_conn(), trees_dir=None)
    text = (
        '> **Talent Build — Rogue: Assassination 12 (12 points)**\n'
        '>\n'
        '> | Talent | Rank |\n'
        '> | --- | --- |\n'
        '> | Malice | 5/5 |\n'
        '> | Desconocido | 2/2 |\n')
    annotated = builds.annotate_tables(text)
    assert '> | Malice {esES: Maldad} | 5/5 |' in annotated
    assert '> | Desconocido | 2/2 |' in annotated
    assert annotated.count('\n') == text.count('\n')
