"""Prepare a database release and an orphan branch for GitHub Actions."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile


TAG_RE = re.compile(r'^data-\d{4}\.\d{2}\.\d{2}(?:\.\d+)?$')


def _git(repo: Path, *args: str, env=None, text=True) -> str | bytes:
    result = subprocess.run(
        ['git', '-C', str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=text,
    )
    return result.stdout.strip()


def _branch_exists(repo: Path, branch: str) -> bool:
    return subprocess.run(
        ['git', '-C', str(repo), 'show-ref', '--verify', '--quiet', f'refs/heads/{branch}'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def _create_orphan_branch(repo: Path, branch: str, tag: str, archive: Path, checksum: Path) -> None:
    with tempfile.TemporaryDirectory(prefix='askforever-index-') as temporary:
        index_path = Path(temporary) / 'index'
        env = os.environ.copy()
        env['GIT_INDEX_FILE'] = str(index_path)
        _git(repo, 'read-tree', '--empty', env=env)
        for source, name in ((archive, 'wow.sqlite.zip'), (checksum, 'wow.sqlite.zip.sha256')):
            blob = _git(repo, 'hash-object', '-w', str(source.resolve()))
            _git(repo, 'update-index', '--add', '--cacheinfo', f'100644,{blob},base/{name}', env=env)
        tree = _git(repo, 'write-tree', env=env)
        commit = _git(repo, 'commit-tree', tree, '-m', f'data: base {tag}')
        _git(repo, 'branch', branch, commit)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True, help='etiqueta data-YYYY.MM.DD[.N]')
    parser.add_argument('--db', default='../wowdata/datos/wow.sqlite', help='base SQLite de origen')
    parser.add_argument('--out', default='release', help='carpeta para los archivos de release')
    parser.add_argument('--repo', default='.', help='repositorio Git local')
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if not TAG_RE.fullmatch(args.tag):
        print('Error: la etiqueta debe tener el formato data-YYYY.MM.DD[.N].', file=sys.stderr)
        return 2

    repo = Path(args.repo).resolve()
    branch = f'publicar-base/{args.tag}'
    output = Path(args.out) / args.tag
    if output.exists():
        print(f'Error: ya existe la carpeta de salida {output}.', file=sys.stderr)
        return 2
    try:
        _git(repo, 'rev-parse', '--git-dir')
        if _branch_exists(repo, branch):
            print(f'Error: ya existe la rama local {branch}.', file=sys.stderr)
            return 2
        db = Path(args.db)
        if not db.is_file():
            raise FileNotFoundError(f'No se encuentra la base SQLite: {db}')

        output.mkdir(parents=True)
        archive = output / 'wow.sqlite.zip'
        checksum = output / 'wow.sqlite.zip.sha256'
        with ZipFile(archive, 'w', compression=ZIP_DEFLATED) as zipped:
            zipped.write(db, 'wow.sqlite')
        digest = _sha256(archive)
        checksum.write_text(f'{digest}  wow.sqlite.zip\n', encoding='ascii', newline='')
        _create_orphan_branch(repo, branch, args.tag, archive, checksum)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        print(f'Error: no se pudo preparar la publicación: {detail}', file=sys.stderr)
        return 1

    print(f'SHA-256: {digest}')
    print('Siguiente comando:')
    print(f'git push origin {branch}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
