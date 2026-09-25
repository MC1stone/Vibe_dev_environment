"""OP35 verification: KI-requested fields ready in the editor + metadata
overview in the final report (Abschlussbericht).

Two user requirements after OP34:

1. The fields the KI asks for (forward questions: instrument_model,
   serial_number, integration_time, ...) must be AVAILABLE AS INPUTS as
   soon as the edit mode opens - so answering the KI is just typing
   into the offered field, not hunting for the right field name.

2. The final report (Abschlussbericht) must contain a metadata
   overview: per dataset field/value/source with the KI badges, the
   standards compliance table and the open KI questions - documenting
   what the analysis was based on.

T1  editor offers the KI-requested fields (parsed from open_questions)
T2  offered KI fields are empty inputs (value '')
T3  editor keeps existing values prefilled (regression)
T4  no duplicate fields (KI question repeated -> field listed once)
T5  editor ignores questions without 'Fehlende Felder' (konflikte etc.)
T6  final report: metadata overview section renders
T7  final report: per-dataset field/value/source table
T8  final report: source badges (ki computed / projekt-kontext / file)
T9  final report: standards compliance table included
T10 final report: open KI questions listed per dataset
T11 final report: KI relevance summary included
T12 final report: empty datasets -> no section (honest, no invention)
T13 regression: project_report.html (phase-1 template) still compiles
"""

import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / 'django_project'))

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


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
import django  # noqa: E402
django.setup()

from django_project.api.project_views import _metadata_editor_fields  # noqa: E402
from services.project_report import _metadata_overview_html  # noqa: E402

RECOMMENDED = ['operator', 'humidity', 'temperature', 'instrument',
               'acquisition_time']

SENSOR_Q = ("KI-Frage zum Thema 'sensor' (relevant f\u00fcr ASTM_E1655, "
            "ISO_12099, NIR_PUBLIC_DATABASE): Der Sensor ist nur "
            "unvollst\u00e4ndig dokumentiert. Fehlende Felder: "
            "instrument_model, serial_number. Bekannt ist bereits: "
            "instrument_type=Triadsensor. Bitte im Metadaten-Editor "
            "erg\u00e4nzen.")
MESSPARAM_Q = ("KI-Frage zum Thema 'messparameter' (relevant f\u00fcr "
               "ASTM_E1655): Die Integrationszeit ist nicht aus den "
               "Messdaten ableitbar. Fehlende Felder: integration_time. "
               "Bitte im Metadaten-Editor erg\u00e4nzen.")
CONFLICT_Q = ("Metadatenkonflikt f\u00fcr 'operator_name': Deterministisch "
              "'Yvonne', die KI las 'Yvonne Mueller'.")

# ---------------------------------------------------------------- T1-T5
dataset = {
    'metadata': {'operator_name': 'Yvonne', 'temperature': '25'},
    'open_questions': [SENSOR_Q, MESSPARAM_Q, CONFLICT_Q,
                       SENSOR_Q],
}
fields = _metadata_editor_fields(dataset, RECOMMENDED)
names = [f['name'] for f in fields]
check('T1 editor offers the KI-requested fields',
      all(n in names for n in ('instrument_model', 'serial_number',
                               'integration_time')),
      f'names={names}')
check('T2 offered KI fields are empty inputs',
      all(f['value'] == '' for f in fields
          if f['name'] in ('instrument_model', 'serial_number',
                           'integration_time')),
      f'fields={fields}')
check('T3 existing values stay prefilled',
      any(f['name'] == 'operator' and f['value'] == 'Yvonne' for f in fields),
      f'fields={fields}')
check('T4 no duplicate fields (repeated question -> listed once)',
      len(names) == len(set(names)), f'names={names}')
check('T5 conflict questions add no fields',
      'operator_name' not in names
      and all(n in names for n in RECOMMENDED),
      f'names={names}')

# ---------------------------------------------------------------- T6-T12
datasets = [{
    'file_name': 'OEL_MK_Train.csv',
    'metadata_rating': {
        'operator_name': {'value': 'Yvonne', 'source': 'projekt-kontext',
                          'rating': 'ok'},
        'wavelength_range': {'value': '560.0-940.0 nm',
                             'source': 'ki (aus Daten berechnet)',
                             'rating': 'ok'},
        'temperature': {'value': '25', 'source': 'deterministisch',
                         'rating': 'ok'},
    },
    'open_questions': [SENSOR_Q],
}]
mq = {
    'standards_compliance': [
        {'standard': 'ISO_12099', 'present': ['operator_name'],
         'missing': ['sample_id', 'timestamp'], 'satisfied': False},
        {'standard': 'EURACHEM', 'present': ['temperature', 'humidity'],
         'missing': [], 'satisfied': True},
    ],
    'ki_relevance': {'summary': 'Gute Basisdokumentation vorhanden.',
                     'nir_relevance': {}, 'priority_missing': []},
}
html = _metadata_overview_html(datasets, mq)
check('T6 metadata overview section renders',
      'Metadaten-&Uuml;bersicht' in html, f'html={html[:200]}')
check('T7 per-dataset field/value/source table',
      'operator_name' in html and 'Yvonne' in html
      and 'OEL_MK_Train.csv' in html, f'html={html[:300]}')
check('T8 source badges (ki/ctx/file)',
      'meta-ki' in html and 'meta-ctx' in html and 'meta-file' in html,
      f'html={html[:300]}')
check('T9 standards compliance table included',
      'ISO_12099' in html and 'EURACHEM' in html
      and 'unvollst&auml;ndig' in html and 'erf&uuml;llt' in html,
      f'html={html[:300]}')
check('T10 open KI questions listed per dataset',
      'Offene KI-Fragen' in html and 'instrument_model' in html,
      f'html={html[:300]}')
check('T11 KI relevance summary included',
      'Gute Basisdokumentation vorhanden.' in html, f'html={html[:300]}')

check('T12 empty datasets -> no section (honest)',
      _metadata_overview_html([], {}) == ''
      and _metadata_overview_html([{'file_name': 'x',
                                    'metadata_rating': {}}], {}) == '',
      'empty case rendered content')

# ---------------------------------------------------------------- T13
from django.template.loader import get_template  # noqa: E402
try:
    get_template('project_report.html')
    check('T13 project_report.html still compiles', True)
except Exception as e:
    check('T13 project_report.html still compiles', False, str(e))

# ---------------------------------------------------------------- summary
print()
print(f'OP35 metadata editor + final report matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
    sys.exit(1)
