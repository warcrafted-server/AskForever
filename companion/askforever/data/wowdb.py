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

        if not name and not vendors and not drops and not rewards:
            return None
        return {
            'id': item_id,
            'name': name,
            'vendors': vendors,
            'drops': drops,
            'quest_rewards': rewards,
        }

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
