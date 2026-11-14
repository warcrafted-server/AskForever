"""Pruebas del respaldo de la wiki en prompt, respuestas, CLI y bench, sin red."""

from __future__ import annotations

import json

import askforever.cli as cli
import askforever.engine.answer as answer
from askforever import config
from askforever.bench import Question, Target, render_markdown, run_bench
from askforever.engine.answer import answer_message, needs_web
from askforever.engine.prompt import build_prompt
from askforever.engine.retriever import Facts
from askforever.providers.openai_compat import ProviderError
from askforever.web.wiki import WIKI_PAGE_URL, WikiExcerpt

SEARCH_JSON = json.dumps({
    'queries': ['Expert Fishing', 'Fishing trainer'],
    'keywords': ['fishing', 'skill'],
})
FOREVER = WikiExcerpt(
    'Forever fishing techniques',
    WIKI_PAGE_URL + 'Forever_fishing_techniques',
    'Texto de Forever.',
)
EXPERT = WikiExcerpt(
    'Expert Fishing',
    WIKI_PAGE_URL + 'Expert_Fishing',
    'Texto de Expert.',
)
TRAINER = WikiExcerpt(
    'Fishing trainer',
    WIKI_PAGE_URL + 'Fishing_trainer',
    'Texto de trainer.',
)


class FakeProvider:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def chat(self, system, user, *, max_tokens=None, temperature=0.3):
        self.calls.append({
            'system': system,
            'user': user,
            'max_tokens': max_tokens,
            'temperature': temperature,
        })
        if not self.responses:
            return 'La respuesta'
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeWeb:
    def __init__(self, results=None):
        self.results = dict(results or {})
        self.calls = []
        self.keyword_calls = []

    def lookup(self, query, keywords):
        self.calls.append(query)
        self.keyword_calls.append(list(keywords))
        return list(self.results.get(query, []))


def _data(question, ctx=None):
    message = {'v': 1, 'lang': 'esES', 'q': question, 'ctx': ctx or {}}
    return json.dumps(message, ensure_ascii=False).encode('utf-8')


def test_needs_web_cases():
    assert needs_web(Facts(sources=['panorama:zones:16']), '¿Qué hago ahora?') is True
    assert needs_web(Facts(lines=['Zonas...'], sources=['panorama:zones:16']),
                     '¿Qué hago ahora?') is True
    assert needs_web(Facts(lines=['Misión...'], sources=['quest:1']),
                     '¿Dónde entrego X?') is False
    assert needs_web(Facts(missing=['experiencia necesaria por nivel']),
                     '¿Cuánta experiencia necesito?') is True
    assert needs_web(Facts(missing=['ruta completa entre A y B']),
                     '¿Cómo voy de A a B?') is False
    assert needs_web(Facts(), '¿Cómo voy a Ventormenta?') is False
    assert needs_web(Facts(), '¿Y pescar?') is False
    assert needs_web(Facts(), '¿Y pescar?', history=[object()]) is True


def test_answer_message_uses_web_excerpts():
    provider = FakeProvider([SEARCH_JSON, 'La respuesta final'])
    web = FakeWeb({
        'Expert Fishing': [EXPERT, TRAINER],
        'Fishing trainer': [FOREVER, EXPERT],
    })
    data = _data('¿Y a pescar dónde puedo ir?', ctx={
        'class': 'Chamán', 'race': 'Enano', 'fac': 'Alianza', 'lvl': 16,
    })

    result = answer_message(data, provider, web=web,
                            previous_question='¿Dónde compro la caña?')

    assert len(provider.calls) == 2
    search_call, answer_call = provider.calls
    assert 'JSON' in search_call['system']
    assert search_call['max_tokens'] == 150
    assert search_call['temperature'] == 0.0
    assert 'Question: ¿Y a pescar dónde puedo ir?' in search_call['user']
    assert 'Previous question: ¿Dónde compro la caña?' in search_call['user']
    assert 'Class: Chamán' in search_call['user']
    assert 'Race: Enano' in search_call['user']
    assert 'Faction: Alianza' in search_call['user']
    assert 'Level: 16' in search_call['user']

    assert web.calls == ['Expert Fishing', 'Fishing trainer']
    assert web.keyword_calls == [['fishing', 'skill'], ['fishing', 'skill']]
    assert result.web_titles == ['Forever fishing techniques', 'Expert Fishing',
                                 'Fishing trainer']
    assert 'FUENTE EXTERNA' in answer_call['user']
    assert '[Forever fishing techniques] ' + FOREVER.url in answer_call['user']
    assert 'Texto de Forever.' in answer_call['user']
    assert 'wiki:Forever fishing techniques' in result.sources
    assert result.ok is True


def test_answer_message_invalid_search_json_uses_question():
    provider = FakeProvider(['esto no es JSON', 'La respuesta'])
    web = FakeWeb({'¿Y a pescar dónde puedo ir?': [FOREVER]})

    result = answer_message(_data('¿Y a pescar dónde puedo ir?'), provider, web=web)

    assert web.calls == ['¿Y a pescar dónde puedo ir?']
    assert web.keyword_calls == [[]]
    assert 'FUENTE EXTERNA' in provider.calls[1]['user']
    assert result.web_titles == ['Forever fishing techniques']


def test_answer_message_empty_web_has_no_block():
    provider = FakeProvider([SEARCH_JSON, 'La respuesta'])
    web = FakeWeb({})

    result = answer_message(_data('¿Y a pescar dónde puedo ir?'), provider, web=web)

    assert len(provider.calls) == 2
    assert 'FUENTE EXTERNA' not in provider.calls[1]['user']
    assert result.web_titles == []
    assert not any(source.startswith('wiki:') for source in result.sources)


def test_search_provider_failure_leaves_no_web():
    provider = FakeProvider([ProviderError('timeout', 'x'), 'La respuesta'])
    web = FakeWeb({'Expert Fishing': [FOREVER]})

    result = answer_message(_data('¿Y a pescar dónde puedo ir?'), provider, web=web)

    assert len(provider.calls) == 2
    assert web.calls == []
    assert 'FUENTE EXTERNA' not in provider.calls[1]['user']
    assert result.web_titles == []
    assert result.ok is True


def test_entity_facts_skip_web(monkeypatch):
    provider = FakeProvider(['La respuesta'])
    web = FakeWeb()
    facts = Facts(lines=['Misión «X»: la da alguien.'], sources=['quest:1'])
    monkeypatch.setattr(answer, 'retrieve', lambda message, db: facts)

    result = answer_message(_data('¿Dónde entrego X?'), provider, db=object(), web=web)

    assert len(provider.calls) == 1
    assert web.calls == []
    assert result.web_titles == []


def test_route_question_skips_web(monkeypatch):
    provider = FakeProvider(['La respuesta'])
    web = FakeWeb()
    facts = Facts(missing=['ruta completa entre Forjaz y Auberdine'])
    monkeypatch.setattr(answer, 'retrieve', lambda message, db: facts)

    result = answer_message(_data('¿Cómo voy de Forjaz a Auberdine?'), provider,
                            db=object(), web=web)

    assert len(provider.calls) == 1
    assert web.calls == []
    assert result.web_titles == []


def test_web_none_keeps_previous_behaviour():
    provider = FakeProvider(['La respuesta'])

    result = answer_message(_data('¿Y a pescar dónde puedo ir?'), provider, web=None)

    assert len(provider.calls) == 1
    assert 'FUENTE EXTERNA' not in provider.calls[0]['user']
    assert result.web_titles == []
    assert result.sources == []


def test_build_prompt_with_web_excerpts():
    system, user = build_prompt({'lang': 'esES', 'q': '¿Dónde pesco?'},
                                'DATOS VERIFICADOS:\nX', web_excerpts=[FOREVER])

    assert 'FUENTE EXTERNA (warcraft.wiki.gg;' in user
    assert '[Forever fishing techniques] ' + FOREVER.url in user
    assert 'Texto de Forever.' in user
    assert user.index('DATOS VERIFICADOS') < user.index('FUENTE EXTERNA')
    assert user.index('FUENTE EXTERNA') < user.index('Pregunta:')
    assert 'según la wiki' in system
    assert 'mandan los datos verificados' in system
    assert 'Con fuente externa' in system

    system_en, user_en = build_prompt({'lang': 'enUS', 'q': 'Where do I fish?'},
                                      web_excerpts=[FOREVER])
    assert 'EXTERNAL SOURCE (warcraft.wiki.gg;' in user_en
    assert 'according to the wiki' in system_en
    assert 'the verified data wins' in system_en


def test_get_web_enabled(monkeypatch):
    monkeypatch.delenv(config.WEB_ENV, raising=False)
    assert config.get_web_enabled() is True

    for value in ('0', 'false', 'no', 'off', 'FALSE'):
        monkeypatch.setenv(config.WEB_ENV, value)
        assert config.get_web_enabled() is False

    monkeypatch.setenv(config.WEB_ENV, '1')
    assert config.get_web_enabled() is True
    monkeypatch.setenv(config.WEB_ENV, '0')
    assert config.open_wiki() is None


def test_cli_ask_no_web_does_not_open_wiki(monkeypatch, capsys):
    provider = FakeProvider(['La respuesta'])
    monkeypatch.setattr(cli, 'provider_from_config', lambda: provider)

    def forbidden():
        raise AssertionError('no debe abrir la wiki')

    monkeypatch.setattr(cli.config, 'open_wiki', forbidden)

    assert cli.main(['ask', 'hola', '--no-data', '--no-web']) == 0
    output = capsys.readouterr().out
    assert 'Búsqueda web: desactivada' in output
    assert len(provider.calls) == 1


def test_cli_ask_uses_web_and_shows_titles(monkeypatch, capsys):
    provider = FakeProvider([SEARCH_JSON, 'La respuesta'])
    web = FakeWeb({'Expert Fishing': [FOREVER]})
    monkeypatch.setattr(cli, 'provider_from_config', lambda: provider)
    monkeypatch.setattr(cli.config, 'open_wiki', lambda: web)

    assert cli.main(['ask', '¿Y a pescar dónde puedo ir?', '--no-data',
                     '--show-data']) == 0
    output = capsys.readouterr().out
    assert 'Búsqueda web: warcraft.wiki.gg' in output
    assert 'Fuente web:' in output
    assert 'Forever fishing techniques' in output
    assert FOREVER.url in output
    assert web.calls == ['Expert Fishing', 'Fishing trainer']


def test_bench_web_titles_and_markdown():
    question = Question('q1', 'pesca', 'esES', '¿Y a pescar dónde puedo ir?', {}, 'n')
    provider = FakeProvider([SEARCH_JSON, 'La respuesta'])
    web = FakeWeb({'Expert Fishing': [FOREVER]})
    target = Target('fake', 'modelo')

    results = run_bench(
        [question], [target],
        provider_factory=lambda **_: provider,
        web=web,
        sleep=lambda seconds: None,
    )

    assert len(results) == 1
    assert results[0].web_titles == ['Forever fishing techniques']
    assert 'wiki:Forever fishing techniques' in results[0].sources

    markdown = render_markdown([question], [target], results, '2026-11-14 07:00:00')
    assert 'Fuente web: Forever fishing techniques' in markdown
