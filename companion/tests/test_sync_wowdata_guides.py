import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / 'tools' / 'sync_wowdata_guides.py'
_spec = importlib.util.spec_from_file_location('sync_wowdata_guides', _PATH)
sync_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync_tool)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def test_sync_copies_changes_and_new_reports_without_deleting(tmp_path):
    origin = tmp_path / 'wowdata' / 'entrada' / 'guias'
    dest = tmp_path / 'fuentes'
    _write(origin / 'guides' / 'classes' / 'a.md', 'nuevo')
    _write(origin / 'guides' / 'b.md', 'igual')
    _write(origin / 'wowhead-talents' / 'mage.json', '{}')
    for name in ('2026-11-24-0102.md', '2026-11-24-0102-resumen.md', '2026-11-24-0102.json',
                 '2026-11-23-1652.md', '2026-11-23-1652.json'):
        _write(origin / 'reports' / name, name)
    _write(dest / 'wowhead' / 'classes' / 'a.md', 'viejo')
    _write(dest / 'wowhead' / 'b.md', 'igual')
    _write(dest / 'wowhead' / 'retirada-level-20.md', 'se conserva')
    _write(dest / 'cambios' / '2026-11-23-1652.md', 'ya procesado')

    dry = sync_tool.sync(tmp_path / 'wowdata', dest, dry_run=True)
    assert (dest / 'wowhead' / 'classes' / 'a.md').read_text(encoding='utf-8') == 'viejo'
    assert dry['informes'] == ['2026-11-24-0102.md']

    result = sync_tool.sync(tmp_path / 'wowdata', dest)
    assert result['cambiadas'] == ['wowhead/classes/a.md']
    assert result['nuevas'] == ['wowhead-talents/mage.json']
    assert result['informes'] == ['2026-11-24-0102.md']
    assert (dest / 'wowhead' / 'classes' / 'a.md').read_text(encoding='utf-8') == 'nuevo'
    assert (dest / 'wowhead' / 'retirada-level-20.md').is_file()
    assert (dest / 'cambios' / '2026-11-24-0102-resumen.md').is_file()
    assert (dest / 'cambios' / '2026-11-23-1652.md').read_text(encoding='utf-8') == 'ya procesado'

    again = sync_tool.sync(tmp_path / 'wowdata', dest)
    assert again == {'nuevas': [], 'cambiadas': [], 'informes': []}
