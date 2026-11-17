"""Main AskForever App window."""

from __future__ import annotations

import ctypes
import os
import queue
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from askforever import config, setup_wizard
from askforever.app.events import get_bus

BG = '#1b1610'
PANEL = '#241d15'
BORDER = '#5a4630'
GOLD = '#ffd100'
TEXT = '#e8dcc0'
DIM = '#a89a80'
OK = '#7ec46b'
ERROR = '#e06c5a'


def ui_language(get_language=None) -> str:
    """Choose Spanish for Spanish Windows UI, English otherwise."""
    try:
        if get_language is None:
            get_language = ctypes.windll.kernel32.GetUserDefaultUILanguage
        language_id = int(get_language()) & 0x3ff
        return 'es' if language_id == 0x0a else 'en'
    except Exception:
        return 'es'


def format_event(event, language: str) -> str:
    text = event.es if language == 'es' else event.en
    return f'{event.time:%H:%M}  {text}'


def event_tag(kind: str) -> str:
    if kind == 'error':
        return 'error'
    if kind == 'answer':
        return 'answer'
    return 'normal'


def drain_event_queue(events, consume, limit=200, root=None, callback=None) -> int:
    count = 0
    while count < limit:
        try:
            event = events.get_nowait()
        except queue.Empty:
            break
        consume(event)
        count += 1
    if root is not None and callback is not None:
        root.after(100, callback)
    return count


def should_hide_to_tray(tray_available: bool) -> bool:
    return bool(tray_available)


_WORDS = {
    'es': {
        'game': 'Juego', 'ai': 'IA', 'data': 'Datos', 'app': 'App',
        'activity': 'Actividad', 'configure': 'Configurar IA',
        'logs': 'Abrir registro', 'help': 'Ayuda', 'exit': 'Salir',
        'confirm_title': 'Salir de AskForever App',
        'confirm': ('Si cierras AskForever App, el addon dejará de responder hasta que la vuelvas '
                    'a abrir. ¿Salir?'),
        'running': 'En marcha', 'waiting': 'Esperando al juego',
        'updating': 'Actualizando…', 'unknown': 'Sin información',
        'open': 'Abrir', 'quit': 'Salir',
    },
    'en': {
        'game': 'Game', 'ai': 'AI', 'data': 'Data', 'app': 'App',
        'activity': 'Activity', 'configure': 'Configure AI',
        'logs': 'Open log', 'help': 'Help', 'exit': 'Quit',
        'confirm_title': 'Quit AskForever App',
        'confirm': ('If you close AskForever App, the addon will stop responding until you open it '
                    'again. Quit?'),
        'running': 'Running', 'waiting': 'Waiting for the game',
        'updating': 'Updating…', 'unknown': 'No information',
        'open': 'Open', 'quit': 'Quit',
    },
}


class AppWindow(tk.Tk):
    """Tk window; callbacks from other threads are marshalled through queues."""

    def __init__(self, on_configure=None, on_exit=None, language=None, bus=None):
        super().__init__()
        self.language = language or ui_language()
        self.words = _WORDS[self.language]
        self.on_configure = on_configure
        self.on_exit = on_exit
        self.bus = bus or get_bus()
        self.events = queue.Queue()
        self.commands = queue.Queue()
        self.tray = None
        self._closing = False
        self._activity_count = 0

        self.title('AskForever App')
        self.geometry('640x520')
        self.minsize(520, 420)
        self.configure(background=BG)
        icon_path = Path(__file__).parent / 'askforever.ico'
        try:
            self.iconbitmap(str(icon_path))
        except (tk.TclError, OSError):
            pass

        self._build()
        self.bus.subscribe(self.events.put)
        for event in self.bus.recent():
            self._append_event(event)
        self.protocol('WM_DELETE_WINDOW', self.hide_or_exit)
        self.after(100, self._poll)

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        header = tk.Frame(self, bg=BG, padx=18, pady=12)
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(1, weight=1)
        try:
            logo = tk.PhotoImage(file=str(Path(__file__).parent / 'askforever.ico'))
            self._logo = logo
            tk.Label(header, image=logo, bg=BG).grid(row=0, column=0, rowspan=2,
                                                     padx=(0, 12))
        except (tk.TclError, OSError):
            pass
        tk.Label(header, text='AskForever App', fg=GOLD, bg=BG,
                 font=('Segoe UI', 17, 'bold')).grid(row=0, column=1, sticky='w')
        self.main_status = tk.Label(header, text=self.words['waiting'], fg=TEXT,
                                    bg=BG, font=('Segoe UI', 12, 'bold'))
        self.main_status.grid(row=1, column=1, sticky='w', pady=(4, 0))

        cards = tk.Frame(self, bg=BG, padx=14)
        cards.grid(row=1, column=0, sticky='ew')
        for column in (0, 1):
            cards.columnconfigure(column, weight=1)
        self.status_labels = {}
        self.status_dots = {}
        for index, key in enumerate(('game', 'ai', 'data', 'app')):
            row, column = divmod(index, 2)
            card = tk.Frame(cards, bg=PANEL, highlightbackground=BORDER,
                            highlightthickness=1, padx=12, pady=8)
            card.grid(row=row, column=column, sticky='ew', padx=4, pady=4)
            card.columnconfigure(1, weight=1)
            tk.Label(card, text=self.words[key], fg=GOLD, bg=PANEL,
                     font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w')
            dot = tk.Label(card, text='●', fg=DIM, bg=PANEL, font=('Segoe UI', 12))
            dot.grid(row=1, column=0, sticky='w', padx=(0, 8))
            text = tk.Label(card, text=self.words['unknown'], fg=TEXT, bg=PANEL,
                            anchor='w', justify='left', wraplength=230)
            text.grid(row=1, column=1, sticky='ew')
            self.status_labels[key] = text
            self.status_dots[key] = dot

        activity_frame = tk.Frame(self, bg=BG, padx=18, pady=6)
        activity_frame.grid(row=2, column=0, sticky='nsew')
        activity_frame.rowconfigure(1, weight=1)
        activity_frame.columnconfigure(0, weight=1)
        tk.Label(activity_frame, text=self.words['activity'], fg=GOLD, bg=BG,
                 font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, sticky='w', pady=(0, 5))
        self.activity = tk.Text(activity_frame, height=8, wrap='word', state='disabled',
                                bg=PANEL, fg=TEXT, insertbackground=TEXT,
                                selectbackground=BORDER, relief='flat', padx=8, pady=6,
                                font=('Segoe UI', 9))
        self.activity.grid(row=1, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(activity_frame, command=self.activity.yview)
        scrollbar.grid(row=1, column=1, sticky='ns')
        self.activity.configure(yscrollcommand=scrollbar.set)
        self.activity.tag_configure('normal', foreground=TEXT)
        self.activity.tag_configure('error', foreground=ERROR)
        self.activity.tag_configure('answer', foreground=OK)

        buttons = tk.Frame(self, bg=BG, padx=14, pady=10)
        buttons.grid(row=3, column=0, sticky='ew')
        for column in range(4):
            buttons.columnconfigure(column, weight=1)
        self.configure_button = tk.Button(
            buttons, text=self.words['configure'], command=self._open_configuration,
            state='normal' if self.on_configure is not None else 'disabled',
            bg=PANEL, fg=TEXT, activebackground=BORDER, activeforeground=GOLD,
            disabledforeground=DIM, relief='flat')
        self.configure_button.grid(row=0, column=0, sticky='ew', padx=4)
        button_options = dict(bg=PANEL, fg=TEXT, activebackground=BORDER,
                              activeforeground=GOLD, relief='flat')
        tk.Button(buttons, text=self.words['logs'], command=self.open_logs,
                  **button_options).grid(
            row=0, column=1, sticky='ew', padx=4)
        tk.Button(buttons, text=self.words['help'], command=self.open_help,
                  **button_options).grid(
            row=0, column=2, sticky='ew', padx=4)
        tk.Button(buttons, text=self.words['exit'], command=self.request_exit,
                  **button_options).grid(
            row=0, column=3, sticky='ew', padx=4)

    def set_tray(self, tray):
        self.tray = tray

    def submit_command(self, command):
        self.commands.put(command)

    def _append_event(self, event):
        at_bottom = self.activity.yview()[1] >= 0.99
        self.activity.configure(state='normal')
        self.activity.insert('end', format_event(event, self.language) + '\n',
                             event_tag(event.kind))
        self._activity_count += 1
        if self._activity_count > 200:
            self.activity.delete('1.0', '2.0')
            self._activity_count -= 1
        if at_bottom:
            self.activity.see('end')
        self.activity.configure(state='disabled')

    def _refresh_statuses(self):
        statuses = self.bus.statuses()
        for key, status in statuses.items():
            text = status[self.language] or self.words['unknown']
            self.status_labels[key].configure(text=text)
            ok = status['ok']
            colour = OK if ok is True else ERROR if ok is False else DIM
            self.status_dots[key].configure(fg=colour)
        app_status = statuses['app'][self.language]
        self.main_status.configure(text=app_status or self.words['waiting'])

    def _poll(self):
        if self._closing:
            return
        drain_event_queue(self.events, self._append_event, root=self,
                          callback=self._poll)
        self._refresh_statuses()
        while True:
            try:
                command = self.commands.get_nowait()
            except queue.Empty:
                break
            if command == 'open':
                self.deiconify()
                self.lift()
            elif command == 'exit':
                self.request_exit()

    def _open_configuration(self):
        if self.on_configure is not None:
            self.on_configure()

    def open_logs(self):
        path = config.user_data_dir().parent / 'logs'
        path.mkdir(parents=True, exist_ok=True)
        startfile = getattr(os, 'startfile', None)
        if startfile is not None:
            startfile(str(path))

    def open_help(self):
        webbrowser.open(setup_wizard.GUIDE_URL)

    def hide_or_exit(self):
        if should_hide_to_tray(self.tray is not None):
            self.withdraw()
            if self.language == 'es':
                title = 'AskForever App sigue en marcha'
                text = ('Está en la bandeja del sistema, junto al reloj. Déjala abierta: sin ella, '
                        'el addon no puede responder. Para salir: clic derecho en el icono → Salir.')
            else:
                title = 'AskForever App is still running'
                text = ('It is in the system tray, next to the clock. Keep it running: without it '
                        'the addon cannot answer. To quit: right-click the icon → Quit.')
            self.tray.show_balloon(title, text)
        else:
            self.request_exit()

    def request_exit(self):
        if not messagebox.askyesno(self.words['confirm_title'], self.words['confirm'], parent=self):
            return
        self._closing = True
        self.bus.unsubscribe(self.events.put)
        if self.on_exit is not None:
            self.on_exit()
        else:
            self.destroy()
