"""Pruebas de la herramienta de paquetes de fuentes de la guía."""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

MODULE_PATH = (Path(__file__).resolve().parent.parent / 'tools' / 'guide_pack.py')
SPEC = importlib.util.spec_from_file_location('guide_pack', MODULE_PATH)
guide_pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guide_pack)

SCHEMA = {
    'GlobalStrings': (
        'CREATE TABLE GlobalStrings (ID INTEGER, BaseTag TEXT, TagText_lang TEXT, '
        'Flags INTEGER, TagText_lang_esES TEXT)'),
    'gametips': (
        'CREATE TABLE gametips (ID INTEGER, Text_lang TEXT, SortIndex INTEGER, '
        'Min_level INTEGER, Max_level INTEGER, ContentTuningID INTEGER, '
        'Text_lang_esES TEXT)'),
    'ChrClasses': (
        'CREATE TABLE ChrClasses (ID INTEGER, Name_lang TEXT, Name_lang_esES TEXT, '
        'Description_lang TEXT, Description_lang_esES TEXT)'),
    'ChrRaces': (
        'CREATE TABLE ChrRaces (ID INTEGER, Name_lang TEXT, Name_lang_esES TEXT, '
        'FactionID INTEGER, PlayableRaceBit INTEGER, LoreDescription_lang TEXT, '
        'LoreDescription_lang_esES TEXT)'),
    'ChrRaceRacialAbility': (
        'CREATE TABLE ChrRaceRacialAbility (ID INTEGER, Name_lang TEXT, '
        'Description_lang TEXT, DescriptionShort_lang TEXT, "Order" INTEGER, '
        'ChrRacesID INTEGER, Name_lang_esES TEXT, Description_lang_esES TEXT, '
        'DescriptionShort_lang_esES TEXT)'),
    'SkillLine': (
        'CREATE TABLE SkillLine (ID INTEGER, DisplayName_lang TEXT, '
        'DisplayName_lang_esES TEXT, CategoryID INTEGER, Description_lang TEXT, '
        'Description_lang_esES TEXT)'),
    'exhaustion': (
        'CREATE TABLE exhaustion (ID INTEGER, Name_lang TEXT, Name_lang_esES TEXT, '
        'Xp INTEGER, Factor REAL, OutdoorHours INTEGER, InnHours INTEGER, '
        'Threshold INTEGER)'),
    'levelexperience': (
        'CREATE TABLE levelexperience (ID INTEGER, Level INTEGER, '
        'ContentSetID INTEGER, Experience INTEGER)'),
    'chatchannels': (
        'CREATE TABLE chatchannels (ID INTEGER, Name_lang TEXT, '
        'Name_lang_esES TEXT, Shortcut_lang TEXT, Shortcut_lang_esES TEXT, '
        'Flags INTEGER, FactionGroup INTEGER)'),
}


def _insert(conn, table, columns, rows):
    placeholders = ', '.join('?' for _ in columns)
    quoted = ', '.join(f'"{column}"' for column in columns)
    conn.executemany(
        f'INSERT INTO {table} ({quoted}) VALUES ({placeholders})',
        rows)


def _make_db(path: Path, missing=()):
    conn = sqlite3.connect(path)
    for table, statement in SCHEMA.items():
        if table not in missing:
            conn.execute(statement)
    if 'GlobalStrings' not in missing:
        _insert(conn, 'GlobalStrings',
                ['ID', 'BaseTag', 'TagText_lang', 'Flags', 'TagText_lang_esES'], [
            (1, 'TUTORIAL7',
             '|cffffd100Tip:|r If you defeat an enemy, right-click the corpse '
             'to loot it.',
             0, '|cffffd100Consejo:|r Si derrotas a un enemigo, haz clic derecho '
                'en el cadáver para despojarlo.'),
            (2, 'OPTION_TOOLTIP_X',
             'Loot and enemy options for the game interface.', 0,
             'Opciones de despojo para enemigos y botín del juego.'),
        ])
    if 'gametips' not in missing:
        _insert(conn, 'gametips',
                ['ID', 'Text_lang', 'SortIndex', 'Min_level', 'Max_level',
                 'ContentTuningID', 'Text_lang_esES'], [
            (201, 'You can cancel a spell by moving.', 1, 1, 60, None,
             'Puedes cancelar un hechizo moviéndote.'),
        ])
    if 'ChrClasses' not in missing:
        _insert(conn, 'ChrClasses',
                ['ID', 'Name_lang', 'Name_lang_esES', 'Description_lang',
                 'Description_lang_esES'], [
            (1, 'Warrior', 'Guerrero', 'A melee fighter.', 'Un combatiente cuerpo a cuerpo.'),
        ])
    if 'ChrRaces' not in missing:
        _insert(conn, 'ChrRaces',
                ['ID', 'Name_lang', 'Name_lang_esES', 'FactionID',
                 'PlayableRaceBit', 'LoreDescription_lang',
                 'LoreDescription_lang_esES'], [
            (1, 'Human', 'Humano', 1, 0, 'A playable race.', 'Una raza jugable.'),
            (2, 'NPC Race', 'Raza NPC', 0, -1, 'Not playable.', 'No jugable.'),
        ])
    if 'ChrRaceRacialAbility' not in missing:
        _insert(conn, 'ChrRaceRacialAbility',
                ['ID', 'Name_lang', 'Description_lang', 'DescriptionShort_lang',
                 'Order', 'ChrRacesID', 'Name_lang_esES', 'Description_lang_esES',
                 'DescriptionShort_lang_esES'], [
            (10, 'Will to Survive', 'Removes movement impairing effects.',
             'Removes movement effects.', 1, 1, 'Voluntad de supervivencia',
             'Elimina efectos que impiden moverse.', 'Elimina efectos de movimiento.'),
            (11, 'NPC Ability', 'Only for NPCs.', 'NPC only.', 1, 2,
             'Habilidad NPC', 'Solo PNJ.', 'Solo PNJ.'),
        ])
    if 'SkillLine' not in missing:
        _insert(conn, 'SkillLine',
                ['ID', 'DisplayName_lang', 'DisplayName_lang_esES', 'CategoryID',
                 'Description_lang', 'Description_lang_esES'], [
            (1, 'Herbalism', 'Herboristería', 11, 'Gather herbs.',
             'Recolecta hierbas.'),
            (2, 'Cooking', 'Cocina', 9, 'Cook food.', 'Cocina comida.'),
            (3, 'Other', 'Otra', 7, 'Not a profession.', 'No es profesión.'),
        ])
    if 'exhaustion' not in missing:
        _insert(conn, 'exhaustion',
                ['ID', 'Name_lang', 'Name_lang_esES', 'Xp', 'Factor',
                 'OutdoorHours', 'InnHours', 'Threshold'], [
            (1, 'Rested', 'Descansado', 200, 1.5, 8, 24, 1),
        ])
    if 'levelexperience' not in missing:
        _insert(conn, 'levelexperience',
                ['ID', 'Level', 'ContentSetID', 'Experience'], [
            (1, 1, 0, 400),
            (60, 60, 0, 100000),
            (61, 61, 0, 120000),
        ])
    if 'chatchannels' not in missing:
        _insert(conn, 'chatchannels',
                ['ID', 'Name_lang', 'Name_lang_esES', 'Shortcut_lang',
                 'Shortcut_lang_esES', 'Flags', 'FactionGroup'], [
            (1, 'General', 'General', '/1', '/1', 0, 0),
        ])
    conn.commit()
    conn.close()


def test_parse_index_only_numbered_chapters():
    text = '''# Índice
## 1. Primeros pasos

| Pregunta | Fuente prevista |
|---|---|
| ¿Qué es esto? | C (TUTORIAL7) |
| ¿Cómo despojo? | C, M |

## Siguiente paso

## 3. Razas

| Pregunta | Fuente prevista |
|---|---|
| ¿Qué razas hay? | C (ChrRaces) |
'''
    chapters = guide_pack.parse_index(text)
    assert [chapter['number'] for chapter in chapters] == [1, 3]
    assert chapters[0]['title'] == 'Primeros pasos'
    assert chapters[0]['questions'] == [
        ('¿Qué es esto?', 'C (TUTORIAL7)'), ('¿Cómo despojo?', 'C, M')]
    assert chapters[1]['questions'] == [('¿Qué razas hay?', 'C (ChrRaces)')]


def test_corpus_labels_and_search(tmp_path):
    path = tmp_path / 'wow.sqlite'
    _make_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    corpus = guide_pack.build_corpus(conn, 20)
    results = guide_pack.search(corpus, '¿cómo despojo a un enemigo?', 8)
    by_ref = {result['ref']: result for result in results}
    assert by_ref['GlobalStrings:TUTORIAL7']['label'] == 'texto de ayuda'
    assert by_ref['GlobalStrings:OPTION_TOOLTIP_X']['label'] == (
        'sin verificar en Forever')
    assert results[0]['ref'] == 'GlobalStrings:TUTORIAL7'
    assert results[0]['score'] >= 2
    conn.close()


def test_chapter_three_only_playable_races(tmp_path):
    path = tmp_path / 'wow.sqlite'
    _make_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    text = guide_pack.render_chapter(
        {'number': 3, 'title': 'Razas', 'questions': []}, [], conn, 8,
        '2026-01-01 00:00', path.name)
    assert 'Humano' in text
    assert 'Raza NPC' not in text
    assert 'Voluntad de supervivencia' in text
    assert 'Habilidad NPC' not in text
    assert 'Tablas del cliente (sin verificar en Forever)' in text
    conn.close()


def test_missing_table_is_tolerated(tmp_path):
    path = tmp_path / 'wow.sqlite'
    _make_db(path, missing={'ChrClasses'})
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    text = guide_pack.render_chapter(
        {'number': 4, 'title': 'Clases', 'questions': []}, [], conn, 8,
        '2026-01-01 00:00', path.name)
    assert 'tabla no disponible' in text
    conn.close()


def _write_index(path: Path):
    path.write_text(
        '# Índice\n\n'
        '## 1. Primeros pasos\n\n'
        '| Pregunta | Fuente prevista |\n'
        '|---|---|\n'
        '| ¿Cómo despojo a un enemigo? | C (TUTORIAL7) |\n\n'
        '## 3. Razas\n\n'
        '| Pregunta | Fuente prevista |\n'
        '|---|---|\n'
        '| ¿Qué razas hay? | C (ChrRaces) |\n',
        encoding='utf-8')


def test_main_writes_chapter_files_without_full_db_path(tmp_path, capsys):
    db_path = tmp_path / 'wow.sqlite'
    _make_db(db_path)
    index_path = tmp_path / 'indice.md'
    _write_index(index_path)
    out_dir = tmp_path / 'paquetes'

    assert guide_pack.main(['--db', str(db_path), '--index', str(index_path),
                            '--out', str(out_dir)]) == 0
    first = out_dir / '01-primeros-pasos.md'
    third = out_dir / '03-razas.md'
    assert first.is_file() and third.is_file()
    first_text = first.read_text(encoding='utf-8')
    third_text = third.read_text(encoding='utf-8')
    assert '# Paquete de fuentes — 1. Primeros pasos' in first_text
    assert '`GlobalStrings:TUTORIAL7`' in first_text
    assert 'texto de ayuda' in first_text
    assert f'base: {db_path.name}' in first_text
    assert str(db_path) not in first_text
    assert str(db_path) not in third_text
    assert 'Humano' in third_text
    output = capsys.readouterr().out
    assert 'Paquetes escritos: 2' in output
    assert 'Preguntas: 2' in output


def test_probe_extracts_only_probe_block(tmp_path):
    db_path = tmp_path / 'wow.sqlite'
    _make_db(db_path)
    index_path = tmp_path / 'indice.md'
    _write_index(index_path)
    out_dir = tmp_path / 'paquetes'
    probe_path = tmp_path / 'collector.lua'
    probe_path.write_text(
        'Saved = {\n'
        '  ["probe"] = {\n'
        '    alpha = 1,\n'
        '    nested = { beta = 2 },\n'
        '  },\n'
        '  ["other"] = { gamma = 3 },\n'
        '}\n',
        encoding='utf-8')

    assert guide_pack.main(['--db', str(db_path), '--index', str(index_path),
                            '--out', str(out_dir), '--probe',
                            str(probe_path)]) == 0
    diagnostic = (out_dir / 'diagnostico.md').read_text(encoding='utf-8')
    assert '```lua' in diagnostic
    assert '["probe"]' in diagnostic
    assert 'alpha = 1' in diagnostic
    assert 'nested = { beta = 2 }' in diagnostic
    assert 'gamma = 3' not in diagnostic
    assert f'base: {db_path.name}' in diagnostic
