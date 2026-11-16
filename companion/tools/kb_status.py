#!/usr/bin/env python3
"""Enlaza las fichas editoriales con el corpus privado y detecta fichas caducadas."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CARDS = BASE_DIR / 'askforever' / 'data' / 'guide'
DEFAULT_CORPUS = REPO_ROOT / '.agents' / 'corpus' / 'corpus.sqlite'
DEFAULT_REPORT = REPO_ROOT / '.agents' / 'corpus' / 'fichas.md'

SPACE_RE = re.compile(r'\s+')


def normalize_url(url: str) -> str:
    """Iguala http/https, mayúsculas del host, query, fragmento y barra final."""
    raw = str(url or '').strip()
    if not raw:
        return ''
    if '://' not in raw:
        raw = '//' + raw
    parts = urlsplit(raw)
    host = parts.netloc.lower()
    if host.startswith('www.'):
        host = host[4:]
    path = parts.path.rstrip('/')
    return f'{host}{path}'


def normalize_heading(value: str) -> str:
    return SPACE_RE.sub(' ', str(value or '').strip()).casefold()


def load_cards(cards_dir: Path) -> list[tuple[Path, dict]]:
    cards = []
    for path in sorted(Path(cards_dir).glob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and isinstance(data.get('sections'), list):
            cards.append((path, data))
    return cards


def _corpus(conn: sqlite3.Connection):
    guides = {}
    for row in conn.execute(
            'SELECT guide_key, source, url, topic, superseded_by, hash '
            'FROM guides ORDER BY guide_key'):
        item = {
            'guide_key': row[0], 'source': row[1], 'url': row[2],
            'topic': row[3], 'superseded_by': row[4], 'hash': row[5],
            'sections': [],
        }
        guides[row[0]] = item
    for row in conn.execute(
            'SELECT guide_key, heading, heading_path, hash, ord '
            'FROM sections ORDER BY guide_key, ord'):
        guide = guides.get(row[0])
        if guide is not None:
            guide['sections'].append({
                'heading': row[1], 'heading_path': row[2],
                'hash': row[3], 'ord': row[4],
            })
    by_url = {}
    for guide in sorted(guides.values(), key=lambda item: item['guide_key']):
        key = normalize_url(guide['url'])
        if key and key not in by_url:
            by_url[key] = guide
    return guides, by_url


def _match_section(guide: dict, heading: str) -> Optional[dict]:
    target = normalize_heading(heading)
    if not target:
        return None
    for section in guide['sections']:
        if normalize_heading(section['heading']) == target:
            return section
        path = str(section['heading_path'] or '')
        last = path.rsplit(' > ', 1)[-1]
        if normalize_heading(last) == target:
            return section
    return None


def _source_links(section: dict, guides: dict, by_url: dict):
    topics = set()
    hashes = set()
    missing = []
    superseded = []
    for source in section.get('sources') or []:
        if not isinstance(source, dict):
            continue
        url = source.get('url')
        if not isinstance(url, str) or not url.strip():
            continue
        guide = by_url.get(normalize_url(url))
        if guide is None:
            missing.append({
                'section_id': section.get('id', ''),
                'url': url,
                'ref': source.get('ref', ''),
            })
            continue
        topics.add(guide['topic'])
        ref = str(source.get('ref') or '')
        heading = ref.split(' › ', 1)[1].strip() if ' › ' in ref else ''
        matched = _match_section(guide, heading) if heading else None
        if matched is not None:
            hashes.add('section:' + matched['hash'])
        else:
            hashes.add('guide:' + guide['hash'])
        if guide['source'] == 'icy-veins' and guide.get('superseded_by'):
            superseded.append({
                'section_id': section.get('id', ''),
                'guide_key': guide['guide_key'],
                'superseded_by': guide['superseded_by'],
            })
    return topics, hashes, missing, superseded


def _topic_families(topics):
    result = {}
    for topic in topics:
        family = topic.split(':', 1)[0]
        result.setdefault(family, []).append(topic)
    return result


def run_status(cards_dir: Path, corpus_path: Path, report_path: Path,
               write: bool = False) -> dict:
    cards = load_cards(cards_dir)
    conn = sqlite3.connect(corpus_path)
    try:
        guides, by_url = _corpus(conn)
        all_links = []
        missing = []
        superseded = []
        stale = []
        for path, data in cards:
            for section in data.get('sections') or []:
                if not isinstance(section, dict):
                    continue
                links = _source_links(section, guides, by_url)
                topics, hashes, section_missing, section_superseded = links
                topics = sorted(topics)
                hashes = sorted(hashes)
                all_links.append((path, data, section, topics, hashes))
                missing.extend(section_missing)
                superseded.extend(section_superseded)
                stored = section.get('source_hashes')
                if isinstance(stored, list) and stored:
                    if set(stored) != set(hashes):
                        stale.append(section.get('id', ''))
        if write:
            for path, data, section, topics, hashes in all_links:
                section['topics'] = topics
                section['source_hashes'] = hashes
            for path, data in cards:
                _save_card(path, data)
    finally:
        conn.close()

    covered = {topic for _path, _data, _section, topics, _hashes in all_links
               for topic in topics}
    uncovered = []
    if 'guides' in locals():
        for guide in sorted(guides.values(), key=lambda item: item['guide_key']):
            if guide['source'] == 'wowhead' and not guide.get('superseded_by'):
                if guide['topic'] not in covered:
                    uncovered.append(guide['topic'])
    _write_report(report_path, cards, all_links, stale, superseded,
                  missing, uncovered)
    return {
        'cards': len(cards),
        'sections': len(all_links),
        'stale': len(stale),
        'superseded': len(superseded),
        'missing': len(missing),
        'uncovered': len(uncovered),
    }


def _save_card(path: Path, data: dict) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)


def _write_report(path: Path, cards, links, stale, superseded, missing,
                  uncovered) -> None:
    lines = ['# Estado de las fichas de la guía', '',
             '## Totales', '',
             f'- Fichas: {len(cards)}',
             f'- Secciones: {len(links)}',
             f'- Enlaces de fuente: {sum(len(item[4]) for item in links)}', '']
    lines.extend(['## Fichas caducadas', ''])
    if stale:
        for section_id in sorted(set(stale)):
            lines.append(f'- `{section_id}`')
    else:
        lines.append('Ninguna.')

    lines.extend(['', '## Fichas de Icy Veins sustituidas por Wowhead', ''])
    if superseded:
        seen = set()
        for item in superseded:
            key = (item['section_id'], item['guide_key'], item['superseded_by'])
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- `{item['section_id']}` — `{item['guide_key']}` "
                         f"sustituida por `{item['superseded_by']}`")
    else:
        lines.append('Ninguna.')

    lines.extend(['', '## Temas sin ficha', ''])
    families = _topic_families(sorted(set(uncovered)))
    if families:
        for family in sorted(families):
            topics = sorted(families[family])
            lines.append(f'### {family} ({len(topics)})')
            for topic in topics:
                lines.append(f'- {topic}')
    else:
        lines.append('Ninguno.')

    lines.extend(['', '## Fuentes no encontradas', ''])
    if missing:
        seen = set()
        for item in missing:
            key = (item['section_id'], item['url'], item['ref'])
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- `{item['section_id']}` — {item['url']}")
    else:
        lines.append('Ninguna.')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(lines) + '\n')


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description='Enlaza las fichas editoriales con el corpus privado.')
    parser.add_argument('--cards', type=Path, default=DEFAULT_CARDS)
    parser.add_argument('--corpus', type=Path, default=DEFAULT_CORPUS)
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    summary = run_status(args.cards, args.corpus, args.report, args.write)
    print(f"Fichas: {summary['cards']} · Secciones: {summary['sections']} · "
          f"Caducadas: {summary['stale']} · Sustituidas: {summary['superseded']} · "
          f"Sin fuente: {summary['missing']} · Temas sin ficha: {summary['uncovered']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
