"""Pruebas del cálculo de rutas de viaje con una base de datos temporal."""

from __future__ import annotations

import sqlite3

import pytest

from askforever.data.routes import (KIND_FLIGHT, Node, KIND_TRANSPORT, KIND_TRAM, KIND_WALK,
                                    Route, RouteGraph, Step, describe, find_route,
                                    flight_point_near, resolve_place,
                                    route_flight_points, transport_between)
from askforever.data.wowdb import WowDb

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
    conn.commit()
    conn.close()

    database = WowDb(path)
    yield database
    database.close()


def test_build_is_cached_per_faction(db):
    graph_a = RouteGraph.build(db, 'A')
    assert RouteGraph.build(db, 'A') is graph_a
    assert RouteGraph.build(db, 'H') is not graph_a


def test_resolve_place(db):
    graph = RouteGraph.build(db, 'A')

    def names(text):
        return [node.name for node in resolve_place(graph, text)]

    assert 'Ventormenta, Elwynn' in names('Stormwind')
    assert 'Ventormenta, Elwynn' in names('ventormenta')
    assert 'Auberdine, Costa Oscura' in names('Costa Oscura')
    assert 'Cabo de la Niebla, Costa Oscura' in names('Costa Oscura')
    assert resolve_place(graph, 'Generic') == []


def test_find_route_to_auberdine(db):
    graph = RouteGraph.build(db, 'A')
    route = find_route(graph, 'Forjaz', 'Auberdine')

    assert route is not None
    assert route.seconds == 660
    kinds = [step.kind for step in route.steps]
    assert KIND_TRAM in kinds
    assert KIND_TRANSPORT in kinds
    assert any(step.kind == KIND_TRANSPORT and step.seen_in_game
               for step in route.steps)
    assert not any('Menethil' in step.from_name + step.to_name
                   for step in route.steps)

    text = describe(route, 'esES')
    assert '-> (tranvía) Ciudad de Ventormenta' in text
    assert '-> (a pie) Puerto de Ventormenta' in text
    assert '(barco, visto en el juego) Cabo de la Niebla, Costa Oscura' in text
    assert '-> (a pie) Auberdine, Costa Oscura' in text
    assert 'Tiempo aproximado:' in text

    english = describe(route, 'enUS')
    assert '(tram)' in english
    assert '(boat, seen in the game)' in english
    assert 'Approximate time:' in english


def test_route_reverse(db):
    graph = RouteGraph.build(db, 'A')
    route = find_route(graph, 'Costa Oscura', 'Forjaz')

    assert route is not None
    assert route.seconds == 600
    assert any(step.kind == KIND_TRANSPORT for step in route.steps)
    assert any(step.kind in (KIND_TRAM, KIND_FLIGHT) for step in route.steps)
    assert 'Forjaz' in describe(route, 'esES')


def test_route_chooses_faster_option(db):
    graph = RouteGraph.build(db, 'A')
    route = find_route(graph, 'Ventormenta', 'Forjaz')

    assert route is not None
    assert route.seconds == 180
    assert any(step.kind == KIND_TRAM for step in route.steps)
    assert not any(step.kind == KIND_FLIGHT for step in route.steps)


def test_horde_does_not_use_alliance_flights(db):
    graph_h = RouteGraph.build(db, 'H')
    horde = find_route(graph_h, 'Orgrimmar', 'Thunder Bluff')

    assert horde is not None
    assert all(step.kind == KIND_FLIGHT for step in horde.steps)
    assert find_route(graph_h, 'Forjaz', 'Thelsamar') is None

    graph_a = RouteGraph.build(db, 'A')
    assert find_route(graph_a, 'Orgrimmar', 'Thunder Bluff') is None


def test_unknown_place(db):
    graph = RouteGraph.build(db, 'A')
    assert find_route(graph, 'Forjaz', 'Lugar Inventado') is None


def test_transport_between(db):
    graph = RouteGraph.build(db, 'A')
    transports = transport_between(graph, 'Auberdine', 'Ventormenta')

    assert transports
    assert any(step.kind == KIND_TRANSPORT for step in transports)
    assert transport_between(graph, 'Auberdine', 'Forjaz') == []
    assert transport_between(graph, 'Auberdine', "Rut'theran")


def test_walk_within_600_yards(db):
    graph = RouteGraph.build(db, 'A')
    route = find_route(graph, 'Trade District', 'Stormwind')

    assert route is not None
    assert len(route.steps) == 1
    assert route.steps[0].kind == KIND_WALK
    assert route.seconds == 60


def test_free_flight_is_not_used(db):
    # Los vuelos gratuitos (Claro de la Luna) solo son para druidas: no entran en las rutas.
    graph = RouteGraph.build(db, 'A')
    route = find_route(graph, 'Thelsamar', 'Menethil')

    # Sin el vuelo gratuito directo, la ruta pasa por Forjaz (dos vuelos).
    assert route is not None
    assert len(route.steps) >= 2
    assert any('Forjaz' in step.to_name for step in route.steps)


def test_describe_merges_walks():
    route = Route(
        steps=[
            Step(KIND_WALK, 'A', 'B'),
            Step(KIND_WALK, 'B', 'C'),
            Step(KIND_FLIGHT, 'C', 'D', 50),
        ],
        seconds=120,
    )
    text = describe(route, 'esES')

    assert 'A -> (a pie) C -> (vuelo) D' in text
    assert text.count('(a pie)') == 1
    assert 'Tiempo aproximado: 2 min.' in text


def test_describe_spanish_languages():
    route = Route([Step(KIND_FLIGHT, 'A', 'B')], 120)

    for lang in ('es', 'esES', 'esMX'):
        text = describe(route, lang)
        assert '(vuelo)' in text
        assert 'Tiempo aproximado: 2 min.' in text

    assert '(flight)' in describe(route, 'enUS')
    assert 'Approximate time:' in describe(route, 'en')


def test_transport_node_does_not_create_walk(db):
    graph = RouteGraph.build(db, 'A')

    assert find_route(graph, 'Ratchet', 'Booty Bay') is None
    for node in graph.nodes.values():
        if node.garbage:
            for _neighbor, _seconds, step in graph.adjacency.get(node.key, []):
                assert step.kind != KIND_WALK


def test_auberdine_to_ventormenta_uses_recorded_boat(db):
    graph = RouteGraph.build(db, 'A')
    route = find_route(graph, 'Auberdine', 'Ventormenta')

    assert route is not None
    assert route.seconds == 540
    boats = [step for step in route.steps if step.kind == KIND_TRANSPORT]
    assert boats
    assert any('Cabo de la Niebla' in step.from_name
               or 'Cabo de la Niebla' in step.to_name for step in boats)
    assert any(step.seen_in_game for step in boats)


def test_find_route_uses_known_flights_only(db):
    graph = RouteGraph.build(db, 'A')

    assert find_route(graph, 'Forjaz', 'Thelsamar', set()) is None
    assert find_route(graph, 'Forjaz', 'Thelsamar', {6}) is None
    assert find_route(graph, 'Forjaz', 'Thelsamar', {8}) is None
    route = find_route(graph, 'Forjaz', 'Thelsamar', {6, 8})
    assert route is not None
    assert any(step.kind == KIND_FLIGHT for step in route.steps)


def test_route_flight_points(db):
    graph = RouteGraph.build(db, 'A')
    route = find_route(graph, 'Forjaz', 'Thelsamar', {6, 8})

    assert route_flight_points(route, 'es') == ['Forjaz, Dun Morogh',
                                                'Thelsamar, Loch Modan']
    assert route_flight_points(route, 'en') == ['Ironforge, Dun Morogh',
                                                'Thelsamar, Loch Modan']
    tram_route = find_route(graph, 'Forjaz', 'Ventormenta')
    assert route_flight_points(tram_route) == []


def test_flight_point_near(db):
    graph = RouteGraph.build(db, 'A')

    assert flight_point_near(graph, 'Forjaz').taxi_id == 6
    assert flight_point_near(graph, 'Thelsamar').taxi_id == 8
    assert flight_point_near(graph, 'Cabo de la Niebla') is None
    assert flight_point_near(graph, 'Lugar Inventado') is None


def test_generic_words_do_not_match_by_prefix():
    node = Node(key=('taxi', 1), name='Astranaar, Vallefresno', name_en='Astranaar, Ashenvale',
                place='Astranaar', zone='vallefresno', place_en='Astranaar',
                zone_en='ashenvale', taxi_id=1)
    graph = RouteGraph({node.key: node}, {})

    assert resolve_place(graph, 'Valle de Crestanevada') == []
    assert resolve_place(graph, 'Vallefresno') == [node]
