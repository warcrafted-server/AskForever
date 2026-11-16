"""Nombres oficiales en español de España (esES) por ID, desde wowdata, para los enlaces de las guías.

Los enlaces de Wowhead (`wowhead.com/forever/spell=19574`) e Icy Veins (`db.icy-veins.com/wow-forever/spells/19574`)
llevan el ID del juego. Un mismo nombre inglés puede tener varios nombres en español (Bestial Wrath: «Ira de bestias» y
«Cólera de las bestias»), así que el nombre se busca siempre por ID, nunca por el nombre inglés.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WOWDB = REPO_ROOT.parent / 'wowdata' / 'datos' / 'wow.sqlite'

# Enlace Markdown con ID: [Nombre](https://www.wowhead.com/forever/spell=19574) o (…/wow-forever/spells/19574).
LINK = re.compile(
    r'\[(?P<name>[^\]]+)\]\((?P<url>https?://(?:www\.)?(?:wowhead\.com/forever/(?P<wh>[a-z]+)=(?P<whid>\d+)'
    r'|db\.icy-veins\.com/wow-forever/(?P<iv>[a-z]+)/(?P<ivid>\d+))[^)]*)\)')
ICY_TYPES = {'spells': 'spell', 'items': 'item', 'npcs': 'npc', 'quests': 'quest'}

QUERIES = {
    # Si el hechizo es el que enseña una habilidad de armas («Thrown»), manda el nombre de la habilidad
    # («Armas arrojadizas»), no el del hechizo («Lanzado»).
    'spell': ['SELECT k.DisplayName_lang_esES FROM SpellName s JOIN SkillLine k ON k.DisplayName_lang = s.Name_lang '
              'WHERE s.ID = ? AND k.CategoryID = 6 AND k.DisplayName_lang_esES IS NOT NULL',
              'SELECT Name_lang_esES FROM SpellName WHERE ID = ?'],
    'item': ["SELECT name FROM ext_item_l10n WHERE item_id = ? AND locale = 'esES'",
             'SELECT Display_lang_esES FROM ItemSparse WHERE ID = ?'],
    'npc': ["SELECT nombre FROM v_npc WHERE npc_id = ? AND nombre_idioma = 'es'"],
    'quest': ["SELECT titulo FROM v_mision WHERE quest_id = ? AND titulo_idioma = 'es'"],
    'zone': ['SELECT AreaName_lang_esES FROM AreaTable WHERE ID = ?'],
    'skill': ['SELECT DisplayName_lang_esES FROM SkillLine WHERE ID = ?'],
    'faction': ['SELECT Name_lang_esES FROM Faction WHERE ID = ?'],
    'object': ["SELECT name FROM ext_object_l10n WHERE object_id = ? AND locale = 'esES'"],
    'pet': ['SELECT Name_lang_esES FROM CreatureFamily WHERE ID = ?'],
}


def link_entity(match: re.Match) -> tuple[Optional[str], Optional[int]]:
    if match.group('wh'):
        return match.group('wh'), int(match.group('whid'))
    return ICY_TYPES.get(match.group('iv')), int(match.group('ivid'))


class OfficialNames:
    def __init__(self, path: Optional[Path] = None):
        path = Path(path) if path else DEFAULT_WOWDB
        self.conn = sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True) if path.is_file() else None
        self.cache: dict[tuple[str, int], Optional[str]] = {}

    def es(self, kind: Optional[str], entity_id: int) -> Optional[str]:
        if self.conn is None or kind not in QUERIES:
            return None
        key = (kind, entity_id)
        if key not in self.cache:
            name = None
            for query in QUERIES[kind]:
                try:
                    row = self.conn.execute(query, (entity_id,)).fetchone()
                except sqlite3.Error:
                    row = None
                if row and row[0]:
                    name = row[0].strip()
                    break
            self.cache[key] = name
        return self.cache[key]

    def annotate(self, text: str) -> str:
        """Añade «{esES: …}» tras cada enlace con ID cuyo nombre oficial se conoce y difiere del inglés."""
        def repl(match):
            kind, entity_id = link_entity(match)
            name = self.es(kind, entity_id)
            if name and name.lower() != match.group('name').strip().lower():
                return f'{match.group(0)} {{esES: {name}}}'
            return match.group(0)
        return LINK.sub(repl, text)

    def pairs(self, text: str) -> dict[str, str]:
        """{nombre inglés: nombre oficial esES} de los enlaces del texto (el primero gana si se repite)."""
        result = {}
        for match in LINK.finditer(text):
            kind, entity_id = link_entity(match)
            name = self.es(kind, entity_id)
            english = match.group('name').strip()
            if name and english not in result:
                result[english] = name
        return result
