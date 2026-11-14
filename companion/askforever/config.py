"""Configuración del companion: modelo de IA y clave de la API."""

from __future__ import annotations

import os
from typing import Optional

import keyring

KEYRING_SERVICE = 'AskForever'
KEYRING_USER = 'gemini'
GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/'
DEFAULT_MODEL = 'gemini-3.5-flash-lite'
FALLBACK_MODEL = 'gemini-3.5-flash'

MODEL_ENV = 'ASKFOREVER_MODEL'
KEY_ENV = 'ASKFOREVER_GEMINI_KEY'


def get_model() -> str:
    """Modelo configurado en ASKFOREVER_MODEL o el de por defecto."""
    model = os.environ.get(MODEL_ENV, '').strip()
    return model or DEFAULT_MODEL


def get_api_key() -> Optional[str]:
    """Clave guardada en el Administrador de credenciales, o del entorno."""
    stored = None
    try:
        stored = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
    except Exception:
        stored = None
    if stored:
        stored = stored.strip()
        if stored:
            return stored
    fallback = os.environ.get(KEY_ENV, '').strip()
    return fallback or None


def set_api_key(key: str) -> None:
    """Guarda la clave en el Administrador de credenciales de Windows."""
    key = (key or '').strip()
    if not key:
        raise ValueError('empty API key')
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, key)


def mask_key(key: str) -> str:
    """Vista segura de la clave: cuatro primeros caracteres y longitud."""
    key = key or ''
    return f'{key[:4]}…({len(key)} caracteres)'
