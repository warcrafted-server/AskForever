#!/usr/bin/env python3
"""Actualiza los paquetes de clase y clasifica fichas caducadas."""

from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
CLASSES = ('warrior', 'paladin', 'hunter', 'rogue', 'priest', 'shaman',
           'mage', 'warlock', 'druid')
PACKS_A = ('overview', 'rotation', 'stats', 'talents', 'general')
PACKS_B = ('leveling', 'extra')
BUILD_RE = re.compile(r'\{build: ([^}]*)\}')
REPORT_STAMP_RE = re.compile(r'(?P<stamp>\d{4}-\d{2}-\d{2}-\d{4})')
ZERO_WIDTH = str.maketrans({char: ' ' for char in '\u200b\u200c\u200d\u2060\ufeff\u00a0'})


def _load_tool(name: str):
    path = Path(__file__).with_name(f'{name}.py')
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f'No se pudo cargar {path.name}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


kb_status = _load_tool('kb_status')
kb_pack = _load_tool('kb_pack')
kb_names = _load_tool('kb_names')
corpus_tool = _load_tool('corpus')


def normalize_pack_text(text: str) -> str:
    """Normaliza variaciones tipográficas y de URL del calculador de talentos."""
    url_re = re.compile(
        r'(?:https?://(?:www\.)?wowhead\.com/forever/)?'
        r'talent-calc/[^\s)<>]+')
    version_re = re.compile(
        r'((?:^|/)talent-calc/[a-z-]+)/v(?:2|[a-z]+)(?=[\d-])')

    def normalize_url(match: re.Match) -> str:
        url = match.group(0)
        url = version_re.sub(r'\1/v<version>', url)
        return url.split('_t0', 1)[0]

    text = url_re.sub(normalize_url, text)
    text = text.translate(ZERO_WIDTH)
    return re.sub(r'\s+', ' ', text).strip()


def _pack_sections(text: str) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    guide_key = None
    heading = None
    body: list[str] = []

    def save() -> None:
        if guide_key is not None and heading is not None:
            result[(guide_key, heading)] = '\n'.join(body).strip()

    for line in text.splitlines():
        if line.startswith('# ') and ' · ' in line:
            save()
            guide_key = None
            heading = None
            body = []
        elif line.startswith('- guía: `') and line.endswith('`'):
            guide_key = line[len('- guía: `'):-1]
        elif line.startswith('## › '):
            save()
            heading = line[len('## › '):]
            body = []
        elif heading is not None:
            body.append(line)
    save()
    return result


def _resolve_card_sources(section: dict, guides: dict, by_url: dict
                          ) -> list[tuple[str, str]]:
    resolved = []
    for source in section.get('sources') or []:
        if not isinstance(source, dict):
            continue
        url = source.get('url')
        if not isinstance(url, str) or not url.strip():
            continue
        guide = by_url.get(kb_status.normalize_url(url))
        if guide is None:
            continue
        ref = str(source.get('ref') or '')
        heading = ref.split(' › ', 1)[1].strip() if ' › ' in ref else ''
        matched = kb_status._match_section(guide, heading) if heading else None
        if matched is not None:
            resolved.append((guide['guide_key'], matched['heading_path']))
        else:
            resolved.extend((guide['guide_key'], item['heading_path'])
                            for item in guide['sections'])
    return resolved


def classify_cards(cards_dir: Path, stale_ids: set[str], corpus_path: Path,
                   old_packs: dict[str, str], new_packs: dict[str, str]
                   ) -> dict[str, dict[str, list]]:
    """Clasifica las fichas caducadas por clase comparando sus fuentes en los paquetes."""
    sections_by_pack = {
        'old': {name: _pack_sections(text) for name, text in old_packs.items()},
        'new': {name: _pack_sections(text) for name, text in new_packs.items()},
    }
    result = {cls: {'cosmetic': [], 'real': []} for cls in CLASSES}
    result['other'] = {'cosmetic': [], 'real': []}
    conn = sqlite3.connect(corpus_path)
    try:
        guides, by_url = kb_status._corpus(conn)
    finally:
        conn.close()

    for path, data in kb_status.load_cards(cards_dir):
        match = re.fullmatch(r'04-clase-([a-z-]+)\.json', path.name)
        class_name = match.group(1) if match and match.group(1) in result else None
        for card in data.get('sections') or []:
            if not isinstance(card, dict) or card.get('id') not in stale_ids:
                continue
            cosmetic = class_name is not None
            sources = _resolve_card_sources(card, guides, by_url)
            if not sources:
                cosmetic = False
            for guide_key, heading in sources:
                old_text = next((sections_by_pack['old'].get(f'{class_name}-{pack}', {}).get(
                    (guide_key, heading)) for pack in ('a', 'b')
                    if (guide_key, heading) in sections_by_pack['old'].get(
                        f'{class_name}-{pack}', {})), None)
                new_text = next((sections_by_pack['new'].get(f'{class_name}-{pack}', {}).get(
                    (guide_key, heading)) for pack in ('a', 'b')
                    if (guide_key, heading) in sections_by_pack['new'].get(
                        f'{class_name}-{pack}', {})), None)
                if old_text is None or new_text is None or (
                        normalize_pack_text(old_text) != normalize_pack_text(new_text)):
                    cosmetic = False
                    break
            result[class_name or 'other'][
                'cosmetic' if cosmetic else 'real'].append(card)
    return result


def _stale_ids(cards_dir: Path, corpus_path: Path) -> set[str]:
    stale = set()
    conn = sqlite3.connect(corpus_path)
    try:
        guides, by_url = kb_status._corpus(conn)
        for _path, data in kb_status.load_cards(cards_dir):
            for section in data.get('sections') or []:
                if not isinstance(section, dict):
                    continue
                _topics, hashes, _missing, _superseded = kb_status._source_links(
                    section, guides, by_url)
                stored = section.get('source_hashes')
                if isinstance(stored, list) and stored and set(stored) != hashes:
                    stale.add(section.get('id', ''))
    finally:
        conn.close()
    return stale


def _builds_by_section(text: str) -> dict[tuple[str, str], list[str]]:
    result: dict[tuple[str, str], list[str]] = {}
    guide_key = None
    heading = None
    for line in text.splitlines():
        if line.startswith('# ') and ' · ' in line:
            guide_key = None
            heading = None
        elif line.startswith('- guía: `') and line.endswith('`'):
            guide_key = line[len('- guía: `'):-1]
        elif line.startswith('## › '):
            heading = line[len('## › '):]
        elif guide_key is not None and heading is not None:
            for annotation in BUILD_RE.findall(line):
                values = result.setdefault((guide_key, heading), [])
                if annotation not in values:
                    values.append(annotation)
    return result


def _build_changes(old_packs: dict[str, str], new_packs: dict[str, str]
                   ) -> dict[str, dict[str, list[dict]]]:
    result = {cls: {'new': [], 'removed': []} for cls in CLASSES}
    for cls in CLASSES:
        for pack in ('a', 'b'):
            old = _builds_by_section(old_packs.get(f'{cls}-{pack}', ''))
            new = _builds_by_section(new_packs.get(f'{cls}-{pack}', ''))
            for key in sorted(set(old) | set(new)):
                old_builds, new_builds = old.get(key, []), new.get(key, [])
                for build in new_builds:
                    if build not in old_builds:
                        result[cls]['new'].append({
                            'guide_key': key[0], 'heading_path': key[1],
                            'build': build, 'pack': pack,
                        })
                for build in old_builds:
                    if build not in new_builds:
                        result[cls]['removed'].append({
                            'guide_key': key[0], 'heading_path': key[1],
                            'build': build, 'pack': pack,
                        })
    return result


def _report_stamp(path: Path) -> str:
    match = REPORT_STAMP_RE.search(path.name)
    return match.group('stamp') if match else datetime.now().strftime('%Y-%m-%d-%H%M')


def _load_registry(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _select_report(sources: Path, explicit: Optional[Path], registry: dict,
                   force: bool) -> Optional[Path]:
    if explicit is not None:
        return explicit
    reports = sorted((path for path in (sources / 'cambios').glob('*.md')
                      if not path.name.endswith('-resumen.md')),
                     key=lambda path: path.name, reverse=True)
    for path in reports:
        if force or path.name not in registry:
            return path
    return None


def _diff_text(old: str, new: str, old_name: str, new_name: str) -> str:
    old_lines = [line for line in old.splitlines(keepends=True)
                 if not line.startswith('- actualizada')]
    new_lines = [line for line in new.splitlines(keepends=True)
                 if not line.startswith('- actualizada')]
    return ''.join(difflib.unified_diff(old_lines, new_lines,
                                       fromfile=old_name, tofile=new_name))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='')


def _relative_path(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        # Fuera del repo (p. ej. temporales en otra unidad, como en el runner de CI): ruta absoluta.
        return Path(path).resolve().as_posix()


def _class_patterns(class_name: str, pack: str) -> list[str]:
    if pack == 'a':
        return [f'class:{class_name}:%:{aspect}' for aspect in PACKS_A[:-1]] + [
            f'class:{class_name}:general:%']
    return [f'class:{class_name}:%:leveling', f'class:{class_name}:extra:%']


def _render_report(path: Path, report: Path, corpus_counts: dict,
                   classified: dict, builds: dict, changed_without_stale: list[str],
                   uncovered: int) -> None:
    lines = ['# Actualización diaria de las guías', '',
             f'Informe usado: `{report}`',
             f'Corpus: {corpus_counts["guides"]} guías, '
             f'{corpus_counts["sections"]} secciones.', '',
             '## Fichas cosméticas actualizadas', '']
    for cls in CLASSES:
        cards = classified[cls]['cosmetic']
        if cards:
            lines.append(f'- **{cls}**: ' + ', '.join(
                f'`{card.get("id", "")}`' for card in cards))
    lines.extend(['', '## Fichas caducadas con cambios reales', ''])
    for cls in CLASSES:
        cards = classified[cls]['real']
        if cards:
            lines.append(f'- **{cls}**: ' + ', '.join(
                f'`{card.get("id", "")}`' for card in cards))
    lines.extend(['', '## Builds nuevas o modificadas', ''])
    for cls in CLASSES:
        if builds[cls]['new']:
            lines.append(f'- **{cls}**: ' + '; '.join(
                f'`{item["guide_key"]}` › {item["heading_path"]}: '
                f'{item["build"]}' for item in builds[cls]['new']))
    lines.extend(['', '## Builds eliminadas', ''])
    for cls in CLASSES:
        if builds[cls]['removed']:
            lines.append(f'- **{cls}**: ' + '; '.join(
                f'`{item["guide_key"]}` › {item["heading_path"]}: '
                f'{item["build"]}' for item in builds[cls]['removed']))
    lines.extend(['', '## Paquetes cambiados sin fichas caducadas', ''])
    lines.extend(f'- {cls}' for cls in changed_without_stale)
    lines.extend(['', f'Temas sin ficha: {uncovered}.', ''])
    _write_text(path, '\n'.join(lines))


def update(report: Optional[Path] = None, force: bool = False,
           dry_run: bool = False, sources: Optional[Path] = None,
           corpus: Optional[Path] = None, cards: Optional[Path] = None,
           packs: Optional[Path] = None, wowdb: Optional[Path] = None,
           out: Optional[Path] = None, registry: Optional[Path] = None) -> int:
    def root_path(value: Optional[Path], default: Path) -> Path:
        result = Path(value) if value is not None else default
        return result if result.is_absolute() else REPO_ROOT / result

    sources_path = root_path(sources, Path('.agents/plans/guia/fuentes'))
    corpus_path = root_path(corpus, Path('.agents/corpus/corpus.sqlite'))
    cards_path = root_path(cards, Path('companion/askforever/data/guide'))
    packs_path = root_path(packs, Path('.agents/corpus/packs'))
    wowdb_path = root_path(wowdb, REPO_ROOT.parent / 'wowdata/datos/wow.sqlite')
    out_path = root_path(out, Path('.agents/plans/conocimiento/actualizaciones'))
    registry_path = root_path(registry, Path('.agents/corpus/actualizaciones.json'))
    registry_data = _load_registry(registry_path)
    explicit_report = root_path(report, Path()) if report is not None else None
    report_path = _select_report(sources_path, explicit_report, registry_data, force)
    if report_path is None or not report_path.is_file():
        print('Sin informes nuevos')
        return 0

    stamp = _report_stamp(report_path)
    output_dir = out_path / (stamp + ('-prueba' if dry_run else ''))
    output_dir.mkdir(parents=True, exist_ok=True)

    if not dry_run:
        backup = corpus_path.with_suffix(corpus_path.suffix + '.bak')
        had_corpus = corpus_path.is_file()
        if had_corpus:
            shutil.copy2(corpus_path, backup)
        try:
            status = corpus_tool.main([
                '--sources', str(sources_path), '--db', str(corpus_path),
                '--report', str(corpus_path.parent / 'informe.md'),
            ])
            if status:
                raise RuntimeError(f'La importación terminó con estado {status}')
        except Exception as exc:
            if had_corpus and backup.exists():
                shutil.copy2(backup, corpus_path)
            elif not had_corpus:
                corpus_path.unlink(missing_ok=True)
            print(f'No se pudo importar el corpus: {exc}', file=sys.stderr)
            return 1

    names = kb_names.OfficialNames(wowdb_path)
    old_packs: dict[str, str] = {}
    new_packs: dict[str, str] = {}
    changed = {cls: [] for cls in CLASSES}
    diffs = {cls: [] for cls in CLASSES}
    for cls in CLASSES:
        for pack in ('a', 'b'):
            name = f'{cls}-{pack}'
            pack_path = packs_path / f'{name}.md'
            old = pack_path.read_text(encoding='utf-8') if pack_path.is_file() else ''
            old_packs[name] = old
            text = kb_pack.build_pack(corpus_path, _class_patterns(cls, pack),
                                      {'level20', 'level30'}, names)
            new_packs[name] = text
            diff = _diff_text(old, text, pack_path.name, pack_path.name)
            if diff:
                changed[cls].append(pack)
                diff_path = output_dir / f'diff-{name}.txt'
                _write_text(diff_path, diff)
                diffs[cls].append(_relative_path(diff_path))
            if not dry_run:
                history_dir = packs_path.parent / 'packs-historial' / stamp
                if pack_path.is_file():
                    history_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(pack_path, history_dir / pack_path.name)
                _write_text(pack_path, text)
    if names.conn is not None:
        names.conn.close()

    with tempfile.TemporaryDirectory(prefix='guide-update-') as temp_dir:
        status_report = Path(temp_dir) / 'status.md'
        summary = kb_status.run_status(cards_path, corpus_path, status_report,
                                       write=False)
    stale = _stale_ids(cards_path, corpus_path)
    classified = classify_cards(cards_path, stale, corpus_path,
                                old_packs, new_packs)
    cosmetic_ids = {
        card.get('id') for values in classified.values()
        for card in values['cosmetic'] if isinstance(card.get('id'), str)
    }
    if not dry_run and cosmetic_ids:
        kb_status.run_status(cards_path, corpus_path,
                             output_dir / 'estado-fichas.md', write=True,
                             only=cosmetic_ids)

    builds = _build_changes(old_packs, new_packs)
    classes_with_stale = {
        cls for cls, values in classified.items()
        if values['cosmetic'] or values['real']
    }
    changed_without_stale = [cls for cls in CLASSES
                             if changed[cls] and cls not in classes_with_stale]
    counts_conn = sqlite3.connect(corpus_path)
    try:
        corpus_counts = {
            'guides': counts_conn.execute('SELECT COUNT(*) FROM guides').fetchone()[0],
            'sections': counts_conn.execute('SELECT COUNT(*) FROM sections').fetchone()[0],
        }
    finally:
        counts_conn.close()
    _render_report(output_dir / 'INFORME.md', report_path, corpus_counts,
                   classified, builds, changed_without_stale, summary['uncovered'])

    if classified['other']['real']:
        with (output_dir / 'INFORME.md').open('a', encoding='utf-8', newline='') as handle:
            handle.write('\nFichas caducadas fuera de archivos de clase: ' + ', '.join(
                f'`{card.get("id", "")}`' for card in classified['other']['real']) + '.\n')

    for cls in CLASSES:
        new_builds, removed_builds = builds[cls]['new'], builds[cls]['removed']
        if not classified[cls]['real'] and not new_builds and not removed_builds:
            continue
        data = {
            'class': cls,
            'stale_real': [card.get('id') for card in classified[cls]['real']],
            'cosmetic': [card.get('id') for card in classified[cls]['cosmetic']],
            'builds_new': new_builds,
            'builds_removed': removed_builds,
            'diffs': diffs[cls],
            'packs': {pack: _relative_path(packs_path / f'{cls}-{pack}.md')
                      for pack in ('a', 'b')},
        }
        _write_text(output_dir / f'{cls}.json',
                    json.dumps(data, ensure_ascii=False, indent=2) + '\n')

    if not dry_run:
        registry_data[report_path.name] = datetime.now().astimezone().isoformat(
            timespec='seconds')
        _write_text(registry_path,
                    json.dumps(registry_data, ensure_ascii=False, indent=2) + '\n')
    print(f'Informe: {output_dir / "INFORME.md"}')
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--sources', type=Path)
    parser.add_argument('--corpus', type=Path)
    parser.add_argument('--cards', type=Path)
    parser.add_argument('--packs', type=Path)
    parser.add_argument('--wowdb', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--registry', type=Path)
    args = parser.parse_args(argv)
    return update(args.report, args.force, args.dry_run, args.sources,
                  args.corpus, args.cards, args.packs, args.wowdb, args.out,
                  args.registry)


if __name__ == '__main__':
    raise SystemExit(main())
