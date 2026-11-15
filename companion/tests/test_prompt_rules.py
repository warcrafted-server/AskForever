"""La IA no debe afirmar ni negar funciones del juego que no estén en los datos."""

from askforever.engine.prompt import build_prompt


def _system(lang):
    message = {'q': 'tenemos doble especializacion de talentos?', 'lang': lang, 'ctx': {}}
    system, _user = build_prompt(message, 'Ramas de talentos de Cazador: Punteria')
    return system


def test_spanish_rule_forbids_claiming_features_without_data():
    system = _system('esES')
    assert 'nunca afirmes ni niegues que algo existe' in system
    assert 'Forever no es igual que otras versiones' in system


def test_english_rule_forbids_claiming_features_without_data():
    system = _system('enUS')
    assert 'never state or deny' in system
    assert 'Forever is not the same as other' in system


def test_prompt_limits_panorama_and_extra_places():
    from askforever.engine.prompt import build_prompt
    system, _user = build_prompt({'lang': 'esES', 'q': '¿Dónde está la casa de subastas?'})
    assert 'no añadas barrios, distritos, edificios ni puntos de referencia' in system
    assert 'si la pregunta es de otra cosa, no lo menciones' in system
    system, _user = build_prompt({'lang': 'enUS', 'q': 'Where is the auction house?'})
    assert 'do not add districts, quarters, buildings or landmarks' in system
    assert 'if the question is about something else, do not mention it' in system


def test_prompt_gives_guide_recommendations_with_reason():
    from askforever.engine.prompt import build_prompt
    system, _user = build_prompt({'lang': 'esES', 'q': '¿Qué mascota me recomiendas?'})
    assert 'da esa recomendación con su motivo' in system
    system, _user = build_prompt({'lang': 'enUS', 'q': 'Which pet should I pick?'})
    assert 'give that recommendation with its reason' in system


def test_levelling_question_is_not_travel():
    from askforever.engine.retriever import is_travel_question
    assert not is_travel_question('qué talentos cojo para subir de nivel')
    assert is_travel_question('quiero ir a Forjaz')
    assert is_travel_question('¿Cómo voy a Ventormenta?')
