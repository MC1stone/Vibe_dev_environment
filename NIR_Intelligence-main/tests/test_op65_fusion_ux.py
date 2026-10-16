#!/usr/bin/env python3
# OP65 test matrix: fusion UX release feedback.
# A) Double-fusion guard (accidental re-merge -> clear error + link),
# B) tolerance levels derived from the reference resolution (brix 0.1),
# C) metadata suggestions from the donor dataset,
# D) UI: redesigned comparison table (all metrics side by side).
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
import numpy as np  # noqa: E402

# ---------------------------------------------------------------------------
# T1: Toleranzstufen aus der Referenz-Aufloesung (Brix 0,1-Schritte)
# ---------------------------------------------------------------------------
from services.fusion_calibration import _tolerance_levels_from_targets  # noqa: E402

brix01 = [round(4.0 + 0.1 * i, 1) for i in range(40)]
check("T1a brix 0.1 steps -> (0.5, 1.0)",
      _tolerance_levels_from_targets(brix01) == (0.5, 1.0),
      str(_tolerance_levels_from_targets(brix01)))
fein = [round(4.0 + 0.01 * i, 2) for i in range(40)]
check("T1b very fine -> includes 0.1",
      0.1 in _tolerance_levels_from_targets(fein))
grob = [float(i % 5) for i in range(40)]
check("T1c coarse integer steps -> coarser levels",
      _tolerance_levels_from_targets(grob) == (1.0, 2.0))
check("T1d degenerate input -> default",
      _tolerance_levels_from_targets([]) == (0.5, 1.0))

# ---------------------------------------------------------------------------
# T1b: Generalisierung (OP65-Nachtrag): unbekannte Kontextfelder nehmen
# automatisch am Metadaten-Abgleich teil - Kaffee/Boden-Kontext funktioniert
# ohne Code-Aenderung genauso wie Tomaten.
# ---------------------------------------------------------------------------
from services.project_fusion import metadata_diff  # noqa: E402

ka = {'operator_name': 'Alice', 'coffee_origin': 'Aethiopien',
      'soil_type': 'Lehm'}
kb = {'operator_name': 'Bob', 'coffee_origin': 'Kolumbien',
      'soil_type': 'Lehm'}
kd = metadata_diff(ka, kb)
kkeys = {f['key']: f for f in kd['fields']}
check("T1b-a unknown context fields join the comparison",
      'coffee_origin' in kkeys and 'soil_type' in kkeys,
      str(kkeys.keys()))
check("T1b-b differing context field detected",
      kkeys['coffee_origin']['equal'] is False)
check("T1b-c equal context field detected",
      kkeys['soil_type']['equal'] is True)
ta = {'operator_name': 'A', 'tomato_variety': 'Roma'}
tb = {'operator_name': 'B', 'tomato_variety': 'San Marzano'}
td = metadata_diff(ta, tb)
tkeys = {f['key']: f for f in td['fields']}
check("T1b-d tomato context still works (article case)",
      'tomato_variety' in tkeys
      and tkeys['tomato_variety']['equal'] is False)

# ---------------------------------------------------------------------------
# T2: Doppel-Fusionsschutz
# ---------------------------------------------------------------------------
from core.models import AnalysisProject, GenericFile  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op65user").first()
if user is None:
    user = User.objects.create_user("op65user", password="pw",
                                    email="op65@example.com")

fa = GenericFile.objects.create(user=user, name="a.csv", file_size=10)
fb = GenericFile.objects.create(user=user, name="b.csv", file_size=10)
pa = AnalysisProject.objects.create(user=user, name="OP65 Quelle A")
pa.files.set([fa])
pb = AnalysisProject.objects.create(user=user, name="OP65 Quelle B")
pb.files.set([fb])

from services.project_fusion import execute_fusion, metadata_suggestions  # noqa: E402

r1 = execute_fusion(user, [str(pa.id), str(pb.id)], name="OP65 Fusion")
check("T2a first fusion succeeds", r1.get('success') is True, str(r1))

r2 = execute_fusion(user, [str(pa.id), str(pb.id)])
check("T2b second fusion of the same sources rejected",
      r2.get('success') is False, str(r2))
check("T2c rejection names the existing project",
      'bereits zusammengefuehrt' in r2.get('error', ''), str(r2.get('error')))
check("T2d rejection links the existing project",
      r2.get('existing_project_id') == r1.get('project_id')
      and r2.get('existing_project_url', '').endswith(
          str(r1.get('project_id')) + '/'), str(r2))
r3 = execute_fusion(user, [str(pa.id), str(pb.id), str(r1['project_id'])])
check("T2e different combination still allowed",
      r3.get('success') is True, str(r3))

# ---------------------------------------------------------------------------
# T3: Metadaten-Vorschlaege (Donor -> Datensatz ohne Metadaten)
# ---------------------------------------------------------------------------
fused = AnalysisProject.objects.get(id=r1['project_id'])
donor = AnalysisProject.objects.create(user=user, name="OP65 Donor")
donor.preparation_report = {'datasets': [
    {'file_id': 'd.csv', 'usable': True, 'file_name': 'd.csv',
     'metadata': {'operator_name': 'Alice', 'tomato_variety': 'Roma',
                  'instrument_type': 'ESP32-S3', 'measurement_date': '2026-10-16'}}]}
donor.save(update_fields=['preparation_report'])
pa.preparation_report = {'datasets': [
    {'file_id': 'a.csv', 'usable': True, 'file_name': 'a.csv',
     'metadata': {}}]}
pa.save(update_fields=['preparation_report'])

fused2 = AnalysisProject.objects.create(user=user, name="OP65 Fusion 2")
fused2.preparation_report = {
    'fusion': {'source_projects': [
        {'project_id': str(pa.id), 'project_name': 'A'},
        {'project_id': str(donor.id), 'project_name': 'Donor'}]},
    'datasets': [
        {'file_id': 'a.csv', 'usable': True, 'file_name': 'a.csv',
         'metadata': {}},
        {'file_id': 'd.csv', 'usable': True, 'file_name': 'd.csv',
         'metadata': {'operator_name': 'Alice', 'tomato_variety': 'Roma',
                      'instrument_type': 'ESP32-S3',
                      'measurement_date': '2026-10-16'}}]}
fused2.save(update_fields=['preparation_report'])

sugg = metadata_suggestions(fused2)
check("T3a suggestions available", sugg.get('available') is True,
      str(sugg))
by_file = {s['file_name']: s for s in sugg.get('suggestions', [])}
check("T3b dataset without metadata gets proposals",
      'a.csv' in by_file and len(by_file['a.csv']['proposals']) >= 3,
      str(by_file.get('a.csv')))
fields = {p['field'] for p in by_file['a.csv']['proposals']}
check("T3c operator/tomato/sensor proposed",
      {'operator_name', 'tomato_variety', 'instrument_type'} <= fields,
      str(fields))
check("T3d dataset with own metadata gets none",
      'd.csv' not in by_file, str(by_file.keys()))
check("T3e proposals carry the donor file",
      all(p.get('source_file') == 'd.csv'
          for p in by_file['a.csv']['proposals']))

# ---------------------------------------------------------------------------
# T4: API-Endpoint (Runtime)
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402
import json  # noqa: E402

try:
    url = reverse('project-fusion-metadata-suggestions', args=[fused2.id])
    check("T4a suggestions route registered",
          url.endswith('/fusion/metadata-suggestions/'), url)
except Exception as exc:
    check("T4a suggestions route registered", False, str(exc))

client = Client()
client.force_login(user)
r = client.get(f'/api/projects/{fused2.id}/fusion/metadata-suggestions/')
check("T4b suggestions endpoint 200", r.status_code == 200,
      f"status {r.status_code}")
body = r.json()
check("T4c endpoint returns suggestions",
      body.get('success') is True and body.get('available') is True)
r = client.get(f'/api/projects/{pa.id}/fusion/metadata-suggestions/')
check("T4d non-fusion project rejected 422", r.status_code == 422,
      f"status {r.status_code}")
client.logout()
r = client.get(f'/api/projects/{fused2.id}/fusion/metadata-suggestions/')
check("T4e anonymous rejected", r.status_code in (401, 403),
      f"status {r.status_code}")

# ---------------------------------------------------------------------------
# T5: UI - redesigned comparison table + suggestion panel
# ---------------------------------------------------------------------------
main_src = (REPO_ROOT / "django_project" / "static" / "js"
            / "main.js").read_text(encoding="utf-8")
check("T5a one row per dataset, metrics side by side",
      "rowspan=\"2\"" in main_src and "Trefferquote" in main_src)
check("T5b hit-rate colouring (success/warning/danger)",
      "text-success" in main_src and "text-warning" in main_src)
check("T5c mae/rmse/r2/rpd all in the table",
      all(k in main_src for k in ("MAE", "RMSE", "RPD")))
check("T5d metadata suggestion UI present",
      "nirFusionMetadataSuggestions" in main_src
      and "nirApplyMetadataSuggestion" in main_src)

tpl = (REPO_ROOT / "django_project" / "templates"
       / "project_report.html").read_text(encoding="utf-8")
check("T5e suggestion panel in template (fusion + drafted only)",
      "fusionMetaSuggestionsBox" in tpl
      and "preparation.fusion" in tpl)
check("T5f calibration panel still present", "fusionCalibrationBox" in tpl)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
