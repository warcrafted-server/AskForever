"""Cálculo de rutas de viaje con vuelos, transportes y tramos a pie."""

from __future__ import annotations

import heapq
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from askforever.data.wowdb import normalize, taxi_display_name

JSON_PATH = Path(__file__).with_name('forever_transports.json')
WALK_SECONDS = 60.0
FLIGHT_SPEED = 30.0
FLIGHT_OVERHEAD = 15.0
TRANSPORT_SECONDS = 420.0
WALK_RADIUS = 600.0
KIND_FLIGHT = 'vuelo'
KIND_TRANSPORT = 'barco/zepelín'
KIND_TRAM = 'tranvía'
KIND_WALK = 'a pie'
EXCLUDED_WORDS = {
    'ciudad', 'puerto', 'transporte', 'transport', 'generic', 'playa', 'villa',
    'oscura', 'oscuro', 'costa', 'bosque', 'valle', 'monte', 'lago', 'aldea',
    'pueblo', 'campamento', 'refugio', 'torre', 'isla',
}
KIND_LABELS = {
    'es': {KIND_FLIGHT: 'vuelo', KIND_TRANSPORT: 'barco', KIND_TRAM: 'tranvía',
           KIND_WALK: 'a pie'},
    'en': {KIND_FLIGHT: 'flight', KIND_TRANSPORT: 'boat', KIND_TRAM: 'tram',
           KIND_WALK: 'on foot'},
}


@dataclass
class Node:
    """Extremo de una ruta con su nombre localizado y sus partes."""

    key: tuple
    name: str
    name_en: str
    place: str
    zone: str
    place_en: str
    zone_en: str
    taxi_id: int = 0
    continent: Optional[int] = None
    pos: Optional[tuple] = None
    garbage: bool = False
    hard_garbage: bool = False


@dataclass
class Step:
    """Tramo de una ruta."""

    kind: str
    from_name: str
    to_name: str
    cost_copper: int = 0
    seen_in_game: bool = False
    from_name_en: str = ''
    to_name_en: str = ''


@dataclass
class Route:
    """Ruta completa con sus tramos y su tiempo estimado."""

    steps: list[Step] = field(default_factory=list)
    seconds: int = 0


class RouteGraph:
    """Grafo de viaje construido a partir de v_ruta, TaxiNodes y el JSON."""

    def __init__(self, nodes: dict, adjacency: dict):
        self.nodes = nodes
        self.adjacency = adjacency

    @classmethod
    def build(cls, db, faction=None):
        """Devuelve el grafo de la facción, construido una sola vez por db."""
        if isinstance(faction, str):
            faction = faction.upper()
        cache = getattr(db, '_route_graph_cache', None)
        if not isinstance(cache, dict):
            cache = {}
            setattr(db, '_route_graph_cache', cache)
        key = faction or ''
        graph = cache.get(key)
        if graph is None:
            graph = _build_graph(db, faction)
            cache[key] = graph
        return graph


def _int(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _number(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _split_name(name: str):
    text = (name or '').strip()
    if ',' in text:
        place, zone = text.rsplit(',', 1)
        return place.strip(), normalize(zone)
    return text, ''


def _words(text: str) -> set:
    return {word for word in normalize(text).split()
            if len(word) >= 5 and word not in EXCLUDED_WORDS}


def _parse_pos(value):
    try:
        coords = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        return None
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    try:
        return tuple(float(item) for item in coords[:3])
    except (TypeError, ValueError):
        return None


def _garbage_flags(name: str):
    text = normalize(name)
    hard = text.startswith(('generic', 'zz')) or 'quest path' in text
    return hard or text.startswith('transport'), hard


def _faction_ok(faction, value) -> bool:
    if faction is None:
        return True
    text = normalize(value)
    if not text:
        return True
    return text == ('alianza' if faction == 'A' else 'horda')


def _seen(value) -> bool:
    return bool(value and str(value).strip())


def _loading_json() -> list:
    try:
        data = json.loads(JSON_PATH.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    transports = data.get('transports') if isinstance(data, dict) else None
    return transports if isinstance(transports, list) else []


def _taxi_nodes(db) -> dict:
    nodes = {}
    for row in db._rows('SELECT ID, Name_lang, Name_lang_esES, ContinentID, Pos '
                        'FROM TaxiNodes'):
        taxi_id = _int(row['ID'])
        if taxi_id is None:
            continue
        nodes[taxi_id] = {
            'name': (row['Name_lang_esES'] or row['Name_lang'] or '').strip(),
            'name_en': (row['Name_lang'] or row['Name_lang_esES'] or '').strip(),
            'continent': _int(row['ContinentID']),
            'pos': _parse_pos(row['Pos']),
        }
    return nodes


def _ensure_node(nodes, key, name, name_en, taxi_id=0, info=None):
    if key is None:
        key = ('text', normalize(name))
    node = nodes.get(key)
    if node is not None:
        return node
    place, zone = _split_name(name)
    place_en, zone_en = _split_name(name_en or name)
    garbage, hard = _garbage_flags(name)
    info = info or {}
    # La zona se conserva para resolver lugares («Bosque de Elwynn» llega a
    # Ventormenta), pero se muestra solo el nombre de la ciudad.
    node = Node(
        key=key,
        name=taxi_display_name(name),
        name_en=taxi_display_name(name_en or name),
        place=place,
        zone=zone,
        place_en=place_en,
        zone_en=zone_en,
        taxi_id=taxi_id or 0,
        continent=info.get('continent'),
        pos=info.get('pos'),
        garbage=garbage,
        hard_garbage=hard,
    )
    nodes[key] = node
    return node


def _endpoint(row, side, taxi):
    node_id = _int(row[f'nodo_{side}']) or 0
    text = str(row[side] or '').strip()
    if not node_id:
        return None, text, text, 0, None
    info = taxi.get(node_id)
    if info:
        return ('taxi', node_id), info['name'] or text, info['name_en'] or text, node_id, info
    return ('taxi', node_id), text, text, node_id, None


def _add_edge(adjacency, source, target, seconds, kind, cost=0, seen=False):
    step = Step(kind, source.name, target.name, cost, seen,
                source.name_en, target.name_en)
    adjacency.setdefault(source.key, []).append((target.key, seconds, step))
    return step


def _add_walk(adjacency, first, second):
    _add_edge(adjacency, first, second, WALK_SECONDS, KIND_WALK)
    _add_edge(adjacency, second, first, WALK_SECONDS, KIND_WALK)


def _walk_connected(first, second, words) -> bool:
    if first.zone and first.zone == second.zone:
        return True
    if first.zone_en and first.zone_en == second.zone_en:
        return True
    # Los nodos de transporte tienen continentes poco fiables: no se filtran.
    regular = (first.taxi_id and not first.garbage
               and second.taxi_id and not second.garbage)
    same_continent = (not regular or first.continent is None or second.continent is None
                      or first.continent == second.continent)
    if same_continent and words[first.key] & words[second.key]:
        return True
    if (regular and first.pos and second.pos and first.continent is not None
            and first.continent == second.continent
            and any(abs(value) > 1e-9 for value in first.pos)
            and any(abs(value) > 1e-9 for value in second.pos)):
        squared = sum((a - b) ** 2 for a, b in zip(first.pos, second.pos))
        if squared < WALK_RADIUS ** 2:
            return True
    return False


def _add_walking(nodes, adjacency):
    items = [node for node in nodes.values() if not node.garbage]
    words = {node.key: _node_words(node) for node in items}
    for index, first in enumerate(items):
        for second in items[index + 1:]:
            if _walk_connected(first, second, words):
                _add_walk(adjacency, first, second)


def _flight_seconds(length) -> float:
    value = _number(length) or 0.0
    if value < 0:
        value = 0.0
    return value / FLIGHT_SPEED + FLIGHT_OVERHEAD


def _build_graph(db, faction) -> RouteGraph:
    taxi = _taxi_nodes(db)
    nodes = {}
    adjacency = {}

    for row in db._rows('SELECT * FROM v_ruta'):
        kind = normalize(row['tipo'])
        # Los «vuelos gratuitos» (Claro de la Luna) solo los pueden usar los druidas.
        if kind != 'vuelo' and not kind.startswith('transporte'):
            continue
        if not _faction_ok(faction, row['faccion']):
            continue
        origin_key, origin, origin_en, origin_id, origin_info = _endpoint(
            row, 'origen', taxi)
        target_key, target, target_en, target_id, target_info = _endpoint(
            row, 'destino', taxi)
        if not origin or not target:
            continue
        origin_node = _ensure_node(nodes, origin_key, origin, origin_en,
                                   origin_id, origin_info)
        target_node = _ensure_node(nodes, target_key, target, target_en,
                                   target_id, target_info)
        if kind in ('vuelo', 'vuelo gratuito'):
            if origin_node.garbage or target_node.garbage:
                continue
            seconds = _flight_seconds(row['longitud'])
            _add_edge(adjacency, origin_node, target_node, seconds, KIND_FLIGHT,
                      _int(row['coste']) or 0, _seen(row['visto_en_juego']))
        else:
            if origin_node.garbage or target_node.garbage:
                continue
            seconds = TRANSPORT_SECONDS
            seen = _seen(row['visto_en_juego'])
            _add_edge(adjacency, origin_node, target_node, seconds, KIND_TRANSPORT,
                      0, seen)
            _add_edge(adjacency, target_node, origin_node, seconds, KIND_TRANSPORT,
                      0, seen)

    for item in _loading_json():
        if not isinstance(item, dict):
            continue
        if not _faction_ok(faction, item.get('faction')):
            continue
        origin = str(item.get('from_es') or item.get('from_en') or '').strip()
        origin_en = str(item.get('from_en') or item.get('from_es') or '').strip()
        target = str(item.get('to_es') or item.get('to_en') or '').strip()
        target_en = str(item.get('to_en') or item.get('to_es') or '').strip()
        if not origin or not target:
            continue
        origin_node = _ensure_node(nodes, None, origin, origin_en)
        target_node = _ensure_node(nodes, None, target, target_en)
        if origin_node.hard_garbage or target_node.hard_garbage:
            continue
        minutes = _number(item.get('minutes')) or 0.0
        seconds = minutes * 60.0
        _add_edge(adjacency, origin_node, target_node, seconds, KIND_TRAM)
        _add_edge(adjacency, target_node, origin_node, seconds, KIND_TRAM)

    _add_walking(nodes, adjacency)
    return RouteGraph(nodes, adjacency)


def _node_words(node: Node) -> set:
    combined = set()
    for text in (node.place, node.zone, node.place_en, node.zone_en):
        combined |= _words(text)
    return combined


def resolve_place(graph, text) -> list:
    """Nodos candidatos para un lugar escrito en español o inglés."""
    target = normalize(text)
    if not target:
        return []
    # Sin las palabras genéricas, «Valle de Crestanevada» casaría con «Vallefresno».
    tokens = [token for token in target.split()
              if len(token) >= 5 and token not in EXCLUDED_WORDS]
    exact = []
    prefixed = []
    for node in graph.nodes.values():
        if node.garbage:
            continue
        exact_names = (node.zone, node.zone_en, normalize(node.place),
                       normalize(node.place_en))
        if target in exact_names:
            exact.append(node)
            continue
        if tokens:
            own = _node_words(node)
            if any(word.startswith(token) for word in own for token in tokens):
                prefixed.append(node)
    candidates = exact or prefixed
    return sorted(candidates, key=lambda node: (node.name, str(node.key)))


def _walk_neighbors(graph, keys):
    result = set(keys)
    for key in keys:
        for neighbor, _seconds, step in graph.adjacency.get(key, []):
            if step.kind == KIND_WALK:
                result.add(neighbor)
    return result


def _flight_endpoint_keys(graph) -> set:
    keys = set()
    for source, edges in graph.adjacency.items():
        for neighbor, _seconds, step in edges:
            if step.kind == KIND_FLIGHT:
                keys.add(source)
                keys.add(neighbor)
    return keys


def flight_point_near(graph, place_text):
    """Punto de vuelo (nodo con taxi_id y vuelos) de un lugar, o None."""
    if graph is None:
        return None
    flight_keys = _flight_endpoint_keys(graph)
    for node in resolve_place(graph, place_text):
        if node.taxi_id and node.key in flight_keys:
            return node
    return None


def find_route(graph, origin_text, destination_text,
               known_flights=None) -> Optional[Route]:
    """Ruta más rápida entre dos lugares, o None si no hay camino.

    Si known_flights es un conjunto de taxi_id, los vuelos solo pueden usar
    puntos de vuelo que el personaje conoce.
    """
    origins = resolve_place(graph, origin_text)
    destinations = resolve_place(graph, destination_text)
    if not origins or not destinations:
        return None
    targets = {node.key for node in destinations}
    distances = {}
    previous = {}
    queue = []
    counter = 0
    for node in origins:
        if node.key in distances:
            continue
        distances[node.key] = 0.0
        heapq.heappush(queue, (0.0, counter, node.key))
        counter += 1
    while queue:
        distance, _order, key = heapq.heappop(queue)
        if distance > distances.get(key, math.inf) + 1e-9:
            continue
        if key in targets:
            steps = []
            current = key
            while current in previous:
                parent, step = previous[current]
                steps.append(step)
                current = parent
            steps.reverse()
            return Route(steps, int(round(distance)))
        key_node = graph.nodes.get(key)
        for neighbor, seconds, step in graph.adjacency.get(key, []):
            if known_flights is not None and step.kind == KIND_FLIGHT:
                target_node = graph.nodes.get(neighbor)
                if (key_node is None or target_node is None
                        or key_node.taxi_id not in known_flights
                        or target_node.taxi_id not in known_flights):
                    continue
            candidate = distance + seconds
            if candidate < distances.get(neighbor, math.inf) - 1e-9:
                distances[neighbor] = candidate
                previous[neighbor] = (key, step)
                heapq.heappush(queue, (candidate, counter, neighbor))
                counter += 1
    return None


def transport_between(graph, a_text, b_text) -> list:
    """Transportes directos (sin vuelos) entre dos lugares."""
    origins = resolve_place(graph, a_text)
    destinations = resolve_place(graph, b_text)
    if not origins or not destinations:
        return []
    origin_keys = _walk_neighbors(graph, {node.key for node in origins})
    destination_keys = _walk_neighbors(graph, {node.key for node in destinations})
    transports = []
    seen = set()
    for key in origin_keys:
        for neighbor, _seconds, step in graph.adjacency.get(key, []):
            if step.kind not in (KIND_TRANSPORT, KIND_TRAM):
                continue
            if neighbor not in destination_keys:
                continue
            marker = (step.kind, step.from_name, step.to_name)
            if marker in seen:
                continue
            seen.add(marker)
            transports.append(step)
    return transports


def _copy_step(step: Step) -> Step:
    return Step(step.kind, step.from_name, step.to_name, step.cost_copper,
                step.seen_in_game, step.from_name_en, step.to_name_en)


def _merge_walks(steps) -> list:
    merged = []
    for step in steps:
        if step.kind == KIND_WALK and merged and merged[-1].kind == KIND_WALK:
            merged[-1].to_name = step.to_name
            merged[-1].to_name_en = step.to_name_en
        else:
            merged.append(_copy_step(step))
    return merged


def _step_name(step: Step, english: bool, end: str) -> str:
    if english:
        value = getattr(step, f'{end}_name_en') or getattr(step, f'{end}_name')
    else:
        value = getattr(step, f'{end}_name') or getattr(step, f'{end}_name_en')
    return value


def route_flight_points(route, lang: str = 'es') -> list:
    """Puntos de vuelo usados por la ruta, en orden y sin repetir."""
    if route is None:
        return []
    spanish = lang in ('es', 'esES', 'esMX')
    names = []
    for step in route.steps:
        if step.kind != KIND_FLIGHT:
            continue
        for end in ('from', 'to'):
            name = _step_name(step, not spanish, end)
            if name and name not in names:
                names.append(name)
    return names


def describe(route, lang: str) -> str:
    """Una línea con los tramos y el tiempo aproximado de la ruta."""
    if route is None or not route.steps:
        return ''
    spanish = lang in ('es', 'esES', 'esMX')
    labels = KIND_LABELS['es' if spanish else 'en']
    steps = _merge_walks(route.steps)
    parts = [_step_name(steps[0], not spanish, 'from')]
    for step in steps:
        label = labels.get(step.kind, step.kind)
        if step.seen_in_game:
            label += ', visto en el juego' if spanish else ', seen in the game'
        parts.append(f'({label}) {_step_name(step, not spanish, "to")}')
    minutes = max(0, int(round(route.seconds / 60)))
    time_label = 'Tiempo aproximado' if spanish else 'Approximate time'
    return ' -> '.join(parts) + f'. {time_label}: {minutes} min.'
