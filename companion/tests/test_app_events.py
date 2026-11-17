import re

from askforever.app import events
from askforever.app.events import EventBus


def test_bus_keeps_last_200_and_notifies_subscribers(tmp_path, monkeypatch):
    monkeypatch.setattr(events, 'user_data_dir', lambda: tmp_path / 'data')
    bus = EventBus()
    received = []
    bus.subscribe(received.append)

    for number in range(205):
        bus.emit('info', str(number), str(number))
    bus.set_status('game', 'Juego detectado', 'Game detected', ok=True)

    recent = bus.recent()
    assert len(recent) == 200
    assert recent[0].es == '6'
    assert recent[-1].kind == 'status'
    assert received[-1].kind == 'status'
    assert bus.statuses()['game'] == {
        'es': 'Juego detectado', 'en': 'Game detected', 'ok': True,
    }
    assert set(bus.statuses()) == {'game', 'ai', 'data', 'app'}


def test_failing_subscriber_is_logged_without_interrupting_emit(tmp_path, monkeypatch):
    monkeypatch.setattr(events, 'user_data_dir', lambda: tmp_path / 'data')
    bus = EventBus()
    received = []

    def fail(_event):
        raise RuntimeError('subscriber failed')

    bus.subscribe(fail)
    bus.subscribe(received.append)
    bus.emit('info', 'En marcha', 'Running', detail='diagnostic detail')

    log = tmp_path / 'logs' / 'app.log'
    assert log.is_file()
    text = log.read_text(encoding='utf-8')
    assert 'diagnostic detail' in text
    assert 'subscriber failed' in text
    assert received[0].es == 'En marcha'


def test_log_directory_failure_is_silently_skipped(monkeypatch):
    monkeypatch.setattr(events, '_log_path', lambda: (_ for _ in ()).throw(OSError()))
    bus = EventBus()
    assert bus.emit('info', 'Listo', 'Ready').es == 'Listo'


def test_console_sink_prints_only_friendly_text(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv('ASKFOREVER_CONSOLE', '1')
    monkeypatch.setattr(events, 'user_data_dir', lambda: tmp_path / 'data')
    bus = EventBus()
    bus.emit('question', 'Pregunta recibida: ¿Dónde?', 'Question received: Where?',
             detail='msg_id=secret conv=42')

    output = capsys.readouterr().out
    assert re.match(r'^\[\d{2}:\d{2}:\d{2}\] ', output)
    assert '] Pregunta recibida: ¿Dónde?\n' in output
    assert 'msg_id' not in output


def test_subscribe_and_unsubscribe():
    bus = EventBus()
    received = []
    callback = received.append
    bus.subscribe(callback)
    bus.emit('info', 'Uno', 'One')
    bus.unsubscribe(callback)
    bus.emit('info', 'Dos', 'Two')
    assert [event.es for event in received] == ['Uno']
