import hashlib
from pathlib import Path
import sqlite3
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts' / 'publish_base.py'


def _git(repo, *args, env=None):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True, env=env).strip()


def _git_bytes(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def _repository(path):
    path.mkdir()
    _git(path, 'init', '-q')
    _git(path, 'config', 'user.name', 'Test User')
    _git(path, 'config', 'user.email', 'test@example.invalid')
    (path / 'tracked.txt').write_text('working tree\n', encoding='utf-8')
    _git(path, 'add', 'tracked.txt')
    _git(path, 'commit', '-qm', 'initial')
    return path


def _database(path):
    connection = sqlite3.connect(path)
    connection.execute('CREATE TABLE sample (value TEXT)')
    connection.execute('INSERT INTO sample VALUES (?)', ('tiny database',))
    connection.commit()
    connection.close()
    return path


def _run(repo, db, out, tag='data-2026.11.18'):
    return subprocess.run(
        [sys.executable, str(SCRIPT), '--tag', tag, '--db', str(db), '--out', str(out), '--repo', str(repo)],
        capture_output=True,
        text=True,
    )


def test_publishes_zip_checksum_and_an_isolated_orphan_commit(tmp_path):
    repo = _repository(tmp_path / 'repo')
    db = _database(tmp_path / 'wow.sqlite')
    out = tmp_path / 'release'
    tag = 'data-2026.11.18.2'
    initial_head = _git(repo, 'rev-parse', 'HEAD')
    initial_branch = _git(repo, 'branch', '--show-current')
    initial_index = (repo / '.git' / 'index').read_bytes()
    initial_status = _git(repo, 'status', '--porcelain')

    result = _run(repo, db, out, tag)

    assert result.returncode == 0, result.stderr
    archive = out / tag / 'wow.sqlite.zip'
    checksum_file = out / tag / 'wow.sqlite.zip.sha256'
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert checksum_file.read_text(encoding='ascii') == f'{digest}  wow.sqlite.zip\n'
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.namelist() == ['wow.sqlite']
        assert zipped.getinfo('wow.sqlite').compress_type == zipfile.ZIP_DEFLATED
        assert zipped.read('wow.sqlite') == db.read_bytes()

    branch = f'publicar-base/{tag}'
    commit = _git(repo, 'rev-parse', f'refs/heads/{branch}')
    assert _git(repo, 'rev-list', '--parents', '-n', '1', commit) == commit
    assert _git(repo, 'ls-tree', '-r', '--name-only', commit).splitlines() == [
        'base/wow.sqlite.zip', 'base/wow.sqlite.zip.sha256',
    ]
    assert _git_bytes(repo, 'show', f'{commit}:base/wow.sqlite.zip') == archive.read_bytes()
    assert _git_bytes(repo, 'show', f'{commit}:base/wow.sqlite.zip.sha256') == checksum_file.read_bytes()
    assert _git(repo, 'rev-parse', 'HEAD') == initial_head
    assert _git(repo, 'branch', '--show-current') == initial_branch
    assert (repo / '.git' / 'index').read_bytes() == initial_index
    assert _git(repo, 'status', '--porcelain') == initial_status
    assert f'SHA-256: {digest}' in result.stdout
    assert f'git push origin {branch}' in result.stdout


@pytest.mark.parametrize('tag', ['bad', 'data-2026.1.18', 'data-2026.11.18/other'])
def test_invalid_tag_exits_two_without_creating_output_or_branch(tmp_path, tag):
    repo = _repository(tmp_path / 'repo')
    db = _database(tmp_path / 'wow.sqlite')
    out = tmp_path / 'release'

    result = _run(repo, db, out, tag)

    assert result.returncode == 2
    assert 'etiqueta' in result.stderr
    assert not out.exists()
    assert _git(repo, 'branch', '--list', 'publicar-base/*') == ''


@pytest.mark.parametrize('existing', ['output', 'branch'])
def test_existing_output_or_branch_exits_two_without_creating_the_other(tmp_path, existing):
    repo = _repository(tmp_path / 'repo')
    db = _database(tmp_path / 'wow.sqlite')
    out = tmp_path / 'release'
    tag = 'data-2026.11.18'
    branch = f'publicar-base/{tag}'
    if existing == 'output':
        (out / tag).mkdir(parents=True)
    else:
        _git(repo, 'branch', branch, 'HEAD')
        before = _git(repo, 'rev-parse', f'refs/heads/{branch}')

    result = _run(repo, db, out, tag)

    assert result.returncode == 2
    if existing == 'output':
        assert 'carpeta de salida' in result.stderr
        assert _git(repo, 'branch', '--list', 'publicar-base/*') == ''
    else:
        assert 'rama local' in result.stderr
        assert _git(repo, 'rev-parse', f'refs/heads/{branch}') == before
        assert not out.exists()
