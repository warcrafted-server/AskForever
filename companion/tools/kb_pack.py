#!/usr/bin/env python3
"""Paquete de secciones del corpus privado para redactar fichas: solo guías no sustituidas y secciones no repetidas.

    python tools/kb_pack.py --topic "class:hunter:%" --skip abilities,bis,enchants --out ../.agents/corpus/packs/hunter.md
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = REPO_ROOT / '.agents' / 'corpus' / 'corpus.sqlite'


def build_pack(corpus: Path, patterns: list[str], skip: set[str]) -> str:
    conn = sqlite3.connect(f'file:{corpus.as_posix()}?mode=ro', uri=True)
    where = ' OR '.join('g.topic LIKE ?' for _ in patterns)
    guides = conn.execute(
        f'SELECT guide_key, source, title, url, updated, topic FROM guides g '
        f'WHERE superseded_by IS NULL AND ({where}) '
        "ORDER BY CASE source WHEN 'wowhead' THEN 0 ELSE 1 END, topic, guide_key", patterns).fetchall()
    lines = []
    for guide_key, source, title, url, updated, topic in guides:
        if topic.rsplit(':', 1)[-1] in skip:
            continue
        lines += [f'# {topic} · {source}', '', f'- guía: `{guide_key}`', f'- título: {title}',
                  f'- url: {url}', f'- actualizada: {updated}', '']
        for heading_path, text in conn.execute(
                'SELECT heading_path, text FROM sections WHERE guide_key = ? AND duplicate_of IS NULL '
                'ORDER BY ord', (guide_key,)):
            lines += [f'## › {heading_path or "(intro)"}', '', text.strip(), '']
    conn.close()
    return '\n'.join(lines) + '\n'


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--corpus', type=Path, default=DEFAULT_CORPUS)
    parser.add_argument('--topic', action='append', required=True, help='patrón LIKE de tema (repetible)')
    parser.add_argument('--skip', default='', help='aspectos finales de tema que se omiten, separados por comas')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    text = build_pack(args.corpus, args.topic, {s for s in args.skip.split(',') if s})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding='utf-8')
    print(f'{args.out}: {len(text)} caracteres')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
