"""Window-based setup for the Gemini API key."""

from __future__ import annotations

from dataclasses import dataclass
import queue
import threading
import webbrowser
import tkinter as tk

from askforever import setup_wizard
from askforever.app.window import BG, BORDER, DIM, ERROR, GOLD, OK, PANEL, TEXT
from askforever.providers.openai_compat import ProviderError


def validate_key_text(key: str) -> str:
    """Return a trimmed key, or an empty string when no key was entered."""
    return str(key or '').strip()


@dataclass(frozen=True)
class TestOutcome:
    success: bool
    message: str
    provider_error: bool = False


def test_key_outcome(key, test_fn=None, lang='es') -> TestOutcome:
    """Run a key test and map its result to player-facing text."""
    key = validate_key_text(key)
    if not key:
        return TestOutcome(False, 'Pega tu clave primero' if lang == 'es'
                           else 'Paste your key first')
    tester = test_fn or setup_wizard._default_test
    try:
        result = setup_wizard._call_test(tester, key)
        if isinstance(result, Exception):
            raise result
        failed_test = (isinstance(result, tuple) and result
                       and result[0] is False)
        if failed_test or (result is not None and not result):
            raise RuntimeError('key test returned false')
    except ProviderError as error:
        return TestOutcome(False, error.user_message('esES' if lang == 'es' else 'enUS'),
                           provider_error=True)
    except Exception:
        message = ('No se pudo probar la clave. Revisa tu conexión.' if lang == 'es'
                   else 'Could not test the key. Check your connection.')
        return TestOutcome(False, message)
    return TestOutcome(True, 'Clave correcta y guardada' if lang == 'es'
                       else 'Key is valid and saved')


class ProviderHolder:
    """Thread-safe reference to the provider used by the answer path."""

    def __init__(self, provider=None):
        self._lock = threading.Lock()
        self._provider = provider

    def get(self):
        with self._lock:
            return self._provider

    def swap(self, provider):
        with self._lock:
            previous = self._provider
            self._provider = provider
            return previous


class SetupDialog(tk.Toplevel):
    """Modal dialog for testing and saving the Gemini API key."""

    def __init__(self, parent, lang, on_saved):
        super().__init__(parent)
        self.parent = parent
        self.lang = 'es' if lang == 'es' else 'en'
        self.on_saved = on_saved
        self._worker_running = False
        self._results = queue.Queue()
        self.title('Configurar la IA' if self.lang == 'es' else 'Set up the AI')
        self.configure(background=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self._build()
        self.grab_set()
        self.key_entry.focus_set()
        self.after(50, self._poll_results)

    def _build(self):
        spanish = self.lang == 'es'
        self.columnconfigure(0, weight=1)
        tk.Label(
            self,
            text=('AskForever App usa la IA de Google (Gemini). La clave es gratuita y se '
                  'guarda cifrada en el Administrador de credenciales de Windows.'
                  if spanish else
                  'AskForever App uses Google AI (Gemini). The key is free and is stored '
                  'encrypted in Windows Credential Manager.'),
            fg=TEXT, bg=BG, wraplength=430, justify='left',
            font=('Segoe UI', 10), padx=20, pady=16,
        ).grid(row=0, column=0, sticky='ew')

        link = tk.Label(
            self, text=('Cómo conseguir la clave gratis' if spanish else
                        'How to get a free key'),
            fg=GOLD, bg=BG, cursor='hand2', font=('Segoe UI', 10, 'underline'),
        )
        link.grid(row=1, column=0, sticky='w', padx=20, pady=(0, 12))
        link.bind('<Button-1>', lambda _event: webbrowser.open(setup_wizard.GUIDE_URL))

        entry_row = tk.Frame(self, bg=BG, padx=20)
        entry_row.grid(row=2, column=0, sticky='ew')
        entry_row.columnconfigure(0, weight=1)
        self.key_entry = tk.Entry(
            entry_row, show='•', bg=PANEL, fg=TEXT, insertbackground=TEXT,
            relief='flat', font=('Segoe UI', 10),
        )
        self.key_entry.grid(row=0, column=0, sticky='ew', ipady=6)
        self.show_key = tk.BooleanVar(value=False)
        tk.Checkbutton(
            entry_row, text='Mostrar' if spanish else 'Show', variable=self.show_key,
            command=self._toggle_key, fg=TEXT, bg=BG, activebackground=BG,
            activeforeground=GOLD, selectcolor=PANEL,
        ).grid(row=0, column=1, padx=(10, 0))

        self.status = tk.Label(self, text='', fg=TEXT, bg=BG, anchor='w',
                               wraplength=430, justify='left')
        self.status.grid(row=3, column=0, sticky='ew', padx=20, pady=(12, 6))

        buttons = tk.Frame(self, bg=BG, padx=20, pady=12)
        buttons.grid(row=4, column=0, sticky='ew')
        for column in (0, 1):
            buttons.columnconfigure(column, weight=1)
        self.test_button = tk.Button(
            buttons, text='Probar y guardar' if spanish else 'Test and save',
            command=self._test_and_save, bg=PANEL, fg=TEXT, activebackground=BORDER,
            activeforeground=GOLD, relief='flat',
        )
        self.test_button.grid(row=0, column=0, sticky='ew', padx=(0, 5))
        tk.Button(
            buttons, text='Cancelar' if spanish else 'Cancel', command=self.destroy,
            bg=PANEL, fg=TEXT, activebackground=BORDER, activeforeground=GOLD,
            relief='flat',
        ).grid(row=0, column=1, sticky='ew', padx=(5, 0))

    def _toggle_key(self):
        self.key_entry.configure(show='' if self.show_key.get() else '•')

    def _set_status(self, text, colour=TEXT):
        self.status.configure(text=text, fg=colour)

    def _test_and_save(self):
        key = validate_key_text(self.key_entry.get())
        if not key:
            self._set_status('Pega tu clave primero' if self.lang == 'es'
                             else 'Paste your key first', ERROR)
            return
        if self._worker_running:
            return
        self._worker_running = True
        self.test_button.configure(state='disabled')
        self._set_status('Probando la clave…' if self.lang == 'es'
                         else 'Testing the key…', DIM)

        def test_in_background():
            outcome = test_key_outcome(key, lang=self.lang)
            self._results.put((key, outcome))

        threading.Thread(target=test_in_background, name='AskForeverKeyTest',
                         daemon=True).start()

    def _poll_results(self):
        if not self.winfo_exists():
            return
        try:
            key, outcome = self._results.get_nowait()
        except queue.Empty:
            self.after(50, self._poll_results)
            return
        self._finish_test(key, outcome)

    def _finish_test(self, key, outcome):
        self._worker_running = False
        if not self.winfo_exists():
            return
        self.test_button.configure(state='normal')
        if not outcome.success:
            self._set_status(outcome.message, ERROR)
            return
        try:
            setup_wizard._save_key(key, 'gemini')
        except Exception:
            self._set_status(
                'No se pudo guardar la clave en el Administrador de credenciales de Windows.'
                if self.lang == 'es' else
                'Could not save the key in Windows Credential Manager.', ERROR)
            return
        self._set_status(outcome.message, OK)
        self.on_saved()
        self.after(1000, self.destroy)
