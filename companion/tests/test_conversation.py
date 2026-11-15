"""Pruebas de la memoria de conversación, el prompt y las cadenas del bench."""

from __future__ import annotations

import json
import sqlite3
import threading
import time

import pytest

import askforever.cli as cli
from askforever.bench import Target, load_questions, render_markdown, run_bench
from askforever.capture.grabber import ReceivedMessage
from askforever.data.wowdb import WowDb
from askforever.engine.answer import answer_message
from askforever.engine.conversation import ConversationStore, Turn
from askforever.engine.prompt import build_prompt

SCHEMA = [
    'CREATE TABLE ext_quests (quest_id INTEGER)',
    'CREATE TABLE ext_dungeons (area_id INTEGER, name_enUS TEXT, name_esES TEXT, '
    'parent_zone_id INTEGER)',
    'CREATE TABLE ext_dungeon_entrances (area_id INTEGER, idx INTEGER, zone_id INTEGER, '
    'x REAL, y REAL)',
    'CREATE TABLE ext_zones (group_id INTEGER, area_id INTEGER, name_enUS TEXT, '
    'name_esES TEXT)',
]

CTX = {'lvl': 16, 'race': 'Enano', 'class': 'Chamán', 'fac': 'Alianza', 'zone': 'Forjaz'}


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'wow.sqlite'
    conn = sqlite3.connect(path)
    for statement in SCHEMA:
        conn.execute(statement)
    conn.execute('INSERT INTO ext_dungeons (area_id, name_enUS, name_esES, parent_zone_id) '
                 "VALUES (718, 'Wailing Caverns', 'Cuevas de los Lamentos', 17)")
    conn.execute('INSERT INTO ext_dungeon_entrances (area_id, idx, zone_id, x, y) '
                 'VALUES (718, 1, 17, 46.0, 36.5)')
    conn.execute("INSERT INTO ext_zones (group_id, area_id, name_enUS, name_esES) "
                 "VALUES (1, 17, 'The Barrens', 'Los Baldíos')")
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
        self.calls.append({'system': system, 'user': user,
                           'max_tokens': max_tokens, 'temperature': temperature})
        return self.responses.pop(0) if self.responses else 'respuesta'


def _data(question: str, conv=None) -> bytes:
    message = {'v': 1, 'lang': 'esES', 'q': question, 'ctx': dict(CTX)}
    if conv is not None:
        message['conv'] = conv
    return json.dumps(message, ensure_ascii=False).encode('utf-8')


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_key_variants():
    store = ConversationStore()
    assert store.key({'conv': 7}) == '7'
    assert store.key({'conv': 'abc'}) == 'abc'
    assert store.key({'conv': '   '}) == 'default'
    assert store.key({'conv': ''}) == 'default'
    assert store.key({'conv': None}) == 'default'
    assert store.key({'conv': True}) == 'default'
    assert store.key({}) == 'default'
    assert store.key(None) == 'default'


def test_history_order_and_max_turns():
    store = ConversationStore(max_turns=3)
    for index in range(5):
        store.add('a', f'q{index}', f'a{index}', f'facts{index}')

    turns = store.history('a')
    assert [turn.question for turn in turns] == ['q2', 'q3', 'q4']
    assert [turn.answer for turn in turns] == ['a2', 'a3', 'a4']
    assert [turn.facts_text for turn in turns] == ['facts2', 'facts3', 'facts4']
    assert store.history('b') == []


def test_ttl_with_fake_clock():
    clock = FakeClock()
    store = ConversationStore(ttl=10.0, clock=clock)
    store.add('a', 'q1', 'a1')

    clock.now = 9.9
    assert len(store.history('a')) == 1
    clock.now = 10.0
    assert store.history('a') == []

    store.add('a', 'q2', 'a2')
    assert [turn.question for turn in store.history('a')] == ['q2']


def test_switching_conversation_forgets_previous():
    store = ConversationStore()
    store.add('a', 'qa', 'aa')
    store.add('b', 'qb', 'ab')

    assert store.history('a') == []
    assert [turn.question for turn in store.history('b')] == ['qb']

    store.add('a', 'qa2', 'aa2')
    assert [turn.question for turn in store.history('a')] == ['qa2']
    assert store.history('b') == []


def test_thread_safety_adding_turns():
    store = ConversationStore(max_turns=1000)

    def worker(base):
        for index in range(20):
            store.add('same', f'q{base}-{index}', 'a')

    threads = [threading.Thread(target=worker, args=(base,)) for base in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(store.history('same')) == 200


def test_build_prompt_with_history():
    history = [Turn('primera', 'a' * 400), Turn('segunda', 'b')]
    system, user = build_prompt({'lang': 'esES', 'q': '¿y allí?'}, 'DATOS VERIFICADOS: X',
                                history)

    assert 'CONVERSACIÓN PREVIA (de la más antigua a la más reciente):' in user
    assert 'Jugador: primera' in user
    assert 'Asistente: ' + 'a' * 300 in user
    assert 'a' * 301 not in user
    assert 'Jugador: segunda' in user
    assert user.index('CONVERSACIÓN PREVIA') < user.index('DATOS VERIFICADOS')
    assert user.index('DATOS VERIFICADOS') < user.index('Pregunta: ¿y allí?')
    assert 'conversación previa' in system.lower()

    _system, english = build_prompt({'lang': 'enUS', 'q': 'and there?'}, history=history)
    assert 'PREVIOUS CONVERSATION (oldest first):' in english
    assert 'Player: primera' in english
    assert 'Assistant: ' + 'a' * 300 in english


def test_system_prompt_has_concrete_rules():
    system, _user = build_prompt({'lang': 'esES', 'q': '¿Dónde está Hogger?'})
    for text in ('Sé concreto y útil', 'UNA frase', 'guías', 'webs', 'foros',
                 'No inventes', 'SOLO', '2 a 5'):
        assert text in system

    system, _user = build_prompt({'lang': 'enUS', 'q': 'Where is Hogger?'})
    for text in ('Be concrete and useful', 'ONE sentence', 'guides', 'websites',
                 'Do not invent', 'ONLY', '2 to 5'):
        assert text in system


def test_follow_up_reuses_previous_question_facts(db):
    provider = FakeProvider()
    result = answer_message(_data('¿Y a qué nivel la puedo hacer?'), provider, db=db,
                            previous_question='¿Qué jefes tiene Cuevas de los Lamentos?')

    assert result.ok is True
    assert 'Cuevas de los Lamentos' in result.facts_text
    assert 'Cuevas de los Lamentos' in provider.calls[0]['user']
    assert result.facts


def test_follow_up_without_previous_question_has_no_entity_facts(db):
    provider = FakeProvider()
    result = answer_message(_data('¿Y a qué nivel la puedo hacer?'), provider, db=db)

    assert 'Mazmorra «Cuevas de los Lamentos»' not in result.facts_text
    assert 'Mazmorras para tu nivel (16):' in result.facts_text
    assert 'Mazmorra «Cuevas de los Lamentos»' not in provider.calls[0]['user']


def test_answer_message_passes_history_to_prompt(db):
    provider = FakeProvider()
    history = [Turn('¿Qué misiones me recomiendas?', 'Prueba Loch Modan.')]
    result = answer_message(_data('¿Y a qué nivel la puedo hacer?'), provider, db=db,
                            history=history,
                            previous_question='¿Qué jefes tiene Cuevas de los Lamentos?')

    user = provider.calls[0]['user']
    assert 'CONVERSACIÓN PREVIA' in user
    assert 'Jugador: ¿Qué misiones me recomiendas?' in user
    assert 'Asistente: Prueba Loch Modan.' in user
    assert user.index('CONVERSACIÓN PREVIA') < user.index('DATOS VERIFICADOS')
    assert result.facts_text


def _write_questions(tmp_path, chained=True):
    questions = [
        {'id': 'c1', 'category': 'seguimiento', 'q': '¿Qué misiones me recomiendas?',
         'notes': 'n'},
        {'id': 'c2', 'category': 'seguimiento', 'q': '¿Puedo ir a otra zona?',
         'notes': 'n'},
    ]
    if chained:
        for question in questions:
            question['chain'] = 'inicio'
    data = {'default_ctx': {'lvl': 16, 'race': 'Enano'}, 'questions': questions}
    path = tmp_path / 'questions.json'
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return load_questions(path)


def test_bench_chain_passes_history(tmp_path):
    questions = _write_questions(tmp_path, chained=True)
    provider = FakeProvider(['recomiendo Loch Modan', 'prueba Páramos de Poniente'])
    results = run_bench(
        questions, [Target('fake', 'modelo')],
        provider_factory=lambda **_: provider,
        sleep=lambda seconds: None,
    )

    assert all(result.ok for result in results)
    first = provider.calls[0]['user']
    second = provider.calls[1]['user']
    assert 'CONVERSACIÓN PREVIA' not in first
    assert 'CONVERSACIÓN PREVIA' in second
    assert 'Jugador: ¿Qué misiones me recomiendas?' in second
    assert 'Asistente: recomiendo Loch Modan' in second

    markdown = render_markdown(questions, [Target('fake', 'modelo')], results,
                               '2026-11-14 06:00:00')
    assert 'cadena inicio' in markdown


def test_bench_without_chain_has_no_history(tmp_path):
    questions = _write_questions(tmp_path, chained=False)
    provider = FakeProvider(['uno', 'dos'])
    run_bench(
        questions, [Target('fake', 'modelo')],
        provider_factory=lambda **_: provider,
        sleep=lambda seconds: None,
    )

    assert 'CONVERSACIÓN PREVIA' not in provider.calls[0]['user']
    assert 'CONVERSACIÓN PREVIA' not in provider.calls[1]['user']


def _wait_for(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_run_command_passes_history_per_conversation(monkeypatch):
    events = []
    done = threading.Event()
    provider = FakeProvider(['primera respuesta', 'segunda respuesta', 'tercera respuesta'])
    messages = [
        ReceivedMessage(1, 1, _data('primera', 1), 0.0, 0.1),
        ReceivedMessage(2, 1, _data('segunda', 1), 0.0, 0.2),
        ReceivedMessage(3, 1, _data('tercera', 2), 0.0, 0.3),
    ]

    class Grabber:
        def __init__(self, on_message, fps=30.0):
            self.on_message = on_message
            self.captures = 0
            self.valid_frames = 0
            self.messages = 0
            self.errors = 0

        def run(self, stop_event):
            for index, message in enumerate(messages):
                self.messages += 1
                self.on_message(message)
                _wait_for(lambda: len([event for event in events
                                       if event[0] == 'answer']) >= index + 1)
            done.set()

    class Overlay:
        def __init__(self, ttl=30.0):
            self.ttl = ttl

        def show_thinking(self, question, lang):
            events.append(['thinking', question, lang])

        def show_answer(self, question, text, lang):
            events.append(['answer', question, text, lang])

        def show_error(self, text, lang):
            events.append(['error', text, lang])

        def run(self, stop_event=None):
            done.wait(5.0)

        def close(self):
            pass

    monkeypatch.setattr(cli, 'Grabber', Grabber)
    monkeypatch.setattr(cli, 'OverlaySupervisor', Overlay)
    monkeypatch.setattr(cli, 'provider_from_config', lambda: provider)

    assert cli.main(['run', '--no-data', '--no-web']) == 0
    assert done.is_set()

    calls = provider.calls
    assert len(calls) == 3
    assert 'CONVERSACIÓN PREVIA' not in calls[0]['user']
    assert 'CONVERSACIÓN PREVIA' in calls[1]['user']
    assert 'Jugador: primera' in calls[1]['user']
    assert 'Asistente: primera respuesta' in calls[1]['user']
    assert 'CONVERSACIÓN PREVIA' not in calls[2]['user']


def test_is_follow_up_detects_short_continuations():
    from askforever.engine.answer import is_follow_up
    assert is_follow_up('y para levear cuál me recomiendas?')
    assert is_follow_up('¿Y en Forjaz?')
    assert is_follow_up('and where is that?')
    assert not is_follow_up('¿Dónde está el banco de Ventormenta?')
    assert not is_follow_up('y ' + 'palabra ' * 12)
    assert not is_follow_up('')



def test_follow_up_with_own_facts_keeps_previous_topic(db, monkeypatch):
    from askforever.engine import answer as answer_module
    from askforever.engine.retriever import Facts

    asked = []

    def fake_retrieve(message, _db):
        asked.append(message['q'])
        return Facts(lines=[f"dato de: {message['q']}"])

    monkeypatch.setattr(answer_module, 'retrieve', fake_retrieve)
    result = answer_message(_data('y para levear cuál me recomiendas?'), FakeProvider(),
                            db=db, previous_question='¿Qué ramas de talentos tengo?')

    assert asked == ['y para levear cuál me recomiendas?',
                     '¿Qué ramas de talentos tengo? y para levear cuál me recomiendas?']
    assert 'ramas de talentos' in result.facts_text

    asked.clear()
    answer_message(_data('¿Dónde está el banco de Ventormenta?'), FakeProvider(), db=db,
                   previous_question='¿Qué ramas de talentos tengo?')
    assert asked == ['¿Dónde está el banco de Ventormenta?']
