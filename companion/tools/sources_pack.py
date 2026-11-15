#!/usr/bin/env python3
"""Convierte páginas de guías guardadas en paquetes de fuentes por capítulo."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import guide_pack
from askforever.engine.guide import _token_match, tokenize

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SRC = (REPO_ROOT / '.agents' / 'plans' / 'guia' / 'fuentes' /
               'icy-veins' / 'guides')
DEFAULT_INDEX = REPO_ROOT / '.agents' / 'plans' / 'guia' / 'indice.md'
DEFAULT_OUT = REPO_ROOT / '.agents' / 'plans' / 'guia' / 'paquetes-fuentes'
MIN_PASSAGE = 40
MAX_TEXT = 1200

IMAGE_RE = re.compile(r'!\[[^\]]*\]\([^)]+\)')
LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]+\)')
HEADING_RE = re.compile(r'^\s{0,3}(#{1,4})\s+(.+?)\s*#*\s*$')
LIST_RE = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+')


class PassageList(list):
    """Lista de pasajes con índice invertido para buscar por token."""

    def __init__(self, entries=(), pages=()):
        super().__init__(entries)
        self.pages = list(pages)
        self.tokens = [
            (frozenset(tokenize(passage.get('heading') or '')),
             frozenset(tokenize(passage.get('text') or '')))
            for passage in self
        ]
        self.index = _build_index(self)


def _split_front_matter(text: str):
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return {}, text
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == '---':
            end = index
            break
    if end is None:
        return {}, text
    meta = {}
    for raw in lines[1:end]:
        key, separator, value = raw.partition(':')
        if not separator:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]
        if key:
            meta[key] = value
    body = '\n'.join(lines[end + 1:]).lstrip('\n')
    return meta, body


def _clean_markup(text: str) -> str:
    text = IMAGE_RE.sub('', str(text or ''))
    return LINK_RE.sub(r'\1', text)


def unwrap(text: str) -> str:
    """Une párrafos partidos en varias líneas y conserva tablas y listas."""
    lines = _clean_markup(text).splitlines()
    blocks = []
    paragraph = []
    special = []
    special_kind = None

    def flush_paragraph():
        if paragraph:
            blocks.append(' '.join(paragraph))
            paragraph.clear()

    def flush_special():
        nonlocal special_kind
        if special:
            blocks.append('\n'.join(special))
            special.clear()
        special_kind = None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_special()
            continue
        if stripped.startswith('|'):
            flush_paragraph()
            if special_kind != 'table':
                flush_special()
                special_kind = 'table'
            special.append(line)
        elif LIST_RE.match(line):
            flush_paragraph()
            if special_kind != 'list':
                flush_special()
                special_kind = 'list'
            special.append(line)
        elif stripped.startswith('```'):
            flush_paragraph()
            flush_special()
            blocks.append(stripped)
        elif HEADING_RE.match(line):
            flush_paragraph()
            flush_special()
            blocks.append(stripped)
        else:
            flush_special()
            paragraph.append(stripped)
    flush_paragraph()
    flush_special()
    return '\n\n'.join(blocks).strip()


def _date(value) -> str:
    text = str(value or '').strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}', text):
        return text[:10]
    return text


def _modified_ts(value) -> float:
    text = str(value or '').strip()
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()
    except ValueError:
        return 0.0


def _folder_of(rel_path) -> str:
    parent = Path(str(rel_path)).parent.as_posix()
    return '' if parent == '.' else parent


def _page_title(meta: dict, rel_path) -> str:
    return str(meta.get('title') or Path(str(rel_path)).stem)


def _heading_text(value: str) -> str:
    return _clean_markup(value).strip()


def _passages_for_body(meta: dict, body: str, rel_path: str):
    file = Path(rel_path).as_posix()
    title = _page_title(meta, file)
    url = str(meta.get('url') or '')
    modified = str(meta.get('modified') or '')
    passages = []
    heading = title
    current = []

    def add_passage():
        text = unwrap('\n'.join(current))
        if len(text) < MIN_PASSAGE:
            return
        anchor = text.split('\n\n', 1)[0].strip()
        heading_value = heading or title
        passages.append({
            'file': file,
            'url': url,
            'title': title,
            'modified': modified,
            'heading': heading_value,
            'anchor_text': anchor[:200],
            'text': text,
        })

    for line in body.splitlines():
        match = HEADING_RE.match(line)
        if match:
            add_passage()
            heading = _heading_text(match.group(2)) or title
            current = []
        else:
            current.append(line)
    add_passage()
    return passages


def parse_page(text: str, rel_path):
    """Devuelve (metadatos, pasajes) de una página Markdown."""
    meta, body = _split_front_matter(text)
    file = Path(str(rel_path)).as_posix()
    meta = dict(meta)
    meta['title'] = _page_title(meta, file)
    return meta, _passages_for_body(meta, body, file)


def _build_index(passages):
    index = {}
    passage_tokens = getattr(passages, 'tokens', None)
    for number, passage in enumerate(passages):
        if passage_tokens is not None:
            heading_tokens, text_tokens = passage_tokens[number]
        else:
            heading_tokens = frozenset(tokenize(passage.get('heading') or ''))
            text_tokens = frozenset(tokenize(passage.get('text') or ''))
        for token in set(heading_tokens) | set(text_tokens):
            index.setdefault(token[:4], set()).add(number)
    return index


def build_passages(src_dir):
    root = Path(src_dir)
    if not root.is_dir():
        return PassageList()
    passages = []
    pages = []
    for path in sorted(root.rglob('*.md'), key=lambda item: item.as_posix()):
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        rel_path = path.relative_to(root).as_posix()
        meta, body = _split_front_matter(text)
        file = Path(rel_path).as_posix()
        page = {
            'file': file,
            'folder': _folder_of(file),
            'title': _page_title(meta, file),
            'url': str(meta.get('url') or ''),
            'modified': str(meta.get('modified') or ''),
            'sha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
        }
        pages.append(page)
        _meta, page_passages = parse_page(text, rel_path)
        passages.extend(page_passages)
    return PassageList(passages, pages)


def _chapter_boost(passage, chapter_number: int) -> int:
    folder = str(passage.get('folder') or '')
    if not folder:
        folder = _folder_of(passage.get('file') or '')
    file = str(passage.get('file') or '')
    under = lambda prefix: folder == prefix or folder.startswith(prefix + '/')
    if chapter_number == 3 and under('razas'):
        return 1
    if chapter_number == 4 and (under('clases')
                                or file == 'general/talent-calculator.md'):
        return 1
    if chapter_number == 5 and under('profesiones'):
        return 1
    if chapter_number == 7 and under('mazmorras'):
        return 1
    if (chapter_number == 10 and file.startswith('general/pvp-')
            and file.endswith('.md')):
        return 1
    if chapter_number in (1, 12) and under('general'):
        return 1
    return 0


def match(passages, question, chapter_number: int, limit: int):
    entries = passages
    index = getattr(passages, 'index', None)
    if index is None:
        index = _build_index(entries)
    question_tokens = set(tokenize(question))
    if not question_tokens:
        return []
    candidates = set()
    for token in question_tokens:
        candidates.update(index.get(token[:4], ()))
    results = []
    passage_tokens = getattr(passages, 'tokens', None)
    for number in candidates:
        passage = entries[number]
        if passage_tokens is not None:
            heading_tokens, text_tokens = passage_tokens[number]
        else:
            heading_tokens = frozenset(tokenize(passage.get('heading') or ''))
            text_tokens = frozenset(tokenize(passage.get('text') or ''))
        score = 0
        for token in question_tokens:
            if any(_token_match(token, candidate) for candidate in heading_tokens):
                score += 2
            elif any(_token_match(token, candidate) for candidate in text_tokens):
                score += 1
        score += _chapter_boost(passage, chapter_number)
        if score < 2 and not (len(question_tokens) <= 2 and score >= 1):
            continue
        results.append((score, passage))
    results.sort(key=lambda item: (
        -item[0],
        -_modified_ts(item[1].get('modified')),
        len(item[1].get('text') or ''),
        item[1].get('file') or '',
        item[1].get('heading') or '',
    ))
    try:
        limit = max(0, int(limit))
    except (TypeError, ValueError):
        limit = 6
    return results[:limit]


def _truncate(text: str, length: int = MAX_TEXT) -> str:
    return text if len(text) <= length else text[:length] + '…'


def _cell(value) -> str:
    return str(value or '').replace('|', '\\|')


def _indented(text: str) -> str:
    return '\n'.join('   ' + line for line in text.splitlines())


def render_chapter(chapter, passages, pages, limit: int, generated: str,
                   source_name: str) -> str:
    number = chapter['number']
    lines = [f'# Fuentes externas — {number}. {chapter["title"]}', '']
    lines.append(f'Fuente: {source_name} · generado {generated} · '
                 f'{len(pages)} páginas')
    lines.append('')
    lines.append(
        'Estos son textos editoriales de terceros para redactar. No los copies '
        'en la guía: escribe los datos con tus propias palabras y cita la URL y '
        'el encabezado. Los datos que salgan de ellos empiezan como '
        '«pendiente» hasta confirmarse.')
    lines.append('')
    for question, planned_source in chapter['questions']:
        lines.append(f'## {question}')
        lines.append('')
        lines.append(f'Fuente prevista: {planned_source}')
        lines.append('')
        found = match(passages, question, number, limit)
        if not found:
            lines.append('_Sin pasajes._')
            lines.append('')
            continue
        for position, (score, passage) in enumerate(found, 1):
            title = passage.get('title') or ''
            heading = passage.get('heading') or title
            lines.append(f'{position}. {title} › {heading} · actualizado '
                         f'{_date(passage.get("modified"))} · puntuación {score}')
            lines.append(f'   {passage.get("url") or ""}')
            lines.append(_indented(_truncate(passage.get('text') or '')))
            lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def render_pages(pages, matched_files, generated: str, source_name: str) -> str:
    lines = ['# Páginas de fuentes externas', '',
             f'Fuente: {source_name} · generado {generated}', '',
             '| Carpeta | Título | URL | Actualizado |',
             '|---|---|---|---|']
    for page in sorted(pages, key=lambda item: (
            item.get('folder') or '', (item.get('title') or '').lower())):
        lines.append('| ' + ' | '.join((
            _cell(page.get('folder')), _cell(page.get('title')),
            _cell(page.get('url')), _cell(_date(page.get('modified'))))) + ' |')
    lines.extend(['', '## Sin asignar', ''])
    unassigned = [page for page in pages
                  if page.get('file') not in matched_files]
    if not unassigned:
        lines.append('_Ninguna._')
    else:
        for page in sorted(unassigned, key=lambda item: (
                item.get('folder') or '', (item.get('title') or '').lower())):
            lines.append(f'- {page.get("title") or page.get("file")} '
                         f'({page.get("url") or ""})')
    return '\n'.join(lines).rstrip() + '\n'


def diff_state(old, new):
    old = old if isinstance(old, dict) else {}
    new = new if isinstance(new, dict) else {}
    return {
        'new': sorted(set(new) - set(old)),
        'changed': sorted(path for path in set(old) & set(new)
                          if old[path] != new[path]),
        'removed': sorted(set(old) - set(new)),
    }


def render_changes(diff, old, new, first: bool, generated: str,
                   source_name: str) -> str:
    lines = ['# Cambios en las fuentes externas', '',
             f'Fuente: {source_name} · generado {generated}', '']
    if first:
        lines.extend(['Primera ejecución.', ''])
    for title, paths in (('Nuevas', diff['new']),
                         ('Modificadas', diff['changed']),
                         ('Eliminadas', diff['removed'])):
        lines.append(f'## {title}')
        lines.append('')
        if not paths:
            lines.append('_Ninguna._')
        for path in paths:
            if title == 'Nuevas':
                lines.append(f'- {path} (actualizado '
                             f'{_date((new.get(path) or {}).get("modified"))})')
            elif title == 'Modificadas':
                lines.append(
                    f'- {path} (antes: '
                    f'{_date((old.get(path) or {}).get("modified"))} · ahora: '
                    f'{_date((new.get(path) or {}).get("modified"))})')
            else:
                lines.append(f'- {path}')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8', newline='')


def _load_state(path: Path, first: bool):
    if first:
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Genera paquetes de fuentes externas.')
    parser.add_argument('--src', default=str(DEFAULT_SRC))
    parser.add_argument('--index', default=str(DEFAULT_INDEX))
    parser.add_argument('--out', default=str(DEFAULT_OUT))
    parser.add_argument('--source-name', default='Icy Veins')
    parser.add_argument('--limit', type=int, default=6)
    parser.add_argument('--state')
    args = parser.parse_args(argv)

    src_dir = Path(args.src)
    if not src_dir.is_dir():
        print(f'No existe la carpeta de fuentes: {src_dir.name}')
        return 2
    index_path = Path(args.index)
    if not index_path.is_file():
        print(f'No existe el índice: {index_path.name}')
        return 2
    chapters = guide_pack.parse_index(index_path.read_text(encoding='utf-8'))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state) if args.state else out_dir / 'estado.json'
    first = not state_path.is_file()

    passages = build_passages(src_dir)
    pages = getattr(passages, 'pages', [])
    generated = datetime.now().strftime('%Y-%m-%d %H:%M')
    matched_files = set()
    without = 0
    written = 0
    for chapter in chapters:
        for question, _source in chapter['questions']:
            all_hits = match(passages, question, chapter['number'],
                             max(1, len(passages)))
            matched_files.update(hit[1]['file'] for hit in all_hits)
            if not match(passages, question, chapter['number'], args.limit):
                without += 1
        filename = f'{chapter["number"]:02d}-{guide_pack.slugify(chapter["title"])}.md'
        _write_text(out_dir / filename,
                    render_chapter(chapter, passages, pages, args.limit,
                                   generated, args.source_name))
        written += 1

    _write_text(out_dir / 'paginas.md',
                render_pages(pages, matched_files, generated, args.source_name))

    new_state = {page['file']: {'sha256': page['sha256'],
                                'modified': page['modified']} for page in pages}
    old_state = _load_state(state_path, first)
    diff = diff_state(old_state, new_state)
    _write_text(out_dir / 'cambios.md',
                render_changes(diff, old_state, new_state, first, generated,
                               args.source_name))
    _write_text(state_path, json.dumps(new_state, ensure_ascii=False, indent=2) + '\n')

    print(f'Páginas: {len(pages)}')
    print(f'Pasajes: {len(passages)}')
    print(f'Preguntas sin pasajes: {without}')
    print(f'Nuevas: {len(diff["new"])} · Modificadas: '
          f'{len(diff["changed"])} · Eliminadas: {len(diff["removed"])}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
