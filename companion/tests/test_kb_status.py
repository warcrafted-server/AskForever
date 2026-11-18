"""Pruebas de la herramienta que enlaza fichas editoriales con el corpus."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent.parent / 'tools' / 'kb_status.py'
SPEC = importlib.util.spec_from_file_location('kb_status', MODULE_PATH)
kb_status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kb_status)


def _card(path: Path, section: dict) -> None:
    path.write_text(json.dumps({
        'description': 'Ficha de prueba',
        'sections': [section],
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _corpus(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE guides (
            guide_key TEXT PRIMARY KEY, source TEXT, url TEXT, topic TEXT,
            superseded_by TEXT, hash TEXT
        );
        CREATE TABLE sections (
            section_id TEXT PRIMARY KEY, guide_key TEXT, heading TEXT,
            heading_path TEXT, hash TEXT, ord INTEGER
        );
    """)
    conn.executemany(
        'INSERT INTO guides VALUES (?, ?, ?, ?, ?, ?)', [
            ('wowhead/hunter', 'wowhead',
             'http://www.example.test/hunter/?utm=1',
             'class:hunter:general:hunter', None, 'guide-hunter'),
            ('icy-veins/hunter', 'icy-veins',
             'https://icy.example.test/hunter', 'class:hunter:general:hunter',
             'wowhead/hunter', 'guide-icy'),
            ('wowhead/other', 'wowhead',
             'https://example.test/other', 'profession:alchemy:overview',
             None, 'guide-other'),
        ])
    conn.executemany(
        'INSERT INTO sections VALUES (?, ?, ?, ?, ?, ?)', [
            ('wowhead/hunter#Overview', 'wowhead/hunter', 'Overview',
             'Overview', 'hash-overview', 1),
            ('wowhead/hunter#Rotation', 'wowhead/hunter', 'Rotation',
             'Class > Rotation', 'hash-rotation', 2),
        ])
    conn.commit()
    conn.close()


def test_normalize_url_ignores_scheme_query_and_trailing_slash():
    assert kb_status.normalize_url(
        'http://www.example.test/a/b/?x=1#frag') == 'example.test/a/b'
    assert kb_status.normalize_url(
        'https://example.test/a/b') == 'example.test/a/b'


def test_section_match_heading_path_and_guide_fallback(tmp_path):
    db = tmp_path / 'corpus.sqlite'
    _corpus(db)
    cards = tmp_path / 'cards'
    cards.mkdir()
    _card(cards / 'card.json', {
        'id': 'card-1',
        'sources': [
            {'url': 'https://example.test/hunter',
             'ref': 'Icy Veins: Guide › Overview'},
            {'url': 'https://example.test/hunter',
             'ref': 'Icy Veins: Guide › Rotation'},
            {'url': 'https://example.test/hunter',
             'ref': 'Icy Veins: Guide › Not a heading'},
        ],
    })
    report = tmp_path / 'report.md'
    kb_status.run_status(cards, db, report, write=True)
    section = json.loads((cards / 'card.json').read_text(encoding='utf-8'))['sections'][0]
    assert section['topics'] == ['class:hunter:general:hunter']
    assert section['source_hashes'] == [
        'guide:guide-hunter', 'section:hash-overview', 'section:hash-rotation']


def test_write_preserves_fields_and_detects_stale_superseded_and_uncovered(tmp_path):
    db = tmp_path / 'corpus.sqlite'
    _corpus(db)
    cards = tmp_path / 'cards'
    cards.mkdir()
    card_path = cards / 'card.json'
    section = {
        'id': 'card-1',
        'title_es': 'Título',
        'sources': [
            {'url': 'https://example.test/hunter',
             'ref': 'Icy Veins: Guide › Overview'},
            {'url': 'https://example.test/hunter',
             'ref': 'Icy Veins: Guide › Rotation'},
            {'url': 'https://icy.example.test/hunter',
             'ref': 'Icy Veins: Guide › Overview'},
        ],
    }
    _card(card_path, section)
    report = tmp_path / 'report.md'
    summary = kb_status.run_status(cards, db, report, write=True)
    loaded = json.loads(card_path.read_text(encoding='utf-8'))
    written = loaded['sections'][0]
    assert list(written)[-2:] == ['topics', 'source_hashes']
    assert written['title_es'] == 'Título'
    assert summary['superseded'] == 1
    assert summary['uncovered'] == 1
    assert 'profession:alchemy:overview' in report.read_text(encoding='utf-8')

    conn = sqlite3.connect(db)
    conn.execute("UPDATE sections SET hash = 'hash-new' "
                 "WHERE section_id = 'wowhead/hunter#Overview'")
    conn.commit()
    conn.close()
    stale = kb_status.run_status(cards, db, report, write=False)
    assert stale['stale'] == 1
    assert 'Fichas caducadas' in report.read_text(encoding='utf-8')
    assert 'card-1' in report.read_text(encoding='utf-8')


def test_missing_source_is_reported(tmp_path):
    db = tmp_path / 'corpus.sqlite'
    _corpus(db)
    cards = tmp_path / 'cards'
    cards.mkdir()
    _card(cards / 'card.json', {
        'id': 'card-1',
        'sources': [{'url': 'https://example.test/missing',
                     'ref': 'Icy Veins: Guide › Missing'}],
    })
    report = tmp_path / 'report.md'
    summary = kb_status.run_status(cards, db, report, write=False)
    assert summary['missing'] == 1
    assert 'Fuentes no encontradas' in report.read_text(encoding='utf-8')


def test_write_only_refreshes_selected_ids_and_preserves_other_files(tmp_path):
    db = tmp_path / 'corpus.sqlite'
    _corpus(db)
    cards = tmp_path / 'cards'
    cards.mkdir()
    selected_path = cards / 'selected.json'
    other_path = cards / 'other.json'
    selected_sections = [
        {'id': 'selected', 'topics': ['old-topic'],
         'source_hashes': ['old-hash'],
         'sources': [{'url': 'https://example.test/hunter',
                      'ref': 'Icy Veins: Guide › Overview'}]},
        {'id': 'stale', 'topics': ['stale-topic'],
         'source_hashes': ['stale-hash'],
         'sources': [{'url': 'https://example.test/hunter',
                      'ref': 'Icy Veins: Guide › Rotation'}]},
    ]
    selected_path.write_text(
        json.dumps({'sections': selected_sections}, indent=2) + '\n',
        encoding='utf-8')
    _card(other_path, {
        'id': 'other', 'topics': ['other-topic'],
        'source_hashes': ['other-hash'],
        'sources': [{'url': 'https://example.test/hunter',
                     'ref': 'Icy Veins: Guide › Overview'}],
    })
    other_bytes = other_path.read_bytes()
    report = tmp_path / 'report.md'

    summary = kb_status.run_status(cards, db, report, write=True,
                                   only={'selected'})

    saved = json.loads(selected_path.read_text(encoding='utf-8'))['sections']
    assert saved[0]['topics'] == ['class:hunter:general:hunter']
    assert saved[0]['source_hashes'] == ['section:hash-overview']
    assert saved[1]['topics'] == ['stale-topic']
    assert saved[1]['source_hashes'] == ['stale-hash']
    assert other_path.read_bytes() == other_bytes
    assert summary['stale'] == 3


def test_only_unknown_id_returns_two_without_writing(tmp_path, capsys):
    db = tmp_path / 'corpus.sqlite'
    _corpus(db)
    cards = tmp_path / 'cards'
    cards.mkdir()
    card_path = cards / 'card.json'
    _card(card_path, {
        'id': 'known', 'topics': ['old-topic'],
        'source_hashes': ['old-hash'], 'sources': [],
    })
    report = tmp_path / 'report.md'
    report.write_text('existing report\n', encoding='utf-8')
    card_bytes = card_path.read_bytes()
    report_bytes = report.read_bytes()

    result = kb_status.main([
        '--cards', str(cards), '--corpus', str(db), '--report', str(report),
        '--write', '--only', 'missing',
    ])

    captured = capsys.readouterr()
    assert result == 2
    assert "missing" in captured.err
    assert card_path.read_bytes() == card_bytes
    assert report.read_bytes() == report_bytes


def test_write_without_only_refreshes_every_card(tmp_path):
    db = tmp_path / 'corpus.sqlite'
    _corpus(db)
    cards = tmp_path / 'cards'
    cards.mkdir()
    for card_id in ('first', 'second'):
        _card(cards / f'{card_id}.json', {
            'id': card_id, 'topics': ['old-topic'],
            'source_hashes': ['old-hash'],
            'sources': [{'url': 'https://example.test/hunter',
                         'ref': 'Icy Veins: Guide › Overview'}],
        })

    kb_status.run_status(cards, db, tmp_path / 'report.md', write=True)

    for card_id in ('first', 'second'):
        saved = json.loads((cards / f'{card_id}.json').read_text(
            encoding='utf-8'))['sections'][0]
        assert saved['topics'] == ['class:hunter:general:hunter']
        assert saved['source_hashes'] == ['section:hash-overview']
