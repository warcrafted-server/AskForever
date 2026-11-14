"""Pruebas del primer arranque, el asistente de clave y la desinstalación."""

from __future__ import annotations

import askforever.cli as cli
import askforever.config as config
import askforever.setup_wizard as setup_wizard
import askforever.uninstall as uninstall
from askforever.providers.openai_compat import ProviderError


class FakeStdin:
    def __init__(self, interactive):
        self.interactive = interactive

    def isatty(self):
        return self.interactive


class FakeKeyring:
    def __init__(self, users=('gemini', 'groq')):
        self.users = set(users)
        self.deleted = []

    def delete_password(self, service, user):
        if user not in self.users:
            raise RuntimeError('no existe')
        self.users.remove(user)
        self.deleted.append((service, user))


def forbidden(*_args, **_kwargs):
    raise AssertionError('no debería llamarse')


def test_main_without_args_with_key_runs_companion(monkeypatch):
    called = []

    def fake_run(args):
        called.append(args)
        return 0

    monkeypatch.setattr(cli.config, 'get_api_key', lambda provider=None: 'clave')
    monkeypatch.setattr(cli, '_run_companion', fake_run)
    monkeypatch.setattr(cli, 'run_wizard', forbidden)

    assert cli.main([]) == 0
    assert len(called) == 1
    assert called[0].fps == 30.0
    assert called[0].ttl == 30.0


def test_main_without_args_without_key_interactive_runs_wizard(monkeypatch):
    called = []

    def fake_wizard():
        called.append('wizard')
        return True

    monkeypatch.setattr(cli.config, 'get_api_key', lambda provider=None: None)
    monkeypatch.setattr(cli.sys, 'stdin', FakeStdin(True))
    monkeypatch.setattr(cli, 'run_wizard', fake_wizard)
    monkeypatch.setattr(cli, '_run_companion', lambda args: 0)

    assert cli.main([]) == 0
    assert called == ['wizard']


def test_main_without_args_without_key_non_interactive_exits(monkeypatch, capsys):
    monkeypatch.setattr(cli.config, 'get_api_key', lambda provider=None: None)
    monkeypatch.setattr(cli.sys, 'stdin', FakeStdin(False))
    monkeypatch.setattr(cli, 'run_wizard', forbidden)
    monkeypatch.setattr(cli, '_run_companion', forbidden)

    assert cli.main([]) == 1
    output = capsys.readouterr().out
    assert 'set-key' in output
    assert 'CLAVE_GEMINI.md' in output


def test_wizard_saves_key_after_success(monkeypatch, capsys):
    saved = {}
    opened = []
    tested = []

    def fake_set(key, provider=None):
        saved['key'] = key
        saved['provider'] = provider

    def fake_test(key):
        tested.append(key)
        return None

    monkeypatch.setattr(config, 'get_provider_name', lambda provider=None: 'gemini')
    monkeypatch.setattr(config, 'set_api_key', fake_set)

    result = setup_wizard.run_wizard(
        input_fn=lambda prompt: '',
        getpass_fn=lambda prompt: '  AIza-test  ',
        open_url=lambda url: opened.append(url) or True,
        test_fn=fake_test,
    )

    assert result is True
    assert saved == {'key': 'AIza-test', 'provider': 'gemini'}
    assert opened == [setup_wizard.GUIDE_URL]
    assert tested == ['AIza-test']
    output = capsys.readouterr().out
    assert 'Probando la clave...' in output
    assert config.mask_key('AIza-test') in output


def test_wizard_retries_after_provider_error(monkeypatch, capsys):
    keys = iter(['mala', 'buena'])
    tested = []
    saved = []

    def fake_test(key):
        tested.append(key)
        if key == 'mala':
            raise ProviderError('auth')
        return True

    monkeypatch.setattr(config, 'get_provider_name', lambda provider=None: 'gemini')
    monkeypatch.setattr(config, 'set_api_key',
                        lambda key, provider=None: saved.append(key))

    result = setup_wizard.run_wizard(
        input_fn=lambda prompt: 'n',
        getpass_fn=lambda prompt: next(keys),
        open_url=forbidden,
        test_fn=fake_test,
    )

    assert result is True
    assert tested == ['mala', 'buena']
    assert saved == ['buena']
    output = capsys.readouterr().out
    assert ProviderError('auth').user_message('esES') in output


def test_wizard_empty_key_does_not_test_or_save(monkeypatch):
    tested = []
    saved = []

    monkeypatch.setattr(config, 'get_provider_name', lambda provider=None: 'gemini')
    monkeypatch.setattr(config, 'set_api_key', lambda *args, **kwargs: saved.append(args))

    result = setup_wizard.run_wizard(
        input_fn=lambda prompt: 'n',
        getpass_fn=lambda prompt: '   ',
        open_url=forbidden,
        test_fn=lambda key: tested.append(key) or True,
    )

    assert result is False
    assert tested == []
    assert saved == []


def test_wizard_gives_up_after_three_failures(monkeypatch):
    keys = iter(['a', 'b', 'c', 'd'])
    tested = []

    monkeypatch.setattr(config, 'get_provider_name', lambda provider=None: 'gemini')
    monkeypatch.setattr(config, 'set_api_key', forbidden)

    result = setup_wizard.run_wizard(
        input_fn=lambda prompt: 'n',
        getpass_fn=lambda prompt: next(keys),
        open_url=forbidden,
        test_fn=lambda key: tested.append(key) or False,
    )

    assert result is False
    assert tested == ['a', 'b', 'c']


def test_uninstall_yes_removes_data_keys_and_slots(tmp_path, monkeypatch):
    local = tmp_path / 'Local'
    local.mkdir()
    monkeypatch.setenv('LOCALAPPDATA', str(local))
    root = local / 'AskForever'
    (root / 'data').mkdir(parents=True)
    (root / 'log').mkdir()
    (root / 'data' / 'wow.sqlite').write_text('x', encoding='utf-8')

    addons = tmp_path / 'Game' / 'Interface' / 'AddOns'
    addons.mkdir(parents=True)
    slot = addons / 'AskForever_Slot1'
    slot.mkdir()
    slot2 = addons / 'AskForever_Slot2'
    slot2.mkdir()
    main_addon = addons / 'AskForever'
    main_addon.mkdir()
    other = addons / 'OtherAddon'
    other.mkdir()
    outside = tmp_path / 'Outside'
    outside.mkdir()

    fake_keyring = FakeKeyring()
    monkeypatch.setattr(uninstall, 'keyring', fake_keyring)

    assert uninstall.uninstall(yes=True, remove_addon=False,
                               game_addons_dir=addons) == 0

    assert not root.exists()
    assert not slot.exists()
    assert not slot2.exists()
    assert main_addon.exists()
    assert other.exists()
    assert outside.exists()
    assert fake_keyring.deleted == [
        ('AskForever', 'gemini'),
        ('AskForever', 'groq'),
    ]


def test_uninstall_addon_flag_removes_main_addon(tmp_path, monkeypatch):
    local = tmp_path / 'Local'
    local.mkdir()
    monkeypatch.setenv('LOCALAPPDATA', str(local))
    addons = tmp_path / 'AddOns'
    addons.mkdir()
    main_addon = addons / 'AskForever'
    main_addon.mkdir()
    other = addons / 'OtherAddon'
    other.mkdir()
    monkeypatch.setattr(uninstall, 'keyring', FakeKeyring())

    assert uninstall.uninstall(yes=True, remove_addon=True,
                               game_addons_dir=addons) == 0
    assert not main_addon.exists()
    assert other.exists()


def test_uninstall_cancel_does_nothing(tmp_path, monkeypatch):
    local = tmp_path / 'Local'
    local.mkdir()
    monkeypatch.setenv('LOCALAPPDATA', str(local))
    root = local / 'AskForever'
    root.mkdir()
    addons = tmp_path / 'AddOns'
    addons.mkdir()
    slot = addons / 'AskForever_Slot1'
    slot.mkdir()
    fake_keyring = FakeKeyring()
    monkeypatch.setattr(uninstall, 'keyring', fake_keyring)

    assert uninstall.uninstall(yes=False, input_fn=lambda prompt: 'n',
                               game_addons_dir=addons) == 0
    assert root.exists()
    assert slot.exists()
    assert fake_keyring.deleted == []


def test_cli_setup_runs_wizard(monkeypatch):
    called = []
    monkeypatch.setattr(cli, 'run_wizard', lambda: called.append('wizard') or True)
    assert cli.main(['setup']) == 0
    assert called == ['wizard']


def test_cli_uninstall_passes_flags(monkeypatch):
    calls = []

    def fake_uninstall(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(cli, 'uninstall', fake_uninstall)
    assert cli.main(['uninstall', '--yes', '--addon']) == 0
    assert calls == [{'yes': True, 'remove_addon': True}]
