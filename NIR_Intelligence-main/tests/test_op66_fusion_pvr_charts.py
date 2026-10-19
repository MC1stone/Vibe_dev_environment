#!/usr/bin/env python3
# OP66 test matrix:
#  a) Chart-Erklaerungen auch in der Kalibrations-Uebersicht (/calibration/)
#  b) Predicted-vs-Reference-Streudiagramm des Fusionsprojekts als EIN
#     kombinierter Datensatz (Brix-Vorhersage vs. gemessene Brix)
#  c) Fusionsergebnisse als Chatbot-Diskussionskontext (MO 10)
# Offline-safe: Django in-memory, keine externen Dienste.
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "django_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {detail}")


try:
    import django
    django.setup()
    check("T0a django setup", True)
except Exception as exc:
    check("T0a django setup", False, str(exc))
    sys.exit(1)

from django.conf import settings as dj_settings  # noqa: E402

if "testserver" not in dj_settings.ALLOWED_HOSTS:
    dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]
dj_settings.DATABASES["default"]["NAME"] = ":memory:"
dj_settings.DATABASES["default"].setdefault("ATOMIC_REQUESTS", False)

from django.core.management import call_command  # noqa: E402
call_command("migrate", interactive=False, verbosity=0)

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# T1: fusion_calibration.py - PVR-Chart fuer das Fusionsprojekt
# ---------------------------------------------------------------------------
import py_compile  # noqa: E402

cal_path = REPO_ROOT / "services" / "fusion_calibration.py"
check("T1a fusion_calibration.py exists", cal_path.exists())
try:
    py_compile.compile(str(cal_path), doraise=True)
    check("T1b fusion_calibration compiles", True)
except Exception as exc:
    check("T1b fusion_calibration compiles", False, str(exc))

src = cal_path.read_text(encoding="utf-8")
check("T1c _pvr_chart reuses calibration_charts._ref_vs_pred",
      "_ref_vs_pred" in src and "from services.calibration_charts import" in src,
      "no chart logic copy allowed")
check("T1d pvr_chart only attached to the fused project",
      "pid == str(fused_project.id)" in src and "pvr_chart" in src)

from services.fusion_calibration import _pvr_chart  # noqa: E402
pvr = {'n': 40, 'cv_folds': 5, 'rmse': 0.2, 'mae': 0.1,
       'pairs': [{'reference': float(i % 10), 'predicted': float(i % 10) + 0.1}
                 for i in range(40)]}
try:
    chart = _pvr_chart(pvr, 'brix', 'Fusion A+B')
    try:
        import matplotlib  # noqa: F401
        check("T1e pvr chart is a PNG data URL", bool(chart)
              and chart.startswith('data:image/png;base64,'), str(chart)[:60])
    except ImportError:
        check("T1e pvr chart degrades to None without matplotlib",
              chart is None, "honest degradation expected")
except Exception as exc:
    check("T1e pvr chart never raises", False, str(exc))

check("T1f empty pairs -> None (no fake chart)",
      _pvr_chart({'pairs': []}, 'brix', 'Fusion') is None)

# ---------------------------------------------------------------------------
# T2: comparative_calibration liefert pvr_chart + discussion_summary
# ---------------------------------------------------------------------------
import numpy as np  # noqa: E402
from core.models import AnalysisProject  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from services.fusion_calibration import comparative_calibration  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op66cal").first()
if user is None:
    user = User.objects.create_user("op66cal", password="pw",
                                    email="op66cal@example.com")

rng = np.random.default_rng(42)
n_features = 20
X = rng.normal(0.0, 1.0, (60, n_features))
w = rng.normal(0.0, 1.0, n_features)
y = X @ w + rng.normal(0.0, 0.1, 60) + 5.0


def _mk_project(name, samples, targets, fusion_sources=None):
    prep = {'datasets': [
        {'file_id': f'{name}.csv', 'usable': True,
         'file_name': f'{name}.csv',
         'calibration_samples': [list(map(float, s)) for s in samples],
         'reference_values': [float(t) for t in targets],
         'target_name': 'brix'},
    ]}
    if fusion_sources:
        prep['fusion'] = {'source_projects': fusion_sources}
    p = AnalysisProject.objects.create(user=user, name=name)
    p.preparation_report = prep
    p.save(update_fields=['preparation_report'])
    return p


pa = _mk_project("Quelle A", X[:30], y[:30])
pb = _mk_project("Quelle B", X[30:], y[30:])
fused = _mk_project("Fusion A+B", list(X), list(y),
                    fusion_sources=[{'project_id': str(pa.id),
                                     'project_name': 'Quelle A'},
                                    {'project_id': str(pb.id),
                                     'project_name': 'Quelle B'}])

comparison = comparative_calibration(fused, [pa, pb])
check("T2a comparison status ok", comparison.get('status') == 'ok')
cals = comparison.get('calibrations', {})
fused_cal = cals.get('Fusion A+B', {})
check("T2b fused dataset carries pvr_chart key",
      'pvr_chart' in fused_cal, str(fused_cal.keys()))
try:
    import matplotlib  # noqa: F401
    check("T2c fused pvr_chart is a PNG data URL",
          bool(fused_cal.get('pvr_chart'))
          and fused_cal['pvr_chart'].startswith('data:image/png;base64,'))
except ImportError:
    check("T2c fused pvr_chart degrades honestly (no matplotlib)",
          fused_cal.get('pvr_chart') is None)
singles_have_no_chart = all('pvr_chart' not in c
                            for l, c in cals.items() if l != 'Fusion A+B')
check("T2d single datasets carry no fused chart", singles_have_no_chart)

summary = comparison.get('discussion_summary') or ''
check("T2e discussion_summary present", bool(summary))
check("T2f summary contains metrics and Fazit",
      'R2/CV' in summary and 'Fazit' in summary, summary[:120])

# ---------------------------------------------------------------------------
# T3: Endpoint liefert fusion_project_name (UI-Anzeige des kombinierten
#     Datensatzes) - nur Fusionsprojekte
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402

client = Client()
client.force_login(user)
r = client.get(f'/api/projects/{fused.id}/fusion/calibration/')
check("T3a endpoint 200", r.status_code == 200, f"status {r.status_code}")
body = r.json()
check("T3b endpoint returns fusion_project_name",
      body.get('fusion_project_name') == 'Fusion A+B')
check("T3c endpoint returns discussion_summary",
      bool(body.get('discussion_summary')))

# ---------------------------------------------------------------------------
# T4: UI - Chart + Erklaerung im Stufe-3-Panel, Chatbot-Kontext
# ---------------------------------------------------------------------------
main_src = (REPO_ROOT / "django_project" / "static" / "js"
            / "main.js").read_text(encoding="utf-8")
check("T4a main.js renders the fused pvr chart img",
      "pvr_chart" in main_src and "<img" in main_src)
check("T4b chart carries collapsible explanation",
      "Was zeigt dieses Diagramm?" in main_src)
check("T4c chart only rendered for the fused dataset",
      "fusion_project_name" in main_src)
check("T4d discussion summary fed into chatbot context",
      "nirChatbotContext" in main_src
      and "fusion_discussion" in main_src)

panel_src = (REPO_ROOT / "django_project" / "static" / "js"
             / "chatbot_panel.js").read_text(encoding="utf-8")
check("T4e chatbot panel sends fusion discussion as document",
      "fusion_discussion" in panel_src and "documents" in panel_src
      and "fusion_calibration" in panel_src)

node = os.environ.get("NODE_BIN", "node")
try:
    import subprocess
    for js in ("main.js", "chatbot_panel.js"):
        res = subprocess.run([node, "--check",
                              str(REPO_ROOT / "django_project" / "static" / "js" / js)],
                             capture_output=True, text=True)
        check(f"T4f node --check {js}", res.returncode == 0,
              res.stderr[:200])
except FileNotFoundError:
    check("T4f node --check (node not available)", True, "skipped")

# ---------------------------------------------------------------------------
# T5: OP66a - Chart-Erklaerungen in der Kalibrations-Uebersicht
# ---------------------------------------------------------------------------
tpl = (REPO_ROOT / "django_project" / "templates"
       / "calibration_overview.html").read_text(encoding="utf-8")
check("T5a calibration_overview loads chart_explanations",
      "load chart_explanations" in tpl)
check("T5b every chart gets a collapsible explanation dropdown",
      "Was zeigt dieses Diagramm?" in tpl
      and "chart_explanation" in tpl)
check("T5c explanations reuse the shared filter (no duplicate logic)",
      "CHART_EXPLANATIONS" not in tpl)

# Template kompiliert (Django-Parser)
try:
    from django.template.loader import get_template
    get_template("calibration_overview.html")
    check("T5d calibration_overview template compiles", True)
except Exception as exc:
    check("T5d calibration_overview template compiles", False, str(exc))

# Regression: project_report-Erklaerungen unveraendert vorhanden
report_tpl = (REPO_ROOT / "django_project" / "templates"
              / "project_report.html").read_text(encoding="utf-8")
check("T5e project_report chart explanations intact",
      "chart_explanation" in report_tpl)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
