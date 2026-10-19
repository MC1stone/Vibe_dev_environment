#!/usr/bin/env python3
# OP68 test matrix: Sensor-Analyse + Korrektur-Loop der Fusion
# (a) sensoragnostischer Dark/White-Referenzvertrag (>= 50 Wiederholungen)
# (b) Gain-Kurve aus Referenzen (nur Fusionsprojekte, OP68-Scope)
# (c) Korrekturvarianten SNV/MSC/Gain + korrigiertes Verdict
# (d) Sensor-Vergleich aller Details (Ratios, Korrelation, Konfundierung)
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
# T1: fusion_sensor_analysis.py existiert, kompiliert, Vertrag bekannt
# ---------------------------------------------------------------------------
import py_compile  # noqa: E402
svc = REPO_ROOT / "services" / "fusion_sensor_analysis.py"
check("T1a fusion_sensor_analysis.py exists", svc.exists())
try:
    py_compile.compile(str(svc), doraise=True)
    check("T1b compiles", True)
except Exception as exc:
    check("T1b compiles", False, str(exc))

from services.fusion_sensor_analysis import (  # noqa: E402
    MIN_REFERENCE_REPEATS, apply_gain_curve, gain_curve_from_references,
    reference_measurements, sensor_comparison,
)

check("T1c Mindestvertrag 50 Wiederholungen", MIN_REFERENCE_REPEATS == 50)

# T2: Referenzvertrag - Deklaration, Compliance, Sensoragnostik
ref_ok = {'metadata': {'reference_type': 'white', 'n_repeats': 55,
                       'reference_artifact': 'White-Kappe'},
          'calibration_samples': [[100.0, 200.0]] * 55,
          'usable': True, 'dataset_type': 'measurement'}
r = reference_measurements(ref_ok)
check("T2a compliant white reference recognized",
      r and r['compliant'] and r['reference_type'] == 'white')

ref_short = {'metadata': {'reference_type': 'white', 'n_repeats': 10},
             'calibration_samples': [[1.0]] * 10, 'usable': True}
r = reference_measurements(ref_short)
check("T2b < 50 Wiederholungen -> nicht konform (ehrliche Meldung)",
      r and not r['compliant'] and 'Mindestvertrag' in r['reason'])

r = reference_measurements({'metadata': {'reference_type': 'pink'},
                            'usable': True})
check("T2c unbekannter Referenztyp -> None (kein Fake)", r is None)
r = reference_measurements({'metadata': {}, 'usable': True})
check("T2d ohne Deklaration -> None (sensoragnostisch: nur Vertrag zaehlt)",
      r is None)

# T3: Gain-Kurve aus Referenzen
wa = {'reference_type': 'white', 'n_repeats': 55, 'compliant': True,
      'values': [[100.0, 200.0]] * 55}
wb = {'reference_type': 'white', 'n_repeats': 60, 'compliant': True,
      'values': [[150.0, 260.0]] * 60}
da = {'reference_type': 'dark', 'n_repeats': 55, 'compliant': True,
      'values': [[5.0, 8.0]] * 55}
db = {'reference_type': 'dark', 'n_repeats': 55, 'compliant': True,
      'values': [[6.0, 9.0]] * 55}
gc = gain_curve_from_references([da, wa], [db, wb])
check("T3a gain curve estimable with compliant refs", gc['estimable'] is True)
check("T3b curve values finite & positive",
      all(v > 0 for v in gc['gain_curve']))
gc_no = gain_curve_from_references([da, wa], [db])
check("T3c ohne White in Quelle B -> ehrlich nicht schaetzbar",
      gc_no['estimable'] is False and 'White' in gc_no['reason'])

# apply_gain_curve
corrected = apply_gain_curve([[150.0, 260.0]], gc['gain_curve'])
check("T3d apply_gain_curve skaliert B->A",
      abs(corrected[0][0] - 100.0) < 25.0)
try:
    apply_gain_curve([[1.0, 2.0]], [0.5])
    check("T3e falsche Kanalzahl -> ValueError", False)
except ValueError:
    check("T3e falsche Kanalzahl -> ValueError", True)

# T4: Sensor-Vergleich (alle Details) - synthetische Quellen mit Offset+Gain
import numpy as np  # noqa: E402
rng = np.random.default_rng(42)
n, k = 60, 6
Xa = rng.normal(1000, 100, (n, k))
ya = Xa @ np.linspace(0.1, 0.5, k) + rng.normal(0, 0.05, n) + 4.0
gain = np.linspace(1.4, 0.8, k)          # kanalabhaengiger Gain B->A
Xb = Xa * gain + rng.normal(0, 20, (n, k))
yb = ya + rng.normal(0, 0.05, n)
ds_a = [{'usable': True, 'dataset_type': 'measurement',
         'file_name': 'a.csv', 'calibration_samples': Xa.tolist()}]
ds_b = [{'usable': True, 'dataset_type': 'measurement',
         'file_name': 'b.csv', 'calibration_samples': Xb.tolist()}]
cmp_res = sensor_comparison(ds_a, ds_b, channel_names=['c1', 'c2', 'c3',
                                                       'c4', 'c5', 'c6'])
check("T4a comparison performed", cmp_res['performed'] is True)
check("T4b per-channel ratios present",
      len(cmp_res['channels']) == 6
      and all('ratio_b_over_a' in c for c in cmp_res['channels']))
check("T4c correlation structure present",
      cmp_res['correlation_structure'] is not None)
check("T4d significant channels counted",
      isinstance(cmp_res['n_significant_channels'], int)
      and cmp_res['n_significant_channels'] >= 1)
cmp_bad = sensor_comparison([{'usable': False}], ds_b)
check("T4e zu wenige Daten -> performed False + reason",
      cmp_bad['performed'] is False and 'reason' in cmp_bad)

# T5: Korrektur-Loop in comparative_calibration (echte Funktion)
from core.models import AnalysisProject  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from services.fusion_calibration import (  # noqa: E402
    comparative_calibration, correction_variants, corrected_verdict,
)

User = get_user_model()
user = User.objects.filter(username="op68cal").first()
if user is None:
    user = User.objects.create_user("op68cal", password="pw",
                                    email="op68@example.com")


def _mk_project(name, samples, targets, fusion_sources=None,
                reference_ds=None):
    datasets = [{'file_id': f'{name}.csv', 'usable': True,
                 'file_name': f'{name}.csv',
                 'calibration_samples': [list(map(float, s)) for s in samples],
                 'reference_values': [float(t) for t in targets],
                 'target_name': 'brix'}]
    if reference_ds:
        datasets.append(reference_ds)
    prep = {'datasets': datasets}
    if fusion_sources:
        prep['fusion'] = {'source_projects': fusion_sources}
    p = AnalysisProject.objects.create(user=user, name=name)
    p.preparation_report = prep
    p.save(update_fields=['preparation_report'])
    return p


pa = _mk_project("Q68 A", Xa.tolist(), ya.tolist())
pb = _mk_project("Q68 B", Xb.tolist(), yb.tolist())
pf = _mk_project("Fusion 68", list(Xa.tolist()) + list(Xb.tolist()),
                 list(ya.tolist()) + list(yb.tolist()),
                 fusion_sources=[{'project_id': str(pa.id),
                                  'project_name': 'Q68 A'},
                                 {'project_id': str(pb.id),
                                  'project_name': 'Q68 B'}])
comparison = comparative_calibration(pf, [pa, pb])
check("T5a comparison ok", comparison.get('status') == 'ok')
check("T5b sensor_comparison in result",
      comparison.get('sensor_comparison', {}).get('performed') is True)
check("T5c gain_curve_report ehrlich ohne Referenzen",
      comparison['gain_curve_report']['estimable'] is False
      and 'reason' in comparison['gain_curve_report'])
cv = comparison.get('correction_variants') or {}
check("T5d Korrekturvarianten gerechnet (snv + msc)",
      {'snv', 'msc'} <= set(cv.keys()),
      str(cv.keys()))
check("T5e jede Variante mit kreuzvalidierter Bewertung",
      all((v.get('predicted_vs_reference') or {}).get('pairs')
          for v in cv.values()))
check("T5f korrigiertes Verdict vorhanden",
      bool(comparison.get('corrected_verdict')))
check("T5g Verdict nennt beste Variante + Empfehlung",
      'Beste Korrekturvariante' in comparison['corrected_verdict']
      and 'Referenzmessung' in comparison['corrected_verdict'])

# T6: mit complianten Referenzen wird gain_curve-Variante gerechnet
wa_ds = {'file_id': 'refa.csv', 'usable': True,
         'dataset_type': 'measurement',
         'file_name': 'refa.csv',
         'calibration_samples': [[100.0, 200.0, 300.0,
                                   400.0, 500.0, 600.0]] * 55,
         'metadata': {'reference_type': 'white', 'n_repeats': 55}}
wb_ds = {'file_id': 'refb.csv', 'usable': True,
         'dataset_type': 'measurement',
         'file_name': 'refb.csv',
         'calibration_samples': [[150.0, 260.0, 340.0,
                                   410.0, 470.0, 520.0]] * 55,
         'metadata': {'reference_type': 'white', 'n_repeats': 55}}
da_ds = {'file_id': 'darka.csv', 'usable': True,
         'dataset_type': 'measurement', 'file_name': 'darka.csv',
         'calibration_samples': [[5.0, 8.0, 1.0, 2.0, 3.0, 4.0]] * 55,
         'metadata': {'reference_type': 'dark', 'n_repeats': 55}}
db_ds = {'file_id': 'darkb.csv', 'usable': True,
         'dataset_type': 'measurement', 'file_name': 'darkb.csv',
         'calibration_samples': [[6.0, 9.0, 1.2, 2.2, 3.1, 4.1]] * 55,
         'metadata': {'reference_type': 'dark', 'n_repeats': 55}}
pa2 = _mk_project("Q68 A ref", Xa.tolist(), ya.tolist(), reference_ds=wa_ds)
pb2 = _mk_project("Q68 B ref", Xb.tolist(), yb.tolist(),
                  reference_ds=wb_ds)
# Dark in beiden + White in beiden
pa2.preparation_report['datasets'].append(da_ds)
pa2.save(update_fields=['preparation_report'])
pb2.preparation_report['datasets'].append(db_ds)
pb2.save(update_fields=['preparation_report'])
pf2 = _mk_project("Fusion 68 ref", list(Xa.tolist()) + list(Xb.tolist()),
                  list(ya.tolist()) + list(yb.tolist()),
                  fusion_sources=[{'project_id': str(pa2.id)},
                                  {'project_id': str(pb2.id)}])
comp2 = comparative_calibration(pf2, [pa2, pb2])
check("T6a gain_curve_report estimable mit Referenzen",
      comp2['gain_curve_report'].get('estimable') is True,
      str(comp2['gain_curve_report'])[:150])
cv2 = comp2.get('correction_variants') or {}
check("T6b gain_curve-Variante gerechnet", 'gain_curve' in cv2,
      str(cv2.keys()))
check("T6c gain_curve-Variante traegt die Kurve",
      isinstance(cv2.get('gain_curve', {}).get('gain_curve'), list))

# T7: corrected_verdict Logik isoliert
v = {'snv': {'predicted_vs_reference': {'rmse': 0.30, 'pairs': [1] * 5,
                                        'hits_within_tolerance': {},
                                        'mae': 0.2, 'n': 5}},
     'msc': {'predicted_vs_reference': {'rmse': 0.40, 'pairs': [1] * 5,
                                        'hits_within_tolerance': {},
                                        'mae': 0.3, 'n': 5}}}
verdict = corrected_verdict(0.5, v, 0.995)
check("T7a beste Variante gewaehlt (RMSE-minimal: snv)",
      'snv' in verdict and 'msc' not in verdict.split('Beste')[1][:10])
check("T7b Verbesserung erkannt", 'verbessert' in verdict)
check("T7c korrigierte Fusion unter Einzelquelle -> Empfehlung "
      "Referenzmessung", 'Einzelquelle' in verdict
      and 'Referenzmessung' in verdict, verdict)
# Fachlicher Grenzfall: korrigierte Fusion ERREICHT die Einzelquelle
# -> positive Option statt Empfehlung (kein falsch-negatives Verdict)
verdict_up = corrected_verdict(0.5, v, 0.9)
check("T7c2 erreicht Einzelquelle -> Fusion als Option gemeldet",
      'Option' in verdict_up and 'bleibt unter' not in verdict_up)
verdict2 = corrected_verdict(None, {}, None)
check("T7d keine Varianten -> ehrliche Meldung",
      'Keine Korrekturvariante' in verdict2)

# T8: Endpoint liefert die OP68-Felder (Runtime)
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402
client = Client()
client.force_login(user)
r = client.get(f'/api/projects/{pf.id}/fusion/calibration/')
body = r.json()
check("T8a endpoint 200 mit OP68-Feldern", r.status_code == 200
      and 'sensor_comparison' in body and 'gain_curve_report' in body)
check("T8b correction_variants + corrected_verdict im Payload",
      'correction_variants' in body and 'corrected_verdict' in body)

# T9: UI + Chatbot-Kontext
main_src = (REPO_ROOT / "django_project" / "static" / "js"
            / "main.js").read_text(encoding="utf-8")
check("T9a Sensor-Vergleichstabelle gerendert",
      "Sensor-Vergleich der Quellen" in main_src
      and "ratio_b_over_a" in main_src)
check("T9b Konfundierungs-Warnung gerendert",
      "confounding" in main_src and "median_iqr" in main_src)
check("T9c Gain-Kurven-Status gerendert (estimable + Vertragstext)",
      "gain_curve_report" in main_src and "50 Wiederholungen" in main_src)
check("T9d Korrekturvarianten-Tabelle gerendert",
      "correction_variants" in main_src and "Korrigiertes Fazit" in main_src)
check("T9e Chatbot-Kontext enthaelt korrigierte Bewertung",
      "corrected_verdict" in main_src
      and "fusion_discussion" in main_src)
import subprocess  # noqa: E402
res = subprocess.run(["node", "--check", str(REPO_ROOT / "django_project"
                       / "static" / "js" / "main.js")],
                     capture_output=True, text=True)
check("T9f node --check main.js", res.returncode == 0, res.stderr[:200])

# T10: Scope nur Fusionsprojekte - Nicht-Fusionsprojekt weiterhin 422
r = client.get(f'/api/projects/{pa.id}/fusion/calibration/')
check("T10a non-fusion project rejected (Scope-Fusion-only)",
      r.status_code == 422)

# Regression: OP63/OP64/OP66-Felder weiterhin vorhanden
check("T11a OP66-Felder intakt (pvr_chart, discussion_summary)",
      'pvr_chart' in str(body) and body.get('discussion_summary'))
check("T11b OP63-Kern intakt (calibrations, significance)",
      'calibrations' in body and 'significance' in body)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
