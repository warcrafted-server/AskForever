#!/usr/bin/env python3
"""Herramienta de diagnóstico: prepara addons «slot» de carga diferida en AddOns."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Sequence

DEFAULT_ADDONS = Path(r'C:\Wow\World of Warcraft\_forever_\Interface\AddOns')
INTERFACE = '16001'
SIGNALS_FOLDER = 'AskForever_Signals'
MARKER = '.askforever'
MARKER_TEXT = 'AskForever slot'
STATE_RE = re.compile(r'state\s*=\s*"([^"]*)"', re.IGNORECASE)


def slot_folder_name(slot: int) -> str:
    return f'AskForever_Slot{slot:03d}'


def signal_file_name(slot: int) -> str:
    return f'ready_{slot:03d}.tga'


def _valid_slot(slot: int) -> bool:
    return 1 <= slot <= 999


def lua_quote(text: str) -> str:
    """Cadena Lua entre comillas; escapa por bytes y deja el UTF-8 tal cual."""
    result = bytearray(b'"')
    for byte in str(text).encode('utf-8'):
        if byte == 0x5C:
            result += b'\\\\'
        elif byte == 0x22:
            result += b'\\"'
        elif byte == 0x0A:
            result += b'\\n'
        elif byte == 0x0D:
            result += b'\\r'
        elif byte < 32 or byte == 127:
            result += f'\\{byte:03d}'.encode('ascii')
        else:
            result.append(byte)
    result += b'"'
    return result.decode('utf-8')


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8', newline='')


def _atomic_write(path: Path, text: str) -> None:
    fd, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f'.{path.name}.',
                                     suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _slot_toc(slot: int) -> str:
    return '\n'.join([
        f'## Interface: {INTERFACE}',
        f'## Title: AskForever (slot {slot:03d})',
        '## Notes: Datos temporales de AskForever. No lo desactives.',
        '## Author: WarCrafted',
        '## LoadOnDemand: 1',
        f'## X-AskForever-Slot: {slot}',
        'data.lua',
    ]) + '\n'


def _initial_data(slot: int) -> str:
    return ('AskForeverSlotData = AskForeverSlotData or {}\n'
            f'AskForeverSlotData[{slot}] = {{ state = "empty" }}\n')


def _signals_toc() -> str:
    return '\n'.join([
        f'## Interface: {INTERFACE}',
        '## Title: AskForever (signals)',
        '## LoadOnDemand: 1',
    ]) + '\n'


def _tga_bytes() -> bytes:
    """TGA RGBA de 2x2 sin comprimir: cabecera de 18 bytes y 4 píxeles."""
    header = bytes([
        0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 2, 0, 32, 8,
    ])
    return header + bytes([0, 0, 255, 255]) * 4


def _prepare_folder(addons: Path, name: str) -> bool:
    """Crea o reescribe una carpeta con marcador; False si hay que respetarla."""
    folder = addons / name
    if folder.exists() and not (folder / MARKER).is_file():
        print(f'Aviso: {name} ya existe sin marcador; no se toca.')
        return False
    folder.mkdir(exist_ok=True)
    return True


def prepare(addons: Path, count: int) -> int:
    """Crea los slots 1..count y la carpeta de señales."""
    if count < 1 or count > 999:
        print('El número de slots debe estar entre 1 y 999.')
        return 2
    created = 0
    for slot in range(1, count + 1):
        name = slot_folder_name(slot)
        if not _prepare_folder(addons, name):
            continue
        _write_text(addons / name / f'{name}.toc', _slot_toc(slot))
        _write_text(addons / name / 'data.lua', _initial_data(slot))
        _write_text(addons / name / MARKER, MARKER_TEXT)
        created += 1
    if _prepare_folder(addons, SIGNALS_FOLDER):
        _write_text(addons / SIGNALS_FOLDER / f'{SIGNALS_FOLDER}.toc', _signals_toc())
        _write_text(addons / SIGNALS_FOLDER / MARKER, MARKER_TEXT)
    print(f'Preparados {created} slot(s) y la carpeta de señales en {addons}.')
    print('Hay que CERRAR Y ABRIR el juego del todo para que los detecte.')
    return 0


def write(addons: Path, slot: int, text: str) -> int:
    """Escribe la respuesta del slot y crea su señal de listo."""
    if not _valid_slot(slot):
        print('El número de slot debe estar entre 1 y 999.')
        return 2
    folder = addons / slot_folder_name(slot)
    if not folder.is_dir():
        print(f'No existe el slot {folder.name} en {addons}. Ejecuta prepare primero.')
        return 2
    written = int(time.time())
    content = ('AskForeverSlotData = AskForeverSlotData or {}\n'
               f'AskForeverSlotData[{slot}] = {{ state = "ready", '
               f'text = {lua_quote(text)}, written = {written} }}\n')
    _atomic_write(folder / 'data.lua', content)
    signals = addons / SIGNALS_FOLDER
    signals.mkdir(exist_ok=True)
    (signals / signal_file_name(slot)).write_bytes(_tga_bytes())
    print(f'Escrito {folder.name} y creada la señal {signal_file_name(slot)}.')
    return 0


def unready(addons: Path, slot: int) -> int:
    """Borra la señal del slot si existe."""
    if not _valid_slot(slot):
        print('El número de slot debe estar entre 1 y 999.')
        return 2
    signal = addons / SIGNALS_FOLDER / signal_file_name(slot)
    if signal.is_file():
        signal.unlink()
        print(f'Señal {signal.name} borrada.')
    else:
        print(f'No había señal {signal.name}.')
    return 0


def _read_state(path: Path) -> str:
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return 'desconocido'
    found = STATE_RE.search(text)
    if found is None:
        return 'desconocido'
    state = found.group(1)
    return state if state in ('empty', 'ready') else 'desconocido'


def status(addons: Path) -> int:
    """Lista cada slot con su estado y si tiene señal, sin ejecutar Lua."""
    slots = sorted(path for path in addons.glob('AskForever_Slot[0-9][0-9][0-9]')
                   if path.is_dir())
    if not slots:
        print('No hay slots en la carpeta de addons.')
        return 0
    signals = addons / SIGNALS_FOLDER
    for folder in slots:
        state = _read_state(folder / 'data.lua')
        has_signal = (signals / f'ready_{folder.name[-3:]}.tga').is_file()
        signal_text = 'sí' if has_signal else 'no'
        print(f'{folder.name}: estado={state}, señal={signal_text}')
    return 0


def clean(addons: Path) -> int:
    """Borra solo las carpetas de AskForever que llevan el marcador."""
    candidates = [path for path in addons.glob('AskForever_Slot*') if path.is_dir()]
    signals = addons / SIGNALS_FOLDER
    if signals.is_dir() and signals not in candidates:
        candidates.append(signals)
    removed = 0
    for folder in sorted(candidates):
        if not (folder / MARKER).is_file():
            print(f'Aviso: {folder.name} no tiene marcador; no se toca.')
            continue
        shutil.rmtree(folder)
        print(f'Borrada {folder.name}.')
        removed += 1
    if removed == 0:
        print('No había carpetas de AskForever que borrar.')
    return 0


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Prepara addons «slot» de carga diferida para probar AskForever.')
    parser.add_argument('--addons', default=str(DEFAULT_ADDONS),
                        help='carpeta Interface\\AddOns de Forever')
    commands = parser.add_subparsers(dest='command', required=True)

    prepare_parser = commands.add_parser('prepare', help='crea N slots y la carpeta de señales')
    prepare_parser.add_argument('count', type=int, help='número de slots (1..999)')

    write_parser = commands.add_parser('write', help='escribe una respuesta y crea la señal')
    write_parser.add_argument('slot', type=int)
    write_parser.add_argument('text')

    unready_parser = commands.add_parser('unready', help='borra la señal de un slot')
    unready_parser.add_argument('slot', type=int)

    commands.add_parser('status', help='muestra el estado de cada slot')
    commands.add_parser('clean', help='borra solo las carpetas con marcador')
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    addons = Path(args.addons)
    if not addons.is_dir():
        print(f'No existe la carpeta de addons: {addons}')
        print('Indica Interface\\AddOns de Forever con --addons RUTA.')
        return 2
    if args.command == 'prepare':
        return prepare(addons, args.count)
    if args.command == 'write':
        return write(addons, args.slot, args.text)
    if args.command == 'unready':
        return unready(addons, args.slot)
    if args.command == 'status':
        return status(addons)
    if args.command == 'clean':
        return clean(addons)
    return 2


if __name__ == '__main__':
    sys.exit(main())
