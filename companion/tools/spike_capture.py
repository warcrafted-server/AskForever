#!/usr/bin/env python3
"""Spike de diagnóstico: lee la tira de colores de /af pattern y cuenta los errores."""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from PIL import Image

COMPANION_ROOT = Path(__file__).resolve().parent.parent
if str(COMPANION_ROOT) not in sys.path:
    sys.path.insert(0, str(COMPANION_ROOT))

from askforever.capture.window import GameWindow, client_region_for, find_game_window

SYNC_SYMBOLS = (0, 21, 42, 63, 51, 12, 51, 12)
DATA_SYMBOLS = 1016
MAX_SHIFT = 16


def _sample_offsets(block: int) -> tuple[tuple[int, int], ...]:
    """Desplazamientos de los píxeles centrales que se muestrean dentro de cada bloque."""
    if block >= 2:
        start = block // 2 - 1
        return ((start, start), (start + 1, start), (start, start + 1), (start + 1, start + 1))
    return ((0, 0),)


def _block_mean(image: Image.Image, x0: int, y0: int, block: int) -> tuple[float, float, float]:
    offsets = _sample_offsets(block)
    total_r = total_g = total_b = 0.0
    for dx, dy in offsets:
        pixel = image.getpixel((x0 + dx, y0 + dy))
        total_r += pixel[0]
        total_g += pixel[1]
        total_b += pixel[2]
    count = float(len(offsets))
    return total_r / count, total_g / count, total_b / count


def _quantize(value: float, thresholds: Sequence[float]) -> int:
    if value < thresholds[0]:
        return 0
    if value < thresholds[1]:
        return 1
    if value < thresholds[2]:
        return 2
    return 3


def _calibrate(image: Image.Image, block: int) -> Optional[dict]:
    """Deriva niveles y umbrales de los cuatro bloques grises de la sincronía."""
    levels = {'r': [], 'g': [], 'b': []}
    for level in range(4):
        r, g, b = _block_mean(image, level * block, 0, block)
        levels['r'].append(r)
        levels['g'].append(g)
        levels['b'].append(b)

    for values in levels.values():
        for index in range(3):
            if values[index + 1] - values[index] < 30:
                return None

    thresholds = {}
    for channel, values in levels.items():
        thresholds[channel] = [
            (values[0] + values[1]) / 2,
            (values[1] + values[2]) / 2,
            (values[2] + values[3]) / 2,
        ]
    return {'levels': levels, 'thresholds': thresholds}


def _symbol_at(image: Image.Image, block: int, col: int, row: int, calibration: dict) -> int:
    r, g, b = _block_mean(image, col * block, row * block, block)
    limits = calibration['thresholds']
    return (_quantize(r, limits['r']) << 4) | (_quantize(g, limits['g']) << 2) | _quantize(b, limits['b'])


def decode_grid(
    image: Image.Image,
    cols: int,
    rows: int,
    block: int,
) -> Optional[tuple[list[int], dict]]:
    """Decodifica la rejilla de bloques; devuelve símbolos y calibración, o None."""
    if cols < 1 or rows < 1 or block < 1:
        return None
    width, height = image.size
    if width < cols * block or height < rows * block:
        return None

    calibration = _calibrate(image, block)
    if calibration is None:
        return None

    symbols = []
    for row in range(rows):
        for col in range(cols):
            symbols.append(_symbol_at(image, block, col, row, calibration))

    if tuple(symbols[:len(SYNC_SYMBOLS)]) != SYNC_SYMBOLS:
        return None
    return symbols, calibration


def _sync_quality(image: Image.Image, cols: int, rows: int, block: int) -> Optional[float]:
    """Puntuación de la sincronía, o None si no cuadra; mayor = bloques mejor centrados."""
    width, height = image.size
    if width < cols * block or height < rows * block:
        return None
    calibration = _calibrate(image, block)
    if calibration is None:
        return None
    symbol_count = len(SYNC_SYMBOLS)
    synchronisation = tuple(_symbol_at(image, block, index, 0, calibration) for index in range(symbol_count))
    if synchronisation != SYNC_SYMBOLS:
        return None
    quality = 0.0
    for values in calibration['levels'].values():
        for index in range(3):
            quality += values[index + 1] - values[index]
    return quality


def count_errors(symbols: Sequence[int]) -> int:
    """Errores de los símbolos de datos frente al patrón de prueba i % 64."""
    errors = 0
    for index in range(DATA_SYMBOLS):
        expected = index % 64
        position = len(SYNC_SYMBOLS) + index
        actual = symbols[position] if position < len(symbols) else -1
        if actual != expected:
            errors += 1
    return errors


def _make_test_image(cols: int, rows: int, block: int) -> Image.Image:
    """Imagen sintética con la sincronía y el patrón de prueba."""
    symbols = list(SYNC_SYMBOLS) + [index % 64 for index in range(DATA_SYMBOLS)]
    total = cols * rows
    symbols = symbols[:total] + [0] * max(0, total - len(symbols))

    image = Image.new('RGB', (cols * block, rows * block))
    pixels = image.load()
    for index, symbol in enumerate(symbols):
        color = ((symbol >> 4 & 3) * 85, (symbol >> 2 & 3) * 85, (symbol & 3) * 85)
        x0 = (index % cols) * block
        y0 = (index // cols) * block
        for dy in range(block):
            for dx in range(block):
                pixels[x0 + dx, y0 + dy] = color
    return image


def _add_noise(image: Image.Image, amplitude: int = 25, seed: int = 1234) -> Image.Image:
    """Copia con ruido uniforme ±amplitude por canal."""
    rng = random.Random(seed)
    noisy = image.copy()
    pixels = noisy.load()
    width, height = noisy.size
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            pixels[x, y] = (
                max(0, min(255, r + rng.randint(-amplitude, amplitude))),
                max(0, min(255, g + rng.randint(-amplitude, amplitude))),
                max(0, min(255, b + rng.randint(-amplitude, amplitude))),
            )
    return noisy


def _apply_gamma(image: Image.Image, gamma: float) -> Image.Image:
    """Aplica una curva gamma a la imagen (simula otro perfil de color)."""
    return image.point(lambda value: int(round(255.0 * (value / 255.0) ** gamma)))


def run_selftest() -> int:
    """Comprueba el decodificador con imágenes sintéticas conocidas."""
    base = _make_test_image(128, 8, 4)
    cases = [
        ('patrón limpio', base),
        ('ruido ±25', _add_noise(base, 25, 1234)),
        ('gamma 0.85', _apply_gamma(base, 0.85)),
        ('gamma 1.15', _apply_gamma(base, 1.15)),
    ]
    failures = 0
    for name, case_image in cases:
        result = decode_grid(case_image, 128, 8, 4)
        if result is None:
            print(f'FALLO {name}: sincronía no válida')
            failures += 1
            continue
        symbols, _calibration = result
        errors = count_errors(symbols)
        if errors:
            print(f'FALLO {name}: {errors} errores de símbolo')
            failures += 1
        else:
            print(f'OK {name}')
    return 0 if failures == 0 else 1


def _region(window: GameWindow, dx: int, dy: int, width: int, height: int) -> dict:
    """Región mss desplazada dentro del área cliente y recortada a ella."""
    return {
        'left': window.x + dx,
        'top': window.y + dy,
        'width': max(1, min(width, window.width - dx)),
        'height': max(1, min(height, window.height - dy)),
    }


def _grab(sct, region: dict) -> Image.Image:
    shot = sct.grab(region)
    return Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')


def _find_offset(sct, window: GameWindow, width: int, height: int, cols: int, rows: int, block: int):
    """Busca la tira en la esquina y hasta MAX_SHIFT píxeles a la derecha y abajo."""
    region = {
        'left': window.x,
        'top': window.y,
        'width': max(1, min(width + MAX_SHIFT, window.width)),
        'height': max(1, min(height + MAX_SHIFT, window.height)),
    }
    image = _grab(sct, region)
    best = None
    best_quality = None
    for dy in range(MAX_SHIFT + 1):
        for dx in range(MAX_SHIFT + 1):
            if image.size[0] < dx + width or image.size[1] < dy + height:
                continue
            patch = image.crop((dx, dy, dx + width, dy + height))
            quality = _sync_quality(patch, cols, rows, block)
            if quality is not None and (best_quality is None or quality > best_quality):
                best = (dx, dy)
                best_quality = quality
    return best


def _format_values(values: Sequence[float]) -> str:
    return '[' + ', '.join(f'{value:.1f}' for value in values) + ']'


def _save_image(image: Image.Image) -> Path:
    out_dir = Path(__file__).resolve().parent / 'out'
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f'strip_{datetime.now():%Y%m%d_%H%M%S}.png'
    image.save(path)
    return path


def run_capture(args: argparse.Namespace) -> int:
    """Flujo normal: localiza el juego, espera la sincronía y mide los errores."""
    window = find_game_window()
    if window is None:
        print('No se encontró la ventana del juego (Wow.exe). Abre el juego y vuelve a intentarlo.')
        return 2
    print(f'Ventana: {window.title!r}')
    print(f'Área cliente: {window.width}x{window.height} en ({window.x}, {window.y})')

    width = args.cols * args.block
    height = args.rows * args.block

    import mss

    factory = getattr(mss, 'MSS', None) or mss.mss
    with factory() as sct:
        deadline = time.monotonic() + max(args.wait, 0.0)
        offset = None
        while True:
            offset = _find_offset(sct, window, width, height, args.cols, args.rows, args.block)
            if offset is not None:
                break
            if time.monotonic() >= deadline:
                break
            print('.', end='', flush=True)
            time.sleep(1.0)

        if offset is None:
            print()
            print('No apareció la sincronía de la tira en la esquina del área cliente.')
            print('Abre el juego, ejecuta /af pattern y vuelve a lanzar la herramienta.')
            return 2

        dx, dy = offset
        if dx or dy:
            print()
            print(f'Sincronía encontrada con desplazamiento (+{dx}, +{dy}) px.')
        else:
            print('Sincronía encontrada en la esquina del área cliente.')

        captures = 0
        valid = 0
        best_errors = None
        best_image = None
        best_calibration = None
        start = time.monotonic()
        while time.monotonic() - start < args.duration:
            image = _grab(sct, _region(window, dx, dy, width, height))
            captures += 1
            result = decode_grid(image, args.cols, args.rows, args.block)
            if result is None:
                continue
            symbols, calibration = result
            valid += 1
            errors = count_errors(symbols)
            if best_errors is None or errors < best_errors:
                best_errors = errors
                best_image = image
                best_calibration = calibration
        elapsed = max(time.monotonic() - start, 1e-9)

    print(f'Capturas: {captures}')
    print(f'FPS medios: {captures / elapsed:.1f}')
    print(f'Capturas con sincronía válida: {valid}')

    if best_image is None or best_errors is None or best_calibration is None:
        print('No se capturó ningún marco con sincronía válida.')
        return 2

    levels = best_calibration['levels']
    thresholds = best_calibration['thresholds']
    print(f'Mejor marco: {best_errors} errores de símbolo (patrón esperado i % 64).')
    print(f"Grises medidos 0..3: R={_format_values(levels['r'])} "
          f"G={_format_values(levels['g'])} B={_format_values(levels['b'])}")
    print(f"Umbrales: R={_format_values(thresholds['r'])} "
          f"G={_format_values(thresholds['g'])} B={_format_values(thresholds['b'])}")
    path = _save_image(best_image)
    print(f'Imagen guardada en {path}')

    return 0 if best_errors == 0 else 1


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Diagnóstico de la captura de la tira de colores de AskForever (/af pattern).'
    )
    parser.add_argument('--wait', type=float, default=30.0,
                        help='segundos esperando a que aparezca la sincronía (por defecto 30)')
    parser.add_argument('--duration', type=float, default=10.0,
                        help='segundos de captura tras detectar la sincronía (por defecto 10)')
    parser.add_argument('--block', type=int, default=4,
                        help='tamaño de bloque en píxeles (por defecto 4)')
    parser.add_argument('--cols', type=int, default=128,
                        help='columnas de la tira (por defecto 128)')
    parser.add_argument('--rows', type=int, default=8,
                        help='filas de la tira (por defecto 8)')
    parser.add_argument('--selftest', action='store_true',
                        help='prueba el decodificador con imágenes sintéticas, sin juego')
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    if args.block < 1 or args.cols < 1 or args.rows < 1:
        print('Los valores de --block, --cols y --rows deben ser mayores que cero.')
        return 2
    if args.selftest:
        return run_selftest()
    return run_capture(args)


if __name__ == '__main__':
    sys.exit(main())
