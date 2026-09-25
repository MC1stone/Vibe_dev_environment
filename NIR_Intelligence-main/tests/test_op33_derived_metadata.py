"""OP33 verification: KI derives standard-relevant metadata from the data
and asks the user for what the data cannot provide.

User requirement (verified against the oil ZIP report): the standards
verdict listed wavelength_range, resolution, integration_time and
instrument_model as missing - but except integration_time everything
can be CALCULATED from the loaded data. The KI is expected to analyse
for that, predict/suggest the values and expose them to the user.

T1  derived pass: wavelength_range computed from the wavelength axis
T2  derived pass: resolution computed from axis span and point count
T3  derived pass: scan_count mirrors the wide-export measurement count
T4  derived pass: never overwrites user/header-provided values
T5  derived pass: non-usable datasets are skipped (no invention)
T6  derived values are visible in the metadata rating (source: ki berechnet)
T7  standards compliance flips: ASTM_E1655 gains wavelength_range+resolution
T8  forward questions: integration_time asked (not derivable -> ask user)
T9  forward questions: instrument_model asked
T10 forward questions: no question for fields already present
T11 forward questions carry the standards the field unlocks
T12 recommendations reference the KI question (escalation, never silent)
T13 offline resilience: template question survives without Ollama
T14 project_report.html compiles with the computed-source badge
T15 regression: OP31 conflict/verbatim logic unaffected
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

tmp = tempfile.mkdtemp(prefix='op33_')
csv_path = os.path.join(tmp, 'OEL_MK_Train.csv')
data = []
for i in range(20):
    row = {'Probe': f'Oel_{i % 3}', 'Brix': 10.0 + i * 0.3}
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


# ---------------------------------------------------------------- T1-T5
entry = project_ingest._ingest_single_file(
    _Record(csv_path, 'OEL_MK_Train.csv'), csv_path)
meta = entry.get('metadata') or {}
sources = entry.get('metadata_sources') or {}
check('T1 wavelength_range computed from the axis',
      meta.get('wavelength_range') == '560.0-940.0 nm (380.0 nm Spanne, 12 Punkte)',
      f'wr={meta.get("wavelength_range")!r}')
check('T2 resolution computed from span and point count',
      meta.get('resolution') == '34.55 nm (12 Punkte)',
      f'res={meta.get("resolution")!r}')
check('T3 scan_count mirrors the measurement count',
      meta.get('scan_count') == '20', f'sc={meta.get("scan_count")!r}')
check('T4a derived fields marked as ki-computed source',
      sources.get('wavelength_range') == 'ki (aus Daten berechnet)'
      and sources.get('resolution') == 'ki (aus Daten berechnet)',
      f'sources={sources}')

entry_prefill = {
    'usable': True, 'wavelength_min': 560.0, 'wavelength_max': 940.0,
    'num_points': 12, 'num_measurements': 20,
    'metadata': {'wavelength_range': 'vom Geraet: 560-940 nm',
                 'resolution': '3.5 nm (laut Herstellervertrag)'},
    'metadata_sources': {},
}
project_ingest._derived_metadata_pass(entry_prefill)
check('T4b never overwrites provided values',
      entry_prefill['metadata']['wavelength_range'] == 'vom Geraet: 560-940 nm'
      and entry_prefill['metadata']['resolution'] == '3.5 nm (laut Herstellervertrag)',
      f'meta={entry_prefill["metadata"]}')

entry_unusable = {'usable': False, 'wavelength_min': 1.0, 'wavelength_max': 2.0,
                  'num_points': 5, 'metadata': {}, 'metadata_sources': {}}
project_ingest._derived_metadata_pass(entry_unusable)
check('T5 non-usable datasets skipped (no invention)',
      not entry_unusable['metadata'], f'meta={entry_unusable["metadata"]}')

# ---------------------------------------------------------------- T6/T7
assessment = project_ingest._assess_metadata([entry])
rating = entry.get('metadata_rating') or {}
check('T6 derived values visible in the metadata rating',
      'wavelength_range' in rating and 'resolution' in rating
      and 'berechnet' in str(rating.get('wavelength_range', {}).get('source')),
      f'rating keys={sorted(rating.keys())}')

compliance = {c['standard']: c for c in assessment.get('standards_compliance', [])}
astm = compliance.get('ASTM_E1655', {})
check('T7 ASTM_E1655 gains the derived fields',
      'wavelength_range' in (astm.get('present') or [])
      and 'resolution' in (astm.get('present') or []),
      f'astm={astm}')

# ---------------------------------------------------------------- T8-T13
project_ingest._ki_forward_questions(entry, project_ingest._metadata_standards())
questions = entry.get('open_questions') or []
check('T8 integration_time asked (not derivable)',
      any(q.startswith("KI-Frage zu 'integration_time'") for q in questions),
      f'questions={questions}')
check('T9 instrument_model asked',
      any(q.startswith("KI-Frage zu 'instrument_model'") for q in questions),
      f'questions={questions}')
check('T10 no question for already present fields',
      not any("KI-Frage zu 'wavelength_range'" in q or "KI-Frage zu 'scan_count'" in q
              for q in questions),
      f'questions={questions}')
check('T11 forward questions name the standards',
      any('ASTM_E1655' in q for q in questions
          if q.startswith("KI-Frage zu 'integration_time'"))
      and any('ASTM_E1655' in q or 'NIR_PUBLIC_DATABASE' in q for q in questions
              if q.startswith("KI-Frage zu 'instrument_model'")),
      f'questions={questions}')

entry_done = {'usable': True,
              'metadata': {'integration_time': '100 ms',
                           'instrument_model': 'Triad NIR'},
              'open_questions': []}
project_ingest._ki_forward_questions(entry_done, project_ingest._metadata_standards())
check('T12 no questions when fields present',
      not entry_done.get('open_questions'),
      f'q={entry_done.get("open_questions")}')

# T13: offline -> template question (no Ollama reachable in CI/sandbox)
check('T13 offline template question survives',
      any('Integrationszeit' in q for q in questions),
      f'questions={questions}')

assessment2 = project_ingest._assess_metadata([entry])
recs = project_ingest._recommendations([entry], assessment2)
check('T14 recommendations escalate the KI question to the user',
      any('KI-Frage' in r or 'integration_time' in r for r in recs),
      f'recs={recs}')

# ---------------------------------------------------------------- T15
sys.path.insert(0, str(PROJECT / 'django_project'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
import django  # noqa: E402
django.setup()
from django.template.loader import get_template  # noqa: E402
try:
    get_template('project_report.html')
    check('T15a project_report.html compiles', True)
except Exception as e:
    check('T15a project_report.html compiles', False, str(e))

from services.metadata_llm import _verbatim  # noqa: E402
check('T15b OP31 verbatim guard unaffected',
      _verbatim('Yvonne', 'die messungen wurden von yvonne gemacht') is True
      and _verbatim('Martin', 'die messungen wurden von yvonne gemacht') is False)

# ---------------------------------------------------------------- summary
print()
print(f'OP33 derived metadata matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
    sys.exit(1)
