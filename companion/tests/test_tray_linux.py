import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytest.importorskip('jeepney')

from jeepney import DBusAddress, HeaderFields, MessageType, new_method_call

from askforever.app import tray_linux

ICON = Path(tray_linux.__file__).with_name('askforever.ico')
BUS = 'org.kde.StatusNotifierItem-1-1'


def _call(path, interface, member, signature=None, body=()):
    message = new_method_call(
        DBusAddress(path, bus_name=BUS, interface=interface), member, signature, body)
    message.header.serial = 7
    return message


def _reply(tray, message):
    reply = tray.handle_message(message)
    assert reply is not None
    assert reply.header.message_type in (MessageType.method_return, MessageType.error)
    assert reply.header.fields[HeaderFields.reply_serial] == message.header.serial
    reply.serialise(serial=message.header.serial + 1)
    return reply


def _tray(events, language='es', icon_path=ICON):
    return tray_linux.LinuxTrayIcon(
        icon_path,
        on_open=lambda: events.append('open'),
        on_exit=lambda: events.append('exit'),
        language=language,
        tooltip='AskForever App: en marcha')


def test_get_all_describes_the_status_notifier_item():
    tray = _tray([])
    reply = _reply(tray, _call(tray_linux.SNI_PATH,
                               tray_linux.PROPERTIES_IFACE, 'GetAll', 's',
                               (tray_linux.SNI_IFACE,)))
    props = reply.body[0]

    assert props['Category'] == ('s', 'ApplicationStatus')
    assert props['Id'] == ('s', 'askforever')
    assert props['Title'] == ('s', 'AskForever App: en marcha')
    assert props['Status'] == ('s', 'Active')
    assert props['WindowId'] == ('i', 0)
    assert props['IconName'] == ('s', '')
    assert props['OverlayIconPixmap'] == ('a(iiay)', [])
    assert props['AttentionIconPixmap'] == ('a(iiay)', [])
    assert props['ToolTip'] == (
        '(sa(iiay)ss)', ('', [], 'AskForever App', 'AskForever App: en marcha'))
    assert props['ItemIsMenu'] == ('b', False)
    assert props['Menu'] == ('o', '/MenuBar')
    assert props['IconThemePath'] == ('s', '')

    pixmaps = props['IconPixmap'][1]
    assert [width for width, _, _ in pixmaps] == [22, 32, 48]
    assert all(len(data) == width * height * 4
               for width, height, data in pixmaps)


def test_get_reports_individual_properties():
    tray = _tray([])
    reply = _reply(tray, _call(tray_linux.SNI_PATH,
                               tray_linux.PROPERTIES_IFACE, 'Get', 'ss',
                               (tray_linux.SNI_IFACE, 'Title')))
    assert reply.body[0] == ('s', 'AskForever App: en marcha')

    menu = _reply(tray, _call(tray_linux.MENU_PATH,
                              tray_linux.PROPERTIES_IFACE, 'GetAll', 's',
                              (tray_linux.MENU_IFACE,)))
    assert menu.body[0] == {
        'Version': ('u', 3),
        'TextDirection': ('s', 'ltr'),
        'Status': ('s', 'normal'),
        'IconThemePath': ('as', []),
    }


def test_argb32_data_orders_bytes_as_argb():
    Image = pytest.importorskip('PIL.Image')
    assert tray_linux.argb32_data(Image.new('RGBA', (1, 1), (10, 20, 30, 40))) == \
        bytes([40, 10, 20, 30])


def test_icon_pixmaps_resize_and_keep_colour(tmp_path):
    Image = pytest.importorskip('PIL.Image')
    path = tmp_path / 'icon.ico'
    Image.new('RGBA', (48, 48), (10, 20, 30, 255)).save(
        path, sizes=[(16, 16), (32, 32), (48, 48)])

    pixmaps = tray_linux.icon_pixmaps(path)

    assert [(width, height) for width, height, _ in pixmaps] == [
        (22, 22), (32, 32), (48, 48)]
    for width, height, data in pixmaps:
        assert len(data) == width * height * 4
        assert data[:4] == bytes([255, 10, 20, 30])


@pytest.mark.parametrize('language, labels', [('es', ['Abrir', 'Salir']),
                                              ('en', ['Open', 'Quit'])])
def test_get_layout_lists_open_and_quit_in_the_right_language(language, labels):
    tray = _tray([], language=language)
    reply = _reply(tray, _call(tray_linux.MENU_PATH, tray_linux.MENU_IFACE,
                               'GetLayout', 'iias', (0, -1, [])))
    revision, layout = reply.body

    assert revision == tray_linux.MENU_REVISION
    root_id, root_props, children = layout
    assert root_id == 0
    assert root_props['children-display'] == ('s', 'submenu')
    assert [child[0] for child in children] == [
        '(ia{sv}av)', '(ia{sv}av)']
    assert [child[1][0] for child in children] == [1, 2]
    assert [child[1][1]['label'][1] for child in children] == labels


def test_get_layout_of_an_item_and_group_properties():
    tray = _tray([])
    reply = _reply(tray, _call(tray_linux.MENU_PATH, tray_linux.MENU_IFACE,
                               'GetLayout', 'iias', (1, -1, [])))
    assert reply.body[1][0] == 1
    assert reply.body[1][2] == []

    group = _reply(tray, _call(tray_linux.MENU_PATH, tray_linux.MENU_IFACE,
                               'GetGroupProperties', 'aias', ([2], [])))
    assert group.body[0] == [(2, tray._menu_items()[2])]

    prop = _reply(tray, _call(tray_linux.MENU_PATH, tray_linux.MENU_IFACE,
                              'GetProperty', 'is', (1, 'label')))
    assert prop.body[0] == ('s', 'Abrir')

    show = _reply(tray, _call(tray_linux.MENU_PATH, tray_linux.MENU_IFACE,
                              'AboutToShow', 'i', (0,)))
    assert show.body == (False,)

    about = _reply(tray, _call(tray_linux.MENU_PATH, tray_linux.MENU_IFACE,
                               'AboutToShowGroup', 'ai', ([1, 2],)))
    assert about.body == ([], [])


def test_event_clicked_calls_the_matching_callback():
    events = []
    tray = _tray(events)

    for item_id, expected in ((1, 'open'), (2, 'exit')):
        _reply(tray, _call(tray_linux.MENU_PATH, tray_linux.MENU_IFACE,
                           'Event', 'isvu', (item_id, 'clicked', ('s', ''), 0)))
        assert events[-1] == expected

    _reply(tray, _call(tray_linux.MENU_PATH, tray_linux.MENU_IFACE,
                       'Event', 'isvu', (9, 'clicked', ('s', ''), 0)))
    _reply(tray, _call(tray_linux.MENU_PATH, tray_linux.MENU_IFACE,
                       'Event', 'isvu', (1, 'hovered', ('s', ''), 0)))
    assert events == ['open', 'exit']

    group = _reply(tray, _call(tray_linux.MENU_PATH, tray_linux.MENU_IFACE,
                               'EventGroup', 'a(isvu)',
                               ([(1, 'clicked', ('s', ''), 0)],)))
    assert group.body == ([],)
    assert events == ['open', 'exit', 'open']


def test_activate_calls_open_and_context_menu_replies_empty():
    events = []
    tray = _tray(events)

    for member, signature, body in (
            ('Activate', 'ii', (10, 20)),
            ('SecondaryActivate', 'ii', (10, 20))):
        reply = _reply(tray, _call(tray_linux.SNI_PATH, tray_linux.SNI_IFACE,
                                   member, signature, body))
        assert reply.body == ()
    assert events == ['open', 'open']

    for member, signature, body in (('ContextMenu', 'ii', (10, 20)),
                                    ('Scroll', 'is', (1, 'vertical'))):
        reply = _reply(tray, _call(tray_linux.SNI_PATH, tray_linux.SNI_IFACE,
                                   member, signature, body))
        assert reply.body == ()
    assert events == ['open', 'open']


def test_unknown_method_and_property_get_errors():
    tray = _tray([])
    reply = _reply(tray, _call(tray_linux.SNI_PATH, tray_linux.SNI_IFACE,
                               'Frobnicate'))
    assert reply.header.fields[HeaderFields.error_name] == \
        tray_linux.UNKNOWN_METHOD

    other = _reply(tray, _call(tray_linux.SNI_PATH, 'org.example.Other',
                               'Frobnicate'))
    assert other.header.fields[HeaderFields.error_name] == \
        tray_linux.UNKNOWN_METHOD

    prop = _reply(tray, _call(tray_linux.SNI_PATH, tray_linux.PROPERTIES_IFACE,
                              'Get', 'ss', (tray_linux.SNI_IFACE, 'Nope')))
    assert prop.header.fields[HeaderFields.error_name] == \
        tray_linux.UNKNOWN_PROPERTY


def test_introspection_is_valid_xml_with_both_interfaces():
    tray = _tray([])
    for path, interface in ((tray_linux.SNI_PATH, tray_linux.SNI_IFACE),
                            (tray_linux.MENU_PATH, tray_linux.MENU_IFACE)):
        reply = _reply(tray, _call(path, tray_linux.INTROSPECTABLE_IFACE,
                                   'Introspect'))
        root = ET.fromstring(reply.body[0])
        names = [child.get('name') for child in root.findall('interface')]
        assert interface in names
        assert tray_linux.PROPERTIES_IFACE in names


def test_start_returns_false_without_a_session_bus(monkeypatch):
    monkeypatch.setenv('DBUS_SESSION_BUS_ADDRESS',
                       'unix:path=/nonexistent/askforever-test.sock')
    monkeypatch.setattr(tray_linux, 'READY_TIMEOUT', 1.0)
    tray = _tray([])

    assert tray.start() is False
    assert tray.show_balloon('AskForever App', 'texto') is False
    tray.remove()
    tray.remove()
