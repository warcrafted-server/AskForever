from datetime import datetime
import queue

import pytest

from askforever.app.events import Event
from askforever.app.tray import NOTIFYICONDATAW, TrayIcon, notify_icon_data_size
from askforever.app.window import (
    AppWindow,
    drain_event_queue,
    event_tag,
    format_event,
    should_hide_to_tray,
    ui_language,
)


def test_ui_language_uses_windows_primary_language_and_falls_back_to_spanish():
    assert ui_language(lambda: 0x0C0A) == 'es'
    assert ui_language(lambda: 0x0409) == 'en'
    assert ui_language(lambda: 0x0411) == 'en'
    assert ui_language(lambda: (_ for _ in ()).throw(OSError())) == 'es'


def test_event_format_and_colour_tag():
    event = Event(datetime(2026, 11, 17, 20, 51), 'answer', 'Respuesta enviada',
                  'Answer sent')
    assert format_event(event, 'es') == '20:51  Respuesta enviada'
    assert format_event(event, 'en') == '20:51  Answer sent'
    assert event_tag('error') == 'error'
    assert event_tag('answer') == 'answer'
    assert event_tag('question') == 'normal'


def test_queue_drain_schedules_next_poll_with_fake_root():
    class FakeRoot:
        def __init__(self):
            self.scheduled = []

        def after(self, delay, callback):
            self.scheduled.append((delay, callback))

    events = queue.Queue()
    events.put('one')
    events.put('two')
    received = []
    root = FakeRoot()
    callback = lambda: None

    assert drain_event_queue(events, received.append, root=root,
                             callback=callback) == 2
    assert received == ['one', 'two']
    assert root.scheduled == [(100, callback)]


def test_close_hides_only_when_tray_is_available():
    assert should_hide_to_tray(True)
    assert not should_hide_to_tray(False)


def test_notify_icon_data_size_matches_native_structure():
    tray = TrayIcon('missing.ico', lambda: None, lambda: None)
    tray._hwnd = 123
    assert tray._new_data(0).cbSize == notify_icon_data_size()


def test_app_window_has_disabled_configuration_button_without_callback():
    try:
        window = AppWindow(language='en')
    except Exception as error:
        pytest.skip(f'tkinter display unavailable: {error}')
    try:
        assert window.title() == 'AskForever App'
        assert window.configure_button['state'] == 'disabled'
    finally:
        window.destroy()
