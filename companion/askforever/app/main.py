"""Application entry point and single-instance guard."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
from pathlib import Path

from askforever import config
from askforever.app.selfupdate import Updater
from askforever.app.events import emit, log_detail, set_status
from askforever.app.setup import ProviderHolder, SetupDialog
from askforever.app.tray import TrayIcon
from askforever.app.window import AppWindow, ui_language
from askforever.overlay.supervisor import OverlaySupervisor

MUTEX_NAME = 'Local\\AskForeverApp'
ERROR_ALREADY_EXISTS = 183


def _lock_path() -> Path:
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    return Path(runtime or '/tmp') / f'askforever-app-{os.getuid()}.lock'


def _create_instance_lock():
    """Linux: bloqueo exclusivo no bloqueante sobre un archivo; se libera al cerrar."""
    import fcntl

    try:
        handle = open(_lock_path(), 'a')
    except OSError:
        return None, False
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return handle, True
    return handle, False


def _create_instance_mutex():
    if os.name != 'nt':
        return _create_instance_lock()
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool,
                                          ctypes.c_wchar_p]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        ctypes.set_last_error(0)
        handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
        if not handle:
            raise OSError(ctypes.get_last_error(), 'CreateMutexW failed')
        return handle, ctypes.get_last_error() == ERROR_ALREADY_EXISTS
    except Exception:
        return None, False


def acquire_single_instance(create_mutex=None):
    """Return the mutex handle and whether another app instance owns the name."""
    return (create_mutex or _create_instance_mutex)()


def _release_instance_mutex(handle, already_exists=False):
    if not handle:
        return
    if os.name != 'nt':
        try:
            handle.close()
        except Exception:
            pass
        return
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.ReleaseMutex.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        if not already_exists:
            kernel32.ReleaseMutex(handle)
        kernel32.CloseHandle(handle)
    except Exception:
        pass


def _message_box(text, title, flags):
    if os.name != 'nt':
        return
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.MessageBoxW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p,
                                   ctypes.c_wchar_p, ctypes.c_uint]
    user32.MessageBoxW.restype = ctypes.c_int
    user32.MessageBoxW(None, text, title, flags)


def _show_existing_message(language):
    if language == 'es':
        text = 'AskForever App ya está en marcha (mira la bandeja del sistema)'
        title = 'AskForever App'
    else:
        text = 'AskForever App is already running (check the system tray)'
        title = 'AskForever App'
    try:
        if os.name == 'nt':
            _message_box(text, title, 0x40)
        else:
            print(text, file=sys.stderr)
            subprocess.run(['notify-send', title, text], check=False, timeout=5)
    except Exception:
        pass


def run_app(args) -> int:
    language = ui_language()
    mutex, already_running = acquire_single_instance()
    if os.name == 'nt' and mutex is None:
        try:
            _message_box(
                'No se pudo proteger AskForever App contra varias instancias.',
                'AskForever App', 0x10)
        except Exception:
            pass
        return 1
    if already_running:
        _show_existing_message(language)
        _release_instance_mutex(mutex, already_exists=True)
        return 0

    from askforever.cli import _run_companion

    stop_event = threading.Event()
    window = None
    tray = None
    core_thread = None
    updater = None
    busy_event = threading.Event()
    try:
        provider_holder = ProviderHolder()

        def provider_saved():
            from askforever.providers.openai_compat import provider_from_config

            provider = provider_from_config('gemini')
            provider_holder.swap(provider)
            model = getattr(provider, 'model', '')
            set_status('ai', f'IA lista: Gemini ({model})',
                       f'AI ready: Gemini ({model})', ok=True)
            emit('info', f'IA lista: Gemini ({model})',
                 f'AI ready: Gemini ({model})')

        window = AppWindow(
            language=language,
            on_configure=lambda: SetupDialog(window, language, provider_saved),
        )
        tooltip = ('AskForever App: en marcha (necesaria para el addon)'
                   if language == 'es' else
                   'AskForever App: running (needed by the addon)')
        tray = TrayIcon(Path(__file__).parent / 'askforever.ico',
                        on_open=lambda: window.submit_command('open'),
                        on_exit=lambda: window.submit_command('exit'),
                        language=language, tooltip=tooltip)
        if not tray.start():
            tray = None
        window.set_tray(tray)

        def run_core():
            try:
                _run_companion(args, stop_event=stop_event,
                               overlay_factory=OverlaySupervisor,
                               provider_holder=provider_holder,
                               busy_event=busy_event)
            except Exception as error:
                log_detail(f'app core failed: {error!r}')
                emit('error', 'AskForever App encontró un error.',
                     'AskForever App encountered an error.', detail=str(error))
                set_status('app', 'Se produjo un error', 'An error occurred', ok=False)

        core_thread = threading.Thread(target=run_core, name='AskForeverCore', daemon=True)

        def exit_app():
            if threading.current_thread() is not threading.main_thread():
                # tkinter solo desde el hilo principal: la ventana lo recoge de su cola.
                window.submit_command('exit_now')
                return
            if updater is not None:
                updater.stop()
            stop_event.set()
            if core_thread is not None:
                core_thread.join(timeout=3.0)
            if tray is not None:
                tray.remove()
            window.destroy()

        window.on_exit = exit_app
        core_thread.start()
        updater = Updater(exit_app=exit_app, is_busy=busy_event.is_set)
        updater.start()
        try:
            missing_key = not bool(config.get_api_key('gemini'))
        except Exception:
            missing_key = True
        if missing_key:
            window.after(100, window._open_configuration)
        window.mainloop()
        stop_event.set()
        if core_thread.is_alive():
            core_thread.join(timeout=3.0)
        return 0
    except Exception as error:
        if updater is not None:
            updater.stop()
        if stop_event is not None:
            stop_event.set()
        if core_thread is not None and core_thread.is_alive():
            core_thread.join(timeout=3.0)
        if tray is not None:
            tray.remove()
        if window is not None:
            try:
                window.destroy()
            except Exception:
                pass
        log_detail(f'app startup failed: {error!r}')
        return 1
    finally:
        _release_instance_mutex(mutex)
