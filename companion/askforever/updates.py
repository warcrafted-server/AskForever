"""Actualización de la base de datos del juego desde GitHub Releases."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import shutil
import sqlite3
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from askforever import __version__

RELEASES_URL = (
    'https://api.github.com/repos/warcrafted-server/AskForever/releases?per_page=30'
)
USER_AGENT = (f'AskForever-companion/{__version__} '
              '(+https://github.com/warcrafted-server/AskForever)')
TIMEOUT = 15.0
BLOCK_SIZE = 64 * 1024
ZIP_NAME = 'wow.sqlite.zip'
SHA_NAME = 'wow.sqlite.zip.sha256'
DATABASE_NAME = 'wow.sqlite'
BACKUP_NAME = 'wow.sqlite.bak'
VERSION_NAME = 'version.json'


class UpdateError(Exception):
    """Fallo de actualización con un motivo corto para la consola."""

    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def parse_data_version(tag) -> Optional[tuple[int, ...]]:
    """Convierte 'data-AAAA.MM.DD[.N]' en una tupla comparable."""
    if not isinstance(tag, str) or not tag.startswith('data-'):
        return None
    parts = tag[len('data-'):].split('.')
    if len(parts) not in (3, 4):
        return None
    if not all(part.isascii() and part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def _build_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={'User-Agent': USER_AGENT})


def _default_fetch_json(url: str):
    request = _build_request(url)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        payload = response.read()
    return json.loads(payload.decode('utf-8'))


def _call_fetch_json(fetch_json):
    """Llama al obtenedor de JSON inyectado, acepte o no la URL."""
    try:
        parameters = list(inspect.signature(fetch_json).parameters.values())
    except (TypeError, ValueError):
        return fetch_json(RELEASES_URL)
    positional = [parameter for parameter in parameters
                  if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                        inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    has_varargs = any(parameter.kind is inspect.Parameter.VAR_POSITIONAL
                      for parameter in parameters)
    keyword_url = any(parameter.name == 'url'
                      and parameter.kind is inspect.Parameter.KEYWORD_ONLY
                      for parameter in parameters)
    if positional:
        return fetch_json(RELEASES_URL)
    if keyword_url:
        return fetch_json(url=RELEASES_URL)
    if has_varargs:
        try:
            return fetch_json(RELEASES_URL)
        except TypeError:
            return fetch_json()
    return fetch_json()


def latest_data_release(fetch_json=None) -> Optional[dict]:
    """Release de datos no draft con mayor versión y los dos assets."""
    try:
        payload = (_default_fetch_json(RELEASES_URL) if fetch_json is None
                   else _call_fetch_json(fetch_json))
    except Exception:
        return None
    if not isinstance(payload, list):
        return None

    best = None
    for release in payload:
        if not isinstance(release, dict) or release.get('draft'):
            continue
        version = parse_data_version(release.get('tag_name'))
        if version is None:
            continue
        assets = release.get('assets')
        if not isinstance(assets, list):
            continue
        urls = {}
        sizes = {}
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = asset.get('name')
            url = asset.get('browser_download_url')
            if not isinstance(name, str) or not isinstance(url, str) or not url:
                continue
            urls[name] = url
            sizes[name] = asset.get('size')
        if ZIP_NAME not in urls or SHA_NAME not in urls:
            continue
        try:
            size = int(sizes.get(ZIP_NAME))
        except (TypeError, ValueError):
            size = 0
        candidate = {
            'version_tag': release['tag_name'],
            'version': version,
            'zip_url': urls[ZIP_NAME],
            'sha_url': urls[SHA_NAME],
            'size': size,
        }
        if best is None or candidate['version'] > best['version']:
            best = candidate
    return best


def installed_version(data_dir) -> Optional[dict]:
    """Contenido de version.json, o None si falta o no es válido."""
    path = Path(data_dir) / VERSION_NAME
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _temp_path(directory: Path, suffix: str) -> Path:
    handle, name = tempfile.mkstemp(prefix='.wow-', suffix=suffix, dir=directory)
    os.close(handle)
    return Path(name)


def _default_download(url: str, target: Path, progress=None) -> None:
    request = _build_request(url)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        header = response.headers.get('Content-Length')
        try:
            total = int(header) if header else 0
        except (TypeError, ValueError):
            total = 0
        downloaded = 0
        with open(target, 'wb') as handle:
            while True:
                block = response.read(BLOCK_SIZE)
                if not block:
                    break
                handle.write(block)
                downloaded += len(block)
                if progress is not None:
                    progress(downloaded, total)


def _write_returned_payload(target: Path, payload, progress) -> None:
    """Escribe bytes o texto devueltos por un descargador inyectado."""
    if payload is None:
        return
    if target.exists() and target.stat().st_size:
        return
    if isinstance(payload, (bytes, bytearray)):
        target.write_bytes(bytes(payload))
        length = len(payload)
    elif isinstance(payload, str):
        target.write_text(payload, encoding='utf-8')
        length = len(payload)
    else:
        return
    if progress is not None:
        progress(length, length)


def _call_download(download, url: str, target: Path, progress) -> None:
    """Llama al descargador inyectado con la firma que tenga."""
    if download is None:
        _default_download(url, target, progress)
        return
    try:
        parameters = list(inspect.signature(download).parameters.values())
    except (TypeError, ValueError):
        download(url, target, progress)
        return
    positional = [parameter for parameter in parameters
                  if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                        inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    has_varargs = any(parameter.kind is inspect.Parameter.VAR_POSITIONAL
                      for parameter in parameters)
    keyword_progress = any(parameter.name == 'progress'
                           and parameter.kind is inspect.Parameter.KEYWORD_ONLY
                           for parameter in parameters)
    if positional:
        if len(positional) >= 3 or has_varargs:
            result = download(url, target, progress)
        elif len(positional) == 2:
            if keyword_progress:
                result = download(url, target, progress=progress)
            else:
                result = download(url, target)
        else:
            result = download(url)
    elif has_varargs:
        try:
            result = download(url, target, progress)
        except TypeError:
            try:
                result = download(url, target)
            except TypeError:
                result = download(url)
    elif keyword_progress:
        result = download(progress=progress)
    else:
        result = download()
    _write_returned_payload(target, result, progress)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(BLOCK_SIZE), b''):
            digest.update(block)
    return digest.hexdigest()


def _expected_sha(text: str) -> str:
    parts = text.strip().split()
    return parts[0].lower() if parts else ''


def _extract_database(archive_path: Path, target: Path) -> None:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            if names != [DATABASE_NAME]:
                raise UpdateError('zip')
            with archive.open(DATABASE_NAME) as source, open(target, 'wb') as handle:
                shutil.copyfileobj(source, handle)
    except UpdateError:
        raise
    except (KeyError, OSError, RuntimeError, zipfile.BadZipFile) as error:
        raise UpdateError('zip') from error


def _validate_database(path: Path) -> None:
    connection = None
    try:
        uri = path.resolve().as_uri() + '?mode=ro'
        connection = sqlite3.connect(uri, uri=True)
        row = connection.execute('PRAGMA quick_check').fetchone()
    except (OSError, ValueError, sqlite3.Error) as error:
        raise UpdateError('database') from error
    finally:
        if connection is not None:
            connection.close()
    if not row or str(row[0]).lower() != 'ok':
        raise UpdateError('database')


def install_data(release: dict, data_dir, download=None, progress=None) -> str:
    """Descarga, verifica e instala la base; devuelve la etiqueta instalada."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    version_tag = release.get('version_tag')
    zip_url = release.get('zip_url')
    sha_url = release.get('sha_url')
    if not isinstance(version_tag, str) or not version_tag:
        raise UpdateError('release')
    if not isinstance(zip_url, str) or not zip_url:
        raise UpdateError('release')
    if not isinstance(sha_url, str) or not sha_url:
        raise UpdateError('release')

    current = data_dir / DATABASE_NAME
    backup = data_dir / BACKUP_NAME
    version_path = data_dir / VERSION_NAME
    zip_temp = _temp_path(data_dir, '.zip')
    sha_temp = _temp_path(data_dir, '.sha256')
    database_temp = _temp_path(data_dir, '.sqlite')
    version_temp = _temp_path(data_dir, '.json')
    try:
        try:
            _call_download(download, zip_url, zip_temp, progress)
            _call_download(download, sha_url, sha_temp, None)
        except UpdateError:
            raise
        except Exception as error:
            raise UpdateError('download') from error

        try:
            expected = _expected_sha(sha_temp.read_text(encoding='utf-8',
                                                        errors='replace'))
        except OSError as error:
            raise UpdateError('hash') from error
        actual = _sha256_file(zip_temp)
        if not expected or expected != actual:
            raise UpdateError('hash')

        _extract_database(zip_temp, database_temp)
        _validate_database(database_temp)

        version = {
            'version_tag': version_tag,
            'sha256': actual,
            'installed_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        }
        version_temp.write_text(
            json.dumps(version, ensure_ascii=True) + '\n', encoding='utf-8')

        had_base = current.is_file()
        if had_base:
            os.replace(current, backup)
        try:
            os.replace(database_temp, current)
        except Exception:
            if had_base and backup.is_file():
                try:
                    os.replace(backup, current)
                except OSError:
                    pass
            raise
        try:
            os.replace(version_temp, version_path)
        except Exception:
            try:
                current.unlink()
            except OSError:
                pass
            if had_base and backup.is_file():
                try:
                    os.replace(backup, current)
                except OSError:
                    pass
            raise
        return version_tag
    finally:
        for temporary in (zip_temp, sha_temp, database_temp, version_temp):
            try:
                temporary.unlink()
            except OSError:
                pass


def _current_tag(current, data_dir) -> Optional[str]:
    if isinstance(current, dict):
        tag = current.get('version_tag')
    elif current is not None:
        tag = current
    else:
        info = installed_version(data_dir)
        tag = info.get('version_tag') if isinstance(info, dict) else None
    return tag if isinstance(tag, str) and tag else None


def check_and_update(data_dir, current=None, fetch_json=None, download=None,
                     progress=None) -> tuple[str, Optional[str]]:
    """Comprueba la última release y actualiza; nunca lanza."""
    try:
        installed = _current_tag(current, data_dir)
    except Exception:
        installed = None

    try:
        release = latest_data_release(fetch_json)
    except Exception:
        return ('offline', installed)
    if not isinstance(release, dict):
        return ('offline', installed)

    release_tag = release.get('version_tag')
    installed_version_tuple = (parse_data_version(installed)
                               if isinstance(installed, str) else None)
    installed_release = release.get('version')
    if not isinstance(installed_release, tuple):
        installed_release = parse_data_version(release_tag)
    if installed and (installed == release_tag
                      or (installed_version_tuple is not None
                          and installed_release is not None
                          and installed_version_tuple >= installed_release)):
        return ('current', installed)

    try:
        return ('updated', install_data(release, data_dir, download=download,
                                        progress=progress))
    except UpdateError as error:
        return ('error', str(error) or error.kind)
    except Exception as error:
        return ('error', str(error) or type(error).__name__)
