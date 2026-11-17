from askforever import cli
from askforever.app import main


def test_single_instance_guard_uses_injected_mutex_function():
    handle = object()
    assert main.acquire_single_instance(lambda: (handle, False)) == (handle, False)
    assert main.acquire_single_instance(lambda: (handle, True)) == (handle, True)


def test_app_subcommand_routes_to_window_app(monkeypatch):
    called = []
    monkeypatch.setattr(main, 'run_app', lambda args: called.append(args) or 7)

    assert cli.main(['app']) == 7
    assert called[0].command == 'run'
    assert called[0].ttl == 30.0


def test_frozen_no_command_routes_to_window_app(monkeypatch):
    called = []
    monkeypatch.setattr(cli.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(main, 'run_app', lambda args: called.append(args) or 3)

    assert cli.main([]) == 3
    assert called[0].command == 'run'
