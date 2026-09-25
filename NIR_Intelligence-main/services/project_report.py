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


def spectrum_chart_data_url(datasets: List[Dict[str, Any]],
                             outlier_map=None,
                             cleaned_medians=None) -> str:
    """One line per usable dataset (measurement data graphic, MO 6).
    Uses the full measurement series when available (full_series), otherwise
    the 64-point preparation preview. Returns '' without preview data or
    matplotlib.

    OP38: the preview/full series is the median over ALL measurements,
    outliers included - so when the outlier analysis found outliers for a
    dataset, the raw line is drawn DASHED GREY, labelled as 'Median (inkl.
    Ausreissern)', and the cleaned median (over non-outlier measurements
    only) is added as the solid blue curve. Without an outlier verdict for
    a dataset the line stays exactly as before (backward compatible)."""
    if not MATPLOTLIB_AVAILABLE or not datasets:
        return ''
    outlier_map = outlier_map or {}
    cleaned_medians = cleaned_medians or {}
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
    has_cleaned = False
    for dataset in usable:
        name = str(dataset['file_name'])
        verdict = outlier_map.get(name)
        outliers = (verdict.get('outlier_indices')
                    if isinstance(verdict, dict) else None) or []
        cleaned = cleaned_medians.get(name)
        if outliers and cleaned and len(cleaned) == len(dataset['wavelengths']):
            ax.plot(dataset['wavelengths'],
                    dataset['intensities'],
                    color='grey', alpha=0.7, ls='--', lw=1.2,
                    label=f'{name}: Median (inkl. {len(outliers)} Ausreissern)')
            ax.plot(dataset['wavelengths'],
                    cleaned,
                    color='#0d6efd', lw=2.2,
                    label=f'{name}: bereinigt (ohne Ausreisser)')
            has_cleaned = True
        else:
            ax.plot(dataset['wavelengths'],
                    dataset['intensities'],
                    label=name)
    ax.set_xlabel('Wellenlänge (nm)')
    ax.set_ylabel('Intensität')
    ax.set_title('Messdaten aller Datensätze'
                 + (' - bereinigt nach Ausreisser-Analyse' if has_cleaned else ''))
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    return _figure_to_data_url(fig)


def spectrum_outlier_map(per_agent: List[Dict[str, Any]],
                         datasets: List[Dict[str, Any]]):
    """OP38: collect the outlier verdicts and cleaned median spectra for
    the usable datasets from the per-agent outlier sections. Returns
    ({file_name: verdict_data}, {file_name: cleaned_median}) - the verdict
    data is the honest per-dataset block (assessable, outlier_indices,
    measurement_count) from the outlier_analysis section; cleaned medians
    are computed from the dataset's measurement_samples. Never raises: a
    missing/failed analysis simply leaves the dataset unmarked."""
    verdicts: Dict[str, Dict[str, Any]] = {}
    cleaned: Dict[str, List[float]] = {}
    try:
        from services.outlier_analysis import cleaned_median
    except Exception:
        return verdicts, cleaned
    for section in per_agent or []:
        if not isinstance(section, dict) or section.get('agent') != 'outlier_analysis':
            continue
        data = section.get('data') or {}
        name = str(data.get('file_name') or '')
        if not name or not data.get('assessable'):
            continue
        verdicts[name] = data
    for dataset in datasets or []:
        name = str(dataset.get('file_name') or '')
        verdict = verdicts.get(name)
        if not verdict:
            continue
        samples = dataset.get('measurement_samples') or []
        wavelengths = dataset.get('wavelengths') or \
            (dataset.get('preview') or {}).get('wavelengths') or []
        curve = cleaned_median(samples, verdict)
        if curve and wavelengths and len(curve) == len(wavelengths):
            cleaned[name] = curve
    return verdicts, cleaned


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
ul { padding-left: 20px; } .muted { color: #6c757d; }.small { font-size: 0.85rem; }.meta-table { font-size: 0.85rem; margin: 8px 0 14px; }.meta-badge { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 0.75rem; }.meta-ki { background: #cfe2ff; color: #084293; }.meta-ctx { background: #d1e7dd; color: #0f5132; }.meta-file { background: #e9ecef; color: #495057; }
.print-actions { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
.print-actions button, .print-actions a { padding: 8px 16px;
  border: 1px solid #0d6efd; border-radius: 6px; background: #0d6efd;
  color: #fff; cursor: pointer; font-size: 0.9rem; text-decoration: none; }
.eq-block { background: #f8f9fa; border: 1px solid #dee2e6;
  border-left: 4px solid #0d6efd; border-radius: 6px; padding: 12px 16px;
  margin: 10px 0; }
.eq-block code { font-size: 0.85rem; }
@media print {
  .print-actions, #chatbot-section { display: none !important; }
  body { background: #fff; }
  .container { max-width: 100%; padding: 0; }
  .card { border: 1px solid #999; page-break-inside: avoid; }
  details { page-break-inside: avoid; }
  details > pre.code { max-height: none; }
  img.chart, .fig-block img { max-width: 100%; page-break-inside: avoid; }
  h2 { page-break-after: avoid; }
}
"""


def _kpi_row(items: List[Any]) -> str:
    cells = ''.join(
        f'<div><div class="value">{_escape(value)}</div>'
        f'<div class="label">{_escape(label)}</div></div>'
        for label, value in items)
    return f'<div class="kpi">{cells}</div>'


_CHART_TITLES = {
    'spectrum': 'Messdaten-Spektrum (Median; bei Ausreissern zus\u00e4tzlich bereinigte Kurve)',
    'quality_bar': 'Qualitätsbewertung der Analysebereiche',
    'similarity_top3': 'Top-3 ähnlichste Spektren aus der Datenbank',
    'sensor_dashboard': 'Sensorqualitäts-Dashboard (SPC)',
    'score_plot': 'PCA Score-Plot',
    'loading_plot': 'PCA Loading-Plot',
    'biplot': 'PCA Biplot',
    'scree_plot': 'PCA Scree-Plot',
    'r2_per_wavelength': 'PCA R² pro Wellenlänge',
    'spe_plot': 'PCA SPE-Plot',
    'prediction_vs_actual': 'Vorhersage vs. Referenzwert (neuronales Netz)',
    'loss_curves': 'Trainings- und Validierungs-Loss',
    'shap_summary': 'SHAP Summary (globale Wichtigkeit)',
    'shap_waterfall': 'SHAP Waterfall (lokale Erklärung)',
    'saliency_map': 'Saliency Map',
    'grad_cam': 'Grad-CAM',
    'attention_weights': 'Attention-Weights',
    'ref_vs_pred': 'Referenz vs. Vorhersage (PLS-Kreuzvalidierung)',
    'reg_coefficients': 'Regressionskoeffizienten pro Wellenlänge',
    'rmsecv_vs_n': 'RMSECV vs. Anzahl PLS-Komponenten',
    'outlier_distance': 'Ausreisser-Abstände (robuster z-Score, SNV + MAD)',
    'outlier_overlay': 'Spektren mit markierten Ausreissern',
}

AGENT_SOURCE_FILES = {
    'spectral_analysis': ['agents/spectral_analysis_agent.py',
                          'services/similarity_charts.py'],
    'metadata_quality': ['agents/metadata_quality_agent.py'],
    'sensor_quality': ['agents/sensor_quality_agent.py',
                       'services/sensor_charts.py'],
    'statistical_analysis': ['agents/statistical_analysis_agent.py',
                             'services/pca_charts.py'],
    'neural_network': ['agents/neural_network_agent.py',
                       'services/xai_charts.py'],
    'calibration': ['agents/calibration_agent.py',
                    'services/calibration_charts.py'],
    'faiss_similarity': ['agents/faiss_agent.py',
                          'services/spectrum_similarity.py'],
    'outlier_analysis': ['services/outlier_analysis.py'],
}

_SOURCE_CACHE: Dict[str, str] = {}


def _source_code(rel_path: str) -> str:
    cached = _SOURCE_CACHE.get(rel_path)
    if cached is not None:
        return cached
    path = PROJECT_ROOT / rel_path
    code = ''
    if path.exists():
        code = _escape(path.read_text(encoding='utf-8', errors='replace'))
    _SOURCE_CACHE[rel_path] = code
    return code


def _equation_html(equation: Dict[str, Any]) -> str:
    if not isinstance(equation, dict) or equation.get('status') != 'ok':
        return ''
    target = _escape(equation.get('target_name', 'Zielwert'))
    intercept = equation.get('intercept', 0.0)
    method = _escape(equation.get('method', 'PLS'))
    r2 = equation.get('r2_fit')
    rmsec = equation.get('rmsec')
    terms = equation.get('top_terms') or []
    rows = ''.join(
        f'<tr><td>{_escape(t.get("channel_index"))}</td>'
        f'<td>{_escape(t.get("wavelength_nm"))}</td>'
        f'<td>{_escape(f"{t.get("coefficient", 0.0):+.4f}")}</td>'
        f'<td>{_escape(t.get("channel_mean"))}</td>'
        f'<td>{_escape(t.get("channel_std"))}</td></tr>'
        for t in terms)
    stats = ''
    if r2 is not None and rmsec is not None:
        stats = (f' &middot; R&sup2;<sub>fit</sub> = {_escape(f"{r2:.4f}")}'
                 f' &middot; RMSEC = {_escape(f"{rmsec:.4f}")} {target}')
    return ('<div class="eq-block"><p><b>Kalibrierungsgleichung</b> '
            f'({method}):</p>'
            f'<p><code>{target} = {_escape(f"{intercept:.4f}")} '
            '+ &Sigma;<sub>i</sub> coef<sub>i</sub> '
            '&middot; (x<sub>i</sub> &minus; mean<sub>i</sub>) / '
            'std<sub>i</sub></code></p>'
            '<p class="small muted">Standardisierte Kanäle (z-Scores); '
            'die vollständige Kanal-Statistik (mean_i, std_i) und alle '
            'Koeffizienten stehen im Abschnitts-Datensatz '
            f'(<code>calibration_equation</code>).</p>'
            f'<p class="small">Fit über {terms and "die" or ""}'
            f'{_escape(equation.get("num_samples"))} Messungen '
            f'({stats.strip()})</p>'
            '<table class="meta-table"><thead><tr><th>Kanal</th>'
            '<th>Wellenlänge (nm)</th><th>Koeffizient</th>'
            '<th>Kanal-Mittelwert</th><th>Kanal-Stdabw.</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            '<p class="small muted">Ausführbar: y = intercept + '
            'sum(coef_i * (x_i - mean_i)/std_i) über alle Kanäle; '
            f'in-sample-Fit, Kreuzvalidierung siehe Ref. vs. Pred.</p></div>')


def _section_source_html(section: Dict[str, Any]) -> str:
    rel_paths = AGENT_SOURCE_FILES.get(str(section.get('agent', ''))) or []
    if not rel_paths:
        return ''
    parts = []
    for rel_path in rel_paths:
        code = _source_code(rel_path)
        if not code:
            continue
        parts.append(f'<details><summary>Quellcode: {_escape(rel_path)} '
                     '(ausführbar)</summary>'
                     f'<pre class="code"><code>{code}</code></pre></details>')
    return ''.join(parts)


def _figure_caption(number: int, key: str) -> str:
    title = _CHART_TITLES.get(key) or key.replace('_', ' ').capitalize()
    return (f'<div class="fig-caption"><b>Abbildung {number}:</b> '
            f'{_escape(title)}</div>')


def _figure_registry(per_agent: List[Dict[str, Any]],
                     overview_keys: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Ordered figure list identical to student_report.figure_explanations
    and the chatbot figure numbering (overview charts first, then the agent
    section charts in report order)."""
    figures: List[Dict[str, Any]] = []
    for key in (overview_keys or []):
        figures.append({'key': key, 'section_index': -1})
    for index, section in enumerate(per_agent):
        for key, url in (section.get('charts') or {}).items():
            if url:
                figures.append({'key': key, 'section_index': index})
    for number, figure in enumerate(figures, start=1):
        figure['number'] = number
    return figures


def _agent_section_html(section: Dict[str, Any],
                        section_figures: Optional[List[Dict[str, Any]]] = None) -> str:
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
    findings = (section.get('data', {}) or {}).get('findings') or []
    findings_html = ''
    if findings:
        paras = ''.join(f'<p>{_escape(f)}</p>' for f in findings)
        findings_html = f'<h3>Befunde</h3>{paras}'
    charts_html = ''
    charts = section.get('charts') or {}
    if charts:
        fig_map = {f['key']: f['number'] for f in (section_figures or [])}
        imgs = ''.join(
            f'<div class="fig-block"><img src="{_escape(url)}" alt="{_escape(_CHART_TITLES.get(k) or k)}" '
            f'style="max-width:100%;height:auto;margin:6px;">'
            + (_figure_caption(fig_map[k], k) if k in fig_map else '')
            + '</div>'
            for k, url in charts.items() if url)
        note = _escape(section.get('charts_note') or 'PCA-Diagramme')
        charts_html = f'<h3>{note}</h3>{imgs}'
    equation_html = ''
    data = section.get('data') or {}
    if isinstance(data, dict) and data.get('calibration_equation'):
        equation_html = _equation_html(data.get('calibration_equation'))
    source_html = _section_source_html(section)
    return (f'<div class="card"><h3>{_escape(section.get("title", section.get("agent", "Agent")))} '
            f'<span class="badge {badge}">{_escape(status)}</span></h3>'
            f'{table}{equation_html}{charts_html}{findings_html}{recs}'
            f'{source_html}</div>')


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


def _metadata_overview_html(datasets: List[Dict[str, Any]],
                             metadata_quality: Dict[str, Any]) -> str:
    """Metadata overview section for the final report (OP35): per dataset
    the collected fields with value and source (KI / computed from data /
    project context / file / editor), the standards compliance verdicts and
    the open KI questions - the same structure the project report shows,
    so the Abschlussbericht documents what the analysis was based on."""
    if not datasets:
        return ''
    blocks = []
    for dataset in datasets:
        rating = dataset.get('metadata_rating') or {}
        rows = []
        for field, r in rating.items():
            if field == 'konflikte' or not isinstance(r, dict):
                continue
            source = str(r.get('source') or 'Datei')
            badge = ('ki' if 'berechnet' in source
                     else 'ki' if source.startswith('ki')
                     else 'ctx' if source == 'projekt-kontext'
                     else 'file')
            rows.append(
                f'<tr><td><code>{_escape(field)}</code></td>'
                f'<td>{_escape(str(r.get("value", ""))[:80])}</td>'
                f'<td><span class="meta-badge meta-{badge}">{_escape(source)}</span></td></tr>')
        questions = dataset.get('open_questions') or []
        q_html = ''.join(f'<li>{_escape(q)}</li>' for q in questions)
        q_block = (f'<p class="muted small"><strong>Offene KI-Fragen:</strong></p>'
                   f'<ul>{q_html}</ul>') if q_html else ''
        if rows:
            blocks.append(
                f'<h3>{_escape(dataset.get("file_name", "?"))}</h3>'
                f'<table class="meta-table"><thead><tr><th>Feld</th><th>Wert</th>'
                f'<th>Quelle</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
                f'{q_block}')
    standards = metadata_quality.get('standards_compliance') or []
    std_rows = ''.join(
        f'<tr><td>{_escape(c.get("standard", "?"))}</td>'
        f'<td>{_escape(", ".join(c.get("present") or [])) or "-"}</td>'
        f'<td>{_escape(", ".join(c.get("missing") or [])) or "-"}</td>'
        f'<td>{"erf&uuml;llt" if c.get("satisfied") else "unvollst&auml;ndig"}</td></tr>'
        for c in standards)
    std_block = ''
    if std_rows:
        std_block = ('<p class="muted small"><strong>Standards-Konformit&auml;t:</strong></p>'
                     '<table class="meta-table"><thead><tr><th>Standard</th>'
                     '<th>Vorhanden</th><th>Fehlt</th><th>Status</th></tr></thead>'
                     f'<tbody>{std_rows}</tbody></table>')
    ki = metadata_quality.get('ki_relevance') or {}
    ki_block = ''
    if ki.get('summary'):
        ki_block = (f'<p class="muted small"><strong>KI-Einsch&auml;tzung '
                    f'(NIR-Relevanz):</strong> {_escape(ki["summary"])}</p>')
    body = ''.join(blocks)
    if not body and not std_block and not ki_block:
        return ''
    return (f'<h2>Metadaten-&Uuml;bersicht</h2>'
            f'<div class="card">{ki_block}{std_block}{body}</div>')


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    head = '| ' + ' | '.join(headers) + ' |'
    sep = '|' + '|'.join(['---'] * len(headers)) + '|'
    body = ''.join('\n| ' + ' | '.join(str(c) for c in row) + ' |'
                   for row in rows)
    return head + '\n' + sep + body


def _md_equation(equation: Dict[str, Any]) -> str:
    if not isinstance(equation, dict) or equation.get('status') != 'ok':
        return ''
    target = str(equation.get('target_name', 'Zielwert'))
    lines = [f"**Kalibrierungsgleichung ({equation.get('method', 'PLS')}):**",
             '',
             f"`{target} = {equation.get('intercept', 0.0):.4f} "
             "+ SUM_i coef_i * (x_i - mean_i) / std_i`",
             '']
    terms = equation.get('top_terms') or []
    if terms:
        lines.append(_md_table(
            ['Kanal', 'Wellenlänge (nm)', 'Koeffizient',
             'Kanal-Mittelwert', 'Kanal-Stdabw.'],
            [[str(t.get('channel_index')), str(t.get('wavelength_nm')),
              f"{t.get('coefficient', 0.0):+.4f}", str(t.get('channel_mean')),
              str(t.get('channel_std'))] for t in terms]))
        lines.append('')
    stats = (f"R²_fit = {equation.get('r2_fit', 0.0):.4f}, "
             f"RMSEC = {equation.get('rmsec', 0.0):.4f} "
             f"({equation.get('num_samples')} Messungen, in-sample-Fit; "
             "Kreuzvalidierung siehe Ref. vs. Pred).")
    lines.append(stats)
    return '\n'.join(lines) + '\n'


def _md_source(section: Dict[str, Any]) -> str:
    parts = []
    for rel_path in (AGENT_SOURCE_FILES.get(str(section.get('agent', '')))
                     or []):
        path = PROJECT_ROOT / rel_path
        if not path.exists():
            continue
        code = path.read_text(encoding='utf-8', errors='replace')
        fence = '```'
        while fence + 'python' in code or fence in code.split(fence)[:-1]:
            fence += '`'
        parts.append(f'**Quellcode: `{rel_path}` (ausführbar)**\n\n'
                     f'{fence}python\n{code}\n{fence}\n')
    return '\n'.join(parts)


def generate_markdown_report(project, crew_results: Dict[str, Any],
                             full_series: Optional[List[Dict[str, Any]]] = None) -> str:
    """Render the final report as Markdown (OP39): same structure as the
    HTML report (KPIs, metadata overview, per-agent sections with findings,
    charts as figure references, calibration equation, source code per
    section) - download/print friendly. Returns the file path."""
    preparation = project.preparation_report or {}
    datasets = [d for d in preparation.get('datasets', []) if d.get('usable')]
    per_agent = crew_results.get('per_agent_reports', [])
    figures = _figure_registry(per_agent, overview_keys=['spectrum'])
    lines = [f"# {project.name} – Abschlussbericht (Markdown)",
             '',
             f"Projekt-ID: {project.id} · "
             f"Datum: {datetime.now().strftime('%d.%m.%Y %H:%M')} · "
             f"Request-ID: {crew_results.get('request_id', '-')}",
             '',
             '## KPIs',
             '']
    lines.append(_md_table(
        ['Kennzahl', 'Wert'],
        [['Gesamtqualität',
          round(float(crew_results.get('overall_quality_score') or 0), 1)],
         ['Datensätze analysiert',
          crew_results.get('datasets_analyzed'
                           ) if crew_results.get('datasets_analyzed'
                                                 ) is not None else len(datasets)],
         ['Agenten-Berichte', len(per_agent)],
         ['Bearbeitungszeit (s)',
          round(float(crew_results.get('processing_time') or 0), 1)]]))
    lines.append('')
    for dataset in datasets:
        rating = dataset.get('metadata_rating') or {}
        rows = [[f, str(r.get('value', ''))[:60], str(r.get('source', ''))]
                for f, r in rating.items()
                if f != 'konflikte' and isinstance(r, dict)]
        if rows:
            lines += [f"### Metadaten: {dataset.get('file_name', '?')}", '',
                      _md_table(['Feld', 'Wert', 'Quelle'], rows), '']
    for section in per_agent:
        agent = section.get('agent', '?')
        figs = [f for f in figures if f.get('section_index')
                and per_agent[f['section_index']].get('agent') == agent]
        lines += [f"## {section.get('title', agent)}"
                  f" ({section.get('status', '?')})", '']
        data = section.get('data') or {}
        rows = [(k, v) for k, v in _metric_rows(data)
                if k != 'calibration_equation' and not k.startswith('calibration_equation.')]
        if rows:
            lines += [_md_table(['Feld', 'Wert'],
                                [[k, str(v)[:120]] for k, v in rows]), '']
        if figs:
            lines += ['Abbildungen: '
                      + ', '.join(f"{f['number']} "
                                  f"({_CHART_TITLES.get(f['key'], f['key'])})"
                                  for f in figs), '']
        equation = data.get('calibration_equation') if isinstance(data, dict) else None
        if equation:
            lines += [_md_equation(equation), '']
        for finding in (data.get('findings') if isinstance(data, dict) else []) or []:
            lines += [f"- {finding}"]
        if (data.get('findings') if isinstance(data, dict) else None):
            lines.append('')
        source = _md_source(section)
        if source:
            lines += [source, '']
    output_dir = PROJECT_ROOT / 'output' / 'projects' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'final_{project.id}_{timestamp}.md'
    output_file.write_text('\n'.join(lines), encoding='utf-8')
    logger.info('Markdown project report written: %s', output_file)
    return str(output_file)


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

    outlier_verdicts, cleaned_medians = spectrum_outlier_map(per_agent, datasets)
    spectrum_chart = spectrum_chart_data_url(
        datasets, outlier_map=outlier_verdicts, cleaned_medians=cleaned_medians)
    quality_chart = quality_bar_chart_data_url(per_agent)
    overview_keys = (['spectrum'] if spectrum_chart else []) + \
                    (['quality_bar'] if quality_chart else [])
    figures = _figure_registry(per_agent, overview_keys=overview_keys)
    charts = ''
    if spectrum_chart:
        number = next((f['number'] for f in figures if f['key'] == 'spectrum'), 0)
        cleaned_note = ''
        if cleaned_medians:
            cleaned_note = ('<p class="muted small">Ausreisser-Hinweis: Die gestrichelte '
                            'graue Kurve ist der Median inklusive der in der '
                            'Ausreisser-Analyse gefundenen Abweichler; die '
                            'durchgezogene Kurve zeigt den bereinigten Median '
                            '(nur Messungen ohne Ausreisser) - nur diese ist '
                            'f&uuml;r die Interpretation belastbar.</p>')
        charts += f'<h3>Messdaten (grafisch)</h3>' \
                 f'<div class="fig-block"><img class="chart" src="{spectrum_chart}" ' \
                 f'alt="Messdaten-Plot">{_figure_caption(number, "spectrum")}' \
                 f'{cleaned_note}</div>'
    if quality_chart:
        number = next((f['number'] for f in figures if f['key'] == 'quality_bar'), 0)
        charts += f'<h3>Auswertungsbewertung</h3>' \
                 f'<div class="fig-block"><img class="chart" src="{quality_chart}" ' \
                 f'alt="Qualitäts-Scores">{_figure_caption(number, "quality_bar")}</div>'

    agent_html = ''
    for index, section in enumerate(per_agent):
        section_figures = [f for f in figures if f['section_index'] == index]
        agent_html += _agent_section_html(section, section_figures=section_figures)
    agent_html = agent_html or \
        '<p class="muted">Keine Agenten-Berichte vorhanden.</p>'

    student_sections = {'discussion': '', 'conclusion': '', 'literature': ''}
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
<div class="print-actions">
<button onclick="window.print()" title="Drucken oder als PDF speichern (Browser-Dialog)">Drucken / PDF</button>
<a href="/projects/{_escape(project.id)}/final-report/markdown/" title="Bericht als Markdown-Datei herunterladen">Markdown-Download</a>
</div>

{_kpi_row([
    ('Gesamtqualität', round(float(crew_results.get('overall_quality_score') or 0), 1)),
    ('Datensätze analysiert', crew_results.get('datasets_analyzed')
        if crew_results.get('datasets_analyzed') is not None else len(datasets)),
    ('Agenten-Berichte', len(per_agent)),
    ('Bearbeitungszeit', f"{round(float(crew_results.get('processing_time') or 0), 1)} s"),
])}

<h2>Übersicht &amp; Grafiken</h2>
<div class="card">{charts or '<p class="muted">Keine Grafiken verfügbar.</p>'}</div>

{_metadata_overview_html(datasets, preparation.get('metadata_quality') or {})}

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
