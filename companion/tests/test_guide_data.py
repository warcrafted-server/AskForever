"""Valida los archivos de secciones editoriales de la guía."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

from askforever.engine.guide import load_sections

COMPANION_DIR = Path(__file__).resolve().parents[1]
GUIDE_DIR = COMPANION_DIR / 'askforever' / 'data' / 'guide'
GUIDE_JSON = COMPANION_DIR / 'askforever' / 'data' / 'guide.json'
GUIDE_FILES = sorted(GUIDE_DIR.glob('*.json'))

REQUIRED_FIELDS = {
    'id', 'chapter', 'status', 'title_es', 'title_en', 'summary_es',
    'summary_en', 'keywords_es', 'keywords_en', 'text_es', 'text_en',
    'sources', 'updated',
}
SOURCE_FIELDS = {'type', 'ref', 'url', 'date'}
ALLOWED_TAGS = {
    'WARRIOR', 'PALADIN', 'HUNTER', 'ROGUE', 'PRIEST', 'SHAMAN', 'MAGE',
    'WARLOCK', 'DRUID', 'HUMAN', 'ORC', 'DWARF', 'NIGHTELF', 'SCOURGE',
    'TAUREN', 'GNOME', 'TROLL', 'SKYBORNE',
}
KEBAB_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _chapter_sections():
    for path in GUIDE_FILES:
        data = _read(path)
        assert isinstance(data, dict), path
        assert isinstance(data.get('sections'), list), path
        for section in data['sections']:
            yield path, section


def _guide_json_sections():
    data = _read(GUIDE_JSON)
    assert isinstance(data, dict)
    assert isinstance(data.get('sections'), list)
    return data['sections']


@pytest.mark.parametrize('path', GUIDE_FILES, ids=lambda item: item.name)
def test_chapter_file_schema(path):
    data = _read(path)
    assert isinstance(data, dict)
    assert isinstance(data.get('sections'), list)
    for section in data['sections']:
        assert isinstance(section, dict)
        missing = REQUIRED_FIELDS - set(section)
        assert not missing, (path.name, section.get('id'), missing)
        assert isinstance(section['id'], str) and section['id']
        assert KEBAB_RE.fullmatch(section['id']), (path.name, section['id'])
        assert isinstance(section['chapter'], int)
        assert not isinstance(section['chapter'], bool)
        assert section['chapter'] > 0
        assert section['status'] == 'editorial'
        for field in ('title_es', 'title_en'):
            assert isinstance(section[field], str) and section[field].strip()
            assert len(section[field]) <= 60, (section['id'], field)
        for field in ('summary_es', 'summary_en'):
            assert isinstance(section[field], str) and section[field].strip()
            assert len(section[field]) <= 120, (section['id'], field)
        for field in ('text_es', 'text_en'):
            assert isinstance(section[field], str) and section[field].strip()
            assert len(section[field]) <= 600, (section['id'], field)
        for field in ('keywords_es', 'keywords_en'):
            values = section[field]
            assert isinstance(values, list), (section['id'], field)
            assert 3 <= len(values) <= 8, (section['id'], field, len(values))
            assert all(isinstance(value, str) and value.strip()
                       for value in values), (section['id'], field)
        _assert_sources(section)
        assert DATE_RE.match(section['updated']), (section['id'], 'updated')
        date.fromisoformat(section['updated'])
        tags = section.get('tags')
        if tags is not None:
            assert isinstance(tags, list), (section['id'], 'tags')
            assert all(isinstance(tag, str) and tag in ALLOWED_TAGS
                       for tag in tags), (section['id'], tags)
        topics = section.get('topics')
        if topics is not None:
            assert isinstance(topics, list), (section['id'], 'topics')
            assert all(isinstance(topic, str) and topic.strip()
                       for topic in topics), (section['id'], topics)
        source_hashes = section.get('source_hashes')
        if source_hashes is not None:
            assert isinstance(source_hashes, list), (section['id'], 'source_hashes')
            assert all(isinstance(item, str) and (
                item.startswith('section:') or item.startswith('guide:'))
                for item in source_hashes), (section['id'], source_hashes)


def _assert_sources(section):
    sources = section['sources']
    assert isinstance(sources, list) and sources, section['id']
    for source in sources:
        assert isinstance(source, dict), section['id']
        missing = SOURCE_FIELDS - set(source)
        assert not missing, (section['id'], missing)
        assert source['type'] == 'editorial', section['id']
        assert isinstance(source['ref'], str)
        assert source['ref'].startswith('Icy Veins: '), section['id']
        assert isinstance(source['url'], str)
        assert source['url'].startswith('https://'), section['id']
        assert isinstance(source['date'], str)
        assert DATE_RE.match(source['date']), (section['id'], source['date'])
        date.fromisoformat(source['date'])


def test_ids_are_unique_across_guide_files_and_guide_json():
    ids = []
    for _path, section in _chapter_sections():
        ids.append(section['id'])
    for section in _guide_json_sections():
        ids.append(section['id'])
    assert len(ids) == len(set(ids))
    assert len(GUIDE_FILES) >= 1


def test_load_sections_returns_every_section():
    expected = {section['id'] for _path, section in _chapter_sections()}
    expected |= {section['id'] for section in _guide_json_sections()}
    loaded = load_sections()
    loaded_ids = {section['id'] for section in loaded}
    assert expected == loaded_ids


SOURCE_MENTION_RE = re.compile(
    r'\b(?:la página|la guía|según la (?:página|guía|web)|the page|the guide|according to the)\b'
    r'|icy veins|tier list',
    re.IGNORECASE)


@pytest.mark.parametrize('path', GUIDE_FILES, ids=lambda path: path.name)
def test_texts_never_mention_the_source(path):
    # Decisión de Marc: la IA usa estos datos sin citar la fuente; la fuente va solo en sources.
    for section in _read(path)['sections']:
        for field in ('text_es', 'text_en', 'summary_es', 'summary_en', 'title_es', 'title_en'):
            assert not SOURCE_MENTION_RE.search(section[field]), (section['id'], field)
