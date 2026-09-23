"""OP25 verification: website cleanup + workflow overview diagram.

The platform grew many legacy demo pages (dashboard, agents, spectra, files,
analysis, jobs, settings, documentation, chatbot, ilias) that are not part of
the implemented project workflow (upload -> metadata -> release -> report ->
spectral database). OP25 reduces the navigation to the real workflow links,
rebuilds the start page as a workflow overview diagram where hovering a step
shows a German explanation of that step, and keeps the legacy routes/templates
functional (existing suites such as test_op7 depend on files.html). Offline.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


PROJECT = Path(__file__).resolve().parent.parent
DJANGO_DIR = PROJECT / 'django_project'
TEMPLATES = DJANGO_DIR / 'templates'

LEGACY_HREFS = [
    'href="/dashboard/"',
    'href="/agents/"',
    'href="/spectra/"',
    'href="/files/"',
    'href="/analysis/"',
    'href="/jobs/"',
    'href="/settings/"',
    'href="/documentation/"',
    'href="/chatbot/"',
    'href="/ilias/"',
]

WORKFLOW_HREFS = [
    ('/projects/', 'projects list'),
    ('/projects/database/', 'spectral database'),
    ('/login/', 'login'),
    ('/register/', 'register'),
]

WORKFLOW_STEPS = [
    ('Login / Registrierung', 'login/register'),
    ('Projekt anlegen (Upload)', 'project upload'),
    ('Metadaten bearbeiten', 'metadata editor'),
    ('Dateien erg&auml;nzen', 'add files (Bearbeiten)'),
    ('Release (Agenten-Analyse)', 'crew release'),
    ('Abschlussbericht', 'final report + chatbot'),
    ('Spektrendatenbank', 'persistent database'),
]

# ---------------------------------------------------------------------------
# T1: base.html navigation cleaned to the real workflow
# ---------------------------------------------------------------------------
base_src = (TEMPLATES / 'base.html').read_text()

check('T1a base.html exists', (TEMPLATES / 'base.html').exists())
for href in LEGACY_HREFS:
    short = href.split('/')[-2]
    check(f'T1b no legacy nav link /{short}/', href not in base_src,
          f'{href} found in base.html')
for href, label in WORKFLOW_HREFS:
    check(f'T1c workflow link {label} present', href in base_src,
          f'{href} missing from base.html')
check('T1d navbar labels are the German workflow labels',
      'Projekte' in base_src and 'Spektrendatenbank' in base_src)
check('T1e settings link removed from the user dropdown',
      'href="/settings/"' not in base_src)

# ---------------------------------------------------------------------------
# T2: start page shows the workflow overview diagram with hover tooltips
# ---------------------------------------------------------------------------
index_src = (TEMPLATES / 'index.html').read_text()

check('T2a index.html exists', (TEMPLATES / 'index.html').exists())
for step_title, label in WORKFLOW_STEPS:
    check(f'T2b workflow step present: {label}', step_title in index_src)
check('T2c step explanation container present',
      'workflow-tooltip' in index_src and index_src.count('workflow-tooltip') >= 7,
      'expected at least 7 tooltip blocks')
check('T2d steps are numbered 1..7',
      all(f'workflow-step__num">{n}<' in index_src for n in range(1, 8)))
check('T2e hover/focus tooltip behaviour wired (CSS)',
      '.workflow-step:hover .workflow-tooltip' in index_src
      and '.workflow-step:focus-visible .workflow-tooltip' in index_src)
check('T2f arrows between the steps',
      index_src.count('workflow-arrow') >= 6)
check('T2g steps reference the real UI actions',
      'Neues Projekt (Upload)' in index_src
      and 'Zur Analyse freigeben' in index_src
      and 'Bearbeiten' in index_src
      and 'Quarto-Abschlussbericht' in index_src)
check('T2h start page links only workflow targets',
      all(href in index_src for href, _ in WORKFLOW_HREFS)
      and all(h not in index_src for h in LEGACY_HREFS))

# ---------------------------------------------------------------------------
# T3: projects/database pages free of legacy links
# ---------------------------------------------------------------------------
projects_src = (TEMPLATES / 'projects.html').read_text()
database_src = (TEMPLATES / 'spectrum_database.html').read_text()
detail_src = (TEMPLATES / 'spectrum_detail.html').read_text()
report_src = (TEMPLATES / 'project_report.html').read_text()

for name, src in (('projects.html', projects_src),
                  ('spectrum_database.html', database_src),
                  ('spectrum_detail.html', detail_src),
                  ('project_report.html', report_src)):
    check(f'T3a {name} has no legacy links',
          all(h not in src for h in LEGACY_HREFS))

# ---------------------------------------------------------------------------
# T4: templates compile with the real Django engine
# ---------------------------------------------------------------------------
import os  # noqa: E402
import django  # noqa: E402

sys.path.insert(0, str(DJANGO_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
django.setup()

from django.template.loader import get_template  # noqa: E402

for name in ('base.html', 'index.html', 'projects.html',
             'project_report.html', 'spectrum_database.html',
             'spectrum_detail.html', 'login.html', 'register.html'):
    try:
        get_template(name)
        check(f'T4a {name} compiles', True)
    except Exception as exc:
        check(f'T4a {name} compiles', False, str(exc)[:120])

# ---------------------------------------------------------------------------
# T5: legacy routes stay functional (unlinked, but not broken)
# ---------------------------------------------------------------------------
from django.urls import resolve, Resolver404  # noqa: E402

LEGACY_ROUTES = [
    ('/dashboard/', 'dashboard'),
    ('/agents/', 'agents-page'),
    ('/spectra/', 'spectra-page'),
    ('/files/', 'files-page'),
    ('/chatbot/', 'chatbot-page'),
    ('/ilias/', 'ilias-page'),
    ('/analysis/', 'analysis-page'),
    ('/jobs/', 'jobs-page'),
    ('/settings/', 'settings-page'),
    ('/documentation/', 'documentation-page'),
]
for path, name in LEGACY_ROUTES:
    try:
        match = resolve(path)
        check(f'T5a legacy route {path} still resolves', match.view_name == name,
              f'view={match.view_name}')
    except Resolver404:
        check(f'T5a legacy route {path} still resolves', False, 'Resolver404')

WORKFLOW_ROUTES = [
    ('/projects/', 'project-list'),
    ('/projects/create/', 'project-create'),
    ('/projects/database/', 'spectrum-database'),
    ('/login/', 'login'),
    ('/register/', 'register'),
]
for path, name in WORKFLOW_ROUTES:
    try:
        match = resolve(path)
        check(f'T5b workflow route {path} resolves', match.view_name == name,
              f'view={match.view_name}')
    except Resolver404:
        check(f'T5b workflow route {path} resolves', False, 'Resolver404')

# ---------------------------------------------------------------------------
# T6: workflow diagram centered in two rows; visible figure captions
# ---------------------------------------------------------------------------
check('T6a workflow diagram centered (max-width + auto margins)',
      'margin: 0 auto' in index_src and 'max-width: 900px' in index_src)
check('T6b steps grouped into centered rows (4 + 3)',
      index_src.count('workflow-row') >= 4 and 'workflow-row--wrap' in index_src)
check('T6c wrap arrow between the rows', 'bi-arrow-return-down' in index_src)

report_src = (PROJECT / 'services' / 'project_report.py').read_text()
check('T6d figure registry mirrors the student report numbering',
      '_figure_registry' in report_src and 'section_index' in report_src)
check('T6e visible "Abbildung N" captions rendered under the charts',
      '_figure_caption' in report_src and 'Abbildung {number}' in report_src)
check('T6f agent sections receive their own figure numbers',
      'section_figures=section_figures' in report_src)
check('T6g overview charts carry captions too',
      'fig-caption' in report_src
      and report_src.count('_figure_caption(number') >= 2)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f'OP25 website cleanup matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', ', '.join(FAILED))
    sys.exit(1)
