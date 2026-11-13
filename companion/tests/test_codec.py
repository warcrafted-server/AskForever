"""Pruebas del códec del protocolo de la tira de píxeles."""

from __future__ import annotations

import random

import pytest
from PIL import Image

from askforever.protocol import codec

REFERENCE_HEX = '41460100010001000a7b2271223a226869227d4173a9ec'
REFERENCE_SYMBOLS = [
    16, 20, 24, 1, 0, 0, 4, 0, 0, 16, 0, 10, 30, 50, 9, 49,
    8, 35, 40, 34, 26, 6, 36, 34, 31, 20, 5, 51, 42, 30, 48,
]


def _page_image(frame_bytes: bytes):
    data_symbols = codec.bytes_to_symbols(frame_bytes)
    rows = codec.rows_for(len(data_symbols))
    return codec.symbols_to_image(data_symbols, rows), rows


def _frames_for(message: bytes, msg_id: int) -> list[codec.Frame]:
    frames = []
    for symbols in codec.paginate(message, msg_id):
        frame = codec.parse_frame(codec.symbols_to_bytes(symbols))
        assert frame is not None
        frames.append(frame)
    return frames


def _add_noise(image: Image.Image, amplitude: int = 30, seed: int = 2024) -> Image.Image:
    rng = random.Random(seed)
    noisy = image.copy()
    pixels = noisy.load()
    for y in range(noisy.height):
        for x in range(noisy.width):
            r, g, b = pixels[x, y]
            pixels[x, y] = (
                max(0, min(255, r + rng.randint(-amplitude, amplitude))),
                max(0, min(255, g + rng.randint(-amplitude, amplitude))),
                max(0, min(255, b + rng.randint(-amplitude, amplitude))),
            )
    return noisy


def _gamma(image: Image.Image, value: float) -> Image.Image:
    return image.point(lambda channel: int(round(255.0 * (channel / 255.0) ** value)))


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_reference_frame_bytes_and_symbols():
    frame = codec.encode_frame(1, 0, 1, b'{"q":"hi"}')
    assert frame.hex() == REFERENCE_HEX
    assert codec.crc32(frame[:19]) == 0x4173A9EC
    assert codec.bytes_to_symbols(frame) == REFERENCE_SYMBOLS
    assert codec.parse_frame(frame) == codec.Frame(1, 0, 1, b'{"q":"hi"}')
    assert codec.parse_frame(codec.symbols_to_bytes(REFERENCE_SYMBOLS)) == codec.Frame(
        1, 0, 1, b'{"q":"hi"}'
    )


def test_crc32_reference():
    assert codec.crc32(b'123456789') == 0xCBF43926


@pytest.mark.parametrize('length', range(0, 41))
def test_bytes_symbols_round_trip(length):
    data = bytes((index * 37 + 11) & 0xFF for index in range(length))
    assert codec.symbols_to_bytes(codec.bytes_to_symbols(data)) == data


def test_frame_round_trip():
    frame = codec.encode_frame(42, 1, 3, b'payload')
    assert codec.parse_frame(frame) == codec.Frame(42, 1, 3, b'payload')


def test_parse_frame_rejects_bad_data():
    good = codec.encode_frame(7, 0, 1, b'abc')

    bad_crc = bytearray(good)
    bad_crc[-1] ^= 0xFF
    assert codec.parse_frame(bytes(bad_crc)) is None

    version = bytearray(good)
    version[2] = 2
    assert codec.parse_frame(bytes(version)) is None

    signature = bytearray(good)
    signature[0] = ord('B')
    assert codec.parse_frame(bytes(signature)) is None

    assert codec.parse_frame(good[:-1]) is None
    assert codec.parse_frame(b'') is None
    assert codec.parse_frame(bytearray(codec.encode_frame(1, 0, 1, b'x') + b'\x00\x00')) is not None


def test_payload_capacity():
    assert len(codec.encode_frame(1, 0, 1, b'x' * codec.MAX_PAYLOAD)) == 9 + codec.MAX_PAYLOAD + 4
    with pytest.raises(ValueError):
        codec.encode_frame(1, 0, 1, b'x' * (codec.MAX_PAYLOAD + 1))


@pytest.mark.parametrize('size,expected_pages', [(1, 1), (749, 1), (750, 2), (1400, 2), (3000, 5)])
def test_paginate_sizes_and_reassembly(size, expected_pages):
    message = bytes((index * 7) & 0xFF for index in range(size))
    pages = codec.paginate(message, 9)
    assert len(pages) == expected_pages

    assembler = codec.Assembler()
    delivered = None
    for symbols in pages:
        frame = codec.parse_frame(codec.symbols_to_bytes(symbols))
        assert frame is not None
        delivered = assembler.add(frame)
    assert delivered == message


def test_paginate_empty_message():
    with pytest.raises(ValueError):
        codec.paginate(b'', 1)


def test_paginate_rejects_more_than_255_pages():
    message = b'x' * (255 * codec.MAX_PAYLOAD + 1)
    with pytest.raises(ValueError):
        codec.paginate(message, 1)


def test_rows_for():
    assert codec.rows_for(1016) == 8
    assert codec.rows_for(31) == 1
    assert codec.rows_for(120) == 1
    assert codec.rows_for(121) == 2


def test_decode_synthetic_image():
    frame_bytes = codec.encode_frame(5, 0, 1, b'{"q":"hello"}')
    image, rows = _page_image(frame_bytes)
    assert codec.decode_image(image, codec.COLS, rows, codec.BLOCK) == codec.Frame(
        5, 0, 1, b'{"q":"hello"}'
    )
    data_symbols = codec.decode_grid(image, codec.COLS, rows, codec.BLOCK)
    assert data_symbols is not None
    assert len(data_symbols) == rows * codec.COLS - len(codec.SYNC)


def test_decode_full_page():
    payload = bytes((index * 19 + 3) & 0xFF for index in range(codec.MAX_PAYLOAD))
    frame_bytes = codec.encode_frame(6, 0, 1, payload)
    image, rows = _page_image(frame_bytes)
    assert rows == codec.MAX_ROWS
    assert codec.decode_image(image, codec.COLS, rows, codec.BLOCK) == codec.Frame(6, 0, 1, payload)


@pytest.mark.parametrize('transform', [
    lambda image: _add_noise(image, 30, 2024),
    lambda image: _gamma(image, 0.8),
    lambda image: _gamma(image, 1.2),
])
def test_decode_survives_noise_and_gamma(transform):
    frame_bytes = codec.encode_frame(8, 0, 1, b'{"q":"colour"}')
    image, rows = _page_image(frame_bytes)
    assert codec.decode_image(transform(image), codec.COLS, rows, codec.BLOCK) == codec.Frame(
        8, 0, 1, b'{"q":"colour"}'
    )


def test_altered_data_block_fails_crc():
    frame_bytes = codec.encode_frame(2, 0, 1, b'{"q":"hi"}')
    image, rows = _page_image(frame_bytes)
    pixels = image.load()
    for dy in range(codec.BLOCK):
        for dx in range(codec.BLOCK):
            pixels[len(codec.SYNC) * codec.BLOCK + dx, dy] = (255, 0, 0)

    assert codec.decode_grid(image, codec.COLS, rows, codec.BLOCK) is not None
    assert codec.decode_image(image, codec.COLS, rows, codec.BLOCK) is None


def test_image_without_sync():
    image = Image.new('RGB', (codec.COLS * codec.BLOCK, codec.MAX_ROWS * codec.BLOCK), (10, 20, 30))
    assert codec.decode_grid(image, codec.COLS, codec.MAX_ROWS, codec.BLOCK) is None


def test_assembler_delivers_once_and_after_ttl():
    message = bytes((index * 13) & 0xFF for index in range(1600))
    frames = _frames_for(message, 3)
    assert len(frames) == 3

    clock = FakeClock()
    assembler = codec.Assembler(ttl=10.0, clock=clock)
    assert assembler.add(frames[2]) is None
    assert assembler.add(frames[0]) is None
    assert assembler.add(frames[2]) is None
    assert assembler.add(frames[1]) == message

    assert assembler.add(frames[1]) is None
    assert assembler.add(frames[0]) is None
    assert assembler.add(frames[2]) is None

    clock.advance(10.5)
    assert assembler.add(frames[0]) is None
    assert assembler.add(frames[1]) is None
    assert assembler.add(frames[2]) == message


def test_assembler_keeps_first_duplicate_page():
    message = b'A' * 800
    frames = _frames_for(message, 4)
    assert len(frames) == 2

    assembler = codec.Assembler(clock=FakeClock())
    alternative = codec.Frame(4, 0, 2, b'X' * codec.MAX_PAYLOAD)
    assert assembler.add(frames[0]) is None
    assert assembler.add(alternative) is None
    assert assembler.add(frames[1]) == message


def test_assembler_incomplete_messages_expire():
    message = bytes(range(200)) * 8
    frames = _frames_for(message, 5)
    assert len(frames) == 3

    clock = FakeClock()
    assembler = codec.Assembler(ttl=5.0, clock=clock)
    assert assembler.add(frames[0]) is None
    clock.advance(6.0)
    assert assembler.add(frames[1]) is None
    assert assembler.add(frames[2]) is None
    assert assembler.add(frames[0]) == message


def test_assembler_ignores_invalid_frames():
    assembler = codec.Assembler(clock=FakeClock())
    assert assembler.add(None) is None
    assert assembler.add(codec.Frame(1, 3, 2, b'x')) is None
    assert assembler.add(codec.Frame(2, 0, 0, b'x')) is None
    assert assembler.add(codec.Frame(3, -1, 1, b'x')) is None
    assert assembler.add(codec.Frame(9, 0, 2, b'a')) is None
    assert assembler.add(codec.Frame(9, 1, 3, b'b')) is None
