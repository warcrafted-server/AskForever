"""Pruebas del empaquetado de la versión de Linux (scripts/build-linux.sh).

Se usa una carpeta de programa falsa con --stage-only, así que no hace falta
PyInstaller. En los equipos que no son Linux o no tienen Pillow se omiten.
"""

import hashlib
import io
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

try:
    from PIL import Image
except ImportError:  # pragma: no cover - depende del entorno
    Image = None

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith('linux') or Image is None,
    reason='paquete de Linux con Pillow')

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / 'scripts' / 'build-linux.sh'
VERSION = (REPO / 'VERSION').read_text(encoding='utf-8').strip()


def _make_fake_dist(tmp_path):
    dist = tmp_path / 'programa-falso'
    dist.mkdir()
    program = dist / 'AskForeverApp'
    program.write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
    program.chmod(0o755)
    internal = dist / '_internal'
    internal.mkdir()
    (internal / 'base_library.zip').write_text('interno\n', encoding='utf-8')
    return dist


def _build_stage_only(tmp_path):
    dist = _make_fake_dist(tmp_path)
    out = tmp_path / 'salida'
    env = os.environ.copy()
    env['PYTHON'] = sys.executable
    result = subprocess.run(
        ['bash', str(SCRIPT), '--stage-only', str(dist), '--out', str(out)],
        env=env, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stderr
    tarball = out / f'askforever-{VERSION}-linux-x86_64.tar.gz'
    assert tarball.is_file(), result.stdout
    return out, tarball


def test_stage_only_packages_program_addon_and_checksum(tmp_path):
    out, tarball = _build_stage_only(tmp_path)
    top = f'askforever-{VERSION}'

    with tarfile.open(tarball, 'r:gz') as archive:
        members = {member.name: member for member in archive.getmembers()}
        toc = archive.extractfile(f'{top}/addon/AskForever/AskForever.toc')
        toc_text = toc.read().decode('utf-8')
        icon = archive.extractfile(f'{top}/app/askforever.png')
        icon_bytes = icon.read()

    assert all(name == top or name.startswith(f'{top}/')
               for name in members)
    assert f'{top}/install.sh' in members
    assert f'{top}/uninstall.sh' in members
    assert members[f'{top}/install.sh'].mode & 0o777 == 0o755
    assert members[f'{top}/uninstall.sh'].mode & 0o777 == 0o755
    assert f'{top}/LICENSE' in members
    assert f'{top}/app/AskForeverApp' in members
    assert f'{top}/app/_internal/base_library.zip' in members
    assert f'{top}/addon/AskForever/AskForever.toc' in members
    assert f'{top}/addon/AskForever/core/Init.lua' in members
    assert f'{top}/addon/AskForever/data/manifest.lua' in members
    assert f'{top}/addon/AskForever/data/db-001.lua' in members

    with Image.open(io.BytesIO(icon_bytes)) as image:
        assert image.size == (256, 256)

    # Sin restos de desarrollo en el addon ni en el .toc.
    assert f'{top}/addon/AskForever/AskForeverDev.toc' not in members
    assert not [name for name in members if '/addon/AskForever/dev/' in name]
    assert not [name for name in members if name.endswith('.gitkeep')]
    assert not [line for line in toc_text.splitlines()
                if line.strip().startswith('dev/')]

    # La carpeta temporal de preparación queda dentro de --out.
    stage = out / 'stage' / top
    assert (stage / 'install.sh').is_file()
    assert (stage / 'addon' / 'AskForever' / 'AskForever.toc').is_file()

    checksum_file = tarball.with_name(tarball.name + '.sha256')
    digest, name = checksum_file.read_text(encoding='utf-8').split(None, 1)
    assert name.strip() == tarball.name
    assert digest == hashlib.sha256(tarball.read_bytes()).hexdigest()
