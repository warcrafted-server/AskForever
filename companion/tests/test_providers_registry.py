"""Pruebas del registro de proveedores, el modelo/clave por proveedor y la CLI."""

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
from askforever.providers.openai_compat import ProviderError, list_models, provider_from_config

REQUEST = httpx.Request('POST', 'https://example.test')


def _status(error_class, status: int, message: str = 'boom'):
    response = httpx.Response(status, request=REQUEST)
    return error_class(message, response=response, body=None)


class FakeModels:
    def __init__(self, ids=None, error=None):
        self.ids = ids or []
        self.error = error
        self.calls = 0

    def list(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return types.SimpleNamespace(data=[types.SimpleNamespace(id=value) for value in self.ids])


class FakeClient:
    def __init__(self, ids=None, error=None):
        self.models = FakeModels(ids, error)


def test_registry_complete():
    assert set(config.PROVIDERS) == {'gemini', 'groq', 'mistral', 'cerebras', 'openrouter'}
    expected = {
        'gemini': (config.GEMINI_BASE_URL, config.DEFAULT_MODEL, 'gemini',
                   'ASKFOREVER_GEMINI_KEY', 'https://aistudio.google.com'),
        'groq': ('https://api.groq.com/openai/v1', 'llama-3.3-70b-versatile', 'groq',
                 'ASKFOREVER_GROQ_KEY', 'https://console.groq.com'),
        'mistral': ('https://api.mistral.ai/v1', None, 'mistral',
                    'ASKFOREVER_MISTRAL_KEY', 'https://console.mistral.ai'),
        'cerebras': ('https://api.cerebras.ai/v1', None, 'cerebras',
                     'ASKFOREVER_CEREBRAS_KEY', 'https://cloud.cerebras.ai'),
        'openrouter': ('https://openrouter.ai/api/v1', None, 'openrouter',
                       'ASKFOREVER_OPENROUTER_KEY', 'https://openrouter.ai'),
    }
    for name, values in expected.items():
        preset = config.PROVIDERS[name]
        assert preset.name == name
        assert (preset.base_url, preset.default_model, preset.keyring_user,
                preset.key_env, preset.key_url) == values


def test_get_provider_name(monkeypatch):
    monkeypatch.delenv('ASKFOREVER_PROVIDER', raising=False)
    assert config.get_provider_name() == 'gemini'
    assert config.get_provider_name('groq') == 'groq'

    monkeypatch.setenv('ASKFOREVER_PROVIDER', 'mistral')
    assert config.get_provider_name() == 'mistral'
    assert config.get_provider_name('groq') == 'groq'

    with pytest.raises(ValueError) as info:
        config.get_provider_name('desconocido')
    message = str(info.value)
    assert 'gemini' in message
    assert 'groq' in message


def test_get_model_gemini_default(monkeypatch):
    monkeypatch.delenv('ASKFOREVER_MODEL', raising=False)
    monkeypatch.delenv('ASKFOREVER_PROVIDER', raising=False)
    assert config.get_model() == config.DEFAULT_MODEL
    monkeypatch.setenv('ASKFOREVER_MODEL', 'gemini-x')
    assert config.get_model() == 'gemini-x'
    assert config.get_model('gemini') == 'gemini-x'


def test_get_model_groq_and_mistral(monkeypatch):
    monkeypatch.delenv('ASKFOREVER_MODEL', raising=False)
    monkeypatch.delenv('ASKFOREVER_PROVIDER', raising=False)
    assert config.get_model('groq') == 'llama-3.3-70b-versatile'
    assert config.get_model('groq', 'mi-modelo') == 'mi-modelo'
    assert config.get_model('mistral') is None


def test_model_env_only_for_environment_default(monkeypatch):
    monkeypatch.delenv('ASKFOREVER_PROVIDER', raising=False)
    monkeypatch.setenv('ASKFOREVER_MODEL', 'modelo-entorno')
    assert config.get_model('groq') == 'llama-3.3-70b-versatile'
    monkeypatch.setenv('ASKFOREVER_PROVIDER', 'groq')
    assert config.get_model('groq') == 'modelo-entorno'


def test_get_api_key_per_provider(monkeypatch):
    seen = []
    monkeypatch.setattr(
        config.keyring,
        'get_password',
        lambda service, user: seen.append(user) or None,
    )
    monkeypatch.setenv('ASKFOREVER_GROQ_KEY', ' groq-key\n')
    assert config.get_api_key('groq') == 'groq-key'
    assert seen == ['groq']

    monkeypatch.delenv('ASKFOREVER_GROQ_KEY')
    monkeypatch.setenv('ASKFOREVER_CEREBRAS_KEY', 'cerebras-key')
    assert config.get_api_key('cerebras') == 'cerebras-key'


def test_get_api_key_defaults_to_gemini(monkeypatch):
    seen = []
    monkeypatch.setattr(
        config.keyring,
        'get_password',
        lambda service, user: seen.append(user) or None,
    )
    monkeypatch.delenv('ASKFOREVER_GEMINI_KEY', raising=False)
    assert config.get_api_key() is None
    assert seen == ['gemini']


def test_set_api_key_per_provider(monkeypatch):
    saved = {}
    monkeypatch.setattr(
        config.keyring,
        'set_password',
        lambda service, user, key: saved.update(service=service, user=user, key=key),
    )
    config.set_api_key(' secreta ', 'openrouter')
    assert saved == {'service': 'AskForever', 'user': 'openrouter', 'key': 'secreta'}


def test_provider_from_config_without_key(monkeypatch):
    monkeypatch.setattr(config, 'get_api_key', lambda provider=None: None)
    with pytest.raises(ProviderError) as info:
        provider_from_config('groq')
    assert info.value.kind == 'auth'
    assert 'groq' in info.value.detail
    assert 'https://console.groq.com' in info.value.detail


def test_provider_from_config_without_model(monkeypatch):
    monkeypatch.setattr(config, 'get_api_key', lambda provider=None: 'clave')
    with pytest.raises(ProviderError) as info:
        provider_from_config('mistral')
    assert info.value.kind == 'bad_request'
    assert 'Falta el modelo' in info.value.detail


def test_provider_from_config_builds_selected_provider(monkeypatch):
    monkeypatch.setattr(config, 'get_api_key', lambda provider=None: 'clave')
    provider = provider_from_config('groq', 'mi-modelo')
    assert provider.base_url == 'https://api.groq.com/openai/v1'
    assert provider.model == 'mi-modelo'


def test_list_models_sorted_and_unprefixed():
    client = FakeClient(['models/zeta', 'alpha', 'models/beta'])
    assert list_models('https://base', 'secret', client=client) == ['alpha', 'beta', 'zeta']


@pytest.mark.parametrize('factory,kind', [
    (lambda: _status(openai.AuthenticationError, 401, 'clave secret'), 'auth'),
    (lambda: _status(openai.PermissionDeniedError, 403, 'clave secret'), 'auth'),
    (lambda: _status(openai.BadRequestError, 400, 'clave secret'), 'bad_request'),
    (lambda: _status(openai.RateLimitError, 429, 'clave secret'), 'rate_limit'),
    (lambda: _status(openai.InternalServerError, 500, 'clave secret'), 'server'),
    (lambda: openai.APITimeoutError(request=REQUEST), 'timeout'),
    (lambda: openai.APIConnectionError(request=REQUEST), 'network'),
    (lambda: RuntimeError('clave secret'), 'unknown'),
])
def test_list_models_translates_errors(factory, kind):
    client = FakeClient(error=factory())
    with pytest.raises(ProviderError) as info:
        list_models('https://base', 'secret', client=client)
    assert info.value.kind == kind
    assert 'secret' not in info.value.detail
    assert client.models.calls == 1


def test_providers_command(monkeypatch, capsys):
    monkeypatch.setattr(
        config,
        'get_api_key',
        lambda provider=None: 'SECRETO' if provider == 'groq' else None,
    )
    assert cli.main(['providers']) == 0
    output = capsys.readouterr().out
    for name in ('gemini', 'groq', 'mistral', 'cerebras', 'openrouter'):
        assert name in output
    assert '[x] groq' in output
    assert '[ ] gemini' in output
    assert '(elige con --model)' in output
    assert 'https://console.groq.com' in output
    assert 'SECRETO' not in output


def test_list_models_command(monkeypatch, capsys):
    monkeypatch.setattr(config, 'get_api_key', lambda provider=None: 'clave')
    captured = {}

    def fake_list_models(base_url, api_key):
        captured['base_url'] = base_url
        captured['api_key'] = api_key
        return ['modelo-alfa', 'modelo-beta']

    monkeypatch.setattr(cli, 'list_models', fake_list_models)

    assert cli.main(['list-models', '--provider', 'groq']) == 0
    output = capsys.readouterr().out
    assert 'modelo-alfa' in output
    assert 'modelo-beta' in output
    assert 'Total: 2' in output
    assert captured['base_url'] == 'https://api.groq.com/openai/v1'


def test_list_models_without_key(monkeypatch, capsys):
    monkeypatch.setattr(config, 'get_api_key', lambda provider=None: None)
    assert cli.main(['list-models', '--provider', 'groq']) == 1
    output = capsys.readouterr().out
    assert 'set-key --provider groq' in output
    assert 'https://console.groq.com' in output


def test_list_models_requires_provider(monkeypatch, capsys):
    monkeypatch.delenv('ASKFOREVER_PROVIDER', raising=False)
    assert cli.main(['list-models']) == 1
    assert 'list-models --provider' in capsys.readouterr().out


def test_set_key_provider(monkeypatch, capsys):
    key = 'gsk_SECRETO_123'
    saved = {}
    monkeypatch.setattr(
        config.keyring,
        'set_password',
        lambda service, user, value: saved.update(service=service, user=user, key=value),
    )
    monkeypatch.setenv('AF_KEY', key)

    assert cli.main(['set-key', '--provider', 'groq']) == 0
    assert saved == {'service': 'AskForever', 'user': 'groq', 'key': key}
    output = capsys.readouterr().out
    assert key not in output
    assert 'groq' in output
    assert 'gsk_' in output


def test_test_key_with_provider_and_model(monkeypatch, capsys):
    calls = []

    class FakeProvider:
        model = 'mi-modelo'

        def chat(self, system, user, *, max_tokens=None, temperature=0.3):
            return 'OK'

    def fake_provider(provider=None, model=None):
        calls.append((provider, model))
        return FakeProvider()

    monkeypatch.setattr(cli, 'provider_from_config', fake_provider)

    assert cli.main(['test-key', '--provider', 'groq', '--model', 'mi-modelo']) == 0
    output = capsys.readouterr().out
    assert calls == [('groq', 'mi-modelo')]
    assert 'Proveedor: groq' in output
    assert 'mi-modelo' in output
    assert 'OK' in output
