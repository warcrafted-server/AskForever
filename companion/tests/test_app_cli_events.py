from askforever import cli


def test_run_companion_activity_helpers_emit_friendly_events(monkeypatch):
    emitted = []
    monkeypatch.setattr(cli, 'emit', lambda *args, **kwargs: emitted.append((args, kwargs)))

    cli._emit_question_event('¿' + 'a' * 100, 'private-id', 'conv-7')
    cli._emit_answer_event(1234, 'private-id', 'respuesta completa')
    cli._emit_answer_error('fallo breve', 'private-id')

    question, answer, error = emitted
    assert question[0][0] == 'question'
    assert question[0][1] == 'Pregunta recibida: ¿' + 'a' * 79
    assert 'private-id' not in question[0][1]
    assert question[1]['detail'] == 'msg_id=private-id conv=conv-7'
    assert answer[0][1] == 'Respuesta enviada en 1,2 s'
    assert answer[0][2] == 'Answer sent in 1.2 s'
    assert answer[1]['detail'].endswith('answer_length=18')
    assert error[0][1] == 'No se pudo responder: fallo breve'
    assert 'private-id' not in error[0][1]


def test_game_data_update_emits_progress_and_friendly_result(monkeypatch, tmp_path):
    emitted = []
    statuses = []
    monkeypatch.setattr(cli, 'emit', lambda *args, **kwargs: emitted.append((args, kwargs)))
    monkeypatch.setattr(cli, 'set_status', lambda *args, **kwargs: statuses.append((args, kwargs)))
    monkeypatch.setattr(cli, 'user_data_dir', lambda: tmp_path / 'data')

    def update(_path, progress):
        progress(10, 100)
        progress(19, 100)
        progress(20, 100)
        return 'updated', '2026.11.17'

    monkeypatch.setattr(cli, 'check_and_update', update)
    assert cli._update_game_data() == ('updated', '2026.11.17')

    assert [item[0][0] for item in emitted].count('update') == 3
    assert emitted[-1][0][1:3] == (
        'Datos actualizados a 2026.11.17', 'Data updated to 2026.11.17')
    assert statuses[-1][0][0] == 'data'
    assert statuses[-1][1]['ok'] is True
