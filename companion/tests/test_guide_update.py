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
GUIDE_URL = 'https://example.test/druid'
URL_OLD = ('https://www.wowhead.com/forever/talent-calc/druid/'
           'v25232-001_t0_r2/0AC')
URL_NEW = ('https://www.wowhead.com/forever/talent-calc/druid/'
           'vkndmh5232-001_t0/2D')
OLD_BODY = '## Overview\nTexto base.\n'
STRUCTURED = (
    '**Talent Build — Druid: Balance 51 (51 points)**\n'
    '\n'
    '#### Balance (51/51)\n'
    '\n'
    '| Talent | Rank |\n'
    '| --- | --- |\n'
    '| Malice | 5/5 |\n'
    '\n'
    '**Talent Order**\n'
    '\n'
    '| Level | Talent | Rank |\n'
    '| --- | --- | --- |\n'
    '| 10 | Malice | Rank 1 |\n'
    '\n'
    '**Map: Durotar**\n'
    '\n'
    '- Razor Hill (52, 43)\n')


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _quoted(text: str) -> str:
    return ''.join(f'> {line}\n' if line else '>\n' for line in text.splitlines())


def _source(root: Path, body: str) -> Path:
    return _write(root / 'wowhead/classes/druid/balance/overview-pve-dps.md',
                  '---\n'
                  'title: Druid overview\n'
                  f'url: {GUIDE_URL}\n'
                  '---\n'
                  f'{body}')


def _section_hash(corpus: Path, heading: str = 'Overview') -> str:
    conn = sqlite3.connect(corpus)
    try:
        return conn.execute(
            'SELECT hash FROM sections WHERE guide_key = ? AND heading_path = ?',
            (GUIDE_KEY, heading)).fetchone()[0]
    finally:
        conn.close()


def _card(cards: Path, filename: str, card_id: str, heading: str,
          stored: str) -> None:
    _write(cards / filename, json.dumps({'sections': [{
        'id': card_id,
        'source_hashes': [stored],
        'sources': [{'url': GUIDE_URL, 'ref': f'Wowhead: Druid › {heading}'}],
    }]}, ensure_ascii=False, indent=2) + '\n')


def _report_json(report: Path, guides: list[dict]) -> None:
    _write(report.with_suffix('.json'), json.dumps({
        'version': 1, 'stamp': report.stem, 'guides': guides,
    }, ensure_ascii=False, indent=2) + '\n')


def _manual_db(path: Path, sections: list[tuple[str, str, str]]) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript('''
        CREATE TABLE guides (
            guide_key TEXT, source TEXT, url TEXT, topic TEXT,
            superseded_by TEXT, hash TEXT
        );
        CREATE TABLE sections (
            guide_key TEXT, heading TEXT, heading_path TEXT, text TEXT,
            hash TEXT, ord INTEGER
        );
    ''')
    conn.execute('INSERT INTO guides VALUES (?, ?, ?, ?, ?, ?)',
                 (GUIDE_KEY, 'wowhead', GUIDE_URL,
                  'class:druid:balance:overview', None, 'guide-hash'))
    conn.executemany(
        'INSERT INTO sections VALUES (?, ?, ?, ?, ?, ?)',
        [(GUIDE_KEY, heading, heading, text, hash_, index)
         for index, (heading, text, hash_) in enumerate(sections)])
    conn.commit()
    conn.close()
    return path


def _cards_with(entries: list[tuple[str, str, str]]) -> str:
    return json.dumps({'sections': [
        {'id': card_id, 'source_hashes': [stored], 'sources': [
            {'url': GUIDE_URL, 'ref': f'Wowhead: Druid › {heading}'}]}
        for card_id, heading, stored in entries
    ]}, ensure_ascii=False, indent=2) + '\n'


def _cards_with_sources(card_id: str, entries: list[tuple[str, str]]) -> str:
    return json.dumps({'sections': [{
        'id': card_id,
        'source_hashes': [stored for _heading, stored in entries],
        'sources': [{'url': GUIDE_URL, 'ref': f'Wowhead: Druid › {heading}'}
                    for heading, _stored in entries],
    }]}, ensure_ascii=False, indent=2) + '\n'


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


def test_classify_cards_cosmetic_applies_to_class_and_non_class(tmp_path):
    cards = tmp_path / 'cards'
    _write(cards / '04-clase-druid.json', _cards_with([
        ('class-cosmetic', 'Overview', 'section:old-overview')]))
    _write(cards / '01-general.json', _cards_with([
        ('other-cosmetic', 'Overview', 'section:old-overview')]))
    db = _manual_db(tmp_path / 'corpus.sqlite', [
        ('Overview', f'## Overview\nBuild: [{URL_NEW}]({URL_NEW})\n', 'new-overview')])
    old = {(GUIDE_KEY, 'Overview'):
           (f'## Overview\nBuild: [{URL_OLD}]({URL_OLD})\n', 'old-overview')}

    result = guide_update.classify_cards(
        cards, {'class-cosmetic', 'other-cosmetic'}, db, old, {})

    assert [card['id'] for card in result['druid']['cosmetic']] == ['class-cosmetic']
    assert [card['id'] for card in result['other']['cosmetic']] == ['other-cosmetic']
    assert result['druid']['real'] == []
    assert result['other']['real'] == []


def test_classify_cards_requires_the_stored_old_hash_as_evidence(tmp_path):
    cards = tmp_path / 'cards'
    _write(cards / '04-clase-druid.json', _cards_with([
        ('desfasada', 'Overview', 'section:otro-hash')]))
    db = _manual_db(tmp_path / 'corpus.sqlite', [
        ('Overview', '## Overview\nTexto nuevo.\n', 'new-overview')])
    old = {(GUIDE_KEY, 'Overview'): ('## Overview\nTexto viejo.\n', 'old-overview')}

    result = guide_update.classify_cards(cards, {'desfasada'}, db, old, {})

    assert [card['id'] for card in result['druid']['real']] == ['desfasada']
    assert result['druid']['cosmetic'] == []


def test_classify_cards_without_a_difference_in_this_run_is_real(tmp_path):
    cards = tmp_path / 'cards'
    _write(cards / '04-clase-druid.json', _cards_with([
        ('sin-cambio', 'Overview', 'section:old-overview')]))
    db = _manual_db(tmp_path / 'corpus.sqlite', [
        ('Overview', '## Overview\nTexto base.\n', 'old-overview')])
    old = {(GUIDE_KEY, 'Overview'): ('## Overview\nTexto base.\n', 'old-overview')}

    result = guide_update.classify_cards(cards, {'sin-cambio'}, db, old, {})

    assert [card['id'] for card in result['druid']['real']] == ['sin-cambio']


def test_classify_cards_section_changed_earlier_makes_the_card_real(tmp_path):
    cards = tmp_path / 'cards'
    _write(cards / '04-clase-druid.json', _cards_with_sources('mixta', [
        ('Overview', 'section:viejo-overview'),
        ('Rotation', 'section:viejo-rotation')]))
    db = _manual_db(tmp_path / 'corpus.sqlite', [
        ('Overview', '## Overview\nTexto base.\n', 'overview-pasada'),
        ('Rotation', OLD_BODY + '\n' + STRUCTURED, 'nueva-rotation')])
    old = {
        (GUIDE_KEY, 'Overview'): ('## Overview\nTexto base.\n', 'overview-pasada'),
        (GUIDE_KEY, 'Rotation'): (OLD_BODY, 'viejo-rotation'),
    }

    result = guide_update.classify_cards(
        cards, {'mixta'}, db, old, {}, {GUIDE_KEY: 'recovered'})

    assert [card['id'] for card in result['druid']['real']] == ['mixta']
    assert result['druid']['structured'] == []


def test_classify_cards_guide_hash_counts_the_earlier_section_as_reviewed(tmp_path):
    cards = tmp_path / 'cards'
    _write(cards / '04-clase-druid.json', _cards_with_sources('mixta', [
        ('Overview', 'guide:guide-hash'),
        ('Rotation', 'section:viejo-rotation')]))
    db = _manual_db(tmp_path / 'corpus.sqlite', [
        ('Overview', '## Overview\nTexto base.\n', 'overview-pasada'),
        ('Rotation', OLD_BODY + '\n' + STRUCTURED, 'nueva-rotation')])
    old = {
        (GUIDE_KEY, 'Overview'): ('## Overview\nTexto base.\n', 'overview-pasada'),
        (GUIDE_KEY, 'Rotation'): (OLD_BODY, 'viejo-rotation'),
    }

    result = guide_update.classify_cards(
        cards, {'mixta'}, db, old, {GUIDE_KEY: 'guide-hash'},
        {GUIDE_KEY: 'recovered'})

    assert [card['id'] for card in result['druid']['structured']] == ['mixta']


def test_classify_cards_structured_removes_talent_and_map_blocks(tmp_path):
    old_text = OLD_BODY
    new_text = OLD_BODY + '\n' + STRUCTURED
    cards = tmp_path / 'cards'
    _write(cards / '04-clase-druid.json', _cards_with([
        ('estructurada', 'Overview', 'section:old-overview')]))
    db = _manual_db(tmp_path / 'corpus.sqlite', [
        ('Overview', new_text, 'new-overview')])
    old = {(GUIDE_KEY, 'Overview'): (old_text, 'old-overview')}

    result = guide_update.classify_cards(
        cards, {'estructurada'}, db, old, {}, {GUIDE_KEY: 'recovered'})

    assert [card['id'] for card in result['druid']['structured']] == ['estructurada']


def test_classify_cards_structured_also_when_blockquoted(tmp_path):
    old_text = OLD_BODY
    new_text = OLD_BODY + '\n' + _quoted(STRUCTURED)
    cards = tmp_path / 'cards'
    _write(cards / '04-clase-druid.json', _cards_with([
        ('estructurada', 'Overview', 'section:old-overview')]))
    db = _manual_db(tmp_path / 'corpus.sqlite', [
        ('Overview', new_text, 'new-overview')])
    old = {(GUIDE_KEY, 'Overview'): (old_text, 'old-overview')}

    result = guide_update.classify_cards(
        cards, {'estructurada'}, db, old, {}, {GUIDE_KEY: 'visual'})

    assert [card['id'] for card in result['druid']['structured']] == ['estructurada']


def test_strip_structured_blocks_ends_the_talent_order_table_at_the_blank_line():
    text = ('**Talent Order**\n\n'
            '| Level | Talent | Rank |\n'
            '| --- | --- | --- |\n'
            '| 10 | Malice | Rank 1 |\n\n'
            '| Nivel | Zona |\n'
            '| --- | --- |\n'
            '| 20 | Durotar |\n')

    stripped = guide_update._strip_structured_blocks(text)

    assert '| Level | Talent | Rank |' not in stripped
    assert '| 10 | Malice | Rank 1 |' not in stripped
    assert '| Nivel | Zona |' in stripped


def test_strip_structured_blocks_ignores_a_table_that_is_not_level_talent_rank():
    text = ('**Talent Order**\n\n'
            '| Nivel | Zona |\n'
            '| --- | --- |\n'
            '| 20 | Durotar |\n')

    assert '| Nivel | Zona |' in guide_update._strip_structured_blocks(text)


def test_strip_structured_blocks_ends_the_talent_build_table_at_the_blank_line():
    text = ('**Talent Build — Druid: Balance 51 (51 points)**\n\n'
            '#### Balance (51/51)\n\n'
            '| Talent | Rank |\n'
            '| --- | --- |\n'
            '| Malice | 5/5 |\n\n'
            '| Nivel | Zona |\n'
            '| --- | --- |\n'
            '| 20 | Durotar |\n')

    stripped = guide_update._strip_structured_blocks(text)

    assert '| Malice | 5/5 |' not in stripped
    assert '| Nivel | Zona |' in stripped


def test_strip_structured_blocks_ignores_a_table_after_the_tree_heading():
    text = ('**Talent Build — Druid: Balance 51 (51 points)**\n\n'
            '#### Balance (51/51)\n\n'
            '| Otro | Formato |\n'
            '| --- | --- |\n'
            '| A | B |\n')

    assert '| Otro | Formato |' in guide_update._strip_structured_blocks(text)


def test_strip_structured_blocks_keeps_the_following_trees_of_the_build():
    text = ('**Talent Build — Druid: Balance 51 (51 points)**\n\n'
            '#### Balance (51/51)\n\n'
            '| Talent | Rank |\n'
            '| --- | --- |\n'
            '| Malice | 5/5 |\n\n'
            '#### Restoration (0/51)\n\n'
            '| Talent | Rank |\n'
            '| --- | --- |\n'
            '| Furor | 3/3 |\n')

    assert guide_update._strip_structured_blocks(text).strip() == ''


def test_classify_cards_recovered_when_the_text_really_changes(tmp_path):
    cards = tmp_path / 'cards'
    _write(cards / '04-clase-druid.json', _cards_with([
        ('recuperada', 'Overview', 'section:old-overview')]))
    db = _manual_db(tmp_path / 'corpus.sqlite', [
        ('Overview', '## Overview\nTexto distinto.\n', 'new-overview')])
    old = {(GUIDE_KEY, 'Overview'): ('## Overview\nTexto base.\n', 'old-overview')}

    result = guide_update.classify_cards(
        cards, {'recuperada'}, db, old, {}, {GUIDE_KEY: 'recovered'})

    assert [card['id'] for card in result['druid']['recovered']] == ['recuperada']


def test_guide_kinds_game_wins_and_missing_json_means_game(tmp_path):
    old = tmp_path / '2026-11-18-0100.md'
    _write(old, 'Change report\n')
    _report_json(old, [{
        'path': 'classes/druid/balance/overview-pve-dps.md',
        'status': 'updated', 'reason': 'format', 'change_kind': 'info'}])
    assert guide_update._guide_kinds([old]) == {GUIDE_KEY: 'recovered'}

    game = tmp_path / '2026-11-18-0101.md'
    _write(game, 'Change report\n')
    _report_json(game, [{
        'path': 'classes/druid/balance/overview-pve-dps.md',
        'status': 'updated'}])
    assert guide_update._guide_kinds([old, game])[GUIDE_KEY] == 'game'

    without_json = tmp_path / '2026-11-18-0102.md'
    _write(without_json, 'Change report\n')
    assert guide_update._guide_kinds([old, without_json]) == {}


def test_update_processes_all_pending_reports_in_one_pass(tmp_path):
    root = tmp_path
    sources = root / 'sources'
    _source(sources, f'## Overview\nBuild: [{URL_OLD}]({URL_OLD})\n')
    cards = root / 'cards'
    cards.mkdir()
    corpus = root / 'corpus.sqlite'
    guide_update.corpus_tool.import_corpus(sources, corpus, root / 'initial.md')
    stored = 'section:' + _section_hash(corpus)
    _card(cards, '04-clase-druid.json', 'cosmetica', 'Overview', stored)
    _source(sources, f'## Overview\nBuild: [{URL_NEW}]({URL_NEW})\n')
    packs = root / 'packs'
    _write(packs / 'druid-a.md', '')
    _write(packs / 'druid-b.md', '')
    old_report = _write(sources / 'cambios/2026-11-18-0100.md', 'Viejo\n')
    new_report = _write(sources / 'cambios/2026-11-18-0300.md', 'Nuevo\n')
    registry = root / 'registry.json'
    out = root / 'out'

    assert guide_update.update(sources=sources, corpus=corpus, cards=cards,
                               packs=packs, wowdb=root / 'missing.sqlite',
                               out=out, registry=registry) == 0

    saved = json.loads((cards / '04-clase-druid.json').read_text(encoding='utf-8'))
    assert saved['sections'][0]['source_hashes'] != [stored]
    assert set(json.loads(registry.read_text(encoding='utf-8'))) == {
        old_report.name, new_report.name}
    report = out / '2026-11-18-0300' / 'INFORME.md'
    text = report.read_text(encoding='utf-8')
    assert old_report.name in text and new_report.name in text
    conn = sqlite3.connect(corpus)
    try:
        assert conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 2
    finally:
        conn.close()


def test_update_explicit_missing_report_fails_with_code_1(tmp_path):
    root = tmp_path
    sources = root / 'sources'
    sources.mkdir()
    out = root / 'out'
    registry = root / 'registry.json'
    corpus = root / 'corpus.sqlite'

    assert guide_update.update(
        reports=[root / 'cambios/2026-11-18-0100.md'], sources=sources,
        corpus=corpus, cards=root / 'cards', packs=root / 'packs',
        wowdb=root / 'missing.sqlite', out=out, registry=registry) == 1

    assert not out.exists()
    assert not registry.exists()
    assert not corpus.exists()


def test_update_keeps_structured_cards_unless_refresh_flag(tmp_path):
    def scenario(name: str) -> dict:
        root = tmp_path / name
        sources = root / 'sources'
        _source(sources, OLD_BODY)
        cards = root / 'cards'
        cards.mkdir()
        corpus = root / 'corpus.sqlite'
        guide_update.corpus_tool.import_corpus(sources, corpus, root / 'initial.md')
        stored = 'section:' + _section_hash(corpus)
        _card(cards, '04-clase-druid.json', 'estructurada', 'Overview', stored)
        _source(sources, OLD_BODY + '\n' + STRUCTURED)
        report = _write(sources / 'cambios/2026-11-18-0400.md', 'Cambio\n')
        _report_json(report, [{
            'path': 'classes/druid/balance/overview-pve-dps.md',
            'status': 'updated', 'reason': 'format', 'change_kind': 'info'}])
        return {'root': root, 'sources': sources, 'cards': cards,
                'corpus': corpus, 'report': report, 'stored': stored,
                'packs': root / 'packs', 'registry': root / 'registry.json',
                'out': root / 'out'}

    def run(data: dict, refresh: bool) -> int:
        return guide_update.update(
            reports=[data['report']], refresh_structured=refresh,
            sources=data['sources'], corpus=data['corpus'], cards=data['cards'],
            packs=data['packs'], wowdb=data['root'] / 'missing.sqlite',
            out=data['out'], registry=data['registry'])

    quiet = scenario('quiet')
    assert run(quiet, refresh=False) == 0
    saved = json.loads((quiet['cards'] / '04-clase-druid.json').read_text(encoding='utf-8'))
    assert saved['sections'][0]['source_hashes'] == [quiet['stored']]
    data = json.loads((quiet['out'] / '2026-11-18-0400/druid.json').read_text(encoding='utf-8'))
    assert data['stale_structured'] == ['estructurada']

    forced = scenario('forced')
    assert run(forced, refresh=True) == 0
    saved = json.loads((forced['cards'] / '04-clase-druid.json').read_text(encoding='utf-8'))
    assert saved['sections'][0]['source_hashes'] != [forced['stored']]


def test_update_keeps_mixed_cards_real_even_with_refresh_structured(tmp_path):
    root = tmp_path
    sources = root / 'sources'
    _source(sources, '## Overview\nTexto base.\n\n## Rotation\nRotación base.\n')
    cards = root / 'cards'
    cards.mkdir()
    corpus = root / 'corpus.sqlite'
    guide_update.corpus_tool.import_corpus(sources, corpus, root / 'initial.md')
    _write(cards / '04-clase-druid.json', _cards_with_sources('mixta', [
        ('Overview', 'section:' + _section_hash(corpus, 'Overview')),
        ('Rotation', 'section:' + _section_hash(corpus, 'Rotation'))]))
    # Overview cambió en una pasada anterior que no refrescó la ficha.
    _source(sources, '## Overview\nTexto base cambiado.\n\n## Rotation\nRotación base.\n')
    guide_update.corpus_tool.import_corpus(sources, corpus, root / 'anterior.md')
    _source(sources, '## Overview\nTexto base cambiado.\n\n## Rotation\n'
                     'Rotación base.\n\n' + STRUCTURED)
    report = _write(sources / 'cambios/2026-11-18-0800.md', 'Formato\n')
    _report_json(report, [{
        'path': 'classes/druid/balance/overview-pve-dps.md',
        'status': 'updated', 'reason': 'format', 'change_kind': 'info'}])
    before = (cards / '04-clase-druid.json').read_bytes()

    assert guide_update.update(reports=[report], refresh_structured=True,
                               sources=sources, corpus=corpus, cards=cards,
                               packs=root / 'packs',
                               wowdb=root / 'missing.sqlite', out=root / 'out',
                               registry=root / 'registry.json') == 0

    assert (cards / '04-clase-druid.json').read_bytes() == before
    data = json.loads((root / 'out/2026-11-18-0800/druid.json').read_text(encoding='utf-8'))
    assert data['stale_real'] == ['mixta']
    assert data['stale_structured'] == []


def test_update_never_refreshes_recovered_and_writes_its_diff(tmp_path):
    root = tmp_path
    sources = root / 'sources'
    _source(sources, '## Overview\nTexto viejo.\n')
    cards = root / 'cards'
    cards.mkdir()
    corpus = root / 'corpus.sqlite'
    guide_update.corpus_tool.import_corpus(sources, corpus, root / 'initial.md')
    stored = 'section:' + _section_hash(corpus)
    _card(cards, '04-clase-druid.json', 'recuperada', 'Overview', stored)
    _source(sources, '## Overview\nTexto nuevo distinto.\n')
    report = _write(sources / 'cambios/2026-11-18-0500.md', 'Cambio\n')
    _report_json(report, [{
        'path': 'classes/druid/balance/overview-pve-dps.md',
        'status': 'updated', 'reason': 'format', 'change_kind': 'info'}])
    out = root / 'out'
    registry = root / 'registry.json'

    assert guide_update.update(reports=[report], sources=sources, corpus=corpus,
                               cards=cards, packs=root / 'packs',
                               wowdb=root / 'missing.sqlite', out=out,
                               registry=registry) == 0

    saved = json.loads((cards / '04-clase-druid.json').read_text(encoding='utf-8'))
    assert saved['sections'][0]['source_hashes'] == [stored]
    data = json.loads((out / '2026-11-18-0500/druid.json').read_text(encoding='utf-8'))
    assert data['stale_recovered'] == ['recuperada']
    diff = (out / '2026-11-18-0500/recuperado-recuperada.diff').read_text(encoding='utf-8')
    assert 'Texto viejo.' in diff and 'Texto nuevo distinto.' in diff


def test_update_game_precedence_beats_recovered(tmp_path):
    root = tmp_path
    sources = root / 'sources'
    _source(sources, '## Overview\nTexto viejo.\n')
    cards = root / 'cards'
    cards.mkdir()
    corpus = root / 'corpus.sqlite'
    guide_update.corpus_tool.import_corpus(sources, corpus, root / 'initial.md')
    stored = 'section:' + _section_hash(corpus)
    _card(cards, '04-clase-druid.json', 'juego', 'Overview', stored)
    _source(sources, '## Overview\nTexto nuevo distinto.\n')
    formatted = _write(sources / 'cambios/2026-11-18-0600.md', 'Formato\n')
    _report_json(formatted, [{
        'path': 'classes/druid/balance/overview-pve-dps.md',
        'status': 'updated', 'reason': 'format', 'change_kind': 'info'}])
    edited = _write(sources / 'cambios/2026-11-18-0700.md', 'Edición\n')
    _report_json(edited, [{
        'path': 'classes/druid/balance/overview-pve-dps.md',
        'status': 'updated'}])
    out = root / 'out'

    assert guide_update.update(sources=sources, corpus=corpus, cards=cards,
                               packs=root / 'packs',
                               wowdb=root / 'missing.sqlite', out=out,
                               registry=root / 'registry.json') == 0

    data = json.loads((out / '2026-11-18-0700/druid.json').read_text(encoding='utf-8'))
    assert data['stale_real'] == ['juego']
    assert data['stale_recovered'] == []
    assert not (out / '2026-11-18-0700/recuperado-juego.diff').exists()


def test_update_refreshes_cosmetic_cards_and_skips_registered(tmp_path):
    root = tmp_path
    sources = root / 'sources'
    _source(sources, f'## Overview\nBuild: [{URL_OLD}]({URL_OLD})\n')
    cards = root / 'cards'
    cards.mkdir()
    corpus = root / 'corpus.sqlite'
    guide_update.corpus_tool.import_corpus(sources, corpus, root / 'initial.md')
    with sqlite3.connect(corpus) as conn:
        rows = dict(conn.execute(
            'SELECT heading_path, hash FROM sections WHERE guide_key = ?',
            (GUIDE_KEY,)).fetchall())
    stored = 'section:' + rows['Overview']
    _write(cards / '04-clase-druid.json', _cards_with([
        ('cosmetica', 'Overview', stored),
        ('real', 'Rotation', 'section:old'),
    ]))
    _write(cards / '01-general.json', _cards_with([
        ('otra-cosmetica', 'Overview', stored)]))
    _source(sources, f'## Overview\nBuild: [{URL_NEW}]({URL_NEW})\n')
    report = _write(sources / 'cambios/2026-11-18-0100.md', 'Change report\n')
    packs = root / 'packs'
    _write(packs / 'druid-a.md', '')
    _write(packs / 'druid-b.md', '')
    registry = root / 'registry.json'
    out = root / 'out'

    assert guide_update.update(reports=[report], sources=sources, corpus=corpus,
                               cards=cards, packs=packs,
                               wowdb=root / 'missing.sqlite', out=out,
                               registry=registry) == 0

    saved = json.loads((cards / '04-clase-druid.json').read_text(encoding='utf-8'))
    sections = {section['id']: section for section in saved['sections']}
    assert sections['cosmetica']['source_hashes'] != [stored]
    assert sections['real']['source_hashes'] == ['section:old']
    general = json.loads((cards / '01-general.json').read_text(encoding='utf-8'))
    assert general['sections'][0]['source_hashes'] != [stored]

    before = {path: path.read_bytes() for path in (
        cards / '04-clase-druid.json', cards / '01-general.json',
        packs / 'druid-a.md', registry)}
    assert guide_update.update(sources=sources, corpus=corpus, cards=cards,
                               packs=packs, wowdb=root / 'missing.sqlite',
                               out=out, registry=registry) == 0
    assert all(path.read_bytes() == data for path, data in before.items())


def test_dry_run_leaves_everything_byte_identical(tmp_path, capsys):
    root = tmp_path
    sources = root / 'sources'
    _source(sources, f'## Overview\nBuild: [{URL_OLD}]({URL_OLD})\n')
    cards = root / 'cards'
    cards.mkdir()
    corpus = root / 'corpus.sqlite'
    guide_update.corpus_tool.import_corpus(sources, corpus, root / 'initial.md')
    stored = 'section:' + _section_hash(corpus)
    _card(cards, '04-clase-druid.json', 'card', 'Overview', stored)
    _source(sources, f'## Overview\nBuild: [{URL_NEW}]({URL_NEW})\n')
    report = _write(sources / 'cambios/2026-11-18-0101.md', 'Change report\n')
    _report_json(report, [{
        'path': 'classes/druid/balance/overview-pve-dps.md',
        'status': 'updated'}])
    packs = root / 'packs'
    pack_path = _write(packs / 'druid-a.md', 'pack viejo\n')
    card_path = cards / '04-clase-druid.json'
    registry = root / 'registry.json'
    _write(registry, '{\n  "2026-11-17-0100.md": "2026-11-17T01:00:00+00:00"\n}\n')
    before = {path: path.read_bytes() for path in (
        card_path, pack_path, corpus, registry)}

    assert guide_update.update(reports=[report], dry_run=True, sources=sources,
                               corpus=corpus, cards=cards, packs=packs,
                               wowdb=root / 'missing.sqlite', out=root / 'out',
                               registry=registry) == 0

    assert all(path.read_bytes() == data for path, data in before.items())
    assert not (root / 'out').exists()
    output = capsys.readouterr().out
    assert 'cosméticas' in output
    assert 'Informe:' not in output
