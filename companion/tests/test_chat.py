"""Pruebas del estado puro del chat anclado."""

from __future__ import annotations

from askforever.overlay.chat import ChatSession

RECT = (10, 20, 300, 200)


def _questions(session):
    return [text for role, text in session.entries if role == 'question']


def test_question_and_answer_flow():
    session = ChatSession()
    view = session.question(7, '¿Dónde está Hogger?', RECT, 'esES')

    assert view.visible is True
    assert view.rect == RECT
    assert view.entries == (('question', '¿Dónde está Hogger?'),
                            ('thinking', 'Pensando…'))

    view = session.answer(7, 'En el bosque de Elwynn.')

    assert view.visible is True
    assert view.entries[-1] == ('answer', 'En el bosque de Elwynn.')
    assert session.entries[-2] == ('question', '¿Dónde está Hogger?')


def test_error_replaces_thinking():
    session = ChatSession()
    session.question(3, 'Question', RECT, 'enUS')
    view = session.error(3, 'Provider failed')

    assert view.visible is True
    assert view.entries[-1] == ('error', 'Provider failed')
    assert all(role != 'thinking' for role, _text in view.entries)


def test_new_conversation_resets_entries():
    session = ChatSession()
    session.question(1, 'first', RECT, 'enUS')
    session.answer(1, 'one')
    view = session.question(2, 'second', RECT, 'enUS')

    assert _questions(session) == ['second']
    assert view.entries[0] == ('question', 'second')


def test_close_open_move_and_unknown_events():
    session = ChatSession()
    session.question(1, 'question', RECT, 'enUS')

    hidden = session.ui('close', 1, RECT)
    assert hidden.visible is False
    assert session.window_open is False
    assert session.entries

    opened = session.ui('open', 1, RECT)
    assert opened.visible is True
    assert session.window_open is True

    moved = session.ui('move', 1, (1, 2, 400, 300))
    assert moved.visible is True
    assert moved.rect == (1, 2, 400, 300)

    unchanged = session.ui('unknown', 1, (0, 0, 1, 1))
    assert unchanged == moved


def test_open_without_entries_is_hidden():
    session = ChatSession()
    view = session.ui('open', 1, RECT)

    assert view.visible is False
    assert view.rect == RECT
    assert view.entries == ()


def test_open_new_conversation_resets_entries():
    session = ChatSession()
    session.question(1, 'old', RECT, 'enUS')
    session.answer(1, 'answer')
    view = session.ui('open', 2, RECT)

    assert view.entries == ()
    assert view.visible is False
    assert session.conv == 2


def test_rect_validation():
    session = ChatSession()

    assert session.question(1, 'classic', None, 'enUS') is None
    assert session.answer(1, 'classic') is None
    assert session.question(1, 'zero', (1, 2, 0, 20), 'enUS') is None
    assert session.question(1, 'float', (1, 2, 30.0, 20), 'enUS') is None
    assert session.question(1, 'bool', (1, 2, True, 20), 'enUS') is None
    assert session.question(1, 'short', (1, 2, 30), 'enUS') is None

    view = session.ui('open', 1, (1, 2, 0, 20))
    assert view.visible is False
    assert view.rect is None


def test_classic_fallback_after_chat():
    session = ChatSession()
    session.question(1, 'chat', RECT, 'enUS')

    assert session.question(1, 'classic', None, 'enUS') is None
    assert session.rect is None
    assert session.answer(1, 'not chat') is None


def test_last_twenty_questions_are_kept():
    session = ChatSession()
    for index in range(25):
        session.question(1, f'q{index}', RECT, 'enUS')
        session.answer(1, f'a{index}')

    questions = _questions(session)
    assert questions == [f'q{index}' for index in range(5, 25)]
    assert len(questions) == 20
    assert session.entries[0] == ('question', 'q5')
    assert session.entries[-1] == ('answer', 'a24')


def test_ui_without_rect_keeps_last_rect():
    session = ChatSession()
    session.question(1, 'hola', (10, 20, 300, 200), 'esES')
    session.ui('close', 1, None)
    view = session.ui('open', 1, None)
    assert view.rect == (10, 20, 300, 200)
    assert view.visible
    view = session.ui('move', 1, None)
    assert view.rect == (10, 20, 300, 200)
