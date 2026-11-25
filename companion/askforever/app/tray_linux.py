"""Icono de bandeja de Linux (StatusNotifierItem) sobre D-Bus.

Los escritorios modernos (KDE Plasma, GNOME con extensión) no usan el protocolo
XEmbed: piden al icono que se registre en ``org.kde.StatusNotifierWatcher`` y le
consultan sus propiedades por D-Bus. El menú contextual va aparte, con la
interfaz ``com.canonical.dbusmenu``.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

try:
    from jeepney import (DBusAddress, HeaderFields, MessageType, new_error,
                         new_method_call, new_method_return)
    from jeepney.io.blocking import open_dbus_connection
except ImportError as error:  # pragma: no cover - depende del entorno
    # Sin jeepney el icono no puede funcionar, pero la aplicación debe arrancar.
    JEEPNEY_ERROR = error
    DBusAddress = HeaderFields = MessageType = None
    new_error = new_method_call = new_method_return = None
    open_dbus_connection = None
else:
    JEEPNEY_ERROR = None

LOGGER = logging.getLogger('askforever.app.tray_linux')

SNI_PATH = '/StatusNotifierItem'
SNI_IFACE = 'org.kde.StatusNotifierItem'
MENU_PATH = '/MenuBar'
MENU_IFACE = 'com.canonical.dbusmenu'
WATCHER_PATH = '/StatusNotifierWatcher'
WATCHER_BUS = 'org.kde.StatusNotifierWatcher'
WATCHER_IFACE = 'org.kde.StatusNotifierWatcher'
NOTIFICATIONS_PATH = '/org/freedesktop/Notifications'
NOTIFICATIONS_BUS = 'org.freedesktop.Notifications'
NOTIFICATIONS_IFACE = 'org.freedesktop.Notifications'
PROPERTIES_IFACE = 'org.freedesktop.DBus.Properties'
INTROSPECTABLE_IFACE = 'org.freedesktop.DBus.Introspectable'
PEER_IFACE = 'org.freedesktop.DBus.Peer'
UNKNOWN_METHOD = 'org.freedesktop.DBus.Error.UnknownMethod'
UNKNOWN_PROPERTY = 'org.freedesktop.DBus.Error.UnknownProperty'
PROPERTY_READ_ONLY = 'org.freedesktop.DBus.Error.PropertyReadOnly'
INVALID_ARGS = 'org.freedesktop.DBus.Error.InvalidArgs'

ICON_SIZES = (22, 32, 48)
MENU_OPEN = 1
MENU_QUIT = 2
MENU_VERSION = 3
MENU_REVISION = 1
TOOLTIP_SIG = '(sa(iiay)ss)'
LAYOUT_SIG = '(ia{sv}av)'
READY_TIMEOUT = 3.5
WATCHER_TIMEOUT = 3.0

_PROPERTIES_XML = '''  <interface name="org.freedesktop.DBus.Properties">
    <method name="Get">
      <arg name="interface_name" type="s" direction="in"/>
      <arg name="property_name" type="s" direction="in"/>
      <arg name="value" type="v" direction="out"/>
    </method>
    <method name="GetAll">
      <arg name="interface_name" type="s" direction="in"/>
      <arg name="properties" type="a{sv}" direction="out"/>
    </method>
    <method name="Set">
      <arg name="interface_name" type="s" direction="in"/>
      <arg name="property_name" type="s" direction="in"/>
      <arg name="value" type="v" direction="in"/>
    </method>
    <signal name="PropertiesChanged">
      <arg name="interface_name" type="s"/>
      <arg name="changed_properties" type="a{sv}"/>
      <arg name="invalidated_properties" type="as"/>
    </signal>
  </interface>
'''

_COMMON_XML = _PROPERTIES_XML + '''  <interface name="org.freedesktop.DBus.Introspectable">
    <method name="Introspect">
      <arg name="xml_data" type="s" direction="out"/>
    </method>
  </interface>
  <interface name="org.freedesktop.DBus.Peer">
    <method name="Ping"/>
    <method name="GetMachineId">
      <arg name="machine_uuid" type="s" direction="out"/>
    </method>
  </interface>
'''

_SNI_XML = '''  <interface name="org.kde.StatusNotifierItem">
    <method name="Activate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="ContextMenu">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="Scroll">
      <arg name="delta" type="i" direction="in"/>
      <arg name="orientation" type="s" direction="in"/>
    </method>
    <signal name="NewTitle"/>
    <signal name="NewIcon"/>
    <signal name="NewAttentionIcon"/>
    <signal name="NewOverlayIcon"/>
    <signal name="NewToolTip"/>
    <signal name="NewStatus">
      <arg name="status" type="s"/>
    </signal>
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="WindowId" type="i" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="OverlayIconName" type="s" access="read"/>
    <property name="OverlayIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionIconName" type="s" access="read"/>
    <property name="AttentionIconPixmap" type="a(iiay)" access="read"/>
    <property name="AttentionMovieName" type="s" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <property name="IconThemePath" type="s" access="read"/>
  </interface>
'''

_MENU_XML = '''  <interface name="com.canonical.dbusmenu">
    <method name="GetLayout">
      <arg name="parentId" type="i" direction="in"/>
      <arg name="recursionDepth" type="i" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="revision" type="u" direction="out"/>
      <arg name="layout" type="(ia{sv}av)" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="properties" type="a(ia{sv})" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg name="id" type="i" direction="in"/>
      <arg name="name" type="s" direction="in"/>
      <arg name="value" type="v" direction="out"/>
    </method>
    <method name="Event">
      <arg name="id" type="i" direction="in"/>
      <arg name="eventId" type="s" direction="in"/>
      <arg name="data" type="v" direction="in"/>
      <arg name="timestamp" type="u" direction="in"/>
    </method>
    <method name="EventGroup">
      <arg name="events" type="a(isvu)" direction="in"/>
      <arg name="idErrors" type="ai" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg name="id" type="i" direction="in"/>
      <arg name="needUpdate" type="b" direction="out"/>
    </method>
    <method name="AboutToShowGroup">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="updatesNeeded" type="ai" direction="out"/>
      <arg name="idErrors" type="ai" direction="out"/>
    </method>
    <signal name="LayoutUpdated">
      <arg name="revision" type="u"/>
      <arg name="parent" type="i"/>
    </signal>
    <signal name="ItemActivationRequested">
      <arg name="id" type="i"/>
      <arg name="timestamp" type="u"/>
    </signal>
    <property name="Version" type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
  </interface>
'''


def _introspection(body: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<node>\n'
            + body + _COMMON_XML + '</node>\n')


INTROSPECT_SNI = _introspection(_SNI_XML)
INTROSPECT_MENU = _introspection(_MENU_XML)


def argb32_data(image) -> bytes:
    """Bytes A, R, G, B de cada píxel, como exige ``IconPixmap``."""
    rgba = image.convert('RGBA').tobytes()
    argb = bytearray(len(rgba))
    argb[0::4] = rgba[3::4]
    argb[1::4] = rgba[0::4]
    argb[2::4] = rgba[1::4]
    argb[3::4] = rgba[2::4]
    return bytes(argb)


def icon_pixmaps(icon_path, sizes=ICON_SIZES):
    """Pixmaps (ancho, alto, datos ARGB) del icono en los tamaños de la bandeja."""
    if icon_path is None:
        return []
    try:
        from PIL import Image
    except ImportError:
        return []
    try:
        with Image.open(icon_path) as source:
            image = source.convert('RGBA')
    except Exception as error:
        LOGGER.warning('no se pudo leer el icono %s: %s', icon_path, error)
        return []
    resampling = getattr(Image, 'Resampling', Image)
    resample = getattr(resampling, 'LANCZOS', None) or getattr(Image, 'LANCZOS')
    pixmaps = []
    for size in sizes:
        scaled = (image if image.size == (size, size)
                  else image.resize((size, size), resample))
        pixmaps.append((size, size, argb32_data(scaled)))
    return pixmaps


def _machine_id() -> str:
    for path in ('/var/lib/dbus/machine-id', '/etc/machine-id'):
        try:
            value = Path(path).read_text(encoding='utf-8').strip()
        except OSError:
            continue
        if value:
            return value
    return ''


class LinuxTrayIcon:
    """Icono StatusNotifierItem con menú DBusMenu y notificaciones de escritorio."""

    def __init__(self, icon_path, on_open, on_exit, language='es',
                 tooltip='AskForever App'):
        self.icon_path = Path(icon_path) if icon_path is not None else None
        self.on_open = on_open
        self.on_exit = on_exit
        self.language = language
        self.tooltip = tooltip
        self._pixmaps = icon_pixmaps(self.icon_path)
        self._thread = None
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._connection = None
        self._started = False
        self._start_ok = False
        self._removed = False
        self.bus_name = ''

    # -- ciclo de vida -------------------------------------------------

    def start(self) -> bool:
        if JEEPNEY_ERROR is not None:
            LOGGER.warning('falta jeepney para el icono de bandeja: %s', JEEPNEY_ERROR)
            return False
        if self._started:
            return self._start_ok
        self._started = True
        self._thread = threading.Thread(target=self._thread_main,
                                        name='AskForeverTrayLinux', daemon=True)
        self._thread.start()
        self._ready.wait(READY_TIMEOUT)
        if not self._start_ok:
            self.remove()
        return self._start_ok

    def _thread_main(self):
        try:
            self._run()
        except Exception:
            LOGGER.exception('el hilo del icono de bandeja falló')
            self._start_ok = False
            self._fail_start()
            self._ready.set()

    def _run(self):
        try:
            connection = open_dbus_connection(bus='SESSION')
        except Exception as error:
            LOGGER.warning('no hay bus de sesión D-Bus para el icono: %s', error)
            self._fail_start()
            return
        with self._lock:
            if self._stop.is_set():
                try:
                    connection.close()
                except Exception:
                    pass
                self._ready.set()
                return
            self._connection = connection
        try:
            from jeepney.bus_messages import message_bus

            name = f'org.kde.StatusNotifierItem-{os.getpid()}-1'
            reply = connection.send_and_get_reply(
                message_bus.RequestName(name, 4), timeout=WATCHER_TIMEOUT)
            # 1 = propietario, 4 = ya era nuestro; cualquier otra cosa es un problema.
            if (reply.header.message_type == MessageType.error
                    or reply.body[0] not in (1, 4)):
                raise RuntimeError(f'no se pudo reservar el nombre {name}')
            watcher = DBusAddress(WATCHER_PATH, bus_name=WATCHER_BUS,
                                  interface=WATCHER_IFACE)
            reply = connection.send_and_get_reply(
                new_method_call(watcher, 'RegisterStatusNotifierItem', 's',
                                (name,)),
                timeout=WATCHER_TIMEOUT)
            if reply.header.message_type == MessageType.error:
                raise RuntimeError(f'el observador rechazó el icono: {reply.body}')
        except Exception as error:
            LOGGER.warning('no se pudo registrar el icono de bandeja: %s', error)
            self._fail_start()
            return
        if self._stop.is_set():
            self._fail_start()
            return
        self.bus_name = name
        self._start_ok = True
        self._ready.set()
        self._receive_loop(connection)

    def _receive_loop(self, connection):
        while not self._stop.is_set():
            try:
                message = connection.receive(timeout=0.2)
            except TimeoutError:
                continue
            except Exception as error:
                if not self._stop.is_set():
                    LOGGER.warning('conexión D-Bus del icono cerrada: %s', error)
                break
            reply = self.handle_message(message)
            if reply is None:
                continue
            try:
                connection.send(reply)
            except Exception as error:
                if not self._stop.is_set():
                    LOGGER.warning('no se pudo responder al escritorio: %s', error)
                break
        self._close_connection()

    def _fail_start(self):
        self._start_ok = False
        self._close_connection()
        self._ready.set()

    def _close_connection(self):
        with self._lock:
            connection, self._connection = self._connection, None
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    def remove(self):
        """Retira el icono; se puede llamar varias veces y desde cualquier hilo."""
        with self._lock:
            if self._removed:
                return
            self._removed = True
            self._stop.set()
            connection, self._connection = self._connection, None
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._start_ok = False

    def show_balloon(self, title, text):
        """Muestra una notificación de escritorio; usa una conexión propia."""
        if not self._start_ok:
            return False
        try:
            with open_dbus_connection(bus='SESSION') as connection:
                address = DBusAddress(NOTIFICATIONS_PATH, bus_name=NOTIFICATIONS_BUS,
                                      interface=NOTIFICATIONS_IFACE)
                message = new_method_call(
                    address, 'Notify', 'susssasa{sv}i',
                    ('AskForever', 0, '', str(title), str(text), [], {}, 5000))
                reply = connection.send_and_get_reply(message, timeout=3.0)
                return reply.header.message_type != MessageType.error
        except Exception as error:
            LOGGER.warning('no se pudo mostrar la notificación: %s', error)
            return False

    # -- interfaz pública para los tests -------------------------------

    def handle_message(self, message):
        """Devuelve la respuesta D-Bus a un mensaje entrante, o None si es una señal."""
        if message.header.message_type != MessageType.method_call:
            return None
        try:
            return self._dispatch(message)
        except Exception as error:
            LOGGER.exception('error atendiendo una llamada D-Bus del icono')
            return new_error(message, 'org.freedesktop.DBus.Error.Failed', 's',
                             (str(error),))

    def item_properties(self) -> dict:
        return {
            'Category': ('s', 'ApplicationStatus'),
            'Id': ('s', 'askforever'),
            'Title': ('s', self.tooltip),
            'Status': ('s', 'Active'),
            'WindowId': ('i', 0),
            'IconName': ('s', ''),
            'IconPixmap': ('a(iiay)', self._pixmaps),
            'OverlayIconName': ('s', ''),
            'OverlayIconPixmap': ('a(iiay)', []),
            'AttentionIconName': ('s', ''),
            'AttentionIconPixmap': ('a(iiay)', []),
            'AttentionMovieName': ('s', ''),
            'ToolTip': (TOOLTIP_SIG, ('', [], 'AskForever App', self.tooltip)),
            'ItemIsMenu': ('b', False),
            'Menu': ('o', MENU_PATH),
            'IconThemePath': ('s', ''),
        }

    def menu_properties(self) -> dict:
        return {
            'Version': ('u', MENU_VERSION),
            'TextDirection': ('s', 'ltr'),
            'Status': ('s', 'normal'),
            'IconThemePath': ('as', []),
        }

    # -- despacho ------------------------------------------------------

    def _dispatch(self, message):
        fields = message.header.fields
        path = fields.get(HeaderFields.path)
        interface = fields.get(HeaderFields.interface)
        member = fields.get(HeaderFields.member)
        body = tuple(message.body)

        if interface == PEER_IFACE:
            if member == 'Ping':
                return new_method_return(message)
            if member == 'GetMachineId':
                return new_method_return(message, 's', (_machine_id(),))
            return self._unknown_method(message)
        if interface == INTROSPECTABLE_IFACE and member == 'Introspect':
            return new_method_return(
                message, 's',
                (INTROSPECT_MENU if path == MENU_PATH else INTROSPECT_SNI,))
        if interface == PROPERTIES_IFACE:
            return self._handle_properties(message, path, member, body)

        if path == SNI_PATH and interface == SNI_IFACE:
            return self._handle_sni(message, member, body)
        if path == MENU_PATH and interface == MENU_IFACE:
            return self._handle_menu(message, member, body)
        return self._unknown_method(message)

    def _handle_properties(self, message, path, member, body):
        if path == MENU_PATH:
            properties = self.menu_properties()
        else:
            properties = self.item_properties()
        if member == 'Get' and len(body) == 2:
            interface, name = body
            if interface not in ('', SNI_IFACE if path == SNI_PATH else MENU_IFACE):
                return self._unknown_property(message, name)
            if name not in properties:
                return self._unknown_property(message, name)
            return new_method_return(message, 'v', (properties[name],))
        if member == 'GetAll' and len(body) == 1:
            interface = body[0]
            expected = SNI_IFACE if path == SNI_PATH else MENU_IFACE
            if interface not in ('', expected):
                return new_method_return(message, 'a{sv}', ({},))
            return new_method_return(message, 'a{sv}', (properties,))
        if member == 'Set' and len(body) == 3:
            return new_error(message, PROPERTY_READ_ONLY, 's',
                             ('El icono de bandeja es de solo lectura',))
        return new_error(message, INVALID_ARGS, 's', ('Argumentos incorrectos',))

    def _handle_sni(self, message, member, body):
        if member in ('Activate', 'SecondaryActivate'):
            self._invoke(self.on_open)
        elif member in ('ContextMenu', 'Scroll'):
            pass
        else:
            return self._unknown_method(message)
        return new_method_return(message)

    def _handle_menu(self, message, member, body):
        if member == 'GetLayout' and len(body) == 3:
            revision, layout = self._layout(*body)
            return new_method_return(message, 'u' + LAYOUT_SIG, (revision, layout))
        if member == 'GetGroupProperties' and len(body) == 2:
            return new_method_return(message, 'a(ia{sv})',
                                     (self._group_properties(*body),))
        if member == 'GetProperty' and len(body) == 2:
            item_id, name = body
            items = self._menu_items()
            if item_id not in items or name not in items[item_id]:
                return new_error(message, INVALID_ARGS, 's',
                                 (f'Propiedad desconocida: {name}',))
            return new_method_return(message, 'v', (items[item_id][name],))
        if member == 'Event' and len(body) == 4:
            self._event(body[0], body[1])
            return new_method_return(message)
        if member == 'EventGroup' and len(body) == 1:
            for event in body[0]:
                self._event(event[0], event[1])
            return new_method_return(message, 'ai', ([],))
        if member == 'AboutToShow' and len(body) == 1:
            return new_method_return(message, 'b', (False,))
        if member == 'AboutToShowGroup' and len(body) == 1:
            return new_method_return(message, 'aiai', ([], []))
        return self._unknown_method(message)

    def _unknown_method(self, message):
        member = message.header.fields.get(HeaderFields.member, '')
        return new_error(message, UNKNOWN_METHOD, 's',
                         (f'Método desconocido: {member}',))

    def _unknown_property(self, message, name):
        return new_error(message, UNKNOWN_PROPERTY, 's',
                         (f'Propiedad desconocida: {name}',))

    # -- menú ----------------------------------------------------------

    def _menu_items(self) -> dict:
        open_text, quit_text = (('Abrir', 'Salir') if self.language == 'es'
                                else ('Open', 'Quit'))
        return {
            MENU_OPEN: {
                'label': ('s', open_text),
                'enabled': ('b', True),
                'visible': ('b', True),
                'type': ('s', 'standard'),
            },
            MENU_QUIT: {
                'label': ('s', quit_text),
                'enabled': ('b', True),
                'visible': ('b', True),
                'type': ('s', 'standard'),
            },
        }

    def _layout(self, parent_id, depth, property_names):
        items = self._menu_items()

        def node(item_id, children):
            return (item_id, _filter_properties(items.get(item_id, {}), property_names),
                    children)

        if parent_id == 0:
            children = []
            if depth != 0:
                children = [(LAYOUT_SIG, node(item_id, [])) for item_id in sorted(items)]
            root = (0, {'children-display': ('s', 'submenu')}, children)
            return MENU_REVISION, root
        if parent_id in items:
            return MENU_REVISION, node(parent_id, [])
        return MENU_REVISION, (parent_id, {}, [])

    def _group_properties(self, ids, property_names):
        items = self._menu_items()
        chosen = sorted(items) if not ids else [item_id for item_id in ids
                                                if item_id in items]
        return [(item_id, _filter_properties(items[item_id], property_names))
                for item_id in chosen]

    def _event(self, item_id, event_id):
        if event_id != 'clicked':
            return
        if item_id == MENU_OPEN:
            self._invoke(self.on_open)
        elif item_id == MENU_QUIT:
            self._invoke(self.on_exit)

    def _invoke(self, callback):
        try:
            callback()
        except Exception:
            LOGGER.exception('falló un callback del icono de bandeja')


def _filter_properties(properties: dict, names) -> dict:
    if not names:
        return dict(properties)
    return {name: value for name, value in properties.items() if name in names}
