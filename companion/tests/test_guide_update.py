"""Pruebas de la actualización y clasificación de paquetes de clase."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent.parent / 'tools' / 'guide_update.py'
SPEC = importlib.util.spec_from_file_location('guide_update', MODULE_PATH)
guide_update = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guide_update)


GUIDE_KEY = 'wowhead/classes/druid/balance/overview-pve-dps'
URL_OLD = ('https://www.wowhead.com/forever/talent-calc/druid/'
           'v25232-001_t0_r2/0AC')
URL_NEW = ('https://www.wowhead.com/forever/talent-calc/druid/'
           'vkndmh5232-001_t0/2D')


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _pack(url: str, changed_sentence: str = 'Same sentence.') -> str:
    return (f'# class:druid:balance:overview · wowhead\n\n'
            f'- guía: `{GUIDE_KEY}`\n'
            '- título: Overview\n- url: https://example.test/druid\n'
            '- actualizada: 2026-11-18\n\n'
            '## › Overview\n\n'
            '## Overview\n'
            f'Build: [{url} {{build: no descodificable}}]({url}) '
            '{build: no descodificable}\n\n'
            '## › Rotation\n\n'
            '## Rotation\n'
            f'{changed_sentence}\n')


def _source_tree(root: Path) -> Path:
    return _write(root / 'wowhead/classes/druid/balance/overview-pve-dps.md',
                   '---\n'
                   'title: Druid overview\n'
                   'url: https://example.test/druid\n'
                   '---\n'
                   '## Overview\n'
                   f'Build: [{URL_NEW}]({URL_NEW})\n'
                   '## Rotation\n'
                   'New sentence.\n')


def _card(path: Path, card_id: str, heading: str) -> None:
    _write(path, json.dumps({
        'sections': [{
            'id': card_id,
            'source_hashes': ['section:old-hash'],
            'sources': [{'url': 'https://example.test/druid',
                         'ref': f'Wowhead: Druid › {heading}'}],
        }],
    }, ensure_ascii=False, indent=2) + '\n')


def test_normalize_pack_text_ignores_talent_url_version_and_tail_only():
    assert guide_update.normalize_pack_text(f'Build {URL_OLD}') == \
        guide_update.normalize_pack_text(f'Build {URL_NEW}')
    assert guide_update.normalize_pack_text(
        'talent-calc/druid/v25232-001_t0/0AC') == \
        guide_update.normalize_pack_text(
            'talent-calc/druid/vkndmh5232-001_t0/2D')
    different_build = URL_NEW.replace('5232-001', '6232-001')
    assert guide_update.normalize_pack_text(f'Build {URL_NEW}') != \
        guide_update.normalize_pack_text(f'Build {different_build}')
    assert guide_update.normalize_pack_text('a\u00a0b\u200b c') == 'a b c'


def test_classify_cards_marks_cosmetic_and_real_changes(tmp_path):
    cards = tmp_path / 'cards'
    cards.mkdir()
    _write(cards / '04-clase-druid.json', json.dumps({'sections': [
        {'id': 'cosmetic', 'source_hashes': ['old'], 'sources': [
            {'url': 'https://example.test/druid', 'ref': 'Wowhead: Druid › Overview'}]},
        {'id': 'real', 'source_hashes': ['old'], 'sources': [
            {'url': 'https://example.test/druid', 'ref': 'Wowhead: Druid › Rotation'}]},
    ]}, indent=2) + '\n')
    _write(cards / '01-general.json', json.dumps({'sections': [
        {'id': 'non-class', 'source_hashes': ['old'], 'sources': [
            {'url': 'https://example.test/druid', 'ref': 'Wowhead: Druid › Overview'}]},
    ]}, indent=2) + '\n')
    db = tmp_path / 'corpus.sqlite'
    conn = sqlite3.connect(db)
    conn.executescript('''
        CREATE TABLE guides (
            guide_key TEXT, source TEXT, url TEXT, topic TEXT,
            superseded_by TEXT, hash TEXT
        );
        CREATE TABLE sections (
            guide_key TEXT, heading TEXT, heading_path TEXT, hash TEXT, ord INTEGER
        );
    ''')
    conn.execute('INSERT INTO guides VALUES (?, ?, ?, ?, ?, ?)',
                 (GUIDE_KEY, 'wowhead', 'https://example.test/druid',
                  'class:druid:balance:overview', None, 'guide-hash'))
    conn.executemany('INSERT INTO sections VALUES (?, ?, ?, ?, ?)', [
        (GUIDE_KEY, 'Overview', 'Overview', 'one', 0),
        (GUIDE_KEY, 'Rotation', 'Rotation', 'two', 1),
    ])
    conn.commit()
    conn.close()
    result = guide_update.classify_cards(
        cards, {'cosmetic', 'real', 'non-class'}, db,
        {'druid-a': _pack(URL_OLD)},
        {'druid-a': _pack(URL_NEW, 'Changed sentence.')},
    )
    assert [card['id'] for card in result['druid']['cosmetic']] == ['cosmetic']
    assert [card['id'] for card in result['druid']['real']] == ['real']
    assert [card['id'] for card in result['other']['real']] == ['non-class']

    # Paquete ya regenerado por una pasada anterior: sin diferencias no hay prueba de cambio de forma.
    same = _pack(URL_NEW, 'Changed sentence.')
    again = guide_update.classify_cards(cards, {'cosmetic', 'real'}, db,
                                        {'druid-a': same}, {'druid-a': same})
    assert again['druid']['cosmetic'] == []
    assert sorted(card['id'] for card in again['druid']['real']) == ['cosmetic', 'real']


def test_update_refreshes_only_cosmetic_cards_and_registry_skips_second_run(tmp_path):
    root = tmp_path
    sources = root / 'sources'
    _source_tree(sources)
    report = _write(sources / 'cambios/2026-11-18-0100.md', 'Change report\n')
    cards = root / 'cards'
    cards.mkdir()
    _card(cards / '04-clase-druid.json', 'cosmetic', 'Overview')
    _write(cards / '04-clase-druid.json', json.dumps({'sections': [
        {'id': 'cosmetic', 'source_hashes': ['section:old'], 'sources': [
            {'url': 'https://example.test/druid', 'ref': 'Wowhead: Druid › Overview'}]},
        {'id': 'real', 'source_hashes': ['section:old'], 'sources': [
            {'url': 'https://example.test/druid', 'ref': 'Wowhead: Druid › Rotation'}]},
    ]}, indent=2) + '\n')
    corpus = root / 'corpus.sqlite'
    guide_update.corpus_tool.import_corpus(sources, corpus, root / 'initial.md')
    packs = root / 'packs'
    packs.mkdir()
    _write(packs / 'druid-a.md', _pack(URL_OLD))
    _write(packs / 'druid-b.md', '')
    registry = root / 'registry.json'
    out = root / 'out'

    assert guide_update.update(report=report, sources=sources, corpus=corpus,
                               cards=cards, packs=packs, wowdb=root / 'missing.sqlite',
                               out=out, registry=registry) == 0

    saved = json.loads((cards / '04-clase-druid.json').read_text(encoding='utf-8'))
    sections = {section['id']: section for section in saved['sections']}
    assert sections['cosmetic']['source_hashes'] != ['section:old']
    assert sections['real']['source_hashes'] == ['section:old']
    assert json.loads(registry.read_text(encoding='utf-8'))[report.name]
    before = {
        path: path.read_bytes() for path in
        (cards / '04-clase-druid.json', packs / 'druid-a.md', registry)
    }
    assert guide_update.update(sources=sources, corpus=corpus, cards=cards,
                               packs=packs, wowdb=root / 'missing.sqlite',
                               out=out, registry=registry) == 0
    assert all(path.read_bytes() == data for path, data in before.items())


def test_dry_run_writes_no_cards_packs_or_registry(tmp_path):
    root = tmp_path
    sources = root / 'sources'
    _source_tree(sources)
    report = _write(sources / 'cambios/2026-11-18-0101.md', 'Change report\n')
    cards = root / 'cards'
    cards.mkdir()
    _card(cards / '04-clase-druid.json', 'card', 'Overview')
    corpus = root / 'corpus.sqlite'
    guide_update.corpus_tool.import_corpus(sources, corpus, root / 'initial.md')
    packs = root / 'packs'
    packs.mkdir()
    pack_path = _write(packs / 'druid-a.md', _pack(URL_OLD))
    card_path = cards / '04-clase-druid.json'
    registry = root / 'registry.json'
    card_before, pack_before, corpus_before = (
        card_path.read_bytes(), pack_path.read_bytes(), corpus.read_bytes())

    assert guide_update.update(report=report, dry_run=True, sources=sources,
                               corpus=corpus, cards=cards, packs=packs,
                               wowdb=root / 'missing.sqlite', out=root / 'out',
                               registry=registry) == 0

    assert card_path.read_bytes() == card_before
    assert pack_path.read_bytes() == pack_before
    assert corpus.read_bytes() == corpus_before
    assert not registry.exists()
    assert (root / 'out/2026-11-18-0101-prueba/INFORME.md').is_file()
