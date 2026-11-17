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


def test_prompt_does_not_cite_internal_sources():
    from askforever.engine.prompt import build_prompt
    system, _user = build_prompt({'lang': 'esES', 'q': '¿Cuándo tengo montura?'})
    assert 'No digas de dónde sale cada dato' in system
    system, _user = build_prompt({'lang': 'enUS', 'q': 'When do I get a mount?'})
    assert 'Do not say where each piece of data comes from' in system


def test_prompt_includes_talent_points_for_numeric_levels():
    _system, user = build_prompt({
        'lang': 'esES', 'q': '¿Qué talentos debería tener?', 'ctx': {'lvl': 34},
    })
    assert 'Puntos de talento a este nivel: 25 (uno por nivel desde el 10)' in user

    _system, user = build_prompt({'lang': 'esES', 'q': '¿Qué talentos?', 'ctx': {'lvl': 5}})
    assert 'Puntos de talento a este nivel: 0 (uno por nivel desde el 10)' in user

    _system, user = build_prompt({'lang': 'esES', 'q': '¿Qué talentos?', 'ctx': {'lvl': 60}})
    assert 'Puntos de talento a este nivel: 51 (uno por nivel desde el 10)' in user

    _system, user = build_prompt({
        'lang': 'enUS', 'q': 'Which talents should I have?', 'ctx': {'lvl': 34},
    })
    assert 'Talent points at this level: 25 (one per level from 10)' in user

    _system, user = build_prompt({'lang': 'esES', 'q': '¿Qué talentos?', 'ctx': {}})
    assert 'Puntos de talento a este nivel' not in user


def test_system_prompt_contains_complete_build_and_version_rules():
    system_es = _system('esES')
    assert 'con una respuesta breve de 2 a 5 frases (las builds, completas; ver abajo).' in system_es
    assert 'separa cada tema en su propio párrafo con una línea en blanco' in system_es
    assert 'pon uno por línea empezando por «- »' in system_es
    assert 'cada rama en su propia línea empezando por su nombre y dos puntos' in system_es
    assert 'texto seguido' not in system_es
    assert 'todas sus ramas y cada talento con sus rangos' in system_es
    assert 'nunca cuentes más puntos de los que tiene' in system_es
    assert 'La pregunta puede tratar de otra clase, raza o especialización' in system_es
    assert 'No completes talentos, rangos, builds ni mecánicas de clase' in system_es

    system_en = _system('enUS')
    assert 'with a brief reply of 2 to 5 sentences (builds in full; see below).' in system_en
    assert 'put each topic in its own paragraph separated by a blank line' in system_en
    assert 'put one per line starting with "- "' in system_en
    assert 'each tree on its own line starting with its name and a colon' in system_en
    assert 'running text' not in system_en
    assert 'all its trees and every talent with its ranks' in system_en
    assert 'never count more points than they have' in system_en
    assert 'The question may be about a class, race or specialization' in system_en
    assert 'Do not fill in talents, ranks, builds or class mechanics' in system_en


def test_prompt_orders_build_trees_and_expands_broad_answers():
    system_es = _system('esES')
    assert ('empieza por la rama principal (la que tiene más puntos) y sigue con las demás '
            'de más a menos puntos') in system_es
    assert 'extiéndete lo necesario y cubre cada tema que pidan con los datos' in system_es

    system_en = _system('enUS')
    assert ('start with the main tree (the one with most points) and continue with the others '
            'from most to fewest points') in system_en
    assert 'take the space you need and cover each topic they ask for with the data' in system_en
