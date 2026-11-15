"""Genera las secciones de prioridad de estadísticas de la guía desde stat-priority.json.

Uso (desde companion/):
    .venv\\Scripts\\python.exe tools\\stat_sections.py

Lee el JSON de prioridades guardado de Icy Veins y las fechas de sus páginas (index.json de las
guías) y escribe askforever/data/guide/04-estadisticas.json con una sección editorial por
especialización. Los nombres españoles de estadísticas son los del cliente (GlobalStrings) y los de
especialización salen de TalentTab.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_SOURCE = REPO / '.agents' / 'plans' / 'guia' / 'fuentes' / 'icy-veins'
DEFAULT_OUT = REPO / 'companion' / 'askforever' / 'data' / 'guide' / '04-estadisticas.json'

CLASSES = {
    'warrior': ('Guerrero', 'Warrior', 'WARRIOR'),
    'paladin': ('Paladín', 'Paladin', 'PALADIN'),
    'hunter': ('Cazador', 'Hunter', 'HUNTER'),
    'rogue': ('Pícaro', 'Rogue', 'ROGUE'),
    'priest': ('Sacerdote', 'Priest', 'PRIEST'),
    'shaman': ('Chamán', 'Shaman', 'SHAMAN'),
    'mage': ('Mago', 'Mage', 'MAGE'),
    'warlock': ('Brujo', 'Warlock', 'WARLOCK'),
    'druid': ('Druida', 'Druid', 'DRUID'),
}
ROLES = {
    'ranged-dps': ('daño a distancia', 'ranged DPS'),
    'melee-dps': ('daño cuerpo a cuerpo', 'melee DPS'),
    'melee-dps-and-tank': ('daño cuerpo a cuerpo y tanque', 'melee DPS and tank'),
    'healer': ('sanador', 'healer'),
    'tank': ('tanque', 'tank'),
}
# Nombres del cliente en español (GlobalStrings: STAT_*, SPELL_STAT*_NAME, ITEM_MOD_*).
STATS_ES = {
    'critical strike': 'Golpe crítico',
    'critical strike chance': 'Prob. de golpe crítico',
    'intellect': 'Inteligencia',
    'spell power': 'Poder con hechizos',
    'spirit': 'Espíritu',
    'mp5': 'Regeneración de maná cada 5 s',
    'agility': 'Agilidad',
    'hit chance': 'Prob. de golpe',
    'strength': 'Fuerza',
    'weapon damage': 'Daño del arma',
    'weapon dps': 'DPS del arma',
    'healing power': 'Sanación con hechizos',
    'expertise': 'Pericia',
    'haste': 'Celeridad',
    'attack power': 'Poder de ataque',
    'stamina': 'Aguante',
    'defense': 'Defensa',
    'spell pierce': 'Perforación de hechizo',
    'weapon skill': 'Habilidad con armas',
}
_STAT_RE = re.compile(r'^\s*([A-Za-z0-9 ]+?)\s*(?:\(?\s*(.*?)\)?)?\s*$')


def split_stat(raw: str):
    """«Hit Chance (to 17%)» -> ('hit chance', 'to 17%'); tolera «Hit Chance8%)»."""
    text = raw.strip()
    match = re.match(r'^(.*?)\s*\((.*)\)\s*$', text)
    if match:
        return match.group(1).strip().lower(), match.group(2).strip()
    match = re.match(r'^([A-Za-z ]+?)(\d[\d.,]*%)\)?$', text)
    if match:
        return match.group(1).strip().lower(), match.group(2)
    return text.lower(), ''


def _note_es(note: str) -> str:
    note = note.replace('to ', 'hasta ').replace(' or ', ' o ')
    note = re.sub(r'(\d)\.(\d)', r'\1,\2', note)
    return re.sub(r'(\d)%', r'\1 %', note)


def stat_label(raw: str, lang: str) -> str:
    key, note = split_stat(raw)
    if lang == 'es':
        name = STATS_ES.get(key)
        if name is None:
            raise KeyError(f'Estadística sin traducción: {raw!r}')
        return f'{name} ({_note_es(note)})' if note else name
    name = ' '.join(word.capitalize() if word != 'mp5' else 'MP5' for word in key.split())
    return f'{name} ({note})' if note else name


def parse_slug(slug: str):
    """affliction-warlock-ranged-dps-pve-stat-priority -> ('affliction', 'warlock', role)."""
    core = slug.removesuffix('-pve-stat-priority')
    for class_slug in CLASSES:
        marker = f'-{class_slug}-'
        if marker in core:
            spec, role = core.split(marker, 1)
            if role not in ROLES:
                raise KeyError(f'Rol desconocido en {slug!r}')
            return spec, class_slug, role
    raise KeyError(f'Clase desconocida en {slug!r}')


def spec_names(conn) -> dict:
    names = {}
    for name_en, name_es in conn.execute('SELECT Name_lang, Name_lang_esES FROM TalentTab'):
        if name_en and name_es:
            names[name_en.strip().lower()] = name_es.strip()
    return names


def page_dates(source: Path) -> dict:
    index = json.loads((source / 'guides' / 'index.json').read_text(encoding='utf-8'))
    return {item['slug']: str(item.get('dateModified') or '')[:10] for item in index}


def build_section(entry: dict, specs: dict, dates: dict, today: str) -> dict:
    spec_slug, class_slug, role = parse_slug(entry['slug'])
    class_es, class_en, tag = CLASSES[class_slug]
    spec_en = ' '.join(word.capitalize() for word in spec_slug.split('-'))
    # En el cliente la rama es «Feral Combat» / «Combate feral».
    spec_es = specs.get(spec_en.lower()) or specs.get(f'{spec_en.lower()} combat')
    if not spec_es:
        raise KeyError(f'Especialización sin nombre español: {spec_en!r}')
    role_es, role_en = ROLES[role]
    order_es = ' > '.join(stat_label(stat, 'es') for stat in entry['priority'])
    order_en = ' > '.join(stat_label(stat, 'en') for stat in entry['priority'])
    date_modified = dates.get(entry['slug'])
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_modified or ''):
        raise KeyError(f'Sin fecha de página para {entry["slug"]!r}')
    lower_spec_es = spec_es.lower()
    lower_class_es = class_es.lower()
    return {
        'id': f'clase-{class_slug}-estadisticas-{spec_slug}',
        'chapter': 4,
        'status': 'editorial',
        'title_es': f'Estadísticas de {class_es} {spec_es}'[:60],
        'title_en': f'{spec_en} {class_en} stat priority'[:60],
        'summary_es': f'Qué estadísticas priorizar como {class_es} {spec_es} ({role_es}) en JcE.'[:120],
        'summary_en': f'Which stats to prioritise as a {spec_en} {class_en} ({role_en}) in PvE.'[:120],
        'keywords_es': [
            f'estadisticas {lower_spec_es}',
            f'stats {lower_spec_es}',
            f'prioridad de estadisticas {lower_class_es}',
            f'que estadisticas {lower_class_es}',
            f'stats {lower_class_es}',
        ],
        'keywords_en': [
            f'{spec_en.lower()} stats',
            f'{spec_en.lower()} stat priority',
            f'{class_en.lower()} stat priority',
            f'{class_en.lower()} stats',
        ],
        'tags': [tag],
        'text_es': (f'Prioridad de estadísticas para {class_es} {spec_es} ({role_es}, JcE), de '
                    f'más a menos importante: {order_es}.'),
        'text_en': (f'Stat priority for {spec_en} {class_en} ({role_en}, PvE), from most to least '
                    f'important: {order_en}.'),
        'sources': [{
            'type': 'editorial',
            'ref': f'Icy Veins: {entry["title"]}',
            'url': entry['url'],
            'date': date_modified,
        }],
        'updated': today,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--db', type=Path, default=None)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    db_path = args.db
    if db_path is None:
        sys.path.insert(0, str(REPO / 'companion'))
        from askforever.config import get_wowdata_path
        db_path = get_wowdata_path()
    if db_path is None:
        print('No se encuentra la base de wowdata.', file=sys.stderr)
        return 2
    conn = sqlite3.connect(f'file:{Path(db_path).resolve().as_posix()}?mode=ro', uri=True)
    try:
        specs = spec_names(conn)
    finally:
        conn.close()
    entries = json.loads((args.source / 'stat-priority.json').read_text(encoding='utf-8'))
    dates = page_dates(args.source)
    today = date.today().isoformat()
    sections = [build_section(entry, specs, dates, today)
                for entry in sorted(entries, key=lambda item: item['slug'])]
    payload = {
        'description': ('Capítulo 4: clases. Prioridad de estadísticas por especialización '
                        '(editorial, generada con tools/stat_sections.py).'),
        'sections': sections,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
                        encoding='utf-8', newline='\n')
    print(f'Secciones escritas: {len(sections)} en {args.out.name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
