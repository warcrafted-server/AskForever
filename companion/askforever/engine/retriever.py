"""Recuperación determinista de datos verificados de WoW para el prompt."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from askforever.data.wowdb import CLASSES, class_mask_from_name, normalize

LIMIT = 1600

SPELL_KEYWORDS = ('aprend', 'hechiz', 'habilidad', 'spell', 'learn', 'abilit')
TRAINER_KEYWORDS = ('instructor', 'instructora', 'entrenador', 'trainer')
FLIGHT_KEYWORDS = ('vuelo', 'volar', 'grifo', 'maestro de vuelo', 'flight', 'fly',
                   'gryphon')
TALENT_KEYWORDS = ('talento', 'rama', 'especializ', 'talent', 'spec', 'tree')
LIST_KEYWORDS = ('mi lista', 'mis misiones', 'mi registro', 'my quests', 'my list',
                 'quest log')
# Nombres genéricos que aparecen como palabras normales en las preguntas
# (p. ej. «puntos» en «puntos de vuelo») y no deben tratarse como entidades.
GENERIC_ENTITY_NAMES = {'puntos', 'points'}


@dataclass
class Facts:
    """Datos verificados para el prompt, con sus fuentes y sus huecos."""

    lines: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def render(self, lang: str) -> str:
        """Bloque de texto plano, o cadena vacía si no hay nada que contar."""
        spanish = lang in ('esES', 'esMX')
        if not self.lines and not self.missing:
            return ''
        title = ('DATOS VERIFICADOS (base de WoW Forever):' if spanish
                 else 'VERIFIED DATA (WoW Forever database):')
        segments = [title] + list(self.lines)
        if self.missing:
            segments.append('SIN DATOS EN LA BASE:' if spanish
                            else 'NOT IN THE DATABASE:')
            segments.extend(self.missing)
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


def _quest_line(quest, lang: str) -> str:
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
    if variants > 1:
        text += f' (there are {variants} quests with that name)'
    return text


def _dungeon_line(dungeon, lang: str) -> str:
    name = dungeon.get('name') or ''
    entrances = dungeon.get('entrances') or []
    if lang == 'es':
        if entrances:
            return f'Mazmorra «{name}»: entrada en {_location_text(entrances[0])}.'
        return f'Mazmorra «{name}»: sin entrada conocida.'
    if entrances:
        return f'Dungeon "{name}": entrance in {_location_text(entrances[0])}.'
    return f'Dungeon "{name}": no known entrance.'


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
            rate = drop.get('rate')
            pieces.append(f'{npc} ({rate} %)' if rate is not None else npc)
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


def _detect_entities(facts: Facts, db, question: str, lang: str, ctx: dict) -> bool:
    try:
        matches = db.match_entities(question, lang=lang)
    except Exception:
        matches = []
    player_level = ctx.get('lvl')
    for match in matches:
        kind = match.get('kind')
        entity_id = match.get('id')
        if normalize(match.get('name') or '') in GENERIC_ENTITY_NAMES:
            continue
        if kind == 'quest':
            quest = db.find_quest(entity_id, lang, player_level=player_level)
            if quest is None:
                continue
            facts.lines.append(_quest_line(quest, lang))
            _add_source(facts, f'quest:{quest["id"]}')
        elif kind == 'dungeon':
            dungeon = db.dungeon(entity_id, lang)
            if dungeon is None:
                continue
            facts.lines.append(_dungeon_line(dungeon, lang))
            _add_source(facts, f'dungeon:{dungeon["id"]}')
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
    return any(match.get('kind') == 'dungeon' for match in matches)


def _ctx_level(ctx: dict):
    level = ctx.get('lvl')
    if isinstance(level, bool):
        return None
    if isinstance(level, (int, float)):
        return int(level)
    if isinstance(level, str) and level.strip().isdigit():
        return int(level.strip())
    return None


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


def _faction(value):
    text = normalize(value)
    if text in ('alianza', 'alliance'):
        return 'A'
    if text in ('horda', 'horde'):
        return 'H'
    return None


def _detect_spells(facts: Facts, db, normalized: str, lang: str, ctx: dict) -> None:
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


def _detect_trainers(facts: Facts, db, normalized: str, lang: str, ctx: dict) -> None:
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


def _flight_name_ok(name: str) -> bool:
    normalized = normalize(name)
    if normalized.startswith('zz'):
        return False
    if 'quest path' in normalized:
        return False
    return ':' not in name


def _detect_flights(facts: Facts, db, normalized: str, lang: str, ctx: dict) -> None:
    if not any(word in normalized for word in FLIGHT_KEYWORDS):
        return
    continent = None
    try:
        continent = db.zone_continent(ctx.get('zone'))
    except Exception:
        continent = None
    if continent is None:
        continent = 0
    faction = _faction(ctx.get('fac'))
    try:
        points = db.flight_points(continent, faction, lang)
    except Exception:
        points = []
    points = [point for point in points if _flight_name_ok(point.get('name') or '')]
    if not points:
        facts.missing.append('puntos de vuelo para tu facción' if lang == 'es'
                             else 'flight points for your faction')
        return
    current_zone = normalize(ctx.get('zone') or '')

    def sort_key(point):
        name = normalize(point.get('name') or '')
        here = 0 if current_zone and current_zone in name else 1
        return (here, point.get('id') or 0)

    points.sort(key=sort_key)
    names = '; '.join(point.get('name') or '' for point in points[:12])
    if lang == 'es':
        facts.lines.append(f'Puntos de vuelo de tu facción en este continente: {names}')
    else:
        facts.lines.append(f"Your faction's flight points on this continent: {names}")
    _add_source(facts, f'flights:{continent}:{faction or "any"}')


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
        facts.lines.append(line)
        _add_source(facts, f'quest:{quest["id"]}')


def _detect_gaps(facts: Facts, normalized: str, lang: str, has_dungeon: bool) -> None:
    mentions_level = any(word in normalized for word in ('nivel', 'level', 'rango'))
    mentions_dungeon = any(word in normalized
                           for word in ('mazmorra', 'dungeon', 'instancia', 'instance'))
    if mentions_level and (has_dungeon or mentions_dungeon):
        facts.missing.append('rangos de nivel de mazmorras' if lang == 'es'
                             else 'dungeon level ranges')
    words = set(normalized.split())
    if ('experiencia' in normalized or 'experience' in normalized
            or 'xp' in words or 'exp' in words):
        facts.missing.append('experiencia necesaria por nivel' if lang == 'es'
                             else 'experience needed per level')


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

        has_dungeon = _detect_entities(facts, db, question, lang, ctx)
        _detect_spells(facts, db, normalized, lang, ctx)
        _detect_trainers(facts, db, normalized, lang, ctx)
        _detect_flights(facts, db, normalized, lang, ctx)
        _detect_talents(facts, db, normalized, lang, ctx)
        _detect_quest_list(facts, db, normalized, lang, ctx)
        _detect_gaps(facts, normalized, lang, has_dungeon)

        facts.lines = list(dict.fromkeys(facts.lines))
        facts.missing = list(dict.fromkeys(facts.missing))
        return facts
    except Exception:
        return Facts()
