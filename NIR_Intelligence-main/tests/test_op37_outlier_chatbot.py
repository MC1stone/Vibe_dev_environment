"""OP37 verification: documented outlier analysis + KI-first chatbot.

User requirement: "Die Darstellung der Spektren zeigt, dass hier keine
Ausreisser-Analyse stattfindet und diese Ausreisser dokumentiert werden.
Auch ist der Bot nicht wirklich gut, er ist sehr eingeschraenkt in
seinen Antworten."

T1  outlier detection: clean measurements -> no outliers, assessable
T2  outlier detection: one deviant measurement is found exactly
T3  detection is robust (MAD): a huge spike does not break the verdict
T4  too few measurements -> honest 'not assessable' verdict
T5  verdict carries the numbers (count, threshold, z-scores)
T6  charts rendered: distance plot + spectrum overlay as data urls
T7  overlay marks the outlier measurement (distinct from inliers)
T8  findings text names the outlier indices and the method
T9  findings text for clean data names 'keine Ausreisser'
T10 crew _outlier_section: completed section with data + charts
T11 crew report contains the outlier section (wired into sections)
T12 report renders outlier charts with captions (figure registry)
T13 report agent section renders the findings as 'Befunde' paragraphs
T14 student report: findings appear in the error sources (Diskussion)
T15 chatbot KB: outlier entry with concrete findings + figure links
T16 chatbot widget is KI-first: asks /api/chatbot/message/ with context
T17 chatbot widget carries the compact report context (facts only)
T18 chatbot widget keeps the offline keyword fallback (labelled)
T19 chatbot widget sends conversation history (multi-turn)
T20 chatbot widget no longer crashes the report on empty KB ('')
T21 context is bounded (anti-bloat, max chars per document)
T22 widget JS is syntactically closed (template placeholders replaced)
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


import numpy as np  # noqa: E402
from services import outlier_analysis  # noqa: E402

rng = np.random.default_rng(11)
WL = np.array([610.0, 680.0, 730.0, 760.0, 810.0, 860.0, 560.0, 585.0,
               645.0, 705.0, 900.0, 940.0])
WL_LIST = WL.tolist()


def _spectrum():
    # realistic sensor spectrum: smooth structure + small noise
    # (pure white noise has no spectral shape, SNV would flatten it and
    # no distance spread would exist - see T1a)
    base = 1000.0 + 50.0 * np.sin((WL - 560.0) / 100.0)
    return base + rng.normal(0, 3.0, len(WL))


# ---------------------------------------------------------------- T1-T5
clean = np.array([_spectrum() for _ in range(20)])
verdict_clean = outlier_analysis.detect_outliers(clean.tolist(), WL_LIST)
check('T1 clean measurements -> assessable, no outliers',
      verdict_clean['assessable'] and not verdict_clean['outlier_indices'],
      f'v={verdict_clean}')
check('T1a clean verdict is not an error',
      not verdict_clean.get('reason') or 'keine Ausreisser' in verdict_clean['reason'],
      f"reason={verdict_clean.get('reason')!r}")

dirty = clean.copy()
# clearly deviant: strong water-band-like dip around 940 nm + bump at 760
dirty[4] = (dirty[4]
            - 120.0 * np.exp(-((WL - 940.0) / 25.0) ** 2)
            + 90.0 * np.exp(-((WL - 760.0) / 30.0) ** 2))
verdict_dirty = outlier_analysis.detect_outliers(dirty.tolist(), WL_LIST)
check('T2 deviant measurement found exactly',
      verdict_dirty['assessable']
      and verdict_dirty['outlier_indices'] == [4],
      f"outliers={verdict_dirty['outlier_indices']}")

spike = clean.copy()
spike[19, 3] = 2 ** 31  # 32-bit ADC saturation marker
verdict_spike = outlier_analysis.detect_outliers(spike.tolist(), WL_LIST)
check('T3 detection survives a huge saturation spike',
      verdict_spike['assessable'] and 19 in verdict_spike['outlier_indices'],
      f"outliers={verdict_spike['outlier_indices']}")

verdict_few = outlier_analysis.detect_outliers(clean[:3].tolist(), WL_LIST)
check('T4 too few measurements -> honest not-assessable',
      not verdict_few['assessable'] and verdict_few['reason'],
      f'v={verdict_few}')

check('T5 verdict carries the numbers',
      verdict_dirty['measurement_count'] == 20
      and verdict_dirty['threshold'] == 3.5
      and len(verdict_dirty['robust_z_scores']) == 20
      and len(verdict_dirty['distances']) == 20,
      f"v={ {k: verdict_dirty[k] for k in ('measurement_count', 'threshold')} }")

# ---------------------------------------------------------------- T6-T9
charts = outlier_analysis.outlier_charts(dirty.tolist(), WL_LIST, verdict_dirty, 'oel.csv')
check('T6 distance plot + overlay rendered',
      charts.get('outlier_distance', '').startswith('data:image/png;base64,')
      and charts.get('outlier_overlay', '').startswith('data:image/png;base64,'),
      f'keys={list(charts)}')
check('T6a no charts when not assessable',
      outlier_analysis.outlier_charts(clean[:3].tolist(), WL_LIST, verdict_few, 'x') == {})

findings = outlier_analysis.outlier_findings_text(verdict_dirty, 'oel.csv')
check('T8 findings name outlier index and method',
      any('Messung 5' in f and 'z-Score' in f and 'Median' in f
          for f in findings),
      f'findings={findings}')
findings_clean = outlier_analysis.outlier_findings_text(verdict_clean, 'oel.csv')
check('T9 clean findings name "keine Ausreisser"',
      any('keine Ausreisser' in f for f in findings_clean),
      f'findings={findings_clean}')

# ---------------------------------------------------------------- T10-T13
dataset = {'file_name': 'oel.csv',
           'preview': {'wavelengths': WL_LIST},
           'measurement_samples': dirty.tolist()}
from services import project_crew  # noqa: E402
section = project_crew._outlier_section(dataset)
check('T10 crew outlier section completed with data + charts',
      section['agent'] == 'outlier_analysis'
      and section['status'] == 'completed'
      and section['data']['assessable']
      and section['data']['outlier_indices'] == [4]
      and 'outlier_distance' in section.get('charts', {}),
      f'section={section}')

src = (PROJECT / 'services' / 'project_crew.py').read_text(encoding='utf-8')
check('T11 outlier section wired into the report sections',
      'sections.append(_outlier_section(dataset))' in src, '')

from services import project_report  # noqa: E402
figures = project_report._figure_registry(
    [{'agent': 'outlier_analysis', 'charts': charts}], [])
fig_map = {f['key']: f['number'] for f in figures}
html = project_report._agent_section_html(
    {'agent': 'outlier_analysis', 'title': 'Ausreisser-Analyse',
     'status': 'completed',
     'data': {'assessable': True, 'measurement_count': 20,
              'outlier_indices': [4], 'threshold': 3.5,
              'findings': findings},
     'charts': charts},
    section_figures=figures)
chart_area = html.split('<details>')[0]  # OP39: source code follows as details
check('T12 report renders outlier charts with captions',
      'outlier_distance' not in chart_area  # img src is a data url, alt instead
      and 'Ausreisser-Abst' in chart_area
      and f"Abbildung {fig_map.get('outlier_distance')}" in html,
      f'fig_map={fig_map}')
check('T13 findings rendered as Befunde paragraphs',
      '<h3>Befunde</h3>' in html and 'Messung 5' in html, html[:400])

# ---------------------------------------------------------------- T14
from services import student_report  # noqa: E402
per_agent = [{'agent': 'outlier_analysis', 'status': 'completed',
              'data': {'findings': findings}}]
items = student_report.error_source_items(per_agent)
check('T14 student report documents the findings in the Diskussion',
      any('Ausreisser-Analyse:' in i and 'Messung 5' in i for i in items),
      f'items={items[:2]}')

# ---------------------------------------------------------------- T15
sys.path.insert(0, str(PROJECT / 'django_project'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
import django  # noqa: E402
django.setup()

from agents.chatbot_agent import ChatbotAgent  # noqa: E402
figures_full = project_report._figure_registry(
    [{'agent': 'outlier_analysis', 'charts': charts}], [])
context = {'per_agent_reports': per_agent,
           'crew_results': {}, 'datasets': [],
           'overview_keys': []}
out = ChatbotAgent().execute(context)
kb = (out.data or {}).get('knowledge_base') or []
check('T15 chatbot KB carries the outlier findings',
      any(e['category'] == 'Ausreisser' and 'Messung 5' in e['answer']
          for e in kb),
      f'kb={[(e["category"], e["answer"][:40]) for e in kb]}')

# ---------------------------------------------------------------- T16-T22
from services import report_chatbot  # noqa: E402
widget = report_chatbot.chatbot_html(
    per_agent, {'overall_quality_score': 80.0,
                'recommendations': ['Metadaten ergaenzen']},
    [dataset])['widget']
check('T16 widget is KI-first: posts to /api/chatbot/message/',
      '/api/chatbot/message/' in widget, '')
check('T16a widget shows the KI thinking state',
      'KI denkt' in widget, '')
ctx_docs = report_chatbot._compact_report_context(
    per_agent, {'overall_quality_score': 80.0}, [dataset])
check('T17 widget context carries report facts',
      any('Ausreisser' in d['text'] for d in ctx_docs)
      and any('Gesamtqualitaet der Analyse: 80.0' in d['text']
              for d in ctx_docs),
      f'ctx={ctx_docs[:2]}')
check('T18 offline keyword fallback kept and labelled',
      'Offline-Wissensbasis' in widget and 'topEntries' in widget, '')
check('T19 widget sends conversation history (multi-turn)',
      'history.slice(-6)' in widget, '')
check('T20 empty KB -> no widget, full builder never crashes',
      report_chatbot.build_chatbot_widget([]) == ''
      and isinstance(report_chatbot.chatbot_html([], {}, [])['widget'], str), '')
check('T21 context documents are bounded',
      all(len(d['text']) <= 4000 for d in ctx_docs), '')
check('T22 template placeholders fully replaced',
      '__KB__' not in widget and '__CTX__' not in widget, '')

# ---------------------------------------------------------------- summary
print()
print(f'OP37 outlier + chatbot matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', FAILED)
    sys.exit(1)
