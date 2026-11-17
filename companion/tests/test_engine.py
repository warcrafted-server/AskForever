"""Pruebas del motor de respuesta: prompt, validación y comando ask."""

from __future__ import annotations

import json
import time

import pytest

import askforever.cli as cli
from askforever.capture.grabber import ReceivedMessage
from askforever.engine.answer import (Answer, _clean_answer, answer_message, is_follow_up,
                                      needs_web, parse_message)
from askforever.engine.prompt import build_prompt
from askforever.engine.retriever import Facts
from askforever.providers.openai_compat import ProviderError


class FakeProvider:
    def __init__(self, response='La respuesta', error=None):
        self.response = response
        self.error = error
        self.calls = []

    def chat(self, system, user, *, max_tokens=None, temperature=0.3):
        self.calls.append({
            'system': system,
            'user': user,
            'max_tokens': max_tokens,
            'temperature': temperature,
        })
        if self.error is not None:
            raise self.error
        return self.response


def make_message(**overrides):
    message = {
        'v': 1,
        'lang': 'esES',
        'q': '¿Dónde está Hogger?',
        'ctx': {
            'lvl': 15,
            'race': 'Enano',
            'class': 'Chamán',
            'fac': 'Alianza',
            'zone': 'Forjaz',
            'sub': 'La Sala Mística',
            'x': 37.3,
            'y': 12.7,
            'map': 1455,
            'quests': [['Una tarea', 12, 0], ['Otra', None, 1]],
        },
    }
    message.update(overrides)
    return message


def make_data(**overrides) -> bytes:
    return json.dumps(make_message(**overrides), ensure_ascii=False).encode('utf-8')


def test_build_prompt_spanish():
    system, user = build_prompt(make_message())

    assert 'no inventes' in system.lower()
    assert '2 a 5' in system
    assert 'Nivel: 15' in user
    assert 'Raza: Enano' in user
    assert 'Clase: Chamán' in user
    assert 'Facción: Alianza' in user
    assert 'Zona: Forjaz - La Sala Mística' in user
    assert 'Coordenadas: 37.3, 12.7' in user
    assert 'Misiones activas:' in user
    assert '- [ ] Una tarea (12)' in user
    assert '- [x] Otra' in user
    assert 'Pregunta: ¿Dónde está Hogger?' in user
    assert 'Level' not in user
    assert 'Active quests' not in user


def test_build_prompt_english():
    message = make_message(lang='enUS', q='Where is Hogger?')
    system, user = build_prompt(message)

    assert 'do not invent' in system.lower()
    assert '2 to 5' in system
    assert 'Level: 15' in user
    assert 'Active quests:' in user
    assert 'Question: Where is Hogger?' in user
    assert 'Nivel' not in user


def test_build_prompt_missing_lang_uses_english():
    message = make_message()
    del message['lang']
    _system, user = build_prompt(message)
    assert 'Level: 15' in user
    assert 'Question:' in user


def test_build_prompt_without_context():
    _system, user = build_prompt({'lang': 'esES', 'q': 'hola'})
    assert user == 'Pregunta: hola'


def test_build_prompt_limits_quests():
    quests = [[f'Misión {index}', index, 0] for index in range(20)]
    _system, user = build_prompt(make_message(ctx={'quests': quests}))
    assert user.count('- [') == 15


def test_build_prompt_ignores_weird_values():
    message = make_message(ctx={
        'lvl': 'abc',
        'race': 42,
        'class': None,
        'fac': '',
        'zone': ['x'],
        'x': 'a',
        'y': None,
        'quests': [None, 'texto', ['', 1, 0], ['ok', 'nivel', 1], ['sin nivel']],
    })
    _system, user = build_prompt(message)
    assert 'Nivel' not in user
    assert 'Raza' not in user
    assert 'Coordenadas' not in user
    assert '- [x] ok' in user
    assert '- [ ] sin nivel' in user

    _system, user = build_prompt({'lang': 'esES', 'q': 'x', 'ctx': 'no es un dict'})
    assert user == 'Pregunta: x'


def test_parse_message():
    assert parse_message(make_data()) is not None
    assert parse_message(make_data(q='')) is None
    assert parse_message(make_data(q='   ')) is None
    assert parse_message(make_data(v=2)) is None
    assert parse_message(b'{no es json') is None
    assert parse_message(json.dumps([1, 2]).encode('utf-8')) is None
    assert parse_message(b'\xff\xfe') is None


def test_answer_message_success_and_cleaning():
    provider = FakeProvider(response='  # Título\n**Hola** ```código```  ')
    result = answer_message(make_data(), provider)

    assert isinstance(result, Answer)
    assert result.ok is True
    assert result.text == 'Título\nHola código'
    assert result.lang == 'esES'
    assert result.question == '¿Dónde está Hogger?'
    assert result.elapsed_ms >= 0
    call = provider.calls[0]
    assert call['system']
    assert 'Pregunta:' in call['user']
    assert call['max_tokens'] is None


def test_clean_answer_keeps_long_answers_and_removes_guide_labels():
    text = ('En WoW Forever: ' + 'a' * 1000 + '\n'
            + 'En WoW Forever: ' + 'b' * 1000)
    cleaned = _clean_answer(text)
    assert cleaned == 'a' * 1000 + '\n' + 'b' * 1000


def test_is_follow_up_detects_other_options_questions():
    assert is_follow_up('Hay más opciones para ir a kalimdor?')
    assert is_follow_up('No hay más?')


def test_needs_web_skips_zone_quest_sources():
    facts = Facts(missing=['misiones de Bosque de Elwynn para tu nivel'],
                  sources=['zone_quests:12'])
    assert not needs_web(facts, '¿Qué misiones hay aquí?')


def test_answer_message_passes_max_tokens():
    provider = FakeProvider(response='ok')
    answer_message(make_data(), provider, max_tokens=256)
    assert provider.calls[0]['max_tokens'] == 256


def test_answer_message_provider_error():
    provider = FakeProvider(error=ProviderError('rate_limit'))
    result = answer_message(make_data(), provider)

    assert result.ok is False
    assert result.text == ProviderError('rate_limit').user_message('esES')
    assert result.detail == 'rate_limit'
    assert len(provider.calls) == 1


def test_answer_message_invalid_without_provider_call():
    provider = FakeProvider()
    result = answer_message(b'no es json', provider)
    assert result.ok is False
    assert result.detail == 'invalid'
    assert result.text == 'The received question could not be read.'
    assert provider.calls == []

    result = answer_message(make_data(q=''), provider)
    assert result.ok is False
    assert result.detail == 'invalid'
    assert result.text == 'No se entendió la pregunta recibida.'
    assert provider.calls == []


def test_answer_message_generic_exception():
    provider = FakeProvider(error=RuntimeError('boom'))
    result = answer_message(make_data(), provider)
    assert result.ok is False
    assert result.detail == 'unknown'
    assert result.text


def test_ask_command_success(monkeypatch, capsys):
    provider = FakeProvider(response='  La respuesta  ')
    monkeypatch.setattr(cli, 'provider_from_config', lambda: provider)

    assert cli.main(['ask', '¿Dónde está Hogger?', '--lang', 'esES',
                     '--level', '15', '--zone', 'Forjaz', '--no-data', '--no-web']) == 0
    output = capsys.readouterr().out
    assert 'La respuesta' in output
    assert 'ms' in output

    call = provider.calls[0]
    assert 'Nivel: 15' in call['user']
    assert 'Zona: Forjaz' in call['user']
    assert '¿Dónde está Hogger?' in call['user']


def test_ask_command_error(monkeypatch, capsys):
    provider = FakeProvider(error=ProviderError('rate_limit'))
    monkeypatch.setattr(cli, 'provider_from_config', lambda: provider)

    assert cli.main(['ask', 'hola', '--no-data', '--no-web']) == 1
    output = capsys.readouterr().out
    assert ProviderError('rate_limit').user_message('esES') in output


def test_listen_ask_prints_answer(monkeypatch, capsys):
    monkeypatch.setattr(cli, 'find_game_window', lambda: None)
    provider = FakeProvider(response='Respuesta de prueba')
    monkeypatch.setattr(cli, 'provider_from_config', lambda: provider)
    data = make_data()

    class OneMessageGrabber:
        def __init__(self, on_message, fps=30.0):
            self.on_message = on_message
            self.captures = 0
            self.valid_frames = 0
            self.messages = 0
            self.errors = 0

        def run(self, stop_event):
            self.messages = 1
            self.on_message(ReceivedMessage(1, 1, data, 0.0, 0.5))

    monkeypatch.setattr(cli, 'Grabber', OneMessageGrabber)

    assert cli.main(['listen', '--ask', '--no-data', '--no-web']) == 0
    time.sleep(0.2)
    output = capsys.readouterr().out
    assert 'Respuesta (' in output
    assert 'Respuesta de prueba' in output


@pytest.mark.parametrize('lang', ['esES', 'esMX'])
def test_answer_language_variants(lang):
    provider = FakeProvider(error=ProviderError('rate_limit'))
    result = answer_message(make_data(lang=lang), provider)
    assert result.text == ProviderError('rate_limit').user_message(lang)
