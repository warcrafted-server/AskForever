"""Pruebas del instalador y desinstalador de Linux (scripts/linux).

Todo se ejecuta contra carpetas temporales: nunca contra una instalación real
de WoW Forever. En los equipos que no son Linux se omiten.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith('linux'), reason='instalador de Linux')

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts' / 'linux'
BUNDLED_VERSION = '0.5.0-beta.2'

FAKE_APP = r'''#!/usr/bin/env bash
set -u
if [ -n "${FAKE_ARGS:-}" ]; then
    printf '%s\n' "$*" >> "$FAKE_ARGS"
fi
case "${1:-}" in
    find-wow)
        if [ -n "${FAKE_FIND:-}" ] && [ -f "$FAKE_FIND" ]; then
            while IFS= read -r line; do
                [ -n "$line" ] && printf '%s\n' "$line"
            done < "$FAKE_FIND"
            exit 0
        fi
        exit 1
        ;;
    uninstall)
        exit "${FAKE_UNINSTALL_EXIT:-0}"
        ;;
esac
exit 0
'''


def _write_program(path):
    path.write_text(FAKE_APP, encoding='utf-8')
    path.chmod(0o755)


def _make_tarball(tmp_path):
    """Carpeta extraída del tar.gz, con el programa y el addon falsos."""
    root = tmp_path / f'askforever-{BUNDLED_VERSION}'
    (root / 'app' / '_internal').mkdir(parents=True)
    shutil.copy2(SCRIPTS / 'install.sh', root / 'install.sh')
    shutil.copy2(SCRIPTS / 'uninstall.sh', root / 'uninstall.sh')
    _write_program(root / 'app' / 'AskForeverApp')
    (root / 'app' / '_internal' / 'base_library.zip').write_text(
        'interno\n', encoding='utf-8')
    (root / 'app' / 'askforever.png').write_bytes(b'\x89PNG\r\n\x1a\n')
    addon = root / 'addon' / 'AskForever'
    addon.mkdir(parents=True)
    (addon / 'AskForever.toc').write_bytes(
        ('## Interface: 16001\r\n'
         '## Title: AskForever\r\n'
         f'## Version: {BUNDLED_VERSION}\r\n').encode('utf-8'))
    (addon / 'core.lua').write_text('-- addon incluido\n', encoding='utf-8')
    return root


def _env(tmp_path, **extra):
    env = os.environ.copy()
    for name in ('ASKFOREVER_HOME', 'ASKFOREVER_WOW_DIR', 'XDG_DATA_HOME'):
        env.pop(name, None)
    env['HOME'] = str(tmp_path / 'home')
    env['XDG_DATA_HOME'] = str(tmp_path / 'xdg')
    env['FAKE_ARGS'] = str(tmp_path / 'fake-args.txt')
    env.update({name: str(value) for name, value in extra.items()})
    return env


def _make_game(tmp_path, parent='World of Warcraft'):
    """Crea <parent>/_forever_ con Wow.exe y una instancia de AddOns."""
    game = tmp_path / parent / '_forever_'
    (game / 'Interface' / 'AddOns').mkdir(parents=True)
    (game / 'Wow.exe').write_bytes(b'MZ')
    return game


def _run(script, args=(), env=None, stdin=''):
    return subprocess.run(
        ['bash', str(script), *args],
        env=env, input=stdin, capture_output=True, text=True, timeout=120)


def _install(tarball, game, env, *extra):
    # Acepta la carpeta "World of Warcraft": install.sh también debe hacerlo.
    return _run(tarball / 'install.sh', ['--wow-dir', str(game.parent), *extra],
                env=env)


def _desktop_exec(path):
    """Repite el escapado de Exec del instalador (spec Desktop Entry)."""
    value = str(path)
    value = value.replace('\\', '\\\\')
    value = value.replace('"', '\\"')
    value = value.replace('`', '\\`')
    value = value.replace('$', '\\$')
    value = value.replace('\\', '\\\\')
    return f'Exec="{value}" app'


def test_install_copies_program_addon_and_marker(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path, parent='Juegos (SSD)')
    env = _env(tmp_path)

    result = _install(tarball, game, env)

    assert result.returncode == 0, result.stderr
    target = game / 'AskForever'
    assert (target / 'AskForeverApp').is_file()
    assert os.access(target / 'AskForeverApp', os.X_OK)
    assert (target / '_internal' / 'base_library.zip').is_file()
    assert (target / 'askforever.png').is_file()
    assert (target / 'uninstall.sh').is_file()
    assert os.access(target / 'uninstall.sh', os.X_OK)
    assert (target / '.askforever-install').is_file()
    addon = game / 'Interface' / 'AddOns' / 'AskForever'
    assert (addon / 'AskForever.toc').read_bytes() == \
        (tarball / 'addon' / 'AskForever' / 'AskForever.toc').read_bytes()
    assert (addon / 'core.lua').is_file()
    assert not (target / 'data').exists()
    assert 'uninstall.sh' in result.stdout
    assert 'borderless' in result.stdout


def test_install_accepts_forever_folder_directly(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path)
    result = _run(tarball / 'install.sh', ['--wow-dir', str(game)],
                  env=_env(tmp_path))
    assert result.returncode == 0, result.stderr
    assert (game / 'AskForever' / 'AskForeverApp').is_file()


def test_reinstall_keeps_data_and_logs(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path)
    env = _env(tmp_path)
    assert _install(tarball, game, env).returncode == 0

    target = game / 'AskForever'
    (target / 'data').mkdir()
    (target / 'data' / 'player.db').write_text('datos\n', encoding='utf-8')
    (target / 'logs').mkdir()
    (target / 'logs' / 'app.log').write_text('registro\n', encoding='utf-8')

    result = _install(tarball, game, env)

    assert result.returncode == 0, result.stderr
    assert (target / 'data' / 'player.db').read_text(encoding='utf-8') == 'datos\n'
    assert (target / 'logs' / 'app.log').read_text(encoding='utf-8') == 'registro\n'
    assert (target / 'AskForeverApp').is_file()


def test_install_refuses_foreign_folder_untouched(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path)
    target = game / 'AskForever'
    target.mkdir()
    (target / 'otra-cosa.txt').write_text('mío\n', encoding='utf-8')

    result = _install(tarball, game, _env(tmp_path))

    assert result.returncode != 0
    assert 'no parece' in result.stderr
    assert (target / 'otra-cosa.txt').read_text(encoding='utf-8') == 'mío\n'
    assert not (target / 'AskForeverApp').exists()


def test_install_refuses_symlinked_program_folder(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path)
    external = tmp_path / 'externo'
    external.mkdir()
    (external / 'nota.txt').write_text('fuera\n', encoding='utf-8')
    target = game / 'AskForever'
    target.symlink_to(external, target_is_directory=True)

    result = _install(tarball, game, _env(tmp_path))

    assert result.returncode != 0
    assert target.is_symlink()
    assert sorted(p.name for p in external.iterdir()) == ['nota.txt']


def test_install_leaves_symlinked_addon_untouched(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path)
    external = tmp_path / 'addon-externo'
    external.mkdir()
    (external / 'mio.lua').write_text('-- mío\n', encoding='utf-8')
    (game / 'Interface' / 'AddOns' / 'AskForever').symlink_to(
        external, target_is_directory=True)

    result = _install(tarball, game, _env(tmp_path))

    assert result.returncode == 0, result.stderr
    addon = game / 'Interface' / 'AddOns' / 'AskForever'
    assert addon.is_symlink()
    assert (external / 'mio.lua').is_file()
    assert not (external / 'core.lua').exists()
    assert 'enlace' in result.stdout
    assert (game / 'AskForever' / 'AskForeverApp').is_file()


def test_install_keeps_newer_addon(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path)
    addon = game / 'Interface' / 'AddOns' / 'AskForever'
    addon.mkdir()
    # 0.5.0-beta.12 > 0.5.0-beta.2 con sort -V tras cambiar '-' por '~'.
    (addon / 'AskForever.toc').write_bytes(
        b'## Interface: 16001\r\n## Version: 0.5.0-beta.12\r\n')
    (addon / 'mio.lua').write_text('-- mío\n', encoding='utf-8')

    result = _install(tarball, game, _env(tmp_path))

    assert result.returncode == 0, result.stderr
    assert 'conserva' in result.stdout
    assert (addon / 'mio.lua').is_file()
    assert not (addon / 'core.lua').exists()
    assert b'0.5.0-beta.12' in (addon / 'AskForever.toc').read_bytes()


def test_install_replaces_older_addon(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path)
    addon = game / 'Interface' / 'AddOns' / 'AskForever'
    addon.mkdir()
    (addon / 'AskForever.toc').write_text(
        '## Interface: 16001\n## Version: 0.5.0-beta.1\n', encoding='utf-8')
    (addon / 'viejo.lua').write_text('-- viejo\n', encoding='utf-8')

    result = _install(tarball, game, _env(tmp_path))

    assert result.returncode == 0, result.stderr
    assert not (addon / 'viejo.lua').exists()
    assert (addon / 'core.lua').is_file()
    assert (addon / 'AskForever.toc').read_bytes() == \
        (tarball / 'addon' / 'AskForever' / 'AskForever.toc').read_bytes()


def test_install_lists_several_detected_folders(tmp_path):
    tarball = _make_tarball(tmp_path)
    first = tmp_path / 'Juegos (SSD)' / '_forever_'
    second = tmp_path / 'Otro disco' / '_forever_'
    find_file = tmp_path / 'detectadas.txt'
    find_file.write_text(f'{first}\n{second}\n', encoding='utf-8')
    env = _env(tmp_path, FAKE_FIND=find_file)

    result = _run(tarball / 'install.sh', env=env)

    assert result.returncode != 0
    assert str(first) in result.stderr
    assert str(second) in result.stderr
    assert '--wow-dir' in result.stderr
    assert not (first / 'AskForever').exists()
    assert not (second / 'AskForever').exists()


def test_install_without_detection_explains_wow_dir(tmp_path):
    tarball = _make_tarball(tmp_path)
    result = _run(tarball / 'install.sh', env=_env(tmp_path))
    assert result.returncode != 0
    assert '--wow-dir' in result.stderr


def test_install_creates_desktop_entry_with_quoted_exec(tmp_path):
    tarball = _make_tarball(tmp_path)
    parent = 'Juegos (SSD) $HOME `curioso` y "comillas" \\ atrás'
    game = _make_game(tmp_path, parent=parent)
    env = _env(tmp_path)

    result = _install(tarball, game, env, '--desktop')

    assert result.returncode == 0, result.stderr
    target = game / 'AskForever'
    desktop = tmp_path / 'xdg' / 'applications' / 'askforever.desktop'
    assert desktop.is_file()
    text = desktop.read_text(encoding='utf-8')
    lines = text.splitlines()
    assert lines[0] == '[Desktop Entry]'
    assert 'Type=Application' in lines
    assert 'Name=AskForever App' in lines
    assert 'Terminal=false' in lines
    assert 'Categories=Game;' in lines
    assert _desktop_exec(target / 'AskForeverApp') in lines
    assert f'Icon={target / "askforever.png"}' in lines
    assert f'X-AskForever-Dir={target}' in lines
    assert (target / '.desktop-path').read_text(encoding='utf-8').strip() == \
        str(desktop)


def test_install_desktop_entry_without_icon(tmp_path):
    tarball = _make_tarball(tmp_path)
    (tarball / 'app' / 'askforever.png').unlink()
    game = _make_game(tmp_path)

    result = _install(tarball, game, _env(tmp_path), '--desktop')

    assert result.returncode == 0, result.stderr
    target = game / 'AskForever'
    desktop = tmp_path / 'xdg' / 'applications' / 'askforever.desktop'
    assert not (target / 'askforever.png').exists()
    assert 'Icon=' not in desktop.read_text(encoding='utf-8')


def test_uninstall_removes_only_its_folder_and_desktop(tmp_path):
    tarball = _make_tarball(tmp_path)
    game_a = _make_game(tmp_path, parent='Juego A (1)')
    game_b = _make_game(tmp_path, parent='Juego B')
    env = _env(tmp_path)
    assert _install(tarball, game_a, env, '--desktop').returncode == 0
    assert _install(tarball, game_b, env).returncode == 0

    target_a = game_a / 'AskForever'
    addons_a = game_a / 'Interface' / 'AddOns'
    (addons_a / 'OtroAddon').mkdir()
    (addons_a / 'OtroAddon' / 'OtroAddon.toc').write_text(
        '## Interface: 16001\n', encoding='utf-8')
    desktop = tmp_path / 'xdg' / 'applications' / 'askforever.desktop'
    otro_desktop = tmp_path / 'xdg' / 'applications' / 'otro.desktop'
    otro_desktop.write_text('[Desktop Entry]\nType=Application\n',
                            encoding='utf-8')

    result = _run(target_a / 'uninstall.sh', ['--yes'], env=env)

    assert result.returncode == 0, result.stderr
    assert not target_a.exists()
    assert not desktop.exists()
    assert otro_desktop.is_file()
    assert (addons_a / 'OtroAddon' / 'OtroAddon.toc').is_file()
    assert (game_a / 'Wow.exe').is_file()
    assert (game_b / 'AskForever' / 'AskForeverApp').is_file()
    assert (game_b / 'Interface' / 'AddOns' / 'AskForever').is_dir()
    recorded = (tmp_path / 'fake-args.txt').read_text(encoding='utf-8')
    assert 'uninstall --yes --addon' in recorded


def test_install_rejects_wow_dir_without_wow_exe(tmp_path):
    tarball = _make_tarball(tmp_path)
    empty = tmp_path / 'World of Warcraft' / '_forever_'
    empty.mkdir(parents=True)

    result = _install(tarball, empty, _env(tmp_path))

    assert result.returncode != 0
    assert 'Wow.exe' in result.stderr
    assert not (empty / 'AskForever').exists()


def test_uninstall_aborts_while_program_runs(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path)
    env = _env(tmp_path)
    assert _install(tarball, game, env).returncode == 0

    target = game / 'AskForever'
    sleeper = target / 'AskForeverApp.test'
    shutil.copy2(shutil.which('sleep'), sleeper)
    process = subprocess.Popen([str(sleeper), '60'])
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                running = os.readlink(f'/proc/{process.pid}/exe')
            except OSError:
                running = ''
            if running == str(sleeper):
                break
            time.sleep(0.02)
        result = _run(target / 'uninstall.sh', ['--yes'], env=env)
    finally:
        process.kill()
        process.wait()

    assert result.returncode != 0
    assert 'proceso' in result.stderr
    assert target.is_dir()


def test_uninstall_aborts_from_tarball_copy(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path)
    env = _env(tmp_path)
    assert _install(tarball, game, env).returncode == 0

    result = _run(tarball / 'uninstall.sh', ['--yes', '--force'], env=env)

    assert result.returncode != 0
    assert 'AskForever' in result.stderr
    assert 'uninstall.sh' in result.stderr
    assert (tarball / 'app' / 'AskForeverApp').is_file()
    assert (tarball / 'install.sh').is_file()
    assert (game / 'AskForever' / 'AskForeverApp').is_file()


def test_uninstall_without_confirmation_cancels(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path)
    env = _env(tmp_path)
    assert _install(tarball, game, env).returncode == 0

    result = _run(game / 'AskForever' / 'uninstall.sh', env=env)

    assert result.returncode != 0
    assert (game / 'AskForever' / 'AskForeverApp').is_file()
    assert not (tmp_path / 'fake-args.txt').exists()


def test_uninstall_keeps_folder_when_program_fails(tmp_path):
    tarball = _make_tarball(tmp_path)
    game = _make_game(tmp_path)
    env = _env(tmp_path)
    assert _install(tarball, game, env).returncode == 0
    target = game / 'AskForever'

    failing = _env(tmp_path, FAKE_UNINSTALL_EXIT='1')
    result = _run(target / 'uninstall.sh', ['--yes'], env=failing)

    assert result.returncode != 0
    assert target.is_dir()
    assert (target / 'AskForeverApp').is_file()

    forced = _run(target / 'uninstall.sh', ['--yes', '--force'], env=failing)

    assert forced.returncode == 0, forced.stderr
    assert not target.exists()


def test_uninstall_refuses_folder_without_marker(tmp_path):
    game = _make_game(tmp_path)
    target = game / 'AskForever'
    target.mkdir()
    _write_program(target / 'AskForeverApp')

    result = _run(target / 'uninstall.sh', ['--yes', '--force'],
                  env=_env(tmp_path))

    assert result.returncode != 0
    assert (target / 'AskForeverApp').is_file()
