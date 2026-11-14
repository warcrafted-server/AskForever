"""Pruebas de los informes de desarrollo del companion."""

from __future__ import annotations

import json
import threading
from datetime import datetime

from askforever import cli, devreport, paths
from askforever.capture.grabber import ReceivedMessage
from askforever.devreport import (
    build_report,
    is_report,
    parse_report,
    reports_dir,
    write_report,
)

NOW = datetime(2026, 11, 14, 17, 54, 6)
MOMENT = datetime(2026, 11, 14, 17, 50, 0)


def _exchange():
    return {
        'msg_id': 42,
        'question': '¿Dónde está Hogger?',
        'lang': 'esES',
        'conv': 7,
        'ctx': {'lvl': 10, 'zone': 'Dun Morogh'},
        'moment': MOMENT,
        'model': 'modelo-de-prueba',
        'ok': True,
        'text': 'Hogger está en el Bosque de Elwynn.',
        'detail': '',
        'elapsed_ms': 1234,
        'facts': ['dato de prueba'],
        'sources': ['route:Forjaz>Ventormenta'],
        'facts_text': 'DATOS: algo comprobado',
        'web_titles': ['Hogger'],
    }


def test_reports_dir_uses_dev_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(devreport, 'dev_dir', lambda: tmp_path)
    assert reports_dir() == tmp_path / 'informes'


def test_reports_dir_uses_paths_dev_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(paths, 'dev_dir', lambda: tmp_path)
    assert reports_dir() == tmp_path / 'informes'


def test_build_report_has_all_sections():
    text = build_report(_exchange(), 'la respuesta es mala',
                        {'zone': 'Forjaz'}, NOW)

    for heading in (
        'FECHA', 'NOTA', 'PREGUNTA', 'CONTEXTO DEL JUGADOR',
        'DATOS QUE RECIBIÓ LA IA', 'FUENTES', 'MODELO', 'TIEMPO',
        'RESPUESTA', 'ESTADO', 'CONTEXTO AL PULSAR EL BOTÓN',
    ):
        assert heading in text

    assert 'la respuesta es mala' in text
    assert '¿Dónde está Hogger?' in text
    assert 'msg_id: 42' in text
    assert 'conv: 7' in text
    assert 'idioma: esES' in text
    assert 'DATOS: algo comprobado' in text
    assert 'route:Forjaz>Ventormenta' in text
    assert 'Hogger' in text
    assert 'modelo-de-prueba' in text
    assert '1234 ms' in text
    assert 'Hogger está en el Bosque de Elwynn.' in text
    assert 'ok' in text
    assert '"zone": "Forjaz"' in text
    assert '"lvl": 10' in text


def test_build_report_without_exchange():
    text = build_report(None, '', {'zone': 'Forjaz'}, NOW)

    assert '(no hay ninguna pregunta respondida en esta sesión del companion)' in text
    assert '(sin nota)' in text
    assert '"zone": "Forjaz"' in text


def test_write_report_names_and_suffix(tmp_path):
    first = write_report(_exchange(), 'nota', {'zona': 'Forjaz'},
                         directory=tmp_path, now=NOW)
    assert first.name == 'informe-20261114-175406.txt'
    assert 'nota' in first.read_text(encoding='utf-8')

    second = write_report(_exchange(), 'nota', {'zona': 'Forjaz'},
                          directory=tmp_path, now=NOW)
    third = write_report(_exchange(), 'nota', {'zona': 'Forjaz'},
                         directory=tmp_path, now=NOW)
    assert second.name == 'informe-20261114-175406-2.txt'
    assert third.name == 'informe-20261114-175406-3.txt'


def test_is_report_and_parse_report():
    assert is_report({'kind': 'report'})
    assert not is_report({'kind': 'question'})
    assert not is_report(None)

    report = parse_report(json.dumps({'v': 1, 'kind': 'report', 'q': '',
                                      'ctx': {}}).encode('utf-8'))
    assert report is not None
    assert report['kind'] == 'report'
    assert parse_report(b'no es json') is None
    assert parse_report(json.dumps({'q': 'hola'}).encode('utf-8')) is None


def test_report_message_does_not_call_provider(monkeypatch, tmp_path, capsys):
    events = []
    answered = threading.Event()
    done = threading.Event()

    class FakeProvider:
        model = 'modelo-falso'

        def __init__(self):
            self.calls = 0

        def chat(self, system, user, *, max_tokens=None, temperature=0.3):
            self.calls += 1
            return 'respuesta de prueba'

    provider = FakeProvider()

    class FakeOverlay:
        def __init__(self, ttl=30.0):
            self.ttl = ttl

        def show_thinking(self, question, lang):
            events.append(['thinking', question, lang])

        def show_answer(self, question, text, lang):
            events.append(['answer', question, text, lang])
            if question != 'Informe':
                answered.set()

        def show_error(self, text, lang):
            events.append(['error', text, lang])

        def run(self, stop_event=None):
            done.wait(5.0)

        def close(self):
            pass

    normal = json.dumps({'v': 1, 'lang': 'esES', 'q': 'pregunta',
                         'ctx': {'lvl': 10, 'zone': 'Dun Morogh'}}).encode('utf-8')
    report = json.dumps({'v': 1, 'lang': 'esES', 'q': 'nota del revisor',
                         'kind': 'report', 'ctx': {'zone': 'Forjaz'}}).encode('utf-8')

    class FakeGrabber:
        def __init__(self, on_message, fps=30.0):
            self.on_message = on_message
            self.captures = 0
            self.valid_frames = 0
            self.messages = 0
            self.errors = 0

        def run(self, stop_event):
            self.messages = 2
            self.on_message(ReceivedMessage(1, 1, normal, 0.0, 0.1))
            answered.wait(2.0)
            self.on_message(ReceivedMessage(2, 1, report, 0.0, 0.2))
            done.set()

    monkeypatch.setattr(cli, 'Grabber', FakeGrabber)
    monkeypatch.setattr(cli, 'OverlaySupervisor', FakeOverlay)
    monkeypatch.setattr(cli, 'provider_from_config', lambda: provider)
    monkeypatch.setattr(devreport, 'reports_dir', lambda: tmp_path)

    assert cli.main(['run', '--no-data', '--no-web']) == 0
    assert provider.calls == 1

    files = list(tmp_path.glob('informe-*.txt'))
    assert len(files) == 1
    text = files[0].read_text(encoding='utf-8')
    assert 'pregunta' in text
    assert 'nota del revisor' in text
    assert 'respuesta de prueba' in text
    assert '"zone": "Forjaz"' in text
    assert 'modelo-falso' in text
    assert any(event[0] == 'answer' and event[1] == 'Informe' for event in events)

    output = capsys.readouterr().out
    assert 'Informe guardado:' in output
