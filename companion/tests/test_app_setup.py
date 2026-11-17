import pytest

from askforever.app.setup import (
    ProviderHolder,
    SetupDialog,
    test_key_outcome as get_test_key_outcome,
    validate_key_text,
)
from askforever.providers.openai_compat import ProviderError


def test_validate_key_text_trims_and_rejects_empty_values():
    assert validate_key_text('  gemini-key  ') == 'gemini-key'
    assert validate_key_text('   ') == ''


def test_test_key_outcome_handles_success_and_empty_key():
    received = []
    outcome = get_test_key_outcome(' key ', lambda key: received.append(key) or True)

    assert received == ['key']
    assert outcome.success
    assert outcome.message == 'Clave correcta y guardada'
    assert get_test_key_outcome('', lambda: True).message == 'Pega tu clave primero'


def test_test_key_outcome_maps_provider_and_unexpected_errors():
    provider_error = get_test_key_outcome(
        'key', lambda _key: (_ for _ in ()).throw(ProviderError('auth')), lang='en')
    unexpected = get_test_key_outcome(
        'key', lambda _key: (_ for _ in ()).throw(RuntimeError('offline')), lang='es')

    assert provider_error.provider_error
    assert provider_error.message == 'The Google key is invalid or not saved. Check the guide.'
    assert unexpected.message == 'No se pudo probar la clave. Revisa tu conexión.'


def test_provider_holder_swaps_provider_safely():
    first, second = object(), object()
    holder = ProviderHolder(first)

    assert holder.get() is first
    assert holder.swap(second) is first
    assert holder.get() is second


def test_setup_dialog_can_be_created_when_tkinter_is_available():
    try:
        import tkinter as tk
        root = tk.Tk()
    except Exception as error:
        pytest.skip(f'tkinter display unavailable: {error}')
    try:
        dialog = SetupDialog(root, 'en', lambda: None)
        assert dialog.title() == 'Set up the AI'
        assert dialog.test_button['state'] == 'normal'
    finally:
        root.destroy()
