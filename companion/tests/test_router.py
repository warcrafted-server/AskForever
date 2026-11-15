"""Pruebas del enrutador de secciones de la guía."""

from __future__ import annotations

import json
import os
import sqlite3
import time

import pytest

from askforever import cli
from askforever.engine import guide as guide_module
from askforever.engine import router
from askforever.engine.answer import answer_message
from askforever.bench import Question, Target, run_bench
from askforever.providers.openai_compat import ProviderError


class GuideDb:
    """Base mínima para el índice: sin tablas de juego, solo las de textos."""

    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('CREATE TABLE gametips (ID INTEGER, Text_lang TEXT, '
                          'Text_lang_esES TEXT)')
        self.conn.execute('CREATE TABLE GlobalStrings (ID INTEGER, BaseTag TEXT, '
                          'TagText_lang TEXT, TagText_lang_esES TEXT, Flags INTEGER)')

    def _rows(self, sql, params=()):
        try:
            return self.conn.execute(sql, params).fetchall()
        except sqlite3.Error:
            return []

    def close(self):
        self.conn.close()

    def available(self):
        return True

    def match_entities(self, *_args, **_kwargs):
        return []

    def zones_for_level(self, *_args, **_kwargs):
        return []

    def find_quest(self, *_args, **_kwargs):
        return None

    def xp_to_next_level(self, *_args, **_kwargs):
        return None

    def dungeons_for_level(self, *_args, **_kwargs):
        return []

    def zone_continent(self, *_args, **_kwargs):
        return None

    def flight_points(self, *_args, **_kwargs):
        return []


class FakeProvider:
    def __init__(self, responses=None, errors=None, delay=0):
        self.responses = list(responses or [])
        self.errors = list(errors or [])
        self.delay = delay
        self.calls = []

    def chat(self, system, user, *, max_tokens=None, temperature=None):
        self.calls.append((system, user, max_tokens, temperature))
        if self.delay:
            time.sleep(self.delay)
        if self.errors:
            raise self.errors.pop(0)
        if self.responses:
            return self.responses.pop(0)
        return 'respuesta'


def _section(identifier, tags=None, chapter=4, text_es='Texto.', text_en='Text.'):
    return {
        'id': identifier,
        'chapter': chapter,
        'status': 'editorial',
        'title_es': f'Título {identifier}',
        'title_en': f'Title {identifier}',
        'summary_es': f'Resumen {identifier}.',
        'summary_en': f'Summary {identifier}.',
        'keywords_es': [identifier],
        'keywords_en': [identifier],
        'tags': tags or [],
        'text_es': text_es,
        'text_en': text_en,
        'sources': [{'type': 'prueba', 'ref': 'prueba'}],
        'updated': '2026-11-15',
    }


def _write_sections(path, sections):
    path.write_text(json.dumps({'sections': sections}, ensure_ascii=False),
                    encoding='utf-8')


def _message(question='¿Qué puede hacer mi mascota?', lang='esES',
             ctx=None):
    return json.dumps({
        'v': 1, 'lang': lang, 'q': question,
        'ctx': dict(ctx or {'lvl': 16, 'race': 'Humano', 'class': 'Cazador'}),
    }, ensure_ascii=False).encode('utf-8')


@pytest.fixture
def sections(tmp_path, monkeypatch):
    path = tmp_path / 'guide.json'
    _write_sections(path, [
        _section('general', chapter=2),
        _section('hunter', ['HUNTER'], chapter=4),
        _section('mage', ['MAGE'], chapter=4),
        _section('night', ['NIGHTELF'], chapter=4),
        _section('sky', ['SKYBORNE'], chapter=4),
    ])
    monkeypatch.setattr(guide_module, 'GUIDE_SECTIONS_PATH', path)
    monkeypatch.setattr(guide_module, 'GUIDE_SECTIONS_DIR', tmp_path / 'empty')
    guide_module._CACHE.clear()
    guide_module._TOC_CACHE.clear()
    yield path
    guide_module._CACHE.clear()
    guide_module._TOC_CACHE.clear()


def test_build_toc_filters_other_classes_and_races(sections):
    toc = guide_module.build_toc('es', {'class': 'Cazador', 'race': 'Humano'})
    ids = [identifier for identifier, _line in toc]
    assert ids == ['general', 'hunter']
    assert 'Título hunter' in dict(toc)['hunter']

    named = guide_module.build_toc('es', {}, '¿Qué hace un mago?')
    assert [identifier for identifier, _line in named] == ['general', 'mage']
    named = guide_module.build_toc('es', {}, '¿Qué hace un cazador?')
    assert [identifier for identifier, _line in named] == ['general', 'hunter']


def test_route_parses_json_drops_unknown_and_caps(monkeypatch):
    monkeypatch.setattr(router, 'build_toc', lambda *_args, **_kwargs: [
        ('a', 'a | A | A'), ('b', 'b | B | B'), ('c', 'c | C | C')])
    provider = FakeProvider(['texto {"ids": ["a", "nope", "b", "c"]} final'])
    assert router.route(provider, 'pregunta', 'es', {}, timeout=1) == ['a', 'b', 'c']
    assert provider.calls[0][2] == 60
    assert provider.calls[0][3] == 0


def test_route_empty_and_failures(monkeypatch):
    monkeypatch.setattr(router, 'build_toc', lambda *_args, **_kwargs: [
        ('a', 'a | A | A')])
    assert router.route(FakeProvider(['{"ids": []}']), 'p', 'es', {}) == []
    assert router.route(FakeProvider(['no json']), 'p', 'es', {}) is None
    assert router.route(FakeProvider(['{"ids": 4}']), 'p', 'es', {}) is None
    assert router.route(FakeProvider(errors=[ProviderError('rate_limit', 'x')]),
                        'p', 'es', {}) is None
    assert router.route(FakeProvider(['{"ids": ["a"]}'], delay=0.2),
                        'p', 'es', {}, timeout=0.01) is None


def test_answer_router_on_adds_section_first_and_keeps_answer(sections):
    db = GuideDb()
    keyword = _section('mascota', ['HUNTER'], text_es='Las mascotas comen.',
                       text_en='Pets eat.')
    keyword['keywords_es'] = ['mascota']
    keyword['keywords_en'] = ['pet']
    routed = _section('routed', ['HUNTER'], text_es='Sección elegida.',
                      text_en='Chosen section.')
    _write_sections(sections, [
        _section('general', chapter=2), keyword, routed,
    ])
    guide_module._CACHE.clear()
    guide_module._TOC_CACHE.clear()
    provider = FakeProvider(['{"ids": ["routed"]}', 'La respuesta'])
    result = answer_message(_message(), provider, db=db)
    assert result.ok is True
    assert result.router == 'ok:routed'
    assert 'Sección elegida.' in result.facts_text
    assert 'Las mascotas comen.' in result.facts_text
    guide_lines = [line for line in result.facts
                   if line.startswith(('En WoW Forever:', 'Guía verificada'))]
    assert guide_lines[0].endswith('Sección elegida.')
    assert any('Las mascotas comen.' in line for line in guide_lines)
    assert len(provider.calls) == 2


def test_answer_router_off_makes_one_call(sections, monkeypatch):
    monkeypatch.setenv('ASKFOREVER_GUIDE_ROUTER', '0')
    db = GuideDb()
    keyword = _section('mascota', ['HUNTER'], text_es='Las mascotas comen.',
                       text_en='Pets eat.')
    keyword['keywords_es'] = ['mascota']
    keyword['keywords_en'] = ['pet']
    _write_sections(sections, [keyword])
    guide_module._CACHE.clear()
    guide_module._TOC_CACHE.clear()
    provider = FakeProvider(['La respuesta'])
    result = answer_message(_message(), provider, db=db)
    assert result.router == 'off'
    assert len(provider.calls) == 1
    assert any('Las mascotas comen.' in line for line in result.facts)


def test_answer_router_failure_keeps_keyword_lines(sections):
    db = GuideDb()
    keyword = _section('mascota', ['HUNTER'], text_es='Las mascotas comen.',
                       text_en='Pets eat.')
    keyword['keywords_es'] = ['mascota']
    keyword['keywords_en'] = ['pet']
    _write_sections(sections, [keyword])
    guide_module._CACHE.clear()
    guide_module._TOC_CACHE.clear()
    provider = FakeProvider(errors=[ProviderError('rate_limit', 'x')],
                            responses=['La respuesta'])
    result = answer_message(_message(), provider, db=db)
    assert result.ok is True
    assert result.router == 'fallback'
    assert any('Las mascotas comen.' in line for line in result.facts)
    assert len(provider.calls) == 2


def test_answer_router_skips_travel_questions(sections, monkeypatch):
    monkeypatch.setenv('ASKFOREVER_GUIDE_ROUTER', '1')
    # La base falsa no tiene zonas: se simula que «Ventormenta» es un lugar conocido.
    from askforever.engine import retriever as retriever_module
    monkeypatch.setattr(retriever_module, '_zone_in_question',
                        lambda _db, text, _lang: ((1519, 'Ciudad de Ventormenta')
                                                  if 'ventormenta' in text else (None, '')))
    db = GuideDb()
    provider = FakeProvider(['La respuesta'])
    result = answer_message(_message('¿Cómo voy a Ventormenta?'), provider, db=db)
    assert result.router == 'off'
    assert len(provider.calls) == 1


def test_bench_records_router_outcome(sections):
    db = GuideDb()
    keyword = _section('mascota', ['HUNTER'], text_es='Las mascotas comen.',
                       text_en='Pets eat.')
    keyword['keywords_es'] = ['mascota']
    keyword['keywords_en'] = ['pet']
    routed = _section('routed', ['HUNTER'], text_es='Sección elegida.',
                      text_en='Chosen section.')
    _write_sections(sections, [keyword, routed])
    guide_module._CACHE.clear()
    guide_module._TOC_CACHE.clear()
    fake_provider = FakeProvider(['{"ids": ["routed"]}', 'La respuesta'])
    question = Question('q1', 'general', 'esES', '¿Qué come mi mascota?',
                        {'lvl': 16, 'race': 'Humano', 'class': 'Cazador'}, 'Notas')
    results = run_bench(
        [question], [Target('fake', 'modelo')],
        provider_factory=lambda provider=None, model=None: fake_provider,
        db=db, sleep=lambda seconds: None,
    )
    assert len(results) == 1
    assert results[0].ok is True
    assert results[0].router == 'ok:routed'
    assert 'guide:section:routed' in results[0].sources
    assert 'guide:section:mascota' in results[0].sources


def test_bench_no_router_skips_route_and_restores_env(sections, monkeypatch, tmp_path):
    db = GuideDb()
    keyword = _section('mascota', ['HUNTER'], text_es='Las mascotas comen.',
                       text_en='Pets eat.')
    keyword['keywords_es'] = ['mascota']
    keyword['keywords_en'] = ['pet']
    routed = _section('routed', ['HUNTER'], text_es='Sección elegida.',
                      text_en='Chosen section.')
    _write_sections(sections, [keyword, routed])
    guide_module._CACHE.clear()
    guide_module._TOC_CACHE.clear()
    fake_provider = FakeProvider(['La respuesta'])
    questions = [Question('q1', 'general', 'esES', '¿Qué come mi mascota?',
                          {'lvl': 16, 'race': 'Humano', 'class': 'Cazador'}, 'Notas')]
    monkeypatch.setenv('ASKFOREVER_GUIDE_ROUTER', '1')
    monkeypatch.setattr(cli, '_open_data', lambda no_data: db)
    monkeypatch.setattr(cli, 'load_questions', lambda path=None: questions)
    monkeypatch.setattr(cli, 'provider_from_config',
                        lambda provider=None, model=None: fake_provider)
    monkeypatch.setattr(cli, 'save_report',
                        lambda *args, **kwargs: (tmp_path / 'b.md', tmp_path / 'b.json'))

    assert cli.main(['bench', '--targets', 'fake:modelo', '--pause', '0',
                     '--no-web', '--no-router']) == 0
    assert len(fake_provider.calls) == 1
    assert os.environ['ASKFOREVER_GUIDE_ROUTER'] == '1'


def test_travel_shaped_question_without_place_uses_router(sections, monkeypatch):
    monkeypatch.setenv('ASKFOREVER_GUIDE_ROUTER', '1')
    db = GuideDb()
    provider = FakeProvider(['{"ids": []}', 'La respuesta'])
    result = answer_message(_message('¿Cuándo podré ir a caballo?'), provider, db=db)
    assert result.router == 'empty'
    assert len(provider.calls) == 2


def test_routed_section_already_found_moves_to_the_front(monkeypatch):
    from askforever.engine import guide as guide_mod
    from askforever.engine.retriever import Facts, add_guide_sections

    def fake_sections(_path=None):
        return [{'id': name, 'status': 'editorial', 'text_es': f'Texto {name}.',
                 'text_en': f'Text {name}.'} for name in ('a', 'b', 'c', 'd', 'e')]

    monkeypatch.setattr(guide_mod, 'load_sections', fake_sections)
    facts = Facts(lines=['Dato de la base.'] + [f'En WoW Forever: Texto {name}.'
                                                  for name in ('b', 'c', 'd', 'a')])

    class Db:
        pass

    add_guide_sections(facts, Db(), ['a', 'e'], 'es')
    guide_lines = [line for line in facts.lines if line.startswith('En WoW Forever')]
    assert guide_lines[:2] == ['En WoW Forever: Texto a.', 'En WoW Forever: Texto e.']
    assert len(guide_lines) == 4
