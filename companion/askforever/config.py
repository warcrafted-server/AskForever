"""Configuración del companion: proveedores de IA, modelo y clave."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import keyring

KEYRING_SERVICE = 'AskForever'
KEYRING_USER = 'gemini'
GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/'
DEFAULT_MODEL = 'gemini-3.5-flash-lite'
FALLBACK_MODEL = 'gemini-3.5-flash'

MODEL_ENV = 'ASKFOREVER_MODEL'
KEY_ENV = 'ASKFOREVER_GEMINI_KEY'
DEFAULT_PROVIDER = 'gemini'
PROVIDER_ENV = 'ASKFOREVER_PROVIDER'
TEMPERATURE_ENV = 'ASKFOREVER_TEMPERATURE'
DEFAULT_TEMPERATURE = 0.2
WOWDATA_ENV = 'ASKFOREVER_WOWDATA'


@dataclass(frozen=True)
class ProviderPreset:
    """Datos del proveedor: endpoint, modelo por defecto y dónde va la clave."""

    name: str
    base_url: str
    default_model: Optional[str]
    keyring_user: str
    key_env: str
    key_url: str


PROVIDERS = {
    'gemini': ProviderPreset(
        'gemini', GEMINI_BASE_URL, DEFAULT_MODEL, 'gemini',
        'ASKFOREVER_GEMINI_KEY', 'https://aistudio.google.com',
    ),
    'groq': ProviderPreset(
        'groq', 'https://api.groq.com/openai/v1', 'llama-3.3-70b-versatile', 'groq',
        'ASKFOREVER_GROQ_KEY', 'https://console.groq.com/keys',
    ),
    'mistral': ProviderPreset(
        'mistral', 'https://api.mistral.ai/v1', None, 'mistral',
        'ASKFOREVER_MISTRAL_KEY', 'https://console.mistral.ai/api-keys',
    ),
    'cerebras': ProviderPreset(
        'cerebras', 'https://api.cerebras.ai/v1', None, 'cerebras',
        'ASKFOREVER_CEREBRAS_KEY', 'https://cloud.cerebras.ai',
    ),
    'openrouter': ProviderPreset(
        'openrouter', 'https://openrouter.ai/api/v1', None, 'openrouter',
        'ASKFOREVER_OPENROUTER_KEY', 'https://openrouter.ai/settings/keys',
    ),
}


def get_provider_name(name: Optional[str] = None) -> str:
    """Nombre del proveedor pedido, del entorno o el de por defecto."""
    candidate = (name or '').strip() or os.environ.get(PROVIDER_ENV, '').strip() or DEFAULT_PROVIDER
    candidate = candidate.lower()
    if candidate not in PROVIDERS:
        valid = ', '.join(sorted(PROVIDERS))
        raise ValueError(f'Proveedor desconocido: {candidate}. Válidos: {valid}')
    return candidate


def get_preset(name: Optional[str] = None) -> ProviderPreset:
    """Preset del proveedor indicado."""
    return PROVIDERS[get_provider_name(name)]


def get_model(provider: Optional[str] = None, model: Optional[str] = None) -> Optional[str]:
    """Modelo explícito, del entorno o el de por defecto del proveedor."""
    selected = str(model).strip() if model else ''
    if selected:
        return selected
    name = get_provider_name(provider)
    env_model = os.environ.get(MODEL_ENV, '').strip()
    if env_model and name == get_provider_name():
        return env_model
    return PROVIDERS[name].default_model


def get_api_key(provider: Optional[str] = None) -> Optional[str]:
    """Clave guardada del proveedor, o su variable de entorno."""
    preset = get_preset(provider)
    stored = None
    try:
        stored = keyring.get_password(KEYRING_SERVICE, preset.keyring_user)
    except Exception:
        stored = None
    if stored:
        stored = stored.strip()
        if stored:
            return stored
    fallback = os.environ.get(preset.key_env, '').strip()
    return fallback or None


def set_api_key(key: str, provider: Optional[str] = None) -> None:
    """Guarda la clave del proveedor en el Administrador de credenciales."""
    key = (key or '').strip()
    if not key:
        raise ValueError('empty API key')
    preset = get_preset(provider)
    keyring.set_password(KEYRING_SERVICE, preset.keyring_user, key)


def mask_key(key: str) -> str:
    """Vista segura de la clave: cuatro primeros caracteres y longitud."""
    key = key or ''
    return f'{key[:4]}…({len(key)} caracteres)'


def get_temperature() -> float:
    """Temperatura configurada en ASKFOREVER_TEMPERATURE, recortada a 0..2."""
    value = os.environ.get(TEMPERATURE_ENV, '').strip()
    try:
        temperature = float(value)
    except (TypeError, ValueError):
        return DEFAULT_TEMPERATURE
    return max(0.0, min(2.0, temperature))


def _sibling_wowdata_path() -> Path:
    return Path(__file__).resolve().parents[2].parent / 'wowdata' / 'datos' / 'wow.sqlite'


def get_wowdata_path() -> Optional[Path]:
    """Ruta de la base de wowdata: entorno o hermana, solo si existe."""
    env_path = os.environ.get(WOWDATA_ENV, '').strip()
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return candidate
    sibling = _sibling_wowdata_path()
    if sibling.is_file():
        return sibling
    return None


def open_wowdata():
    """Abre la base de wowdata en solo lectura, o None si no está disponible."""
    from askforever.data.wowdb import WowDb

    path = get_wowdata_path()
    if path is None:
        return None
    database = WowDb(path)
    if not database.available():
        database.close()
        return None
    return database
