"""OP40 verification: honest metadata score + optional source print.

User requirement: "Die Metadaten werden beim Einlesen mit 100% nach dem
Editieren bewertet im Abschlussbericht aber nur als Fair..." and
"besteht die Moeglichkeit den Quellcode optional zum Druck
mit anzubieten?"

Root cause (reproduced): the crew's MetadataQualityAgent judged every
metadata field against ALL 5 standards (ISO 19115, Dublin Core, JSON-LD,
Schema.org, NIR Custom) - unknown fields scored 0/5, dragging a fully
documented dataset to consistency 3.1% -> 'fair'. Data payload keys
(measurement_samples, ...) were assessed as metadata fields, and noise
recommendations demanded ISO/Dublin-Core compliance for NIR spectra.

T1  fully documented metadata -> score 100, grade excellent (not fair)
T2  completeness/accuracy/consistency all 100 for complete metadata
T3  payload keys (measurement_samples, ...) are NOT assessed as fields
T4  consistency only counts standards that regulate the field
T5  unknown fields (no standard mentions them) do not dilute consistency
T6  recommendations: no ISO/Dublin-Core noise for NIR datasets
T7  missing metadata -> honest MISSING grade, score 0
T8  partially documented -> grade between, honest (not excellent)
T9  report: source-code print toggle (checkbox) present
T10 report: toggle JS opens/closes source details blocks
T11 report: print CSS hides collapsed details content is NOT claimed -
    the toggle decides (open -> printed, collapsed -> summary only)
T12 metadata section in the crew report carries the fixed score
"""
import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

PASS = 0
FAIL = 0
FAILED = []


def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'[PASS] {name}')
    else:
        FAIL += 1
        FAILED.append(name)
        print(f'[FAIL] {name} {detail}')


from agents.metadata_quality_agent import (  # noqa: E402
    MetadataQualityAgent, MetadataStandard)

# ---------------------------------------------------------------- T1-T8
agent = MetadataQualityAgent()
complete = {'measurement_samples': [[1.0] * 10] * 40,
            'calibration_samples': [[1.0] * 10] * 20,
            'reference_values': [5.0] * 20,
            'file_name': 'oel.csv', 'file_extension': '.csv',
            'saturated_measurements': 0, 'target_name': 'Fett',
            'operator': 'Yvonne', 'operator_name': 'Yvonne',
            'humidity': '88', 'temperature': '25',
            'instrument': 'Triadsensor', 'instrument_type': 'Triadsensor',
            'acquisition_time': '2025-01-15', 'timestamp': '2025-01-15',
            'sample_id': 'oel1', 'wavelength_range': '600, 1100',
            'measurement_date': '2025-01-15', 'location': 'Lab'}
res = agent.assess_metadata_quality(complete, 'oel.csv')
check('T1 fully documented metadata -> 100 / excellent (not fair)',
      res.overall_quality_score == 100.0
      and res.overall_quality_grade.value == 'excellent',
      f"score={res.overall_quality_score} grade={res.overall_quality_grade.value}")
check('T2 completeness/accuracy/consistency all 100',
      res.completeness_score == 100.0
      and res.accuracy_score == 100.0
      and res.consistency_score == 100.0,
      f"c={res.completeness_score} a={res.accuracy_score} "
      f"k={res.consistency_score}")
assessed_names = {f.name for f in res.fields_assessed}
check('T3 payload keys not assessed as metadata fields',
      'measurement_samples' not in assessed_names
      and 'calibration_samples' not in assessed_names
      and 'reference_values' not in assessed_names
      and 'file_name' not in assessed_names,
      f'fields={sorted(assessed_names)}')
standard_fields = agent._standard_field_names()
regulated = standard_fields[MetadataStandard.CUSTOM_NIR.value]
check('T4 consistency counts only regulating standards (helper)',
      'operator' in regulated and 'sample_id' in regulated
      and 'humidity' not in regulated,
      f'regulated={sorted(regulated)[:6]}...')
# a complete required set PLUS unknown extra fields: the extras must not
# dilute the consistency (before OP40 they scored 0/5 per field)
full_plus_unknown = {k: v for k, v in complete.items()
                     if k not in ('measurement_samples',)}
full_plus_unknown['humidity'] = '88'
full_plus_unknown['temperature'] = '25'
res_full_unknown = agent.assess_metadata_quality(full_plus_unknown, 'x')
check('T5 unknown extra fields do not dilute consistency',
      res_full_unknown.consistency_score == 100.0
      and res_full_unknown.overall_quality_grade.value == 'excellent',
      f"consistency={res_full_unknown.consistency_score} "
      f"score={res_full_unknown.overall_quality_score}")
# and a metadata set WITHOUT any required field keeps consistency honest
# at 0 (the required fields are absent), not dragged by unknowns alone
unknown_only = {'humidity': '88', 'temperature': '25'}
res_unknown = agent.assess_metadata_quality(unknown_only, 'x')
check('T5a absent required fields -> honest low score with missing list',
      res_unknown.missing_required_fields
      and res_unknown.overall_quality_score < 50,
      f"score={res_unknown.overall_quality_score} "
      f"missing={res_unknown.missing_required_fields}")
check('T6 no ISO/Dublin-Core noise recommendations for NIR data',
      not any('ISO 19115' in r or 'Dublin Core' in r or 'JSON-LD' in r
              or 'Schema.org' in r for r in res.recommendations),
      f'recs={res.recommendations}')
res_empty = agent.assess_metadata_quality({}, 'x')
check('T7 missing metadata -> honest MISSING, score 0',
      res_empty.overall_quality_grade.value == 'missing'
      and res_empty.overall_quality_score == 0.0, '')
partial = {'operator': 'Yvonne', 'temperature': '25'}
res_partial = agent.assess_metadata_quality(partial, 'x')
check('T8 partial metadata -> honest intermediate score + missing list',
      0 < res_partial.overall_quality_score < 100
      and res_partial.missing_required_fields
      and res_partial.overall_quality_grade.value in ('fair', 'poor',
                                                      'good'),
      f"score={res_partial.overall_quality_score} "
      f"missing={res_partial.missing_required_fields}")

# ---------------------------------------------------------------- T9-T11
sys.path.insert(0, str(PROJECT / 'django_project'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
import django  # noqa: E402
django.setup()

from services import project_report  # noqa: E402


class _StubProject:
    id = 'p40'
    name = 'OP40 Test'
    preparation_report = {'datasets': []}
    crew_results = {}


crew_results = {'request_id': 'req-op40', 'overall_quality_score': 90.0,
                'datasets_analyzed': 1, 'processing_time': 0.5,
                'recommendations': [], 'warnings': [], 'errors': [],
                'per_agent_reports': [
                    {'agent': 'calibration', 'title': 'Kalibration',
                     'status': 'completed',
                     'data': {'best_method': 'PLS'}}]}
path = Path(project_report.generate_final_html_report(
    _StubProject(), crew_results))
html = path.read_text(encoding='utf-8')
check('T9 source print toggle present',
      'print-source-toggle' in html and 'Quellcode im Ausdruck einbeziehen'
      in html, '')
check('T10 toggle JS opens/closes the source details',
      "d.querySelector('pre.code')" in html and 'd.open=show' in html, '')
check('T11 toggle styling + aligned actions',
      '.src-toggle' in html, '')
path.unlink()

# ---------------------------------------------------------------- T12
crew_src = (PROJECT / 'services' / 'project_crew.py').read_text(
    encoding='utf-8')
check('T12 crew metadata section carries grade + score',
      'overall_quality_score' in crew_src
      and 'overall_quality_grade' in crew_src, '')

# ---------------------------------------------------------------- summary
print()
print(f'OP40 metadata honesty + print toggle matrix: '
      f'{PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
    sys.exit(1)
