"""Proveedor de IA compatible con la API OpenAI Chat Completions."""

from __future__ import annotations

import time
from typing import Callable, Optional

import openai

from askforever import config

_MESSAGES = {
    'auth': (
        'La clave de Google no es válida o no está guardada. Revisa la guía.',
        'The Google key is invalid or not saved. Check the guide.',
    ),
    'rate_limit': (
        'Has alcanzado el límite gratuito de Google. Espera un momento y vuelve a preguntar.',
        "You have reached Google's free limit. Wait a moment and ask again.",
    ),
    'timeout': (
        'No se pudo conectar con la IA. Comprueba tu conexión.',
        'Could not connect to the AI. Check your connection.',
    ),
    'network': (
        'No se pudo conectar con la IA. Comprueba tu conexión.',
        'Could not connect to the AI. Check your connection.',
    ),
    'empty': (
        'La IA no devolvió respuesta. Inténtalo de nuevo.',
        'The AI returned no answer. Try again.',
    ),
    'server': (
        'El servicio de IA no está disponible ahora mismo. Inténtalo más tarde.',
        'The AI service is unavailable right now. Try again later.',
    ),
    'bad_request': (
        'La petición a la IA no es válida. Prueba con otra pregunta.',
        'The AI request is invalid. Try another question.',
    ),
    'unknown': (
        'Ocurrió un error inesperado al hablar con la IA.',
        'An unexpected error occurred while talking to the AI.',
    ),
}


class ProviderError(Exception):
    """Error del proveedor con un tipo estable y un detalle sin la clave."""

    def __init__(self, kind: str, detail: str = '') -> None:
        super().__init__(detail or kind)
        self.kind = kind
        self.detail = detail

    def user_message(self, lang: str) -> str:
        """Mensaje breve para el jugador en castellano o inglés."""
        spanish = str(lang).lower() in ('eses', 'esmx')
        spanish_text, english_text = _MESSAGES.get(self.kind, _MESSAGES['unknown'])
        return spanish_text if spanish else english_text


class OpenAICompatProvider:
    """Proveedor mínimo sobre Chat Completions con reintentos propios."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        client=None,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = 3,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key or ''
        self.model = model
        self.sleep = sleep
        self.max_retries = max(0, int(max_retries))
        self.timeout = timeout
        if client is None:
            client = openai.OpenAI(
                base_url=base_url,
                api_key=self.api_key,
                timeout=timeout,
                max_retries=0,
            )
        self.client = client

    def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: Optional[int] = None,
        temperature: float = 0.3,
    ) -> str:
        """Pide una respuesta al modelo y la devuelve recortada."""
        request = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            'temperature': temperature,
        }
        if max_tokens is not None:
            request['max_tokens'] = max_tokens

        attempts = {'rate_limit': 0, 'timeout': 0, 'network': 0, 'server': 0}
        while True:
            try:
                response = self.client.chat.completions.create(**request)
            except openai.AuthenticationError as exc:
                raise self._error('auth', exc) from None
            except openai.PermissionDeniedError as exc:
                raise self._error('auth', exc) from None
            except openai.BadRequestError as exc:
                raise self._error('bad_request', exc) from None
            except openai.RateLimitError as exc:
                if attempts['rate_limit'] >= self.max_retries:
                    raise self._error('rate_limit', exc) from None
                delay = self._retry_after(exc)
                self.sleep(delay if delay is not None else float(2 ** attempts['rate_limit']))
                attempts['rate_limit'] += 1
                continue
            except openai.APITimeoutError as exc:
                if attempts['timeout'] >= 2:
                    raise self._error('timeout', exc) from None
                self.sleep(float(2 ** attempts['timeout']))
                attempts['timeout'] += 1
                continue
            except openai.APIConnectionError as exc:
                if attempts['network'] >= 2:
                    raise self._error('network', exc) from None
                self.sleep(float(2 ** attempts['network']))
                attempts['network'] += 1
                continue
            except openai.InternalServerError as exc:
                if attempts['server'] >= 2:
                    raise self._error('server', exc) from None
                self.sleep(float(2 ** attempts['server']))
                attempts['server'] += 1
                continue
            except Exception as exc:
                raise self._error('unknown', exc) from None

            content = self._content(response)
            if content is None:
                raise ProviderError('empty')
            return content

    @staticmethod
    def _content(response) -> Optional[str]:
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, KeyError, TypeError):
            return None
        if content is None:
            return None
        text = str(content).strip()
        return text or None

    def _error(self, kind: str, exc: BaseException) -> ProviderError:
        detail = str(exc)
        if self.api_key and self.api_key in detail:
            detail = detail.replace(self.api_key, '<clave>')
        return ProviderError(kind, detail)

    @staticmethod
    def _retry_after(exc: BaseException) -> Optional[float]:
        response = getattr(exc, 'response', None)
        headers = getattr(response, 'headers', None)
        if headers is None:
            return None
        value = headers.get('Retry-After')
        if value is None:
            value = headers.get('retry-after')
        if value is None:
            return None
        try:
            seconds = float(value)
        except (TypeError, ValueError):
            return None
        if 0 <= seconds <= 30:
            return seconds
        return None


def _sanitize(text, api_key) -> str:
    text = str(text)
    if api_key and api_key in text:
        text = text.replace(api_key, '<clave>')
    return text


def provider_from_config(provider=None, model=None) -> OpenAICompatProvider:
    """Crea el proveedor del registro con su clave y modelo configurados."""
    name = config.get_provider_name(provider)
    preset = config.get_preset(name)
    api_key = config.get_api_key(name)
    if not api_key:
        raise ProviderError(
            'auth',
            f'No hay clave guardada para {name}. Consíguela en {preset.key_url}',
        )
    selected_model = config.get_model(name, model)
    if not selected_model:
        raise ProviderError(
            'bad_request',
            'Falta el modelo: usa --model o `list-models --provider NOMBRE`',
        )
    return OpenAICompatProvider(preset.base_url, api_key, selected_model)


def list_models(base_url, api_key, *, client=None, timeout=20.0) -> list[str]:
    """Lista los modelos del proveedor; traduce los errores de la API."""
    if client is None:
        client = openai.OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=0,
        )
    try:
        response = client.models.list()
    except openai.AuthenticationError as exc:
        raise ProviderError('auth', _sanitize(exc, api_key)) from None
    except openai.PermissionDeniedError as exc:
        raise ProviderError('auth', _sanitize(exc, api_key)) from None
    except openai.BadRequestError as exc:
        raise ProviderError('bad_request', _sanitize(exc, api_key)) from None
    except openai.RateLimitError as exc:
        raise ProviderError('rate_limit', _sanitize(exc, api_key)) from None
    except openai.APITimeoutError as exc:
        raise ProviderError('timeout', _sanitize(exc, api_key)) from None
    except openai.APIConnectionError as exc:
        raise ProviderError('network', _sanitize(exc, api_key)) from None
    except openai.InternalServerError as exc:
        raise ProviderError('server', _sanitize(exc, api_key)) from None
    except Exception as exc:
        raise ProviderError('unknown', _sanitize(exc, api_key)) from None

    identifiers = set()
    for model in getattr(response, 'data', None) or []:
        identifier = getattr(model, 'id', None)
        if identifier is None:
            continue
        identifier = str(identifier)
        if identifier.startswith('models/'):
            identifier = identifier[len('models/'):]
        identifiers.add(identifier)
    return sorted(identifiers)
