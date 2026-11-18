"""Generate readable addon data files from a published SQLite base.

Oversized tables continue in later files as repeated patch entries with row parts.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
from urllib.parse import quote
from urllib.request import urlopen
from zipfile import ZipFile, BadZipFile


WRAPPER_HEADER = '-- AskForever data: read by the AskForever companion, never loaded by the game.\nreturn [==[\n'
WRAPPER_FOOTER = '\n]==]\n'
DEFAULT_FILE_SIZE = 4 * 1024 * 1024
WARN_TOTAL_SIZE = 25 * 1024 * 1024
HASH_RE = re.compile(r'^[0-9a-fA-F]{64}$')
VOLATILE_COLUMNS = frozenset({'ultima_vez'})


class PatchError(Exception):
    """An input cannot be represented as a valid addon patch."""


def _json_bytes(value):
    if isinstance(value, bytes):
        return {'b64': base64.b64encode(value).decode('ascii')}
    return value


def _encode_json(value):
    try:
        result = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise PatchError(f'cannot encode patch data as JSON: {exc}') from exc
    if ']==]' in result:
        raise PatchError("JSON contains the forbidden wrapper terminator ']==]'")
    return result


def wrap_json(value):
    return WRAPPER_HEADER + _encode_json(value) + WRAPPER_FOOTER


def _sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _download_base(base_tag, cache):
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f'{base_tag}-wow.sqlite.zip'
    checksum_file = cache / f'{base_tag}-wow.sqlite.zip.sha256'
    encoded_tag = quote(base_tag, safe='-.')
    base_url = f'https://github.com/warcrafted-server/AskForever/releases/download/{encoded_tag}'
    try:
        for url, destination in (
            (f'{base_url}/wow.sqlite.zip', archive),
            (f'{base_url}/wow.sqlite.zip.sha256', checksum_file),
        ):
            with urlopen(url, timeout=60) as response, destination.open('wb') as target:
                shutil.copyfileobj(response, target)
    except Exception as exc:
        raise PatchError(f'could not download base release {base_tag}: {exc}') from exc
    checksum_parts = checksum_file.read_text(encoding='ascii').strip().split()
    if not checksum_parts:
        raise PatchError(f'empty SHA-256 file for base release {base_tag}')
    expected = checksum_parts[0]
    if not HASH_RE.fullmatch(expected):
        raise PatchError(f'invalid SHA-256 file for base release {base_tag}')
    actual = _sha256(archive)
    if actual.lower() != expected.lower():
        raise PatchError(f'SHA-256 mismatch for downloaded base: expected {expected}, got {actual}')
    return archive, actual


@contextmanager
def _open_database(path):
    path = Path(path)
    temporary = None
    if path.suffix.lower() == '.zip':
        try:
            with ZipFile(path) as archive:
                members = [name for name in archive.namelist() if name.lower().endswith('.sqlite')]
                if len(members) != 1:
                    raise PatchError(f'{path} must contain exactly one .sqlite database (found {len(members)})')
                temporary = tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False)
                with archive.open(members[0]) as source:
                    shutil.copyfileobj(source, temporary)
                temporary.close()
        except (OSError, BadZipFile) as exc:
            raise PatchError(f'cannot read SQLite zip {path}: {exc}') from exc
        db_path = temporary.name
    else:
        db_path = path
    connection = None
    try:
        connection = sqlite3.connect(db_path)
        yield connection
    except sqlite3.DatabaseError as exc:
        raise PatchError(f'cannot read SQLite database {path}: {exc}') from exc
    finally:
        if connection is not None:
            connection.close()
        if temporary is not None:
            Path(temporary.name).unlink(missing_ok=True)


def _quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def _tables(connection):
    return {
        name: sql
        for name, sql in connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        if not name.startswith('sqlite_')
    }


def _normalized_sql(sql):
    return re.sub(r'\s+', ' ', sql or '').strip()


def _columns(connection, table):
    quoted = _quote_identifier(table)
    return [row[1] for row in connection.execute(f'PRAGMA table_info({quoted})')]


def _rows(connection, table, columns):
    quoted = _quote_identifier(table)
    selected = ', '.join(_quote_identifier(column) for column in columns)
    query = f'SELECT {selected} FROM {quoted}' if columns else f'SELECT * FROM {quoted}'
    return [tuple(row) for row in connection.execute(query)]


def _row_json(row):
    return [_json_bytes(value) for value in row]


def _multiset_difference(left, right, compared=None):
    """Rows of left missing from right, comparing only the column indexes in compared (all if None)."""
    def key(row):
        return row if compared is None else tuple(row[index] for index in compared)

    remaining = Counter(key(row) for row in right)
    difference = []
    for row in left:
        row_key = key(row)
        if remaining[row_key]:
            remaining[row_key] -= 1
        else:
            difference.append(_row_json(row))
    return difference


def _schema_objects(connection, object_type):
    return [
        {'name': name, 'sql': sql}
        for name, sql in connection.execute(
            'SELECT name, sql FROM sqlite_master WHERE type=? AND sql IS NOT NULL ORDER BY name',
            (object_type,),
        )
    ]


def build_table_changes(base, new):
    base_tables = _tables(base)
    new_tables = _tables(new)
    changes = []
    for name in sorted(base_tables.keys() | new_tables.keys()):
        if name not in new_tables:
            changes.append({'name': name, 'action': 'drop'})
            continue
        new_columns = _columns(new, name)
        new_rows = _rows(new, name, new_columns)
        if name not in base_tables or _normalized_sql(base_tables[name]) != _normalized_sql(new_tables[name]):
            changes.append({
                'name': name,
                'action': 'replace',
                'sql': new_tables[name],
                'columns': new_columns,
                'rows': [_row_json(row) for row in new_rows],
            })
            continue
        base_columns = _columns(base, name)
        base_rows = _rows(base, name, base_columns)
        # wowdata renueva ultima_vez en cada importación aunque el dato no cambie; el companion no la usa,
        # así que una fila que solo cambia ahí se queda como en la base y no viaja en el parche.
        compared = [index for index, column in enumerate(new_columns) if column not in VOLATILE_COLUMNS]
        deleted = _multiset_difference(base_rows, new_rows, compared)
        inserted = _multiset_difference(new_rows, base_rows, compared)
        if deleted or inserted:
            changes.append({
                'name': name,
                'action': 'patch',
                'columns': new_columns,
                'delete': deleted,
                'insert': inserted,
            })
    return changes


def _database_document(tables, views=(), indexes=()):
    return {'tables': tables, 'views': list(views), 'indexes': list(indexes)}


def _document_size(document):
    return len(wrap_json(document).encode('utf-8'))


def _entry_layout(entry):
    """Return a serialized empty-entry size and one encoded size per row."""
    row_fields = ('rows',) if entry['action'] == 'replace' else (
        ('delete', 'insert') if entry['action'] == 'patch' else ()
    )
    empty = dict(entry)
    row_sizes = {}
    for field in row_fields:
        rows = entry[field]
        empty[field] = []
        row_sizes[field] = [len(_encode_json(row).encode('utf-8')) for row in rows]
    header_size = len(_encode_json(empty).encode('utf-8'))
    return header_size, row_sizes


def _entry_size(header_size, row_sizes):
    size = header_size
    for lengths in row_sizes.values():
        size += sum(lengths) + max(0, len(lengths) - 1)
    return size


def _document_overhead(views, indexes):
    return len(wrap_json(_database_document([], views, indexes)).encode('utf-8'))


def _packed_document_size(entry_sizes, overhead):
    return overhead + sum(entry_sizes) + max(0, len(entry_sizes) - 1)


def _split_rows_entry_sized(entry, layout, max_size, overhead):
    """Split a large entry incrementally; continuation rows are patches."""
    header_size, row_sizes = layout
    action = entry['action']
    if action == 'drop':
        return [(entry, header_size)]

    if action == 'replace':
        rows = entry['rows']
        if not rows:
            return [(entry, header_size)]
        first_header, _ = _entry_layout({**entry, 'rows': []})
        continuation = {
            'name': entry['name'], 'action': 'patch', 'columns': entry['columns'],
            'delete': [], 'insert': [],
        }
        continuation_header, _ = _entry_layout(continuation)
        parts = []
        group = []
        group_size = first_header
        first_part = True
        for row, row_size in zip(rows, row_sizes['rows']):
            if group and overhead + group_size + row_size + 1 > max_size:
                if first_part:
                    part = {**entry, 'rows': group}
                else:
                    part = {**continuation, 'insert': group}
                parts.append((part, group_size))
                group = []
                group_size = continuation_header
                first_part = False
            group.append(row)
            group_size += row_size + (1 if len(group) > 1 else 0)
        if group:
            if first_part:
                part = {**entry, 'rows': group}
            else:
                part = {**continuation, 'insert': group}
            parts.append((part, group_size))
        return parts

    chunks = []
    current = {'name': entry['name'], 'action': 'patch', 'columns': entry['columns'], 'delete': [], 'insert': []}
    current_size = header_size
    for operation in ('delete', 'insert'):
        for row, row_size in zip(entry[operation], row_sizes[operation]):
            added_size = row_size + (1 if current[operation] else 0)
            if (current['delete'] or current['insert']) and overhead + current_size + added_size > max_size:
                chunks.append((current, current_size))
                current = {
                    'name': entry['name'], 'action': 'patch', 'columns': entry['columns'],
                    'delete': [], 'insert': [],
                }
                current_size = header_size
                added_size = row_size
            current[operation].append(row)
            current_size += added_size
    if current['delete'] or current['insert']:
        chunks.append((current, current_size))
    return chunks


def build_database_documents(base, new, max_file_size=DEFAULT_FILE_SIZE):
    changes = build_table_changes(base, new)
    views = _schema_objects(new, 'view')
    indexes = _schema_objects(new, 'index')
    documents = []
    current = []
    current_payload_size = 0
    current_overhead = _document_overhead(views, indexes)
    metadata_pending = True

    def metadata():
        return (views, indexes) if metadata_pending else ((), ())

    def flush():
        nonlocal current, current_payload_size, current_overhead, metadata_pending
        documents.append(_database_document(current, *metadata()))
        current = []
        current_payload_size = 0
        metadata_pending = False
        current_overhead = _document_overhead(*metadata())

    for entry in changes:
        layout = _entry_layout(entry)
        entry_size = _entry_size(*layout)
        separator_size = 1 if current else 0
        if current_overhead + current_payload_size + separator_size + entry_size <= max_file_size:
            current.append(entry)
            current_payload_size += separator_size + entry_size
            continue
        if current:
            flush()
            if current_overhead + entry_size <= max_file_size:
                current.append(entry)
                current_payload_size = entry_size
                continue

        parts = _split_rows_entry_sized(entry, layout, max_file_size, current_overhead)
        for part, part_size in parts:
            separator_size = 1 if current else 0
            if current and current_overhead + current_payload_size + separator_size + part_size > max_file_size:
                flush()
                separator_size = 0
            current.append(part)
            current_payload_size += separator_size + part_size

    if current or not documents:
        flush()
    return documents, changes


def load_guide(guide_dir):
    guide_dir = Path(guide_dir)
    paths = [guide_dir / 'guide.json'] + sorted((guide_dir / 'guide').glob('*.json'))
    contents = {}
    for path in paths:
        if not path.is_file():
            if path.name == 'guide.json':
                raise PatchError(f'missing guide file: {path}')
            continue
        relative = 'guide.json' if path.parent == guide_dir else path.name
        try:
            contents[relative] = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise PatchError(f'cannot read guide JSON {path}: {exc}') from exc
    return {'files': contents}


def _write_outputs(out_dir, guide, documents, manifest):
    out_dir.mkdir(parents=True, exist_ok=True)
    # Validate every output before removing any previous generated file.
    rendered = {'manifest.lua': wrap_json(manifest), 'guide.lua': wrap_json(guide)}
    for index, document in enumerate(documents, 1):
        rendered[f'db-{index:03d}.lua'] = wrap_json(document)
    for path in out_dir.glob('db-*.lua'):
        if path.is_file():
            path.unlink()
    for name in ('manifest.lua', 'guide.lua'):
        path = out_dir / name
        if path.is_file():
            path.unlink()
    for name, text in rendered.items():
        (out_dir / name).write_text(text, encoding='utf-8', newline='')
    return {name: len(text.encode('utf-8')) for name, text in rendered.items()}


def generate(args, max_file_size=DEFAULT_FILE_SIZE):
    base_path = args.base
    if args.download_base:
        if base_path:
            raise PatchError('--base cannot be used together with --download-base')
        if not args.cache:
            raise PatchError('--cache is required with --download-base')
        base_path, base_sha256 = _download_base(args.base_tag, Path(args.cache))
    else:
        if not base_path:
            raise PatchError('provide --base or use --download-base')
        base_path = Path(base_path)
        if args.base_sha256:
            base_sha256 = args.base_sha256.lower()
            if not HASH_RE.fullmatch(base_sha256):
                raise PatchError('--base-sha256 must be 64 hexadecimal characters')
            if base_path.suffix.lower() == '.zip':
                actual = _sha256(base_path)
                if actual.lower() != base_sha256:
                    raise PatchError(f'SHA-256 mismatch for base zip: expected {base_sha256}, got {actual}')
        elif base_path.suffix.lower() == '.zip':
            base_sha256 = _sha256(base_path)
        else:
            raise PatchError('--base-sha256 is required when --base is a SQLite file')

    with _open_database(base_path) as base, _open_database(args.new) as new:
        documents, changes = build_database_documents(base, new, max_file_size=max_file_size)
    guide = load_guide(args.guide)
    db_files = [f'db-{index:03d}.lua' for index in range(1, len(documents) + 1)]
    manifest = {
        'format': 1,
        'patch': args.patch,
        'base': args.base_tag,
        'base_sha256': base_sha256,
        'guide': 'guide.lua',
        'db': db_files,
        'generated': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
    }
    sizes = _write_outputs(Path(args.out), guide, documents, manifest)
    action_counts = Counter(entry['action'] for entry in changes)
    row_count = sum(
        len(entry.get('rows', ())) + len(entry.get('delete', ())) + len(entry.get('insert', ()))
        for entry in changes
    )
    total_size = sum(sizes.values())
    print(
        f"Tables: {action_counts['patch']} patched, {action_counts['replace']} replaced, "
        f"{action_counts['drop']} dropped; rows: {row_count}; total size: {total_size:,} bytes"
    )
    if total_size > WARN_TOTAL_SIZE:
        print('Warning: output exceeds 25 MB; publish a new base instead.', file=sys.stderr)


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', help='base SQLite file or wow.sqlite.zip')
    parser.add_argument('--base-tag', required=True, help='published base release tag')
    parser.add_argument('--base-sha256', help='SHA-256 of the published base zip')
    parser.add_argument('--download-base', action='store_true', help='download the base zip and checksum')
    parser.add_argument('--cache', help='folder for a downloaded base release')
    parser.add_argument('--new', required=True, help='new wow.sqlite database')
    parser.add_argument('--guide', required=True, help='companion data folder containing guide.json')
    parser.add_argument('--out', required=True, help='addon data output folder')
    parser.add_argument('--patch', required=True, help='patch version')
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        generate(args)
    except (PatchError, OSError, sqlite3.DatabaseError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
