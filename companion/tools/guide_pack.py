#!/usr/bin/env python3
"""Genera paquetes de fuentes por capítulo para la guía de principiantes."""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from askforever import config
from askforever.data.wowdb import normalize
from askforever.engine.guide import (_ALLOWED_TAG_RE, _token_match, clean_text,
                                     tokenize)

CHAPTER_RE = re.compile(r'^##\s+(\d+)\.\s+(.+?)\s*$')
TABLE_SEPARATOR = re.compile(r'^:?-{2,}:?$')
CORPUS_TABLES = (
    'GlobalStrings', 'gametips', 'ChrClasses', 'ChrRaces',
    'ChrRaceRacialAbility', 'SkillLine', 'exhaustion',
)
CHAPTER_TABLES = ('levelexperience', 'chatchannels')
ALL_TABLES = CORPUS_TABLES + CHAPTER_TABLES


class Corpus(list):
    """Lista de entradas con un índice invertido por prefijo de token."""

    def __init__(self, entries=()):
        super().__init__(entries)
        self.index = _build_index(self)


def _entry(ref: str, text_es, text_en) -> dict:
    text_es = clean_text(text_es)
    text_en = clean_text(text_en)
    if not text_es:
        text_es = text_en
    return {
        'ref': ref,
        'text_es': text_es,
        'text_en': text_en,
        'tokens_es': frozenset(tokenize(text_es)),
        'tokens_en': frozenset(tokenize(text_en)),
        'label': _label(ref),
        'length': len(text_es) + len(text_en),
    }


def _label(ref: str) -> str:
    if ref.startswith('gametip:'):
        return 'texto de ayuda'
    if ref.startswith('GlobalStrings:'):
        tag = ref.split(':', 1)[1]
        if _ALLOWED_TAG_RE.match(tag):
            return 'texto de ayuda'
    return 'sin verificar en Forever'


def _table_exists(conn, table: str) -> bool:
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,)).fetchone()
        return row is not None
    except sqlite3.Error:
        return False


def _rows(conn, sql: str, params=()):
    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        if not rows or isinstance(rows[0], (sqlite3.Row, dict)):
            return rows
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    except sqlite3.Error:
        return []


def _build_index(entries) -> dict:
    index = {}
    for entry in entries:
        tokens = set(entry.get('tokens_es') or ())
        tokens |= set(entry.get('tokens_en') or ())
        for token in tokens:
            index.setdefault(token[:4], []).append(entry)
    return index


def build_corpus(conn, min_length: int):
    try:
        min_length = max(0, int(min_length))
    except (TypeError, ValueError):
        min_length = 20
    entries = []
    for row in _rows(conn,
                     'SELECT ID, BaseTag, TagText_lang, TagText_lang_esES '
                     'FROM GlobalStrings'):
        ref = f'GlobalStrings:{row["BaseTag"] or ""}'
        entry = _entry(ref, row['TagText_lang_esES'] or row['TagText_lang'],
                       row['TagText_lang'])
        if max(len(entry['text_es']), len(entry['text_en'])) < min_length:
            continue
        if entry['text_es'] or entry['text_en']:
            entries.append(entry)
    for row in _rows(conn,
                     'SELECT ID, Text_lang, Text_lang_esES FROM gametips'):
        entry = _entry(f'gametip:{row["ID"]}',
                       row['Text_lang_esES'] or row['Text_lang'],
                       row['Text_lang'])
        if entry['text_es'] or entry['text_en']:
            entries.append(entry)
    for row in _rows(conn,
                     'SELECT ID, Description_lang, Description_lang_esES '
                     'FROM ChrClasses'):
        entry = _entry(f'ChrClasses:{row["ID"]}',
                       row['Description_lang_esES'] or row['Description_lang'],
                       row['Description_lang'])
        if entry['text_es'] or entry['text_en']:
            entries.append(entry)
    playable = {row['ID'] for row in _rows(
        conn, 'SELECT ID FROM ChrRaces WHERE PlayableRaceBit >= 0')}
    if playable:
        for row in _rows(
                conn,
                'SELECT ID, Name_lang, Name_lang_esES, Description_lang, '
                'Description_lang_esES, DescriptionShort_lang, '
                'DescriptionShort_lang_esES, ChrRacesID '
                'FROM ChrRaceRacialAbility'):
            if row['ChrRacesID'] not in playable:
                continue
            es = (row['Description_lang_esES']
                  or row['DescriptionShort_lang_esES']
                  or row['Name_lang_esES'] or row['Name_lang'] or '')
            en = (row['Description_lang'] or row['DescriptionShort_lang']
                  or row['Name_lang'] or '')
            entry = _entry(f'ChrRaceRacialAbility:{row["ID"]}', es, en)
            if entry['text_es'] or entry['text_en']:
                entries.append(entry)
    for row in _rows(
            conn,
            'SELECT ID, Description_lang, Description_lang_esES '
            'FROM SkillLine WHERE CategoryID IN (9, 11)'):
        entry = _entry(f'SkillLine:{row["ID"]}',
                       row['Description_lang_esES'] or row['Description_lang'],
                       row['Description_lang'])
        if entry['text_es'] or entry['text_en']:
            entries.append(entry)
    for row in _rows(conn, 'SELECT ID, Name_lang, Name_lang_esES FROM exhaustion'):
        entry = _entry(f'exhaustion:{row["ID"]}',
                       row['Name_lang_esES'] or row['Name_lang'],
                       row['Name_lang'])
        if entry['text_es'] or entry['text_en']:
            entries.append(entry)
    return Corpus(entries)


def search(corpus, question, limit: int):
    entries = corpus
    index = getattr(corpus, 'index', None)
    if index is None:
        index = _build_index(entries)
    question_tokens = set(tokenize(question))
    if not question_tokens:
        return []
    candidates = {}
    for token in question_tokens:
        for entry in index.get(token[:4], ()):
            candidates[id(entry)] = entry
    results = []
    for entry in candidates.values():
        tokens = set(entry.get('tokens_es') or ())
        tokens |= set(entry.get('tokens_en') or ())
        score = sum(1 for token in question_tokens
                    if any(_token_match(token, candidate) for candidate in tokens))
        if score < 2 and not (len(question_tokens) <= 2 and score >= 1):
            continue
        result = dict(entry)
        result['score'] = score
        results.append(result)
    results.sort(key=lambda item: (
        -item['score'],
        0 if item['label'] == 'texto de ayuda' else 1,
        item['length'], item['ref']))
    return results[:limit]


def parse_index(text: str):
    chapters = []
    current = None
    for raw_line in text.splitlines():
        match = CHAPTER_RE.match(raw_line.strip())
        if match:
            current = {
                'number': int(match.group(1)),
                'title': match.group(2).strip(),
                'questions': [],
            }
            chapters.append(current)
            continue
        if raw_line.strip().startswith('##'):
            current = None
            continue
        if current is None:
            continue
        line = raw_line.strip()
        if not line.startswith('|'):
            continue
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        if len(cells) < 2:
            continue
        if cells[0].lower() in ('pregunta', 'question'):
            continue
        if all(TABLE_SEPARATOR.match(cell) for cell in cells):
            continue
        if cells[0] and cells[1]:
            current['questions'].append((cells[0], cells[1]))
    return chapters


def slugify(title: str) -> str:
    slug = '-'.join(normalize(title).split())
    return slug or 'capitulo'


def _truncate(text: str, length: int = 400) -> str:
    return text if len(text) <= length else text[:length] + '…'


def _cell(value) -> str:
    if isinstance(value, (int, float)):
        return str(value)
    text = clean_text(value)
    return text.replace('|', '\\|')


def _table(lines, title: str, headers, rows, missing: bool = False) -> None:
    lines.append(f'### {title}')
    lines.append('')
    if missing:
        lines.append('_tabla no disponible_')
        lines.append('')
        return
    if not rows:
        lines.append('_Sin filas._')
        lines.append('')
        return
    lines.append('| ' + ' | '.join(headers) + ' |')
    lines.append('| ' + ' | '.join('---' for _header in headers) + ' |')
    for row in rows:
        lines.append('| ' + ' | '.join(_cell(value) for value in row) + ' |')
    lines.append('')


def _missing_tables(conn) -> list:
    return [name for name in ALL_TABLES if not _table_exists(conn, name)]


def _chapter_tables(conn, number: int):
    lines = []
    if number == 1:
        missing = not _table_exists(conn, 'exhaustion')
        rows = _rows(conn, 'SELECT ID, Name_lang_esES, Name_lang, Xp, Factor, '
                           'OutdoorHours, InnHours, Threshold FROM exhaustion '
                           'ORDER BY ID')
        values = [(row['ID'], row['Name_lang_esES'] or row['Name_lang'],
                   row['Name_lang'], row['Xp'], row['Factor'],
                   row['OutdoorHours'], row['InnHours'], row['Threshold'])
                  for row in rows]
        _table(lines, 'exhaustion',
               ['ID', 'ES', 'EN', 'Xp', 'Factor', 'Horas exterior',
                'Horas posada', 'Umbral'], values, missing)
        missing = not _table_exists(conn, 'levelexperience')
        if missing:
            _table(lines, 'levelexperience', ['ID', 'Nivel', 'Experiencia'], [],
                   True)
        else:
            rows = _rows(conn, 'SELECT ID, Level, ContentSetID, Experience '
                               'FROM levelexperience WHERE Level <= 60 '
                               'ORDER BY ContentSetID, Level, ID')
            groups = {}
            for row in rows:
                groups.setdefault(row['ContentSetID'], []).append(
                    (row['ID'], row['Level'], row['Experience']))
            if not groups:
                _table(lines, 'levelexperience', ['ID', 'Nivel', 'Experiencia'],
                       [], False)
            for content_set, values in groups.items():
                _table(lines, f'levelexperience (ContentSetID {content_set})',
                       ['ID', 'Nivel', 'Experiencia'], values)
    elif number == 3:
        missing = not _table_exists(conn, 'ChrRaces')
        races = _rows(conn, 'SELECT ID, Name_lang, Name_lang_esES, FactionID, '
                            'PlayableRaceBit FROM ChrRaces '
                            'WHERE PlayableRaceBit >= 0 ORDER BY ID')
        values = [(row['ID'], row['Name_lang_esES'] or row['Name_lang'],
                   row['Name_lang'], row['FactionID'], row['PlayableRaceBit'])
                  for row in races]
        _table(lines, 'ChrRaces (razas jugables)',
               ['ID', 'ES', 'EN', 'FactionID', 'PlayableRaceBit'], values, missing)
        playable = {row['ID'] for row in races}
        missing = not _table_exists(conn, 'ChrRaceRacialAbility')
        rows = _rows(conn, 'SELECT ID, Name_lang, Name_lang_esES, '
                           'DescriptionShort_lang, DescriptionShort_lang_esES, '
                           'ChrRacesID FROM ChrRaceRacialAbility ORDER BY ID')
        values = [(row['ChrRacesID'], row['ID'],
                   row['Name_lang_esES'] or row['Name_lang'], row['Name_lang'],
                   row['DescriptionShort_lang_esES']
                   or row['DescriptionShort_lang'],
                   row['DescriptionShort_lang'])
                  for row in rows if row['ChrRacesID'] in playable]
        _table(lines, 'ChrRaceRacialAbility (razas jugables)',
               ['Raza ID', 'ID', 'Habilidad ES', 'Habilidad EN',
                'Descripción corta ES', 'Descripción corta EN'], values, missing)
    elif number == 4:
        missing = not _table_exists(conn, 'ChrClasses')
        rows = _rows(conn, 'SELECT ID, Name_lang, Name_lang_esES, '
                           'Description_lang, Description_lang_esES '
                           'FROM ChrClasses ORDER BY ID')
        values = [(row['ID'], row['Name_lang_esES'] or row['Name_lang'],
                   row['Name_lang'], row['Description_lang_esES']
                   or row['Description_lang'])
                  for row in rows]
        _table(lines, 'ChrClasses', ['ID', 'ES', 'EN', 'Descripción ES'],
               values, missing)
    elif number == 5:
        missing = not _table_exists(conn, 'SkillLine')
        rows = _rows(conn, 'SELECT ID, DisplayName_lang, DisplayName_lang_esES, '
                           'CategoryID, Description_lang, Description_lang_esES '
                           'FROM SkillLine WHERE CategoryID IN (9, 11) '
                           'ORDER BY CategoryID, ID')
        values = [(row['ID'], row['CategoryID'],
                   row['DisplayName_lang_esES'] or row['DisplayName_lang'],
                   row['DisplayName_lang'], row['Description_lang_esES']
                   or row['Description_lang'])
                  for row in rows]
        _table(lines, 'SkillLine (categorías 11 y 9)',
               ['ID', 'Categoría', 'ES', 'EN', 'Descripción ES'], values, missing)
    elif number == 11:
        missing = not _table_exists(conn, 'chatchannels')
        rows = _rows(conn, 'SELECT ID, Name_lang, Name_lang_esES, '
                           'Shortcut_lang, Shortcut_lang_esES '
                           'FROM chatchannels ORDER BY ID')
        values = [(row['ID'], row['Name_lang_esES'] or row['Name_lang'],
                   row['Name_lang'], row['Shortcut_lang_esES']
                   or row['Shortcut_lang'])
                  for row in rows]
        _table(lines, 'chatchannels', ['ID', 'ES', 'EN', 'Atajo ES'],
               values, missing)
    return lines


def render_chapter(chapter, corpus, conn, limit: int, generated: str,
                   db_name: str) -> str:
    number = chapter['number']
    title = chapter['title']
    lines = [f'# Paquete de fuentes — {number}. {title}', '']
    lines.append(f'Generado: {generated} · base: {Path(str(db_name)).name}')
    lines.append('')
    lines.append(
        'Estos textos son candidatos, no respuestas. Los textos marcados como '
        '«sin verificar en Forever» necesitan confirmación antes de usarlos. '
        'Las fuentes web se añaden a mano con su URL.')
    lines.append('')
    missing = _missing_tables(conn)
    if missing:
        lines.append('_Tablas no disponibles: ' + ', '.join(
            f'{name} (tabla no disponible)' for name in missing) + '._')
        lines.append('')
    for question, planned_source in chapter['questions']:
        lines.append(f'## {question}')
        lines.append('')
        lines.append(f'Fuente prevista: {planned_source}')
        lines.append('')
        candidates = search(corpus, question, limit)
        if candidates:
            for index, candidate in enumerate(candidates, 1):
                lines.append(
                    f'{index}. `{candidate["ref"]}` · {candidate["label"]} · '
                    f'puntuación {candidate["score"]}')
                lines.append(f'   - ES: {_truncate(candidate["text_es"])}')
                lines.append(f'   - EN: {_truncate(candidate["text_en"])}')
        else:
            lines.append('_Sin candidatos en el cliente._')
        lines.append('')
        lines.append('### Fuentes web (añadir a mano)')
        lines.append('')
        lines.append('- (pendiente)')
        lines.append('')
    lines.append('## Tablas del cliente (sin verificar en Forever)')
    lines.append('')
    table_lines = _chapter_tables(conn, number)
    if table_lines:
        lines.extend(table_lines)
    else:
        lines.append('_Sin tablas específicas para este capítulo._')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def _probe_block(text: str) -> str:
    lines = text.splitlines(keepends=True)
    offset = 0
    for line in lines:
        if '["probe"]' in line:
            probe_at = line.find('["probe"]')
            tail = text[offset + probe_at:]
            brace = tail.find('{')
            if brace < 0:
                break
            depth = 0
            for index, char in enumerate(tail[brace:], brace):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        return text[offset:offset + probe_at + index + 1]
            break
        offset += len(line)
    return text


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8', newline='')


def _probe_text(probe_path: Path, generated: str, db_name: str) -> str:
    raw = probe_path.read_text(encoding='utf-8')
    block = _probe_block(raw)
    return ('# Diagnóstico de la sonda\n'
            f'Generado: {generated} · base: {Path(str(db_name)).name}\n\n'
            f'```lua\n{block.rstrip()}\n```\n')


def _database_uri(path: Path) -> str:
    return path.resolve().as_uri() + '?mode=ro'


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Genera paquetes de fuentes de la guía.')
    parser.add_argument('--db')
    parser.add_argument('--index', default=str(
        REPO_ROOT / '.agents' / 'plans' / 'guia' / 'indice.md'))
    parser.add_argument('--out', default=str(
        REPO_ROOT / '.agents' / 'plans' / 'guia' / 'paquetes'))
    parser.add_argument('--limit', type=int, default=8)
    parser.add_argument('--min-length', dest='min_length', type=int, default=20)
    parser.add_argument('--probe')
    args = parser.parse_args(argv)

    db_value = args.db or config.get_wowdata_path()
    if not db_value:
        print('No se encontró la base de datos de wowdata. Usa --db RUTA.')
        return 2
    db_path = Path(db_value)
    if not db_path.is_file():
        print(f'No existe la base de datos: {db_path.name}')
        return 2
    index_path = Path(args.index)
    if not index_path.is_file():
        print(f'No existe el índice: {index_path.name}')
        return 2
    chapters = parse_index(index_path.read_text(encoding='utf-8'))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = datetime.now().strftime('%Y-%m-%d %H:%M')
    db_name = db_path.name
    written = questions = without = 0
    try:
        conn = sqlite3.connect(_database_uri(db_path), uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        print('No se pudo abrir la base de datos en modo lectura.')
        return 2
    try:
        corpus = build_corpus(conn, args.min_length)
        for chapter in chapters:
            filename = f'{chapter["number"]:02d}-{slugify(chapter["title"])}.md'
            text = render_chapter(chapter, corpus, conn, args.limit, generated,
                                  db_name)
            _write_text(out_dir / filename, text)
            written += 1
            questions += len(chapter['questions'])
            without += sum(1 for question, _source in chapter['questions']
                           if not search(corpus, question, args.limit))
        if args.probe:
            probe_path = Path(args.probe)
            if probe_path.is_file():
                try:
                    _write_text(out_dir / 'diagnostico.md',
                                _probe_text(probe_path, generated, db_name))
                except (OSError, UnicodeError):
                    pass
    finally:
        conn.close()
    print(f'Paquetes escritos: {written}')
    print(f'Preguntas: {questions}')
    print(f'Sin candidatos: {without}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
