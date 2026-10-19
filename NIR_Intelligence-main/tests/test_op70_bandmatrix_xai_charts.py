#!/usr/bin/env python3
# OP70 test matrix:
#  (a) Brix-Band-Konfusionsmatrix (gemessen x geschaetzt) in der Fusion,
#      inkl. Aufteilung pro Quell-Datensatz + Heatmap-Chart
#  (b) CNN/XAI-Graphen IMMER - sklearn-MLP-Fallback ohne TensorFlow
# Offline-safe, deterministisch (seed 42).
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
# T1: _brix_band_matrix - Logik
# ---------------------------------------------------------------------------
from services.fusion_calibration import _brix_band_matrix  # noqa: E402
pairs = [{'reference': 4.0 + i * 0.8, 'predicted': 4.0 + i * 0.8 + 0.1}
         for i in range(20)]
bm = _brix_band_matrix(pairs)
check("T1a band matrix computed", bool(bm.get('matrix')))
check("T1b labels are Brix ranges (Bandid   )",
      all('-' in l for l in bm['labels']), str(bm['labels'][:2]))
total = sum(sum(r) for r in bm['matrix'])
check("T1c alle Messungen in der Matrix", total == len(pairs), total)
diag = sum(bm['matrix'][i][i] for i in range(bm['n_bands']))
check("T1d nahezu-perfekte Vorhersage -> Diagonale dominiert",
      diag == len(pairs), diag)

pairs_src = ([{'reference': 4.0 + i * 0.5, 'predicted': 4.0 + i * 0.5}
              for i in range(20)]
             + [{'reference': 6.0 + i * 0.5, 'predicted': 6.0 + i * 0.5 + 1.0}
                for i in range(20)])
srcs = ['A.csv'] * 20 + ['B.csv'] * 20
bm2 = _brix_band_matrix(pairs_src, src_labels=srcs)
check("T1e per_source aufgeteilt",
      set(bm2.get('per_source', {})) == {'A.csv', 'B.csv'})
check("T1f Quelle A diagonal perfekt",
      sum(bm2['per_source']['A.csv'][i][i]
          for i in range(bm2['n_bands'])) == 20)
check("T1g Quelle B off-diagonal (Systematik sichtbar)",
      sum(bm2['per_source']['B.csv'][i][i]
          for i in range(bm2['n_bands'])) < 20)

# T2: _band_matrix_chart - PNG oder ehrliches None
from services.fusion_calibration import _band_matrix_chart  # noqa: E402
try:
    import matplotlib  # noqa: F401
    chart = _band_matrix_chart(bm['matrix'], bm['labels'], 'Test')
    check("T2a chart is PNG data URL",
          bool(chart) and chart.startswith('data:image/png;base64,'))
except ImportError:
    chart = _band_matrix_chart(bm['matrix'], bm['labels'], 'Test')
    check("T2a honest None without matplotlib", chart is None)

# ---------------------------------------------------------------------------
# T3: comparative_calibration liefert die Matrix + Charts (Runtime)
# ---------------------------------------------------------------------------
import numpy as np  # noqa: E402
from core.models import AnalysisProject  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from services.fusion_calibration import comparative_calibration  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op70cal").first()
if user is None:
    user = User.objects.create_user("op70cal", password="pw",
                                    email="op70@example.com")
rng = np.random.default_rng(42)
nf = 12
X = rng.normal(0, 1, (60, nf))
w = rng.normal(0, 1, nf)
y = X @ w + rng.normal(0, 0.1, 60) + 4.0


def _mk(name, samples, targets, fusion_sources=None, fname=None):
    prep = {'datasets': [
        {'file_id': fname or f'{name}.csv', 'usable': True,
         'file_name': fname or f'{name}.csv',
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


pa = _mk("Q70 A", X[:30], y[:30], fname='A.csv')
pb = _mk("Q70 B", X[30:], y[30:], fname='B.csv')
# Fusionsprojekt mit ZWEI Datensaetzen (realistisches Layout nach
# execute_fusion: die Messreihen beider Quellen im neuen Projekt) -
# nur so kann die Band-Matrix die Quellen trennen.
pf = AnalysisProject.objects.create(user=user, name="Fusion 70")
pf.preparation_report = {
    'fusion': {'source_projects': [{'project_id': str(pa.id)},
                                   {'project_id': str(pb.id)}]},
    'datasets': [
        {'file_id': 'A.csv', 'usable': True, 'file_name': 'A.csv',
         'calibration_samples': [list(map(float, r)) for r in X[:30]],
         'reference_values': [float(t) for t in y[:30]],
         'target_name': 'brix'},
        {'file_id': 'B.csv', 'usable': True, 'file_name': 'B.csv',
         'calibration_samples': [list(map(float, r)) for r in X[30:]],
         'reference_values': [float(t) for t in y[30:]],
         'target_name': 'brix'},
    ]}
pf.save(update_fields=['preparation_report'])
comparison = comparative_calibration(pf, [pa, pb])
cals = comparison.get('calibrations', {})
ok_cals = {l: c for l, c in cals.items() if c.get('status') == 'ok'}
check("T3a alle drei Kalibrationen ok", len(ok_cals) == 3)
bm_in_all = all(
    ((c.get('predicted_vs_reference') or {}).get('brix_band_matrix') or {})
    .get('matrix')
    for c in ok_cals.values())
check("T3b Brix-Band-Matrix in jeder Kalibration", bm_in_all)
fused_cal = ok_cals.get('Fusion 70', {})
check("T3c band_matrix_chart am Fusionsdatensatz",
      bool(fused_cal.get('band_matrix_chart')))
per_src_charts = fused_cal.get('band_matrix_charts_sources') or {}
check("T3d pro Quell-Datensatz ein Chart (A.csv, B.csv)",
      set(per_src_charts) == {'A.csv', 'B.csv'}
      and all(bool(v) for v in per_src_charts.values()), str(per_src_charts))

# ---------------------------------------------------------------------------
# T4: XAI-Graphen IMMER (MLP-Fallback ohne TensorFlow)
# ---------------------------------------------------------------------------
src_xai = (REPO_ROOT / "services" / "xai_charts.py").read_text(encoding="utf-8")
check("T4a MLP-Fallback implementiert",
      "def _mlp_fallback_charts" in src_xai)
check("T4b TF-Check routed zu Fallback statt leerem Dict",
      "return _mlp_fallback_charts(" in src_xai
      and "if not _tensor_flow_available():" in src_xai)

from services.xai_charts import xai_chart_data_urls  # noqa: E402
Xs = rng.normal(0, 1, (60, 10)).tolist()
ys = (np.asarray(Xs) @ np.linspace(0.1, 0.9, 10) + 4).tolist()
charts = xai_chart_data_urls(Xs, ys, list(range(410, 500, 9)),
                             epochs=20, target_name='brix')
try:
    import tensorflow  # noqa: F401
    tf_present = True
except ImportError:
    tf_present = False
if tf_present:
    check("T4c mit TF: volle Key-Menge",
          {'prediction_vs_actual', 'loss_curves', 'shap_summary',
           'shap_waterfall', 'saliency_map', 'grad_cam',
           'attention_weights'} <= set(charts.keys()),
          str(sorted(charts.keys())))
else:
    check("T4c ohne TF: Graphen trotzdem da (Fallback-Keys)",
          {'prediction_vs_actual', 'loss_curves', 'shap_summary',
           'shap_waterfall'} <= set(charts.keys()),
          str(sorted(charts.keys())))
    check("T4d TF-exklusive Keys ehrlich weg (kein Fake)",
          'grad_cam' not in charts and 'attention_weights' not in charts)
check("T4e alle Werte PNG-Data-URLs",
      all(v.startswith('data:image/png;base64,') for v in charts.values()))

# ---------------------------------------------------------------------------
# T5: UI-Rendering der Band-Matrix
# ---------------------------------------------------------------------------
main_src = (REPO_ROOT / "django_project" / "static" / "js"
            / "main.js").read_text(encoding="utf-8")
check("T5a Band-Matrix-Tabelle gerendert",
      "brix_band_matrix" in main_src and "Konfusionsmatrix" in main_src)
check("T5b Heatmap-Chart gerendert (gesamt + pro Quelle)",
      "band_matrix_chart" in main_src
      and "band_matrix_charts_sources" in main_src)
import subprocess  # noqa: E402
res = subprocess.run(["node", "--check",
                      str(REPO_ROOT / "django_project" / "static" / "js"
                          / "main.js")],
                     capture_output=True, text=True)
check("T5c node --check main.js", res.returncode == 0, res.stderr[:200])

# Regression: OP63-OP68-Felder weiterhin intakt
body_keys = list(comparison.keys())
check("T6a OP68-Felder intakt (sensor_comparison, correction_variants)",
      'sensor_comparison' in body_keys
      and ('correction_variants' in body_keys
           or 'gain_curve_report' in body_keys))
check("T6b OP66/OP63-Felder intakt (significance, calibrations)",
      'significance' in body_keys and 'calibrations' in body_keys)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
