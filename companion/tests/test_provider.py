"""Pruebas del proveedor compatible con OpenAI, la configuración y los comandos de clave."""

from __future__ import annotations

import types

import openai
import pytest

try:
    import httpx2 as httpx
except ImportError:  # pragma: no cover - entornos con el paquete httpx clásico
    import httpx

import askforever.cli as cli
import askforever.config as config
from askforever.providers.openai_compat import (
    OpenAICompatProvider,
    ProviderError,
    provider_from_config,
)

REQUEST = httpx.Request('POST', 'https://example.test/chat')
KINDS = ['auth', 'rate_limit', 'timeout', 'network', 'bad_request', 'server', 'empty', 'unknown']


def reply(content):
    message = types.SimpleNamespace(content=content)
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


def status_error(error_class, status: int, message: str = 'boom', headers=None):
    response = httpx.Response(status, request=REQUEST, headers=headers or {})
    return error_class(message, response=response, body=None)


def rate_limit(message: str = 'rate limited', retry_after=None):
    headers = {'Retry-After': str(retry_after)} if retry_after is not None else None
    return status_error(openai.RateLimitError, 429, message, headers)


def auth_error(message: str = 'invalid key'):
    return status_error(openai.AuthenticationError, 401, message)


def bad_request(message: str = 'bad request'):
    return status_error(openai.BadRequestError, 400, message)


def server_error():
    return status_error(openai.InternalServerError, 500, 'server down')


class FakeCompletions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes):
        self.completions = FakeCompletions(outcomes)
        self.chat = types.SimpleNamespace(completions=self.completions)


def make_provider(outcomes, sleeps=None, max_retries=3, api_key='test-key'):
    sleeps = [] if sleeps is None else sleeps
    client = FakeClient(outcomes)
    provider = OpenAICompatProvider(
        'https://example.test/v1',
        api_key,
        'gemini-test',
        client=client,
        sleep=sleeps.append,
        max_retries=max_retries,
    )
    return provider, client, sleeps


def test_chat_returns_stripped_text():
    provider, client, sleeps = make_provider([reply('  OK  ')])
    assert provider.chat('system', 'user') == 'OK'
    call = client.completions.calls[0]
    assert call['model'] == 'gemini-test'
    assert call['messages'] == [
        {'role': 'system', 'content': 'system'},
        {'role': 'user', 'content': 'user'},
    ]
    assert call['temperature'] == 0.3
    assert 'max_tokens' not in call
    assert sleeps == []


def test_chat_sends_max_tokens_when_given():
    provider, client, _sleeps = make_provider([reply('ok')])
    assert provider.chat('s', 'u', max_tokens=256, temperature=0.5) == 'ok'
    call = client.completions.calls[0]
    assert call['max_tokens'] == 256
    assert call['temperature'] == 0.5


@pytest.mark.parametrize('content', [None, '', '   '])
def test_empty_content_is_an_error(content):
    provider, _client, _sleeps = make_provider([reply(content)])
    with pytest.raises(ProviderError) as info:
        provider.chat('s', 'u')
    assert info.value.kind == 'empty'


def test_rate_limit_twice_then_success():
    provider, client, sleeps = make_provider([rate_limit(), rate_limit(), reply('hola')])
    assert provider.chat('s', 'u') == 'hola'
    assert len(client.completions.calls) == 3
    assert sleeps == [1, 2]


def test_rate_limit_exhausts_retries():
    provider, client, sleeps = make_provider([rate_limit(), rate_limit(), rate_limit()],
                                             max_retries=2)
    with pytest.raises(ProviderError) as info:
        provider.chat('s', 'u')
    assert info.value.kind == 'rate_limit'
    assert len(client.completions.calls) == 3
    assert sleeps == [1, 2]


def test_retry_after_is_respected():
    provider, _client, sleeps = make_provider([rate_limit(retry_after=3), reply('ok')])
    assert provider.chat('s', 'u') == 'ok'
    assert sleeps == [3]


def test_retry_after_too_long_uses_backoff():
    provider, _client, sleeps = make_provider([rate_limit(retry_after=120), reply('ok')])
    assert provider.chat('s', 'u') == 'ok'
    assert sleeps == [1]


def test_authentication_error_without_retries():
    provider, client, sleeps = make_provider([auth_error()])
    with pytest.raises(ProviderError) as info:
        provider.chat('s', 'u')
    assert info.value.kind == 'auth'
    assert len(client.completions.calls) == 1
    assert sleeps == []


def test_server_error_after_two_retries():
    provider, client, sleeps = make_provider([server_error(), server_error(), server_error()])
    with pytest.raises(ProviderError) as info:
        provider.chat('s', 'u')
    assert info.value.kind == 'server'
    assert len(client.completions.calls) == 3
    assert sleeps == [1, 2]


def test_timeout_after_two_retries():
    timeouts = [openai.APITimeoutError(request=REQUEST) for _ in range(3)]
    provider, client, sleeps = make_provider(timeouts)
    with pytest.raises(ProviderError) as info:
        provider.chat('s', 'u')
    assert info.value.kind == 'timeout'
    assert len(client.completions.calls) == 3
    assert sleeps == [1, 2]


def test_connection_error_after_two_retries():
    errors = [openai.APIConnectionError(request=REQUEST) for _ in range(3)]
    provider, client, sleeps = make_provider(errors)
    with pytest.raises(ProviderError) as info:
        provider.chat('s', 'u')
    assert info.value.kind == 'network'
    assert len(client.completions.calls) == 3
    assert sleeps == [1, 2]


def test_bad_request_without_retries():
    provider, client, sleeps = make_provider([bad_request()])
    with pytest.raises(ProviderError) as info:
        provider.chat('s', 'u')
    assert info.value.kind == 'bad_request'
    assert len(client.completions.calls) == 1
    assert sleeps == []


def test_detail_never_contains_the_key():
    secret = 'AIza' + 'S' * 20
    provider, _client, _sleeps = make_provider([rate_limit(f'incorrect key {secret}')],
                                               max_retries=0, api_key=secret)
    with pytest.raises(ProviderError) as info:
        provider.chat('s', 'u')
    assert secret not in info.value.detail
    assert '<clave>' in info.value.detail


@pytest.mark.parametrize('kind', KINDS)
def test_user_messages(kind):
    error = ProviderError(kind, 'AIzaSECRET')
    spanish = error.user_message('esES')
    english = error.user_message('enUS')
    assert spanish
    assert english
    assert spanish != english
    assert 'AIzaSECRET' not in spanish
    assert 'AIzaSECRET' not in english
    assert error.user_message('esMX') == spanish


def test_get_model(monkeypatch):
    monkeypatch.delenv('ASKFOREVER_MODEL', raising=False)
    assert config.get_model() == config.DEFAULT_MODEL
    monkeypatch.setenv('ASKFOREVER_MODEL', 'gemini-custom')
    assert config.get_model() == 'gemini-custom'
    monkeypatch.setenv('ASKFOREVER_MODEL', '   ')
    assert config.get_model() == config.DEFAULT_MODEL


def test_get_api_key_from_keyring(monkeypatch):
    monkeypatch.setattr(config.keyring, 'get_password', lambda service, user: ' AIza123\n')
    monkeypatch.delenv('ASKFOREVER_GEMINI_KEY', raising=False)
    assert config.get_api_key() == 'AIza123'


def test_get_api_key_from_environment(monkeypatch):
    monkeypatch.setattr(config.keyring, 'get_password', lambda service, user: None)
    monkeypatch.setenv('ASKFOREVER_GEMINI_KEY', ' env-key \n')
    assert config.get_api_key() == 'env-key'


def test_get_api_key_when_keyring_fails(monkeypatch):
    def failing(service, user):
        raise RuntimeError('keyring unavailable')

    monkeypatch.setattr(config.keyring, 'get_password', failing)
    monkeypatch.setenv('ASKFOREVER_GEMINI_KEY', 'fallback')
    assert config.get_api_key() == 'fallback'


def test_set_api_key(monkeypatch):
    saved = {}
    monkeypatch.setattr(
        config.keyring,
        'set_password',
        lambda service, user, key: saved.update(service=service, user=user, key=key),
    )
    config.set_api_key('  AIza  ')
    assert saved == {'service': 'AskForever', 'user': 'gemini', 'key': 'AIza'}
    with pytest.raises(ValueError):
        config.set_api_key('   ')


def test_mask_key():
    key = 'AIza' + 'x' * 49
    masked = config.mask_key(key)
    assert 'AIza' in masked
    assert '53' in masked
    assert 'x' not in masked


def test_provider_from_config_requires_key(monkeypatch):
    monkeypatch.setattr(config, 'get_api_key', lambda provider=None: None)
    with pytest.raises(ProviderError) as info:
        provider_from_config()
    assert info.value.kind == 'auth'


def test_provider_from_config_builds_provider(monkeypatch):
    monkeypatch.setattr(config, 'get_api_key', lambda provider=None: 'test-key')
    monkeypatch.setattr(config, 'get_model', lambda provider=None, model=None: 'gemini-test')
    provider = provider_from_config()
    assert provider.model == 'gemini-test'
    assert provider.base_url == config.GEMINI_BASE_URL


def test_set_key_saves_and_does_not_print_the_key(monkeypatch, capsys):
    key = 'AIza' + 'Z' * 20
    saved = {}
    monkeypatch.setattr(
        config.keyring,
        'set_password',
        lambda service, user, value: saved.update(key=value),
    )
    monkeypatch.setenv('AF_KEY', key)

    assert cli.main(['set-key']) == 0
    assert saved['key'] == key
    output = capsys.readouterr().out
    assert key not in output
    assert 'AIza' in output
    assert str(len(key)) in output


def test_set_key_rejects_empty_key(monkeypatch, capsys):
    monkeypatch.setenv('AF_KEY', '   ')
    assert cli.main(['set-key']) == 1
    assert 'vacía' in capsys.readouterr().out


class FakeProvider:
    model = 'gemini-fake'

    def chat(self, system, user, *, max_tokens=None, temperature=0.3):
        assert system
        assert user == 'ping'
        assert max_tokens == 256
        return 'OK'


def test_test_key_success(monkeypatch, capsys):
    monkeypatch.setattr(cli, 'provider_from_config', lambda: FakeProvider())
    assert cli.main(['test-key']) == 0
    output = capsys.readouterr().out
    assert 'gemini-fake' in output
    assert 'ms' in output
    assert 'OK' in output


def test_test_key_provider_error(monkeypatch, capsys):
    class FailingProvider:
        model = 'gemini-fake'

        def chat(self, system, user, *, max_tokens=None, temperature=0.3):
            raise ProviderError('rate_limit', 'detalle del error')

    monkeypatch.setattr(cli, 'provider_from_config', lambda: FailingProvider())
    assert cli.main(['test-key']) == 1
    output = capsys.readouterr().out
    assert ProviderError('rate_limit').user_message('esES') in output
    assert 'detalle del error' in output


def test_test_key_without_key(monkeypatch, capsys):
    def raise_auth():
        raise ProviderError('auth', 'no API key configured')

    monkeypatch.setattr(cli, 'provider_from_config', raise_auth)
    assert cli.main(['test-key']) == 1
    output = capsys.readouterr().out
    assert 'docs/CLAVE_GEMINI.md' in output
