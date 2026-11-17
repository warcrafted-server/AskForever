"""Tests for addon-shipped guide and database patches."""

from __future__ import annotations

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import time
import zipfile

import pytest

from askforever.data import patch


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = ROOT / 'scripts' / 'make_data_patch.py'
_spec = importlib.util.spec_from_file_location('make_data_patch', GENERATOR_PATH)
generator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generator)


def _database(path, statements):
    connection = sqlite3.connect(path)
    try:
        connection.executescript(statements)
        connection.commit()
    finally:
        connection.close()
    return Path(path)


def _wrapped(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generator.wrap_json(value), encoding='utf-8')
    return path


def _manifest(addon, *, patch_version='2026.11.18.1', base='data-2026.11.14',
              base_sha=None, guide='guide.lua', db=None):
    if base_sha is None:
        base_sha = 'a' * 64
    value = {
        'format': 1,
        'patch': patch_version,
        'base': base,
        'base_sha256': base_sha,
        'guide': guide,
        'db': ['db-001.lua'] if db is None else db,
        'generated': '2026-11-18T00:00:00Z',
    }
    _wrapped(Path(addon) / 'manifest.lua', value)
    return value


def _zip_database(database, target):
    with zipfile.ZipFile(target, 'w') as archive:
        archive.write(database, 'wow.sqlite')
    return Path(target).read_bytes()


def test_read_wrapped_json_validates_wrapper_and_json(tmp_path):
    path = _wrapped(tmp_path / 'good.lua', {'files': {'guide.json': {'x': 1}}})
    assert patch.read_wrapped_json(path) == {'files': {'guide.json': {'x': 1}}}
    for contents in ('return {"bad": true}', 'return [==[{]==]', 'return [==[[]==]'):
        bad = tmp_path / 'bad.lua'
        bad.write_text(contents, encoding='utf-8')
        with pytest.raises(patch.PatchError):
            patch.read_wrapped_json(bad)


def test_load_manifest_checks_required_fields_and_safe_filenames(tmp_path):
    _manifest(tmp_path)
    assert patch.load_manifest(tmp_path)['format'] == 1
    _wrapped(tmp_path / 'manifest.lua', {'format': 2})
    with pytest.raises(patch.PatchError):
        patch.load_manifest(tmp_path)
    invalid = {
        'format': 1, 'patch': 'p', 'base': 'b', 'base_sha256': 'a' * 64,
        'guide': '../guide.lua', 'db': [], 'generated': 'now',
    }
    _wrapped(tmp_path / 'manifest.lua', invalid)
    with pytest.raises(patch.PatchError):
        patch.load_manifest(tmp_path)


def test_find_addon_data_dir_precedence(tmp_path, monkeypatch):
    game = tmp_path / 'Wow.exe'
    dev = tmp_path / 'Interface' / 'AddOns' / 'AskForeverDev' / 'data'
    prod = tmp_path / 'Interface' / 'AddOns' / 'AskForever' / 'data'
    _wrapped(dev / 'manifest.lua', {})
    _wrapped(prod / 'manifest.lua', {})
    override = tmp_path / 'override'
    _wrapped(override / 'manifest.lua', {})
    monkeypatch.setenv('ASKFOREVER_ADDON_DIR', str(override))
    assert patch.find_addon_data_dir(game) == override
    (override / 'manifest.lua').unlink()
    assert patch.find_addon_data_dir(game) == dev
    (dev / 'manifest.lua').unlink()
    assert patch.find_addon_data_dir(game) == prod
    assert patch.find_addon_data_dir(None) is None


def test_ensure_base_downloads_and_checks_sha(tmp_path):
    database = _database(tmp_path / 'source.sqlite', 'CREATE TABLE t (x); INSERT INTO t VALUES (1);')
    archive = _zip_database(database, tmp_path / 'base.zip')
    digest = hashlib.sha256(archive).hexdigest()
    calls = []

    def download(url, target, progress=None):
        calls.append(url)
        target.write_bytes(archive)

    result = patch.ensure_base('data-2026.11.14', digest, tmp_path / 'cache', download)
    assert result.name == 'base-data-2026.11.14.sqlite'
    assert calls[0].endswith('/data-2026.11.14/wow.sqlite.zip')
    with pytest.raises(patch.PatchError, match='SHA-256 mismatch'):
        patch.ensure_base('data-2026.11.15', '0' * 64, tmp_path / 'cache', download)
    assert not (tmp_path / 'cache' / 'base-data-2026.11.15.sqlite').exists()


def _snapshot(path):
    connection = sqlite3.connect(path)
    try:
        tables = {}
        for name, sql in connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            tables[name] = (sql, Counter(tuple(row) for row in connection.execute(
                f'SELECT * FROM "{name.replace(chr(34), chr(34) * 2)}"')))
        views = dict(connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='view' AND sql IS NOT NULL"))
        indexes = dict(connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"))
        return tables, views, indexes
    finally:
        connection.close()


def test_rebuild_matches_generator_patch_for_tables_views_indexes_and_bytes(tmp_path):
    base = _database(tmp_path / 'base.sqlite', """
        CREATE TABLE repeated (v TEXT, b BLOB);
        INSERT INTO repeated VALUES ('same', X'01');
        INSERT INTO repeated VALUES ('same', X'01');
        INSERT INTO repeated VALUES ('gone', NULL);
        CREATE TABLE replaced (old TEXT);
        INSERT INTO replaced VALUES ('old');
        CREATE TABLE removed (id INTEGER);
        CREATE INDEX old_index ON repeated(v);
        CREATE VIEW old_view AS SELECT v FROM repeated;
    """)
    new = _database(tmp_path / 'new.sqlite', """
        CREATE TABLE repeated (v TEXT, b BLOB);
        INSERT INTO repeated VALUES ('same', X'01');
        INSERT INTO repeated VALUES ('new', X'FF00');
        CREATE TABLE replaced (id INTEGER PRIMARY KEY, value TEXT);
        INSERT INTO replaced VALUES (4, 'new schema');
        CREATE INDEX new_index ON repeated(b);
        CREATE VIEW new_view AS SELECT value FROM replaced;
    """)
    base_db = sqlite3.connect(base)
    new_db = sqlite3.connect(new)
    try:
        documents, _changes = generator.build_database_documents(base_db, new_db)
    finally:
        base_db.close()
        new_db.close()

    addon = tmp_path / 'addon'
    addon.mkdir()
    names = []
    for index, document in enumerate(documents, 1):
        name = f'db-{index:03d}.lua'
        names.append(name)
        _wrapped(addon / name, document)
    manifest = _manifest(addon, db=names)
    target = tmp_path / 'output.sqlite'
    patch.rebuild(base, addon, manifest, target)
    assert _snapshot(target) == _snapshot(new)


def test_rebuild_keeps_first_nonempty_views_and_indexes_across_files(tmp_path):
    base = _database(tmp_path / 'base.sqlite', 'CREATE TABLE t (value); INSERT INTO t VALUES (1);')
    addon = tmp_path / 'addon'
    addon.mkdir()
    names = ['db-001.lua', 'db-002.lua']
    _wrapped(addon / names[0], {
        'tables': [],
        'indexes': [{'sql': 'CREATE INDEX first_index ON t(value)'}],
        'views': [{'sql': 'CREATE VIEW first_view AS SELECT value FROM t'}],
    })
    _wrapped(addon / names[1], {'tables': [], 'indexes': [], 'views': []})

    target = tmp_path / 'output.sqlite'
    patch.rebuild(base, addon, _manifest(addon, db=names), target)
    connection = sqlite3.connect(target)
    try:
        objects = set(connection.execute(
            "SELECT type, name FROM sqlite_master WHERE type IN ('view', 'index')"))
    finally:
        connection.close()
    assert ('index', 'first_index') in objects
    assert ('view', 'first_view') in objects


def test_rebuild_deletes_50000_rows_quickly(tmp_path):
    base = tmp_path / 'base.sqlite'
    connection = sqlite3.connect(base)
    try:
        connection.execute('CREATE TABLE t (value INTEGER)')
        connection.executemany('INSERT INTO t VALUES (?)', ((i,) for i in range(50000)))
        connection.commit()
    finally:
        connection.close()

    addon = tmp_path / 'addon'
    addon.mkdir()
    _wrapped(addon / 'db-001.lua', {
        'tables': [{
            'name': 't',
            'action': 'patch',
            'columns': ['value'],
            'delete': [[i] for i in range(50000)],
            'insert': [],
        }],
        'indexes': [],
        'views': [],
    })

    started = time.perf_counter()
    target = tmp_path / 'output.sqlite'
    patch.rebuild(base, addon, _manifest(addon), target)
    elapsed = time.perf_counter() - started
    connection = sqlite3.connect(target)
    try:
        assert connection.execute('SELECT COUNT(*) FROM t').fetchone()[0] == 0
    finally:
        connection.close()
    assert elapsed < 10, f'50,000 deletes took {elapsed:.2f} seconds'


def test_rebuild_rolls_back_and_keeps_existing_target(tmp_path):
    base = _database(tmp_path / 'base.sqlite', 'CREATE TABLE t (value); INSERT INTO t VALUES (1);')
    target = _database(tmp_path / 'target.sqlite', 'CREATE TABLE original (value); INSERT INTO original VALUES (7);')
    addon = tmp_path / 'addon'
    addon.mkdir()
    _wrapped(addon / 'db-001.lua', {'tables': [{'name': 't', 'action': 'nonsense'}]})
    manifest = _manifest(addon)
    before = target.read_bytes()
    with pytest.raises(patch.PatchError):
        patch.rebuild(base, addon, manifest, target)
    assert target.read_bytes() == before
    assert not Path(str(target) + '.bak').exists()
    assert not list(tmp_path.glob('.target.sqlite-*.tmp'))


def test_sync_states_and_guide_patch_content(tmp_path, monkeypatch):
    addon = tmp_path / 'addon'
    addon.mkdir()
    guide = {'files': {'guide.json': {'sections': [{'name': 'new'}]}}}
    _wrapped(addon / 'guide.lua', guide)
    base_db = _database(tmp_path / 'source.sqlite', 'CREATE TABLE t (value); INSERT INTO t VALUES (1);')
    archive = _zip_database(base_db, tmp_path / 'base.zip')
    digest = hashlib.sha256(archive).hexdigest()
    _manifest(addon, base_sha=digest)
    _wrapped(addon / 'db-001.lua', {'tables': [], 'views': [], 'indexes': []})
    monkeypatch.setenv('ASKFOREVER_ADDON_DIR', str(addon))

    data_dir = tmp_path / 'managed'
    def download(url, target, progress=None):
        target.write_bytes(archive)

    assert patch.sync(data_dir=data_dir, managed=True, download=download) == ('patched', '2026.11.18.1')
    assert patch.sync(data_dir=data_dir, managed=True, download=download) == ('current', '2026.11.18.1')
    guide_payload = json.loads((data_dir / 'guide-patch.json').read_text(encoding='utf-8'))
    assert guide_payload == {'patch': '2026.11.18.1', 'files': guide['files']}

    dev_data = tmp_path / 'development'
    assert patch.sync(data_dir=dev_data, managed=False) == ('guide-only', '2026.11.18.1')
    assert json.loads((dev_data / 'guide-patch.json').read_text(encoding='utf-8')) == guide_payload


def test_sync_returns_none_and_error_without_raising(tmp_path, monkeypatch):
    monkeypatch.delenv('ASKFOREVER_ADDON_DIR', raising=False)
    assert patch.sync(data_dir=tmp_path / 'none', managed=True) == ('none', '')
    addon = tmp_path / 'broken'
    _wrapped(addon / 'manifest.lua', {
        'format': 99, 'patch': 'p', 'base': 'b', 'base_sha256': 'a' * 64,
        'guide': 'guide.lua', 'db': [], 'generated': 'now',
    })
    monkeypatch.setenv('ASKFOREVER_ADDON_DIR', str(addon))
    status, reason = patch.sync(data_dir=tmp_path / 'bad', managed=True)
    assert status == 'error'
    assert 'unsupported manifest format' in reason
