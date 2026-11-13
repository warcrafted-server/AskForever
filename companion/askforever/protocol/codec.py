"""Códec del protocolo v1 de la tira de píxeles: marcos, símbolos, rejilla y ensamblado."""

from __future__ import annotations

import time
import zlib
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from PIL import Image

COLS = 128
BLOCK = 4
MAX_ROWS = 8
SYNC = (0, 21, 42, 63, 51, 12, 51, 12)
MAX_PAYLOAD = 749
PROTOCOL_VERSION = 1

SIGNATURE = b'AF'
HEADER_SIZE = 9
CRC_SIZE = 4


@dataclass
class Frame:
    """Marco del protocolo: una página de un mensaje."""

    msg_id: int
    page: int
    pages: int
    payload: bytes


def crc32(data: bytes) -> int:
    """CRC-32 IEEE (polinomio de zlib), sin signo."""
    return zlib.crc32(data) & 0xFFFFFFFF


def encode_frame(msg_id: int, page: int, pages: int, payload: bytes) -> bytes:
    """Serializa una página; ValueError si la carga no cabe en una página."""
    payload = bytes(payload)
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f'payload too large: {len(payload)} > {MAX_PAYLOAD}')
    if not 0 <= msg_id <= 0xFFFF:
        raise ValueError('msg_id out of range')
    if not 0 <= page <= 0xFF:
        raise ValueError('page out of range')
    if not 1 <= pages <= 0xFF:
        raise ValueError('pages out of range')

    frame = bytearray(SIGNATURE)
    frame.append(PROTOCOL_VERSION)
    frame += msg_id.to_bytes(2, 'big')
    frame.append(page)
    frame.append(pages)
    frame += len(payload).to_bytes(2, 'big')
    frame += payload
    return bytes(frame) + crc32(frame).to_bytes(4, 'big')


def parse_frame(data: bytes) -> Optional[Frame]:
    """Decodifica un marco; None si la firma, versión, longitud o CRC no cuadran."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        return None
    data = bytes(data)
    if len(data) < HEADER_SIZE + CRC_SIZE:
        return None
    if data[0:2] != SIGNATURE or data[2] != PROTOCOL_VERSION:
        return None

    msg_id = int.from_bytes(data[3:5], 'big')
    page = data[5]
    pages = data[6]
    length = int.from_bytes(data[7:9], 'big')
    if pages < 1 or page >= pages or length > MAX_PAYLOAD:
        return None

    total = HEADER_SIZE + length + CRC_SIZE
    if len(data) < total:
        return None
    payload = data[HEADER_SIZE:HEADER_SIZE + length]
    expected = int.from_bytes(data[HEADER_SIZE + length:total], 'big')
    if expected != crc32(data[:HEADER_SIZE + length]):
        return None
    return Frame(msg_id, page, pages, payload)


def bytes_to_symbols(data: bytes) -> list[int]:
    """Empaqueta bytes en símbolos de 6 bits, bit más significativo primero."""
    symbols = []
    buffer = 0
    bits = 0
    for byte in bytes(data):
        buffer = (buffer << 8) | byte
        bits += 8
        while bits >= 6:
            bits -= 6
            symbols.append((buffer >> bits) & 0x3F)
        buffer &= (1 << bits) - 1
    if bits:
        symbols.append((buffer << (6 - bits)) & 0x3F)
    return symbols


def symbols_to_bytes(symbols: Sequence[int]) -> bytes:
    """Recompone bytes desde símbolos de 6 bits y descarta el relleno parcial final."""
    out = bytearray()
    buffer = 0
    bits = 0
    for symbol in symbols:
        buffer = (buffer << 6) | (int(symbol) & 0x3F)
        bits += 6
        while bits >= 8:
            bits -= 8
            out.append((buffer >> bits) & 0xFF)
        buffer &= (1 << bits) - 1
    return bytes(out)


def rows_for(n_data_symbols: int) -> int:
    """Filas necesarias para la sincronía más los símbolos de datos indicados."""
    rows = (len(SYNC) + max(0, int(n_data_symbols)) + COLS - 1) // COLS
    return max(1, min(MAX_ROWS, rows))


def paginate(message: bytes, msg_id: int) -> list[list[int]]:
    """Divide el mensaje en páginas y devuelve, por página, sus símbolos de datos."""
    message = bytes(message)
    if not message:
        raise ValueError('empty message')
    total = (len(message) + MAX_PAYLOAD - 1) // MAX_PAYLOAD
    if total > 255:
        raise ValueError('message needs more than 255 pages')

    pages = []
    for index in range(total):
        chunk = message[index * MAX_PAYLOAD:(index + 1) * MAX_PAYLOAD]
        pages.append(bytes_to_symbols(encode_frame(msg_id, index, total, chunk)))
    return pages


def symbols_to_image(data_symbols: Sequence[int], rows: int) -> Image.Image:
    """Imagen RGB de prueba con la sincronía delante y relleno con símbolo 0."""
    rows = max(1, min(int(rows), MAX_ROWS))
    symbols = list(SYNC) + [int(symbol) & 0x3F for symbol in data_symbols]
    if len(symbols) > rows * COLS:
        raise ValueError('too many symbols for the requested rows')
    symbols += [0] * (rows * COLS - len(symbols))

    image = Image.new('RGB', (COLS * BLOCK, rows * BLOCK))
    pixels = image.load()
    for index, symbol in enumerate(symbols):
        color = ((symbol >> 4 & 3) * 85, (symbol >> 2 & 3) * 85, (symbol & 3) * 85)
        x0 = (index % COLS) * BLOCK
        y0 = (index // COLS) * BLOCK
        for dy in range(BLOCK):
            for dx in range(BLOCK):
                pixels[x0 + dx, y0 + dy] = color
    return image


def _sample_offsets(block: int) -> tuple[tuple[int, int], ...]:
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


def _calibrate(image: Image.Image, block: int) -> Optional[dict]:
    """Niveles y umbrales por canal derivados de los cuatro grises de la sincronía."""
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


def _quantize(value: float, thresholds: Sequence[float]) -> int:
    if value < thresholds[0]:
        return 0
    if value < thresholds[1]:
        return 1
    if value < thresholds[2]:
        return 2
    return 3


def _symbol_at(image: Image.Image, block: int, col: int, row: int, calibration: dict) -> int:
    r, g, b = _block_mean(image, col * block, row * block, block)
    limits = calibration['thresholds']
    return (_quantize(r, limits['r']) << 4) | (_quantize(g, limits['g']) << 2) | _quantize(b, limits['b'])


def decode_grid(
    image: Image.Image,
    cols: int = COLS,
    rows: int = MAX_ROWS,
    block: int = BLOCK,
) -> Optional[list[int]]:
    """Símbolos de datos de todas las filas de la imagen, o None si la sincronía no cuadra."""
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

    if tuple(symbols[:len(SYNC)]) != SYNC:
        return None
    return symbols[len(SYNC):]


def decode_image(
    image: Image.Image,
    cols: int = COLS,
    rows: int = MAX_ROWS,
    block: int = BLOCK,
) -> Optional[Frame]:
    """Decodifica la imagen completa hasta el marco, o None si algo no cuadra."""
    data_symbols = decode_grid(image, cols, rows, block)
    if data_symbols is None:
        return None
    return parse_frame(symbols_to_bytes(data_symbols))


class Assembler:
    """Reensambla páginas por msg_id y entrega cada mensaje una vez cada ttl segundos."""

    def __init__(self, ttl: float = 60.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl = float(ttl)
        self.clock = clock
        self._pending: dict[int, dict] = {}
        self._delivered: dict[tuple[int, int], float] = {}

    def add(self, frame: Optional[Frame]) -> Optional[bytes]:
        """Añade una página; devuelve el mensaje completo la primera vez que se cierra."""
        try:
            return self._add(frame)
        except Exception:
            return None

    def _add(self, frame: Optional[Frame]) -> Optional[bytes]:
        if frame is None:
            return None
        now = self.clock()
        self._purge(now)

        msg_id = int(frame.msg_id)
        page = int(frame.page)
        pages = int(frame.pages)
        payload = bytes(frame.payload)
        if pages < 1 or page < 0 or page >= pages:
            return None

        entry = self._pending.get(msg_id)
        if entry is None:
            entry = {'pages': {}, 'total': pages, 'started': now}
            self._pending[msg_id] = entry
        elif entry['total'] != pages:
            return None

        if page not in entry['pages']:
            entry['pages'][page] = payload

        if len(entry['pages']) < entry['total']:
            return None
        if any(index not in entry['pages'] for index in range(entry['total'])):
            return None

        message = b''.join(entry['pages'][index] for index in range(entry['total']))
        del self._pending[msg_id]

        key = (msg_id, crc32(message))
        last = self._delivered.get(key)
        if last is not None and now - last <= self.ttl:
            return None
        self._delivered[key] = now
        return message

    def _purge(self, now: float) -> None:
        stale = [msg_id for msg_id, entry in self._pending.items() if now - entry['started'] > self.ttl]
        for msg_id in stale:
            del self._pending[msg_id]
        expired = [key for key, stamp in self._delivered.items() if now - stamp > self.ttl]
        for key in expired:
            del self._delivered[key]
