"""Pruebas de la herramienta de diagnóstico slot_spike."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from PIL import Image

MODULE_PATH = Path(__file__).resolve().parent.parent / 'tools' / 'slot_spike.py'
SPEC = importlib.util.spec_from_file_location('slot_spike', MODULE_PATH)
slot_spike = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(slot_spike)


def _run(tmp_path, *args):
    return slot_spike.main(['--addons', str(tmp_path), *args])


def test_prepare_creates_slots(tmp_path, capsys):
    assert _run(tmp_path, 'prepare', '3') == 0
    for slot in (1, 2, 3):
        name = f'AskForever_Slot{slot:03d}'
        folder = tmp_path / name
        toc = (folder / f'{name}.toc').read_text(encoding='utf-8')
        assert toc.splitlines() == [
            '## Interface: 16001',
            f'## Title: AskForever (slot {slot:03d})',
            '## Notes: Datos temporales de AskForever. No lo desactives.',
            '## Author: WarCrafted',
            '## LoadOnDemand: 1',
            f'## X-AskForever-Slot: {slot}',
            'data.lua',
        ]
        data = (folder / 'data.lua').read_text(encoding='utf-8')
        assert data == ('AskForeverSlotData = AskForeverSlotData or {}\n'
                        f'AskForeverSlotData[{slot}] = {{ state = "empty" }}\n')
        assert (folder / '.askforever').read_text(encoding='utf-8') == 'AskForever slot'

    signals = tmp_path / 'AskForever_Signals'
    toc = (signals / 'AskForever_Signals.toc').read_text(encoding='utf-8')
    assert toc.splitlines() == [
        '## Interface: 16001',
        '## Title: AskForever (signals)',
        '## LoadOnDemand: 1',
    ]
    assert (signals / '.askforever').is_file()
    assert not list(signals.glob('*.lua'))
    assert 'CERRAR Y ABRIR' in capsys.readouterr().out


def test_prepare_respects_folder_without_marker(tmp_path, capsys):
    folder = tmp_path / 'AskForever_Slot002'
    folder.mkdir()
    (folder / 'nota.txt').write_text('no tocar', encoding='utf-8')

    assert _run(tmp_path, 'prepare', '3') == 0
    assert (folder / 'nota.txt').read_text(encoding='utf-8') == 'no tocar'
    assert not (folder / 'data.lua').exists()
    assert (tmp_path / 'AskForever_Slot001' / 'data.lua').is_file()
    assert (tmp_path / 'AskForever_Slot003' / 'data.lua').is_file()
    assert 'sin marcador' in capsys.readouterr().out


def test_prepare_rewrites_marked_folder(tmp_path):
    assert _run(tmp_path, 'prepare', '1') == 0
    data = tmp_path / 'AskForever_Slot001' / 'data.lua'
    data.write_text('basura', encoding='utf-8')

    assert _run(tmp_path, 'prepare', '1') == 0
    assert data.read_text(encoding='utf-8').startswith('AskForeverSlotData =')


def test_write_quotes_text_and_creates_signal(tmp_path):
    assert _run(tmp_path, 'prepare', '2') == 0
    assert _run(tmp_path, 'write', '2', 'hola "mundo"\nñ') == 0

    content = (tmp_path / 'AskForever_Slot002' / 'data.lua').read_text(encoding='utf-8')
    assert '\r' not in content
    lines = content.splitlines()
    assert lines[0] == 'AskForeverSlotData = AskForeverSlotData or {}'
    assert 'state = "ready"' in lines[1]
    assert 'text = "hola \\"mundo\\"\\nñ"' in lines[1]
    assert re.search(r'written = \d+', lines[1])

    signal = tmp_path / 'AskForever_Signals' / 'ready_002.tga'
    with Image.open(signal) as image:
        assert image.size == (2, 2)
        assert image.mode == 'RGBA'


def test_lua_quote_escapes():
    assert slot_spike.lua_quote('a\\b') == '"a\\\\b"'
    assert slot_spike.lua_quote('dice "hola"') == '"dice \\"hola\\""'
    assert slot_spike.lua_quote('linea\nsiguiente') == '"linea\\nsiguiente"'
    assert slot_spike.lua_quote('linea\rsiguiente') == '"linea\\rsiguiente"'
    assert slot_spike.lua_quote('\t') == '"\\009"'
    assert slot_spike.lua_quote('\x00') == '"\\000"'
    assert slot_spike.lua_quote('\x7f') == '"\\127"'
    assert slot_spike.lua_quote('ñandú') == '"ñandú"'


def test_write_missing_slot_fails(tmp_path, capsys):
    assert _run(tmp_path, 'prepare', '1') == 0
    assert _run(tmp_path, 'write', '7', 'texto') != 0
    assert not (tmp_path / 'AskForever_Signals' / 'ready_007.tga').exists()
    assert 'No existe el slot' in capsys.readouterr().out


def test_unready_removes_signal(tmp_path, capsys):
    assert _run(tmp_path, 'prepare', '1') == 0
    assert _run(tmp_path, 'write', '1', 'hola') == 0
    signal = tmp_path / 'AskForever_Signals' / 'ready_001.tga'
    assert signal.is_file()

    assert _run(tmp_path, 'unready', '1') == 0
    assert not signal.exists()
    assert _run(tmp_path, 'unready', '1') == 0
    assert 'No había señal' in capsys.readouterr().out


def test_status_shows_empty_and_ready(tmp_path, capsys):
    assert _run(tmp_path, 'prepare', '2') == 0
    assert _run(tmp_path, 'status') == 0
    output = capsys.readouterr().out
    assert 'AskForever_Slot001: estado=empty, señal=no' in output
    assert 'AskForever_Slot002: estado=empty, señal=no' in output

    assert _run(tmp_path, 'write', '1', 'hola') == 0
    assert _run(tmp_path, 'status') == 0
    output = capsys.readouterr().out
    assert 'AskForever_Slot001: estado=ready, señal=sí' in output
    assert 'AskForever_Slot002: estado=empty, señal=no' in output

    (tmp_path / 'AskForever_Slot002' / 'data.lua').write_text(
        'AskForeverSlotData[2] = { state = "weird" }', encoding='utf-8')
    assert _run(tmp_path, 'status') == 0
    assert 'AskForever_Slot002: estado=desconocido' in capsys.readouterr().out


def test_clean_removes_only_marked_folders(tmp_path, capsys):
    assert _run(tmp_path, 'prepare', '2') == 0
    unmarked = tmp_path / 'AskForever_Slot777'
    unmarked.mkdir()
    (unmarked / 'nota.txt').write_text('no tocar', encoding='utf-8')
    other = tmp_path / 'OtroAddon'
    other.mkdir()
    (other / 'nota.txt').write_text('tampoco', encoding='utf-8')

    assert _run(tmp_path, 'clean') == 0
    assert not (tmp_path / 'AskForever_Slot001').exists()
    assert not (tmp_path / 'AskForever_Slot002').exists()
    assert not (tmp_path / 'AskForever_Signals').exists()
    assert (unmarked / 'nota.txt').read_text(encoding='utf-8') == 'no tocar'
    assert (other / 'nota.txt').read_text(encoding='utf-8') == 'tampoco'
    assert 'no tiene marcador' in capsys.readouterr().out


def test_missing_addons_folder_returns_2(tmp_path, capsys):
    missing = tmp_path / 'no_existe'
    assert slot_spike.main(['--addons', str(missing), 'status']) == 2
    assert 'No existe la carpeta de addons' in capsys.readouterr().out
