"""Pruebas de la herramienta de corpus privado de guías."""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent.parent / 'tools' / 'corpus.py'
SPEC = importlib.util.spec_from_file_location('corpus', MODULE_PATH)
corpus = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(corpus)


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _guide(title: str = 'Guía', body: str = '') -> str:
    return f'---\ntitle: "{title}"\nauthor: Docoda\nurl: https://example.test/{title}\n---\n{body}'


def test_front_matter_accepts_quotes_crlf_and_missing_values():
    text = ('---\r\ntitle: "Una guía"\r\nauthor: Docoda\r\n'
            'url: https://example.test/a:b\r\nclass: "hunter"\r\n---\r\n'
            'Cuerpo\r\n')
    front, body = corpus.parse_front_matter(text)
    assert front['title'] == 'Una guía'
    assert front['url'] == 'https://example.test/a:b'
    assert front['class'] == 'hunter'
    assert body == 'Cuerpo\n'
    assert corpus.parse_front_matter('Sin front matter') == ({}, 'Sin front matter')


def test_sections_keep_deep_headings_inside_parent_and_suffix_repeats():
    body = ('Intro\n'
            '## Uno\nA\n'
            '### Sub\nB\n'
            '#### Detalle\nC\n'
            '### Sub\nD\n'
            '## Uno\nE\n')
    sections = corpus.split_sections('wowhead/guia', body)
    assert [s['level'] for s in sections] == [0, 2, 3, 3, 2]
    assert [s['ord'] for s in sections] == [0, 1, 2, 3, 4]
    assert sections[0]['section_id'] == 'wowhead/guia#intro'
    assert sections[1]['heading_path'] == 'Uno'
    assert sections[2]['heading_path'] == 'Uno > Sub'
    assert sections[2]['section_id'] == 'wowhead/guia#Uno > Sub'
    assert '#### Detalle' in sections[2]['text']
    assert 'C' in sections[2]['text']
    assert 'B' not in sections[1]['text']
    assert sections[3]['section_id'] == 'wowhead/guia#Uno > Sub~2'
    assert sections[4]['section_id'] == 'wowhead/guia#Uno~2'


def test_entities_and_way_formats():
    text = (
        ' [Anacondra](https://www.wowhead.com/forever/npc=3671) '
        '[Quest](https://www.wowhead.com/forever/quest=962) '
        '[Item](https://www.wowhead.com/forever/item=123) '
        '[Spell](https://www.wowhead.com/forever/spell=456) '
        '/way 34 21 /way 49.0 86.4 /way #44 10.5, 72.7')
    assert corpus.extract_entities(text) == [
        ('npc', 3671, 'Anacondra'), ('quest', 962, 'Quest'),
        ('item', 123, 'Item'), ('spell', 456, 'Spell')]
    assert corpus.extract_coords(text) == [
        ('/way 34 21', 34.0, 21.0),
        ('/way 49.0 86.4', 49.0, 86.4),
        ('/way #44 10.5, 72.7', 10.5, 72.7)]


def test_topic_keys_cover_the_rule_families():
    specs = {'hunter': {'beast-mastery', 'marksmanship', 'survival'},
             'warrior': {'arms'}}
    cases = {
        ('wowhead', 'classes/hunter/beast-mastery/overview-pve-dps'):
            'class:hunter:beast-mastery:overview',
        ('wowhead', 'classes/hunter/beast-mastery/rotation-cooldowns-pve-dps'):
            'class:hunter:beast-mastery:rotation',
        ('wowhead', 'classes/hunter/beast-mastery/stat-priority-pve-dps'):
            'class:hunter:beast-mastery:stats',
        ('wowhead', 'classes/hunter/beast-mastery/talent-builds-pve-dps'):
            'class:hunter:beast-mastery:talents',
        ('wowhead', 'classes/hunter/beast-mastery/bis-gear'):
            'class:hunter:beast-mastery:bis',
        ('wowhead', 'classes/hunter/beast-mastery/enchants-consumables-pve-dps'):
            'class:hunter:beast-mastery:enchants',
        ('wowhead', 'classes/hunter/beast-mastery/dps-leveling-tips'):
            'class:hunter:beast-mastery:leveling',
        ('wowhead', 'classes/hunter/beast-mastery/dps-abilities'):
            'class:hunter:beast-mastery:abilities',
        ('wowhead', 'classes/hunter/beast-mastery/level-20-dps-overview'):
            'class:hunter:beast-mastery:level20',
        ('wowhead', 'classes/hunter/beast-mastery/level-30-dps-overview'):
            'class:hunter:beast-mastery:level30',
        ('wowhead', 'classes/hunter/beast-mastery/other-build'):
            'class:hunter:beast-mastery:other-build',
        ('wowhead', 'classes/hunter/leveling-guide'):
            'class:hunter:general:leveling-guide',
        ('wowhead', 'classes/tier-lists/pvp-dps'):
            'tierlist:pvp-dps',
        ('wowhead', 'classes/weapon-trainer-skill-locations'):
            'general:weapon-trainer-skill-locations',
        ('wowhead', 'the-deadmines-dungeon-overview-location-rewards'):
            'dungeon:deadmines',
        ('wowhead', 'dungeons/foo'):
            'dungeon:_all:foo',
        ('wowhead', 'raid-guide'):
            'raid:raid-guide',
        ('wowhead', 'raids/foo'):
            'raid:foo',
        ('wowhead', 'professions/alchemy/foo'):
            'profession:alchemy:foo',
        ('wowhead', 'professions/alchemy-overview-trainer-locations-recipes'):
            'profession:alchemy:overview',
        ('wowhead', 'professions/foo'):
            'profession:_all:foo',
        ('wowhead', 'reputation/foo'):
            'reputation:foo',
        ('wowhead', 'collections/foo'):
            'collection:foo',
        ('wowhead', 'ui/foo'):
            'ui:foo',
        ('wowhead', 'balance-druid-leveling-guide-for-wow-forever-35076'):
            'class:druid:extra:balance-druid-leveling-guide-for-wow-forever',
        ('icy-veins', 'clases/hunter/beast-mastery-hunter-leveling'):
            'class:hunter:beast-mastery:leveling',
        ('icy-veins', 'clases/hunter/beast-mastery-hunter-ranged-dps-pve-guide'):
            'class:hunter:beast-mastery:overview',
        ('icy-veins', 'clases/hunter/beast-mastery-hunter-spec-builds-talents'):
            'class:hunter:beast-mastery:talents',
        ('icy-veins', 'clases/hunter/beast-mastery-hunter-stat-priority'):
            'class:hunter:beast-mastery:stats',
        ('icy-veins', 'clases/hunter/hunter-class-overview'):
            'class:hunter:general:hunter-class-overview',
        ('icy-veins', 'mazmorras/the-stockade-guide'):
            'dungeon:stockade',
        ('icy-veins', 'mazmorras/the-stockade-quests'):
            'dungeon:_all:quests',
        ('icy-veins', 'profesiones/alchemy'):
            'profession:alchemy:overview',
        ('icy-veins', 'razas/human-race-guide'):
            'race:human',
        ('icy-veins', 'tier-lists/pvp'):
            'tierlist:pvp',
        ('icy-veins', 'general/foo'):
            'general:foo',
    }
    for (source, path), expected in cases.items():
        assert corpus.topic_key(source, path, specs) == expected


def test_normalize_text_ignores_links_markup_and_whitespace():
    a = ('## Uno\n[Uno](https://example.test/a)\n**Texto**  con   espacios\n')
    b = '## Uno\nUno\nTexto con espacios\n'
    assert corpus.normalize_text(a) == corpus.normalize_text(b)


def test_import_corpus_marks_changes_dedupes_supersedes_and_searches(tmp_path):
    sources = tmp_path / 'sources'
    long_text = 'Dragon ' + ('contenido repetido ' * 20)
    _write(sources, 'wowhead/classes/hunter/beast-mastery/overview-pve-dps.md',
           _guide('Beast Mastery', 'Intro dragon\n## Uno\n' + long_text))
    _write(sources, 'wowhead/classes/hunter/beast-mastery/dps-leveling-tips.md',
           _guide('Hunter leveling', '## Leveling\nHunter text'))
    _write(sources, 'wowhead/classes/hunter/leveling-guide.md',
           _guide('Hunter general', '## General\nGeneral text'))
    _write(sources, 'wowhead/the-deadmines-dungeon-overview-location-rewards.md',
           _guide('Deadmines', '## Dungeon\nDeadmines text'))
    _write(sources, 'wowhead/balance-druid-leveling-guide-for-wow-forever-35076.md',
           _guide('Druid', '## Druid\nDruid text'))
    _write(sources, 'icy-veins/guides/clases/hunter/beast-mastery-hunter-leveling.md',
           _guide('Icy leveling', '## Uno\n' + long_text))
    _write(sources, 'icy-veins/guides/clases/hunter/hunter-class-overview.md',
           _guide('Icy overview', '## Icy\nIcy text'))

    db = tmp_path / 'corpus.sqlite'
    report = tmp_path / 'informe.md'
    first = corpus.import_corpus(sources, db, report)
    assert first['guides'] == 7
    assert first['new'] == first['sections'] > 0
    assert first['changed'] == first['removed'] == 0
    assert report.exists()
    assert 'Informe del corpus' in report.read_text(encoding='utf-8')

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    duplicate = conn.execute(
        'SELECT section_id FROM sections WHERE duplicate_of IS NOT NULL').fetchone()
    assert duplicate is not None
    superseded = conn.execute(
        "SELECT superseded_by FROM guides WHERE guide_key = "
        "'icy-veins/clases/hunter/beast-mastery-hunter-leveling'").fetchone()
    assert superseded['superseded_by'] == (
        'wowhead/classes/hunter/beast-mastery/dps-leveling-tips')
    found = conn.execute(
        "SELECT section_id FROM sections_fts WHERE sections_fts MATCH 'dragon'").fetchone()
    assert found is not None
    conn.close()

    second = corpus.import_corpus(sources, db, report)
    assert (second['new'], second['changed'], second['removed']) == (0, 0, 0)

    changed_file = sources / 'wowhead/classes/hunter/beast-mastery/overview-pve-dps.md'
    changed_file.write_text(
        _guide('Beast Mastery', 'Intro dragon cambiado\n## Uno\n' + long_text),
        encoding='utf-8')
    removed_file = sources / 'wowhead/classes/hunter/leveling-guide.md'
    removed_file.unlink()
    third = corpus.import_corpus(sources, db, report)
    assert third['changed'] >= 1
    assert third['removed'] >= 1
