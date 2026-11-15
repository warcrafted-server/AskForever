"""Comparador de proveedores y modelos con un cuestionario fijo de WoW."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from askforever import config
from askforever.engine import router
from askforever.engine.answer import web_fallback
from askforever.engine.conversation import Turn
from askforever.engine.prompt import build_prompt
from askforever.engine.retriever import add_guide_sections, retrieve
from askforever.providers.openai_compat import ProviderError, provider_from_config

DEFAULT_QUESTIONS = Path(__file__).resolve().parent.parent / 'bench' / 'questions.es.json'
DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / 'tools' / 'out'
RATE_LIMIT_STREAK = 3
SKIP_RATE_LIMIT = 'límite de uso alcanzado'
MAX_CHAIN_TURNS = 4


@dataclass
class Question:
    """Pregunta del cuestionario con su contexto ya mezclado."""

    id: str
    category: str
    lang: str
    text: str
    ctx: dict
    notes: str
    chain: Optional[str] = None


@dataclass
class Target:
    """Proveedor y modelo opcional a comparar."""

    provider: str
    model: Optional[str] = None

    def __str__(self) -> str:
        return f'{self.provider}:{self.model}' if self.model else self.provider


@dataclass
class Result:
    """Resultado de una llamada (o de una llamada que no se llegó a hacer)."""

    question_id: str
    target: str
    ok: bool
    text: str
    latency_ms: int
    error_kind: str = ''
    error_detail: str = ''
    skipped: bool = False
    sources: list[str] = field(default_factory=list)
    web_titles: list[str] = field(default_factory=list)
    router: str = 'off'


def parse_target(text: str) -> Target:
    """Interpreta 'proveedor' o 'proveedor:modelo' (el modelo puede llevar ':' y '/')."""
    text = (text or '').strip()
    if not text:
        raise ValueError('Objetivo vacío: usa proveedor:modelo')
    provider, separator, model = text.partition(':')
    provider = provider.strip()
    model = model.strip() if separator else ''
    if not provider:
        raise ValueError(f'Objetivo inválido: {text}')
    return Target(provider, model or None)


def load_questions(path=None) -> list[Question]:
    """Carga el cuestionario y mezcla el contexto por defecto con el de cada pregunta."""
    file_path = Path(path) if path else DEFAULT_QUESTIONS
    try:
        data = json.loads(file_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f'No se pudo leer el cuestionario {file_path}: {error}') from error
    if not isinstance(data, dict):
        raise ValueError('El cuestionario debe ser un objeto JSON')

    default_ctx = data.get('default_ctx')
    if not isinstance(default_ctx, dict):
        raise ValueError('Falta default_ctx en el cuestionario')
    raw_questions = data.get('questions')
    if not isinstance(raw_questions, list) or not raw_questions:
        raise ValueError('Falta la lista de preguntas en el cuestionario')

    questions = []
    for index, item in enumerate(raw_questions):
        if not isinstance(item, dict):
            raise ValueError(f'Pregunta {index + 1} inválida')
        identifier = item.get('id')
        category = item.get('category')
        text = item.get('q')
        notes = item.get('notes')
        for name, value in (('id', identifier), ('category', category),
                            ('q', text), ('notes', notes)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'Pregunta {index + 1}: falta el campo {name}')
        lang = item.get('lang') or 'esES'
        own_ctx = item.get('ctx')
        if own_ctx is None:
            own_ctx = {}
        elif not isinstance(own_ctx, dict):
            raise ValueError(f'Pregunta {identifier}: ctx debe ser un objeto')
        chain = item.get('chain')
        if not isinstance(chain, str) or not chain.strip():
            chain = None
        else:
            chain = chain.strip()
        merged = dict(default_ctx)
        merged.update(own_ctx)
        questions.append(Question(identifier, category, lang, text, merged, notes, chain))
    return questions


def build_message(question: Question) -> dict:
    """Mensaje en el formato de la tira para construir el prompt."""
    return {
        'v': 1,
        'lang': question.lang,
        'q': question.text,
        'ctx': dict(question.ctx),
    }


def _skipped(question: Question, target: str, kind: str, detail: str) -> Result:
    return Result(question.id, target, False, '', 0,
                  error_kind=kind, error_detail=detail, skipped=True)


def run_bench(
    questions,
    targets,
    *,
    provider_factory: Callable = provider_from_config,
    repeat: int = 1,
    pause: float = 1.5,
    max_tokens=None,
    db=None,
    web=None,
    temperature=None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    on_progress: Optional[Callable] = None,
) -> list[Result]:
    """Lanza las preguntas contra cada objetivo y devuelve todos los resultados."""
    repeat = max(1, int(repeat))
    if temperature is None:
        temperature = config.get_temperature()
    total = len(questions) * len(targets) * repeat
    results = []
    index = 0
    calls = 0

    def emit(target, question, result):
        nonlocal index
        index += 1
        results.append(result)
        if on_progress is not None:
            on_progress(index, total, target, question, result)

    for target in targets:
        target_name = str(target)
        try:
            provider = provider_factory(provider=target.provider, model=target.model)
            failure = None
        except ProviderError as error:
            provider = None
            failure = (error.kind, error.detail)
        except Exception as error:
            provider = None
            failure = ('unknown', str(error))

        if provider is None:
            for question in questions:
                for _ in range(repeat):
                    emit(target, question, _skipped(question, target_name, failure[0], failure[1]))
            continue

        streak = 0
        aborted = False
        chain_name = None
        chain_turns = []
        for question in questions:
            question_chain = getattr(question, 'chain', None)
            if question_chain != chain_name:
                chain_name = question_chain
                chain_turns = []
            history = list(chain_turns[-MAX_CHAIN_TURNS:]) if chain_name else []
            previous_question = history[-1].question if history else None
            skip_question = aborted
            for _ in range(repeat):
                if skip_question:
                    emit(target, question,
                         _skipped(question, target_name, 'rate_limit', SKIP_RATE_LIMIT))
                    continue

                if calls:
                    sleep(pause)
                calls += 1
                message = build_message(question)
                facts_obj = None
                facts_text = ''
                sources = []
                router_outcome = 'off'
                started = clock()
                if db is not None:
                    try:
                        facts_obj = retrieve(message, db)
                        if not facts_obj.lines and not facts_obj.missing and previous_question:
                            follow_message = dict(message)
                            follow_message['q'] = f'{previous_question} {question.text}'.strip()
                            follow = retrieve(follow_message, db)
                            if follow.lines or follow.missing:
                                facts_obj = follow
                        if (getattr(facts_obj, 'guide_eligible', False)
                                and config.get_guide_router_enabled()):
                            try:
                                ids = router.route(provider, question.text, question.lang,
                                                   question.ctx, history)
                                if ids:
                                    add_guide_sections(facts_obj, db, ids, question.lang)
                                    router_outcome = 'ok:' + ','.join(ids)
                                elif ids == []:
                                    router_outcome = 'empty'
                                else:
                                    router_outcome = 'fallback'
                            except Exception:
                                router_outcome = 'fallback'
                        sources = list(facts_obj.sources)
                        facts_text = facts_obj.render(question.lang)
                    except Exception:
                        facts_obj = None
                        facts_text, sources = '', []
                        router_outcome = 'off'
                web_excerpts, web_titles = web_fallback(
                    web, provider, message, facts_obj, question.text, history=history,
                    previous_question=previous_question)
                for title in web_titles:
                    source = f'wiki:{title}'
                    if source not in sources:
                        sources.append(source)
                system, user = build_prompt(message, facts_text, history=history,
                                            web_excerpts=web_excerpts or None)
                try:
                    text = provider.chat(system, user, max_tokens=max_tokens,
                                         temperature=temperature)
                    latency = int((clock() - started) * 1000)
                    result = Result(question.id, target_name, True, text, latency,
                                    sources=sources, web_titles=web_titles,
                                    router=router_outcome)
                    streak = 0
                    if chain_name:
                        chain_turns.append(Turn(question.text, text, facts_text))
                        if len(chain_turns) > MAX_CHAIN_TURNS:
                            chain_turns = chain_turns[-MAX_CHAIN_TURNS:]
                except ProviderError as error:
                    latency = int((clock() - started) * 1000)
                    result = Result(question.id, target_name, False, '', latency,
                                    error_kind=error.kind, error_detail=error.detail,
                                    sources=sources, web_titles=web_titles,
                                    router=router_outcome)
                    if error.kind == 'rate_limit':
                        streak += 1
                    else:
                        streak = 0
                    if streak >= RATE_LIMIT_STREAK:
                        aborted = True
                except Exception as error:
                    latency = int((clock() - started) * 1000)
                    result = Result(question.id, target_name, False, '', latency,
                                    error_kind='unknown', error_detail=str(error),
                                    sources=sources, web_titles=web_titles,
                                    router=router_outcome)
                    streak = 0

                emit(target, question, result)
                if aborted:
                    skip_question = True
    return results


def _median(values):
    count = len(values)
    middle = count // 2
    if count % 2:
        return float(values[middle])
    return (values[middle - 1] + values[middle]) / 2


def summarize(results) -> list[dict]:
    """Resumen por objetivo: respondidas, errores, saltadas y latencias."""
    rows = {}
    order = []
    for result in results:
        if result.target not in rows:
            rows[result.target] = {
                'target': result.target,
                'answered': 0,
                'errors': 0,
                'skipped': 0,
                'latencies': [],
            }
            order.append(result.target)
        row = rows[result.target]
        if result.skipped:
            row['skipped'] += 1
        elif result.ok:
            row['answered'] += 1
            row['latencies'].append(result.latency_ms)
        else:
            row['errors'] += 1

    summary = []
    for target in order:
        row = rows[target]
        latencies = sorted(row['latencies'])
        summary.append({
            'target': target,
            'answered': row['answered'],
            'errors': row['errors'],
            'skipped': row['skipped'],
            'mean_ms': (sum(latencies) / len(latencies)) if latencies else None,
            'median_ms': _median(latencies) if latencies else None,
            'max_ms': max(latencies) if latencies else None,
        })
    return summary


def _ms_text(value) -> str:
    return '-' if value is None else f'{value:.1f}'


def render_markdown(questions, targets, results, started: str, used_database=False,
                    temperature=None) -> str:
    """Informe Markdown con la tabla resumen y todas las respuestas para puntuar."""
    if temperature is None:
        temperature = config.get_temperature()
    lines = [
        '# Comparador de modelos de AskForever',
        '',
        f'Fecha: {started}',
        f'Base de datos: {"usada" if used_database else "no usada"}',
        f'Temperatura: {temperature}',
        '',
        '## Resumen',
        '',
        '| Objetivo | Respondidas | Errores | Saltadas | Media ms | Mediana ms | Máx ms |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for row in summarize(results):
        lines.append(
            f"| {row['target']} | {row['answered']} | {row['errors']} | "
            f"{row['skipped']} | {_ms_text(row['mean_ms'])} | "
            f"{_ms_text(row['median_ms'])} | {_ms_text(row['max_ms'])} |"
        )

    for question in questions:
        heading = f'## {question.id} · {question.category}'
        chain = getattr(question, 'chain', None)
        if chain:
            heading += f' · cadena {chain}'
        lines += [
            '',
            heading,
            '',
            f'**Pregunta:** {question.text}',
            '',
            f'**Qué comprobar:** {question.notes}',
            '',
        ]
        for target in targets:
            target_name = str(target)
            matches = [result for result in results
                       if result.question_id == question.id and result.target == target_name]
            if not matches:
                continue
            lines += [f'### {target_name}', '']
            for number, result in enumerate(matches, start=1):
                if len(matches) > 1:
                    lines += [f'**Repetición {number}**', '']
                lines.append(f'- Latencia: {result.latency_ms} ms')
                lines.append(f'- Router: {result.router or "off"}')
                if result.skipped:
                    detail = result.error_detail or result.error_kind
                    lines.append(f'- Estado: SALTADA: {detail}')
                elif result.ok:
                    lines.append('- Estado: OK')
                    lines += ['', '````', result.text, '````', '']
                else:
                    lines.append(f'- Estado: ERROR {result.error_kind}')
                    if result.error_detail:
                        lines.append(f'- Detalle: {result.error_detail}')
                sources = ', '.join(result.sources) if result.sources else 'ninguno'
                lines.append(f'- Datos usados: {sources}')
                if result.web_titles:
                    lines.append(f"- Fuente web: {', '.join(result.web_titles)}")
                lines += ['', 'Puntuación (1-5): ___', '']

    lines += ['', '## Conclusión', '', '']
    return '\n'.join(lines)


def save_report(markdown, results, out_dir=None, used_database=False, temperature=None):
    """Guarda el informe Markdown y los datos JSON en tools/out."""
    if temperature is None:
        temperature = config.get_temperature()
    directory = Path(out_dir) if out_dir else DEFAULT_OUT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    md_path = directory / f'bench_{stamp}.md'
    json_path = directory / f'bench_{stamp}.json'
    md_path.write_text(markdown, encoding='utf-8')
    payload = {
        'used_database': used_database,
        'temperature': temperature,
        'results': [asdict(result) for result in results],
        'summary': summarize(results),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return md_path, json_path
