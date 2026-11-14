"""Pruebas de las respuestas de rutas y transportes con una base de datos temporal."""

from __future__ import annotations

import sqlite3

import pytest

from askforever.data.wowdb import WowDb
from askforever.engine.answer import needs_web
from askforever.engine.prompt import build_prompt
from askforever.engine.retriever import Facts, is_travel_question, retrieve

FLIGHT = 'vuelo'
FREE_FLIGHT = 'vuelo gratuito'
TRANSPORT = 'transporte (barco, zepelín, transbordador)'
NODEPATH = 'trayecto sin nodos (transporte o script)'

SCHEMA = [
    'CREATE TABLE v_ruta (ruta_id INTEGER, tipo TEXT, nodo_origen INTEGER, origen TEXT, '
    'nodo_destino INTEGER, destino TEXT, continente_origen INTEGER, '
    'continente_destino INTEGER, faccion TEXT, coste INTEGER, puntos INTEGER, '
    'longitud REAL, inicio_x REAL, inicio_y REAL, fin_x REAL, fin_y REAL, '
    'cerca_del_inicio TEXT, cerca_del_fin TEXT, visto_en_juego TEXT, viajes_vistos INTEGER)',
    'CREATE TABLE TaxiNodes (__id INTEGER, Name_lang TEXT, Pos TEXT, MapOffset TEXT, '
    'FlightMapOffset TEXT, ID INTEGER, ContinentID INTEGER, ConditionID INTEGER, '
    'CharacterBitNumber INTEGER, Flags INTEGER, UiTextureKitID INTEGER, '
    'MinimapAtlasMemberID INTEGER, Facing INTEGER, SpecialIconConditionID INTEGER, '
    'VisibilityConditionID INTEGER, MountCreatureID TEXT, Name_lang_esES TEXT)',
    'CREATE TABLE ext_quests (quest_id INTEGER)',
    'CREATE TABLE ext_zones (group_id INTEGER, area_id INTEGER, name_enUS TEXT, '
    'name_esES TEXT)',
]

TAXI = [
    (2, 'Stormwind, Elwynn', '[-8832.77, 478.62, 109.62]', 2, 0, 'Ventormenta, Elwynn'),
    (6, 'Ironforge, Dun Morogh', '[-4821.78, -1155.44, 502.21]', 6, 0,
     'Forjaz, Dun Morogh'),
    (8, 'Thelsamar, Loch Modan', '[-5421.91, -2930.01, 347.25]', 8, 0,
     'Thelsamar, Loch Modan'),
    (7, 'Menethil Harbor, Wetlands', '[-3792.26, -783.29, 9.06]', 7, 0,
     'Puerto de Menethil, Los Humedales'),
    (26, 'Auberdine, Darkshore', '[6341.38, 557.68, 16.29]', 26, 1,
     'Auberdine, Costa Oscura'),
    (27, "Rut'theran Village, Teldrassil", '[8643.59, 841.05, 23.3]', 27, 1,
     "Aldea Rut'theran, Teldrassil"),
    (23, 'Orgrimmar, Durotar', '[1677.59, -4315.71, 61.17]', 23, 1, 'Orgrimmar, Durotar'),
    (22, 'Thunder Bluff, Mulgore', '[-1197.21, 29.71, 176.95]', 22, 1,
     'Cima del Trueno, Mulgore'),
    (99, 'Trade District', '[-8832.5, 480.0, 109.6]', 99, 0, 'Distrito Comercial'),
    (80, 'Ratchet, The Barrens', '[-894.59, -3773.01, 11.48]', 80, 1,
     'Trinquete, Los Baldíos'),
    (9, 'Booty Bay, Stranglethorn', '[-14271.77, 299.87, 31.09]', 9, 0,
     'Bahía del Botín, Tuercespina'),
]

ZONES = [
    (0, 1537, 'Ironforge', 'Forjaz'),
    (0, 1519, 'Stormwind City', 'Ventormenta'),
    (1, 148, 'Darkshore', 'Costa Oscura'),
    (0, 40, 'Westfall', 'Páramos de Poniente'),
    (0, 38, 'Loch Modan', 'Loch Modan'),
]


def _route(ruta_id, kind, origin_id, origin, target_id, target, faction, cost, length,
           seen=None):
    return (ruta_id, kind, origin_id, origin, target_id, target, 0, 0, faction, cost,
            0, length, None, None, None, None, None, None, seen, None)


ROUTES = [
    _route(12, FLIGHT, 6, 'Ironforge, Dun Morogh', 2, 'Stormwind, Elwynn', 'Alianza',
           50, 6310.3),
    _route(13, FLIGHT, 2, 'Stormwind, Elwynn', 6, 'Ironforge, Dun Morogh', 'Alianza',
           50, 7757.3),
    _route(16, FLIGHT, 6, 'Ironforge, Dun Morogh', 8, 'Thelsamar, Loch Modan', 'Alianza',
           0, 3037.2),
    _route(15, FLIGHT, 8, 'Thelsamar, Loch Modan', 6, 'Ironforge, Dun Morogh', 'Alianza',
           0, 3266.0),
    _route(18, FLIGHT, 6, 'Ironforge, Dun Morogh', 7, 'Menethil Harbor, Wetlands',
           'Alianza', 0, 3860.6),
    _route(17, FLIGHT, 7, 'Menethil Harbor, Wetlands', 6, 'Ironforge, Dun Morogh',
           'Alianza', 0, 2658.3),
    _route(900, FLIGHT, 23, 'Orgrimmar, Durotar', 22, 'Thunder Bluff, Mulgore', 'Horda',
           0, 4000.0),
    _route(901, FLIGHT, 22, 'Thunder Bluff, Mulgore', 23, 'Orgrimmar, Durotar', 'Horda',
           0, 4000.0),
    _route(910, FLIGHT, 6, 'Ironforge, Dun Morogh', 24, 'Generic, World target',
           'Alianza', 0, 1000.0),
    _route(920, FREE_FLIGHT, 8, 'Thelsamar, Loch Modan', 7, 'Menethil Harbor, Wetlands',
           'Alianza', 0, 1000.0),
    _route(921, FLIGHT, 99, 'Trade District', 6, 'Ironforge, Dun Morogh',
           'Alianza', 0, 20000.0),
    _route(101, TRANSPORT, 26, 'Auberdine, Darkshore', 27,
           "Rut'theran Village, Teldrassil", 'Alianza', 0, 2525.0),
    _route(102, TRANSPORT, 27, "Rut'theran Village, Teldrassil", 26,
           'Auberdine, Darkshore', 'Alianza', 0, 2551.4),
    _route(11616, TRANSPORT, 0, 'Puerto de Ventormenta, Ciudad de Ventormenta', 0,
           'Cabo de la Niebla, Costa Oscura', None, 0, 18272.4,
           'Ciudad de Ventormenta -> Costa Oscura'),
    _route(472, NODEPATH, 0, None, 24, 'Generic, World target for Zeppelin Paths',
           None, 0, None),
    _route(950, TRANSPORT, 0, 'Transport, Booty Bay - Ratchet', 0,
           'Transport, Ratchet - Booty Bay', None, 0, 20000.0),
]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'wow.sqlite'
    conn = sqlite3.connect(path)
    for statement in SCHEMA:
        conn.execute(statement)
    conn.executemany(
        'INSERT INTO TaxiNodes (__id, Name_lang, Pos, ID, ContinentID, Name_lang_esES) '
        'VALUES (?, ?, ?, ?, ?, ?)', TAXI)
    conn.executemany(
        'INSERT INTO v_ruta (ruta_id, tipo, nodo_origen, origen, nodo_destino, destino, '
        'continente_origen, continente_destino, faccion, coste, puntos, longitud, '
        'inicio_x, inicio_y, fin_x, fin_y, cerca_del_inicio, cerca_del_fin, '
        'visto_en_juego, viajes_vistos) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', ROUTES)
    conn.executemany(
        'INSERT INTO ext_zones (group_id, area_id, name_enUS, name_esES) '
        'VALUES (?, ?, ?, ?)', ZONES)
    conn.commit()
    conn.close()

    database = WowDb(path)
    yield database
    database.close()


def _message(question, lang='esES', zone='Costa Oscura', sub=None, fp=None):
    ctx = {'fac': 'Alianza', 'zone': zone}
    if sub is not None:
        ctx['sub'] = sub
    if fp is not None:
        ctx['fp'] = fp
    return {'v': 1, 'lang': lang, 'q': question, 'ctx': ctx}


def _text(facts):
    return '\n'.join(facts.lines)


def test_fastest_route_from_current_zone(db):
    facts = retrieve(_message('¿cómo puedo ir lo más rápido posible a Forjaz?'), db)
    text = _text(facts)
    assert 'Ruta más rápida según la base:' in text
    assert 'barco' in text
    assert 'tranvía' in text
    assert not any('ruta entre' in item for item in facts.missing)
    assert any(source.startswith('route:') for source in facts.sources)


def test_route_between_two_places(db):
    facts = retrieve(_message('¿Cómo voy de Forjaz a Auberdine?'), db)
    text = _text(facts)
    assert 'Ruta más rápida según la base:' in text
    assert 'tranvía' in text
    assert 'barco' in text
    assert not any('ruta entre' in item for item in facts.missing)


def test_route_answer_in_english(db):
    facts = retrieve(_message('How do I get to Auberdine?', lang='enUS', zone='Forjaz'), db)
    text = _text(facts)
    assert 'Fastest route according to the database:' in text
    assert '(tram)' in text
    assert '(boat' in text


def test_direct_boat_line(db):
    facts = retrieve(
        _message('¿Sabes que hay un barco de Auberdine a Ventormenta directo?',
                 zone='Forjaz'), db)
    text = _text(facts)
    assert 'Transporte directo entre Auberdine y Ventormenta:' in text
    assert 'barco (visto en el juego)' in text


def test_missing_direct_transport(db):
    facts = retrieve(_message('¿Hay barco de Auberdine a Forjaz?', zone='Forjaz'), db)
    assert 'transporte directo entre Auberdine y Forjaz (no está en la base)' in facts.missing


def test_unknown_destination_does_not_invent_route(db):
    facts = retrieve(_message('¿cómo voy a Narnia?'), db)
    text = _text(facts)
    assert 'Ruta más rápida' not in text
    assert not any('ruta entre' in item for item in facts.missing)
    assert 'ruta: no reconozco el origen o el destino en la base' in facts.missing


def test_from_here_uses_player_position(db):
    facts = retrieve(
        _message('¿y de aquí a Ventormenta?', zone='Dun Morogh',
                 sub='Puertas de Forjaz'), db)
    text = _text(facts)
    assert 'Ruta más rápida según la base:' in text
    assert 'tranvía' in text
    assert 'Desde tu posición' not in text


def test_from_here_falls_back_to_zone(db):
    facts = retrieve(_message('y de aquí a Ventormenta?', zone='Dun Morogh'), db)
    text = _text(facts)
    assert 'Ruta más rápida según la base:' in text
    assert 'Forjaz' in text


def test_from_here_english(db):
    facts = retrieve(
        _message('How do I get from here to Ventormenta?', lang='enUS', zone='Forjaz'), db)
    text = _text(facts)
    assert 'Fastest route according to the database:' in text


def test_position_route_before_main_route(db):
    facts = retrieve(
        _message('¿Cómo voy de Ventormenta a Thelsamar?', zone='Dun Morogh',
                 sub='Puertas de Forjaz'), db)
    lines = facts.lines
    position = next(index for index, line in enumerate(lines)
                    if line.startswith('Desde tu posición (Puertas de Forjaz) '
                                       'hasta Ventormenta:'))
    main = next(index for index, line in enumerate(lines)
                if line.startswith('Ruta más rápida según la base:'))
    assert position < main


def test_no_position_route_when_already_there(db):
    facts = retrieve(_message('¿Cómo voy de Forjaz a Thelsamar?', zone='Forjaz'), db)
    text = _text(facts)
    assert 'Ruta más rápida según la base:' in text
    assert 'Desde tu posición' not in text


def test_missing_flight_points_faster_route(db):
    facts = retrieve(
        _message('¿Cómo voy de Forjaz a Thelsamar?', zone='Forjaz', fp=[]), db)
    text = _text(facts)
    assert 'Aún no tienes los puntos de vuelo' in text
    assert 'Cuando los tengas:' in text
    assert 'Thelsamar, Loch Modan' in text
    assert not any('ruta entre' in item for item in facts.missing)


def test_missing_flight_points_faster_route_english(db):
    facts = retrieve(
        _message('How do I get from Forjaz to Thelsamar?', lang='enUS',
                 zone='Forjaz', fp=[]), db)
    text = _text(facts)
    assert 'You do not have the flight points' in text
    assert 'Once you have them:' in text


def test_no_faster_route_warning_with_known_flights(db):
    facts = retrieve(
        _message('¿Cómo voy de Forjaz a Thelsamar?', zone='Forjaz', fp=[6, 8]), db)
    text = _text(facts)
    assert 'Ruta más rápida según la base:' in text
    assert 'Con puntos de vuelo que aún no tienes' not in text


def test_general_flight_points_warning_without_fp(db):
    facts = retrieve(_message('¿Cómo voy de Forjaz a Thelsamar?', zone='Forjaz'), db)
    text = _text(facts)
    assert 'Esta ruta usa los puntos de vuelo' in text
    assert 'Forjaz' in text
    assert 'Thelsamar, Loch Modan' in text
    assert 'El addon aún no sabe qué puntos de vuelo conoces' in text


def test_destination_flight_point_reminder(db):
    facts = retrieve(
        _message('¿Cómo voy de Forjaz a Ventormenta?', zone='Forjaz', fp=[]), db)
    text = _text(facts)
    assert ('Al llegar a Ventormenta, descubre el punto de vuelo de '
            'Ventormenta.') in text


def test_destination_flight_point_known_no_reminder(db):
    facts = retrieve(
        _message('¿Cómo voy de Forjaz a Ventormenta?', zone='Forjaz', fp=[2]), db)
    text = _text(facts)
    assert 'Al llegar a Ventormenta' not in text


def test_is_travel_question():
    assert is_travel_question('¿cómo puedo ir lo más rápido posible a Forjaz?')
    assert is_travel_question('¿Cómo voy de Forjaz a Auberdine?')
    assert is_travel_question('How do I get to Auberdine?')
    assert is_travel_question('¿Qué ruta me recomiendas?')
    assert is_travel_question('¿y de aquí a Ventormenta?')
    assert is_travel_question('¿Cómo voy desde aquí a Forjaz?')
    assert is_travel_question('How do I get from here to Auberdine?')
    assert not is_travel_question('¿Qué hechizos aprendo?')


def test_needs_web_is_false_for_travel_questions():
    assert needs_web(Facts(), '¿Cómo voy de Forjaz a Auberdine?') is False
    assert needs_web(Facts(), '¿cómo puedo ir lo más rápido posible a Forjaz?') is False


def test_system_prompt_has_travel_rule():
    system_es, _ = build_prompt({'lang': 'esES', 'q': '¿cómo voy a Forjaz?'})
    system_en, _ = build_prompt({'lang': 'enUS', 'q': 'How do I get to Forjaz?'})
    assert 'Para preguntas de viaje' in system_es
    assert 'no añadas atajos' in system_es
    assert 'For travel questions' in system_en
    assert 'do not add shortcuts' in system_en
