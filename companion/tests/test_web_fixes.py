"""Pruebas de las búsquedas en texto plano, no_info y preguntas de profesión."""

from __future__ import annotations

import json
import sqlite3

import pytest

import askforever.engine.answer as answer
from askforever.data.wowdb import WowDb
from askforever.engine.answer import answer_message, needs_web
from askforever.engine.prompt import build_prompt
from askforever.engine.retriever import Facts, is_profession_question, retrieve
from askforever.web.wiki import WIKI_PAGE_URL, WikiExcerpt

SEARCH_SYSTEM = (
    "You turn a World of Warcraft player's question into wiki searches. Output ONLY 1 to 3 "
    'search terms, one per line, 2 to 4 words each, in English, using in-game names as wiki '
    'page titles (for example: Expert Fishing, Fishing trainer, Expert First Aid, Darkshore). '
    'No explanations, no numbering, no quotes, no thinking.'
)
CTX = {'lvl': 16, 'race': 'Enano', 'class': 'Chamán', 'fac': 'Alianza', 'zone': 'Forjaz'}

SCHEMA = [
    'CREATE TABLE ext_quests (quest_id INTEGER)',
    'CREATE TABLE ext_npcs (npc_id INTEGER, min_level INTEGER, max_level INTEGER, '
    'friendly_to_faction TEXT)',
    'CREATE TABLE ext_npc_l10n (npc_id INTEGER, locale TEXT, name TEXT, sub_name TEXT)',
    'CREATE TABLE ext_npc_spawns (npc_id INTEGER, zone_id INTEGER, spawn_idx INTEGER, '
    'x REAL, y REAL)',
    'CREATE TABLE ext_zones (group_id INTEGER, area_id INTEGER, name_enUS TEXT, '
    'name_esES TEXT)',
    'CREATE TABLE v_hechizos_instructor (ClassMask INTEGER, Name_enUS TEXT, '
    'Name_esES TEXT, Level INTEGER)',
]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'wow.sqlite'
    conn = sqlite3.connect(path)
    for statement in SCHEMA:
        conn.execute(statement)
    conn.execute('INSERT INTO ext_npcs (npc_id, min_level, max_level, friendly_to_faction) '
                 "VALUES (258098, 60, 60, 'A')")
    conn.execute('INSERT INTO ext_npc_l10n (npc_id, locale, name, sub_name) '
                 "VALUES (258098, 'esES', 'Eldrun Rompetormentas', 'Instructor de chamanes')")
    conn.execute('INSERT INTO ext_npc_spawns (npc_id, zone_id, spawn_idx, x, y) '
                 'VALUES (258098, 1537, 1, 47.1, 13.8)')
    conn.execute("INSERT INTO ext_zones (group_id, area_id, name_enUS, name_esES) "
                 "VALUES (0, 1537, 'Ironforge', 'Forjaz')")
    conn.execute('INSERT INTO v_hechizos_instructor (ClassMask, Name_enUS, Name_esES, Level) '
                 "VALUES (64, 'Lightning Shield', 'Escudo de relámpagos', 16)")
    conn.commit()
    conn.close()

    database = WowDb(path)
    yield database
    database.close()


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
        return self.responses.pop(0) if self.responses else 'La respuesta'


class FakeWeb:
    def __init__(self, results=None):
        self.results = dict(results or {})
        self.calls = []
        self.keyword_calls = []

    def lookup(self, query, keywords):
        self.calls.append(query)
        self.keyword_calls.append(list(keywords))
        return list(self.results.get(query, []))


def _message(question):
    return {'v': 1, 'lang': 'esES', 'q': question, 'ctx': dict(CTX)}


def _data(question, ctx=None):
    message = {'v': 1, 'lang': 'esES', 'q': question, 'ctx': ctx or dict(CTX)}
    return json.dumps(message, ensure_ascii=False).encode('utf-8')


def test_parse_search_terms_and_keywords():
    terms = answer._parse_search_terms('Expert First Aid\nFirst Aid trainer\nBronze Tube')

    assert terms == ['Expert First Aid', 'First Aid trainer', 'Bronze Tube']
    assert answer._search_keywords(terms) == [
        'Expert', 'First', 'trainer', 'Bronze', 'Tube']


def test_parse_search_terms_discards_thoughts_and_noise():
    text = ('<thought>User is asking about fishing.\nMaybe Expert Fishing.</thought>\n'
            '```json\nHere are the searches:\n- "Expert First Aid"\n1. First Aid trainer')
    assert answer._parse_search_terms(text) == ['Expert First Aid', 'First Aid trainer']
    assert answer._parse_search_terms('```json { "queries": [ <thought> User is asking...') == []


def test_generation_uses_plain_text_prompt():
    provider = FakeProvider(['Expert First Aid\nFirst Aid trainer\nBronze Tube', 'La respuesta'])
    web = FakeWeb()

    result = answer_message(_data('¿Y primeros auxilios a más de 150?'), provider, web=web,
                            previous_question='¿Dónde compro vendas?')

    search = provider.calls[0]
    assert search['system'] == SEARCH_SYSTEM
    assert search['max_tokens'] == 400
    assert search['temperature'] == 0.0
    assert 'Question: ¿Y primeros auxilios a más de 150?' in search['user']
    assert 'Previous question: ¿Dónde compro vendas?' in search['user']
    assert 'Player: level 16 Enano Chamán, Alianza.' in search['user']
    assert web.calls == ['Expert First Aid', 'First Aid trainer', 'Bronze Tube']
    assert web.keyword_calls[0] == ['Expert', 'First', 'trainer', 'Bronze', 'Tube']
    assert result.web_titles == []


def test_reasoning_only_does_not_search_in_spanish():
    provider = FakeProvider([
        '```json { "queries": [ <thought> User is asking about first aid...',
        'La respuesta',
    ])
    web = FakeWeb()

    result = answer_message(_data('¿Y primeros auxilios a más de 150?'), provider, web=web)

    assert web.calls == []
    assert web.keyword_calls == []
    assert result.web_titles == []
    assert 'No hay datos en la base de datos ni en la wiki' in provider.calls[1]['system']


def test_no_info_with_and_without_excerpts():
    question = '¿Y a pescar dónde puedo ir?'

    provider = FakeProvider(['Expert Fishing', 'La respuesta'])
    empty = FakeWeb()
    result = answer_message(_data(question), provider, web=empty)
    assert 'No hay datos en la base de datos ni en la wiki' in provider.calls[1]['system']
    assert 'FUENTE EXTERNA' not in provider.calls[1]['user']
    assert result.web_titles == []

    excerpt = WikiExcerpt('Forever fishing techniques',
                          WIKI_PAGE_URL + 'Forever_fishing_techniques', 'Texto de Forever.')
    provider = FakeProvider(['Expert Fishing', 'La respuesta'])
    full = FakeWeb({'Expert Fishing': [excerpt]})
    result = answer_message(_data(question), provider, web=full)
    assert 'No hay datos en la base de datos ni en la wiki' not in provider.calls[1]['system']
    assert 'FUENTE EXTERNA' in provider.calls[1]['user']
    assert result.web_titles == ['Forever fishing techniques']


def test_build_prompt_no_info():
    system, _user = build_prompt({'lang': 'esES', 'q': 'x'}, no_info=True)
    assert 'No hay datos en la base de datos ni en la wiki' in system
    assert 'NO menciones' in system

    system, _user = build_prompt({'lang': 'enUS', 'q': 'x'}, no_info=True)
    assert 'There is no data in the database or the wiki' in system
    assert 'do NOT mention' in system

    system, _user = build_prompt({'lang': 'esES', 'q': 'x'})
    assert 'No hay datos en la base de datos ni en la wiki' not in system


def test_is_profession_question():
    assert is_profession_question('¿Dónde se aprende pesca a más de 150?') is True
    assert is_profession_question('primeros auxilios') is True
    assert is_profession_question('skinning') is True
    assert is_profession_question('minería') is True
    assert is_profession_question('hechizos de nivel 18') is False


def test_needs_web_for_profession_questions():
    question = '¿Dónde se aprende pesca a más de 150?'

    spells = Facts(lines=['Hechizos de Chamán en el instructor a nivel 16: X.'],
                   sources=['spells:64:16'])
    assert needs_web(spells, question) is True

    fishing = Facts(lines=['Misión de pesca: la da alguien.'], sources=['quest:1'])
    assert needs_web(fishing, question) is False

    route_missing = Facts(missing=['ruta completa entre A y B'])
    assert needs_web(route_missing, question) is False

    route_question = Facts(lines=['Hechizos de Chamán en el instructor a nivel 16: X.'],
                           sources=['spells:64:16'])
    assert needs_web(route_question, '¿Cómo voy a pescar a Ventormenta?') is False


def test_profession_question_skips_spell_and_trainer_intents(db):
    control = retrieve(_message('¿Qué hechizos aprendo a nivel 16?'), db)
    assert any('Hechizos de' in line for line in control.lines)
    control = retrieve(_message('¿Dónde está el instructor de chamanes?'), db)
    assert any('Instructor de' in line for line in control.lines)

    question = '¿Dónde se aprende pesca a más de 150?'
    facts = retrieve(_message(question), db)
    assert not any('Hechizos de' in line for line in facts.lines)
    assert not any('Instructor de' in line for line in facts.lines)
    assert needs_web(facts, question) is False

    trainer_question = '¿Dónde está el instructor de pesca?'
    trainer_facts = retrieve(_message(trainer_question), db)
    assert not any('Instructor de' in line for line in trainer_facts.lines)
    assert not any('Hechizos de' in line for line in trainer_facts.lines)
