"""Compara el orden de talentos de una build con los puntos del personaje."""

from __future__ import annotations

from askforever.data.wowdb import normalize

FIRST_TALENT_LEVEL = 10
MAX_LEVEL = 60


def _int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _display(row) -> str:
    return str(row.get('talento_es') or row.get('talento_en') or '').strip()


def _talents(order):
    """Nombre normalizado -> talento de la build, con sus pasos y su rango máximo."""
    talents = {}
    for row in order or ():
        if not isinstance(row, dict):
            continue
        nivel = _int(row.get('nivel'))
        rango = _int(row.get('rango'))
        key = normalize(row.get('talento_en')) or normalize(row.get('talento_es'))
        if nivel <= 0 or rango <= 0 or not key:
            continue
        talent = talents.setdefault(key, {
            'name': _display(row), 'max_rank': 0, 'steps': []})
        if not talent['name']:
            talent['name'] = _display(row)
        talent['max_rank'] = max(talent['max_rank'], rango)
        talent['steps'].append((nivel, rango))
    return talents


def _aliases(order, by_key):
    """Nombre normalizado (español o inglés) -> clave del talento."""
    aliases = {}
    for row in order or ():
        if not isinstance(row, dict):
            continue
        key = normalize(row.get('talento_en')) or normalize(row.get('talento_es'))
        if key not in by_key:
            continue
        for name in (row.get('talento_es'), row.get('talento_en')):
            normalized = normalize(name)
            if normalized:
                aliases.setdefault(normalized, key)
    return aliases


def next_talent_steps(order, spent, level, limit: int = 3):
    """Puntos que faltan, sobran o tocan según el orden de la build.

    `order` son las filas de WowDb.talent_order y `spent` la lista [[talento, rango], ...]
    del perfil del addon. Con el personaje fuera de ruta no se inventan pasos.
    """
    by_key = _talents(order)
    aliases = _aliases(order, by_key)
    try:
        limit = max(0, int(limit))
    except (TypeError, ValueError):
        limit = 3

    points = {}
    off_route = False
    for entry in spent or ():
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        rank = _int(entry[1])
        normalized = normalize(entry[0])
        if rank <= 0 or not normalized:
            continue
        key = aliases.get(normalized)
        if key is None:
            off_route = True
            continue
        points[key] = points.get(key, 0) + rank
        if points[key] > by_key[key]['max_rank']:
            off_route = True

    cap = min(max(_int(level), 0), MAX_LEVEL)
    expected_ranks = {}
    for key, talent in by_key.items():
        reached = max((rango for nivel, rango in talent['steps'] if nivel <= cap),
                      default=0)
        if reached:
            expected_ranks[key] = reached

    ahead = []
    behind = []
    for key, talent in by_key.items():
        have = points.get(key, 0)
        want = expected_ranks.get(key, 0)
        if have > want:
            ahead.append(talent['name'])
        elif have < want:
            behind.append(talent['name'])

    next_steps = []
    if not off_route:
        for key, talent in by_key.items():
            have = points.get(key, 0)
            for nivel, rango in talent['steps']:
                if nivel <= cap and rango > have:
                    next_steps.append({
                        'nivel': nivel, 'talento': talent['name'], 'rango': rango})
    next_steps.sort(key=lambda step: (step['nivel'], step['rango'], normalize(step['talento'])))

    expected = {by_key[key]['name']: rank for key, rank in expected_ranks.items()}
    return {
        'expected': expected,
        'ahead': sorted(ahead, key=normalize),
        'behind': sorted(behind, key=normalize),
        'off_route': off_route,
        'next': next_steps[:limit],
    }
