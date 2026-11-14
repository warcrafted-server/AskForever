"""Pruebas del glosario de nombres oficiales para los extractos de la wiki."""

from __future__ import annotations

import json
import sqlite3

import pytest

from askforever.data.glossary import spanish_names
from askforever.data.wowdb import WowDb
from askforever.engine.answer import answer_message
from askforever.engine.prompt import build_prompt
from askforever.web.wiki import WIKI_PAGE_URL, WikiExcerpt

SCHEMA = [
    'CREATE TABLE SpellName (ID INTEGER, Name_lang TEXT, Name_lang_esES TEXT)',
    'CREATE TABLE GameObjects (ID INTEGER, Name_lang TEXT, Name_lang_esES TEXT)',
]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'wow.sqlite'
    conn = sqlite3.connect(path)
    for statement in SCHEMA:
        conn.execute(statement)
    conn.executemany('INSERT INTO SpellName VALUES (?, ?, ?)', [
        (1, 'Well Fed', 'Bien alimentado'),
        (2, 'Unknown Thing', ''),
        (3, 'Same Name', 'Same Name'),
    ])
    conn.executemany('INSERT INTO GameObjects VALUES (?, ?, ?)', [
        (1, "Brann's Cozy Campfire", 'Fogata acogedora de Brann'),
        (2, 'Elwynn Forest', 'Bosque de Elwynn'),
        (3, 'No Translation', ''),
    ])
    conn.commit()
    conn.close()

    database = WowDb(path)
    yield database
    database.close()


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, system, user, *, max_tokens=None, temperature=0.3):
        self.calls.append({'system': system, 'user': user})
        return self.responses.pop(0)


class FakeWeb:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def lookup(self, query, keywords):
        self.calls.append(query)
        return list(self.results.get(query, []))


def _excerpt():
    return WikiExcerpt('Well Fed', WIKI_PAGE_URL + 'Well_Fed',
                       'Well Fed is a buff from food.')


def test_spanish_names_finds_well_fed(db):
    assert spanish_names(db, ['Well Fed']) == [('Well Fed', 'Bien alimentado')]


def test_spanish_names_skips_empty_or_same_translation(db):
    assert spanish_names(db, ['Unknown Thing']) == []
    assert spanish_names(db, ['Same Name']) == []


def test_spanish_names_missing_tables_do_not_break(db):
    result = spanish_names(db, ['Well Fed', 'Elwynn Forest'])

    assert ('Well Fed', 'Bien alimentado') in result
    assert ('Elwynn Forest', 'Bosque de Elwynn') in result


def test_spanish_names_no_duplicates_and_limit(db):
    limited = spanish_names(db, ['Well Fed. Well Fed. Elwynn Forest.'], limit=1)
    assert limited == [('Well Fed', 'Bien alimentado')]

    full = spanish_names(db, ['Well Fed. Well Fed. Elwynn Forest.'])
    assert len(full) == len(set(full))
    assert ('Elwynn Forest', 'Bosque de Elwynn') in full


def test_spanish_names_longest_first(db):
    result = spanish_names(db, ["Brann's Cozy Campfire and Well Fed"], limit=2)

    assert result[0] == ("Brann's Cozy Campfire", 'Fogata acogedora de Brann')
    assert ('Well Fed', 'Bien alimentado') in result


def test_spanish_names_short_single_words_are_not_queried():
    class FakeDb:
        def __init__(self):
            self.queries = []

        def _rows(self, sql, params):
            self.queries.append(params[0])
            return []

    fake = FakeDb()
    spanish_names(fake, ['Fed the cat'])

    assert 'Fed' not in fake.queries


def test_build_prompt_with_glossary():
    system, user = build_prompt(
        {'lang': 'esES', 'q': '¿qué debo buscar para las acampadas?'},
        web_excerpts=[_excerpt()],
        glossary=[('Well Fed', 'Bien alimentado')],
    )

    assert 'Nombres oficiales en español (úsalos en la respuesta):' in user
    assert 'Well Fed = Bien alimentado' in user
    assert 'Los extractos de la wiki están en inglés' in system
    assert 'usa los nombres oficiales en español' in system
    assert user.index('Well Fed = Bien alimentado') < user.index('FUENTE EXTERNA')


def test_build_prompt_without_glossary_keeps_current_output():
    system, user = build_prompt({'lang': 'esES', 'q': '¿Hola?'})

    assert 'Nombres oficiales en español' not in user
    assert 'Los extractos de la wiki están en inglés' not in system


def test_answer_message_passes_glossary_to_provider(db):
    provider = FakeProvider(['Well Fed', 'La respuesta'])
    web = FakeWeb({'Well Fed': [_excerpt()]})
    data = json.dumps({
        'v': 1,
        'lang': 'esES',
        'q': '¿qué debo buscar para las acampadas que dan mejoras?',
        'ctx': {'lvl': 10},
    }, ensure_ascii=False).encode('utf-8')

    result = answer_message(data, provider, db=db, web=web)

    assert result.ok
    assert len(provider.calls) == 2
    assert 'Nombres oficiales en español' in provider.calls[1]['user']
    assert 'Well Fed = Bien alimentado' in provider.calls[1]['user']
    assert 'Los extractos de la wiki están en inglés' in provider.calls[1]['system']
