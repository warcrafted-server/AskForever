"""Pruebas del cliente de la wiki con una descarga falsa, sin red."""

from __future__ import annotations

import urllib.parse

from askforever import __version__
from askforever.web import wiki
from askforever.web.wiki import WikiClient, WikiExcerpt

QUERY = 'Classic fishing zones Alliance'
KEYWORDS = ['fishing', 'zone', 'skill', 'Alliance']

GENERIC = (
    'This page describes a topic. It has several sections and links to related articles. '
    'It does not mention any specific place or activity, only general information. ' * 3
)
RELEVANT = (
    'Elwynn Forest is an Alliance fishing zone with plenty of lakes. You need fishing skill '
    'to catch the fish that live there. Many players visit it to practise their skill.'
)
FOREVER_PAGE = GENERIC + '\n\n' + RELEVANT + '\n\nAnother paragraph about fishing.'
CLASSIC_PAGE = (GENERIC + '\n\nElwynn Forest (Classic) is an Alliance zone. '
                'Fishing and skill matter here.')
FISHING_PAGE = GENERIC
DISAMBIGUATION_PAGE = ('This is a disambiguation page. It may refer to several articles.'
                       '\n\n' + GENERIC)
SHORT_PAGE = 'Too short to be useful.'

TITLES = ['Fishing', 'Forever fishing techniques', 'Elwynn Forest (Classic)',
          'Fishing (disambiguation)', 'Short page']
PAGES = {
    'Fishing': FISHING_PAGE,
    'Forever fishing techniques': FOREVER_PAGE,
    'Elwynn Forest (Classic)': CLASSIC_PAGE,
    'Fishing (disambiguation)': DISAMBIGUATION_PAGE,
    'Short page': SHORT_PAGE,
}


class FakeFetch:
    """Descarga falsa que responde según los parámetros de la URL."""

    def __init__(self, pages, titles=None):
        self.pages = dict(pages)
        self.titles = list(titles) if titles is not None else list(pages)
        self.calls = []

    def __call__(self, url, timeout):
        self.calls.append((url, timeout))
        params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if params.get('list') == ['search']:
            return {'query': {'search': [{'title': title} for title in self.titles]}}
        title = params.get('titles', [''])[0]
        return {'query': {'pages': [{'title': title,
                                     'extract': self.pages.get(title, '')}]}}


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_lookup_prioritizes_forever_and_classic():
    client = WikiClient(fetch=FakeFetch(PAGES), max_pages=2)
    excerpts = client.lookup(QUERY, KEYWORDS)

    assert [excerpt.title for excerpt in excerpts] == [
        'Forever fishing techniques', 'Elwynn Forest (Classic)']
    assert all(isinstance(excerpt, WikiExcerpt) for excerpt in excerpts)

    forever = excerpts[0]
    assert 'Elwynn' in forever.text
    assert 'skill' in forever.text
    assert 'page describes a topic' not in forever.text
    assert forever.url == wiki.WIKI_PAGE_URL + 'Forever_fishing_techniques'
    assert excerpts[1].url == wiki.WIKI_PAGE_URL + 'Elwynn_Forest_%28Classic%29'


def test_lookup_discards_disambiguation_and_short_pages():
    client = WikiClient(fetch=FakeFetch(PAGES), max_pages=5)
    titles = [excerpt.title for excerpt in client.lookup(QUERY, KEYWORDS)]

    assert 'Forever fishing techniques' in titles
    assert 'Elwynn Forest (Classic)' in titles
    assert 'Fishing (disambiguation)' not in titles
    assert 'Short page' not in titles


def test_lookup_respects_max_chars():
    client = WikiClient(fetch=FakeFetch(PAGES), max_pages=1, max_chars=120)
    excerpts = client.lookup(QUERY, KEYWORDS)

    assert excerpts
    assert len(excerpts[0].text) <= 120


def test_lookup_falls_back_to_first_chars_without_matches():
    neutral = ('Neutral words only. ' * 40).strip()
    fake = FakeFetch({'Neutral page': neutral}, ['Neutral page'])
    client = WikiClient(fetch=fake, max_pages=1)
    excerpts = client.lookup('fishing', ['fishing'])

    assert excerpts
    assert excerpts[0].text == neutral[:600]


def test_cache_avoids_second_fetch():
    fake = FakeFetch(PAGES)
    client = WikiClient(fetch=fake)
    first = client.lookup(QUERY, KEYWORDS)
    calls_after_first = len(fake.calls)

    second = client.lookup('  classic FISHING zones alliance  ', KEYWORDS)

    assert len(fake.calls) == calls_after_first
    assert [excerpt.title for excerpt in second] == [excerpt.title for excerpt in first]


def test_cache_expires_with_clock():
    clock = FakeClock()
    fake = FakeFetch(PAGES)
    client = WikiClient(fetch=fake, clock=clock, cache_ttl=10.0)
    client.lookup(QUERY, KEYWORDS)
    calls_after_first = len(fake.calls)

    clock.now = 10.0
    client.lookup(QUERY, KEYWORDS)

    assert len(fake.calls) > calls_after_first


def test_network_error_returns_empty_and_last_error():
    def failing_fetch(url, timeout):
        raise OSError('sin red')

    client = WikiClient(fetch=failing_fetch)
    assert client.lookup('Classic fishing', ['fishing']) == []
    assert client.last_error


def test_build_request_has_user_agent():
    request = wiki._build_request(wiki.WIKI_API)
    header = request.get_header('User-agent') or request.headers.get('User-Agent') or ''

    assert 'AskForever-companion/' in header
    assert __version__ in header
