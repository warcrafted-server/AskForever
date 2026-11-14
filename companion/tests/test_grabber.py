"""Pruebas del receptor continuo y del formateo de mensajes de la CLI."""

from __future__ import annotations

import json
import random
import threading
import time

from PIL import Image

import askforever.cli as cli
from askforever.capture.grabber import Grabber
from askforever.cli import format_message
from askforever.protocol import codec


class SequenceCapture:
    """capture_fn de prueba que repite una secuencia de imágenes."""

    def __init__(self, images):
        self.images = list(images)
        self.index = 0

    def __call__(self):
        image = self.images[self.index % len(self.images)]
        self.index += 1
        return image


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _page_images(message: bytes, msg_id: int) -> list[Image.Image]:
    return [codec.symbols_to_image(symbols, codec.MAX_ROWS) for symbols in codec.paginate(message, msg_id)]


def _noise_image(seed: int = 7) -> Image.Image:
    rng = random.Random(seed)
    data = bytes(rng.randrange(256) for _ in range(512 * 32 * 3))
    return Image.frombytes('RGB', (512, 32), data)


def test_single_page_repeated():
    message = b'{"q":"hi"}'
    image = _page_images(message, 1)[0]
    received = []
    grabber = Grabber(received.append, capture_fn=lambda: image)

    for _ in range(20):
        grabber.step()

    assert len(received) == 1
    assert received[0].msg_id == 1
    assert received[0].pages == 1
    assert received[0].data == message
    assert grabber.captures == 20
    assert grabber.valid_frames == 20
    assert grabber.messages == 1
    assert grabber.errors == 0


def test_three_page_carousel():
    message = bytes((index * 13) & 0xFF for index in range(1600))
    images = _page_images(message, 2)
    assert len(images) == 3

    received = []
    grabber = Grabber(received.append, capture_fn=SequenceCapture(images))
    for _ in range(12):
        grabber.step()

    assert len(received) == 1
    assert received[0].msg_id == 2
    assert received[0].pages == 3
    assert received[0].data == message
    assert grabber.messages == 1


def test_two_messages_in_order():
    first = _page_images(b'{"q":"one"}', 1)[0]
    second = _page_images(b'{"q":"two"}', 2)[0]
    received = []
    grabber = Grabber(received.append, capture_fn=SequenceCapture([first, first, second, second]))

    for _ in range(4):
        grabber.step()

    assert [message.msg_id for message in received] == [1, 2]
    assert [message.data for message in received] == [b'{"q":"one"}', b'{"q":"two"}']


def test_none_and_noise_images():
    noise = _noise_image()
    uniform = Image.new('RGB', (512, 32), (12, 34, 56))
    received = []
    grabber = Grabber(received.append, capture_fn=SequenceCapture([None, noise, uniform, None]))

    for _ in range(8):
        grabber.step()

    assert received == []
    assert grabber.messages == 0
    assert grabber.errors == 0
    assert grabber.valid_frames == 0


def test_corrupted_frame_is_ignored():
    message = b'{"q":"damaged"}'
    good = _page_images(message, 3)[0]
    damaged = good.copy()
    pixels = damaged.load()
    first_data_column = len(codec.SYNC) * codec.BLOCK
    for y in range(codec.BLOCK):
        for x in range(first_data_column, first_data_column + codec.BLOCK):
            pixels[x, y] = (170, 0, 0)

    received = []
    grabber = Grabber(received.append, capture_fn=SequenceCapture([damaged, good]))

    grabber.step()
    assert received == []
    grabber.step()

    assert len(received) == 1
    assert received[0].data == message
    assert grabber.captures == 2
    assert grabber.valid_frames == 1


def test_counters_are_coherent():
    message = b'{"q":"counters"}'
    image = _page_images(message, 4)[0]
    noise = _noise_image()
    received = []
    capture = SequenceCapture([None, image, noise, image])
    grabber = Grabber(received.append, capture_fn=capture)

    for _ in range(8):
        grabber.step()

    assert grabber.captures == 6
    assert grabber.valid_frames == 4
    assert grabber.messages == 1
    assert grabber.errors == 0
    assert grabber.valid_frames <= grabber.captures


def test_first_seen_and_completed():
    message = bytes((index * 3) & 0xFF for index in range(1000))
    images = _page_images(message, 5)
    assert len(images) == 2

    clock = FakeClock()
    received = []
    grabber = Grabber(received.append, capture_fn=SequenceCapture(images), clock=clock)

    grabber.step()
    clock.advance(0.5)
    grabber.step()

    assert len(received) == 1
    assert received[0].first_seen == 0.0
    assert received[0].completed == 0.5
    assert received[0].first_seen <= received[0].completed


def test_run_stops_with_event():
    stop_event = threading.Event()
    grabber = Grabber(lambda message: None, fps=200.0, capture_fn=lambda: None)
    thread = threading.Thread(target=grabber.run, args=(stop_event,))
    thread.start()
    time.sleep(0.05)
    stop_event.set()
    thread.join(timeout=2.0)
    assert not thread.is_alive()


def test_run_survives_capture_errors():
    def failing_capture():
        raise RuntimeError('no capture')

    stop_event = threading.Event()
    grabber = Grabber(lambda message: None, fps=200.0, capture_fn=failing_capture)
    thread = threading.Thread(target=grabber.run, args=(stop_event,))
    thread.start()
    time.sleep(0.05)
    stop_event.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert grabber.errors > 0


def test_format_message_json():
    payload = {
        'v': 1,
        'lang': 'esES',
        'q': '¿Dónde está Hogger?',
        'ctx': {
            'lvl': 15,
            'race': 'Enano',
            'class': 'Chamán',
            'fac': 'Alianza',
            'zone': 'Forjaz',
            'quests': [['Una', 12, 0], ['Otra', None, 1]],
        },
    }
    text = format_message(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

    assert 'Pregunta: ¿Dónde está Hogger?' in text
    assert 'Idioma: esES' in text
    assert 'nivel 15' in text
    assert 'Enano Chamán' in text
    assert 'Alianza' in text
    assert 'Forjaz' in text
    assert '2 misiones' in text


def test_format_message_plain_text():
    text = format_message(b'no es json \xff')
    assert 'no es json' in text
    assert format_message(b'[1, 2]') == '[1, 2]'


def test_listen_without_window(monkeypatch, capsys):
    monkeypatch.setattr(cli, 'find_game_window', lambda: None)

    class FakeGrabber:
        def __init__(self, on_message, fps=30.0):
            self.captures = 0
            self.valid_frames = 0
            self.messages = 0
            self.errors = 0

        def run(self, stop_event):
            return None

    monkeypatch.setattr(cli, 'Grabber', FakeGrabber)

    assert cli.main(['listen']) == 0
    output = capsys.readouterr().out
    assert 'Esperando a que se abra el juego' in output
    assert 'Capturas: 0' in output


def test_main_without_subcommand_requires_key(monkeypatch, capsys):
    class FakeStdin:
        def isatty(self):
            return False

    monkeypatch.setattr(cli.config, 'get_api_key', lambda provider=None: None)
    monkeypatch.setattr(cli.sys, 'stdin', FakeStdin())

    assert cli.main([]) == 1
    assert 'set-key' in capsys.readouterr().out


def test_listen_prints_message(monkeypatch, capsys):
    monkeypatch.setattr(cli, 'find_game_window', lambda: None)
    from askforever.capture.grabber import ReceivedMessage

    class OneMessageGrabber:
        def __init__(self, on_message, fps=30.0):
            self.on_message = on_message
            self.captures = 1
            self.valid_frames = 1
            self.messages = 0
            self.errors = 0

        def run(self, stop_event):
            self.messages = 1
            self.on_message(ReceivedMessage(7, 1, b'{"q":"hola","lang":"esES","ctx":{}}', 0.0, 0.5))

    monkeypatch.setattr(cli, 'Grabber', OneMessageGrabber)

    assert cli.main(['listen', '--raw']) == 0
    output = capsys.readouterr().out
    assert 'msg_id=7' in output
    assert 'páginas=1' in output
    assert 'recepción=500 ms' in output
    assert '{"q":"hola"' in output
    assert 'Capturas: 1' in output


def test_listen_handles_ctrl_c(monkeypatch, capsys):
    monkeypatch.setattr(cli, 'find_game_window', lambda: None)

    class InterruptingGrabber:
        def __init__(self, on_message, fps=30.0):
            self.captures = 2
            self.valid_frames = 1
            self.messages = 1
            self.errors = 0

        def run(self, stop_event):
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, 'Grabber', InterruptingGrabber)

    assert cli.main(['listen']) == 0
    output = capsys.readouterr().out
    assert 'Esperando a que se abra el juego' in output
    assert 'Capturas: 2' in output
