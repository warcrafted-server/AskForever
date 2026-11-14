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
