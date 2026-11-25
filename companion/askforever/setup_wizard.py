"""Asistente de primer arranque para configurar la clave de la API."""

from __future__ import annotations

import getpass
import inspect
from typing import Callable, Optional

from askforever import config
from askforever.providers.openai_compat import OpenAICompatProvider, ProviderError
from askforever.system_env import open_url as open_browser

GUIDE_URL = 'https://github.com/warcrafted-server/AskForever/blob/main/docs/CLAVE_GEMINI.md'
MAX_ATTEMPTS = 3


def _provider_name() -> str:
    try:
        return config.get_provider_name()
    except ValueError:
        return config.DEFAULT_PROVIDER


def _default_test(key: str) -> bool:
    """Prueba la clave pegada con la misma petición que test-key."""
    name = _provider_name()
    preset = config.get_preset(name)
    model = config.get_model(name)
    if not model:
        raise ProviderError('bad_request', 'Falta el modelo de la API.')
    provider = OpenAICompatProvider(preset.base_url, key, model)
    provider.chat('Responde solo con la palabra OK.', 'ping', max_tokens=256)
    return True


def _call_test(test_fn, key: str):
    """Llama al probador inyectado, acepte o no el argumento de la clave."""
    try:
        parameters = list(inspect.signature(test_fn).parameters.values())
    except (TypeError, ValueError):
        return test_fn(key)
    positional = [parameter for parameter in parameters
                  if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                        inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    has_varargs = any(parameter.kind is inspect.Parameter.VAR_POSITIONAL
                      for parameter in parameters)
    if positional or has_varargs:
        return test_fn(key)
    return test_fn()


def _ask_guide(input_fn, open_url) -> None:
    try:
        answer = (input_fn('¿Quieres que abra la guía en el navegador? [S/n]: ') or '')
        answer = answer.strip().lower()
    except (EOFError, KeyboardInterrupt, OSError):
        print()
        return
    if answer in ('n', 'no'):
        print(f'Guía: {GUIDE_URL}')
        return
    opened = False
    try:
        opened = bool(open_url(GUIDE_URL))
    except Exception:
        opened = False
    if not opened:
        print(f'No se pudo abrir el navegador. Abre esta guía: {GUIDE_URL}')


def _save_key(key: str, provider_name: str) -> None:
    """Guarda la clave aceptando también dobles de prueba de un solo argumento."""
    try:
        parameters = list(inspect.signature(config.set_api_key).parameters.values())
    except (TypeError, ValueError):
        config.set_api_key(key, provider_name)
        return
    positional = [parameter for parameter in parameters
                  if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                        inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    has_varargs = any(parameter.kind is inspect.Parameter.VAR_POSITIONAL
                      for parameter in parameters)
    keyword_provider = any(parameter.name == 'provider'
                           and parameter.kind is inspect.Parameter.KEYWORD_ONLY
                           for parameter in parameters)
    if len(positional) >= 2 or has_varargs:
        config.set_api_key(key, provider_name)
    elif keyword_provider:
        config.set_api_key(key, provider=provider_name)
    else:
        config.set_api_key(key)


def _read_key(getpass_fn, provider_name: str) -> str:
    prompt = f'Pega tu clave de {provider_name.capitalize()}: '
    try:
        return (getpass_fn(prompt) or '').strip()
    except (EOFError, KeyboardInterrupt, OSError):
        print()
        return ''


def run_wizard(input_fn: Callable[[str], str] = input,
               getpass_fn: Callable[[str], str] = getpass.getpass,
               open_url: Callable[[str], object] = open_browser,
               test_fn: Optional[Callable] = None) -> bool:
    """Guía al jugador para probar y guardar una clave; True si la guardó."""
    print('Bienvenido a AskForever.')
    print('AskForever necesita una clave gratuita de Google Gemini '
          'para responder a tus preguntas.')
    print('La guía explica cómo conseguirla y configurarla.')
    _ask_guide(input_fn, open_url)

    provider_name = _provider_name()
    tester = test_fn if test_fn is not None else _default_test
    for attempt in range(1, MAX_ATTEMPTS + 1):
        key = _read_key(getpass_fn, provider_name)
        if not key:
            print('No se configuró la clave.')
            return False

        print('Probando la clave...')
        try:
            result = _call_test(tester, key)
            if isinstance(result, Exception):
                raise result
            failed_test = (isinstance(result, tuple) and result
                           and result[0] is False)
            if failed_test or (result is not None and not result):
                print('La clave no funciona. Revisa la guía e inténtalo de nuevo.')
                if attempt < MAX_ATTEMPTS:
                    print(f'Intento {attempt} de {MAX_ATTEMPTS}.')
                continue
        except ProviderError as error:
            print(error.user_message('esES'))
            if error.detail:
                detail = str(error.detail).replace(key, '<clave>')
                print(f'Detalle: {detail}')
            if attempt < MAX_ATTEMPTS:
                print(f'Intento {attempt} de {MAX_ATTEMPTS}.')
            continue
        except (EOFError, KeyboardInterrupt):
            print()
            print('No se configuró la clave.')
            return False
        except Exception as error:
            message = str(error).strip() or 'Error desconocido'
            message = message.replace(key, '<clave>')
            print(f'No se pudo probar la clave: {message}')
            if attempt < MAX_ATTEMPTS:
                print(f'Intento {attempt} de {MAX_ATTEMPTS}.')
            continue

        try:
            _save_key(key, provider_name)
        except ValueError:
            print('La clave está vacía; no se ha guardado nada.')
            return False
        except Exception:
            print('No se pudo guardar la clave en el Administrador de credenciales de Windows.')
            return False
        print(f'Clave guardada: {config.mask_key(key)}')
        print('Ya puedes usar AskForever.')
        return True

    print('No se ha guardado la clave.')
    return False
