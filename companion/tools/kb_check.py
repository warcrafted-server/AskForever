#!/usr/bin/env python3
"""Comprueba la precisión de las fichas de la guía frente a sus secciones de origen del corpus privado.

    python tools/kb_check.py [archivo.json ...] [--before REV] [--report RUTA]

Para cada ficha avisa de: cifras del texto que no están en sus fuentes, nombres propios (hechizos, habilidades,
objetos) que no están en sus fuentes, nombres en español que no son el oficial esES del ID enlazado en la fuente,
cifras distintas entre español e inglés y, con --before (una revisión de git, p. ej. HEAD), cifras y nombres que
tenía la versión anterior de la ficha y ya no tiene.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kb_names import OfficialNames, TalentBuilds  # noqa: E402

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
GUIDE_DIR = BASE_DIR / 'askforever' / 'data' / 'guide'
DEFAULT_CORPUS = REPO_ROOT / '.agents' / 'corpus' / 'corpus.sqlite'
DEFAULT_REPORT = REPO_ROOT / '.agents' / 'corpus' / 'comprobacion.md'
DEFAULT_WOWDB = REPO_ROOT.parents[1] / 'wowdata' / 'datos' / 'wow.sqlite'

# Diez palabras seguidas iguales a la fuente ya no son un dato suelto, sino una frase copiada.
COPY_WORDS = 10
NUMBER = re.compile(r'(?<![\w.])(\d+(?:[.,]\d+)?)(?![\w])')
# Secuencias de palabras con mayúscula inicial (Aimed Shot, Aspect of the Hawk, Serpent Sting).
NAME = re.compile(r"\b([A-Z][a-z'’]+(?:\s+(?:of the\s+|of\s+|the\s+)?[A-Z][a-z'’]+)*)\b")
SENTENCE_START = re.compile(r'(^|[.!?:;]\s*|\n\s*)$')
LEADING_VERBS = {'Use', 'Cast', 'Keep', 'Pick', 'Take', 'Learn', 'Avoid', 'Gather', 'As', 'Get', 'Put', 'Save', 'Swap',
                 'Apply', 'Open', 'Start', 'Spend', 'Train', 'Buy', 'Craft', 'Tame', 'Feed', 'Turn', 'Set', 'Place'}
COMMON = {
    'Hunter', 'Hunters', 'Warrior', 'Paladin', 'Rogue', 'Priest', 'Shaman', 'Mage', 'Warlock', 'Druid', 'Forever',
    'Alliance', 'Horde', 'The', 'This', 'That', 'With', 'When', 'While', 'Use', 'Your', 'They', 'Their', 'Then',
    'Beast Mastery', 'Marksmanship', 'Survival', 'World', 'Warcraft', 'For', 'From', 'After', 'Before', 'Each',
    'Some', 'Most', 'Only', 'Also', 'Both', 'Pick', 'Take', 'Keep', 'Get', 'Put', 'Many', 'Every', 'Into', 'Once',
    'Note', 'Level', 'Levels', 'Leveling', 'Stamina', 'Agility', 'Intellect', 'Strength', 'Spirit', 'PvE', 'PvP',
    'Classic', 'Season', 'Phase', 'Skyborne', 'Human', 'Humans', 'Dwarf', 'Dwarves', 'Gnome', 'Gnomes', 'Orc', 'Orcs',
    'Troll', 'Trolls', 'Tauren', 'Undead', 'Night Elf', 'Night Elves', 'Stormwind', 'Ironforge', 'Orgrimmar',
    'Undercity', 'Darnassus', 'Thunder Bluff', 'Unlike', 'Since', 'Because', 'Although', 'However', 'Instead',
    'There', 'These', 'Those', 'What', 'Which', 'Where', 'Here', 'Even', 'Just', 'Still', 'More', 'Less', 'Than',
}


def normalize(text: str) -> str:
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    return re.sub(r'\s+', ' ', text.replace('’', "'")).lower()


def numbers(text: str) -> set[str]:
    return {n.replace(',', '.') for n in NUMBER.findall(text or '')}


def names(text: str) -> set[str]:
    found = set()
    text = text or ''
    for match in NAME.finditer(text):
        words = match.group(1).split()
        at_start = bool(SENTENCE_START.search(text[:match.start(1)]))
        # «Use Aimed Shot», «As Fire, …»: el verbo o la palabra que abre la frase no es parte del nombre.
        if words and (words[0] in LEADING_VERBS or (at_start and len(words) == 1)):
            words = words[1:]
        name = ' '.join(words)
        if not name or name in COMMON or (len(words) == 1 and (len(name) < 5 or words[0] in COMMON)):
            continue
        found.add(name)
    return found


def _norm_url(url: str) -> str:
    url = (url or '').strip().lower().split('?')[0].split('#')[0].rstrip('/')
    return re.sub(r'^https?://(www\.)?', '', url)


class Corpus:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)
        self.by_url = {}
        for guide_key, url in self.conn.execute('SELECT guide_key, url FROM guides'):
            self.by_url[_norm_url(url)] = guide_key

    def excluded(self, source: dict) -> bool:
        """True si la fuente es una guía de nivel 20 o 30 (beta, no se usa)."""
        guide_key = self.by_url.get(_norm_url(source.get('url', '')))
        if guide_key is None:
            return False
        row = self.conn.execute('SELECT topic FROM guides WHERE guide_key = ?', (guide_key,)).fetchone()
        return bool(row) and row[0].rsplit(':', 1)[-1] in ('level20', 'level30')

    def source_text(self, source: dict) -> str:
        guide_key = self.by_url.get(_norm_url(source.get('url', '')))
        if guide_key is None:
            return ''
        ref = source.get('ref', '')
        heading = ref.split(' › ', 1)[1].strip().lower() if ' › ' in ref else None
        rows = self.conn.execute('SELECT heading, heading_path, text FROM sections WHERE guide_key = ?',
                                 (guide_key,)).fetchall()
        if heading:
            chosen = [text for head, path, text in rows
                      if (head or '').strip().lower() == heading
                      or (path or '').split(' > ')[-1].strip().lower() == heading]
            if chosen:
                return '\n'.join(chosen)
        return '\n'.join(text for _, _, text in rows)


class GameNames:
    """Nombres de hechizos de clase y talentos de Forever (wowdata), solo para anotar los avisos."""

    def __init__(self, path: Optional[Path]):
        self.names = set()
        if path and path.is_file():
            conn = sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)
            for query in ('SELECT Name_enUS FROM v_hechizos_clase', 'SELECT nombre_en FROM v_talentos_forever',
                          'SELECT Display_lang FROM ItemSparse'):
                try:
                    self.names.update((row[0] or '').lower() for row in conn.execute(query))
                except sqlite3.Error:
                    pass
            conn.close()

    def note(self, name: str) -> str:
        if not self.names:
            return name
        return f'{name} (existe en Forever)' if name.lower() in self.names else f'{name} (NO encontrado en wowdata)'


def _previous_cards(path: Path, rev: str) -> dict:
    try:
        rel = path.resolve().relative_to(REPO_ROOT).as_posix()
        raw = subprocess.run(['git', 'show', f'{rev}:{rel}'], cwd=REPO_ROOT, capture_output=True, check=True).stdout
        return {card['id']: card for card in json.loads(raw.decode('utf-8'))['sections']}
    except (subprocess.CalledProcessError, ValueError, KeyError, json.JSONDecodeError):
        return {}


def check_card(card: dict, corpus: Corpus, previous: Optional[dict],
               game: Optional['GameNames'] = None, official: Optional[OfficialNames] = None) -> list[str]:
    problems = []
    beta = [s['ref'].split(' › ')[0] for s in card.get('sources', []) if corpus.excluded(s)]
    if beta:
        problems.append('cita guías de nivel 20/30 (beta, no se usan): ' + ', '.join(sorted(set(beta))))
    raw_source = '\n'.join(corpus.source_text(s) for s in card.get('sources', []))
    if official is not None:
        # Las builds solo vienen como enlaces al calculador: se descodifican para comprobar sus talentos.
        raw_source = TalentBuilds(official.conn).annotate(raw_source)
    source = normalize(raw_source)
    text_en, text_es = card.get('text_en', ''), card.get('text_es', '')
    if not source:
        problems.append('sin texto de origen en el corpus')
    else:
        missing = sorted(n for n in numbers(text_en) if not re.search(rf'(?<![\d.]){re.escape(n)}(?![\d])', source))
        if missing:
            problems.append('cifras que no están en la fuente: ' + ', '.join(missing))
        unknown = sorted(n for n in names(text_en) if n.lower().replace('’', "'") not in source)
        if unknown:
            problems.append('nombres que no están en la fuente: '
                            + ', '.join(game.note(n) if game else n for n in unknown))
    if source:
        words = re.findall(r"[a-z0-9']+", normalize(text_en))
        source_words = ' '.join(re.findall(r"[a-z0-9']+", source))
        copied = [' '.join(words[i:i + COPY_WORDS]) for i in range(len(words) - COPY_WORDS + 1)
                  if ' '.join(words[i:i + COPY_WORDS]) in source_words]
        if copied:
            problems.append(f'posible copia literal de la fuente: «{copied[0]}…»')
    if official is not None:
        wrong = sorted(f'{english} → «{spanish}»' for english, spanish in official.pairs(raw_source).items()
                       if re.search(rf'\b{re.escape(english.lower())}\b', text_en.lower())
                       and spanish.lower() not in text_es.lower())
        if wrong:
            problems.append('nombre oficial esES que falta en el texto español: ' + ', '.join(wrong))
    if numbers(text_en) != numbers(text_es):
        problems.append(f'cifras distintas EN/ES: EN {sorted(numbers(text_en))} · ES {sorted(numbers(text_es))}')
    if previous:
        lost_numbers = sorted(numbers(previous.get('text_en', '')) - numbers(text_en))
        lost_names = sorted(names(previous.get('text_en', '')) - names(text_en))
        if lost_numbers:
            problems.append('cifras que tenía antes y ya no: ' + ', '.join(lost_numbers))
        if lost_names:
            problems.append('nombres que tenía antes y ya no: ' + ', '.join(lost_names))
    return problems


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('files', nargs='*', type=Path)
    parser.add_argument('--corpus', type=Path, default=DEFAULT_CORPUS)
    parser.add_argument('--before', help='revisión de git con la versión anterior (p. ej. HEAD)')
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT)
    parser.add_argument('--wowdb', type=Path, default=DEFAULT_WOWDB)
    args = parser.parse_args(argv)
    corpus = Corpus(args.corpus)
    game = GameNames(args.wowdb)
    official = OfficialNames(args.wowdb)
    files = args.files or sorted(GUIDE_DIR.glob('*.json'))
    lines, flagged, total = ['# Comprobación de fichas', ''], 0, 0
    for path in files:
        cards = json.loads(path.read_text(encoding='utf-8'))['sections']
        before = _previous_cards(path, args.before) if args.before else {}
        file_lines = []
        for card in cards:
            total += 1
            problems = check_card(card, corpus, before.get(card['id']), game, official)
            if problems:
                flagged += 1
                file_lines.append(f'- `{card["id"]}`')
                file_lines += [f'  - {problem}' for problem in problems]
        if before:
            gone = sorted(set(before) - {card['id'] for card in cards})
            if gone:
                file_lines.append('- Fichas eliminadas: ' + ', '.join(f'`{g}`' for g in gone))
        if file_lines:
            lines += [f'## {path.name}', ''] + file_lines + ['']
    lines.insert(2, f'Fichas: {total} · con avisos: {flagged}\n')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Fichas: {total} · con avisos: {flagged} · informe: {args.report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
