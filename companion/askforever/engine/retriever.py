"""Recuperación determinista de datos verificados de WoW para el prompt."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from askforever.data.routes import (KIND_FLIGHT, KIND_TRAM, KIND_TRANSPORT, RouteGraph,
                                    _walk_neighbors, describe, find_route,
                                    flight_point_near, resolve_place,
                                    route_flight_points, transport_between)
from askforever.data.wowdb import CLASSES, class_mask_from_name, normalize

LIMIT = 1600
MAX_OBJECTIVE = 220

SPELL_KEYWORDS = ('aprend', 'hechiz', 'habilidad', 'spell', 'learn', 'abilit')
TRAINER_KEYWORDS = ('instructor', 'instructora', 'entrenador', 'trainer')
FLIGHT_KEYWORDS = ('vuelo', 'volar', 'grifo', 'maestro de vuelo', 'flight', 'fly',
                   'gryphon')
TALENT_KEYWORDS = ('talento', 'rama', 'especializ', 'talent', 'spec', 'tree')
LIST_KEYWORDS = ('mi lista', 'mis misiones', 'mi registro', 'my quests', 'my list',
                 'quest log')
BOSS_KEYWORDS = ('jefe', 'jefes', 'boss', 'bosses')
FINAL_KEYWORDS = ('final', 'ultimo', 'last')
DUNGEON_KEYWORDS = ('mazmorra', 'mazmorras', 'instancia', 'instancias', 'dungeon',
                    'dungeons')
ZONE_KEYWORDS = ('subir de nivel', 'levear', 'zonas', 'zona para mi nivel',
                 'where to level', 'level up', 'zones')
TRAVEL_PHRASES = (
    'como voy', 'como llego', 'como ir', 'como puedo ir', 'como puedo llegar',
    'como se va', 'como se llega', 'de aqui a', 'desde aqui', 'ir a ', 'ir de ',
    'llegar a', 'viajar a', 'lo mas rapido', 'mas rapido a', 'ruta', 'camino a',
    'how do i get', 'how can i get', 'how to get', 'fastest way', 'route',
    'travel to', 'from here', 'get to ',
)
TRANSPORT_KEYWORDS = ('barco', 'barcos', 'zepelin', 'tranvia', 'ferry',
                      'transbordador', 'boat', 'ship', 'zeppelin', 'tram')
PLACE_PATTERNS = (
    r'\bde\s+(.+?)\s+a\s+(.+?)(?:\?|$|\.)',
    r'\bdesde\s+(.+?)\s+hasta\s+(.+?)(?:\?|$|\.)',
    r'\bfrom\s+(.+?)\s+to\s+(.+?)(?:\?|$|\.)',
)
PLACE_STOP_WORDS = {
    'de', 'a', 'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'al',
    'del', 'y', 'e', 'o', 'u', 'the', 'to', 'from', 'and', 'of', 'in', 'at',
    'como', 'puedo', 'puede', 'ir', 'voy', 'va', 'llego', 'llega', 'se',
    'viajar', 'camino', 'ruta', 'lo', 'mas', 'rapido', 'rapida', 'posible',
    'que', 'hay', 'barco', 'barcos', 'zepelin', 'tranvia', 'ferry',
    'transbordador', 'boat', 'ship', 'zeppelin', 'tram', 'directo', 'saber',
    'sabes', 'si', 'no', 'how', 'do', 'i', 'get', 'can', 'fastest', 'way',
    'travel', 'route', 'where', 'what', 'when', 'which', 'is', 'it', 'there',
}
HERE_WORDS = {'aqui', 'aca', 'here', 'donde estoy', 'mi posicion'}
FLIGHT_GAIN_SECONDS = 60
PRICE_KEYWORDS = ('cuanto cuesta', 'precio', 'how much')
FLY_FROM_KEYWORDS = ('volar desde', 'adonde puedo volar', 'vuelos desde',
                     'where can i fly')
# Nombres genéricos que aparecen como palabras normales en las preguntas
# (p. ej. «puntos» en «puntos de vuelo») y no deben tratarse como entidades.
GENERIC_ENTITY_NAMES = {'puntos', 'points'}
QUEST_REFERENCE_STOP_WORDS = {
    'mision', 'misiones', 'quest', 'quests', 'donde', 'adonde', 'esta',
    'estan', 'este', 'estos', 'estas', 'esos', 'esas', 'aquel', 'aquella',
    'como', 'consigo', 'encuentro', 'encuentra', 'encuentran', 'encontramos',
    'encontrar', 'conseguir', 'objeto',
    'objetos', 'item', 'items', 'cosa', 'cosas', 'npc', 'pnj', 'tira',
    'tiran', 'suelta', 'sueltan', 'lleva', 'llevan', 'matar', 'mato',
    'kill', 'drop', 'drops', 'where', 'find', 'para', 'pero', 'tengo',
    'hacer', 'hago', 'sale', 'salen', 'zona', 'aqui', 'alli', 'cual',
    'cuales', 'quien', 'quienes', 'what', 'which', 'with', 'from', 'that',
    'this', 'those', 'these', 'have', 'need', 'does', 'get', 'the', 'and',
    'algun', 'alguna', 'algunos', 'algunas', 'tambien', 'solo', 'sabes',
    'saber', 'dime', 'decir', 'puedo', 'puede', 'pueden', 'debo', 'debe',
    'tiene', 'tienen', 'hay', 'ser', 'son', 'fue', 'era', 'cuando',
    'cuanto', 'cuanta', 'cuantos', 'cuantas', 'desde', 'hasta', 'sobre',
    'entre', 'menos', 'ahora', 'entonces', 'porque', 'pues', 'unos', 'unas',
    'objetivo', 'objetivos', 'creature', 'creatures', 'mob', 'mobs',
    'npcs', 'thing', 'things', 'who', 'whom', 'whose', 'why', 'when',
    'could', 'should', 'would', 'were', 'been', 'being', 'about', 'some',
    'any', 'there', 'here', 'your', 'they', 'their', 'then', 'than',
    'also', 'just', 'only', 'please', 'tell', 'know', 'look', 'looking',
    'want', 'give', 'gives', 'take', 'takes', 'kills', 'loot', 'loots',
    'spawn', 'spawns', 'located', 'location', 'zone',
}
EXCLUSION_PHRASES = ('que no sea', 'que no sean', 'excepto', 'menos', 'salvo',
                     'aparte de', 'other than', 'except', 'not ')
PANORAMA_ZONES = 6
PANORAMA_DUNGEONS = 5
PROFESSION_KEYWORDS = (
    'pesca', 'pescar', 'pescador', 'primeros auxilios', 'cocina', 'cocinar',
    'desuello', 'desollar', 'mineria', 'minar', 'herboristeria', 'alquimia',
    'herreria', 'ingenieria', 'encantamiento', 'peleteria', 'sastreria',
    'profesion', 'profesiones', 'fishing', 'first aid', 'cooking', 'skinning',
    'mining', 'herbalism', 'alchemy', 'blacksmithing', 'engineering',
    'enchanting', 'leatherworking', 'tailoring', 'profession', 'professions',
)


def is_profession_question(text) -> bool:
    """True si la pregunta trata de una profesión y no de hechizos de clase."""
    normalized = normalize(text)
    return any(keyword in normalized for keyword in PROFESSION_KEYWORDS)


@dataclass
class Facts:
    """Datos verificados para el prompt, con sus fuentes y sus huecos."""

    lines: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    panorama: list[str] = field(default_factory=list)

    def render(self, lang: str) -> str:
        """Bloque de texto plano, o cadena vacía si no hay nada que contar."""
        spanish = lang in ('esES', 'esMX')
        if not self.lines and not self.missing and not self.panorama:
            return ''
        title = ('DATOS VERIFICADOS (base de WoW Forever):' if spanish
                 else 'VERIFIED DATA (WoW Forever database):')
        segments = [title] + list(self.lines)
        if self.missing:
            segments.append('SIN DATOS EN LA BASE:' if spanish
                            else 'NOT IN THE DATABASE:')
            segments.extend(self.missing)
        # El panorama va al final para que el recorte por tamaño lo quite primero.
        segments.extend(self.panorama)
        text = '\n'.join(segments)
        if len(text) <= LIMIT:
            return text
        cut = text[:LIMIT - 1]
        newline = cut.rfind('\n')
        if newline > 0:
            cut = cut[:newline]
        else:
            space = cut.rfind(' ')
            if space > 0:
                cut = cut[:space]
        return cut.rstrip() + '…'


def _class_name(mask, lang: str) -> str:
    data = CLASSES.get(mask) or {}
    if lang == 'es':
        return data.get('masculine') or ''
    return data.get('english') or ''


def _entity_name(entity) -> str:
    name = entity.get('name') or ''
    sub_name = (entity.get('sub_name') or '').strip()
    return f'{name} ({sub_name})' if sub_name else name


def _location_text(location) -> str:
    if not isinstance(location, dict):
        return ''
    zone = location.get('zone') or ''
    x = location.get('x')
    y = location.get('y')
    if zone and x is not None and y is not None:
        return f'{zone} ({x}, {y})'
    return zone or ''


def _add_source(facts: Facts, source: str) -> None:
    if source not in facts.sources:
        facts.sources.append(source)


def _safe(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception:
        return None


def _level_text(low, high, lang: str) -> str:
    if low == high:
        return f'nivel {low}' if lang == 'es' else f'level {low}'
    return f'niveles {low}-{high}' if lang == 'es' else f'levels {low}-{high}'


def _quest_line(quest, lang: str, details=None) -> str:
    name = quest.get('name') or ''
    level = quest.get('level')
    required = quest.get('required_level')
    starters = [item for item in quest.get('starters') or [] if item.get('locations')]
    finishers = [item for item in quest.get('finishers') or [] if item.get('locations')]
    objectives = quest.get('objective_items') or []
    variants = quest.get('variants') or 1

    parts = []
    if lang == 'es':
        if starters:
            parts.append(f'la da {_entity_name(starters[0])} en '
                         f'{_location_text(starters[0]["locations"][0])}')
        if finishers:
            parts.append(f'se entrega a {_entity_name(finishers[0])} en '
                         f'{_location_text(finishers[0]["locations"][0])}')
        text = f'Misión «{name}» (nivel {level}, requiere {required})'
        if parts:
            text += ': ' + '; '.join(parts) + '.'
        else:
            text += '.'
        if objectives:
            text += ' Objetivos: ' + ', '.join(objectives) + '.'
        if details:
            xp = details.get('xp')
            if xp:
                text += f' Da {xp} de experiencia.'
            quest_objectives = details.get('objectives') or []
            if quest_objectives:
                objective = str(quest_objectives[0])[:MAX_OBJECTIVE]
                text += f' Objetivo: {objective}'
        if variants > 1:
            text += f' (hay {variants} misiones con ese nombre)'
        return text

    if starters:
        parts.append(f'given by {_entity_name(starters[0])} in '
                     f'{_location_text(starters[0]["locations"][0])}')
    if finishers:
        parts.append(f'turned in to {_entity_name(finishers[0])} in '
                     f'{_location_text(finishers[0]["locations"][0])}')
    text = f'Quest "{name}" (level {level}, requires {required})'
    if parts:
        text += ': ' + '; '.join(parts) + '.'
    else:
        text += '.'
    if objectives:
        text += ' Objectives: ' + ', '.join(objectives) + '.'
    if details:
        xp = details.get('xp')
        if xp:
            text += f' Gives {xp} XP.'
        quest_objectives = details.get('objectives') or []
        if quest_objectives:
            objective = str(quest_objectives[0])[:MAX_OBJECTIVE]
            text += f' Objective: {objective}'
    if variants > 1:
        text += f' (there are {variants} quests with that name)'
    return text


def _dungeon_line(dungeon, lang: str, levels=None) -> str:
    name = dungeon.get('name') or ''
    entrances = dungeon.get('entrances') or []
    if lang == 'es':
        if entrances:
            text = f'Mazmorra «{name}»: entrada en {_location_text(entrances[0])}'
        else:
            text = f'Mazmorra «{name}»: sin entrada conocida'
        if levels:
            text += ', ' + _level_text(levels[0], levels[1], lang)
        return text + '.'
    if entrances:
        text = f'Dungeon "{name}": entrance in {_location_text(entrances[0])}'
    else:
        text = f'Dungeon "{name}": no known entrance'
    if levels:
        text += ', ' + _level_text(levels[0], levels[1], lang)
    return text + '.'


def _boss_line(bosses, lang: str, with_final: bool) -> str:
    name = bosses.get('name') or ''
    names = bosses.get('bosses') or []
    if not names:
        return ''
    if lang == 'es':
        text = f'Jefes de {name}, en orden: ' + ', '.join(names)
        if with_final:
            text += f'. Jefe final: {names[-1]}'
    else:
        text = f'Bosses of {name}, in order: ' + ', '.join(names)
        if with_final:
            text += f'. Final boss: {names[-1]}'
    return text + '.'


def _zone_line(levels, lang: str) -> str:
    if lang == 'es':
        return (f"Zona {levels['name']}: niveles {levels['min']}-{levels['max']} "
                '(deducido de los enemigos de la zona).')
    return (f"Zone {levels['name']}: levels {levels['min']}-{levels['max']} "
            '(inferred from the zone enemies).')


def _zones_line(zones, level, lang: str) -> str:
    parts = [f"{zone['name']} ({zone['min']}-{zone['max']})" for zone in zones]
    if lang == 'es':
        return f'Zonas para nivel {level}: ' + ', '.join(parts)
    return f'Zones for level {level}: ' + ', '.join(parts)


def _dungeons_line(dungeons, level, lang: str) -> str:
    parts = [f"{item['name']} ({item['min']}-{item['max']})" for item in dungeons]
    if lang == 'es':
        return f'Mazmorras cerca de tu nivel: ' + ', '.join(parts)
    return f'Dungeons near your level: ' + ', '.join(parts)


def _wings_line(wings, lang: str) -> str:
    parts = [f"{wing['name']} {wing['min']}-{wing['max']}" for wing in wings]
    return ('Alas: ' if lang == 'es' else 'Wings: ') + ', '.join(parts)


def _npc_line(npc, lang: str) -> str:
    name = _entity_name(npc)
    places = '; '.join(_location_text(location)
                       for location in (npc.get('locations') or [])[:2])
    if lang == 'es':
        return f'PNJ {name}: {places}.' if places else f'PNJ {name}: sin posiciones conocidas.'
    return f'NPC {name}: {places}.' if places else f'NPC {name}: no known positions.'


def _item_line(item, lang: str) -> str:
    name = item.get('name') or ''
    parts = []
    vendors = item.get('vendors') or []
    if vendors:
        label = 'vendedores' if lang == 'es' else 'vendors'
        parts.append(f"{label}: " + ', '.join(
            vendor.get('npc') or '' for vendor in vendors))
    drops = item.get('drops') or []
    if drops:
        label = 'botín' if lang == 'es' else 'drops'
        pieces = []
        for drop in drops:
            npc = drop.get('npc') or ''
            place = _location_text(drop)
            rate = drop.get('rate')
            if place:
                npc = npc + (' en ' if lang == 'es' else ' in ') + place
            pieces.append(f'{npc} ({rate} %)' if rate is not None else npc)
        parts.append(f'{label}: ' + ', '.join(pieces))
    objects = item.get('objects') or []
    if objects:
        label = 'se recoge de' if lang == 'es' else 'gathered from'
        pieces = []
        for obj in objects:
            object_name = obj.get('object') or ''
            place = _location_text(obj)
            if place:
                object_name = object_name + (' en ' if lang == 'es' else ' in ') + place
            pieces.append(object_name)
        parts.append(f'{label}: ' + ', '.join(pieces))
    rewards = item.get('quest_rewards') or []
    if rewards:
        label = 'recompensas' if lang == 'es' else 'rewards'
        parts.append(f'{label}: ' + ', '.join(rewards))
    if lang == 'es':
        prefix = f'Objeto «{name}»'
        if parts:
            return prefix + ': ' + '; '.join(parts) + '.'
        return prefix + ': sin fuentes conocidas.'
    prefix = f'Item "{name}"'
    if parts:
        return prefix + ': ' + '; '.join(parts) + '.'
    return prefix + ': no known sources.'


def _entry_quest_id(entry):
    if not isinstance(entry, (list, tuple)) or len(entry) < 4:
        return None
    value = entry[3]
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        quest_id = value
    elif isinstance(value, float) and value.is_integer():
        quest_id = int(value)
    else:
        return None
    return quest_id if quest_id > 0 else None


def _active_quest_ids(ctx):
    if not isinstance(ctx, dict):
        return []
    quests = ctx.get('quests')
    if not isinstance(quests, list):
        return []
    ids = []
    for entry in quests:
        quest_id = _entry_quest_id(entry)
        if quest_id is not None and quest_id not in ids:
            ids.append(quest_id)
    return ids


def _add_quest_facts(facts: Facts, db, quest, lang: str, ctx: dict) -> None:
    details = _safe(db.quest_details, quest['id'], lang)
    facts.lines.append(_quest_line(quest, lang, details))
    _add_source(facts, f'quest:{quest["id"]}')
    objective_ids = quest.get('objective_item_ids') or []
    for item_id in objective_ids[:3]:
        if f'item:{item_id}' in facts.sources:
            continue
        item = _safe(db.item_sources, item_id, lang)
        if item is None:
            continue
        facts.lines.append(_item_line(item, lang))
        _add_source(facts, f'item:{item["id"]}')
    quest_name = quest.get('name') or ''
    creatures = quest.get('objective_creatures') or []
    for creature in creatures[:3]:
        npc_id = creature.get('id')
        source = f'npc:{npc_id}'
        if source in facts.sources:
            continue
        locations = _safe(db.npc_locations, npc_id, 2, lang)
        name = creature.get('name') or ''
        places = [_location_text(location) for location in (locations or [])]
        places = [place for place in places if place]
        if lang == 'es':
            line = f'Objetivo de la misión «{quest_name}»: matar {name}'
            if places:
                line += ' en ' + '; '.join(places) + '.'
            else:
                line += ' (ubicación desconocida en la base).'
        else:
            line = f'Quest «{quest_name}» objective: kill {name}'
            if places:
                line += ' in ' + '; '.join(places) + '.'
            else:
                line += ' (location not in the database).'
        facts.lines.append(line)
        _add_source(facts, source)


def _reference_tokens(value):
    if not isinstance(value, str):
        return []
    return [token for token in re.findall(r'[a-z0-9]+', normalize(value))
            if len(token) >= 4 and token not in QUEST_REFERENCE_STOP_WORDS]


def _token_matches(question_token, vocabulary_token):
    if question_token == vocabulary_token:
        return True
    shorter, longer = ((question_token, vocabulary_token)
                       if len(question_token) <= len(vocabulary_token)
                       else (vocabulary_token, question_token))
    return len(shorter) >= 5 and longer.startswith(shorter)


def _detect_entities(facts: Facts, db, matches, normalized: str, lang: str, ctx: dict):
    player_level = ctx.get('lvl')
    active_ids = _active_quest_ids(ctx)
    wants_final = any(word in normalized for word in FINAL_KEYWORDS)
    wants_bosses = (any(word in normalized for word in BOSS_KEYWORDS)
                    or wants_final)
    has_dungeon = False
    dungeon_level_answered = False
    for match in matches:
        kind = match.get('kind')
        entity_id = match.get('id')
        if normalize(match.get('name') or '') in GENERIC_ENTITY_NAMES:
            continue
        if kind == 'quest':
            lookup = match.get('name') if active_ids else entity_id
            quest = db.find_quest(lookup or entity_id, lang,
                                  player_level=player_level,
                                  prefer_ids=active_ids)
            if quest is None and active_ids and lookup != entity_id:
                quest = db.find_quest(entity_id, lang, player_level=player_level,
                                      prefer_ids=active_ids)
            if quest is None:
                continue
            _add_quest_facts(facts, db, quest, lang, ctx)
        elif kind == 'dungeon':
            has_dungeon = True
            dungeon = db.dungeon(entity_id, lang)
            if dungeon is None:
                continue
            levels = None
            level_data = _safe(db.dungeon_level, entity_id, lang)
            if level_data:
                levels = (level_data['min'], level_data['max'])
                dungeon_level_answered = True
                _add_source(facts, f'dungeon_level:{entity_id}')
            facts.lines.append(_dungeon_line(dungeon, lang, levels))
            _add_source(facts, f'dungeon:{dungeon["id"]}')
            if level_data and level_data.get('wings'):
                facts.lines.append(_wings_line(level_data['wings'], lang))
            if wants_bosses:
                bosses = _safe(db.dungeon_bosses, entity_id, lang)
                if bosses:
                    facts.lines.append(_boss_line(bosses, lang, wants_final))
                    _add_source(facts, f'bosses:{entity_id}')
        elif kind == 'npc':
            npc = db.find_npc(entity_id, lang)
            if npc is None:
                continue
            facts.lines.append(_npc_line(npc, lang))
            _add_source(facts, f'npc:{npc["id"]}')
        elif kind == 'item':
            item = db.item_sources(entity_id, lang)
            if item is None:
                continue
            facts.lines.append(_item_line(item, lang))
            _add_source(facts, f'item:{item["id"]}')
    return has_dungeon, dungeon_level_answered


def _detect_active_quest_reference(facts: Facts, db, question, normalized: str,
                                   lang: str, ctx: dict, matches) -> None:
    if any(isinstance(match, dict) and match.get('kind') == 'quest'
           for match in (matches or [])):
        return
    # «¿Cómo voy a Ventormenta?» no debe arrastrar «Un envío para Ventormenta»: los viajes
    # los resuelve el grafo de rutas.
    if is_travel_question(question if isinstance(question, str) else ''):
        return
    if not isinstance(ctx, dict):
        return
    entries = ctx.get('quests')
    if not isinstance(entries, list) or not entries:
        return

    active_ids = _active_quest_ids(ctx)
    candidates = []
    for entry in entries[:30]:
        if not isinstance(entry, (list, tuple)) or not entry:
            continue
        quest_id = _entry_quest_id(entry)
        title = entry[0] if isinstance(entry[0], str) else ''
        level = entry[1] if len(entry) > 1 else None
        if quest_id is not None:
            quest = _safe(db.find_quest, quest_id, lang)
        elif title:
            quest = _safe(db.find_quest, title, lang, player_level=level,
                          prefer_ids=active_ids)
        else:
            continue
        if isinstance(quest, dict):
            candidates.append(quest)
    if not candidates:
        return

    question_tokens = _reference_tokens(normalized)
    if not question_tokens:
        return

    vocabularies = []
    for quest in candidates:
        vocabulary = {}

        def add(value, source):
            for token in _reference_tokens(value):
                vocabulary.setdefault(token, set()).add(source)

        add(quest.get('name'), 'name')
        items = quest.get('objective_items')
        if isinstance(items, (list, tuple)):
            for item in items:
                add(item, 'item')
        creatures = quest.get('objective_creatures')
        if isinstance(creatures, (list, tuple)):
            for creature in creatures:
                if isinstance(creature, dict):
                    add(creature.get('name'), 'creature')
        vocabularies.append(vocabulary)

    unique_tokens = set(question_tokens)
    common_tokens = set()
    for token in unique_tokens:
        matched_quests = 0
        for vocabulary in vocabularies:
            if any(_token_matches(token, candidate_token)
                   for candidate_token in vocabulary):
                matched_quests += 1
        if matched_quests >= 3:
            common_tokens.add(token)
    scored_tokens = [token for token in unique_tokens
                     if token not in common_tokens]
    if not scored_tokens:
        return

    scored = []
    for quest, vocabulary in zip(candidates, vocabularies):
        score = 0
        for token in scored_tokens:
            if any(_token_matches(token, candidate_token)
                   for candidate_token in vocabulary):
                score += 1
        if score > 0:
            scored.append((score, quest))
    if not scored:
        return

    best = max(score for score, _quest in scored)
    selected = [quest for score, quest in scored if score == best]
    if len(selected) > 2:
        return
    for quest in selected:
        name = quest.get('name') or ''
        if lang == 'es':
            facts.lines.append(
                f'La pregunta parece referirse a tu misión activa «{name}».')
        else:
            facts.lines.append(
                f'The question seems to refer to your active quest «{name}».')
        _add_quest_facts(facts, db, quest, lang, ctx)


def _ctx_level(ctx: dict):
    level = ctx.get('lvl')
    if isinstance(level, bool):
        return None
    if isinstance(level, (int, float)):
        return int(level)
    if isinstance(level, str) and level.strip().isdigit():
        return int(level.strip())
    return None


def _number_in_text(normalized: str):
    numbers = re.findall(r'\b(60|[1-5]\d|[1-9])\b', normalized)
    if numbers:
        return int(numbers[0])
    return None


def _has_exclusion(normalized: str) -> bool:
    return any(phrase in normalized for phrase in EXCLUSION_PHRASES)


def _partial_zone_match(name: str, tokens) -> bool:
    """True si algún token de la pregunta (5+ letras) empieza una palabra de la zona."""
    for word in normalize(name).split():
        for token in tokens:
            if word.startswith(token):
                return True
    return False


def _excluded_zones(matches, nearby, normalized: str):
    """Zonas que el jugador descarta: coincidencia completa y por prefijo."""
    if not _has_exclusion(normalized):
        return set(), set(), []
    tokens = [token for token in normalized.split() if len(token) >= 5]
    if not tokens:
        return set(), set(), []
    excluded_ids = set()
    excluded_keys = set()
    names = []

    def add(area_id, name):
        key = normalize(name)
        if not key or key in excluded_keys:
            return
        excluded_keys.add(key)
        if area_id is not None:
            excluded_ids.add(area_id)
        names.append(name)

    for match in matches:
        if match.get('kind') == 'zone':
            add(match.get('id'), match.get('name') or '')
    for zone in nearby or []:
        if _partial_zone_match(zone.get('name') or '', tokens):
            add(zone.get('area_id'), zone.get('name') or '')
    return excluded_ids, excluded_keys, names


def _zone_is_excluded(zone, excluded_ids, excluded_keys) -> bool:
    return (zone.get('area_id') in excluded_ids
            or normalize(zone.get('name') or '') in excluded_keys)


def _panorama_zones_line(zones, level, lang: str) -> str:
    parts = [f"{zone['name']} ({zone['min']}-{zone['max']})" for zone in zones]
    if lang == 'es':
        return f'Zonas para tu nivel ({level}): ' + ', '.join(parts)
    return f'Zones for your level ({level}): ' + ', '.join(parts)


def _panorama_dungeons_line(dungeons, level, lang: str) -> str:
    parts = [f"{item['name']} ({item['min']}-{item['max']})" for item in dungeons]
    if lang == 'es':
        return f'Mazmorras para tu nivel ({level}): ' + ', '.join(parts)
    return f'Dungeons for your level ({level}): ' + ', '.join(parts)


def _add_panorama(facts: Facts, db, lang: str, level, nearby, zones_level,
                  dungeons_level, excluded_ids, excluded_keys,
                  excluded_names) -> None:
    if excluded_names:
        prefix = ('Excluidas a petición del jugador: ' if lang == 'es'
                  else 'Excluded by the player: ')
        facts.panorama.append(prefix + ', '.join(excluded_names))
    if level is None:
        return
    if zones_level != level:
        zones = [zone for zone in nearby
                 if not _zone_is_excluded(zone, excluded_ids, excluded_keys)]
        zones = zones[:PANORAMA_ZONES]
        if zones:
            facts.panorama.append(_panorama_zones_line(zones, level, lang))
            _add_source(facts, f'panorama:zones:{level}')
    if dungeons_level != level:
        dungeons = (_safe(db.dungeons_for_level, level, lang) or [])
        dungeons = dungeons[:PANORAMA_DUNGEONS]
        if dungeons:
            facts.panorama.append(_panorama_dungeons_line(dungeons, level, lang))
            _add_source(facts, f'panorama:dungeons:{level}')


def _detect_zone_intents(facts: Facts, db, matches, normalized: str, lang: str,
                         ctx: dict, nearby, excluded_ids, excluded_keys):
    zone_matches = [match for match in matches if match.get('kind') == 'zone']
    mentions_level = any(word in normalized for word in ('nivel', 'level', 'rango'))
    current_zone = ctx.get('zone')
    if zone_matches and mentions_level:
        levels = _safe(db.zone_levels, zone_matches[0]['id'], lang)
        if levels:
            facts.lines.append(_zone_line(levels, lang))
            _add_source(facts, f"zone:{levels['area_id']}")
            return None
    if (isinstance(current_zone, str) and current_zone and mentions_level
            and normalize(current_zone) in normalized):
        levels = _safe(db.zone_levels, current_zone, lang)
        if levels:
            facts.lines.append(_zone_line(levels, lang))
            _add_source(facts, f"zone:{levels['area_id']}")
            return None
    if zone_matches:
        return None
    if any(phrase in normalized for phrase in ZONE_KEYWORDS):
        level = _ctx_level(ctx)
        if level is None:
            return None
        zones = [zone for zone in nearby
                 if not _zone_is_excluded(zone, excluded_ids, excluded_keys)]
        if zones:
            facts.lines.append(_zones_line(zones, level, lang))
            _add_source(facts, f'zones:{level}')
            return level
    return None


def _detect_dungeon_intents(facts: Facts, db, matches, normalized: str, lang: str,
                            ctx: dict, has_dungeon: bool,
                            dungeon_level_answered: bool):
    mentions_level = any(word in normalized for word in ('nivel', 'level', 'rango'))
    mentions_dungeon = any(word in normalized for word in DUNGEON_KEYWORDS)
    if not has_dungeon and mentions_dungeon:
        wants_list = ('mi nivel' in normalized or 'my level' in normalized
                      or 'puedo hacer' in normalized or 'can i do' in normalized
                      or _number_in_text(normalized) is not None)
        if wants_list:
            level = _number_in_text(normalized)
            if level is None:
                level = _ctx_level(ctx)
            if level is not None:
                dungeons = _safe(db.dungeons_for_level, level, lang)
                if dungeons:
                    facts.lines.append(_dungeons_line(dungeons, level, lang))
                    _add_source(facts, f'dungeons:{level}')
                    return level
    if mentions_level and (has_dungeon or mentions_dungeon) and not dungeon_level_answered:
        facts.missing.append('rangos de nivel de mazmorras' if lang == 'es'
                             else 'dungeon level ranges')
    return None


def _detect_xp(facts: Facts, db, normalized: str, lang: str, ctx: dict,
               has_quest: bool) -> None:
    words = set(normalized.split())
    if not ('experiencia' in normalized or 'experience' in normalized
            or 'xp' in words or 'exp' in words):
        return
    if has_quest:
        return
    target = None
    found = re.search(r'\b(?:nivel|level)\s+(\d{1,2})\b', normalized)
    if found:
        target = int(found.group(1))
    if target is not None and target > 1:
        level = target - 1
        xp = _safe(db.xp_to_next_level, level)
        if xp is not None:
            if lang == 'es':
                facts.lines.append(f'Experiencia para pasar del nivel {level} al '
                                   f'{target}: {xp} (tabla del cliente).')
            else:
                facts.lines.append(f'Experience to go from level {level} to '
                                   f'{target}: {xp} (client table).')
            _add_source(facts, f'xp:{level}')
            return
    else:
        level = _ctx_level(ctx)
        if level is not None:
            xp = _safe(db.xp_to_next_level, level)
            if xp is not None:
                if lang == 'es':
                    facts.lines.append(f'Experiencia para pasar del nivel {level} al '
                                       f'{level + 1}: {xp} (tabla del cliente).')
                else:
                    facts.lines.append(f'Experience to go from level {level} to '
                                       f'{level + 1}: {xp} (client table).')
                _add_source(facts, f'xp:{level}')
                return
    facts.missing.append('experiencia necesaria por nivel' if lang == 'es'
                         else 'experience needed per level')


def _faction(value):
    text = normalize(value)
    if text in ('alianza', 'alliance'):
        return 'A'
    if text in ('horda', 'horde'):
        return 'H'
    return None


def _detect_places(matches, question: str, ctx: dict):
    for pattern in (r'\bde\s+(.+?)\s+a\s+(.+?)(?:\?|$|\.)',
                    r'\bfrom\s+(.+?)\s+to\s+(.+?)(?:\?|$|\.)'):
        found = re.search(pattern, question, re.IGNORECASE)
        if found:
            origin = found.group(1).strip(' ?!.,¿¡')
            destination = found.group(2).strip(' ?!.,¿¡')
            if origin and destination:
                return origin, destination
    zones = [match.get('name') for match in matches if match.get('kind') == 'zone']
    if len(zones) >= 2:
        return zones[0], zones[1]
    if len(zones) == 1:
        return (ctx.get('zone') or ''), zones[0]
    return (ctx.get('zone') or ''), ''


def is_travel_question(text) -> bool:
    """True si la pregunta pide cómo ir o llegar a un lugar."""
    normalized = normalize(text)
    return any(phrase in normalized for phrase in TRAVEL_PHRASES)


def _place_words(node) -> set:
    words = set()
    for value in (node.place, node.zone, node.place_en, node.zone_en):
        words |= {word for word in normalize(value).split() if len(word) >= 5}
    return words


def _place_matches(graph, phrase: str) -> bool:
    target = normalize(phrase)
    if not target:
        return False
    for node in resolve_place(graph, phrase):
        names = (node.zone, node.zone_en, normalize(node.place),
                 normalize(node.place_en))
        if target in names:
            return True
        if len(target) >= 5 and any(
                word.startswith(target) for word in _place_words(node)):
            return True
    return False


def _clean_place(graph, text: str) -> str:
    tokens = re.findall(r'[^\W\d_]+', text or '', re.UNICODE)
    for start in range(len(tokens)):
        for length in range(min(4, len(tokens) - start), 0, -1):
            phrase = ' '.join(tokens[start:start + length])
            if _place_matches(graph, phrase):
                return phrase
    return ''


def _ngram_places(graph, text: str) -> list:
    tokens = re.findall(r'[^\W\d_]+', text or '', re.UNICODE)
    places = []
    index = 0
    while index < len(tokens):
        token = normalize(tokens[index])
        if token in PLACE_STOP_WORDS or len(token) < 2:
            index += 1
            continue
        matched = None
        for length in range(min(4, len(tokens) - index), 0, -1):
            phrase = ' '.join(tokens[index:index + length])
            if _place_matches(graph, phrase):
                matched = (phrase, length)
                break
        if matched:
            places.append(matched[0])
            index += matched[1]
        else:
            index += 1
    return places


def _is_here(text: str) -> bool:
    return normalize(text) in HERE_WORDS


def _ctx_origin(graph, ctx: dict) -> str:
    sub = ctx.get('sub')
    if isinstance(sub, str) and sub.strip() and resolve_place(graph, sub):
        return sub.strip()
    zone = ctx.get('zone')
    if isinstance(zone, str) and zone.strip():
        return zone.strip()
    return ''


def extract_places(graph, text: str, ctx: dict):
    """Saca (origen, destino) de la pregunta, o ('', '') si no los reconoce."""
    if graph is None:
        return '', ''
    for pattern in PLACE_PATTERNS:
        found = re.search(pattern, text or '', re.IGNORECASE)
        if found:
            raw_origin = found.group(1)
            origin = (_ctx_origin(graph, ctx) if _is_here(raw_origin)
                      else _clean_place(graph, raw_origin))
            destination = _clean_place(graph, found.group(2))
            return origin, destination
    places = _ngram_places(graph, text)
    if len(places) >= 2:
        return places[0], places[1]
    if len(places) == 1:
        return _ctx_origin(graph, ctx), places[0]
    return '', ''


def _route_graph(db, ctx: dict):
    faction = _faction(ctx.get('fac'))
    return _safe(RouteGraph.build, db, faction)


def _known_flights(ctx: dict):
    fp = ctx.get('fp')
    if not isinstance(fp, list):
        return None
    return {value for value in fp
            if isinstance(value, int) and not isinstance(value, bool)}


def _flight_node_lookup(graph) -> dict:
    lookup = {}
    for node in graph.nodes.values():
        if not node.taxi_id:
            continue
        lookup.setdefault(node.name, node)
        lookup.setdefault(node.name_en, node)
    return lookup


def _missing_flight_points(graph, route, known, lang: str) -> list:
    if route is None or known is None:
        return []
    lookup = _flight_node_lookup(graph)
    names = []
    for step in route.steps:
        if step.kind != KIND_FLIGHT:
            continue
        for name, name_en in ((step.from_name, step.from_name_en),
                              (step.to_name, step.to_name_en)):
            node = lookup.get(name) or lookup.get(name_en)
            if node is None or not node.taxi_id or node.taxi_id in known:
                continue
            label = ((node.name_en or node.name) if lang != 'es'
                     else (node.name or node.name_en))
            if label and label not in names:
                names.append(label)
    return names


def _position_route_needed(graph, ctx_origin: str, origin: str) -> bool:
    if not ctx_origin or normalize(origin) == normalize(ctx_origin):
        return False
    origin_nodes = resolve_place(graph, origin)
    ctx_nodes = resolve_place(graph, ctx_origin)
    if not origin_nodes or not ctx_nodes:
        return False
    origin_keys = {node.key for node in origin_nodes}
    ctx_keys = {node.key for node in ctx_nodes}
    if origin_keys & ctx_keys:
        return False
    if _walk_neighbors(graph, origin_keys) & ctx_keys:
        return False
    if _walk_neighbors(graph, ctx_keys) & origin_keys:
        return False
    return True


def _detect_route(facts: Facts, graph, question: str, lang: str, ctx: dict) -> bool:
    if not is_travel_question(question):
        return False
    origin, destination = extract_places(graph, question, ctx) if graph else ('', '')
    if not origin or not destination:
        facts.missing.append(
            'ruta: no reconozco el origen o el destino en la base'
            if lang == 'es'
            else 'route: origin or destination not recognised in the database')
        return False
    known = _known_flights(ctx)
    route = _safe(find_route, graph, origin, destination, known)
    unrestricted = (_safe(find_route, graph, origin, destination)
                    if known is not None else None)
    missing_points = (_missing_flight_points(graph, unrestricted, known, lang)
                      if known is not None else [])
    ctx_origin = _ctx_origin(graph, ctx)
    if _position_route_needed(graph, ctx_origin, origin):
        position_route = _safe(find_route, graph, ctx_origin, origin, known)
        if position_route is not None:
            description = describe(position_route, 'es' if lang == 'es' else 'en')
            if description:
                if lang == 'es':
                    facts.lines.append(f'Desde tu posición ({ctx_origin}) hasta {origin}: '
                                       f'{description}')
                else:
                    facts.lines.append(f'From your position ({ctx_origin}) to {origin}: '
                                       f'{description}')
                _add_source(facts, f'route:{ctx_origin}>{origin}')
    route_added = False
    if route is not None:
        description = describe(route, 'es' if lang == 'es' else 'en')
        if description:
            if lang == 'es':
                facts.lines.append(f'Ruta más rápida según la base: {description}')
            else:
                facts.lines.append(f'Fastest route according to the database: {description}')
            _add_source(facts, f'route:{origin}>{destination}')
            route_added = True
        else:
            # Origen y destino caen en el mismo punto de la base (están al lado).
            if lang == 'es':
                facts.lines.append(f'De {origin} a {destination} se va a pie, '
                                   'sin vuelo ni transporte.')
            else:
                facts.lines.append(f'From {origin} to {destination} you walk, '
                                   'no flight or transport needed.')
            _add_source(facts, f'route:{origin}>{destination}')
            route_added = True
    if known is not None and unrestricted is not None and missing_points:
        faster = route is None or route.seconds - unrestricted.seconds >= FLIGHT_GAIN_SECONDS
        if faster:
            description = describe(unrestricted, 'es' if lang == 'es' else 'en')
            if description:
                names = ', '.join(missing_points)
                # Solo se puede volar a puntos ya descubiertos: es una ruta para más adelante.
                if lang == 'es':
                    facts.lines.append(
                        f'Aún no tienes los puntos de vuelo {names}; no puedes volar a ellos '
                        f'hasta descubrirlos llegando por tierra. Cuando los tengas: '
                        f'{description}')
                else:
                    facts.lines.append(
                        f'You do not have the flight points {names} yet; you cannot fly '
                        f'there until you discover them by arriving over land. Once you '
                        f'have them: {description}')
    if route is None:
        facts.missing.append(
            f'camino por tierra entre {origin} y {destination} con tus puntos de vuelo '
            '(no está en la base)'
            if lang == 'es' and known is not None and missing_points
            else f'ruta entre {origin} y {destination} (aún no está en la base)'
            if lang == 'es'
            else f'land route between {origin} and {destination} with your flight points '
                 '(not in the database)'
            if known is not None and missing_points
            else f'route between {origin} and {destination} (not in the database yet)')
    if known is None and route is not None:
        names = route_flight_points(route, lang)
        if names:
            joined = ', '.join(names)
            if lang == 'es':
                facts.lines.append(
                    f'Esta ruta usa los puntos de vuelo {joined}; si no los tienes, '
                    'descúbrelos hablando con el maestro de vuelo al llegar. (El addon '
                    'aún no sabe qué puntos de vuelo conoces: abre el mapa de un maestro '
                    'de vuelo para registrarlos.)')
            else:
                facts.lines.append(
                    f'This route uses the flight points {joined}; if you do not have them, '
                    'discover them by talking to the flight master when you arrive. (The '
                    "addon does not know which flight points you have yet: open a flight "
                    "master's map to register them.)")
            ground = _safe(find_route, graph, origin, destination, set())
            ground_text = describe(ground, 'es' if lang == 'es' else 'en') if ground else ''
            if ground_text:
                if lang == 'es':
                    facts.lines.append(f'Sin vuelos: {ground_text}')
                else:
                    facts.lines.append(f'Without flights: {ground_text}')
    if known is not None:
        point = _safe(flight_point_near, graph, destination)
        if point is not None and point.taxi_id not in known:
            name = ((point.name_en or point.name) if lang != 'es'
                    else (point.name or point.name_en))
            if lang == 'es':
                facts.lines.append(
                    f'Al llegar a {destination}, descubre el punto de vuelo de {name}.')
            else:
                facts.lines.append(
                    f'When you arrive at {destination}, discover the {name} flight point.')
    return route_added


def _detect_transport(facts: Facts, graph, question: str, normalized: str,
                      lang: str, ctx: dict) -> None:
    if graph is None or not any(word in normalized for word in TRANSPORT_KEYWORDS):
        return
    origin, destination = extract_places(graph, question, ctx)
    if not origin or not destination:
        return
    steps = _safe(transport_between, graph, origin, destination) or []
    labels = []
    for step in steps:
        if step.kind == KIND_TRANSPORT:
            label = 'barco' if lang == 'es' else 'boat'
        elif step.kind == KIND_TRAM:
            label = 'tranvía' if lang == 'es' else 'tram'
        else:
            continue
        if step.seen_in_game:
            label += ' (visto en el juego)' if lang == 'es' else ' (seen in the game)'
        if label not in labels:
            labels.append(label)
    if labels:
        if lang == 'es':
            facts.lines.append(f'Transporte directo entre {origin} y {destination}: '
                               + ', '.join(labels))
        else:
            facts.lines.append(f'Direct transport between {origin} and {destination}: '
                               + ', '.join(labels))
    else:
        facts.missing.append(
            f'transporte directo entre {origin} y {destination} (no está en la base)'
            if lang == 'es'
            else f'direct transport between {origin} and {destination} '
                 '(not in the database)')


def _detect_flights(facts: Facts, db, matches, question: str, normalized: str,
                    lang: str, ctx: dict, skip_generic: bool = False) -> None:
    faction = _faction(ctx.get('fac'))
    current_zone = ctx.get('zone') if isinstance(ctx.get('zone'), str) else ''
    is_price = any(word in normalized for word in PRICE_KEYWORDS)
    is_fly_from = any(word in normalized for word in FLY_FROM_KEYWORDS)

    if is_price:
        origin, destination = _detect_places(matches, question, ctx)
        if origin and destination:
            cost = _safe(db.flight_cost, origin, destination, faction, lang)
            if cost:
                if lang == 'es':
                    facts.lines.append(f"Vuelo {cost['origin']} -> "
                                       f"{cost['destination']}: {cost['cost']}")
                else:
                    facts.lines.append(f"Flight {cost['origin']} -> "
                                       f"{cost['destination']}: {cost['cost']}")
                _add_source(facts, f"flight_cost:{cost['origin']}->{cost['destination']}")
            else:
                facts.missing.append(f'vuelo directo entre {origin} y {destination}'
                                     if lang == 'es'
                                     else f'direct flight between {origin} and {destination}')
        return

    if is_fly_from:
        zone_matches = [match for match in matches if match.get('kind') == 'zone']
        place = zone_matches[0].get('name') if zone_matches else current_zone
        if not place:
            return
        data = _safe(db.flights_from, place, faction, lang)
        if data and data.get('flights'):
            if lang == 'es':
                text = (f"Vuelos desde {data['origin']}: " + '; '.join(
                    f"{flight['destination']} ({flight['cost']})"
                    for flight in data['flights'][:12]))
            else:
                text = (f"Flights from {data['origin']}: " + '; '.join(
                    f"{flight['destination']} ({flight['cost']})"
                    for flight in data['flights'][:12]))
            facts.lines.append(text)
            _add_source(facts, f"flights_from:{data['origin']}")
        return

    if skip_generic:
        return
    if not any(word in normalized for word in FLIGHT_KEYWORDS):
        return

    continent = _safe(db.zone_continent, ctx.get('zone'))
    if continent is None:
        continent = 0
    points = _safe(db.flight_points, continent, faction, lang) or []
    points = [point for point in points if _flight_name_ok(point.get('name') or '')]
    if not points:
        facts.missing.append('puntos de vuelo para tu facción' if lang == 'es'
                             else 'flight points for your faction')
        return
    current = normalize(current_zone)

    def sort_key(point):
        name = normalize(point.get('name') or '')
        here = 0 if current and current in name else 1
        return (here, point.get('id') or 0)

    points.sort(key=sort_key)
    names = '; '.join(point.get('name') or '' for point in points[:12])
    if lang == 'es':
        facts.lines.append(f'Puntos de vuelo de tu facción en este continente: {names}')
    else:
        facts.lines.append(f"Your faction's flight points on this continent: {names}")
    _add_source(facts, f'flights:{continent}:{faction or "any"}')


def _flight_name_ok(name: str) -> bool:
    normalized = normalize(name)
    if normalized.startswith('zz'):
        return False
    if 'quest path' in normalized:
        return False
    return ':' not in name


def _detect_spells(facts: Facts, db, normalized: str, lang: str, ctx: dict) -> None:
    if is_profession_question(normalized):
        return
    wanted = any(word in normalized for word in SPELL_KEYWORDS)
    if not wanted and 'train' in normalized and 'trainer' not in normalized:
        wanted = True
    if not wanted:
        return
    mask = class_mask_from_name(ctx.get('class'))
    if mask is None:
        return
    level = _spell_level(normalized, ctx)
    if level is None:
        facts.missing.append('nivel del personaje' if lang == 'es'
                             else "character's level")
        return
    spells = db.class_spells(mask, level, level, lang)
    class_name = _class_name(mask, lang)
    names = ', '.join(spell['name'] for spell in spells)
    if lang == 'es':
        if names:
            facts.lines.append(f'Hechizos de {class_name} en el instructor a nivel '
                               f'{level}: {names}')
        else:
            facts.lines.append(f'Ninguno nuevo a nivel {level}')
    else:
        if names:
            facts.lines.append(f'{class_name} spells from the trainer at level '
                               f'{level}: {names}')
        else:
            facts.lines.append(f'None new at level {level}')
    _add_source(facts, f'spells:{mask}:{level}')


def _spell_level(normalized: str, ctx: dict):
    if re.search(r'\b(siguiente|proximo|next)\s+(nivel|level)\b', normalized):
        base = _ctx_level(ctx)
        return base + 1 if base is not None else None
    match = re.search(r'\b(?:nivel|level|lvl)\s*(\d{1,2})\b', normalized)
    if match:
        return int(match.group(1))
    if re.search(r'\ba mi nivel\b|\bmy level\b', normalized):
        return _ctx_level(ctx)
    numbers = re.findall(r'\b(60|[1-5]\d|[1-9])\b', normalized)
    if numbers:
        return int(numbers[0])
    return _ctx_level(ctx)


def _detect_trainers(facts: Facts, db, normalized: str, lang: str, ctx: dict) -> None:
    if is_profession_question(normalized):
        return
    if not any(word in normalized for word in TRAINER_KEYWORDS):
        return
    mask = class_mask_from_name(ctx.get('class'))
    if mask is None:
        return
    faction = _faction(ctx.get('fac'))
    trainers = [trainer for trainer in db.class_trainers(mask, faction, lang)
                if trainer.get('locations')]
    class_name = _class_name(mask, lang)
    if not trainers:
        facts.missing.append(
            f'instructor de {class_name} para tu facción' if lang == 'es'
            else f'{class_name} trainer for your faction')
        return
    current_zone = normalize(ctx.get('zone') or '')

    def sort_key(trainer):
        zones = [normalize(location.get('zone') or '')
                 for location in trainer['locations']]
        here = 0 if current_zone and current_zone in zones else 1
        return (here, zones[0] if zones else '', trainer.get('name') or '')

    trainers.sort(key=sort_key)
    for trainer in trainers[:4]:
        place = _location_text(trainer['locations'][0])
        name = trainer.get('name') or ''
        if lang == 'es':
            facts.lines.append(f'Instructor de {class_name}: {name} en {place}')
        else:
            facts.lines.append(f'{class_name} trainer: {name} in {place}')
    _add_source(facts, f'trainers:{mask}:{faction or "any"}')


def _detect_talents(facts: Facts, db, normalized: str, lang: str, ctx: dict) -> None:
    if not any(word in normalized for word in TALENT_KEYWORDS):
        return
    mask = class_mask_from_name(ctx.get('class'))
    if mask is None:
        return
    trees = db.talent_trees(mask, lang)
    if not trees:
        return
    class_name = _class_name(mask, lang)
    if lang == 'es':
        facts.lines.append(f'Ramas de talentos de {class_name}: ' + ', '.join(trees))
    else:
        facts.lines.append(f'{class_name} talent trees: ' + ', '.join(trees))
    _add_source(facts, f'talents:{mask}')


def _detect_quest_list(facts: Facts, db, normalized: str, lang: str, ctx: dict) -> None:
    if not any(phrase in normalized for phrase in LIST_KEYWORDS):
        return
    quests = ctx.get('quests')
    if not isinstance(quests, list):
        return
    for entry in quests[:8]:
        if not isinstance(entry, (list, tuple)) or not entry:
            continue
        title = entry[0]
        if not isinstance(title, str) or not title.strip():
            continue
        level = entry[1] if len(entry) > 1 else None
        quest = db.find_quest(title, lang, player_level=level)
        if quest is None:
            if lang == 'es':
                facts.lines.append(f'Misión «{title}» (nivel {level}): sin datos en la base')
            else:
                facts.lines.append(f'Quest "{title}" (level {level}): not in the database')
            continue
        starters = [item for item in quest.get('starters') or [] if item.get('locations')]
        finishers = [item for item in quest.get('finishers') or [] if item.get('locations')]
        parts = []
        if starters:
            zone = starters[0]['locations'][0].get('zone') or ''
            if lang == 'es':
                parts.append(f'la da {starters[0].get("name") or ""} en {zone}')
            else:
                parts.append(f'given by {starters[0].get("name") or ""} in {zone}')
        if finishers:
            zone = finishers[0]['locations'][0].get('zone') or ''
            if lang == 'es':
                parts.append(f'se entrega a {finishers[0].get("name") or ""} en {zone}')
            else:
                parts.append(f'turned in to {finishers[0].get("name") or ""} in {zone}')
        level_text = level if level is not None else quest.get('level')
        quest_name = quest.get('name') or title
        if lang == 'es':
            line = f'Misión «{quest_name}» (nivel {level_text})'
        else:
            line = f'Quest "{quest_name}" (level {level_text})'
        if parts:
            line += ': ' + '; '.join(parts)
        details = _safe(db.quest_details, quest['id'], lang)
        if details and details.get('xp'):
            line += (f' da {details["xp"]} de experiencia' if lang == 'es'
                     else f' gives {details["xp"]} XP')
        facts.lines.append(line)
        _add_source(facts, f'quest:{quest["id"]}')


def retrieve(message, db) -> Facts:
    """Recupera datos verificados para la pregunta; nunca lanza."""
    facts = Facts()
    try:
        if db is None or not db.available():
            return facts
        if not isinstance(message, dict):
            return facts
        lang = 'es' if message.get('lang') in ('esES', 'esMX') else 'en'
        ctx = message.get('ctx')
        if not isinstance(ctx, dict):
            ctx = {}
        question = message.get('q')
        if not isinstance(question, str):
            question = ''
        normalized = normalize(question)

        matches = _safe(db.match_entities, question, lang) or []
        level = _ctx_level(ctx)
        nearby = (_safe(db.zones_for_level, level, lang, 8) or []) if level is not None else []
        excluded_ids, excluded_keys, excluded_names = _excluded_zones(
            matches, nearby, normalized)
        has_dungeon, dungeon_level_answered = _detect_entities(
            facts, db, matches, normalized, lang, ctx)
        _detect_active_quest_reference(
            facts, db, question, normalized, lang, ctx, matches)
        has_quest = any(match.get('kind') == 'quest' for match in matches)
        zones_level = _detect_zone_intents(facts, db, matches, normalized, lang, ctx,
                                           nearby, excluded_ids, excluded_keys)
        dungeons_level = _detect_dungeon_intents(facts, db, matches, normalized, lang, ctx,
                                                 has_dungeon, dungeon_level_answered)
        _detect_xp(facts, db, normalized, lang, ctx, has_quest)
        needs_graph = (is_travel_question(question)
                       or any(word in normalized for word in TRANSPORT_KEYWORDS))
        graph = _route_graph(db, ctx) if needs_graph else None
        route_added = _detect_route(facts, graph, question, lang, ctx)
        _detect_transport(facts, graph, question, normalized, lang, ctx)
        _detect_flights(facts, db, matches, question, normalized, lang, ctx,
                        skip_generic=route_added)
        _detect_spells(facts, db, normalized, lang, ctx)
        _detect_trainers(facts, db, normalized, lang, ctx)
        _detect_talents(facts, db, normalized, lang, ctx)
        _detect_quest_list(facts, db, normalized, lang, ctx)
        _add_panorama(facts, db, lang, level, nearby, zones_level, dungeons_level,
                      excluded_ids, excluded_keys, excluded_names)

        facts.lines = list(dict.fromkeys(facts.lines))
        facts.missing = list(dict.fromkeys(facts.missing))
        facts.panorama = list(dict.fromkeys(facts.panorama))
        return facts
    except Exception:
        return Facts()
