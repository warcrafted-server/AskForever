#!/usr/bin/env python3
"""Importa las guías descargadas a un corpus SQLite privado y genera un informe."""

from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES = REPO_ROOT / '.agents' / 'plans' / 'guia' / 'fuentes'
DEFAULT_DB = REPO_ROOT / '.agents' / 'corpus' / 'corpus.sqlite'
DEFAULT_REPORT = REPO_ROOT / '.agents' / 'corpus' / 'informe.md'

SOURCES = ('wowhead', 'icy-veins')
CLASSES = ('warrior', 'paladin', 'hunter', 'rogue', 'priest',
           'shaman', 'mage', 'warlock', 'druid')
KNOWN_SPECS = {
    'warrior': {'arms', 'fury', 'protection'},
    'paladin': {'holy', 'protection', 'retribution'},
    'hunter': {'beast-mastery', 'marksmanship', 'survival'},
    'rogue': {'assassination', 'combat', 'subtlety'},
    'priest': {'discipline', 'holy', 'shadow'},
    'shaman': {'elemental', 'enhancement', 'restoration'},
    'mage': {'arcane', 'fire', 'frost'},
    'warlock': {'affliction', 'demonology', 'destruction'},
    'druid': {'balance', 'feral', 'restoration'},
}
ENTITY_TYPES = ('quest', 'npc', 'item', 'spell', 'zone', 'object', 'faction')
HEADING_RE = re.compile(r'^(#{2,4})\s+(.+?)\s*#*\s*$')
ENTITY_RE = re.compile(
    r'\[([^\]]+)\]\(https?://(?:www\.)?wowhead\.com/forever/'
    r'(quest|npc|item|spell|zone|object|faction)=(\d+)[^)]*\)',
    re.IGNORECASE)
WAY_RE = re.compile(
    r'/way\s+(?:#\d+\s+)?(-?\d+(?:[.,]\d+)?)\s*(?:,\s*|\s+)'
    r'(-?\d+(?:[.,]\d+)?)')
MD_LINK_RE = re.compile(r'!?\[([^\]]*)\]\([^)]*\)')
MD_REF_LINK_RE = re.compile(r'\[([^\]]+)\]\[[^\]]*\]')


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode('utf-8')).hexdigest()


def _read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8-sig', errors='replace')


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Lee el bloque YAML sencillo del principio, tolerando valores con o sin comillas."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        return {}, text
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == '---':
            end = index
            break
    if end is None:
        return {}, text
    data: dict[str, str] = {}
    for line in lines[1:end]:
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        key = key.strip().lower()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            data[key] = value
    return data, '\n'.join(lines[end + 1:])


def normalize_text(text: str) -> str:
    """Quita enlaces, marcas Markdown y diferencias de espacios para comparar secciones."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = MD_LINK_RE.sub(r'\1', text)
    text = MD_REF_LINK_RE.sub(r'\1', text)
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'^[ \t]*[-+*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[ \t]*#{1,6}\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'[#*_`~>|]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()


def extract_entities(text: str) -> list[tuple[str, int, str]]:
    """Extrae enlaces de entidades de Wowhead, sin repetir el mismo tipo e id."""
    found: list[tuple[str, int, str]] = []
    seen: set[tuple[str, int]] = set()
    for match in ENTITY_RE.finditer(text):
        name = match.group(1).strip()
        kind = match.group(2).lower()
        entity_id = int(match.group(3))
        key = (kind, entity_id)
        if key not in seen:
            seen.add(key)
            found.append((kind, entity_id, name))
    return found


def extract_coords(text: str) -> list[tuple[str, float, float]]:
    """Extrae /way en formato simple y con número de punto opcional."""
    found = []
    for match in WAY_RE.finditer(text):
        raw = match.group(0)
        x = float(match.group(1).replace(',', '.'))
        y = float(match.group(2).replace(',', '.'))
        found.append((raw, x, y))
    return found


def _iter_sections(guide_key: str, body: str):
    """Devuelve introducción y secciones; los #### quedan dentro de su padre."""
    lines = body.splitlines()
    intro: list[str] = []
    current: Optional[dict] = None
    parent_two: Optional[str] = None
    counts: dict[str, int] = {}
    result: list[dict] = []

    def flush() -> None:
        nonlocal current, result
        if current is None:
            return
        text = '\n'.join(current['lines']).strip('\n')
        path = current['heading_path']
        count = counts.get(path, 0) + 1
        counts[path] = count
        suffix = '' if count == 1 else f'~{count}'
        section_id = f"{current['guide_key']}#{path}{suffix}" if path else f"{current['guide_key']}#intro"
        result.append({
            'section_id': section_id,
            'guide_key': current['guide_key'],
            'ord': len(result),
            'level': current['level'],
            'heading': current['heading'],
            'heading_path': path,
            'text': text,
            'chars': len(text),
            'hash': _sha1(text),
            'norm_hash': _sha1(normalize_text(text)),
            'duplicate_of': None,
        })
        current = None

    for line in lines:
        match = HEADING_RE.match(line)
        if match:
            level = len(match.group(1))
            heading = match.group(2).strip()
            if level <= 3:
                flush()
                if level == 2:
                    parent_two = heading
                    path = heading
                else:
                    path = f'{parent_two} > {heading}' if parent_two else heading
                current = {
                    'guide_key': guide_key,
                    'level': level,
                    'heading': heading,
                    'heading_path': path,
                    'lines': [line],
                }
            else:
                if current is not None:
                    current['lines'].append(line)
                else:
                    intro.append(line)
            continue
        if current is not None:
            current['lines'].append(line)
        else:
            intro.append(line)
    flush()

    intro_text = '\n'.join(intro).strip('\n')
    if intro_text:
        result.insert(0, {
            'section_id': f'{guide_key}#intro',
            'guide_key': guide_key,
            'ord': 0,
            'level': 0,
            'heading': '',
            'heading_path': '',
            'text': intro_text,
            'chars': len(intro_text),
            'hash': _sha1(intro_text),
            'norm_hash': _sha1(normalize_text(intro_text)),
            'duplicate_of': None,
        })
    for index, section in enumerate(result):
        section['ord'] = index
    return result


def split_sections(guide_key: str, body: str) -> list[dict]:
    """Divide un Markdown y rellena los identificadores estables."""
    return _iter_sections(guide_key, body)


def _stem(rel_path: str) -> str:
    name = rel_path.replace('\\', '/').rsplit('/', 1)[-1]
    return name[:-3] if name.lower().endswith('.md') else name


def _norm_dungeon(slug: str) -> str:
    slug = slug.lower()
    if slug.startswith('the-'):
        slug = slug[4:]
    if slug == 'razerfen-kraul':
        slug = 'razorfen-kraul'
    return slug


def _class_in_slug(slug: str) -> Optional[str]:
    for name in CLASSES:
        if re.search(rf'(?<![a-z]){name}(?![a-z])', slug):
            return name
    return None


def _spec_aspect(stem: str) -> str:
    if stem.startswith('overview-pve-'):
        return 'overview'
    if stem.startswith('rotation-cooldowns-'):
        return 'rotation'
    if stem.startswith('stat-priority-'):
        return 'stats'
    if stem.startswith('talent-builds-'):
        return 'talents'
    if stem.startswith('bis-gear'):
        return 'bis'
    if stem.startswith('enchants-consumables-'):
        return 'enchants'
    if 'leveling' in stem:
        return 'leveling'
    if 'abilities' in stem:
        return 'abilities'
    if stem.startswith('level-20-'):
        return 'level20'
    if stem.startswith('level-30-'):
        return 'level30'
    return stem


def _icy_spec(stem: str, specs: Iterable[str]) -> Optional[str]:
    for spec in sorted(specs, key=len, reverse=True):
        if stem == spec or stem.startswith(spec + '-'):
            return spec
    return None


# Cada web nombra distinto el mismo tema: se unifican aquí para detectar lo sustituido.
TOPIC_ALIASES = {
    'general:camping-overview-unlock-rewards': 'general:camping',
    'general:cozy-sleeping-bag-locations-rewards': 'general:sleeping-bag',
    'general:legacy-system-overview-rewards': 'general:legacy-system',
    'general:pvp-overview-ranking-rewards': 'general:pvp',
    'general:pvp-overview': 'general:pvp',
    'general:pvp-rank-system': 'general:pvp',
    'general:dungeons-overview-locations-details': 'general:dungeons-overview',
    'general:content-release-roadmap': 'general:roadmap',
    'general:zones-maps-locations-rewards': 'general:zones-and-maps',
    'general:pre-order-packs-rewards': 'general:wow-forever-pre-orders',
    'dungeon:_all:every-dungeon-quest-location': 'dungeon:_all:quests',
    'profession:professions-overview:overview': 'profession:_all:overview',
    'profession:professions:overview': 'profession:_all:overview',
    'tierlist:pve-tier-list-dps-specs': 'tierlist:dps-pve-rankings',
    'tierlist:pve-tier-list-healer-specs': 'tierlist:healer-pve-rankings',
    'tierlist:pve-tier-list-tank-specs': 'tierlist:tank-pve-rankings',
}
TOPIC_ALIAS_PATTERNS = (
    (re.compile(r'^dungeon:[^:]+:quests$'), 'dungeon:_all:quests'),
)


def canonical_topic(topic: str) -> str:
    topic = TOPIC_ALIASES.get(topic, topic)
    for pattern, target in TOPIC_ALIAS_PATTERNS:
        if pattern.match(topic):
            return target
    return topic


def topic_key(source: str, rel_path: str,
              spec_dirs: Optional[dict[str, Iterable[str]]] = None) -> str:
    """Clave temática canónica (igual en las dos fuentes para el mismo tema)."""
    return canonical_topic(_raw_topic_key(source, rel_path, spec_dirs))


def _raw_topic_key(source: str, rel_path: str,
                   spec_dirs: Optional[dict[str, Iterable[str]]] = None) -> str:
    """Calcula la clave temática a partir de la ruta relativa de la fuente."""
    source = source.lower()
    rel = str(rel_path).replace('\\', '/').lstrip('./')
    parts = [part for part in rel.split('/') if part]
    if source == 'wowhead' and parts and parts[0] == 'wowhead':
        parts = parts[1:]
    if source == 'icy-veins' and parts and parts[0] in ('guides', 'icy-veins'):
        parts = parts[1:]
    stem = _stem(rel)
    slug = stem.lower()

    if source == 'wowhead':
        if parts and parts[0] == 'classes':
            if len(parts) >= 4:
                if parts[1] == 'tier-lists':
                    return f'tierlist:{stem}'
                return f'class:{parts[1].lower()}:{parts[2].lower()}:{_spec_aspect(stem)}'
            if len(parts) == 3:
                if parts[1] == 'tier-lists':
                    return f'tierlist:{stem}'
                return f'class:{parts[1].lower()}:general:{stem}'
            return f'general:{stem}'
        if len(parts) == 1 and slug.endswith('-dungeon-overview-location-rewards'):
            return f'dungeon:{_norm_dungeon(slug[:-len("-dungeon-overview-location-rewards")])}'
        if parts and parts[0] == 'dungeons':
            return f'dungeon:_all:{stem}'
        if (parts and parts[0] == 'raids') or 'raid' in slug:
            return f'raid:{stem}'
        if parts and parts[0] == 'professions':
            if len(parts) >= 3:
                if slug.startswith('overview'):
                    return f'profession:{parts[1].lower()}:overview'
                return f'profession:{parts[1].lower()}:{stem}'
            if len(parts) == 2:
                overview = re.match(r'^(.+)-overview-trainer-locations-recipes$', stem)
                if overview:
                    return f'profession:{overview.group(1).lower()}:overview'
                return f'profession:_all:{stem}'
        if parts and parts[0] == 'reputation':
            return f'reputation:{stem}'
        if parts and parts[0] == 'collections':
            return f'collection:{stem}'
        if parts and parts[0] == 'ui':
            return f'ui:{stem}'
        if slug.endswith('-race-overview'):
            return f'race:{slug[:-len("-race-overview")]}'
        class_name = _class_in_slug(slug[:-len(re.search(r'-\d+$', slug).group(0))] if re.search(r'-\d+$', slug) else slug)
        if class_name:
            clean = re.sub(r'-\d+$', '', slug)
            return f'class:{class_name}:extra:{clean}'
        return f'general:{stem}'

    if source == 'icy-veins':
        if parts and parts[0] == 'clases' and len(parts) >= 3:
            class_name = parts[1].lower()
            specs = (spec_dirs or {}).get(class_name) or KNOWN_SPECS.get(class_name, ())
            spec = _icy_spec(stem, specs)
            if spec:
                aspect = stem
                if stem.endswith('-leveling'):
                    aspect = 'leveling'
                elif stem.endswith('-pve-guide'):
                    aspect = 'overview'
                elif stem.endswith('-spec-builds-talents'):
                    aspect = 'talents'
                elif stem.endswith('-stat-priority'):
                    aspect = 'stats'
                return f'class:{class_name}:{spec}:{aspect}'
            return f'class:{class_name}:general:{stem}'
        if parts and parts[0] == 'mazmorras' and len(parts) >= 2:
            dungeon = stem
            if dungeon.endswith('-guide'):
                return f'dungeon:{_norm_dungeon(dungeon[:-6])}'
            if dungeon.endswith('-quests'):
                return f'dungeon:{_norm_dungeon(dungeon[:-7])}:quests'
        if parts and parts[0] == 'profesiones':
            return f'profession:{slug}:overview'
        if parts and parts[0] == 'razas':
            race = stem
            if race.endswith('-race-guide'):
                race = race[:-11]
            return f'race:{race}'
        if parts and parts[0] == 'tier-lists':
            return f'tierlist:{stem}'
        if parts and parts[0] == 'general':
            return f'general:{stem}'
        return f'general:{stem}'

    return f'general:{stem}'


def _discover_spec_dirs(wowhead_root: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    classes_root = wowhead_root / 'classes'
    if not classes_root.is_dir():
        return result
    for class_dir in sorted(classes_root.iterdir()):
        if not class_dir.is_dir() or class_dir.name.lower() == 'tier-lists':
            continue
        result[class_dir.name.lower()] = {
            child.name.lower() for child in class_dir.iterdir() if child.is_dir()
        }
    return result


def _discover_files(sources_root: Path):
    wowhead_root = sources_root / 'wowhead'
    icy_root = sources_root / 'icy-veins' / 'guides'
    for path in sorted(wowhead_root.rglob('*.md')):
        if path.name.lower() == 'readme.md':
            continue
        yield 'wowhead', path.relative_to(wowhead_root).as_posix(), path
    for path in sorted(icy_root.rglob('*.md')):
        yield 'icy-veins', path.relative_to(icy_root).as_posix(), path


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS guides (
            guide_key TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            path TEXT NOT NULL,
            url TEXT,
            title TEXT,
            author TEXT,
            category TEXT,
            class TEXT,
            updated TEXT,
            patch TEXT,
            topic TEXT,
            superseded_by TEXT,
            hash TEXT
        );
        CREATE TABLE IF NOT EXISTS sections (
            section_id TEXT PRIMARY KEY,
            guide_key TEXT NOT NULL,
            ord INTEGER NOT NULL,
            level INTEGER NOT NULL,
            heading TEXT,
            heading_path TEXT,
            text TEXT NOT NULL,
            chars INTEGER NOT NULL,
            hash TEXT NOT NULL,
            norm_hash TEXT NOT NULL,
            duplicate_of TEXT
        );
        CREATE TABLE IF NOT EXISTS entities (
            section_id TEXT NOT NULL,
            type TEXT NOT NULL,
            id INTEGER NOT NULL,
            name TEXT
        );
        CREATE TABLE IF NOT EXISTS coords (
            section_id TEXT NOT NULL,
            raw TEXT NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
            section_id UNINDEXED, heading_path, text
        );
        CREATE TABLE IF NOT EXISTS runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT NOT NULL,
            guides INTEGER NOT NULL,
            sections INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS changes (
            run_id INTEGER NOT NULL,
            section_id TEXT NOT NULL,
            change TEXT NOT NULL,
            guide_key TEXT NOT NULL
        );
    """)


def _old_sections(conn: sqlite3.Connection) -> dict[str, tuple[str, str]]:
    try:
        rows = conn.execute(
            'SELECT section_id, hash, guide_key FROM sections').fetchall()
    except sqlite3.Error:
        return {}
    return {row[0]: (row[1], row[2]) for row in rows}


def _dedupe_sections(sections: list[dict]) -> None:
    order = {'wowhead': 0, 'icy-veins': 1}
    sections.sort(key=lambda s: (
        order.get(s['guide_key'].split('/', 1)[0], 9),
        s['guide_key'], s['ord']))
    seen: dict[str, str] = {}
    for section in sections:
        if section['chars'] < 200:
            continue
        previous = seen.get(section['norm_hash'])
        if previous:
            section['duplicate_of'] = previous
        else:
            seen[section['norm_hash']] = section['section_id']


def _set_superseded(guides: list[dict]) -> None:
    wowhead_topics: dict[str, str] = {}
    for guide in sorted(guides, key=lambda g: g['guide_key']):
        if guide['source'] == 'wowhead':
            wowhead_topics.setdefault(guide['topic'], guide['guide_key'])
    for guide in guides:
        if guide['source'] == 'icy-veins':
            guide['superseded_by'] = wowhead_topics.get(guide['topic'])


def import_corpus(sources_root: Path, db_path: Path,
                  report_path: Path) -> dict[str, int]:
    """Reconstruye las tablas de contenido, conserva runs/changes y escribe el informe."""
    sources_root = Path(sources_root)
    db_path = Path(db_path)
    report_path = Path(report_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    spec_dirs = _discover_spec_dirs(sources_root / 'wowhead')
    guides: list[dict] = []
    sections: list[dict] = []

    for source, rel_path, path in _discover_files(sources_root):
        raw = _read_text(path)
        front, body = parse_front_matter(raw)
        guide_key = f'{source}/{rel_path[:-3]}'
        topic = topic_key(source, rel_path, spec_dirs)
        guide = {
            'guide_key': guide_key,
            'source': source,
            'path': rel_path,
            'url': front.get('url'),
            'title': front.get('title'),
            'author': front.get('author'),
            'category': front.get('category') or front.get('section'),
            'class': front.get('class'),
            'updated': front.get('updated') or front.get('modified'),
            'patch': front.get('patch'),
            'topic': topic,
            'superseded_by': None,
            'hash': _sha1(raw),
        }
        guides.append(guide)
        for section in split_sections(guide_key, body):
            sections.append(section)

    _dedupe_sections(sections)
    _set_superseded(guides)

    conn = sqlite3.connect(db_path)
    run_id = 0
    try:
        _schema(conn)
        old = _old_sections(conn)
        new_by_id = {section['section_id']: section for section in sections}
        changes: list[tuple[str, str, str]] = []
        for section_id, section in new_by_id.items():
            previous = old.get(section_id)
            if previous is None:
                changes.append((section_id, 'new', section['guide_key']))
            elif previous[0] != section['hash']:
                changes.append((section_id, 'changed', section['guide_key']))
        for section_id, (_hash, guide_key) in old.items():
            if section_id not in new_by_id:
                changes.append((section_id, 'removed', guide_key))

        conn.execute('BEGIN')
        conn.execute('DELETE FROM entities')
        conn.execute('DELETE FROM coords')
        conn.execute('DELETE FROM sections_fts')
        conn.execute('DELETE FROM sections')
        conn.execute('DELETE FROM guides')

        conn.executemany(
            'INSERT INTO guides (guide_key, source, path, url, title, author, '
            'category, class, updated, patch, topic, superseded_by, hash) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [(g['guide_key'], g['source'], g['path'], g['url'], g['title'],
              g['author'], g['category'], g['class'], g['updated'], g['patch'],
              g['topic'], g['superseded_by'], g['hash']) for g in guides])
        conn.executemany(
            'INSERT INTO sections (section_id, guide_key, ord, level, heading, '
            'heading_path, text, chars, hash, norm_hash, duplicate_of) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [(s['section_id'], s['guide_key'], s['ord'], s['level'],
              s['heading'], s['heading_path'], s['text'], s['chars'],
              s['hash'], s['norm_hash'], s['duplicate_of']) for s in sections])
        conn.executemany(
            'INSERT INTO sections_fts (section_id, heading_path, text) VALUES (?, ?, ?)',
            [(s['section_id'], s['heading_path'], s['text']) for s in sections])

        entity_rows = []
        coord_rows = []
        for section in sections:
            for kind, entity_id, name in extract_entities(section['text']):
                entity_rows.append((section['section_id'], kind, entity_id, name))
            for raw, x, y in extract_coords(section['text']):
                coord_rows.append((section['section_id'], raw, x, y))
        conn.executemany(
            'INSERT INTO entities (section_id, type, id, name) VALUES (?, ?, ?, ?)',
            entity_rows)
        conn.executemany(
            'INSERT INTO coords (section_id, raw, x, y) VALUES (?, ?, ?, ?)',
            coord_rows)

        at = datetime.now(timezone.utc).isoformat(timespec='seconds')
        cursor = conn.execute(
            'INSERT INTO runs (at, guides, sections) VALUES (?, ?, ?)',
            (at, len(guides), len(sections)))
        run_id = cursor.lastrowid
        conn.executemany(
            'INSERT INTO changes (run_id, section_id, change, guide_key) '
            'VALUES (?, ?, ?, ?)',
            [(run_id, section_id, change, guide_key)
             for section_id, change, guide_key in changes])
        conn.commit()
        summary = {
            'guides': len(guides),
            'sections': len(sections),
            'new': sum(1 for change in changes if change[1] == 'new'),
            'changed': sum(1 for change in changes if change[1] == 'changed'),
            'removed': sum(1 for change in changes if change[1] == 'removed'),
        }
        _write_report(conn, report_path, summary, run_id)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return summary


def _write_report(conn: sqlite3.Connection, path: Path,
                  summary: dict[str, int], run_id: int) -> None:
    lines = ['# Informe del corpus de guías', '',
             f'Generado: {datetime.now(timezone.utc).isoformat(timespec="seconds")}', '',
             '## Totales', '']
    for source in SOURCES:
        guides = conn.execute(
            'SELECT COUNT(*) FROM guides WHERE source = ?', (source,)).fetchone()[0]
        sections = conn.execute(
            'SELECT COUNT(*), COALESCE(SUM(s.chars), 0) FROM sections s '
            'JOIN guides g ON g.guide_key = s.guide_key WHERE g.source = ?',
            (source,)).fetchone()
        lines.append(f'- **{source}**: {guides} guías, {sections[0]} secciones, '
                     f'{sections[1]} caracteres.')
        entity_rows = conn.execute(
            'SELECT e.type, COUNT(*) FROM entities e '
            'JOIN sections s ON s.section_id = e.section_id '
            'JOIN guides g ON g.guide_key = s.guide_key '
            'WHERE g.source = ? GROUP BY e.type ORDER BY e.type', (source,)).fetchall()
        if entity_rows:
            lines.append('  - Entidades: ' + ', '.join(
                f'{kind}: {count}' for kind, count in entity_rows) + '.')

    lines.extend(['', '## Guías por familia temática', ''])
    families = conn.execute(
        "SELECT CASE WHEN instr(topic, ':') > 0 THEN substr(topic, 1, instr(topic, ':') - 1) "
        "ELSE topic END AS family, COUNT(*) FROM guides GROUP BY family ORDER BY family"
    ).fetchall()
    for family, count in families:
        lines.append(f'- **{family}**: {count}')

    duplicate_count = conn.execute(
        'SELECT COUNT(*) FROM sections WHERE duplicate_of IS NOT NULL').fetchone()[0]
    lines.extend(['', '## Duplicados', '',
                  f'Secciones duplicadas: {duplicate_count}.', ''])
    groups = conn.execute(
        'SELECT duplicate_of, COUNT(*) AS n FROM sections '
        'WHERE duplicate_of IS NOT NULL GROUP BY duplicate_of '
        'ORDER BY n DESC, duplicate_of LIMIT 20').fetchall()
    if groups:
        lines.append('| Sección original | Duplicadas |')
        lines.append('| --- | ---: |')
        for original, count in groups:
            lines.append(f'| {original} | {count} |')
    else:
        lines.append('No hay grupos duplicados.')

    lines.extend(['', '## Guías de Icy Veins no sustituidas', ''])
    not_superseded = conn.execute(
        "SELECT guide_key, topic FROM guides WHERE source = 'icy-veins' "
        'AND superseded_by IS NULL ORDER BY guide_key').fetchall()
    for guide_key, topic in not_superseded:
        lines.append(f'- `{guide_key}` — {topic}')

    lines.extend(['', '## Temas presentes en las dos fuentes', ''])
    topics = conn.execute(
        "SELECT topic FROM guides WHERE source = 'wowhead' "
        'INTERSECT SELECT topic FROM guides WHERE source = \'icy-veins\' '
        'ORDER BY topic').fetchall()
    for (topic,) in topics:
        lines.append(f'- {topic}')

    lines.extend(['', '## Guías en general:', ''])
    general = conn.execute(
        "SELECT guide_key, topic FROM guides WHERE topic LIKE 'general:%' "
        'ORDER BY guide_key').fetchall()
    for guide_key, topic in general:
        lines.append(f'- `{guide_key}` — {topic}')

    lines.extend(['', f'## Cambios de la ejecución {run_id}', '',
                  f'Nuevas: {summary["new"]}; cambiadas: {summary["changed"]}; '
                  f'eliminadas: {summary["removed"]}.', ''])
    change_rows = conn.execute(
        'SELECT guide_key, change, COUNT(*) AS n FROM changes '
        'WHERE run_id = ? GROUP BY guide_key, change '
        'ORDER BY guide_key, change', (run_id,)).fetchall()
    for guide_key, change, count in change_rows:
        lines.append(f'- `{guide_key}` — {change}: {count}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description='Importa las guías descargadas a un corpus SQLite privado.')
    parser.add_argument('--sources', type=Path, default=DEFAULT_SOURCES)
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    summary = import_corpus(args.sources, args.db, args.report)
    print(f'Guías: {summary["guides"]} · Secciones: {summary["sections"]} · '
          f'Nuevas: {summary["new"]} · Cambiadas: {summary["changed"]} · '
          f'Eliminadas: {summary["removed"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
