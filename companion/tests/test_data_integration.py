"""Pruebas de la integración de la base de datos en prompt, respuestas y CLI."""

from __future__ import annotations

import json
import sqlite3

import pytest

import askforever.cli as cli
from askforever import config
from askforever.data.wowdb import WowDb
from askforever.engine.answer import answer_message
from askforever.engine.prompt import build_prompt
from askforever.bench import Question, Target, render_markdown, run_bench, save_report

SCHEMA = [
    'CREATE TABLE ext_quests (quest_id INTEGER, required_level INTEGER, quest_level INTEGER)',
    'CREATE TABLE ext_quest_l10n (quest_id INTEGER, locale TEXT, name TEXT)',
    'CREATE TABLE ext_quest_starters (quest_id INTEGER, entity_type TEXT, entity_id INTEGER)',
    'CREATE TABLE ext_quest_finishers (quest_id INTEGER, entity_type TEXT, entity_id INTEGER)',
    'CREATE TABLE ext_quest_objective_items (quest_id INTEGER, position INTEGER, '
    'item_id INTEGER, text TEXT, icon_type INTEGER)',
    'CREATE TABLE ext_npcs (npc_id INTEGER, min_level INTEGER, max_level INTEGER, '
    'friendly_to_faction TEXT)',
    'CREATE TABLE ext_npc_l10n (npc_id INTEGER, locale TEXT, name TEXT, sub_name TEXT)',
    'CREATE TABLE ext_npc_spawns (npc_id INTEGER, zone_id INTEGER, spawn_idx INTEGER, '
    'x REAL, y REAL)',
    'CREATE TABLE ext_zones (group_id INTEGER, area_id INTEGER, name_enUS TEXT, '
    'name_esES TEXT)',
    'CREATE TABLE ext_dungeons (area_id INTEGER, name_enUS TEXT, name_esES TEXT, '
    'parent_zone_id INTEGER)',
    'CREATE TABLE ext_item_l10n (item_id INTEGER, locale TEXT, name TEXT)',
]

CTX = {'lvl': 16, 'race': 'Enano', 'class': 'Chamán', 'fac': 'Alianza', 'zone': 'Forjaz'}


def _insert(conn, table, columns, rows):
    placeholders = ', '.join('?' for _ in columns)
    conn.executemany(f'INSERT INTO {table} ({", ".join(columns)}) VALUES ({placeholders})', rows)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / 'wow.sqlite'
    conn = sqlite3.connect(path)
    for statement in SCHEMA:
        conn.execute(statement)
    _insert(conn, 'ext_quests', ['quest_id', 'required_level', 'quest_level'], [
        (1338, 9, 14),
    ])
    _insert(conn, 'ext_quest_l10n', ['quest_id', 'locale', 'name'], [
        (1338, 'esES', 'Un pedido de Pico Tormenta'),
        (1338, 'enUS', 'A Request from Ironforge'),
    ])
    _insert(conn, 'ext_quest_starters', ['quest_id', 'entity_type', 'entity_id'], [
        (1338, 'npc', 1343),
    ])
    _insert(conn, 'ext_quest_finishers', ['quest_id', 'entity_type', 'entity_id'], [
        (1338, 'npc', 5413),
    ])
    _insert(conn, 'ext_npcs', ['npc_id', 'min_level', 'max_level', 'friendly_to_faction'], [
        (1343, 10, 10, 'A'),
        (5413, 30, 30, 'A'),
    ])
    _insert(conn, 'ext_npc_l10n', ['npc_id', 'locale', 'name', 'sub_name'], [
        (1343, 'esES', 'Montaraz Pico Tormenta', None),
        (5413, 'esES', 'Furen Barbalarga', None),
    ])
    _insert(conn, 'ext_npc_spawns', ['npc_id', 'zone_id', 'spawn_idx', 'x', 'y'], [
        (1343, 38, 1, 24.8, 18.4),
        (5413, 1519, 1, 64.6, 37.2),
    ])
    _insert(conn, 'ext_zones', ['group_id', 'area_id', 'name_enUS', 'name_esES'], [
        (0, 38, 'Loch Modan', 'Loch Modan'),
        (0, 1519, 'Stormwind City', 'Ciudad de Ventormenta'),
    ])
    conn.commit()
    conn.close()
    return path


def _message(question='¿Dónde entrego Un pedido de Pico Tormenta?', lang='esES'):
    return {'v': 1, 'lang': lang, 'q': question, 'ctx': dict(CTX)}


def _data(question='¿Dónde entrego Un pedido de Pico Tormenta?', lang='esES') -> bytes:
    return json.dumps(_message(question, lang), ensure_ascii=False).encode('utf-8')


class FakeProvider:
    def __init__(self, response='La respuesta'):
        self.response = response
        self.calls = []

    def chat(self, system, user, *, max_tokens=None, temperature=0.3):
        self.calls.append({
            'system': system,
            'user': user,
            'max_tokens': max_tokens,
            'temperature': temperature,
        })
        return self.response


def test_build_prompt_with_facts():
    facts = 'DATOS VERIFICADOS (base de WoW Forever):\nMisión «X»: la da Furen en Ventormenta.'
    system, user = build_prompt(_message(), facts)

    assert facts in user
    assert user.index(facts) < user.index('Pregunta:')
    assert 'SOLO' in system
    assert 'SIN DATOS EN LA BASE' in system


def test_build_prompt_without_facts_keeps_old_behaviour():
    system, user = build_prompt(_message())
    assert 'DATOS VERIFICADOS' not in user
    assert 'no inventes' in system.lower()
    assert '2 a 5' in system
    assert user.endswith('Pregunta: ¿Dónde entrego Un pedido de Pico Tormenta?')


def test_question_language_detection():
    system, _user = build_prompt(_message('Where is the entrance to the Deadmines?'))
    assert 'inglés' in system
    assert 'castellano' in build_prompt(_message('¿Dónde está Hogger?'))[0]
    assert 'Spanish' in build_prompt(_message('¿Dónde está Hogger?', lang='enUS'))[0]
    assert 'English' in build_prompt(_message('Where is Hogger?', lang='enUS'))[0]


def test_answer_message_with_database(db_path):
    database = WowDb(db_path)
    provider = FakeProvider()
    result = answer_message(_data(), provider, db=database)
    database.close()

    assert result.ok is True
    assert 'quest:1338' in result.sources
    assert any('Furen Barbalarga' in line for line in result.facts)
    call = provider.calls[0]
    assert 'Furen Barbalarga' in call['user']
    assert 'DATOS VERIFICADOS' in call['user']
    assert call['temperature'] == 0.2


def test_answer_message_without_database():
    provider = FakeProvider()
    result = answer_message(_data(), provider)
    assert result.sources == []
    assert result.facts == []
    assert 'DATOS VERIFICADOS' not in provider.calls[0]['user']


def test_temperature_default_and_environment(monkeypatch):
    provider = FakeProvider()
    monkeypatch.setenv('ASKFOREVER_TEMPERATURE', '1.1')
    answer_message(_data(), provider)
    assert provider.calls[-1]['temperature'] == 1.1

    monkeypatch.setenv('ASKFOREVER_TEMPERATURE', 'abc')
    answer_message(_data(), provider)
    assert provider.calls[-1]['temperature'] == 0.2

    monkeypatch.setenv('ASKFOREVER_TEMPERATURE', '9')
    assert config.get_temperature() == 2.0

    answer_message(_data(), provider, temperature=0.5)
    assert provider.calls[-1]['temperature'] == 0.5


def test_get_wowdata_path(tmp_path, monkeypatch):
    existing = tmp_path / 'otra.sqlite'
    existing.write_bytes(b'')
    monkeypatch.setenv('ASKFOREVER_WOWDATA', str(existing))
    assert config.get_wowdata_path() == existing

    monkeypatch.setenv('ASKFOREVER_WOWDATA', str(tmp_path / 'no.sqlite'))
    monkeypatch.setattr(config, '_sibling_wowdata_path', lambda: tmp_path / 'tampoco.sqlite')
    assert config.get_wowdata_path() is None

    monkeypatch.delenv('ASKFOREVER_WOWDATA', raising=False)
    monkeypatch.setattr(config, '_sibling_wowdata_path', lambda: existing)
    assert config.get_wowdata_path() == existing


def test_open_wowdata(db_path, monkeypatch):
    monkeypatch.setenv('ASKFOREVER_WOWDATA', str(db_path))
    database = config.open_wowdata()
    assert database is not None
    assert database.available() is True
    database.close()

    monkeypatch.setenv('ASKFOREVER_WOWDATA', str(db_path.parent / 'no.sqlite'))
    monkeypatch.setattr(config, '_sibling_wowdata_path', lambda: db_path.parent / 'no.sqlite')
    assert config.open_wowdata() is None


def test_run_bench_and_markdown_with_database(db_path, tmp_path):
    database = WowDb(db_path)
    fake_provider = FakeProvider(response='Con datos')
    question = Question('b03', 'misiones', 'esES',
                        '¿Dónde entrego Un pedido de Pico Tormenta?', dict(CTX), 'Notas')
    target = Target('fake', 'modelo')

    results = run_bench(
        [question],
        [target],
        provider_factory=lambda provider=None, model=None: fake_provider,
        db=database,
        temperature=0.4,
        sleep=lambda seconds: None,
    )
    database.close()

    assert len(results) == 1
    assert 'quest:1338' in results[0].sources
    assert results[0].ok is True
    call = fake_provider.calls[0]
    assert 'Furen Barbalarga' in call['user']
    assert call['temperature'] == 0.4

    markdown = render_markdown([question], [target], results, '2026-11-14 03:00:00',
                               used_database=True, temperature=0.4)
    assert 'Base de datos: usada' in markdown
    assert 'Temperatura: 0.4' in markdown
    assert 'Datos usados: quest:1338' in markdown

    md_path, json_path = save_report(markdown, results, out_dir=tmp_path,
                                     used_database=True, temperature=0.4)
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding='utf-8'))
    assert payload['used_database'] is True
    assert payload['temperature'] == 0.4
    assert 'quest:1338' in payload['results'][0]['sources']


def test_cli_ask_no_data(monkeypatch, capsys):
    def forbidden():
        raise AssertionError('no debe abrir la base con --no-data')

    monkeypatch.setattr(config, 'open_wowdata', forbidden)
    monkeypatch.setattr(cli, 'provider_from_config', lambda: FakeProvider())

    assert cli.main(['ask', 'hola', '--no-data', '--no-web']) == 0
    output = capsys.readouterr().out
    assert 'Base de datos: no disponible (sin datos verificados)' in output


def test_cli_ask_uses_database(db_path, monkeypatch, capsys):
    opened = []

    def open_database():
        opened.append(True)
        return WowDb(db_path)

    monkeypatch.setattr(config, 'open_wowdata', open_database)
    provider = FakeProvider()
    monkeypatch.setattr(cli, 'provider_from_config', lambda: provider)

    assert cli.main(['ask', '¿Dónde entrego Un pedido de Pico Tormenta?',
                     '--show-data', '--no-web']) == 0
    assert opened == [True]
    output = capsys.readouterr().out
    assert 'Base de datos: ' in output
    assert 'Furen Barbalarga' in output
    assert 'Furen Barbalarga' in provider.calls[0]['user']
