"""Cliente de la API de warcraft.wiki.gg: búsqueda y extracción de texto."""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

from askforever import __version__

WIKI_API = 'https://warcraft.wiki.gg/api.php'
WIKI_PAGE_URL = 'https://warcraft.wiki.gg/wiki/'
USER_AGENT = (f'AskForever-companion/{__version__} '
              '(+https://github.com/warcrafted-server/AskForever)')
MAX_LOOKUP_SECONDS = 8.0
MIN_PAGE_CHARS = 200
FALLBACK_CHARS = 600
MAX_ERROR_CHARS = 160


def _build_request(url: str) -> urllib.request.Request:
    """Petición GET con el User-Agent obligatorio, sin enviarla."""
    return urllib.request.Request(url, headers={'User-Agent': USER_AGENT})


def _default_fetch(url: str, timeout: float) -> dict:
    """Descarga y decodifica el JSON de la API; propaga errores HTTP o de red."""
    request = _build_request(url)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
    return json.loads(payload.decode('utf-8'))


def _normalize(text) -> str:
    """Minúsculas, sin tildes ni signos, con espacios simples."""
    text = str(text or '').lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _error_text(error) -> str:
    text = str(error).strip() or type(error).__name__
    return text[:MAX_ERROR_CHARS]


def _rank_titles(titles) -> list[str]:
    forever = []
    classic = []
    rest = []
    for title in titles:
        lower = title.lower()
        if 'forever' in lower:
            forever.append(title)
        elif 'classic' in lower:
            classic.append(title)
        else:
            rest.append(title)
    return forever + classic + rest


def _is_disambiguation_title(title: str) -> bool:
    normalized = _normalize(title)
    return 'disambiguation' in normalized or 'desambiguacion' in normalized


def _is_disambiguation_text(text: str) -> bool:
    lower = text.lower()
    return 'disambiguation page' in lower or 'may refer to' in lower


def _paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r'\n+', text) if part.strip()]


def _token_matches(token: str, needle: str) -> bool:
    if token == needle:
        return True
    return len(needle) >= 4 and token.startswith(needle)


def _count_phrase(tokens, phrase) -> int:
    if not phrase:
        return 0
    width = len(phrase)
    count = 0
    for index in range(len(tokens) - width + 1):
        if all(_token_matches(tokens[index + offset], phrase[offset])
               for offset in range(width)):
            count += 1
    return count


def _score_paragraph(paragraph: str, query: str, keywords) -> int:
    tokens = _normalize(paragraph).split()
    if not tokens:
        return 0
    score = 0
    for keyword in keywords:
        score += 2 * _count_phrase(tokens, _normalize(keyword).split())
    for word in _normalize(query).split():
        if len(word) < 2:
            continue
        score += _count_phrase(tokens, [word])
    return score


def _page_url(title: str) -> str:
    return WIKI_PAGE_URL + urllib.parse.quote(title.replace(' ', '_'), safe='')


@dataclass
class WikiExcerpt:
    """Fragmento de una página de la wiki, con su título y su URL."""

    title: str
    url: str
    text: str


class WikiClient:
    """Busca en la wiki y devuelve los párrafos más relevantes de sus páginas."""

    def __init__(self, fetch=None, timeout: float = 6.0, cache_ttl: float = 86400.0,
                 clock: Callable[[], float] = time.monotonic,
                 max_pages: int = 2, max_chars: int = 1400) -> None:
        self.fetch = fetch or _default_fetch
        self.timeout = float(timeout)
        self.cache_ttl = float(cache_ttl)
        self.clock = clock
        self.max_pages = max(1, int(max_pages))
        self.max_chars = max(1, int(max_chars))
        self.last_error = ''
        self._cache: dict[tuple[str, str], tuple[float, object]] = {}

    def _cache_get(self, kind: str, key: str):
        entry = self._cache.get((kind, key))
        if entry is None:
            return None
        stored, value = entry
        if self.clock() - stored >= self.cache_ttl:
            self._cache.pop((kind, key), None)
            return None
        return value

    def _cache_set(self, kind: str, key: str, value) -> None:
        self._cache[(kind, key)] = (self.clock(), value)

    @staticmethod
    def _url(params: dict) -> str:
        return WIKI_API + '?' + urllib.parse.urlencode(params)

    def search(self, query: str, limit: int = 6) -> list[str]:
        """Títulos que devuelve la búsqueda, en el orden de la wiki."""
        key = _normalize(query)
        cached = self._cache_get('search', key)
        if cached is not None:
            return list(cached)
        try:
            limit = max(0, int(limit))
        except (TypeError, ValueError):
            limit = 6
        url = self._url({
            'action': 'query',
            'format': 'json',
            'formatversion': '2',
            'list': 'search',
            'srsearch': str(query or ''),
            'srlimit': str(limit),
        })
        data = self.fetch(url, self.timeout)
        if not isinstance(data, dict):
            raise ValueError('respuesta de búsqueda no válida')
        result = data.get('query')
        items = result.get('search') if isinstance(result, dict) else None
        titles = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            title = item.get('title')
            if isinstance(title, str) and title.strip():
                titles.append(title.strip())
        titles = titles[:limit]
        self._cache_set('search', key, titles)
        return list(titles)

    def page_text(self, title: str) -> str:
        """Texto plano de la página; cadena vacía si no tiene extracto."""
        key = _normalize(title)
        cached = self._cache_get('page', key)
        if cached is not None:
            return cached
        url = self._url({
            'action': 'query',
            'format': 'json',
            'formatversion': '2',
            'prop': 'extracts',
            'explaintext': '1',
            'titles': str(title or ''),
        })
        data = self.fetch(url, self.timeout)
        if not isinstance(data, dict):
            raise ValueError('respuesta de página no válida')
        query = data.get('query')
        pages = query.get('pages') if isinstance(query, dict) else None
        if isinstance(pages, dict):
            pages = list(pages.values())
        text = ''
        if isinstance(pages, list) and pages and isinstance(pages[0], dict):
            extract = pages[0].get('extract')
            if isinstance(extract, str):
                text = extract
        self._cache_set('page', key, text)
        return text

    def lookup(self, query: str, keywords) -> list[WikiExcerpt]:
        """Busca y devuelve los extractos relevantes; nunca lanza."""
        self.last_error = ''
        started = self.clock()
        try:
            return self._lookup(query, keywords or [], started)
        except Exception as error:
            self.last_error = _error_text(error)
            return []

    def _lookup(self, query: str, keywords, started: float) -> list[WikiExcerpt]:
        titles = self.search(query)
        if self.clock() - started > MAX_LOOKUP_SECONDS:
            self.last_error = 'tiempo agotado'
            return []
        excerpts = []
        seen = set()
        for title in _rank_titles(titles):
            if len(excerpts) >= self.max_pages:
                break
            if self.clock() - started > MAX_LOOKUP_SECONDS:
                self.last_error = self.last_error or 'tiempo agotado'
                break
            key = _normalize(title)
            if key in seen:
                continue
            seen.add(key)
            if _is_disambiguation_title(title):
                continue
            text = self.page_text(title)
            if _is_disambiguation_text(text) or len(text.strip()) < MIN_PAGE_CHARS:
                continue
            excerpt = self._excerpt(text, query, keywords)
            if not excerpt:
                continue
            excerpts.append(WikiExcerpt(title, _page_url(title), excerpt))
        if self.clock() - started > MAX_LOOKUP_SECONDS and not self.last_error:
            self.last_error = 'tiempo agotado'
        return excerpts

    def _excerpt(self, text: str, query: str, keywords) -> str:
        paragraphs = _paragraphs(text)
        candidates = []
        for index, paragraph in enumerate(paragraphs):
            score = _score_paragraph(paragraph, query, keywords)
            if score > 0:
                candidates.append((index, score, paragraph))
        if not candidates:
            return text.strip()[:min(FALLBACK_CHARS, self.max_chars)]

        ranked = sorted(candidates, key=lambda item: (-item[1], item[0]))
        chosen = []
        length = 0
        for index, score_value, paragraph in ranked:
            separator = 2 if chosen else 0
            remaining = self.max_chars - length - separator
            if remaining <= 0:
                break
            if len(paragraph) > remaining:
                if not chosen:
                    chosen.append((index, paragraph[:remaining]))
                break
            chosen.append((index, paragraph))
            length += len(paragraph) + separator
        if not chosen:
            return ''
        chosen.sort(key=lambda item: item[0])
        return '\n\n'.join(paragraph for _index, paragraph in chosen)
