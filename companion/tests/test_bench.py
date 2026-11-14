"""Pruebas del comparador de modelos: cuestionario, ejecución, informes y CLI."""

from __future__ import annotations

import json

import pytest

import askforever.bench as bench
import askforever.cli as cli
from askforever.bench import (
    Question,
    Result,
    Target,
    build_message,
    load_questions,
    parse_target,
    render_markdown,
    run_bench,
    save_report,
    summarize,
)
from askforever.engine.prompt import build_prompt
from askforever.providers.openai_compat import ProviderError


class FakeProvider:
    def __init__(self, responses=None, errors=None):
        self.responses = list(responses or [])
        self.errors = list(errors or [])
        self.calls = []

    def chat(self, system, user, *, max_tokens=None, temperature=0.3):
        self.calls.append({'system': system, 'user': user, 'max_tokens': max_tokens})
        if self.errors:
            raise self.errors.pop(0)
        if self.responses:
            return self.responses.pop(0)
        return 'respuesta'


class FakeClock:
    def __init__(self, step=0.5):
        self.now = 0.0
        self.step = step

    def __call__(self):
        value = self.now
        self.now += self.step
        return value


def make_questions(count=2):
    return [
        Question(f'q{index:02d}', 'general', 'esES', f'Pregunta {index}',
                 {'lvl': 16, 'race': 'Enano'}, 'Notas')
        for index in range(1, count + 1)
    ]


def test_parse_target():
    assert parse_target('groq') == Target('groq', None)
    assert parse_target('groq:llama-3.3') == Target('groq', 'llama-3.3')
    assert parse_target(' openrouter : meta/llama:free ') == Target(
        'openrouter', 'meta/llama:free'
    )
    assert str(Target('groq', 'llama-3.3')) == 'groq:llama-3.3'
    assert str(Target('groq')) == 'groq'

    with pytest.raises(ValueError):
        parse_target('')
    with pytest.raises(ValueError):
        parse_target('   ')
    with pytest.raises(ValueError):
        parse_target(':modelo')


def test_load_questions_real_file():
    questions = load_questions()
    assert [question.id for question in questions] == [f'q{index:02d}'
                                                       for index in range(1, 11)]
    assert all(question.text and question.notes and question.category
               for question in questions)
    assert all(question.ctx['race'] == 'Enano' for question in questions)

    q07 = next(question for question in questions if question.id == 'q07')
    assert len(q07.ctx['quests']) == 8
    assert q07.ctx['lvl'] == 16

    q10 = next(question for question in questions if question.id == 'q10')
    assert q10.lang == 'enUS'


def test_load_questions_merges_and_replaces_quests(tmp_path):
    data = {
        'default_ctx': {'lvl': 10, 'race': 'Enano', 'quests': [['A', 1, 0]]},
        'questions': [
            {'id': 'x1', 'category': 'c', 'q': 'p', 'notes': 'n',
             'ctx': {'race': 'Humano', 'quests': [['B', 2, 0]]}},
        ],
    }
    path = tmp_path / 'questions.json'
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    question = load_questions(path)[0]
    assert question.ctx['lvl'] == 10
    assert question.ctx['race'] == 'Humano'
    assert question.ctx['quests'] == [['B', 2, 0]]


def test_load_questions_invalid(tmp_path):
    path = tmp_path / 'bad.json'
    path.write_text('{no json', encoding='utf-8')
    with pytest.raises(ValueError):
        load_questions(path)

    path.write_text(json.dumps({'questions': []}), encoding='utf-8')
    with pytest.raises(ValueError):
        load_questions(path)


def test_build_message_feeds_build_prompt():
    q07 = load_questions()[6]
    message = build_message(q07)

    assert message['v'] == 1
    assert message['lang'] == 'esES'
    assert message['q'] == q07.text
    assert message['ctx']['lvl'] == 16
    assert len(message['ctx']['quests']) == 8

    system, user = build_prompt(message)
    assert system
    assert user


def test_run_bench_measures_latency_and_pauses():
    questions = make_questions(2)
    fake = FakeProvider(responses=['uno', 'dos'])
    factory_calls = []

    def factory(provider=None, model=None):
        factory_calls.append((provider, model))
        return fake

    sleeps = []
    results = run_bench(
        questions,
        [Target('groq', 'llama')],
        provider_factory=factory,
        sleep=sleeps.append,
        clock=FakeClock(step=0.5),
    )

    assert len(results) == 2
    assert all(result.ok for result in results)
    assert [result.latency_ms for result in results] == [500, 500]
    assert sleeps == [1.5]
    assert factory_calls == [('groq', 'llama')]
    assert len(fake.calls) == 2
    assert fake.calls[0]['system']
    assert fake.calls[0]['user']


def test_run_bench_skips_target_without_key():
    questions = make_questions(2)
    fake = FakeProvider()

    def factory(provider=None, model=None):
        if provider == 'sin-clave':
            raise ProviderError('auth', 'no hay clave para sin-clave')
        return fake

    results = run_bench(
        questions,
        [Target('sin-clave'), Target('groq', 'm')],
        provider_factory=factory,
        sleep=lambda seconds: None,
    )

    skipped = [result for result in results if result.target == 'sin-clave']
    assert len(skipped) == 2
    assert all(result.skipped for result in skipped)
    assert all(result.error_detail == 'no hay clave para sin-clave' for result in skipped)
    assert len(fake.calls) == 2


def test_run_bench_continues_after_timeout():
    questions = make_questions(2)
    fake = FakeProvider(responses=['ok'], errors=[ProviderError('timeout', 'tarde')])

    results = run_bench(
        questions,
        [Target('groq', 'm')],
        provider_factory=lambda provider=None, model=None: fake,
        sleep=lambda seconds: None,
    )

    assert results[0].ok is False
    assert results[0].error_kind == 'timeout'
    assert results[1].ok is True


def test_run_bench_rate_limit_streak_skips_rest():
    questions = make_questions(5)
    limited = FakeProvider(errors=[ProviderError('rate_limit', 'cuota')] * 3)
    healthy = FakeProvider(responses=['bien'] * 5)

    def factory(provider=None, model=None):
        return limited if provider == 'limitado' else healthy

    results = run_bench(
        questions,
        [Target('limitado', 'm'), Target('sano', 'm')],
        provider_factory=factory,
        sleep=lambda seconds: None,
    )

    limited_results = [result for result in results if result.target == 'limitado:m']
    assert len(limited_results) == 5
    assert [result.error_kind for result in limited_results[:3]] == ['rate_limit'] * 3
    assert all(result.skipped for result in limited_results[3:])
    assert all(result.error_detail == bench.SKIP_RATE_LIMIT for result in limited_results[3:])
    assert len(limited.calls) == 3

    healthy_results = [result for result in results if result.target == 'sano:m']
    assert len(healthy_results) == 5
    assert all(result.ok for result in healthy_results)


def test_run_bench_generic_exception_is_unknown():
    questions = make_questions(1)
    fake = FakeProvider(errors=[RuntimeError('boom')])

    results = run_bench(
        questions,
        [Target('groq', 'm')],
        provider_factory=lambda provider=None, model=None: fake,
        sleep=lambda seconds: None,
    )

    assert results[0].ok is False
    assert results[0].error_kind == 'unknown'
    assert 'boom' in results[0].error_detail


def test_run_bench_repeat_and_progress():
    questions = make_questions(2)
    fake = FakeProvider()
    sleeps = []
    events = []

    def on_progress(index, total, target, question, result):
        events.append((index, total, str(target), question.id, result.ok))

    results = run_bench(
        questions,
        [Target('groq', 'm')],
        provider_factory=lambda provider=None, model=None: fake,
        repeat=2,
        sleep=sleeps.append,
        on_progress=on_progress,
    )

    assert len(results) == 4
    assert len(fake.calls) == 4
    assert sleeps == [1.5, 1.5, 1.5]
    assert [event[0] for event in events] == [1, 2, 3, 4]
    assert all(event[1] == 4 for event in events)


def test_summarize_mean_median_and_max():
    results = [
        Result('q1', 'a:m', True, 'x', 100),
        Result('q2', 'a:m', True, 'x', 300),
        Result('q3', 'a:m', True, 'x', 200),
        Result('q4', 'a:m', False, '', 50, error_kind='timeout'),
        Result('q5', 'a:m', False, '', 0, skipped=True, error_detail='x'),
        Result('q1', 'b:m', True, 'x', 100),
        Result('q2', 'b:m', True, 'x', 200),
        Result('q1', 'c:m', False, '', 0, skipped=True, error_detail='y'),
    ]

    summary = summarize(results)
    first = summary[0]
    assert first['target'] == 'a:m'
    assert (first['answered'], first['errors'], first['skipped']) == (3, 1, 1)
    assert first['mean_ms'] == 200
    assert first['median_ms'] == 200.0
    assert first['max_ms'] == 300

    second = summary[1]
    assert second['median_ms'] == 150.0

    third = summary[2]
    assert third['answered'] == 0
    assert third['mean_ms'] is None
    assert third['median_ms'] is None
    assert third['max_ms'] is None


def test_render_markdown_contains_sections():
    questions = make_questions(1)
    targets = [Target('groq', 'm')]
    results = [Result('q01', 'groq:m', True, 'La respuesta completa', 842)]

    markdown = render_markdown(questions, targets, results, '2026-11-14 02:30:00')

    assert '| Objetivo |' in markdown
    assert 'La respuesta completa' in markdown
    assert markdown.count('Puntuación (1-5): ___') == 1
    assert 'Qué comprobar' in markdown
    assert 'Notas' in markdown
    assert 'Conclusión' in markdown
    assert '2026-11-14 02:30:00' in markdown
    assert 'sk-test-SECRETO' not in markdown


def test_render_markdown_shows_errors_and_skips():
    questions = make_questions(2)
    targets = [Target('groq', 'm')]
    results = [
        Result('q01', 'groq:m', False, '', 10, error_kind='rate_limit', error_detail='cuota'),
        Result('q02', 'groq:m', False, '', 0, skipped=True, error_detail='sin clave'),
    ]

    markdown = render_markdown(questions, targets, results, '2026-11-14 02:30:00')

    assert 'ERROR rate_limit' in markdown
    assert 'cuota' in markdown
    assert 'SALTADA: sin clave' in markdown


def test_save_report(tmp_path):
    results = [Result('q01', 'groq:m', True, 'ok', 100)]
    markdown = '# informe\n'

    md_path, json_path = save_report(markdown, results, out_dir=tmp_path)

    assert md_path.exists()
    assert json_path.exists()
    assert md_path.read_text(encoding='utf-8') == markdown
    assert md_path.name.startswith('bench_')
    assert md_path.suffix == '.md'
    assert json_path.suffix == '.json'

    payload = json.loads(json_path.read_text(encoding='utf-8'))
    assert payload['results'][0]['question_id'] == 'q01'
    assert payload['summary'][0]['answered'] == 1


def test_bench_command_success(monkeypatch, capsys, tmp_path):
    questions = make_questions(2)
    fake = FakeProvider(responses=['uno', 'dos'])

    monkeypatch.setattr(cli, 'load_questions', lambda path=None: questions)
    monkeypatch.setattr(cli, 'provider_from_config',
                        lambda provider=None, model=None: fake)

    saved = {}

    def fake_save(markdown, results):
        md_path = tmp_path / 'bench.md'
        json_path = tmp_path / 'bench.json'
        md_path.write_text(markdown, encoding='utf-8')
        json_path.write_text(json.dumps({'results': []}), encoding='utf-8')
        saved['paths'] = (md_path, json_path)
        return md_path, json_path

    monkeypatch.setattr(cli, 'save_report', fake_save)

    assert cli.main(['bench', '--targets', 'groq:modelo', '--pause', '0']) == 0
    output = capsys.readouterr().out
    assert 'groq:modelo q01 OK' in output
    assert 'Informe:' in output
    assert saved['paths'][0].exists()


def test_bench_command_without_targets(monkeypatch, capsys):
    monkeypatch.setattr(cli.config, 'get_api_key', lambda provider=None: None)
    assert cli.main(['bench']) == 2
    output = capsys.readouterr().out
    assert 'set-key --provider' in output
    assert 'providers' in output


def test_bench_command_invalid_targets(capsys):
    assert cli.main(['bench', '--targets', ':modelo']) == 2
    assert 'Objetivo inválido' in capsys.readouterr().out


def test_bench_command_only_filters(monkeypatch, capsys, tmp_path):
    questions = make_questions(3)
    fake = FakeProvider()

    monkeypatch.setattr(cli, 'load_questions', lambda path=None: questions)
    monkeypatch.setattr(cli, 'provider_from_config',
                        lambda provider=None, model=None: fake)
    monkeypatch.setattr(cli, 'save_report',
                        lambda markdown, results: (tmp_path / 'a.md', tmp_path / 'a.json'))

    assert cli.main(['bench', '--targets', 'groq:m', '--only', 'q01,q03',
                     '--pause', '0']) == 0
    assert len(fake.calls) == 2
    output = capsys.readouterr().out
    assert 'q01' in output
    assert 'q03' in output
    assert 'q02' not in output


def test_bench_command_returns_1_when_nothing_answered(monkeypatch, capsys, tmp_path):
    questions = make_questions(1)
    fake = FakeProvider(errors=[ProviderError('timeout', 'x')])

    monkeypatch.setattr(cli, 'load_questions', lambda path=None: questions)
    monkeypatch.setattr(cli, 'provider_from_config',
                        lambda provider=None, model=None: fake)
    monkeypatch.setattr(cli, 'save_report',
                        lambda markdown, results: (tmp_path / 'a.md', tmp_path / 'a.json'))

    assert cli.main(['bench', '--targets', 'groq:m', '--pause', '0']) == 1


def test_bench_command_default_targets(monkeypatch, capsys, tmp_path):
    keys = {'gemini': 'k1', 'groq': 'k2', 'mistral': 'k3'}
    monkeypatch.setattr(cli.config, 'get_api_key', lambda provider=None: keys.get(provider))

    questions = make_questions(1)
    created = []

    def factory(provider=None, model=None):
        created.append((provider, model))
        return FakeProvider()

    monkeypatch.setattr(cli, 'load_questions', lambda path=None: questions)
    monkeypatch.setattr(cli, 'provider_from_config', factory)
    monkeypatch.setattr(cli, 'save_report',
                        lambda markdown, results: (tmp_path / 'a.md', tmp_path / 'a.json'))

    assert cli.main(['bench', '--pause', '0']) == 0
    assert created == [('gemini', None), ('groq', None)]
    output = capsys.readouterr().out
    assert 'Aviso: mistral no tiene modelo por defecto' in output
