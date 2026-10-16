#!/usr/bin/env python3
# OP63 Stufe 3 test matrix: comparative calibration of the fusion branch
# (source A vs source B vs combined + significance test). Offline-safe.
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
# T1: services/fusion_calibration.py existiert, kompiliert, kennt die Form
# ---------------------------------------------------------------------------
cal_path = REPO_ROOT / "services" / "fusion_calibration.py"
check("T1a fusion_calibration.py exists", cal_path.exists())
import py_compile  # noqa: E402
try:
    py_compile.compile(str(cal_path), doraise=True)
    check("T1b fusion_calibration compiles", True)
except Exception as exc:
    check("T1b fusion_calibration compiles", False, str(exc))

from services.fusion_calibration import (  # noqa: E402
    comparative_calibration, _fit_calibration, _significance_test,
    _residuals_by_group, COMPARISON_METHOD,
)
check("T1c comparison method is PLS (NIR standard)",
      COMPARISON_METHOD == "PLS")

# ---------------------------------------------------------------------------
# T2: _significance_test - homoskedastisch vs heteroskedastisch
# ---------------------------------------------------------------------------
import numpy as np  # noqa: E402
rng = np.random.default_rng(42)
homogen = {'A': list(rng.normal(0.0, 0.1, 40)),
           'B': list(rng.normal(0.0, 0.1, 40))}
hetero = {'A': list(rng.normal(0.0, 0.05, 40)),
          'B': list(rng.normal(2.0, 0.6, 40))}
shifted = {'A': list(rng.normal(0.0, 0.1, 40)),
           'B': list(rng.normal(1.0, 0.1, 40))}

res = _significance_test(homogen)
check("T2a homogeneous residuals: test performed", res.get('performed') is True)
check("T2b homogeneous residuals: variance equal",
      res.get('levene', {}).get('variance_equal') is True)
check("T2c homogeneous residuals: means equal",
      res.get('welch_t', {}).get('means_equal') is True)
check("T2d unproblematic interpretation",
      'unproblematisch' in res.get('interpretation', ''))

res = _significance_test(hetero)
check("T2e heterogeneous variance detected",
      res.get('levene', {}).get('variance_equal') is False)

res = _significance_test(shifted)
check("T2f shifted means detected",
      res.get('welch_t', {}).get('means_equal') is False)
check("T2g interpretation mentions systematic offset",
      'ueber-/unterschaetzt' in res.get('interpretation', ''))

res = _significance_test({'A': [0.1, 0.2], 'B': [0.3, 0.4]})
check("T2h too-few-samples handled gracefully",
      res.get('performed') is False and 'reason' in res)

# ---------------------------------------------------------------------------
# T3: _fit_calibration via CalibrationAgent (PLS-Pipeline, CV)
# ---------------------------------------------------------------------------
n_features = 20
X = rng.normal(0.0, 1.0, (60, n_features))
w = rng.normal(0.0, 1.0, n_features)
y = X @ w + rng.normal(0.0, 0.1, 60) + 5.0
fit = _fit_calibration(X.tolist(), y.tolist(), cv_folds=5)
check("T3a calibration fit returns ok", fit is not None
      and fit.get('status') == 'ok', str(fit))
check("T3b fit has r2/rmse/rpd metrics",
      all(k in (fit or {}) for k in ('mean_r2', 'rmse_cv', 'rpd')))
check("T3c strong signal -> good R2", (fit or {}).get('mean_r2', 0) > 0.9,
      f"r2={fit.get('mean_r2')}")

fit_none = _fit_calibration([[1.0, 2.0]] * 5, [1.0] * 5)
check("T3d too-few samples rejected", fit_none is None)

# ---------------------------------------------------------------------------
# T4: comparative_calibration - drei Kalibrationen + Fazit
# ---------------------------------------------------------------------------
from core.models import AnalysisProject  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op63cal").first()
if user is None:
    user = User.objects.create_user("op63cal", password="pw",
                                    email="op63cal@example.com")

Xa = (X[:30] + 0.0)
ya = y[:30]
Xb = (X[30:] + 0.0)
yb = y[30:]


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


pa = _mk_project("Quelle A", Xa, ya)
pb = _mk_project("Quelle B", Xb, yb)
fused = _mk_project("Fusion A+B", list(Xa) + list(Xb), list(ya) + list(yb),
                    fusion_sources=[{'project_id': str(pa.id),
                                    'project_name': 'Quelle A'},
                                   {'project_id': str(pb.id),
                                    'project_name': 'Quelle B'}])

comparison = comparative_calibration(fused, [pa, pb])
check("T4a comparison status ok", comparison.get('status') == 'ok')
cals = comparison.get('calibrations', {})
check("T4b three calibrations computed", len(cals) == 3, str(cals.keys()))
check("T4c combined calibration ok",
      cals.get('Fusion A+B', {}).get('status') == 'ok',
      str(cals.get('Fusion A+B')))
check("T4d combined has more samples than each single",
      (cals.get('Fusion A+B', {}).get('n_samples') or 0)
      > (cals.get('Quelle A', {}).get('n_samples') or 0))
check("T4e target name propagated",
      comparison.get('target_name') == 'brix')
check("T4f conclusion present", bool(comparison.get('conclusion')))
check("T4g significance performed",
      comparison.get('significance', {}).get('performed') is True)

# nicht kalibrierbare Quellen werden ehrlich gemeldet (kein Fake)
pa_bad = _mk_project("Quelle ohne Referenz", [[1.0, 2.0]] * 3, [])
pb_bad = _mk_project("Quelle ohne Referenz 2", [[1.0, 2.0]] * 3, [])
fused2 = _mk_project("Fusion ohne Referenz", [[1.0, 2.0]] * 3, [],
                     fusion_sources=[{'project_id': str(pa_bad.id)},
                                     {'project_id': str(pb_bad.id)}])
comparison2 = comparative_calibration(fused2, [pa_bad, pb_bad])
check("T4h non-calibratable handled honestly",
      all(c.get('status') == 'not_calibratable'
          for c in comparison2.get('calibrations', {}).values()))
check("T4i non-calibratable conclusion explains",
      'nicht kalibrierbar' in comparison2.get('conclusion', ''))

# ---------------------------------------------------------------------------
# T5: API-Endpoint (Runtime) - nur Fusionsprojekte, Auth noetig
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402
import json  # noqa: E402

try:
    url = reverse('project-fusion-calibration', args=[fused.id])
    check("T5a calibration route registered",
          url.endswith('/fusion/calibration/'), url)
except Exception as exc:
    check("T5a calibration route registered", False, str(exc))

client = Client()
client.force_login(user)
r = client.get(f'/api/projects/{fused.id}/fusion/calibration/')
check("T5b calibration endpoint 200 for fusion project",
      r.status_code == 200, f"status {r.status_code}")
body = r.json()
check("T5c endpoint returns comparison", body.get('success') is True
      and len(body.get('calibrations', {})) == 3)
check("T5d endpoint includes source projects",
      len(body.get('source_projects', [])) == 2)

# Nicht-Fusionsprojekt -> 422
r = client.get(f'/api/projects/{pa.id}/fusion/calibration/')
check("T5e non-fusion project rejected 422", r.status_code == 422,
      f"status {r.status_code}")

# Anonym -> verweigert
client.logout()
r = client.get(f'/api/projects/{fused.id}/fusion/calibration/')
check("T5f anonymous rejected", r.status_code in (401, 403),
      f"status {r.status_code}")

# ---------------------------------------------------------------------------
# T6: UI - Panel im Fusionsprojekt-Report + JS-Helper
# ---------------------------------------------------------------------------
tpl = (REPO_ROOT / "django_project" / "templates"
       / "project_report.html").read_text(encoding="utf-8")
check("T6a report shows calibration panel for fusion projects",
      "fusionCalibrationBox" in tpl and "preparation.fusion" in tpl)
check("T6b panel is fusion-only (template guard)",
      "{% if preparation.fusion and preparation.fusion.source_projects %}" in tpl)

main_src = (REPO_ROOT / "django_project" / "static" / "js"
            / "main.js").read_text(encoding="utf-8")
check("T6c nirFusionCalibration helper present",
      "nirFusionCalibration" in main_src)
check("T6d comparison table renders hit rates/MAE/RPD (OP64)",
      all(k in main_src for k in ("hits_within_tolerance", "rpd"))
      and "Trefferquote" in main_src)
check("T6e significance shown with p-values",
      "Levene p=" in main_src and "Welch p=" in main_src)
check("T6f conclusion rendered as Fazit", "Fazit" in main_src)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
