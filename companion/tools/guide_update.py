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
GROUPS = ('cosmetic', 'structured', 'recovered', 'real')
GUIDE_KIND_RANK = {'visual': 1, 'recovered': 2, 'game': 3}

# Bloques que el extractor guarda aparte (tablas de talentos y puntos de mapa) y las fichas no copian.
TALENT_BUILD_RE = re.compile(r'^\*\*Talent Build\s*[—–-]')
TALENT_ORDER_RE = re.compile(r'^\*\*Talent Order\*\*\s*$')
TREE_HEADING_RE = re.compile(r'^#{4}\s+.*\(\s*\d+\s*/\s*51\s*\)\s*$')
TALENT_TABLE_RE = re.compile(r'^\|\s*Talent\s*\|\s*Rank\s*\|')
ORDER_TABLE_RE = re.compile(r'^\|\s*Level\s*\|\s*Talent\s*\|\s*Rank\s*\|')
MAP_HEADING_RE = re.compile(r'^\*\*Map:\s*.+?\*\*$')
COORD_END_RE = re.compile(
    r'\(\s*-?\d+(?:[.,]\d+)?\s*,\s*-?\d+(?:[.,]\d+)?\s*\)\s*$')


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


def _quote_body(line: str) -> str:
    """Quita el prefijo de cita de Markdown para reconocer los bloques también dentro de una cita."""
    body = line
    while body.startswith('>'):
        body = body[1:]
        if body.startswith(' '):
            body = body[1:]
    return body.strip()


def _next_body(lines: list[str], index: int) -> tuple[int, str]:
    while index < len(lines) and not _quote_body(lines[index]):
        index += 1
    return index, (_quote_body(lines[index]) if index < len(lines) else '')


def _skip_table(lines: list[str], index: int) -> int:
    """Salta solo la tabla Level/Talent/Rank; una cabecera distinta o una línea en blanco la cierran."""
    started = False
    while index < len(lines):
        body = _quote_body(lines[index])
        if not body:
            if started:
                # La tabla acaba aquí; se consumen las líneas en blanco (sin texto propio).
                return _next_body(lines, index)[0]
            index += 1
            continue
        if not body.startswith('|'):
            break
        if not started:
            if not ORDER_TABLE_RE.match(body):
                break
            started = True
        index += 1
    return index


def _skip_talent_build(lines: list[str], index: int) -> int:
    """Salta los árboles del bloque con sus tablas Talent/Rank; una línea en blanco cierra cada tabla."""
    in_table = False
    while index < len(lines):
        body = _quote_body(lines[index])
        if not body:
            if not in_table:
                index += 1
                continue
            # El bloque puede seguir con otro árbol tras la línea en blanco.
            next_index, next_body = _next_body(lines, index)
            if TREE_HEADING_RE.match(next_body):
                in_table = False
                index = next_index
                continue
            return next_index
        if TALENT_BUILD_RE.match(body):
            in_table = False
            index += 1
            continue
        if TREE_HEADING_RE.match(body):
            in_table = False
            index += 1
            continue
        if body.startswith('|'):
            if in_table or TALENT_TABLE_RE.match(body):
                in_table = True
                index += 1
                continue
        break
    return index


def _skip_map(lines: list[str], index: int) -> int:
    while index < len(lines):
        body = _quote_body(lines[index])
        if not body:
            index += 1
        elif body.startswith('-') and COORD_END_RE.search(body):
            index += 1
        else:
            break
    return index


def _strip_structured_blocks(text: str) -> str:
    """Quita del texto los bloques de talentos y mapas que el extractor guarda en tablas."""
    lines = text.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        body = _quote_body(lines[index])
        if TALENT_BUILD_RE.match(body):
            index = _skip_talent_build(lines, index + 1)
        elif TALENT_ORDER_RE.match(body):
            index = _skip_table(lines, index + 1)
        elif MAP_HEADING_RE.match(body):
            index = _skip_map(lines, index + 1)
        else:
            kept.append(lines[index])
            index += 1
    return '\n'.join(kept)


def _section_map(conn: sqlite3.Connection) -> dict[tuple[str, str], tuple[str, str]]:
    try:
        rows = conn.execute(
            'SELECT guide_key, heading_path, text, hash FROM sections '
            'ORDER BY guide_key, ord').fetchall()
    except sqlite3.Error:
        return {}
    result: dict[tuple[str, str], tuple[str, str]] = {}
    for guide_key, heading_path, text, hash_ in rows:
        result.setdefault((guide_key, heading_path), (text, hash_))
    return result


def _sections_snapshot(path: Path) -> dict[tuple[str, str], tuple[str, str]]:
    """Secciones del corpus antes de reimportarlo: (guía, apartado) → (texto, hash)."""
    if not Path(path).is_file():
        return {}
    conn = sqlite3.connect(path)
    try:
        return _section_map(conn)
    finally:
        conn.close()


def _guide_hashes(path: Path) -> dict[str, str]:
    if not Path(path).is_file():
        return {}
    conn = sqlite3.connect(path)
    try:
        try:
            rows = conn.execute('SELECT guide_key, hash FROM guides').fetchall()
        except sqlite3.Error:
            return {}
    finally:
        conn.close()
    return {guide_key: hash_ for guide_key, hash_ in rows}


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


def _guide_evidence_ok(guide_key: str, stored: set[str],
                       old_guides: dict[str, str]) -> bool:
    guide_hash = old_guides.get(guide_key)
    return guide_hash is not None and 'guide:' + guide_hash in stored


def _evidence_ok(guide_key: str, old: Optional[tuple[str, str]],
                 stored: set[str], old_guides: dict[str, str]) -> bool:
    """Solo se puede descartar el cambio como real si la ficha guardaba el hash anterior."""
    if old is None:
        return False
    if 'section:' + old[1] in stored:
        return True
    return _guide_evidence_ok(guide_key, stored, old_guides)


def _is_cosmetic(old_text: str, new_text: str) -> bool:
    return old_text != new_text and (
        normalize_pack_text(old_text) == normalize_pack_text(new_text))


def _same_without_structured(old_text: str, new_text: str) -> bool:
    return normalize_pack_text(old_text) == normalize_pack_text(
        _strip_structured_blocks(new_text))


def classify_cards(cards_dir: Path, stale_ids: set[str], corpus_path: Path,
                   old_sections: dict[tuple[str, str], tuple[str, str]],
                   old_guides: dict[str, str],
                   guide_kinds: Optional[dict[str, str]] = None
                   ) -> dict[str, dict[str, list]]:
    """Clasifica las fichas caducadas comparando el corpus anterior con el recién importado."""
    kinds = guide_kinds or {}
    result = {cls: {group: [] for group in GROUPS} for cls in CLASSES}
    result['other'] = {group: [] for group in GROUPS}
    conn = sqlite3.connect(corpus_path)
    try:
        guides, by_url = kb_status._corpus(conn)
        new_sections = _section_map(conn)
    finally:
        conn.close()

    for path, data in kb_status.load_cards(cards_dir):
        match = re.fullmatch(r'04-clase-([a-z-]+)\.json', path.name)
        class_name = match.group(1) if match and match.group(1) in result else None
        for card in data.get('sections') or []:
            if not isinstance(card, dict) or card.get('id') not in stale_ids:
                continue
            stored = card.get('source_hashes')
            stored_set = set(stored) if isinstance(stored, list) else set()
            sources = list(dict.fromkeys(_resolve_card_sources(card, guides, by_url)))
            changed = []
            unreviewed = False
            for guide_key, heading in sources:
                new = new_sections.get((guide_key, heading))
                if new is None or 'section:' + new[1] in stored_set:
                    continue
                old = old_sections.get((guide_key, heading))
                # Sin diferencia de texto en esta pasada no hay prueba de que el cambio sea de forma:
                # lo cambió una pasada anterior (varios informes seguidos) y debe revisarse como real,
                # salvo que la ficha ya guarde el hash de guía anterior.
                if old is not None and old[1] == new[1]:
                    if not _guide_evidence_ok(guide_key, stored_set, old_guides):
                        unreviewed = True
                    continue
                changed.append((guide_key, heading, old, new))
            entry = dict(card)
            entry['_review_diffs'] = [
                (f'{guide_key} › {heading}', old[0], new[0])
                for guide_key, heading, old, new in changed
                if old is not None and old[0] != new[0]
            ]
            if unreviewed or not changed:
                group = 'real'
            elif not all(_evidence_ok(guide_key, old, stored_set, old_guides)
                         for guide_key, _heading, old, _new in changed):
                group = 'real'
            elif all(old is not None and _is_cosmetic(old[0], new[0])
                     for _guide_key, _heading, old, new in changed):
                group = 'cosmetic'
            else:
                kinds_here = {kinds.get(guide_key, 'game')
                              for guide_key, _heading, _old, _new in changed}
                if kinds_here <= {'recovered', 'visual'} and all(
                        old is not None and _same_without_structured(old[0], new[0])
                        for _guide_key, _heading, old, new in changed):
                    group = 'structured'
                elif kinds_here <= {'recovered', 'visual'}:
                    group = 'recovered'
                else:
                    group = 'real'
            result[class_name or 'other'][group].append(entry)
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


def _explicit_report(value: Path) -> Path:
    """Informe indicado a mano: primero se busca en el directorio actual y luego en la raíz del repo."""
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = Path.cwd() / path
    return candidate if candidate.is_file() else REPO_ROOT / path


def _select_reports(sources: Path, explicit: list[Path], registry: dict,
                    force: bool) -> list[Path]:
    if explicit:
        selected = []
        for value in explicit:
            path = _explicit_report(value)
            if path not in selected:
                selected.append(path)
        return selected
    reports = sorted(
        (path for path in (sources / 'cambios').glob('*.md')
         if path.is_file() and not path.name.endswith('-resumen.md')),
        key=lambda path: path.name)
    if force:
        return reports
    return [path for path in reports if path.name not in registry]


def _guide_kinds(reports: list[Path]) -> dict[str, str]:
    """Tipo de cambio por guía; sin JSON no se distingue la reescritura del extractor del cambio real."""
    result: dict[str, str] = {}
    for report in reports:
        try:
            data = json.loads(report.with_suffix('.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        for entry in data.get('guides') or []:
            if not isinstance(entry, dict):
                continue
            path = entry.get('path')
            if not isinstance(path, str) or not path:
                continue
            key = 'wowhead/' + (path[:-3] if path.endswith('.md') else path)
            if entry.get('reason') != 'format':
                kind = 'game'
            elif entry.get('change_kind') == 'visual':
                kind = 'visual'
            else:
                kind = 'recovered'
            current = result.get(key)
            if current is None or GUIDE_KIND_RANK[kind] > GUIDE_KIND_RANK[current]:
                result[key] = kind
    return result


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


def _render_cards(lines: list[str], classified: dict, group: str, title: str) -> None:
    lines.extend(['', f'## {title}', ''])
    found = False
    for cls in CLASSES + ('other',):
        cards = classified[cls][group]
        if not cards:
            continue
        found = True
        label = cls if cls != 'other' else 'otras'
        lines.append(f'- **{label}**: ' + ', '.join(
            f'`{card.get("id", "")}`' for card in cards))
    if not found:
        lines.append('Ninguna.')


def _render_report(path: Path, reports: list[Path], corpus_counts: dict,
                   classified: dict, builds: dict, changed_without_stale: list[str],
                   uncovered: int) -> None:
    lines = ['# Actualización diaria de las guías', '',
             'Informes usados: ' + ', '.join(f'`{report.name}`' for report in reports),
             f'Corpus: {corpus_counts["guides"]} guías, '
             f'{corpus_counts["sections"]} secciones.']
    _render_cards(lines, classified, 'cosmetic', 'Fichas cosméticas actualizadas')
    _render_cards(lines, classified, 'structured',
                  'Fichas estructuradas pendientes (no actualizadas)')
    _render_cards(lines, classified, 'recovered',
                  'Fichas recuperadas pendientes (no actualizadas)')
    _render_cards(lines, classified, 'real', 'Fichas caducadas con cambios reales')
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


def update(reports: Optional[list[Path]] = None, force: bool = False,
           dry_run: bool = False, refresh_structured: bool = False,
           sources: Optional[Path] = None, corpus: Optional[Path] = None,
           cards: Optional[Path] = None, packs: Optional[Path] = None,
           wowdb: Optional[Path] = None, out: Optional[Path] = None,
           registry: Optional[Path] = None) -> int:
    def root_path(value: Optional[Path], default: Path) -> Path:
        result = Path(value) if value is not None else default
        return result if result.is_absolute() else REPO_ROOT / result

    sources_path = root_path(sources, Path('.agents/plans/guia/fuentes'))
    corpus_path = root_path(corpus, Path('.agents/corpus/corpus.sqlite'))
    cards_path = root_path(cards, Path('companion/askforever/data/guide'))
    packs_path = root_path(packs, Path('.agents/corpus/packs'))
    wowdb_path = root_path(wowdb, REPO_ROOT.parents[1] / 'wowdata/datos/wow.sqlite')
    out_path = root_path(out, Path('.agents/plans/conocimiento/actualizaciones'))
    registry_path = root_path(registry, Path('.agents/corpus/actualizaciones.json'))
    registry_data = _load_registry(registry_path)
    selected = _select_reports(sources_path, list(reports or []), registry_data, force)
    if reports:
        missing = [path for path in selected if not path.is_file()]
        if missing:
            print('No existe el informe: ' + ', '.join(str(path) for path in missing),
                  file=sys.stderr)
            return 1
    if not selected:
        print('Sin informes nuevos')
        return 0

    stamp = max(_report_stamp(path) for path in selected)
    output_dir = out_path / stamp

    with tempfile.TemporaryDirectory(prefix='guide-update-') as temp_dir:
        # En simulación se importa sobre una copia y la salida va al temporal: nada toca el repo.
        work_corpus = corpus_path
        if dry_run:
            work_corpus = Path(temp_dir) / 'corpus.sqlite'
            output_dir = Path(temp_dir) / stamp
            if corpus_path.is_file():
                shutil.copy2(corpus_path, work_corpus)

        old_sections = _sections_snapshot(work_corpus)
        old_guides = _guide_hashes(work_corpus)

        import_report = Path(temp_dir) / 'informe-importacion.md'
        if dry_run:
            try:
                status = corpus_tool.main([
                    '--sources', str(sources_path), '--db', str(work_corpus),
                    '--report', str(import_report),
                ])
                if status:
                    raise RuntimeError(f'La importación terminó con estado {status}')
            except Exception as exc:
                print(f'No se pudo importar el corpus: {exc}', file=sys.stderr)
                return 1
        else:
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
                text = kb_pack.build_pack(work_corpus, _class_patterns(cls, pack),
                                          {'level20', 'level30'}, names)
                new_packs[name] = text
                diff = _diff_text(old, text, pack_path.name, pack_path.name)
                if diff:
                    changed[cls].append(pack)
                    diff_path = output_dir / f'diff-{name}.txt'
                    _write_text(diff_path, diff)
                    diffs[cls].append(_relative_path(diff_path))
        if names.conn is not None:
            names.conn.close()

        summary = kb_status.run_status(cards_path, work_corpus,
                                       Path(temp_dir) / 'status.md', write=False)
        stale = _stale_ids(cards_path, work_corpus)
        classified = classify_cards(cards_path, stale, work_corpus,
                                    old_sections, old_guides, _guide_kinds(selected))
        refresh_groups = ['cosmetic'] + (['structured'] if refresh_structured else [])
        refresh_ids = {
            card.get('id') for group in refresh_groups
            for values in classified.values() for card in values[group]
            if isinstance(card.get('id'), str)
        }
        if not dry_run and refresh_ids:
            kb_status.run_status(cards_path, work_corpus,
                                 output_dir / 'estado-fichas.md', write=True,
                                 only=refresh_ids)

        builds = _build_changes(old_packs, new_packs)
        classes_with_stale = {
            cls for cls, values in classified.items()
            if any(values[group] for group in GROUPS)
        }
        changed_without_stale = [cls for cls in CLASSES
                                 if changed[cls] and cls not in classes_with_stale]
        counts_conn = sqlite3.connect(work_corpus)
        try:
            corpus_counts = {
                'guides': counts_conn.execute('SELECT COUNT(*) FROM guides').fetchone()[0],
                'sections': counts_conn.execute('SELECT COUNT(*) FROM sections').fetchone()[0],
            }
        finally:
            counts_conn.close()
        _render_report(output_dir / 'INFORME.md', selected, corpus_counts,
                       classified, builds, changed_without_stale, summary['uncovered'])

        for values in classified.values():
            for card in values['recovered']:
                text = ''.join(
                    _diff_text(old, new, f'{label} (antes)', f'{label} (después)')
                    for label, old, new in card.get('_review_diffs') or [])
                _write_text(
                    output_dir / f'recuperado-{card.get("id", "ficha")}.diff', text)

        for cls in CLASSES:
            values = classified[cls]
            new_builds, removed_builds = builds[cls]['new'], builds[cls]['removed']
            if not (values['real'] or values['recovered'] or values['structured']
                    or new_builds or removed_builds):
                continue
            data = {
                'class': cls,
                'stale_real': [card.get('id') for card in values['real']],
                'stale_recovered': [card.get('id') for card in values['recovered']],
                'stale_structured': [card.get('id') for card in values['structured']],
                'cosmetic': [card.get('id') for card in values['cosmetic']],
                'builds_new': new_builds,
                'builds_removed': removed_builds,
                'diffs': diffs[cls],
                'packs': {pack: _relative_path(packs_path / f'{cls}-{pack}.md')
                          for pack in ('a', 'b')},
            }
            _write_text(output_dir / f'{cls}.json',
                        json.dumps(data, ensure_ascii=False, indent=2) + '\n')

        if not dry_run:
            for cls in CLASSES:
                for pack in ('a', 'b'):
                    name = f'{cls}-{pack}'
                    pack_path = packs_path / f'{name}.md'
                    history_dir = packs_path.parent / 'packs-historial' / stamp
                    if pack_path.is_file():
                        history_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(pack_path, history_dir / pack_path.name)
                    _write_text(pack_path, new_packs[name])
            now = datetime.now().astimezone().isoformat(timespec='seconds')
            for path in selected:
                registry_data[path.name] = now
            _write_text(registry_path,
                        json.dumps(registry_data, ensure_ascii=False, indent=2) + '\n')

        totals = {group: sum(len(values[group]) for values in classified.values())
                  for group in GROUPS}
        if not dry_run:
            print(f'Informe: {output_dir / "INFORME.md"}')
        print(f'Fichas: cosméticas {totals["cosmetic"]} · estructuradas '
              f'{totals["structured"]} · recuperadas {totals["recovered"]} · '
              f'reales {totals["real"]}')
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, action='append',
                        help='informe concreto; se puede repetir')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--refresh-structured', action='store_true')
    parser.add_argument('--sources', type=Path)
    parser.add_argument('--corpus', type=Path)
    parser.add_argument('--cards', type=Path)
    parser.add_argument('--packs', type=Path)
    parser.add_argument('--wowdb', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--registry', type=Path)
    args = parser.parse_args(argv)
    return update(args.report, args.force, args.dry_run, args.refresh_structured,
                  args.sources, args.corpus, args.cards, args.packs, args.wowdb,
                  args.out, args.registry)


if __name__ == '__main__':
    raise SystemExit(main())
