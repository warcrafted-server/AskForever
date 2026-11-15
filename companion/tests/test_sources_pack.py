"""Pruebas de la herramienta de paquetes de fuentes externas."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = (Path(__file__).resolve().parent.parent / 'tools' / 'sources_pack.py')
SPEC = importlib.util.spec_from_file_location('sources_pack', MODULE_PATH)
sources_pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sources_pack)

PROFESSIONS = '''---
title: Professions Guide
url: https://example.com/professions
author: Tester
published: 2026-01-01T00:00:00+00:00
modified: 2026-02-01T10:00:00+00:00
description: A guide to professions.
category: leveling
section: profesiones
---

This is an introductory paragraph
wrapped over two lines.

## Primary Professions

You can learn two primary
professions at a time. See [Alchemy](https://db.example.com/spell/1).
![icon](https://example.com/icon.png)

| Skill | Limit |
|---|---|
| Primary | 2 |

## Secondary Skills

Cooking and fishing are
secondary professions.
'''

LEVELING = '''---
title: Leveling Guide
url: https://example.com/leveling
modified: 2026-01-15
---

## Leveling

Kill enemies and complete quests to gain experience.
'''


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _make_source(tmp_path: Path):
    src = tmp_path / 'guides'
    _write(src / 'profesiones' / 'professions.md', PROFESSIONS)
    _write(src / 'general' / 'leveling.md', LEVELING)
    return src


def _index(tmp_path: Path, extra: str = ''):
    path = tmp_path / 'indice.md'
    path.write_text(
        '# Índice\n\n'
        '## 1. Primeros pasos\n\n'
        '| Pregunta | Fuente prevista |\n'
        '|---|---|\n'
        '| Where do I start? | C |\n\n'
        '## 5. Profesiones\n\n'
        '| Pregunta | Fuente prevista |\n'
        '|---|---|\n'
        '| two primary professions | C |\n' + extra,
        encoding='utf-8')
    return path


def test_parse_page_front_matter_passages_and_markup():
    meta, passages = sources_pack.parse_page(PROFESSIONS,
                                             'profesiones/professions.md')
    assert meta['title'] == 'Professions Guide'
    assert meta['url'] == 'https://example.com/professions'
    assert meta['modified'] == '2026-02-01T10:00:00+00:00'
    headings = [passage['heading'] for passage in passages]
    assert headings == ['Professions Guide', 'Primary Professions',
                        'Secondary Skills']
    intro = passages[0]
    assert intro['file'] == 'profesiones/professions.md'
    assert intro['url'] == 'https://example.com/professions'
    assert 'introductory paragraph wrapped over two lines' in intro['text']
    primary = passages[1]['text']
    assert 'You can learn two primary professions at a time.' in primary
    assert 'Alchemy' in primary
    assert 'db.example.com' not in primary
    assert 'icon.png' not in primary
    assert '| Skill | Limit |' in primary


def test_unwrap_keeps_tables_and_lists():
    text = ('A long paragraph\nwrapped at eighty.\n\n'
            '- first\n- second\n\n'
            '| A | B |\n|---|---|\n| 1 | 2 |')
    assert sources_pack.unwrap(text) == (
        'A long paragraph wrapped at eighty.\n\n'
        '- first\n- second\n\n'
        '| A | B |\n|---|---|\n| 1 | 2 |')


def test_build_passages_has_pages_and_folders(tmp_path):
    src = _make_source(tmp_path)
    passages = sources_pack.build_passages(src)
    assert isinstance(passages, list)
    assert len(passages.pages) == 2
    assert {page['folder'] for page in passages.pages} == {
        'profesiones', 'general'}
    assert any(passage['heading'] == 'Primary Professions'
               for passage in passages)


def test_match_finds_professions_and_heading_outranks_body():
    passages = sources_pack.PassageList([
        {'file': 'profesiones/a.md', 'folder': 'profesiones',
         'heading': 'Primary Professions', 'text': 'Some text.',
         'modified': '2026-01-01', 'title': 'A', 'url': 'u'},
        {'file': 'general/b.md', 'folder': 'general', 'heading': 'Other',
         'text': 'Primary professions are useful.',
         'modified': '2026-01-01', 'title': 'B', 'url': 'u'},
    ])
    result = sources_pack.match(passages, 'professions', 5, 5)
    assert result
    assert result[0][1]['heading'] == 'Primary Professions'
    assert result[0][0] > result[1][0]


def test_folder_boost_for_professions_chapter():
    passages = sources_pack.PassageList([
        {'file': 'general/a.md', 'folder': 'general', 'heading': 'Professions',
         'text': 'Primary professions text.', 'modified': '2026-01-01',
         'title': 'A', 'url': 'u'},
        {'file': 'profesiones/b.md', 'folder': 'profesiones',
         'heading': 'Professions', 'text': 'Primary professions text.',
         'modified': '2026-01-01', 'title': 'B', 'url': 'u'},
    ])
    result = sources_pack.match(passages, 'primary professions', 5, 5)
    assert result[0][1]['folder'] == 'profesiones'
    assert result[0][0] == result[1][0] + 1


def test_diff_state_reports_new_changed_removed():
    old = {'same.md': {'sha256': 'a', 'modified': '1'},
           'changed.md': {'sha256': 'b', 'modified': '2'},
           'removed.md': {'sha256': 'c', 'modified': '3'}}
    new = {'same.md': {'sha256': 'a', 'modified': '1'},
           'changed.md': {'sha256': 'd', 'modified': '4'},
           'new.md': {'sha256': 'e', 'modified': '5'}}
    assert sources_pack.diff_state(old, new) == {
        'new': ['new.md'], 'changed': ['changed.md'], 'removed': ['removed.md']}


def test_main_writes_outputs_and_tracks_changes(tmp_path):
    src = _make_source(tmp_path)
    index = _index(tmp_path)
    out = tmp_path / 'out'
    state = out / 'estado.json'

    assert sources_pack.main(['--src', str(src), '--index', str(index),
                              '--out', str(out), '--source-name', 'Test',
                              '--state', str(state)]) == 0
    first = out / '05-profesiones.md'
    assert first.is_file()
    text = first.read_text(encoding='utf-8')
    assert '# Fuentes externas — 5. Profesiones' in text
    assert 'Fuente: Test · generado' in text
    assert 'Primary Professions' in text
    assert 'puntuación' in text
    pages = (out / 'paginas.md').read_text(encoding='utf-8')
    assert '| Carpeta | Título | URL | Actualizado |' in pages
    assert 'Professions Guide' in pages
    assert 'Sin asignar' in pages
    changes = (out / 'cambios.md').read_text(encoding='utf-8')
    assert 'Primera ejecución' in changes
    saved = json.loads(state.read_text(encoding='utf-8'))
    assert 'profesiones/professions.md' in saved

    _write(src / 'profesiones' / 'professions.md',
           PROFESSIONS.replace('secondary professions.', 'secondary skills.'))
    assert sources_pack.main(['--src', str(src), '--index', str(index),
                              '--out', str(out), '--source-name', 'Test',
                              '--state', str(state)]) == 0
    changes = (out / 'cambios.md').read_text(encoding='utf-8')
    assert '## Modificadas' in changes
    assert 'profesiones/professions.md' in changes
    assert 'Primera ejecución' not in changes
