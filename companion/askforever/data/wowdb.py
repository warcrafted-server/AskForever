"""Capa de consulta de solo lectura sobre la base SQLite de wowdata."""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Optional

CLASSES = {
    1: {'masculine': 'Guerrero', 'feminine': 'Guerrera', 'plural': 'guerreros',
        'english': 'Warrior'},
    2: {'masculine': 'Paladín', 'feminine': 'Paladín', 'plural': 'paladines',
        'english': 'Paladin'},
    4: {'masculine': 'Cazador', 'feminine': 'Cazadora', 'plural': 'cazadores',
        'english': 'Hunter'},
    8: {'masculine': 'Pícaro', 'feminine': 'Pícara', 'plural': 'pícaros',
        'english': 'Rogue'},
    16: {'masculine': 'Sacerdote', 'feminine': 'Sacerdotisa', 'plural': 'sacerdotes',
         'english': 'Priest'},
    64: {'masculine': 'Chamán', 'feminine': 'Chamana', 'plural': 'chamanes',
         'english': 'Shaman'},
    128: {'masculine': 'Mago', 'feminine': 'Maga', 'plural': 'magos',
          'english': 'Mage'},
    256: {'masculine': 'Brujo', 'feminine': 'Bruja', 'plural': 'brujos',
          'english': 'Warlock'},
    1024: {'masculine': 'Druida', 'feminine': 'Druida', 'plural': 'druidas',
           'english': 'Druid'},
}

STOP_NAMES = {
    'agua', 'pan', 'carne', 'leche', 'water', 'bread',
}

KIND_ORDER = ('quest', 'dungeon', 'npc', 'zone', 'item')

MIN_NAME_LENGTH = 5
MAX_MATCHES = 6

# En la base real los hechos de ext_zones agrupan los Reinos del Este en el
# grupo 0 y Kalimdor en el 1, que son los continentes de TaxiNodes.
ZONE_GROUP_CONTINENT = {0: 0, 1: 1}


def normalize(text) -> str:
    """Minúsculas, sin tildes, sin signos y con espacios simples."""
    if text is None:
        return ''
    text = str(text).replace('\u00a0', ' ')
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    cleaned = ''.join(char if char.isalnum() or char.isspace() else '' for char in text)
    return re.sub(r'\s+', ' ', cleaned).strip()


def _clean_text(value) -> str:
    if value is None:
        return ''
    text = str(value).replace('\u00a0', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def _round1(value) -> Optional[float]:
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def _as_int(value) -> Optional[int]:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit() or (text.startswith('-') and text[1:].isdigit()):
            return int(text)
    return None


def _article_key(text) -> str:
    """Nombre normalizado sin artículo inicial, para comparar mazmorras."""
    normalized = normalize(text)
    for article in ('el ', 'la ', 'los ', 'las ', 'the '):
        if normalized.startswith(article):
            return normalized[len(article):]
    return normalized


# Niveles curados por el mantenedor: mandan sobre los valores del cliente.
FOREVER_LEVELS_PATH = Path(__file__).with_name('forever_dungeon_levels.json')
_FOREVER_LEVELS = None


def _forever_rows():
    """Filas curadas de niveles, cargadas una sola vez y sin lanzar errores."""
    global _FOREVER_LEVELS
    if _FOREVER_LEVELS is None:
        _FOREVER_LEVELS = _load_forever_levels(FOREVER_LEVELS_PATH)
    return _FOREVER_LEVELS


def _load_forever_levels(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:
        return []
    items = data.get('dungeons') if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        lfg_id = _as_int(item.get('lfg_id'))
        low = _as_int(item.get('min'))
        high = _as_int(item.get('max'))
        name_es = _clean_text(item.get('name_es'))
        name_en = _clean_text(item.get('name_en'))
        if lfg_id is None or low is None or high is None or low > high:
            continue
        if not name_es and not name_en:
            continue
        wing_es = _clean_text(item.get('wing_es')) or _clean_text(item.get('wing_en'))
        wing_en = _clean_text(item.get('wing_en')) or _clean_text(item.get('wing_es'))
        rows.append({
            'lfg_id': lfg_id,
            'name_es': name_es or name_en,
            'name_en': name_en or name_es,
            'wing_es': wing_es,
            'wing_en': wing_en,
            'min': low,
            'max': high,
        })
    return rows


def _forever_name_rows(rows, target: str):
    if not target:
        return []
    return [row for row in rows
            if target in (_article_key(row['name_es']), _article_key(row['name_en']))]


def _forever_wing_keys(row):
    return {_article_key(row['wing_es']), _article_key(row['wing_en'])} - {''}


def _forever_wing(name_or_id, rows):
    """Fila del ala pedida, o None si la consulta no identifica un ala."""
    text = _clean_text(name_or_id)
    target = _article_key(text)
    if not target or _forever_name_rows(rows, target):
        return None
    for separator in (':', ' - '):
        if separator not in text:
            continue
        base, wing = text.split(separator, 1)
        wing_key = _article_key(wing)
        for row in _forever_name_rows(rows, _article_key(base)):
            if wing_key and wing_key in _forever_wing_keys(row):
                return row
    matched = [row for row in rows if target in _forever_wing_keys(row)]
    if len(matched) == 1:
        return matched[0]
    return None


def _forever_result(rows, lang: str):
    name_key = 'name_es' if lang == 'es' else 'name_en'
    wing_key = 'wing_es' if lang == 'es' else 'wing_en'
    result = {
        'name': rows[0][name_key],
        'min': min(row['min'] for row in rows),
        'max': max(row['max'] for row in rows),
        'source': 'forever',
    }
    wings = [row for row in rows if row['wing_es'] or row['wing_en']]
    if wings:
        result['wings'] = [
            {'name': row[wing_key], 'min': row['min'], 'max': row['max']}
            for row in wings
        ]
    return result


def _forever_wing_result(row, lang: str):
    name_key = 'name_es' if lang == 'es' else 'name_en'
    wing_key = 'wing_es' if lang == 'es' else 'wing_en'
    return {
        'name': f"{row[name_key]}: {row[wing_key]}",
        'min': row['min'],
        'max': row['max'],
        'source': 'forever',
    }


def class_mask_from_name(name) -> Optional[int]:
    """Máscara de clase a partir de cualquiera de sus nombres normalizados."""
    target = normalize(name)
    if not target:
        return None
    for mask, data in CLASSES.items():
        for key in ('masculine', 'feminine', 'plural', 'english'):
            if normalize(data[key]) == target:
                return mask
    return None


class WowDb:
    """Consultas deterministas y de solo lectura sobre wow.sqlite."""

    def __init__(self, path) -> None:
        self.path = Path(path)
        self._conn = None
        self._entries = None
        self._by_first = None

    def open(self):
        """Abre la conexión de solo lectura de forma perezosa."""
        if self._conn is None:
            uri = f'file:{self.path.resolve().as_posix()}?mode=ro'
            self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def available(self) -> bool:
        """True si el archivo existe y contiene la tabla ext_quests."""
        try:
            if not self.path.is_file():
                return False
            row = self.open().execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ext_quests'"
            ).fetchone()
            return row is not None
        except Exception:
            return False

    def _rows(self, sql, params=()):
        try:
            return self.open().execute(sql, params).fetchall()
        except Exception:
            return []

    @staticmethod
    def _pick(names: dict, lang: str) -> str:
        preferred = 'esES' if lang == 'es' else 'enUS'
        other = 'enUS' if preferred == 'esES' else 'esES'
        return _clean_text(names.get(preferred) or names.get(other) or '')

    def _localized(self, table: str, id_column: str, entity_id, lang: str) -> str:
        rows = self._rows(
            f'SELECT locale, name FROM {table} WHERE {id_column} = ?', (entity_id,))
        names = {row['locale']: row['name'] for row in rows}
        return self._pick(names, lang)

    def _npc_names(self, npc_id, lang: str):
        rows = self._rows(
            'SELECT locale, name, sub_name FROM ext_npc_l10n WHERE npc_id = ?', (npc_id,))
        by_locale = {row['locale']: row for row in rows}
        preferred = 'esES' if lang == 'es' else 'enUS'
        other = 'enUS' if preferred == 'esES' else 'esES'
        row = by_locale.get(preferred) or by_locale.get(other)
        if row is None:
            return '', ''
        return _clean_text(row['name']), _clean_text(row['sub_name'])

    def zone_name(self, area_id, lang: str = 'es') -> str:
        rows = self._rows(
            'SELECT name_esES, name_enUS FROM ext_zones WHERE area_id = ? LIMIT 1', (area_id,))
        if not rows:
            return ''
        row = rows[0]
        if lang == 'es':
            name = row['name_esES'] or row['name_enUS']
        else:
            name = row['name_enUS'] or row['name_esES']
        return _clean_text(name)

    def zone_continent(self, zone_name) -> Optional[int]:
        """Continente de TaxiNodes (0 Reinos del Este, 1 Kalimdor) de una zona."""
        target = normalize(zone_name)
        if not target:
            return None
        rows = self._rows('SELECT group_id, name_esES, name_enUS FROM ext_zones')
        for row in rows:
            if normalize(row['name_esES']) == target or normalize(row['name_enUS']) == target:
                return ZONE_GROUP_CONTINENT.get(row['group_id'])
        return None

    def npc_locations(self, npc_id, limit: int = 3, lang: str = 'es'):
        locations = []
        seen = set()
        zones = {}
        rows = self._rows(
            'SELECT zone_id, spawn_idx, x, y FROM ext_npc_spawns WHERE npc_id = ? '
            'ORDER BY spawn_idx, zone_id', (npc_id,))
        for row in rows:
            zone_id = row['zone_id']
            x = _round1(row['x'])
            y = _round1(row['y'])
            # Los PNJ de dentro de instancias llevan (-1, -1) de relleno: se conserva la zona sin coordenadas.
            if x is not None and y is not None and (x < 0 or y < 0):
                x = y = None
            key = (zone_id, x, y)
            if key in seen:
                continue
            seen.add(key)
            if zone_id not in zones:
                zones[zone_id] = self.zone_name(zone_id, lang)
            locations.append({'zone': zones[zone_id], 'zone_id': zone_id, 'x': x, 'y': y})
            if len(locations) >= limit:
                break
        return locations

    def _quest_name(self, quest_id, lang: str) -> str:
        return self._localized('ext_quest_l10n', 'quest_id', quest_id, lang)

    def _has_starter(self, quest_id) -> bool:
        rows = self._rows(
            'SELECT 1 FROM ext_quest_starters WHERE quest_id = ? LIMIT 1', (quest_id,))
        return bool(rows)

    def _quest_entities(self, table: str, quest_id, lang: str):
        entities = []
        rows = self._rows(
            f'SELECT entity_type, entity_id FROM {table} WHERE quest_id = ?', (quest_id,))
        for row in rows:
            entity_type = row['entity_type']
            entity_id = row['entity_id']
            if entity_type == 'npc':
                name, sub_name = self._npc_names(entity_id, lang)
                locations = self.npc_locations(entity_id, lang=lang)
            elif entity_type == 'object':
                name = self._localized('ext_object_l10n', 'object_id', entity_id, lang)
                sub_name = ''
                locations = []
            elif entity_type == 'item':
                name = self._localized('ext_item_l10n', 'item_id', entity_id, lang)
                sub_name = ''
                locations = []
            else:
                continue
            entities.append({
                'type': entity_type,
                'id': entity_id,
                'name': name,
                'sub_name': sub_name,
                'locations': locations,
            })
        return entities

    def _quest_dict(self, quest_id, lang: str):
        rows = self._rows(
            'SELECT quest_id, quest_level, required_level FROM ext_quests WHERE quest_id = ? '
            'LIMIT 1', (quest_id,))
        if not rows:
            return None
        row = rows[0]
        objective_items = []
        item_rows = self._rows(
            'SELECT item_id, text FROM ext_quest_objective_items WHERE quest_id = ? '
            'ORDER BY position', (quest_id,))
        for item_row in item_rows:
            name = self._localized('ext_item_l10n', 'item_id', item_row['item_id'], lang)
            objective_items.append(name or _clean_text(item_row['text']))
        return {
            'id': quest_id,
            'name': self._quest_name(quest_id, lang),
            'level': row['quest_level'],
            'required_level': row['required_level'],
            'starters': self._quest_entities('ext_quest_starters', quest_id, lang),
            'finishers': self._quest_entities('ext_quest_finishers', quest_id, lang),
            'objective_items': objective_items,
        }

    def find_quest(self, name_or_id, lang: str = 'es', player_level=None):
        quest_id = _as_int(name_or_id)
        if quest_id is not None:
            return self._quest_dict(quest_id, lang)

        target = normalize(name_or_id)
        if not target:
            return None
        rows = self._rows('SELECT quest_id, name FROM ext_quest_l10n')
        matches = set()
        for row in rows:
            if normalize(row['name']) == target:
                matches.add(row['quest_id'])
        if not matches:
            return None

        def score(candidate):
            quest = self._quest_dict(candidate, lang) or {}
            level = quest.get('level')
            has_starter = bool(quest.get('starters'))
            if player_level is not None and isinstance(level, (int, float)):
                distance = abs(level - player_level)
            else:
                distance = 0
            level_key = level if isinstance(level, (int, float)) else 10 ** 6
            return (0 if has_starter else 1, distance, level_key, candidate)

        best = min(matches, key=score)
        result = self._quest_dict(best, lang)
        if result is not None:
            result['variants'] = len(matches)
        return result

    def find_npc(self, name_or_id, lang: str = 'es'):
        npc_id = _as_int(name_or_id)
        if npc_id is None:
            target = normalize(name_or_id)
            if not target:
                return None
            rows = self._rows('SELECT npc_id, locale, name FROM ext_npc_l10n')
            matches = {row['npc_id'] for row in rows if normalize(row['name']) == target}
            if not matches:
                return None
            with_locations = [candidate for candidate in matches if self.npc_locations(candidate, limit=1)]
            npc_id = min(with_locations) if with_locations else min(matches)

        rows = self._rows(
            'SELECT npc_id, min_level, max_level, friendly_to_faction FROM ext_npcs '
            'WHERE npc_id = ? LIMIT 1', (npc_id,))
        if not rows:
            return None
        row = rows[0]
        name, sub_name = self._npc_names(npc_id, lang)
        return {
            'id': npc_id,
            'name': name,
            'sub_name': sub_name,
            'min_level': row['min_level'],
            'max_level': row['max_level'],
            'friendly_to': row['friendly_to_faction'],
            'locations': self.npc_locations(npc_id, lang=lang),
        }

    def class_spells(self, class_mask, level_from, level_to, lang: str = 'es'):
        rows = self._rows(
            'SELECT Name_enUS, Name_esES, Level FROM v_hechizos_instructor '
            'WHERE ClassMask = ? AND Level BETWEEN ? AND ?', (class_mask, level_from, level_to))
        seen = set()
        spells = []
        for row in rows:
            if lang == 'es':
                name = _clean_text(row['Name_esES'] or row['Name_enUS'])
            else:
                name = _clean_text(row['Name_enUS'] or row['Name_esES'])
            key = (name, row['Level'])
            if key in seen:
                continue
            seen.add(key)
            spells.append({'name': name, 'level': row['Level']})
        spells.sort(key=lambda spell: (spell['level'], spell['name']))
        return spells

    def class_trainers(self, class_mask, faction=None, lang: str = 'es'):
        data = CLASSES.get(class_mask)
        if not data:
            return []
        accepted = {
            normalize(f'instructor de {data["plural"]}'),
            normalize(f'instructora de {data["plural"]}'),
            normalize(f'{data["english"]} trainer'),
        }
        rows = self._rows('SELECT npc_id, locale, sub_name FROM ext_npc_l10n')
        npc_ids = set()
        for row in rows:
            if normalize(row['sub_name']) in accepted:
                npc_ids.add(row['npc_id'])

        trainers = []
        for npc_id in sorted(npc_ids):
            npc_rows = self._rows(
                'SELECT friendly_to_faction FROM ext_npcs WHERE npc_id = ? LIMIT 1', (npc_id,))
            if not npc_rows:
                continue
            friendly = npc_rows[0]['friendly_to_faction'] or ''
            if faction and faction not in friendly:
                continue
            name, sub_name = self._npc_names(npc_id, lang)
            trainers.append({
                'id': npc_id,
                'name': name,
                'sub_name': sub_name,
                'friendly_to': friendly,
                'locations': self.npc_locations(npc_id, lang=lang),
            })
        return trainers

    def dungeon(self, name_or_id, lang: str = 'es'):
        area_id = _as_int(name_or_id)
        if area_id is None:
            target = normalize(name_or_id)
            if not target:
                return None
            rows = self._rows(
                'SELECT area_id, name_enUS, name_esES, parent_zone_id FROM ext_dungeons')
            matches = [row for row in rows
                       if normalize(row['name_esES']) == target
                       or normalize(row['name_enUS']) == target]
            if not matches:
                return None
            row = matches[0]
        else:
            rows = self._rows(
                'SELECT area_id, name_enUS, name_esES, parent_zone_id FROM ext_dungeons '
                'WHERE area_id = ? LIMIT 1', (area_id,))
            if not rows:
                return None
            row = rows[0]

        area_id = row['area_id']
        if lang == 'es':
            name = row['name_esES'] or row['name_enUS']
        else:
            name = row['name_enUS'] or row['name_esES']
        entrances = []
        for entrance in self._rows(
                'SELECT zone_id, x, y FROM ext_dungeon_entrances WHERE area_id = ? '
                'ORDER BY idx', (area_id,)):
            entrances.append({
                'zone': self.zone_name(entrance['zone_id'], lang),
                'x': _round1(entrance['x']),
                'y': _round1(entrance['y']),
            })
        return {
            'id': area_id,
            'name': _clean_text(name),
            'zone': self.zone_name(row['parent_zone_id'], lang),
            'entrances': entrances,
        }

    @staticmethod
    def _faction_usable(raw, faction) -> bool:
        # En la base real el primer valor de MountCreatureID es el de la Horda y
        # el resto los de la Alianza; los 0 indican que esa facción no lo usa.
        if not faction:
            return True
        try:
            values = json.loads(raw) if raw else []
        except (TypeError, ValueError):
            return True
        if not isinstance(values, list) or not values:
            return True
        try:
            numbers = [int(value) for value in values]
        except (TypeError, ValueError):
            return True
        if faction == 'H':
            return bool(numbers[0])
        if faction == 'A':
            return any(numbers[1:]) if len(numbers) > 1 else True
        return True

    def flight_points(self, continent_id, faction, lang: str = 'es'):
        points = []
        rows = self._rows(
            'SELECT __id, Name_lang, Name_lang_esES, ContinentID, MountCreatureID '
            'FROM TaxiNodes WHERE ContinentID = ? ORDER BY __id', (continent_id,))
        for row in rows:
            if lang == 'es':
                name = row['Name_lang_esES'] or row['Name_lang'] or ''
            else:
                name = row['Name_lang'] or row['Name_lang_esES'] or ''
            name = _clean_text(name)
            if normalize(name).startswith('transport'):
                continue
            if not self._faction_usable(row['MountCreatureID'], faction):
                continue
            points.append({'id': row['__id'], 'name': name})
        return points

    def talent_trees(self, class_mask, lang: str = 'es'):
        rows = self._rows(
            'SELECT Name_lang, Name_lang_esES, OrderIndex FROM TalentTab '
            'WHERE ClassMask = ? ORDER BY OrderIndex, __id', (class_mask,))
        trees = []
        for row in rows:
            if lang == 'es':
                name = row['Name_lang_esES'] or row['Name_lang']
            else:
                name = row['Name_lang'] or row['Name_lang_esES']
            trees.append(_clean_text(name))
        return trees

    def item_sources(self, name_or_id, lang: str = 'es', limit: int = 3):
        item_id = _as_int(name_or_id)
        if item_id is None:
            target = normalize(name_or_id)
            if not target:
                return None
            rows = self._rows('SELECT item_id, name FROM ext_item_l10n')
            matches = {row['item_id'] for row in rows if normalize(row['name']) == target}
            if not matches:
                return None
            item_id = min(matches)

        name = self._localized('ext_item_l10n', 'item_id', item_id, lang)
        vendors = []
        for row in self._rows(
                'SELECT npc_id FROM ext_item_vendors WHERE item_id = ? ORDER BY position',
                (item_id,)):
            npc_name, sub_name = self._npc_names(row['npc_id'], lang)
            vendors.append({
                'npc': npc_name,
                'sub_name': sub_name,
                'locations': self.npc_locations(row['npc_id'], lang=lang),
            })
            if len(vendors) >= limit:
                break

        drops = []
        for row in self._rows(
                'SELECT npc_id FROM ext_item_npc_drops WHERE item_id = ? ORDER BY position',
                (item_id,)):
            npc_name, _sub_name = self._npc_names(row['npc_id'], lang)
            rate_rows = self._rows(
                'SELECT rate_percent FROM ext_item_drop_rates WHERE item_id = ? AND npc_id = ? '
                'ORDER BY rate_percent DESC LIMIT 1', (item_id, row['npc_id']))
            rate = None
            if rate_rows and rate_rows[0]['rate_percent'] is not None:
                try:
                    rate = float(rate_rows[0]['rate_percent'])
                except (TypeError, ValueError):
                    rate = None
            locations = self.npc_locations(row['npc_id'], limit=1, lang=lang)
            drops.append({
                'npc': npc_name,
                'zone': locations[0]['zone'] if locations else '',
                'rate': rate,
            })
            if len(drops) >= limit:
                break

        rewards = []
        for row in self._rows(
                'SELECT quest_id FROM ext_item_quest_rewards WHERE item_id = ? ORDER BY position',
                (item_id,)):
            quest_name = self._quest_name(row['quest_id'], lang)
            if quest_name:
                rewards.append(quest_name)

        if not drops:
            seen_npcs = set()
            for row in self._rows(
                    'SELECT npc_id, porcentaje FROM v_botin WHERE item_id = ? '
                    'ORDER BY porcentaje DESC', (item_id,)):
                npc_id = row['npc_id']
                if npc_id in seen_npcs:
                    continue
                seen_npcs.add(npc_id)
                npc_name, _sub_name = self._npc_names(npc_id, lang)
                if not npc_name:
                    npc_rows = self._rows(
                        'SELECT nombre, nombre_en FROM v_npc WHERE npc_id = ? LIMIT 1',
                        (npc_id,))
                    if npc_rows:
                        npc_name = _clean_text(
                            npc_rows[0]['nombre'] or npc_rows[0]['nombre_en'])
                locations = self.npc_locations(npc_id, limit=1, lang=lang)
                try:
                    rate = round(float(row['porcentaje']))
                except (TypeError, ValueError):
                    rate = None
                drops.append({
                    'npc': npc_name,
                    'zone': locations[0]['zone'] if locations else '',
                    'rate': rate,
                })
                if len(drops) >= limit:
                    break

        if not name and not vendors and not drops and not rewards:
            return None
        return {
            'id': item_id,
            'name': name,
            'vendors': vendors,
            'drops': drops,
            'quest_rewards': rewards,
        }

    def format_money(self, copper, lang: str = 'es') -> str:
        """Formatea una cantidad de cobre como oro, plata y cobre."""
        try:
            copper = max(0, int(copper or 0))
        except (TypeError, ValueError):
            copper = 0
        gold, rest = divmod(copper, 10000)
        silver, copper_rest = divmod(rest, 100)
        parts = []
        if gold:
            parts.append(f'{gold} de oro' if lang == 'es' else f'{gold} gold')
        if silver:
            parts.append(f'{silver} de plata' if lang == 'es' else f'{silver} silver')
        if not gold and copper_rest:
            parts.append(f'{copper_rest} de cobre' if lang == 'es' else f'{copper_rest} copper')
        if not parts:
            parts.append('0 de cobre' if lang == 'es' else '0 copper')
        return (' y ' if lang == 'es' else ' ').join(parts)

    @staticmethod
    def _zone_level_row(row, lang: str) -> dict:
        if lang == 'es':
            name = row['nombre'] or row['nombre_en']
        else:
            name = row['nombre_en'] or row['nombre']
        return {
            'area_id': row['area_id'],
            'name': _clean_text(name),
            'min': _as_int(row['nivel_min']),
            'max': _as_int(row['nivel_max']),
        }

    def _zone_level_rows(self):
        # v_zona_niveles calcula percentiles al vuelo (~2 s): se lee una vez por instancia.
        if getattr(self, '_zone_level_cache', None) is None:
            self._zone_level_cache = self._rows(
                'SELECT area_id, nombre, nombre_en, nivel_min, nivel_max FROM v_zona_niveles')
        return self._zone_level_cache

    def zone_levels(self, name_or_area_id, lang: str = 'es'):
        rows = self._zone_level_rows()
        if not rows:
            return None
        area_id = _as_int(name_or_area_id)
        if area_id is not None:
            for row in rows:
                if row['area_id'] == area_id:
                    return self._zone_level_row(row, lang)
            return None
        target = normalize(name_or_area_id)
        if not target:
            return None
        for row in rows:
            if normalize(row['nombre']) == target or normalize(row['nombre_en']) == target:
                return self._zone_level_row(row, lang)
        return None

    def zones_for_level(self, level, lang: str = 'es', limit: int = 8):
        try:
            level = int(level)
        except (TypeError, ValueError):
            return []
        # v_zona_niveles también trae instancias (p. ej. Sima Ígnea): no son zonas para subir de nivel.
        dungeon_areas = {_as_int(row['area_id']) for row in self._rows('SELECT area_id FROM ext_dungeons')}
        zones = []
        for row in self._zone_level_rows():
            low = _as_int(row['nivel_min'])
            high = _as_int(row['nivel_max'])
            if low is None or high is None or _as_int(row['area_id']) in dungeon_areas:
                continue
            if low <= level <= high and (high - low) <= 15:
                zones.append((low, row))
        zones.sort(key=lambda item: (level - item[0], item[0], item[1]['area_id']))
        try:
            limit = max(0, int(limit))
        except (TypeError, ValueError):
            limit = 6
        return [self._zone_level_row(row, lang) for _low, row in zones[:limit]]

    def _lfg_dungeon_rows(self):
        return self._rows(
            'SELECT ID, Name_lang, Name_lang_esES, TypeID, MapID, ContentTuningID '
            'FROM LFGDungeons')

    def _content_levels(self, content_tuning_id):
        rows = self._rows(
            'SELECT * FROM contenttuning WHERE ID = ? LIMIT 1', (content_tuning_id,))
        if not rows:
            return None
        row = rows[0]

        def number(name):
            try:
                return int(row[name] or 0)
            except (IndexError, KeyError, TypeError, ValueError):
                return 0

        low = number('MinLevelSquish')
        high = number('MaxLevelSquish')
        if low == 0 and high == 0:
            low = number('LfgMinLevel')
            high = number('LfgMaxLevel')
        if low == 0 and high == 0:
            return None
        if low == 0:
            low = high
        if high == 0:
            high = low
        return low, high

    @staticmethod
    def _lfg_name(row, lang: str) -> str:
        if lang == 'es':
            return _clean_text(row['Name_lang_esES'] or row['Name_lang'])
        return _clean_text(row['Name_lang'] or row['Name_lang_esES'])

    @staticmethod
    def _lfg_for_ext(ext_row, lfg_rows):
        keys = {_article_key(ext_row['name_esES']), _article_key(ext_row['name_enUS'])}
        keys.discard('')
        for row in lfg_rows:
            if (_article_key(row['Name_lang_esES']) in keys
                    or _article_key(row['Name_lang']) in keys):
                return row
        return None

    def _find_lfg_dungeon(self, name_or_id):
        lfg_rows = self._lfg_dungeon_rows()
        ext_rows = self._rows('SELECT area_id, name_enUS, name_esES FROM ext_dungeons')
        number = _as_int(name_or_id)
        if number is not None:
            for row in lfg_rows:
                if row['ID'] == number:
                    return row
            for ext in ext_rows:
                if ext['area_id'] == number:
                    return self._lfg_for_ext(ext, lfg_rows)
            return None
        target = _article_key(name_or_id)
        if not target:
            return None
        for row in lfg_rows:
            if (_article_key(row['Name_lang_esES']) == target
                    or _article_key(row['Name_lang']) == target):
                return row
        for ext in ext_rows:
            if (_article_key(ext['name_esES']) == target
                    or _article_key(ext['name_enUS']) == target):
                return self._lfg_for_ext(ext, lfg_rows)
        return None

    def _forever_rows_for_ext(self, area_id, rows):
        """Filas curadas de una mazmorra de ext_dungeons, sin depender de LFG."""
        ext = self._rows(
            'SELECT name_enUS, name_esES FROM ext_dungeons WHERE area_id = ? LIMIT 1',
            (area_id,))
        if not ext:
            return []
        keys = {_article_key(ext[0]['name_esES']), _article_key(ext[0]['name_enUS'])}
        keys.discard('')
        for key in keys:
            matched = _forever_name_rows(rows, key)
            if matched:
                return matched
        return []

    def dungeon_level(self, name_or_id, lang: str = 'es'):
        forever = _forever_rows()
        wing = _forever_wing(name_or_id, forever) if forever else None
        if wing is not None:
            return _forever_wing_result(wing, lang)
        row = self._find_lfg_dungeon(name_or_id)
        rows = []
        if row is not None:
            rows = [item for item in forever if item['lfg_id'] == row['ID']]
        if not rows:
            rows = _forever_name_rows(forever, _article_key(name_or_id))
        if not rows:
            number = _as_int(name_or_id)
            if number is not None:
                rows = [item for item in forever if item['lfg_id'] == number]
                if not rows:
                    rows = self._forever_rows_for_ext(number, forever)
        if rows:
            return _forever_result(rows, lang)
        if row is None:
            return None
        levels = self._content_levels(row['ContentTuningID'])
        if levels is None:
            return None
        return {'name': self._lfg_name(row, lang), 'min': levels[0], 'max': levels[1],
                'source': 'client'}

    def dungeons_for_level(self, level, lang: str = 'es', below: int = 2, above: int = 5):
        try:
            level = int(level)
            low_limit = level - int(below)
            high_limit = level + int(above)
        except (TypeError, ValueError):
            return []
        forever = _forever_rows()
        if forever:
            name_key = 'name_es' if lang == 'es' else 'name_en'
            wing_key = 'wing_es' if lang == 'es' else 'wing_en'
            dungeons = []
            for row in forever:
                if not row['min'] <= level <= row['max']:
                    continue
                name = row[name_key]
                if row[wing_key]:
                    name = f'{name}: {row[wing_key]}'
                dungeons.append({'name': name, 'min': row['min'], 'max': row['max'],
                                 'source': 'forever'})
            dungeons.sort(key=lambda item: item['min'])
            return dungeons
        ext_keys = set()
        for row in self._rows('SELECT name_enUS, name_esES FROM ext_dungeons'):
            ext_keys.add(_article_key(row['name_esES']))
            ext_keys.add(_article_key(row['name_enUS']))
        ext_keys.discard('')
        dungeons = []
        seen = set()
        for row in self._lfg_dungeon_rows():
            name_en = _article_key(row['Name_lang'])
            name_es = _article_key(row['Name_lang_esES'])
            if name_en not in ext_keys and name_es not in ext_keys:
                continue
            levels = self._content_levels(row['ContentTuningID'])
            if levels is None:
                continue
            low, high = levels
            if not low_limit <= low <= high_limit:
                continue
            key = (low, high, name_en)
            if key in seen:
                continue
            seen.add(key)
            dungeons.append({'name': self._lfg_name(row, lang), 'min': low, 'max': high})
        dungeons.sort(key=lambda item: (item['min'], item['name']))
        return dungeons

    def dungeon_bosses(self, name_or_id, lang: str = 'es'):
        row = self._find_lfg_dungeon(name_or_id)
        if row is None:
            return None
        bosses = self._rows(
            'SELECT encuentro_id, map_id, instancia, dificultad, orden, nombre, nombre_en '
            'FROM v_jefe_mazmorra')
        map_id = row['MapID']
        selected = []
        if map_id:
            selected = [boss for boss in bosses if boss['map_id'] == map_id]
        if not selected:
            keys = {_article_key(row['Name_lang']), _article_key(row['Name_lang_esES'])}
            keys.discard('')
            for boss in bosses:
                boss_key = _article_key(boss['instancia'])
                if not boss_key:
                    continue
                for name_key in keys:
                    if boss_key == name_key or name_key.startswith(boss_key + ' '):
                        selected.append(boss)
                        break
        seen = set()
        ordered = []
        for boss in sorted(selected, key=lambda item: (item['orden'] or 0, item['nombre'] or '')):
            key = (boss['orden'], boss['nombre'])
            if key in seen:
                continue
            seen.add(key)
            ordered.append(boss)
        names = []
        for boss in ordered:
            if lang == 'es':
                names.append(_clean_text(boss['nombre'] or boss['nombre_en']))
            else:
                names.append(_clean_text(boss['nombre_en'] or boss['nombre']))
        return {'name': self._lfg_name(row, lang), 'bosses': names}

    def xp_to_next_level(self, level):
        number = _as_int(level)
        if number is None:
            return None
        rows = self._rows(
            'SELECT Experience FROM levelexperience WHERE Level = ? LIMIT 1', (number,))
        if not rows:
            return None
        try:
            return int(rows[0]['Experience'])
        except (TypeError, ValueError):
            return None

    def quest_details(self, quest_id, lang: str = 'es'):
        number = _as_int(quest_id)
        if number is None:
            return None
        rows = self._rows(
            'SELECT quest_id, titulo, nivel, xp, zona, objetivo, texto, origen '
            'FROM v_mision WHERE quest_id = ? LIMIT 1', (number,))
        if not rows:
            return None
        row = rows[0]
        objectives = []
        raw = row['objetivo']
        if raw:
            try:
                parsed = json.loads(raw)
            except (TypeError, ValueError):
                parsed = None
            if isinstance(parsed, list):
                objectives = [str(item) for item in parsed if item is not None]
            elif isinstance(parsed, str):
                objectives = [parsed]
            else:
                objectives = [str(raw)]
        try:
            xp = int(row['xp'])
        except (TypeError, ValueError):
            xp = None
        return {'xp': xp, 'zone': _clean_text(row['zona']), 'objectives': objectives}

    def _taxi_node_name(self, node_id, lang: str = 'es') -> str:
        rows = self._rows(
            'SELECT Name_lang, Name_lang_esES FROM TaxiNodes WHERE ID = ? LIMIT 1', (node_id,))
        if not rows:
            return ''
        row = rows[0]
        if lang == 'es':
            return _clean_text(row['Name_lang_esES'] or row['Name_lang'])
        return _clean_text(row['Name_lang'] or row['Name_lang_esES'])

    def _find_taxi_node(self, place, lang: str = 'es'):
        target = normalize(place)
        if not target:
            return None
        candidates = []
        for row in self._rows('SELECT ID, Name_lang, Name_lang_esES FROM TaxiNodes'):
            names = [normalize(row['Name_lang_esES'] or ''), normalize(row['Name_lang'] or '')]
            names = [name for name in names if name]
            if target in names:
                score = 0
            elif any(name.startswith(target + ' ') for name in names):
                score = 1
            elif any((' ' + target) in (' ' + name) for name in names):
                score = 2
            else:
                continue
            candidates.append((score, row['ID'], row))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][2]

    @staticmethod
    def _faction_matches(value, faction) -> bool:
        if faction not in ('A', 'H'):
            return True
        if value is None:
            return True
        return value == ('Alianza' if faction == 'A' else 'Horda')

    def flights_from(self, place, faction, lang: str = 'es', limit: int = 12):
        origin = self._find_taxi_node(place, lang)
        if origin is None:
            return None
        origin_name = (self._taxi_node_name(origin['ID'], lang)
                       or _clean_text(origin['Name_lang']))
        flights = []
        seen = set()
        for row in self._rows(
                'SELECT nodo_destino, destino, coste, faccion FROM v_ruta '
                "WHERE tipo = 'vuelo' AND nodo_origen = ?", (origin['ID'],)):
            if not self._faction_matches(row['faccion'], faction):
                continue
            destination_id = row['nodo_destino']
            if destination_id in seen:
                continue
            seen.add(destination_id)
            destination = (self._taxi_node_name(destination_id, lang)
                           or _clean_text(row['destino']))
            try:
                cost = int(row['coste'] or 0)
            except (TypeError, ValueError):
                cost = 0
            flights.append({
                'destination': destination,
                'cost_copper': cost,
                'cost': self.format_money(cost, lang),
            })
        flights.sort(key=lambda item: item['cost_copper'])
        try:
            limit = max(0, int(limit))
        except (TypeError, ValueError):
            limit = 12
        return {'origin': origin_name, 'flights': flights[:limit]}

    def flight_cost(self, place_a, place_b, faction, lang: str = 'es'):
        origin = self._find_taxi_node(place_a, lang)
        destination = self._find_taxi_node(place_b, lang)
        if origin is None or destination is None:
            return None
        best = None
        for row in self._rows(
                'SELECT coste, faccion FROM v_ruta '
                "WHERE tipo = 'vuelo' AND nodo_origen = ? AND nodo_destino = ?",
                (origin['ID'], destination['ID'])):
            if not self._faction_matches(row['faccion'], faction):
                continue
            try:
                cost = int(row['coste'] or 0)
            except (TypeError, ValueError):
                cost = 0
            if best is None or cost < best:
                best = cost
        if best is None:
            return None
        return {
            'origin': (self._taxi_node_name(origin['ID'], lang)
                       or _clean_text(origin['Name_lang'])),
            'destination': (self._taxi_node_name(destination['ID'], lang)
                            or _clean_text(destination['Name_lang'])),
            'cost_copper': best,
            'cost': self.format_money(best, lang),
        }

    @staticmethod
    def _is_generic_end(*names) -> bool:
        for name in names:
            normalized = normalize(name)
            if normalized.startswith('generic') or normalized.startswith('generico'):
                return True
        return False

    def transports(self, faction, lang: str = 'es'):
        entries = []
        seen = set()
        for row in self._rows(
                'SELECT tipo, nodo_origen, origen, nodo_destino, destino, faccion '
                "FROM v_ruta WHERE lower(tipo) LIKE 'transporte%'"):
            if not self._faction_matches(row['faccion'], faction):
                continue
            raw_origin = _clean_text(row['origen'])
            raw_destination = _clean_text(row['destino'])
            origin = self._taxi_node_name(row['nodo_origen'], lang) or raw_origin
            destination = (self._taxi_node_name(row['nodo_destino'], lang)
                           or raw_destination)
            if not origin or not destination:
                continue
            if self._is_generic_end(origin, destination, raw_origin, raw_destination):
                continue
            key = tuple(sorted((origin, destination)))
            if key in seen:
                continue
            seen.add(key)
            entries.append({'type': _clean_text(row['tipo']), 'origin': origin,
                            'destination': destination})
        entries.sort(key=lambda item: (item['origin'], item['destination']))
        return entries

    def ensure_index(self) -> None:
        """Construye una sola vez el índice de nombres para match_entities."""
        if self._entries is not None:
            return
        entries = []
        by_first = {}

        def add(kind, entity_id, names):
            seen_texts = set()
            for locale, raw_name in names.items():
                text = normalize(raw_name)
                if len(text) < MIN_NAME_LENGTH or text in STOP_NAMES or text in seen_texts:
                    continue
                seen_texts.add(text)
                index = len(entries)
                entries.append({
                    'kind': kind,
                    'id': entity_id,
                    'text': text,
                    'names': names,
                })
                by_first.setdefault(text.split(' ', 1)[0], []).append(index)

        quest_names = {}
        for row in self._rows('SELECT quest_id, locale, name FROM ext_quest_l10n'):
            quest_names.setdefault(row['quest_id'], {})[row['locale']] = row['name']
        for quest_id, names in quest_names.items():
            add('quest', quest_id, names)

        dungeon_names = {}
        for row in self._rows('SELECT area_id, name_enUS, name_esES FROM ext_dungeons'):
            dungeon_names[row['area_id']] = {
                'esES': row['name_esES'], 'enUS': row['name_enUS'],
            }
        for area_id, names in dungeon_names.items():
            add('dungeon', area_id, names)

        spawn_ids = {row['npc_id'] for row in self._rows(
            'SELECT DISTINCT npc_id FROM ext_npc_spawns')}
        npc_names = {}
        for row in self._rows('SELECT npc_id, locale, name FROM ext_npc_l10n'):
            if row['npc_id'] in spawn_ids:
                npc_names.setdefault(row['npc_id'], {})[row['locale']] = row['name']
        for npc_id, names in npc_names.items():
            add('npc', npc_id, names)

        zone_names = {}
        for row in self._rows('SELECT area_id, name_enUS, name_esES FROM ext_zones'):
            zone_names[row['area_id']] = {
                'esES': row['name_esES'], 'enUS': row['name_enUS'],
            }
        for area_id, names in zone_names.items():
            add('zone', area_id, names)

        item_names = {}
        for row in self._rows('SELECT item_id, locale, name FROM ext_item_l10n'):
            item_names.setdefault(row['item_id'], {})[row['locale']] = row['name']
        for item_id, names in item_names.items():
            add('item', item_id, names)

        self._entries = entries
        self._by_first = by_first

    def match_entities(self, text, lang: str = 'es', kinds=KIND_ORDER):
        """Entidades cuyos nombres aparecen como palabras completas en el texto."""
        self.ensure_index()
        normalized = normalize(text)
        if not normalized:
            return []

        kind_order = {kind: index for index, kind in enumerate(kinds)}
        candidates = set()
        for token in set(normalized.split()):
            for index in self._by_first.get(token, ()):
                candidates.add(index)

        matches = []
        for index in candidates:
            entry = self._entries[index]
            if entry['kind'] not in kind_order:
                continue
            length = len(entry['text'])
            position = normalized.find(entry['text'])
            while position >= 0:
                end = position + length
                before_ok = position == 0 or not normalized[position - 1].isalnum()
                after_ok = end == len(normalized) or not normalized[end].isalnum()
                if before_ok and after_ok:
                    matches.append((length, kind_order[entry['kind']], position, end, entry))
                    break
                position = normalized.find(entry['text'], position + 1)

        matches.sort(key=lambda item: (-item[0], item[1], item[2]))
        selected = []
        selected_spans = []
        selected_ids = set()
        for length, _order, start, end, entry in matches:
            if len(selected) >= MAX_MATCHES:
                break
            if (entry['kind'], entry['id']) in selected_ids:
                continue
            if any(start < other_end and end > other_start
                   for other_start, other_end in selected_spans):
                continue
            selected.append((start, end, entry))
            selected_spans.append((start, end))
            selected_ids.add((entry['kind'], entry['id']))

        selected.sort(key=lambda item: item[0])
        return [
            {'kind': entry['kind'], 'id': entry['id'],
             'name': self._pick(entry['names'], lang)}
            for _start, _end, entry in selected
        ]
