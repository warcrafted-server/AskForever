import signal
import threading
import types

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


class FakeSignalModule:
    SIGTERM = 15
    SIGINT = 2
    SIGHUP = 1

    def __init__(self, handlers=None):
        self.handlers = dict(handlers or {})

    def getsignal(self, signum):
        return self.handlers.get(signum, 'default')

    def signal(self, signum, handler):
        self.handlers[signum] = handler


class FakeWindow:
    def __init__(self, language=None, on_configure=None):
        self.commands = []
        self.on_exit = None
        self.tray = object()
        self.destroyed = False

    def submit_command(self, command):
        self.commands.append(command)

    def set_tray(self, tray):
        self.tray = tray

    def after(self, _delay, _callback):
        pass

    def _open_configuration(self):
        pass

    def mainloop(self):
        # Se llama al manejador ya instalado; no se envía ninguna señal al proceso.
        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)

    def destroy(self):
        self.destroyed = True


def _as_main_thread(monkeypatch):
    current = threading.current_thread()
    monkeypatch.setattr(main, 'threading', types.SimpleNamespace(
        current_thread=lambda: current, main_thread=lambda: current))


def test_signal_handlers_submit_exit_now_and_restore_previous(monkeypatch):
    _as_main_thread(monkeypatch)
    previous = {FakeSignalModule.SIGTERM: 'old-term',
                FakeSignalModule.SIGINT: 'old-int'}
    signals = FakeSignalModule(previous)
    window = FakeWindow()

    installed = main._install_exit_signals(window, signals)

    assert set(installed) == {FakeSignalModule.SIGTERM, FakeSignalModule.SIGINT,
                              FakeSignalModule.SIGHUP}
    signals.handlers[FakeSignalModule.SIGTERM](FakeSignalModule.SIGTERM, None)
    assert window.commands == ['exit_now']

    main._restore_exit_signals(installed, signals)

    assert signals.handlers == {FakeSignalModule.SIGTERM: 'old-term',
                                FakeSignalModule.SIGINT: 'old-int',
                                FakeSignalModule.SIGHUP: 'default'}


def test_signal_handlers_are_not_installed_on_windows(monkeypatch):
    _as_main_thread(monkeypatch)
    monkeypatch.setattr(main, 'os', types.SimpleNamespace(name='nt'))
    signals = FakeSignalModule()

    assert main._install_exit_signals(FakeWindow(), signals) == {}
    assert signals.handlers == {}


def test_signal_handlers_are_not_installed_outside_main_thread(monkeypatch):
    other = object()
    monkeypatch.setattr(main, 'threading', types.SimpleNamespace(
        current_thread=lambda: other, main_thread=threading.main_thread))
    signals = FakeSignalModule()

    assert main._install_exit_signals(FakeWindow(), signals) == {}
    assert signals.handlers == {}


class FakeTray:
    def start(self):
        return False

    def remove(self):
        pass


class FakeUpdater:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass

    def stop(self):
        pass


def test_run_app_installs_and_restores_exit_signal_handlers(monkeypatch):
    windows = []
    monkeypatch.setattr(main, 'ui_language', lambda: 'es')
    monkeypatch.setattr(main, 'acquire_single_instance', lambda: (object(), False))
    monkeypatch.setattr(main, 'config',
                        types.SimpleNamespace(get_api_key=lambda _name: 'clave'))
    monkeypatch.setattr(main, 'AppWindow', lambda **kwargs: windows.append(
        FakeWindow(**kwargs)) or windows[-1])
    monkeypatch.setattr(main, 'create_tray', lambda *args, **kwargs: FakeTray())
    monkeypatch.setattr(main, 'Updater', FakeUpdater)
    monkeypatch.setattr(cli, '_run_companion', lambda *args, **kwargs: None)

    previous = {signum: signal.getsignal(signum)
                for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}

    assert main.run_app(types.SimpleNamespace()) == 0

    assert windows[-1].commands == ['exit_now']
    assert windows[-1].destroyed is False
    for signum, handler in previous.items():
        assert signal.getsignal(signum) is handler
