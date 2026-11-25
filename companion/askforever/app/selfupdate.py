"""Automatic updates for the packaged AskForever App."""

from __future__ import annotations

import inspect
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

from askforever import __version__
from askforever import config, updates
from askforever.app.events import emit, log_detail, set_status


_VERSION_RE = re.compile(
    r'^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.'
    r'(?P<patch>0|[1-9]\d*)(?:-?beta\.?|b)(?P<pre>0|[1-9]\d*)$|'
    r'^v?(?P<major_final>0|[1-9]\d*)\.(?P<minor_final>0|[1-9]\d*)\.'
    r'(?P<patch_final>0|[1-9]\d*)$'
)
INSTALLER_PREFIX = 'AskForever-Setup-'
LINUX_ASSET_TEMPLATE = 'askforever-{version}-linux-x86_64.tar.gz'
RELEASES_PAGE_URL = 'https://github.com/warcrafted-server/AskForever/releases/tag/'


class SelfUpdateError(Exception):
    """A release could not be downloaded or applied safely."""


def parse_version(text) -> Optional[tuple[int, int, int, int, int]]:
    """Parse a release version into a tuple where beta versions sort first."""
    if not isinstance(text, str):
        return None
    match = _VERSION_RE.fullmatch(text.strip())
    if not match:
        return None
    groups = match.groupdict()
    if groups['major'] is not None:
        return (int(groups['major']), int(groups['minor']),
                int(groups['patch']), 0, int(groups['pre']))
    return (int(groups['major_final']), int(groups['minor_final']),
            int(groups['patch_final']), 1, 0)


def _release_url() -> str:
    return os.environ.get('ASKFOREVER_RELEASES_URL') or updates.RELEASES_URL


def _call_fetch_json(fetch_json, url):
    try:
        parameters = list(inspect.signature(fetch_json).parameters.values())
    except (TypeError, ValueError):
        return fetch_json(url)
    positional = [parameter for parameter in parameters
                  if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                        inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    if positional or any(parameter.kind is inspect.Parameter.VAR_POSITIONAL
                         for parameter in parameters):
        return fetch_json(url)
    if any(parameter.name == 'url'
           and parameter.kind is inspect.Parameter.KEYWORD_ONLY
           for parameter in parameters):
        return fetch_json(url=url)
    return fetch_json()


def latest_app_release(fetch_json=None, platform=None) -> Optional[dict]:
    """Return the highest valid, non-draft app release for the current platform."""
    if platform is None:
        platform = sys.platform
    linux = platform.startswith('linux')
    url = _release_url()
    try:
        payload = (updates._default_fetch_json(url) if fetch_json is None
                   else _call_fetch_json(fetch_json, url))
    except Exception as error:
        log_detail(f'app update release check failed: {error!r}')
        return None
    if not isinstance(payload, list):
        return None

    best = None
    best_version = None
    for release in payload:
        if not isinstance(release, dict) or release.get('draft'):
            continue
        tag = release.get('tag_name')
        if not isinstance(tag, str) or not tag.startswith('v'):
            continue
        version_key = parse_version(tag)
        if version_key is None:
            continue
        version = tag[1:]
        assets = release.get('assets')
        if not isinstance(assets, list):
            continue
        urls = {}
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = asset.get('name')
            asset_url = asset.get('browser_download_url')
            if isinstance(name, str) and isinstance(asset_url, str) and asset_url:
                urls[name] = asset_url
        if linux:
            if LINUX_ASSET_TEMPLATE.format(version=version) not in urls:
                continue
            page_url = release.get('html_url')
            if not (isinstance(page_url, str)
                    and page_url.startswith('https://github.com/')):
                page_url = RELEASES_PAGE_URL + tag
            candidate = {
                'version': version,
                'tag': tag,
                'page_url': page_url,
            }
        else:
            installer_name = f'{INSTALLER_PREFIX}{version}.exe'
            sha_name = installer_name + '.sha256'
            if installer_name not in urls or sha_name not in urls:
                continue
            candidate = {
                'version': version,
                'tag': tag,
                'installer_url': urls[installer_name],
                'sha256_url': urls[sha_name],
            }
        if best_version is None or version_key > best_version:
            best_version = version_key
            best = candidate
    return best


def check(current=__version__) -> Optional[dict]:
    """Return a valid release only when it is newer than the installed version."""
    try:
        release = latest_app_release()
        if not release:
            return None
        latest = parse_version(release.get('tag'))
        installed = parse_version(current)
        return release if latest is not None and installed is not None and latest > installed else None
    except Exception as error:
        log_detail(f'app update check failed: {error!r}')
        return None


def _installer_name(release: dict) -> str:
    tag = release.get('tag')
    if not isinstance(tag, str) or not tag.startswith('v') or parse_version(tag) is None:
        raise SelfUpdateError('invalid release version')
    return f'{INSTALLER_PREFIX}{tag[1:]}.exe'


def download_installer(release, folder=None, download=None) -> Path:
    """Download and verify an installer before atomically publishing it in updates/."""
    try:
        name = _installer_name(release)
        installer_url = release.get('installer_url')
        sha_url = release.get('sha256_url')
        if not isinstance(installer_url, str) or not installer_url:
            raise SelfUpdateError('invalid installer URL')
        if not isinstance(sha_url, str) or not sha_url:
            raise SelfUpdateError('invalid checksum URL')
        directory = Path(folder) if folder is not None else config.user_data_dir().parent / 'updates'
        directory.mkdir(parents=True, exist_ok=True)
        temporary_files = []
        destination = directory / name
        try:
            installer_temp = updates._temp_path(directory, '.exe')
            temporary_files.append(installer_temp)
            sha_temp = updates._temp_path(directory, '.sha256')
            temporary_files.append(sha_temp)
            updates._call_download(download, sha_url, sha_temp, None)
            updates._call_download(download, installer_url, installer_temp, None)
            expected = updates._expected_sha(
                sha_temp.read_text(encoding='utf-8', errors='replace'))
            actual = updates._sha256_file(installer_temp)
            if not expected or expected != actual:
                raise SelfUpdateError('installer SHA-256 mismatch')
            os.replace(installer_temp, destination)
            for old_installer in directory.glob(f'{INSTALLER_PREFIX}*.exe'):
                if old_installer != destination:
                    try:
                        old_installer.unlink()
                    except OSError as error:
                        log_detail(f'old app installer cleanup failed: {error!r}')
            return destination
        finally:
            for temporary in temporary_files:
                try:
                    temporary.unlink()
                except OSError:
                    pass
    except SelfUpdateError:
        raise
    except Exception as error:
        raise SelfUpdateError(str(error) or type(error).__name__) from error


def apply(installer_path, popen=subprocess.Popen):
    """Start the verified installer detached; the caller should then exit."""
    detached = getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
    new_group = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
    return popen([
        str(installer_path), '/VERYSILENT', '/SUPPRESSMSGBOXES',
        '/NORESTART', '/RELAUNCH',
    ], creationflags=detached | new_group)


class Updater:
    def __init__(self, exit_app, is_busy, interval=6 * 3600, first_delay=30,
                 check_func=None, download_func=None, apply_func=None, sleep=None,
                 platform=None):
        self.exit_app = exit_app
        self.is_busy = is_busy
        self.interval = interval
        self.first_delay = first_delay
        self.check_func = check_func or check
        self.download_func = download_func or download_installer
        self.apply_func = apply_func or apply
        self.sleep = sleep
        self.platform = sys.platform if platform is None else platform
        self._announced_version = None
        self._stop = threading.Event()
        self._thread = None

    @staticmethod
    def _enabled() -> bool:
        if os.environ.get('ASKFOREVER_NO_SELF_UPDATE') == '1':
            return False
        return bool(getattr(sys, 'frozen', False)
                    or os.environ.get('ASKFOREVER_SELF_UPDATE') == '1')

    def start(self):
        if not self._enabled():
            set_status('app', 'AskForever App · actualizaciones automáticas desactivadas',
                       'AskForever App · automatic updates disabled', ok=None)
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name='AskForeverUpdater',
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if (self._thread is not None and self._thread is not threading.current_thread()
                and self._thread.is_alive()):
            self._thread.join(timeout=2.0)

    def _wait(self, seconds):
        if self.sleep is None:
            return self._stop.wait(seconds)
        self.sleep(seconds)
        return self._stop.is_set()

    def _run(self):
        if self._wait(self.first_delay):
            return
        while not self._stop.is_set():
            try:
                self._check_once()
            except Exception as error:
                log_detail(f'app update failed: {error!r}')
                emit('error', 'No se pudo actualizar AskForever App: se intentará más tarde',
                     'AskForever App could not be updated; it will try again later',
                     detail=str(error))
            if self._wait(self.interval):
                return

    def _check_once(self):
        current = f'AskForever App {__version__}'
        set_status('app', f'{current} · buscando actualizaciones…',
                   f'{current} · checking for updates…', ok=None)
        release = self.check_func()
        if self._stop.is_set():
            return
        if not release:
            set_status('app', f'{current} · al día', f'{current} · up to date', ok=True)
            return

        version = release['version']
        if self.platform.startswith('linux'):
            self._announce_linux_release(release, version)
            return

        emit('update', f'Hay una versión nueva ({version}): se descarga y se instalará sola',
             f'A new version ({version}) is available: it will download and install itself')
        installer = self.download_func(release)
        if self._stop.is_set():
            return
        waited = 0
        while self.is_busy() and waited < 600:
            if self._wait(2):
                return
            waited += 2
        if self.is_busy():
            raise SelfUpdateError('timed out waiting for the current answer')
        if self._stop.is_set():
            return
        emit('update', f'Instalando la versión {version}; AskForever App se reiniciará',
             f'Installing version {version}; AskForever App will restart')
        set_status('app', 'Actualizando…', 'Updating…', ok=None)
        self.apply_func(installer)
        self.exit_app()

    def _announce_linux_release(self, release, version):
        """On Linux the app only announces the release; it never installs it."""
        page_url = release.get('page_url')
        if not isinstance(page_url, str) or not page_url:
            page_url = RELEASES_PAGE_URL + str(release.get('tag', ''))
        set_status('app', f'Hay una versión nueva de AskForever App ({version})',
                   f'A new version of AskForever App ({version}) is available', ok=None)
        if self._announced_version == version:
            return
        self._announced_version = version
        emit('update',
             f'Hay una versión nueva de AskForever App ({version}): descarga el .tar.gz de '
             f'{page_url} y ejecuta install.sh',
             f'A new version of AskForever App ({version}) is available: download the .tar.gz from '
             f'{page_url} and run install.sh')
