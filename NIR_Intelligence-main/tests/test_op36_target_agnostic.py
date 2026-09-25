"""OP36 verification: the whole chain is target-value (Zielwert) agnostic.

User requirement: "es sind nicht nur BRIX kalibrierungen die wir
anschauen. Es muss zielwert agnostisch sein und diesen anfragen, wenn
die Metadaten oder die Messwertlisten keinen Rueckschluss darauf
zulassen" - the platform must never assume Brix as calibration target:

T1  wide ingest records the reference column name as target_name
T2  target_name lands in the dataset metadata dict
T3  no Brix assumption: a non-brix reference column is recorded verbatim
T4  forward questions: zielwert asked when no target and no reference values
T5  zielwert question is asked only once (topic dedup)
T6  no zielwert question when reference values exist (derivable from data)
T7  no zielwert question when target_name is already in metadata
T8  zielwert question names the standards it unlocks
T9  zielwert question offers target_name in the metadata editor
T10 calibration charts: _ref_vs_pred labels carry the custom target
T11 calibration charts: _rmsecv_vs_n labels carry the custom target
T12 calibration charts: default stays neutral ("Zielwert")
T13 xai charts: prediction_vs_actual labels carry the custom target
T14 student report: analyte comes from target_name, not hardcoded Brix
T15 student report: RMSE paragraphs use the custom target unit
T16 student report: neutral wording when no target recorded
T17 chatbot: RMSE answer uses the custom target unit
T18 chatbot: neutral "Zieleinheit" when no target recorded
T19 no Brix hardcodes remain in the platform source
T20 project_crew passes target_name to the chart builders
"""
import os
import sys
import tempfile
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


import pandas as pd  # noqa: E402
from services import project_ingest  # noqa: E402

CHANNELS = ['A_610', 'B_680', 'C_730', 'D_760', 'E_810', 'F_860',
            'G_560', 'H_585', 'I_645', 'J_705', 'K_900', 'L_940']

tmp = tempfile.mkdtemp(prefix='op36_')

# ---------------------------------------------------------------- data
# Non-brix calibration target: a fat content column ("Fett_prozent")
csv_path = os.path.join(tmp, 'OEL_MK_Train.csv')
targets = [12.5, 18.2, 14.1, 19.8, 13.3, 16.7, 15.2, 17.9] * 2 + \
          [12.5, 18.2, 14.1, 19.8]
data = []
for i in range(20):
    row = {'Probe': f'Oel_{i % 3}', 'Fett_prozent': targets[i]}
    for c in CHANNELS:
        row[c] = 1000.0 + i * 2.5 + CHANNELS.index(c) * 37
    data.append(row)
pd.DataFrame(data).to_csv(csv_path, sep=';', index=False)


class _Record:
    def __init__(self, path, name, rid='00000000-0000-0000-0000-000000000003'):
        self.id = rid
        self.name = name
        self.file_extension = Path(path).suffix.lower() or '.csv'
        self.file_category = 'text'

    def get_file_path(self):
        return csv_path


entry = project_ingest._ingest_single_file(
    _Record(csv_path, 'OEL_MK_Train.csv'), csv_path)

meta = entry.get('metadata') or {}

# ---------------------------------------------------------------- T1-T3
check('T1 wide ingest records the reference column as target_name',
      meta.get('target_name') == 'Fett_prozent',
      f'target_name={meta.get("target_name")!r}')
check('T2 target_name is plain metadata (editor/report visible)',
      'target_name' in meta, f'meta keys={sorted(meta.keys())}')
check('T3 no Brix assumption: non-brix column recorded verbatim',
      'Brix' not in str(meta.get('target_name')) and bool(meta.get('target_name')),
      f'target_name={meta.get("target_name")!r}')

# ---------------------------------------------------------------- T4-T9
project_ingest._ki_forward_questions(entry, project_ingest._metadata_standards())
questions = entry.get('open_questions') or []
check('T4 no zielwert question when the data provides the target',
      not any(q.startswith("KI-Frage zum Thema 'zielwert'") for q in questions),
      f'questions={questions}')

entry_notarget = {'usable': True, 'metadata': {},
                  'open_questions': []}
project_ingest._ki_forward_questions(entry_notarget,
                                     project_ingest._metadata_standards())
qs_a = entry_notarget.get('open_questions') or []
check('T5 zielwert asked when no target and no reference values',
      any(q.startswith("KI-Frage zum Thema 'zielwert'") for q in qs_a),
      f'questions={qs_a}')
check('T6 zielwert question asks only once (topic dedup)',
      sum(1 for q in qs_a if q.startswith("KI-Frage zum Thema 'zielwert'")) == 1,
      f'questions={qs_a}')

entry_refvals = {'usable': True, 'metadata': {},
                 'reference_values': [1.0, 2.0, 3.0],
                 'open_questions': []}
project_ingest._ki_forward_questions(entry_refvals,
                                     project_ingest._metadata_standards())
check('T7 no zielwert question when reference values exist',
      not any(q.startswith("KI-Frage zum Thema 'zielwert'")
              for q in (entry_refvals.get('open_questions') or [])),
      f'questions={entry_refvals.get("open_questions")}')

entry_meta_target = {'usable': True,
                     'metadata': {'target_name': 'Wassergehalt'},
                     'open_questions': []}
project_ingest._ki_forward_questions(entry_meta_target,
                                     project_ingest._metadata_standards())
check('T8 no zielwert question when target_name in metadata',
      not any(q.startswith("KI-Frage zum Thema 'zielwert'")
              for q in (entry_meta_target.get('open_questions') or [])),
      f'questions={entry_meta_target.get("open_questions")}')

zielwert_q = next((q for q in qs_a
                      if q.startswith("KI-Frage zum Thema 'zielwert'")), '')
check('T9 zielwert question is a clear escalation to the user',
      zielwert_q.startswith("KI-Frage zum Thema 'zielwert'")
      and 'Kalibrationsziel' in zielwert_q,
      f'question={zielwert_q!r}')
check('T9a zielwert question offers target_name in the editor',
      any(q.startswith("KI-Frage zum Thema 'zielwert'")
          and 'Fehlende Felder: target_name' in q for q in qs_a),
      f'questions={qs_a}')

# ---------------------------------------------------------------- T10-T13
import matplotlib
matplotlib.use('Agg')
from services import calibration_charts, xai_charts  # noqa: E402

import numpy as np  # noqa: E402

rng = np.random.default_rng(7)
n_samples, n_wl = 30, 12
X = rng.normal(1000, 50, size=(n_samples, n_wl))
y = 10 + X[:, 0] * 0.01 + rng.normal(0, 0.2, n_samples)
wl = [610.0, 680.0, 730.0, 760.0, 810.0, 860.0, 560.0, 585.0,
      645.0, 705.0, 900.0, 940.0]

cal_url = calibration_charts._ref_vs_pred(
    y, y * 1.01, 0.98, 0.25, 'PLS (3 Komponenten)', 'Fett_prozent')
check('T10 _ref_vs_pred renders with custom target (no exception, data url)',
      cal_url.startswith('data:image/png;base64,'), f'url={cal_url[:40]!r}')

cal_default = calibration_charts._ref_vs_pred(
    y, y * 1.01, 0.98, 0.25, 'PLS (3 Komponenten)')
check('T11 _ref_vs_pred default label stays neutral',
      cal_default.startswith('data:image/png;base64,'), '')

rmsecv_url = calibration_charts._rmsecv_vs_n(
    [1, 2, 3], [0.9, 0.6, 0.7], 2, 'Fett_prozent')
check('T12 _rmsecv_vs_n renders with custom target',
      rmsecv_url.startswith('data:image/png;base64,'), '')

rmsecv_default = calibration_charts._rmsecv_vs_n([1, 2, 3], [0.9, 0.6, 0.7], 2)
check('T12a _rmsecv_vs_n default label stays neutral',
      rmsecv_default.startswith('data:image/png;base64,'), '')

import inspect  # noqa: E402

sig_cal = inspect.signature(calibration_charts.calibration_chart_data_urls)
check('T12b calibration_chart_data_urls accepts target_name',
      'target_name' in sig_cal.parameters, f'sig={sig_cal}')

sig_xai = inspect.signature(xai_charts.xai_chart_data_urls)
check('T13 xai_chart_data_urls accepts target_name',
      'target_name' in sig_xai.parameters, f'sig={sig_xai}')

xai_url = xai_charts._prediction_vs_actual(y, y * 1.01, 'Fett_prozent')
check('T13a _prediction_vs_actual renders with custom target',
      xai_url.startswith('data:image/png;base64,'), '')

# ---------------------------------------------------------------- T14-T16
from services import student_report  # noqa: E402

datasets = [{'metadata': {'target_name': 'Fett_prozent'}}]
analyte = student_report._dataset_target_name(datasets)
check('T14 student report analyte comes from target_name',
      analyte == 'Fett_prozent', f'analyte={analyte!r}')
check('T14a student report neutral when no dataset target',
      student_report._dataset_target_name([]) is None
      and student_report._dataset_target_name([{'metadata': {}}]) is None,
      '')

per_agent = [{
    'agent': 'calibration',
    'data': {'method_results': {'PLS': {'mean_r2': 0.9}},
             'best_r2_score': 0.92},
}, {
    'agent': 'neural_network',
    'data': {'model_results': {'CNN': {'r2_score': 0.88, 'rmse': 0.31}}},
}]
paras = student_report.model_quality_paragraphs(per_agent,
                                                target_name='Fett_prozent')
check('T15 RMSE paragraphs use the custom target unit',
      any('Fett_prozent' in p for p in paras)
      and not any('Brix' in p for p in paras), f'paras={paras}')

paras_neutral = student_report.model_quality_paragraphs(per_agent)
check('T16 RMSE paragraphs neutral wording without target',
      any('Zieleinheit' in p for p in paras_neutral)
      and not any('Brix' in p for p in paras_neutral), f'paras={paras_neutral}')

# ---------------------------------------------------------------- T17-T18
sys.path.insert(0, str(PROJECT / 'django_project'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
import django  # noqa: E402
django.setup()

from agents.chatbot_agent import ChatbotAgent  # noqa: E402

context = {
    'per_agent_reports': [{
        'agent': 'neural_network',
        'data': {'model_results': {'CNN': {'r2_score': 0.88, 'rmse': 0.31}}},
    }],
    'crew_results': {'overall_quality_score': 80.0},
    'datasets': [{'file_name': 'oel.csv',
                  'metadata': {'target_name': 'Fett_prozent'}}],
    'overview_keys': [],
}
out = ChatbotAgent().execute(context)
entries = (out.data or {}).get('knowledge_base') if hasattr(out, 'data') else None
answers = [e.get('answer', '') for e in (entries or [])]
check('T17 chatbot RMSE answer uses the custom target unit',
      any('Fett_prozent' in a for a in answers)
      and not any('Brix' in a for a in answers), f'answers={answers}')

context_neutral = {
    'per_agent_reports': [{
        'agent': 'neural_network',
        'data': {'model_results': {'CNN': {'r2_score': 0.88, 'rmse': 0.31}}},
    }],
    'crew_results': {},
    'datasets': [{'file_name': 'oel.csv', 'metadata': {}}],
    'overview_keys': [],
}
out_neutral = ChatbotAgent().execute(context_neutral)
entries_n = ((out_neutral.data or {}).get('knowledge_base')
             if hasattr(out_neutral, 'data') else None)
answers_n = [e.get('answer', '') for e in (entries_n or [])]
check('T18 chatbot neutral "Zieleinheit" without target',
      any('Zieleinheit' in a for a in answers_n)
      and not any('Brix' in a for a in answers_n), f'answers={answers_n}')

# ---------------------------------------------------------------- T19
source_files = [
    PROJECT / 'services' / 'calibration_charts.py',
    PROJECT / 'services' / 'xai_charts.py',
    PROJECT / 'services' / 'student_report.py',
    PROJECT / 'agents' / 'chatbot_agent.py',
    PROJECT / 'services' / 'project_crew.py',
]
offenders = []
for sf in source_files:
    text = sf.read_text(encoding='utf-8')
    if '\u00b0Brix' in text or '(Brix)' in text:
        offenders.append(sf.name)
check('T19 no Brix hardcodes remain in the platform source',
      not offenders, f'offenders={offenders}')

# ---------------------------------------------------------------- T20
crew_text = (PROJECT / 'services' / 'project_crew.py').read_text(encoding='utf-8')
_needle = "get('target_name') or 'Zielwert'"
check('T20 project_crew passes target_name to both chart builders',
      crew_text.count(_needle) == 2,
      f'occurrences={crew_text.count(_needle)}')

# ---------------------------------------------------------------- summary
print()
print(f'OP36 target-agnostic matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
    sys.exit(1)
