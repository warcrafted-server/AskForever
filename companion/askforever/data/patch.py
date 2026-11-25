"""Read and apply the database patch shipped with the game addon."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from askforever import config, paths, updates


class PatchError(Exception):
    """An addon data patch is invalid or could not be applied."""


_SHA256_RE = re.compile(r'^[0-9a-fA-F]{64}$')
_TAG_RE = re.compile(r'^[A-Za-z0-9._-]+$')
_OPEN = 'return [==['
_CLOSE = ']==]'


def read_wrapped_json(path) -> dict:
    """Read the JSON body from a Lua long-string data file."""
    try:
        text = Path(path).read_text(encoding='utf-8')
    except (OSError, UnicodeError) as error:
        raise PatchError(f'cannot read {path}: {error}') from error
    start = text.find(_OPEN)
    end = text.find(_CLOSE, start + len(_OPEN)) if start >= 0 else -1
    if start < 0 or end < 0 or text.find(_OPEN, start + len(_OPEN)) >= 0:
        raise PatchError(f'invalid data wrapper: {path}')
    try:
        payload = json.loads(text[start + len(_OPEN):end].strip())
    except (json.JSONDecodeError, ValueError) as error:
        raise PatchError(f'invalid JSON in {path}: {error}') from error
    if not isinstance(payload, dict):
        raise PatchError(f'expected a JSON object in {path}')
    return payload


def _safe_file_name(name) -> bool:
    return (isinstance(name, str) and bool(name) and name not in ('.', '..')
            and Path(name).name == name and '/' not in name and '\\' not in name)


def _addon_data_in(game_dir: Path) -> Optional[Path]:
    for addon_name in ('AskForeverDev', 'AskForever'):
        candidate = game_dir / 'Interface' / 'AddOns' / addon_name / 'data'
        if (candidate / 'manifest.lua').is_file():
            return candidate
    return None


def find_addon_data_dir(exe_path=None) -> Optional[Path]:
    """Locate addon data, preferring the explicit environment override."""
    override = os.environ.get('ASKFOREVER_ADDON_DIR')
    if override:
        candidate = Path(override)
        if (candidate / 'manifest.lua').is_file():
            return candidate
    if exe_path:
        found = _addon_data_in(Path(exe_path).parent)
        if found is not None:
            return found
    # Empaquetado en Linux el juego está junto al programa y puede estar cerrado.
    game_dir = paths.portable_game_dir()
    if game_dir is not None:
        return _addon_data_in(game_dir)
    return None


def load_manifest(addon_dir) -> dict:
    """Read and validate the addon's manifest and all referenced filenames."""
    path = Path(addon_dir) / 'manifest.lua'
    manifest = read_wrapped_json(path)
    required = ('format', 'patch', 'base', 'base_sha256', 'guide', 'db', 'generated')
    if any(key not in manifest for key in required):
        raise PatchError('manifest is missing required keys')
    if isinstance(manifest['format'], bool) or manifest['format'] != 1:
        raise PatchError('unsupported manifest format')
    if (not isinstance(manifest['patch'], str) or not manifest['patch']
            or not isinstance(manifest['base'], str)
            or not _TAG_RE.fullmatch(manifest['base'])):
        raise PatchError('invalid patch or base version in manifest')
    if (not isinstance(manifest['base_sha256'], str)
            or not _SHA256_RE.fullmatch(manifest['base_sha256'])):
        raise PatchError('invalid base SHA-256 in manifest')
    if not _safe_file_name(manifest['guide']):
        raise PatchError('invalid guide filename in manifest')
    if (not isinstance(manifest['db'], list)
            or any(not _safe_file_name(name) for name in manifest['db'])
            or len(set(manifest['db'])) != len(manifest['db'])):
        raise PatchError('invalid database filenames in manifest')
    if not isinstance(manifest['generated'], str):
        raise PatchError('invalid generated timestamp in manifest')
    return manifest


def ensure_base(tag, sha256, data_dir, download=None, progress=None) -> Path:
    """Download and verify the clean database base if it is not cached."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    if not isinstance(tag, str) or not _TAG_RE.fullmatch(tag):
        raise PatchError('invalid base release tag')
    if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
        raise PatchError('invalid base SHA-256')
    target = data_dir / f'base-{tag}.sqlite'
    if target.is_file():
        return target

    handle, zip_name = tempfile.mkstemp(prefix='.base-', suffix='.zip', dir=data_dir)
    os.close(handle)
    archive = Path(zip_name)
    handle, database_name = tempfile.mkstemp(prefix='.base-', suffix='.sqlite', dir=data_dir)
    os.close(handle)
    database = Path(database_name)
    url = ('https://github.com/warcrafted-server/AskForever/releases/download/'
           f'{quote(tag, safe="-.")}/wow.sqlite.zip')
    try:
        updates._call_download(download, url, archive, progress)
        actual = updates._sha256_file(archive)
        if actual.lower() != sha256.lower():
            raise PatchError('base SHA-256 mismatch')
        updates._extract_database(archive, database)
        updates._validate_database(database)
        os.replace(database, target)
        return target
    except PatchError:
        raise
    except Exception as error:
        raise PatchError(f'could not prepare base {tag}: {error}') from error
    finally:
        for temporary in (archive, database):
            try:
                temporary.unlink()
            except OSError:
                pass


def _quote_identifier(name) -> str:
    if not isinstance(name, str) or not name:
        raise PatchError('invalid SQLite identifier in patch')
    return '"' + name.replace('"', '""') + '"'


def _decode(value):
    if isinstance(value, dict) and set(value) == {'b64'}:
        encoded = value['b64']
        if not isinstance(encoded, str):
            raise PatchError('invalid base64 value in patch')
        try:
            return base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as error:
            raise PatchError('invalid base64 value in patch') from error
    return value


def _rows_for_insert(connection, table, columns, rows):
    if not isinstance(columns, list) or not isinstance(rows, list):
        raise PatchError(f'invalid row data for table {table}')
    table_sql = _quote_identifier(table)
    column_sql = ', '.join(_quote_identifier(column) for column in columns)
    if columns:
        sql = f'INSERT INTO {table_sql} ({column_sql}) VALUES ({", ".join("?" for _ in columns)})'
    else:
        sql = f'INSERT INTO {table_sql} DEFAULT VALUES'
    for row in rows:
        if not isinstance(row, list) or len(row) != len(columns):
            raise PatchError(f'invalid row width for table {table}')
        values = tuple(_decode(value) for value in row)
        if columns:
            connection.execute(sql, values)
        else:
            connection.execute(sql)


def _apply_table(connection, entry):
    if not isinstance(entry, dict):
        raise PatchError('invalid table entry in patch')
    table = entry.get('name')
    table_sql = _quote_identifier(table)
    action = entry.get('action')
    if action == 'drop':
        connection.execute(f'DROP TABLE IF EXISTS {table_sql}')
    elif action == 'replace':
        create_sql = entry.get('sql')
        if not isinstance(create_sql, str) or not create_sql:
            raise PatchError(f'missing CREATE statement for table {table}')
        connection.execute(f'DROP TABLE IF EXISTS {table_sql}')
        connection.execute(create_sql)
        _rows_for_insert(connection, table, entry.get('columns'), entry.get('rows'))
    elif action == 'patch':
        columns = entry.get('columns')
        if not isinstance(columns, list) or not columns:
            raise PatchError(f'invalid patch columns for table {table}')
        where = ' AND '.join(f'{_quote_identifier(column)} IS ?' for column in columns)
        delete_sql = (f'DELETE FROM {table_sql} WHERE rowid IN '
                      f'(SELECT rowid FROM {table_sql} WHERE {where} LIMIT 1)')
        deletes = entry.get('delete', [])
        temporary_index = None
        if len(deletes) > 100:
            existing_names = {row[0] for row in connection.execute(
                'SELECT name FROM sqlite_master')}
            index_name = '__askforever_patch_tmp'
            suffix = 1
            while index_name in existing_names:
                index_name = f'__askforever_patch_tmp_{suffix}'
                suffix += 1
            temporary_index = _quote_identifier(index_name)
            index_columns = ', '.join(_quote_identifier(column) for column in columns)
            connection.execute(
                f'CREATE INDEX {temporary_index} ON {table_sql} ({index_columns})')
        try:
            for row in deletes:
                if not isinstance(row, list) or len(row) != len(columns):
                    raise PatchError(f'invalid delete row for table {table}')
                connection.execute(delete_sql, tuple(_decode(value) for value in row))
        finally:
            if temporary_index is not None:
                connection.execute(f'DROP INDEX {temporary_index}')
        _rows_for_insert(connection, table, columns, entry.get('insert', []))
    else:
        raise PatchError(f'unknown table action for {table}')


def _drop_schema_objects(connection, object_type):
    rows = connection.execute(
        'SELECT name FROM sqlite_master WHERE type=? AND sql IS NOT NULL '
        "AND name NOT LIKE 'sqlite_%'", (object_type,)
    ).fetchall()
    keyword = 'VIEW' if object_type == 'view' else 'INDEX'
    for (name,) in rows:
        connection.execute(f'DROP {keyword} IF EXISTS {_quote_identifier(name)}')


def _apply_objects(connection, objects, object_type):
    if not isinstance(objects, list):
        raise PatchError(f'invalid {object_type} list in patch')
    for item in objects:
        if not isinstance(item, dict) or not isinstance(item.get('sql'), str):
            raise PatchError(f'invalid {object_type} entry in patch')
        connection.execute(item['sql'])


def rebuild(base_path, addon_dir, manifest, target_path) -> Path:
    """Build a patched database next to the destination and atomically install it."""
    base_path = Path(base_path)
    addon_dir = Path(addon_dir)
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f'.{target.name}-', suffix='.tmp', dir=target.parent)
    os.close(handle)
    temporary = Path(temporary_name)
    connection = None
    try:
        shutil.copy2(base_path, temporary)
        connection = sqlite3.connect(temporary)
        connection.execute('BEGIN IMMEDIATE')
        # Old schema objects can block same-named indexes and views while tables change.
        _drop_schema_objects(connection, 'view')
        _drop_schema_objects(connection, 'index')
        final_document = {'indexes': [], 'views': []}
        for name in manifest['db']:
            document = read_wrapped_json(addon_dir / name)
            tables = document.get('tables')
            if not isinstance(tables, list):
                raise PatchError(f'invalid tables list in {name}')
            for entry in tables:
                _apply_table(connection, entry)
            for object_type in ('indexes', 'views'):
                if not final_document[object_type] and document.get(object_type):
                    final_document[object_type] = document[object_type]
        _apply_objects(connection, final_document.get('indexes', []), 'indexes')
        _apply_objects(connection, final_document.get('views', []), 'views')
        connection.commit()
        connection.close()
        connection = None
        updates._validate_database(temporary)

        backup = Path(str(target) + '.bak')
        if target.is_file():
            shutil.copy2(target, backup)
        os.replace(temporary, target)
        return target
    except PatchError:
        if connection is not None:
            connection.rollback()
        raise
    except Exception as error:
        if connection is not None:
            connection.rollback()
        raise PatchError(f'could not rebuild database: {error}') from error
    finally:
        if connection is not None:
            connection.close()
        try:
            temporary.unlink()
        except OSError:
            pass


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f'.{path.name}-', suffix='.tmp', dir=path.parent)
    os.close(handle)
    temporary = Path(name)
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n',
                             encoding='utf-8')
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except OSError:
            pass


def sync(exe_path=None, data_dir=None, managed=None, download=None,
         progress=None) -> tuple[str, str]:
    """Synchronize addon guide and, when managed, rebuild its pinned database."""
    try:
        addon_dir = find_addon_data_dir(exe_path)
        if addon_dir is None:
            return 'none', ''
        manifest = load_manifest(addon_dir)
        guide_document = read_wrapped_json(addon_dir / manifest['guide'])
        guide_files = guide_document.get('files')
        if not isinstance(guide_files, dict):
            raise PatchError('invalid guide files in addon patch')

        patch_files = [manifest['guide'], *manifest['db']]
        file_hashes = {}
        for name in patch_files:
            path = addon_dir / name
            if not path.is_file():
                raise PatchError(f'missing addon patch file: {name}')
            file_hashes[name] = updates._sha256_file(path)

        data_dir = Path(data_dir) if data_dir is not None else config.user_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        guide_patch = {'patch': manifest['patch'], 'files': guide_files}
        guide_path = data_dir / 'guide-patch.json'
        try:
            current_guide = json.loads(guide_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            current_guide = None
        if current_guide != guide_patch:
            _atomic_json(guide_path, guide_patch)

        is_managed = config.data_is_managed() if managed is None else bool(managed)
        if not is_managed:
            return 'guide-only', manifest['patch']

        state = {'base': manifest['base'], 'patch': manifest['patch'], 'files': file_hashes}
        state_path = data_dir / 'patch-state.json'
        try:
            current_state = json.loads(state_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            current_state = None
        target = data_dir / 'wow.sqlite'
        if current_state == state and target.is_file():
            return 'current', manifest['patch']

        base = ensure_base(manifest['base'], manifest['base_sha256'], data_dir,
                           download=download, progress=progress)
        rebuild(base, addon_dir, manifest, target)
        _atomic_json(state_path, state)
        return 'patched', manifest['patch']
    except Exception as error:
        return 'error', str(error) or type(error).__name__
