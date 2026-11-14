"""Informes de desarrollo enviados por el addon."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from askforever import paths
from askforever.paths import dev_dir

_DEFAULT_DEV_DIR = dev_dir
_RID_PATTERN = re.compile(r'^\d{8}-\d{6}-\d{1,5}$')
_REPORT_KINDS = frozenset({'report', 'report-close'})


def reports_dir() -> Path:
    # Se admite parchear dev_dir aquí o en askforever.paths desde las pruebas.
    source = dev_dir
    if source is _DEFAULT_DEV_DIR:
        source = paths.dev_dir
    return source() / 'informes'


def is_report(document) -> bool:
    """True si el documento es un informe de desarrollo."""
    return isinstance(document, dict) and document.get('kind') == 'report'


def valid_rid(value) -> bool:
    """True si el identificador de informe tiene el formato esperado."""
    return isinstance(value, str) and bool(_RID_PATTERN.fullmatch(value))


def parse_report(data) -> dict | None:
    """Devuelve el informe o el cierre de informe aunque la nota vaya vacía."""
    try:
        text = data if isinstance(data, str) else bytes(data).decode('utf-8')
        document = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if isinstance(document, dict) and document.get('kind') in _REPORT_KINDS:
        return document
    return None


def _text(value) -> str:
    return '' if value is None else str(value)


def _display(value, empty='-') -> str:
    text = _text(value).strip()
    return text if text else empty


def _json_text(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return json.dumps(_text(value), ensure_ascii=False, indent=2)


def _format_moment(value) -> str:
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    return _display(value)


def _section(title: str, *lines) -> str:
    content = '\n'.join(_text(line) for line in lines)
    return f'{title}\n{content}'


def _sources_text(exchange) -> str:
    if not isinstance(exchange, dict):
        return '(ninguna)'
    lines = []
    for source in exchange.get('sources') or []:
        lines.append(f'- {_text(source)}')
    titles = exchange.get('web_titles') or []
    if titles:
        lines.append('Web: ' + ', '.join(_text(title) for title in titles))
    return '\n'.join(lines) if lines else '(ninguna)'


def _estado_text(exchange) -> str:
    if not isinstance(exchange, dict):
        return '-'
    if exchange.get('ok'):
        return 'ok'
    detail = _display(exchange.get('detail'), '')
    return f'error: {detail}' if detail else 'error'


def build_report(exchange: dict | None, note: str, report_ctx: dict | None,
                 now: datetime, rid=None) -> str:
    """Construye el informe en texto plano con todas las secciones."""
    exchange = exchange if isinstance(exchange, dict) else None
    blocks = [
        _section('ID', _display(rid if valid_rid(rid) else None, '-')),
        _section('FECHA', _format_moment(now)),
        _section('NOTA', _display(note, '(sin nota)')),
    ]
    if exchange is None:
        blocks.append(_section(
            'PREGUNTA',
            '(no hay ninguna pregunta respondida en esta sesión del companion)',
        ))
    else:
        blocks.append(_section(
            'PREGUNTA',
            _text(exchange.get('question')),
            f"msg_id: {_display(exchange.get('msg_id'))}",
            f"conv: {_display(exchange.get('conv'))}",
            f"idioma: {_display(exchange.get('lang'))}",
            f"hora: {_format_moment(exchange.get('moment'))}",
        ))
    ctx = exchange.get('ctx') if exchange is not None else None
    blocks.append(_section('CONTEXTO DEL JUGADOR', _json_text(ctx)))
    facts = exchange.get('facts_text') if exchange is not None else ''
    blocks.append(_section('DATOS QUE RECIBIÓ LA IA', _display(facts, '(ninguno)')))
    blocks.append(_section('FUENTES', _sources_text(exchange)))
    model = exchange.get('model') if exchange is not None else None
    blocks.append(_section('MODELO', _display(model, '(desconocido)')))
    elapsed = exchange.get('elapsed_ms') if exchange is not None else None
    blocks.append(_section('TIEMPO', f'{elapsed} ms' if elapsed is not None else '-'))
    text = exchange.get('text') if exchange is not None else None
    blocks.append(_section('RESPUESTA', _display(text, '-')))
    blocks.append(_section('ESTADO', _estado_text(exchange)))
    blocks.append(_section('CONTEXTO AL PULSAR EL BOTÓN', _json_text(report_ctx)))
    return '\n\n'.join(blocks) + '\n'


def write_report(exchange, note, report_ctx, directory=None, now=None,
                 rid=None) -> Path:
    """Escribe el informe en UTF-8 y devuelve su ruta."""
    moment = now if isinstance(now, datetime) else datetime.now()
    target = Path(directory) if directory is not None else reports_dir()
    target.mkdir(parents=True, exist_ok=True)
    if valid_rid(rid):
        base = f'informe-{rid}'
    else:
        base = f'informe-{moment:%Y%m%d-%H%M%S}'
    path = target / f'{base}.txt'
    suffix = 2
    while path.exists():
        path = target / f'{base}-{suffix}.txt'
        suffix += 1
    path.write_text(build_report(exchange, note, report_ctx, moment, rid=rid),
                    encoding='utf-8')
    return path


def close_report(rid, directory=None) -> str:
    """Borra los informes del rid dentro de reports_dir."""
    if not valid_rid(rid):
        return 'invalid'
    target = Path(directory) if directory is not None else reports_dir()
    try:
        target_resolved = target.resolve()
    except (OSError, RuntimeError):
        return 'missing'
    if not target.is_dir():
        return 'missing'
    base_name = f'informe-{rid}.txt'
    variant = re.compile(rf'^informe-{re.escape(rid)}-\d+\.txt$')
    deleted = 0
    try:
        entries = list(target.iterdir())
    except OSError:
        return 'missing'
    for path in entries:
        if path.name != base_name and not variant.match(path.name):
            continue
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError):
            continue
        if resolved.parent != target_resolved:
            continue
        try:
            if path.is_file():
                path.unlink()
                deleted += 1
        except OSError:
            continue
    return 'closed' if deleted else 'missing'
