# NIR Intelligence Platform - Final project report builder (OP11)
# Renders the final comprehensive project report as a self-contained HTML
# document: overview, one section per agent (content + metrics), original
# data, source code, evaluation and embedded charts (matplotlib PNG as
# base64 data URLs). Works without the quarto binary; the qmd template
# rendering stays the single-file path (OP7).
import base64
import html
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.ProjectReport")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_FILES = [
    'services/project_ingest.py',
    'services/project_crew.py',
    'services/project_report.py',
]

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:  # charts are optional; the report stays complete
    MATPLOTLIB_AVAILABLE = False


def _figure_to_data_url(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=110, bbox_inches='tight')
    plt.close(fig)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def spectrum_chart_data_url(datasets: List[Dict[str, Any]]) -> str:
    """One line per usable dataset (measurement data graphic, MO 6).
    Uses the full measurement series when available (full_series), otherwise
    the 64-point preparation preview. Returns '' without preview data or
    matplotlib."""
    if not MATPLOTLIB_AVAILABLE or not datasets:
        return ''
    usable = []
    for d in datasets:
        if d.get('wavelengths'):
            usable.append({'file_name': d.get('file_name', 'Datensatz'),
                          'wavelengths': d['wavelengths'],
                          'intensities': d.get('intensities', [])})
        elif d.get('preview', {}).get('wavelengths'):
            preview = d['preview']
            usable.append({'file_name': d.get('file_name', 'Datensatz'),
                          'wavelengths': preview['wavelengths'],
                          'intensities': preview.get('intensities', [])})
    if not usable:
        return ''
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for dataset in usable:
        ax.plot(dataset['wavelengths'],
                dataset['intensities'],
                label=str(dataset['file_name']))
    ax.set_xlabel('Wellenlänge (nm)')
    ax.set_ylabel('Intensität')
    ax.set_title('Messdaten aller Datensätze')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    return _figure_to_data_url(fig)


def single_spectrum_chart_data_url(wavelengths: List[Any],
                                   intensities: List[Any],
                                   title: str = 'Spektrum') -> str:
    """One line for one spectrum - used on the database detail page to
    visualise a persisted SpectrumRecord. Returns '' without matplotlib."""
    if not MATPLOTLIB_AVAILABLE or not wavelengths or not intensities:
        return ''
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(wavelengths, intensities, color='#0d6efd')
    ax.set_xlabel('Wellenlänge (nm)')
    ax.set_ylabel('Intensität')
    ax.set_title(title)
    ax.grid(alpha=0.3)
    return _figure_to_data_url(fig)


def _quality_score(section: Dict[str, Any]) -> Optional[float]:
    """Extract a 0-100 quality score from a per-agent section."""
    data = section.get('data') or {}
    for key in ('quality_score', 'overall_quality_score', 'similarity_score',
                'r2_score', 'score'):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, (int, float)):
            return float(value) * 100 if 0 <= value <= 1 else float(value)
    return None


def quality_bar_chart_data_url(per_agent: List[Dict[str, Any]]) -> str:
    """Horizontal bar chart of the per-agent quality scores (evaluation)."""
    if not MATPLOTLIB_AVAILABLE:
        return ''
    scored = []
    for section in per_agent:
        score = _quality_score(section)
        if score is not None:
            scored.append((str(section.get('title', section.get('agent', '?'))), score))
    if not scored:
        return ''
    fig, ax = plt.subplots(figsize=(7, max(2.2, 0.55 * len(scored))))
    names = [s[0] for s in scored]
    values = [s[1] for s in scored]
    ax.barh(names, values, color='#3b7dd8')
    ax.set_xlim(0, 105)
    ax.set_xlabel('Qualitäts-Score (0-100)')
    ax.set_title('Auswertungsbewertung je Agent')
    ax.invert_yaxis()
    for index, value in enumerate(values):
        ax.text(min(value, 100) + 1.5, index, f'{value:.1f}', va='center', fontsize=8)
    return _figure_to_data_url(fig)


def _escape(value: Any) -> str:
    return html.escape('' if value is None else str(value))


def _metric_rows(data: Any, prefix: str = '') -> List[Any]:
    """Flatten agent data to (key, value) rows, two levels deep."""
    rows: List[Any] = []
    if not isinstance(data, dict):
        return rows
    for key, value in data.items():
        label = f'{prefix}{key}'
        if isinstance(value, dict):
            rows.extend(_metric_rows(value, f'{label}.'))
        elif isinstance(value, (bool, int, float, str)) or value is None:
            rows.append((label, value))
        elif isinstance(value, list) and all(
                isinstance(i, (bool, int, float, str)) for i in value):
            text = ', '.join(str(i) for i in value[:8])
            if len(value) > 8:
                text += f' … ({len(value)} Einträge)'
            rows.append((label, text))
    return rows


def _style() -> str:
    return """
body { font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; margin: 0;
       background: #f4f6f9; color: #212529; }
.container { max-width: 960px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 1.7rem; margin-bottom: 4px; }
h2 { font-size: 1.25rem; margin-top: 36px; border-bottom: 2px solid #3b7dd8;
     padding-bottom: 6px; }
h3 { font-size: 1.05rem; margin-top: 20px; }
.card { background: #fff; border: 1px solid #dee2e6; border-radius: 8px;
        padding: 16px 20px; margin: 14px 0; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 12px;
         font-size: 0.78rem; color: #fff; }
.badge-ok { background: #2a9d5c; } .badge-fail { background: #d64545; }
table { border-collapse: collapse; width: 100%; font-size: 0.88rem; }
th, td { border: 1px solid #dee2e6; padding: 4px 8px; text-align: left; }
th { background: #eef2f7; }
.kpi { display: flex; flex-wrap: wrap; gap: 12px; margin: 12px 0; }
.kpi div { background: #fff; border: 1px solid #dee2e6; border-radius: 8px;
           padding: 10px 18px; text-align: center; min-width: 120px; }
.kpi .value { font-size: 1.4rem; font-weight: 600; }
.kpi .label { color: #6c757d; font-size: 0.8rem; }
img.chart { max-width: 100%; height: auto; border: 1px solid #dee2e6;
            border-radius: 6px; background: #fff; }
pre.code { background: #212529; color: #e9ecef; padding: 14px; border-radius: 6px;
           overflow: auto; font-size: 0.78rem; max-height: 420px; }
details { margin: 10px 0; } summary { cursor: pointer; font-weight: 600; }
ul { padding-left: 20px; } .muted { color: #6c757d; }
"""


def _kpi_row(items: List[Any]) -> str:
    cells = ''.join(
        f'<div><div class="value">{_escape(value)}</div>'
        f'<div class="label">{_escape(label)}</div></div>'
        for label, value in items)
    return f'<div class="kpi">{cells}</div>'


def _agent_section_html(section: Dict[str, Any]) -> str:
    status = section.get('status', 'failed')
    badge = ('badge-ok' if status == 'completed' else 'badge-fail')
    rows = _metric_rows(section.get('data', {}))
    table = ''
    if rows:
        body = ''.join(f'<tr><th>{_escape(k)}</th><td>{_escape(v)}</td></tr>'
                       for k, v in rows)
        table = f'<table><thead><tr><th>Feld</th><th>Wert</th></tr></thead>' \
                f'<tbody>{body}</tbody></table>'
    recommendations = section.get('recommendations') or \
        (section.get('data', {}) or {}).get('recommendations') or []
    recs = ''
    if recommendations:
        items = ''.join(f'<li>{_escape(r)}</li>' for r in recommendations)
        recs = f'<h3>Empfehlungen</h3><ul>{items}</ul>'
    charts_html = ''
    charts = section.get('charts') or {}
    if charts:
        imgs = ''.join(
            f'<img src="{_escape(url)}" alt="PCA {_escape(k)}" '
            f'style="max-width:100%;height:auto;margin:6px;">'
            for k, url in charts.items() if url)
        note = _escape(section.get('charts_note') or 'PCA-Diagramme')
        charts_html = f'<h3>{note}</h3>{imgs}'
    return (f'<div class="card"><h3>{_escape(section.get("title", section.get("agent", "Agent")))} '
            f'<span class="badge {badge}">{_escape(status)}</span></h3>'
            f'{table}{charts_html}{recs}</div>')


def _original_data_html(datasets: List[Dict[str, Any]]) -> str:
    parts = []
    for dataset in datasets:
        preview = dataset.get('preview', {})
        wavelengths = dataset.get('wavelengths') or preview.get('wavelengths', [])
        intensities = dataset.get('intensities') or preview.get('intensities', [])
        rows = ''.join(
            f'<tr><td>{_escape(w)}</td><td>{_escape(i)}</td></tr>'
            for w, i in list(zip(wavelengths, intensities))[:50])
        note = (f'{len(wavelengths)} Punkte, die ersten 50 angezeigt'
                if len(wavelengths) > 50 else f'{len(wavelengths)} Punkte')
        parts.append(
            f'<div class="card"><h3>{_escape(dataset.get("file_name", "Datensatz"))} '
            f'<span class="muted">({_escape(note)})</span></h3>'
            f'<table><thead><tr><th>Wellenlänge (nm)</th><th>Intensität</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')
    return ''.join(parts)


def _source_code_html() -> str:
    parts = []
    for rel_path in SOURCE_FILES:
        path = PROJECT_ROOT / rel_path
        if not path.exists():
            continue
        code = _escape(path.read_text(encoding='utf-8', errors='replace'))
        parts.append(f'<details><summary>{_escape(rel_path)}</summary>'
                     f'<pre class="code"><code>{code}</code></pre></details>')
    return f'<div class="card">{"".join(parts)}</div>'


def generate_final_html_report(project, crew_results: Dict[str, Any],
                                full_series: Optional[List[Dict[str, Any]]] = None) -> str:
    """Render the final comprehensive project report (self-contained HTML
    with embedded charts, original data and source code) and return its
    file path."""
    preparation = project.preparation_report or {}
    datasets = [d for d in preparation.get('datasets', []) if d.get('usable')]
    if full_series:
        for dataset in datasets:
            match = next((s for s in full_series
                          if s.get('file_name') == dataset.get('file_name')), None)
            if match:
                dataset['wavelengths'] = match.get('wavelengths', [])
                dataset['intensities'] = match.get('intensities', [])
    per_agent = crew_results.get('per_agent_reports', [])

    spectrum_chart = spectrum_chart_data_url(datasets)
    quality_chart = quality_bar_chart_data_url(per_agent)
    charts = ''
    if spectrum_chart:
        charts += f'<h3>Messdaten (grafisch)</h3>' \
                 f'<img class="chart" src="{spectrum_chart}" alt="Messdaten-Plot">'
    if quality_chart:
        charts += f'<h3>Auswertungsbewertung</h3>' \
                 f'<img class="chart" src="{quality_chart}" alt="Qualitäts-Scores">'

    agent_html = ''.join(_agent_section_html(s) for s in per_agent) or \
        '<p class="muted">Keine Agenten-Berichte vorhanden.</p>'

    student_sections = {'discussion': '', 'conclusion': '', 'literature': ''}
    overview_keys = (['spectrum'] if spectrum_chart else []) + \
                    (['quality_bar'] if quality_chart else [])
    try:
        from services.student_report import build_student_sections
        student_sections = build_student_sections(
            per_agent, crew_results, datasets,
            overview_keys=overview_keys)
    except Exception:
        logger.exception('Student report sections failed (non-fatal)')

    chatbot_widget = ''
    try:
        from services.report_chatbot import chatbot_html
        chatbot_widget = chatbot_html(
            per_agent, crew_results, datasets,
            overview_keys=overview_keys).get('widget', '')
    except Exception:
        logger.exception('Chatbot widget rendering failed (non-fatal)')

    recommendations = crew_results.get('recommendations', [])
    rec_items = ''.join(f'<li>{_escape(r)}</li>' for r in recommendations) or \
        '<li class="muted">Keine Empfehlungen.</li>'

    warnings = crew_results.get('warnings', [])
    error_items = ''.join(f'<li>{_escape(e)}</li>'
                          for e in list(warnings) + list(crew_results.get('errors', [])))

    report = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(project.name)} – Abschlussbericht</title>
<style>{_style()}</style>
</head>
<body>
<div class="container">
<h1>{_escape(project.name)} – Abschlussbericht</h1>
<p class="muted">Projekt-ID: {_escape(project.id)} ·
Datum: {_escape(datetime.now().strftime('%d.%m.%Y %H:%M'))} ·
Request-ID: {_escape(crew_results.get('request_id', '-'))}</p>

{_kpi_row([
    ('Gesamtqualität', round(float(crew_results.get('overall_quality_score') or 0), 1)),
    ('Datensätze analysiert', crew_results.get('datasets_analyzed')
        if crew_results.get('datasets_analyzed') is not None else len(datasets)),
    ('Agenten-Berichte', len(per_agent)),
    ('Bearbeitungszeit', f"{round(float(crew_results.get('processing_time') or 0), 1)} s"),
])}

<h2>Übersicht &amp; Grafiken</h2>
<div class="card">{charts or '<p class="muted">Keine Grafiken verfügbar.</p>'}</div>

<h2>Agenten-Berichte (je Bereich)</h2>
{agent_html}

<h2>Diskussion</h2>
<div class="card">{student_sections['discussion']}</div>

<h2>Fazit</h2>
<div class="card">{student_sections['conclusion']}</div>

<h2>Literaturhinweise</h2>
<div class="card"><ul>{student_sections['literature']}</ul></div>

{chatbot_widget}

<h2>Originaldaten</h2>
{_original_data_html(datasets)}

<h2>Empfehlungen</h2>
<div class="card"><ul>{rec_items}</ul></div>

{f'<h2>Warnungen &amp; Fehler</h2><div class="card"><ul>{error_items}</ul></div>' if error_items else ''}

<h2>Quellcode der Analyse</h2>
{_source_code_html()}

</div>
</body>
</html>
"""
    output_dir = PROJECT_ROOT / 'output' / 'projects' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'final_{project.id}_{timestamp}.html'
    output_file.write_text(report, encoding='utf-8')
    logger.info('Final project report written: %s', output_file)
    return str(output_file)
