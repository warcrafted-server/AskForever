"""Genera el icono .ico del companion a partir del logo del repositorio."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / 'docs' / 'img' / 'logo.png'
OUTPUT = Path(__file__).resolve().parent / 'askforever.ico'
SIZES = (16, 24, 32, 48, 64, 128, 256)


def main() -> int:
    with Image.open(SOURCE) as image:
        sizes = [(size, size) for size in SIZES]
        image.convert('RGBA').save(OUTPUT, format='ICO', sizes=sizes)
    print(f'Icono generado: {OUTPUT}')
    print('Tamaños: ' + ', '.join(str(size) for size in SIZES))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
