"""Comprueba que las secciones de la guía usan los nombres oficiales en español.

Uso (desde companion/):
    .venv\\Scripts\\python.exe tools\\check_guide_names.py [archivo.json ...]

Busca en el texto inglés de cada sección nombres de objetos, hechizos y PNJ del cliente (de dos o
más palabras) y avisa si el texto español no contiene su nombre oficial (el nombre inglés no vale). Sin argumentos revisa
todos los archivos de askforever/data/guide/. Sale con código 1 si encuentra alguno.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPANION = HERE.parent
sys.path.insert(0, str(COMPANION))

from askforever.config import open_wowdata  # noqa: E402
from askforever.data.wowdb import normalize  # noqa: E402

GUIDE_DIR = COMPANION / 'askforever' / 'data' / 'guide'
QUERIES = (
    ('objeto', "SELECT e.name, s.name FROM ext_item_l10n e JOIN ext_item_l10n s "
               "ON s.item_id = e.item_id AND s.locale = 'esES' WHERE e.locale = 'enUS'"),
    ('hechizo', 'SELECT Name_lang, Name_lang_esES FROM SpellName'),
    ('PNJ', "SELECT e.name, s.name FROM ext_npc_l10n e JOIN ext_npc_l10n s "
            "ON s.npc_id = e.npc_id AND s.locale = 'esES' WHERE e.locale = 'enUS'"),
    # Las ramas de talentos también son nombres oficiales («Beast Mastery» es la rama «Dominio
    # de bestias» y el hechizo «Maestría en bestias»).
    ('rama', 'SELECT Name_lang, Name_lang_esES FROM TalentTab'),
)


def official_names(db) -> dict:
    """Nombre inglés normalizado -> (tipo, nombres españoles posibles)."""
    names = {}
    for kind, sql in QUERIES:
        for english, spanish in db._rows(sql) or []:
            if not english or not spanish or ' ' not in english.strip():
                continue
            key = normalize(english)
            if len(key) < 8:
                continue
            entry = names.setdefault(key, (kind, english, set()))
            entry[2].add(spanish.strip())
    return names


def _words(text: str) -> str:
    return ' ' + ' '.join(re.findall(r'[a-z0-9]+', normalize(text))) + ' '


def check_section(section: dict, names: dict) -> list:
    english = _words(section.get('text_en') or '')
    spanish = _words(section.get('text_es') or '')
    found = {}
    for key, (kind, original, spanish_names) in names.items():
        needle = ' ' + ' '.join(re.findall(r'[a-z0-9]+', key)) + ' '
        if needle in english:
            found[needle] = (kind, original, spanish_names,
                             any(_words(name) in spanish for name in spanish_names))
    problems = []
    for needle, (kind, original, spanish_names, ok) in found.items():
        if ok:
            continue
        # «Mountain Lion» dentro de «Starving Mountain Lion»: vale si el nombre largo ya está bien.
        if any(needle != other and needle in other and found[other][3] for other in found):
            continue
        # Nunca vale dejar el nombre inglés: el español debe ser el oficial esES del cliente.
        problems.append(f"{section.get('id')}: {kind} «{original}» -> en español: "
                        + ' / '.join(sorted(spanish_names)))
    return problems


def main(argv=None) -> int:
    files = [Path(arg) for arg in (argv if argv is not None else sys.argv[1:])]
    if not files:
        files = sorted(GUIDE_DIR.glob('*.json'))
    db = open_wowdata()
    if db is None:
        print('No se encuentra la base de wowdata.', file=sys.stderr)
        return 2
    names = official_names(db)
    problems = []
    for path in files:
        data = json.loads(path.read_text(encoding='utf-8'))
        for section in data.get('sections', []):
            problems += [f'{path.name} · {line}' for line in check_section(section, names)]
    for line in problems:
        print(line)
    print(f'Nombres por revisar: {len(problems)}')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
