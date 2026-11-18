import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import time
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('make_data_patch', ROOT / 'scripts' / 'make_data_patch.py')
patcher = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = patcher
spec.loader.exec_module(patcher)


def _database(path, statements=(), rows=()):
    connection = sqlite3.connect(path)
    connection.executescript(';\n'.join(statements))
    for table, values in rows:
        placeholders = ','.join('?' for _ in values[0])
        connection.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', values)
    connection.commit()
    connection.close()
    return path


def _payload(path):
    text = path.read_text(encoding='utf-8')
    assert text.startswith(patcher.WRAPPER_HEADER)
    assert text.endswith(patcher.WRAPPER_FOOTER)
    return json.loads(text[len(patcher.WRAPPER_HEADER):-len(patcher.WRAPPER_FOOTER)])


def test_patch_rows_preserves_duplicate_multiset_and_encodes_bytes(tmp_path):
    base_path = _database(
        tmp_path / 'base.sqlite', ['CREATE TABLE item (value BLOB)'],
        [('item', [(b'old',), (b'duplicate',), (b'duplicate',)])],
    )
    new_path = _database(
        tmp_path / 'new.sqlite', ['CREATE TABLE item (value BLOB)'],
        [('item', [(b'duplicate',), (b'new',), (b'new',)])],
    )
    with patcher._open_database(base_path) as base, patcher._open_database(new_path) as new:
        documents, changes = patcher.build_database_documents(base, new)
    change = changes[0]
    assert change['action'] == 'patch'
    assert change['delete'] == [[{'b64': 'b2xk'}], [{'b64': 'ZHVwbGljYXRl'}]]
    assert change['insert'] == [[{'b64': 'bmV3'}], [{'b64': 'bmV3'}]]
    assert documents[0]['tables'] == changes


def test_rows_differing_only_in_ultima_vez_are_not_patched(tmp_path):
    schema = ['CREATE TABLE obs (id INTEGER, name TEXT, ultima_vez TEXT)']
    base_path = _database(tmp_path / 'base.sqlite', schema,
                          [('obs', [(1, 'a', '2026-11-17'), (2, 'b', '2026-11-17')])])
    new_path = _database(tmp_path / 'new.sqlite', schema,
                         [('obs', [(1, 'a', '2026-11-18'), (2, 'c', '2026-11-18')])])
    with patcher._open_database(base_path) as base, patcher._open_database(new_path) as new:
        _documents, changes = patcher.build_database_documents(base, new)
    assert len(changes) == 1
    assert changes[0]['delete'] == [[2, 'b', '2026-11-17']]
    assert changes[0]['insert'] == [[2, 'c', '2026-11-18']]


def test_replaced_new_and_dropped_tables_and_schema_objects(tmp_path):
    base_path = _database(tmp_path / 'base.sqlite', [
        'CREATE TABLE changed (value TEXT)', 'CREATE TABLE removed (id INTEGER)',
    ])
    new_path = _database(tmp_path / 'new.sqlite', [
        'CREATE TABLE changed (value TEXT, extra INTEGER)',
        'CREATE TABLE added (id INTEGER)',
        'CREATE VIEW visible AS SELECT id FROM added',
        'CREATE INDEX added_idx ON added(id)',
    ], [('changed', [('v', 3)]), ('added', [(8,)])])
    with patcher._open_database(base_path) as base, patcher._open_database(new_path) as new:
        documents, changes = patcher.build_database_documents(base, new)
    by_name = {entry['name']: entry for entry in changes}
    assert by_name['changed']['action'] == 'replace'
    assert by_name['changed']['rows'] == [['v', 3]]
    assert by_name['added']['action'] == 'replace'
    assert by_name['removed']['action'] == 'drop'
    assert documents[0]['views'] == [{'name': 'visible', 'sql': 'CREATE VIEW visible AS SELECT id FROM added'}]
    assert documents[0]['indexes'] == [{'name': 'added_idx', 'sql': 'CREATE INDEX added_idx ON added(id)'}]


def test_wrapper_rejects_terminator():
    with pytest.raises(patcher.PatchError, match='forbidden'):
        patcher.wrap_json({'value': 'unsafe ]==] content'})


def test_large_table_is_split_and_repeated_as_patch(tmp_path):
    base_path = _database(tmp_path / 'base.sqlite', ['CREATE TABLE stuff (value TEXT)'])
    new_path = _database(
        tmp_path / 'new.sqlite', ['CREATE TABLE stuff (value TEXT)'],
        [('stuff', [(f'row-{index}-' + 'x' * 35,) for index in range(20)])],
    )
    with patcher._open_database(base_path) as base, patcher._open_database(new_path) as new:
        documents, _changes = patcher.build_database_documents(base, new, max_file_size=260)
    assert len(documents) > 1
    entries = [entry for document in documents for entry in document['tables']]
    assert entries[0]['action'] == 'patch'
    assert all(entry['action'] == 'patch' for entry in entries)
    assert sum(len(entry['insert']) for entry in entries) == 20


def test_split_200000_rows_finishes_quickly():
    entry = {
        'name': 'large', 'action': 'patch', 'columns': ['value'], 'delete': [],
        'insert': [[f'row-{index}'] for index in range(200_000)],
    }
    max_size = 256 * 1024
    overhead = patcher._document_overhead([], [])
    layout = patcher._entry_layout(entry)

    started = time.perf_counter()
    parts = patcher._split_rows_entry_sized(entry, layout, max_size, overhead)
    elapsed = time.perf_counter() - started

    assert len(parts) > 1
    assert sum(len(part['insert']) for part, _size in parts) == 200_000
    assert all(patcher._packed_document_size([size], overhead) <= max_size for _part, size in parts)
    assert elapsed < 5


def test_guide_files_are_collected_and_outputs_have_expected_manifest(tmp_path):
    guide_dir = tmp_path / 'guide-data'
    (guide_dir / 'guide').mkdir(parents=True)
    (guide_dir / 'guide.json').write_text('{"sections":[]}', encoding='utf-8')
    (guide_dir / 'guide' / '04-clase-mage.json').write_text('{"class":"mage"}', encoding='utf-8')
    guide = patcher.load_guide(guide_dir)
    assert guide == {'files': {'guide.json': {'sections': []}, '04-clase-mage.json': {'class': 'mage'}}}

    base_path = _database(tmp_path / 'base.sqlite')
    new_path = _database(tmp_path / 'new.sqlite')
    out = tmp_path / 'out'
    args = patcher._parser().parse_args([
        '--base', str(base_path), '--base-tag', 'data-2026.11.14', '--base-sha256', 'a' * 64,
        '--new', str(new_path), '--guide', str(guide_dir), '--out', str(out), '--patch', '2026.11.18.1',
    ])
    patcher.generate(args)
    manifest = _payload(out / 'manifest.lua')
    assert manifest['format'] == 1
    assert manifest['db'] == ['db-001.lua']
    assert _payload(out / 'guide.lua') == guide
    assert _payload(out / manifest['db'][0]) == {'tables': [], 'views': [], 'indexes': []}


def test_zip_base_hash_is_computed_from_archive(tmp_path):
    db_path = _database(tmp_path / 'base.sqlite')
    archive_path = tmp_path / 'base.zip'
    with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.write(db_path, 'wow.sqlite')
    with patcher._open_database(archive_path) as connection:
        assert connection.execute('SELECT 1').fetchone() == (1,)
    assert len(patcher._sha256(archive_path)) == 64


def test_help_is_available(capsys):
    with pytest.raises(SystemExit) as error:
        patcher.main(['--help'])
    assert error.value.code == 0
    assert '--download-base' in capsys.readouterr().out
