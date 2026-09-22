"""OP8 verification: CrewAI agent results visible in the web interface.

The OP6 agents (sensor quality, statistical analysis, neural network) are
real implementations, but until OP8 the crew never executed them in
analyze_sample and the web UI showed demo data. This matrix verifies:

T1: the crew executes all three agents and stores their real results
T2: agent results are JSON-serializable (strict, no NaN/Infinity)
T3: API responses expose the agent results (start_analysis payload shape,
    status endpoint, history entries)
T4: the analysis UI renders the agent results (template elements + JS)
T5: the UI no longer contains demo/fake data paths
T6: regressions: report generation still works with the new data keys,
    OP6 crew factory and OP7 bridge contract untouched.

Offline; the crew runs in standalone mode (CrewAI package optional).
"""

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')


PROJECT = Path(__file__).resolve().parent.parent
DJANGO_DIR = PROJECT / 'django_project'


def make_spectra(n=12, points=40, noise=0.0):
    import numpy as np
    rng = np.random.default_rng(42)
    base = 100 + 50 * rng.random(points)
    return [base + noise * rng.standard_normal(points) for _ in range(n)]


# ---------------------------------------------------------------- T1: crew executes the OP6 agents
from agents.nir_analysis_crew import (
    NIRAnalysisCrew, CrewConfiguration, AnalysisRequest, AnalysisMode, PrivacyLevel,
)
from agents.reporting_agent import ReportType, ReportFormat

out_dir = Path(tempfile.mkdtemp(prefix='op8_out_'))
config = CrewConfiguration(enable_crewai=False,
                           temp_dir=tempfile.mkdtemp(prefix='op8_tmp_'),
                           output_dir=str(out_dir))
crew = NIRAnalysisCrew(config)

spectra_intensities = make_spectra()
request = AnalysisRequest(
    sample_id='op8_sample',
    spectral_data={'wavelengths': list(range(700, 700 + 40 * 10, 10)),
                   'intensities': spectra_intensities[0]},
    metadata={'instrument_type': 'op8', 'reference_values': [5.0, 6.1, 4.9, 5.5, 6.0,
                                                             5.2, 4.8, 5.9, 6.2, 5.4,
                                                             5.1, 5.7]},
    analysis_mode=AnalysisMode.STANDARD,
    privacy_level=PrivacyLevel.LOCAL_ONLY,
    report_type=ReportType.COMPREHENSIVE,
    report_format=ReportFormat.HTML,
)
result = crew.analyze_sample(request)

check('T1a analysis completes without errors', result.errors == [], f'errors={result.errors}')
check('T1b sensor quality agent executed',
      result.sensor_quality_results is not None
      and result.sensor_quality_results.get('status') in ('ok', 'degraded'),
      f"keys={sorted((result.sensor_quality_results or {}).keys())[:6]}")
check('T1c statistical agent executed',
      result.statistical_analysis_results is not None
      and result.statistical_analysis_results.get('status') == 'ok',
      f"methods={result.statistical_analysis_results.get('methods_applied')}")
check('T1d neural network agent executed',
      result.neural_network_results is not None
      and result.neural_network_results.get('status') == 'ok',
      f"trained={result.neural_network_results.get('models_trained')}")
check('T1e sensor quality results are real (drift/noise computed)',
      'drift_level' in result.sensor_quality_results
      and 'noise_level' in result.sensor_quality_results
      and result.sensor_quality_results['num_spectra'] >= 1)
check('T1f statistical methods applied on the data',
      'DescriptiveStatistics' in result.statistical_analysis_results.get('methods_applied', []),
      f"applied={result.statistical_analysis_results.get('methods_applied')}")
check('T1f-2 single-spectrum descriptive stats include outliers and summary',
      'outliers' in result.statistical_analysis_results['method_results']['DescriptiveStatistics']
      and 'mean' in result.statistical_analysis_results['method_results']['DescriptiveStatistics'],
      f"keys={sorted(result.statistical_analysis_results['method_results']['DescriptiveStatistics'].keys())[:8]}")

# single-spectrum input to the multi-sample agents: they receive the same
# unified schema dict, verify the no-data path does not crash the crew
single = crew.analyze_sample(AnalysisRequest(
    sample_id='op8_single',
    spectral_data={'wavelengths': [700, 710], 'intensities': [1.0, 2.0]},
    metadata={},
    analysis_mode=AnalysisMode.QUICK,
))
check('T1g crew completes with minimal input (agents report no_data gracefully)',
      single.errors == [] and single.sensor_quality_results is not None,
      f"sensor={single.sensor_quality_results.get('status')}")

# ---------------------------------------------------------------- T2: strict JSON serializability
try:
    json.dumps(result.sensor_quality_results, allow_nan=False)
    json.dumps(result.statistical_analysis_results, allow_nan=False)
    json.dumps(result.neural_network_results, allow_nan=False)
    check('T2a agent results serialize to strict JSON (no NaN/Infinity)', True)
except ValueError as exc:
    check('T2a agent results serialize to strict JSON (no NaN/Infinity)', False, str(exc))

# ---------------------------------------------------------------- T3: API payload shapes
summary = crew.get_analysis_summary(result)
check('T3a summary exposes sensor quality results',
      summary.get('sensor_quality', {}).get('status') in ('ok', 'degraded'))
check('T3b summary exposes statistical analysis results',
      summary.get('statistical_analysis', {}).get('status') == 'ok')
check('T3c summary exposes neural network results',
      summary.get('neural_network', {}).get('status') == 'ok')

history = crew.get_analysis_history(10)
check('T3d history exposes agent run info',
      len(history) > 0
      and history[0].get('sensor_quality_status') in ('ok', 'degraded')
      and isinstance(history[0].get('statistical_methods_applied'), list)
      and isinstance(history[0].get('neural_models_trained'), list),
      f"entry keys={sorted(history[0].keys())}")

views_path = DJANGO_DIR / 'api' / 'crewai_views.py'
views_src = views_path.read_text()
check('T3e start_analysis view returns agent results',
      'response_data["sensor_quality"]' in views_src
      and 'response_data["statistical_analysis"]' in views_src
      and 'response_data["neural_network"]' in views_src)
check('T3f status endpoint returns flattened summary fields for the UI',
      '"sensor_quality": summary.get("sensor_quality", {})' in views_src
      and '"neural_network": summary.get("neural_network", {})' in views_src)
check('T3g crew status view reports the full agent roster',
      re.search(r'"sensor_quality": "available"', views_src) is not None
      and re.search(r'"statistical_analysis": "available"', views_src) is not None
      and re.search(r'"neural_network": "available"', views_src) is not None
      and '"crewai_agents": len(crew.crewai_agents)' in views_src)

# ---------------------------------------------------------------- T4: UI renders agent results
template_path = DJANGO_DIR / 'templates' / 'analysis.html'
template_src = template_path.read_text()
check('T4a analysis template has sensor quality panel',
      'id="sensorQualityResults"' in template_src)
check('T4b analysis template has statistical analysis panel',
      'id="statisticalResults"' in template_src)
check('T4c analysis template has neural network panel',
      'id="neuralNetworkResults"' in template_src)

js_path = DJANGO_DIR / 'static' / 'js' / 'analysis.js'
js_src = js_path.read_text()
check('T4d JS renders sensor quality results',
      'function renderSensorQualityResults' in js_src
      and "renderSensorQualityResults(result.sensor_quality" in js_src)
check('T4e JS renders statistical results',
      'function renderStatisticalResults' in js_src
      and "renderStatisticalResults(result.statistical_analysis" in js_src)
check('T4f JS renders neural network results',
      'function renderNeuralNetworkResults' in js_src
      and "renderNeuralNetworkResults(result.neural_network" in js_src)

# ---------------------------------------------------------------- T5: no demo data left in the UI
check('T5a demo spectral data generator removed',
      'generateSampleSpectralData' not in js_src)
check('T5b no Math.random chart data left',
      'Math.random() * 0.5' not in js_src)
check('T5c chart uses real spectral data',
      'result.spectral_data' in js_src
      and 'fileUploadData' in js_src)
check('T5d placeholder average processing time removed',
      "'~2.5s'" not in js_src)
check('T5e quick analysis requires a real upload (no demo data)',
      re.search(r"if \(!fileUploadData \|\| !fileUploadData\.fileId\) \{\s*\n\s*showError", js_src) is not None)

# ---------------------------------------------------------------- T6: regressions
check('T6a comprehensive report still generated',
      len(result.generated_reports) == 1
      and result.generated_reports[0].status.value == 'completed',
      f"reports={len(result.generated_reports)}")
report_content = Path(result.generated_reports[0].file_path).read_text(errors='replace')
check('T6b report is a Quarto document with html format',
      report_content.startswith('---') and 'format: html' in report_content)

# OP7 bridge contract: FileCrewAnalysisView still wired
sys.path.insert(0, str(DJANGO_DIR))
os_environ_ok = True
try:
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
    import django
    django.setup()
    from django.urls import resolve
    match = resolve('/api/files/00000000-0000-0000-0000-000000000000/crew-analysis/')
    check('T6c OP7 crew-analysis route still resolves', match is not None,
          str(match.func))
except Exception as exc:  # pragma: no cover
    check('T6c OP7 crew-analysis route still resolves', False, str(exc))

# OP6 factory regression
from agents.nir_analysis_crew import create_analysis_crew
factory_crew = create_analysis_crew(CrewConfiguration(enable_crewai=False,
                                                      temp_dir=tempfile.mkdtemp(),
                                                      output_dir=tempfile.mkdtemp()))
check('T6d OP6 create_analysis_crew factory works',
      factory_crew is not None and hasattr(factory_crew, 'analyze_sample'))

# template compiles with the real Django template engine
try:
    from django.template.loader import get_template
    get_template('analysis.html')
    check('T6e analysis.html compiles (Django engine)', True)
except Exception as exc:
    check('T6e analysis.html compiles (Django engine)', False, str(exc))

# ---------------------------------------------------------------- T7: navigation visibility
base_src = (DJANGO_DIR / 'templates' / 'base.html').read_text()
index_src = (DJANGO_DIR / 'templates' / 'index.html').read_text()
dash_src = (DJANGO_DIR / 'templates' / 'dashboard_colorful.html').read_text()

check('T7a Files page linked in the main navigation',
      'href="/files/"' in base_src)
check('T7b Files page linked in the footer',
      base_src.count('href="/files/"') >= 2)
check('T7c Files nav-card on the landing page',
      'href="/files/"' in index_src)
check('T7d dashboard quick action opens the Files upload page',
      'href="/files/"' in dash_src)
check('T7e no dead legal links in the footer (privacy/terms/imprint removed)',
      '/privacy/' not in base_src and '/terms/' not in base_src
      and '/imprint/' not in base_src)

# every internal link in the touched templates must resolve
try:
    import os as _os
    _os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
    import django as _django
    _django.setup()
    from django.urls import resolve as _resolve
    dead = []
    for tpl_src in (base_src, index_src, dash_src):
        for link in set(re.findall(r'href="(/[a-z0-9\-/]*)"', tpl_src)):
            try:
                _resolve(link)
            except Exception:
                dead.append(link)
    check('T7f all internal links in nav templates resolve', dead == [],
          f'dead={dead}')
except Exception as exc:
    check('T7f all internal links in nav templates resolve', False, str(exc))

# ---------------------------------------------------------------- summary
print()
failed = [name for name, ok in results if not ok]
print(f'{len(results) - len(failed)}/{len(results)} tests passed')
if failed:
    print('FAILED:', ', '.join(failed))
    sys.exit(1)
