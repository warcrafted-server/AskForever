#!/usr/bin/env python3
"""Paquete de secciones del corpus privado para redactar fichas: guías vigentes y secciones no repetidas.

Cada enlace con ID lleva detrás su nombre oficial en español de España («{esES: …}», de wowdata por ID). Al final va un
complemento con las guías de Icy Veins sustituidas por Wowhead, para conservar los datos que Wowhead no trae.

    python tools/kb_pack.py --topic "class:hunter:%" --skip abilities,bis,enchants --out ../.agents/corpus/packs/hunter.md
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kb_names import OfficialNames, TalentBuilds  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = REPO_ROOT / '.agents' / 'corpus' / 'corpus.sqlite'


def build_pack(corpus: Path, patterns: list[str], skip: set[str],
               names: Optional[OfficialNames] = None) -> str:
    conn = sqlite3.connect(f'file:{corpus.as_posix()}?mode=ro', uri=True)
    builds = TalentBuilds(names.conn) if names else None
    annotate = (lambda text: builds.annotate_tables(builds.annotate(names.annotate(text)))
                if names else (lambda text: text))
    where = ' OR '.join('g.topic LIKE ?' for _ in patterns)
    lines = []
    for superseded, header in ((False, ''), (True, 'Complemento · ')):
        guides = conn.execute(
            f'SELECT guide_key, source, title, url, updated, topic, superseded_by FROM guides g '
            f'WHERE superseded_by IS {"NOT " if superseded else ""}NULL AND ({where}) '
            "ORDER BY CASE source WHEN 'wowhead' THEN 0 ELSE 1 END, topic, guide_key", patterns).fetchall()
        if superseded and guides:
            lines += ['# COMPLEMENTO: guías de Icy Veins sustituidas por Wowhead', '',
                      'Úsalas solo para conservar datos que Wowhead no trae y no contradice.', '']
        for guide_key, source, title, url, updated, topic, superseded_by in guides:
            if topic.rsplit(':', 1)[-1] in skip:
                continue
            lines += [f'# {header}{topic} · {source}', '', f'- guía: `{guide_key}`', f'- título: {title}',
                      f'- url: {url}', f'- actualizada: {updated}']
            if superseded_by:
                lines.append(f'- sustituida por: `{superseded_by}`')
            lines.append('')
            for heading_path, text in conn.execute(
                    'SELECT heading_path, text FROM sections WHERE guide_key = ? AND duplicate_of IS NULL '
                    'ORDER BY ord', (guide_key,)):
                lines += [f'## › {heading_path or "(intro)"}', '', annotate(text.strip()), '']
    conn.close()
    return '\n'.join(lines) + '\n'


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--corpus', type=Path, default=DEFAULT_CORPUS)
    parser.add_argument('--topic', action='append', required=True, help='patrón LIKE de tema (repetible)')
    # Las guías de nivel 20 y 30 son de la beta y no se usan (decisión de Marc, 2026-11-16).
    parser.add_argument('--skip', default='level20,level30',
                        help='aspectos finales de tema que se omiten, separados por comas')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--wowdb', type=Path, default=None, help='wow.sqlite de wowdata (nombres esES)')
    args = parser.parse_args(argv)
    text = build_pack(args.corpus, args.topic, {s for s in args.skip.split(',') if s}, OfficialNames(args.wowdb))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding='utf-8')
    print(f'{args.out}: {len(text)} caracteres')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
