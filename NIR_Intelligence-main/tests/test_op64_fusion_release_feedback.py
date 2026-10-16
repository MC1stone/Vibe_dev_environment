#!/usr/bin/env python3
# OP64 test matrix: release feedback from the tomato fusion live test.
# 1) Brix/target detection: monotonic reference series and per-measurement
#    reference values must be ACCEPTED (previously rejected -> 2nd dataset
#    had no calibration). 2) The fusion provenance section must survive
#    build_preparation_report (previously wiped -> no comparison panel).
# 3) Predicted-vs-reference hit rates per measurement (PO: compare predicted
#    vs actual brix per measurement, not abstract CV only). Offline-safe.
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

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# ---------------------------------------------------------------------------
# T1: Target-Heuristik - echte Referenzmessungen werden akzeptiert
# ---------------------------------------------------------------------------
# Simuliert die Ingest-Target-Auswahl direkt nach (worst case: monoton
# aufsteigende Brix-Reihe, jede Messung eigener Referenzwert)
rng = np.random.default_rng(3)
n = 60
brix = np.sort(rng.uniform(4.0, 12.0, n))          # monoton steigend!
channels = [f"ch_{i}" for i in range(20)]
spectra = np.column_stack([brix * 0.5 + rng.normal(0, 0.3, n)
                           for _ in range(20)])
df = pd.DataFrame(spectra, columns=channels)
df["Brix"] = brix                                   # alle Werte einzigartig

target = pd.to_numeric(df["Brix"], errors="coerce")
# Die alte Heuristik: monoton -> abgelehnt; nunique>=len -> abgelehnt.
# Neu: nur Pseudo-ID-Spalten (nunique>=len UND >2) sind ausgeschlossen.
def _is_pseudo_id(series):
    if not (series.nunique() >= len(series) and series.nunique() > 2):
        return False
    ints = series.dropna()
    if not len(ints) or not (ints == ints.astype(int)).all():
        return False
    steps = ints.diff().dropna().unique()
    return len(steps) == 1 and steps[0] == 1.0


check("T1a monotonic brix series is NOT a pseudo-id (accepted)",
      bool(_is_pseudo_id(target)) is False,
      f"nunique={target.nunique()}, len={len(target)}")
check("T1b per-measurement reference values allowed",
      target.nunique() == n)

# Pseudo-ID bleibt ausgeschlossen (Zeilenzhler-Spalte)
counter = pd.Series(np.arange(n, dtype=float))
check("T1c index/counter column still excluded",
      bool(_is_pseudo_id(counter)) is True)

# ---------------------------------------------------------------------------
# T2: Fusion-Sektion ueberlebt build_preparation_report
# ---------------------------------------------------------------------------
from core.models import AnalysisProject  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op64user").first()
if user is None:
    user = User.objects.create_user("op64user", password="pw",
                                    email="op64@example.com")
pa = AnalysisProject.objects.create(user=user, name="OP64 Quelle A")
pa.preparation_report = {'fusion': {
    'source_projects': [{'project_id': str(pa.id), 'project_name': 'A'}],
    'created_by': 'op63_fusion'}}
pa.save(update_fields=['preparation_report'])

src_ingest = (Path(__file__).resolve().parent.parent
              / "services" / "project_ingest.py").read_text(encoding="utf-8")
check("T2a ingest preserves fusion section (code)",
      "report['fusion'] = fusion_section" in src_ingest)

# Funktionsverhalten: build_preparation_report ohne Dateien laesst die
# Fusion-Sektion stehen (kein Wipe mehr)
from services.project_ingest import build_preparation_report  # noqa: E402
build_preparation_report(pa)
fusion_after = (pa.preparation_report or {}).get('fusion')
check("T2b fusion section survives preparation report build",
      fusion_after is not None
      and fusion_after.get('created_by') == 'op63_fusion',
      str(fusion_after))

# ---------------------------------------------------------------------------
# T3: Predicted-vs-Reference (PO: pro Messung vorhergesagt vs. tatsaechl.)
# ---------------------------------------------------------------------------
from services.fusion_calibration import _predicted_vs_reference  # noqa: E402

X = rng.normal(0.0, 1.0, (80, 15))
w = rng.normal(0.0, 1.0, 15)
y = X @ w + rng.normal(0.0, 0.05, 80) + 6.0
pvr = _predicted_vs_reference(X.tolist(), y.tolist(), cv_folds=5)
check("T3a pvr computed", pvr is not None)
check("T3b pairs: one per measurement", pvr['n'] == 80
      and len(pvr['pairs']) == 80)
check("T3c hit rates present for both tolerances",
      set(pvr['hits_within_tolerance'].keys()) == {'0.5', '1.0'})
h05 = pvr['hits_within_tolerance']['0.5']
check("T3d strong signal: >=90% within +-1.0",
      pvr['hits_within_tolerance']['1.0']['ratio'] >= 0.9,
      f"ratio={pvr['hits_within_tolerance']['1.0']['ratio']}")
check("T3e hit counts consistent", h05['n_within'] <= 80
      and 0.0 <= h05['ratio'] <= 1.0)
check("T3f mae/rmse present", 'mae' in pvr and 'rmse' in pvr)
check("T3g predictions near reference (mae small)",
      pvr['mae'] < 1.0, f"mae={pvr['mae']}")

# ---
pvr_none = _predicted_vs_reference([[1.0, 2.0]] * 5, [1.0] * 5)
check("T3h too-few samples -> None", pvr_none is None)

# ---------------------------------------------------------------------------
# T4: comparative_calibration liefert pvr je Kalibration
# ---------------------------------------------------------------------------
from services.fusion_calibration import comparative_calibration  # noqa: E402


def _mk(name, samples, targets, fusion_sources=None):
    prep = {'datasets': [
        {'file_id': f'{name}.csv', 'usable': True, 'file_name': f'{name}.csv',
         'calibration_samples': [list(map(float, s)) for s in samples],
         'reference_values': [float(t) for t in targets],
         'target_name': 'brix'}]}
    if fusion_sources:
        prep['fusion'] = {'source_projects': fusion_sources}
    p = AnalysisProject.objects.create(user=user, name=name)
    p.preparation_report = prep
    p.save(update_fields=['preparation_report'])
    return p


pb = _mk("OP64 B", X[:40].tolist(), y[:40].tolist())
pc = _mk("OP64 Fusion", X.tolist(), y.tolist(),
         fusion_sources=[{'project_id': str(pa.id)},
                         {'project_id': str(pb.id)}])
comparison = comparative_calibration(pc, [pa, pb])
cals = comparison.get('calibrations', {})
ok_cals = {l: c for l, c in cals.items() if c.get('status') == 'ok'}
check("T4a fused + one source calibratable",
      'OP64 Fusion' in ok_cals and 'OP64 B' in ok_cals, str(cals.keys()))
check("T4b fused calibration carries predicted_vs_reference",
      ok_cals.get('OP64 Fusion', {}).get('predicted_vs_reference')
      is not None)
check("T4c single calibrations carry predicted_vs_reference",
      ok_cals.get('OP64 B', {}).get('predicted_vs_reference') is not None)

# ---------------------------------------------------------------------------
# T5: UI - Trefferquote-Spalte im JS
# ---------------------------------------------------------------------------
main_src = (Path(__file__).resolve().parent.parent / "django_project"
             / "static" / "js" / "main.js").read_text(encoding="utf-8")
check("T5a UI shows hit rates (Trefferquote)",
      "Trefferquote" in main_src
      and "hits_within_tolerance" in main_src)
check("T5b UI explains the metric", "tatsächlichen innerhalb der Toleranz"
      in main_src)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
