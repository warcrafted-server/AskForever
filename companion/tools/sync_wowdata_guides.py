#!/usr/bin/env python3
"""Trae a las fuentes de AskForever las guías y los informes que wowdata copió del VPS.

    python -X utf8 tools/sync_wowdata_guides.py [--wowdata CARPETA] [--dry-run]

Origen: <wowdata>/entrada/guias/ (guides/, wowhead-talents/, reports/), espejo del VPS.
Destino: .agents/plans/guia/fuentes/ (wowhead/, wowhead-talents/, cambios/).

Copia las guías nuevas o con contenido distinto y los informes que falten. Nunca borra: una guía retirada
del VPS se queda aquí, porque una fuente retirada sin otra más nueva no caduca las fichas que la citan.
Imprime como última línea un JSON con lo copiado y los informes nuevos, de más viejo a más nuevo, para
pasarlos uno a uno a guide_update.py --report.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WOWDATA = REPO_ROOT.parents[1] / 'wowdata'
DEFAULT_DEST = REPO_ROOT / '.agents' / 'plans' / 'guia' / 'fuentes'
MIRRORS = (('guides', 'wowhead'), ('wowhead-talents', 'wowhead-talents'))


def _same(a: Path, b: Path) -> bool:
    return b.is_file() and a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes()


def sync(wowdata: Path, dest: Path, dry_run: bool = False) -> dict:
    origin = wowdata / 'entrada' / 'guias'
    if not (origin / 'guides').is_dir():
        raise FileNotFoundError(f'No hay guías de wowdata en {origin}')
    result = {'nuevas': [], 'cambiadas': [], 'informes': []}
    for src_name, dst_name in MIRRORS:
        src_root = origin / src_name
        if not src_root.is_dir():
            continue
        for src in sorted(src_root.rglob('*')):
            if not src.is_file():
                continue
            rel = src.relative_to(src_root)
            dst = dest / dst_name / rel
            if _same(src, dst):
                continue
            result['cambiadas' if dst.exists() else 'nuevas'].append(f'{dst_name}/{rel.as_posix()}')
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
    reports = origin / 'reports'
    stamps = sorted(p.stem for p in reports.glob('*.json') if p.stem[:4].isdigit()) if reports.is_dir() else []
    for stamp in stamps:
        if (dest / 'cambios' / f'{stamp}.md').exists():
            continue
        result['informes'].append(f'{stamp}.md')
        if not dry_run:
            (dest / 'cambios').mkdir(parents=True, exist_ok=True)
            for name in (f'{stamp}.md', f'{stamp}-resumen.md', f'{stamp}.json'):
                if (reports / name).is_file():
                    shutil.copy2(reports / name, dest / 'cambios' / name)
    return result


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--wowdata', type=Path,
                        default=Path(os.environ.get('WOWDATA_DIR') or DEFAULT_WOWDATA))
    parser.add_argument('--dest', type=Path, default=DEFAULT_DEST)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = sync(args.wowdata, args.dest, args.dry_run)
    except (OSError, FileNotFoundError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    print(f"Guías nuevas: {len(result['nuevas'])} · cambiadas: {len(result['cambiadas'])} · "
          f"informes nuevos: {len(result['informes'])}" + (' (sin copiar: --dry-run)' if args.dry_run else ''))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
