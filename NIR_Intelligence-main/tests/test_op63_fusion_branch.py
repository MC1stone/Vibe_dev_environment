#!/usr/bin/env python3
# OP63 test matrix: fusion analysis branch (comparable spectra from other
# projects). Offline-safe: no network access required.
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
SERVICES = REPO_ROOT / "services"
TEMPLATES = REPO_ROOT / "django_project" / "templates"
STATIC_JS = REPO_ROOT / "django_project" / "static" / "js"

# ---------------------------------------------------------------------------
# T1: services/project_fusion.py existiert und ist kompilierbar
# ---------------------------------------------------------------------------
fusion_path = SERVICES / "project_fusion.py"
check("T1a services/project_fusion.py exists", fusion_path.exists())
import py_compile  # noqa: E402
try:
    py_compile.compile(str(fusion_path), doraise=True)
    check("T1b project_fusion compiles", True)
except Exception as exc:
    check("T1b project_fusion compiles", False, str(exc))

from services.project_fusion import (  # noqa: E402
    metadata_diff, _meta_get, COMPARISON_FIELDS,
)

# ---------------------------------------------------------------------------
# T2: metadata_diff - felderweiser Abgleich (nur Information, keine Blockade)
# ---------------------------------------------------------------------------
meta_a = {'operator_name': 'Alice', 'sensor_model': 'ESP32-S3',
          'tomato_variety': 'Roma'}
meta_b = {'operator_name': 'Bob', 'sensor_model': 'ESP32-S3',
          'tomato_variety': 'San Marzano'}
diff = metadata_diff(meta_a, meta_b)
check("T2a diff returns fields list", len(diff['fields']) == len(COMPARISON_FIELDS))
check("T2b differences counted", diff['differences'] == 2,
      f"got {diff['differences']}")
by_key = {f['key']: f for f in diff['fields']}
check("T2c equal field detected", by_key['sensor_model']['equal'] is True)
check("T2d differing field detected", by_key['operator_name']['equal'] is False)
check("T2e missing field flagged", by_key['measurement_date']['missing'] is True)
check("T2f labels present", all(f.get('label') for f in diff['fields']))

# case-insensitive Lookup
check("T2g case-insensitive metadata lookup",
      _meta_get({'Operator-Name': 'Alice'}, 'operator_name') == 'Alice')

# ---------------------------------------------------------------------------
# T3: API-Endpoints registriert (URL wiring)
# ---------------------------------------------------------------------------
from django.urls import reverse  # noqa: E402
try:
    url = reverse('project-fusion-preview')
    check("T3a fusion preview route registered",
          url.endswith('/fusion/preview/'), url)
except Exception as exc:
    check("T3a fusion preview route registered", False, str(exc))
try:
    url = reverse('project-fusion-execute')
    check("T3b fusion execute route registered",
          url.endswith('/fusion/execute/'), url)
except Exception as exc:
    check("T3b fusion execute route registered", False, str(exc))

urls_src = (REPO_ROOT / "django_project" / "api" / "project_urls.py").read_text(
    encoding="utf-8")
check("T3c preview view wired",
      "ProjectFusionPreviewView" in urls_src)
check("T3d execute view wired",
      "ProjectFusionExecuteView" in urls_src)

# ---------------------------------------------------------------------------
# T4: Stufe 1 - Offer-Hook in Quick-Check und Projekt-Crew
# ---------------------------------------------------------------------------
crewai_src = (REPO_ROOT / "django_project" / "api" / "crewai_views.py").read_text(
    encoding="utf-8")
check("T4a quick-check attaches fusion_offer",
      "fusion_offer" in crewai_src
      and "build_fusion_offer_for_spectrum" in crewai_src)

crew_src = (SERVICES / "project_crew.py").read_text(encoding="utf-8")
check("T4b project crew attaches fusion_offer",
      "fusion_offer" in crew_src and "build_fusion_offer" in crew_src)

# ---------------------------------------------------------------------------
# T5: Stufe 2 - preview/execute Verhalten (Runtime)
# ---------------------------------------------------------------------------
from django.contrib.auth import get_user_model  # noqa: E402
from django.test import Client  # noqa: E402
from core.models import AnalysisProject, GenericFile  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op63user").first()
if user is None:
    user = User.objects.create_user("op63user", password="pw",
                                    email="op63@example.com")

# Zwei Projekte des Nutzers (OP63-Szenario: gleicher Sensor, andere
# Operatoren/Tomaten)
pa = AnalysisProject.objects.create(user=user, name="Projekt A (Alice, Roma)")
pb = AnalysisProject.objects.create(user=user, name="Projekt B (Bob, San Marzano)")
pa.preparation_report = {"datasets": [
    {"file_id": "fa", "usable": True, "file_name": "a.csv",
     "metadata": {"operator_name": "Alice", "sensor_model": "ESP32-S3",
                  "tomato_variety": "Roma"}}]}
pa.save(update_fields=["preparation_report"])
pb.preparation_report = {"datasets": [
    {"file_id": "fb", "usable": True, "file_name": "b.csv",
     "metadata": {"operator_name": "Bob", "sensor_model": "ESP32-S3",
                  "tomato_variety": "San Marzano"}}]}
pb.save(update_fields=["preparation_report"])

from services.project_fusion import preview_fusion, execute_fusion  # noqa: E402

preview = preview_fusion(user, [str(pa.id), str(pb.id)])
check("T5a preview returns both projects", len(preview['projects']) == 2)
check("T5b preview counts usable datasets", preview['total_datasets'] == 2)
p_b = preview['projects'][1]
check("T5c preview contains metadata diff vs first",
      'metadata_diff_vs_first' in p_b)
diff_b = p_b['metadata_diff_vs_first']
check("T5d diff detects operator difference",
      any(f['key'] == 'operator_name' and not f['equal']
          for f in diff_b['fields']))
check("T5e diff detects same sensor",
      any(f['key'] == 'sensor_model' and f['equal']
          for f in diff_b['fields']))

client = Client()
client.force_login(user)
import json  # noqa: E402


def _post_json(url, payload):
    """POST wie axios im Browser (JSON-Body)."""
    return client.post(url, data=json.dumps(payload),
                      content_type='application/json')
r = _post_json('/api/projects/fusion/preview/',
               {'project_ids': [str(pa.id), str(pb.id)]})
check("T5f preview endpoint 200", r.status_code == 200, f"status {r.status_code}")
body = r.json()
check("T5g preview endpoint success", body.get('success') is True)

# execute: neues Projekt, Originale unangetastet (PO-Entscheidung)
# (ohne Dateien: execute lehnt ab - beide Projekte haben keine GenericFiles)
result = execute_fusion(user, [str(pa.id), str(pb.id)])
check("T5h execute without files rejected gracefully",
      result.get('success') is False and 'error' in result,
      str(result))

# mit Dateien: Fusion erstellt NEUES Projekt, Originale bleiben
fa = GenericFile.objects.create(user=user, name="a.csv", file_size=10)
fb = GenericFile.objects.create(user=user, name="b.csv", file_size=10)
pa.files.set([fa])
pb.files.set([fb])
result = execute_fusion(user, [str(pa.id), str(pb.id)])
check("T5i execute succeeds with files", result.get('success') is True,
      str(result))
fused_id = result.get('project_id')
check("T5j fused project exists",
      AnalysisProject.objects.filter(id=fused_id).exists())
fused = AnalysisProject.objects.get(id=fused_id)
check("T5k fused project references both source files",
      set(fused.files.values_list('id', flat=True)) == {fa.id, fb.id})
check("T5l source projects untouched",
      pa.files.count() == 1 and pb.files.count() == 1
      and AnalysisProject.objects.filter(id=pa.id).exists()
      and AnalysisProject.objects.filter(id=pb.id).exists())
check("T5m fusion provenance recorded",
      (fused.preparation_report or {}).get('fusion', {}).get('source_projects')
      is not None)

r = _post_json('/api/projects/fusion/execute/',
               {'project_ids': [str(pa.id), str(pb.id)], 'name': 'Fusion A+B'})
check("T5n execute endpoint creates project", r.status_code == 200
      and r.json().get('success') is True, f"status {r.status_code}")

# Auth-Guards
client.logout()
r = _post_json('/api/projects/fusion/preview/',
                {'project_ids': [str(pa.id), str(pb.id)]})
check("T5o anonymous preview rejected", r.status_code in (401, 403),
      f"status {r.status_code}")
r = _post_json('/api/projects/fusion/execute/',
                {'project_ids': [str(pa.id)]})
check("T5p single project execute rejected", r.status_code in (400, 401, 403),
      f"status {r.status_code}")

# ---------------------------------------------------------------------------
# T6: UI an beiden Stellen (Quick-Check spectra.js + Projekt-Report)
# ---------------------------------------------------------------------------
spectra_src = (STATIC_JS / "spectra.js").read_text(encoding="utf-8")
check("T6a quick-check renders fusion offer",
      "fusion_offer" in spectra_src and "nirBuildFusionOfferHtml" in spectra_src)

main_src = (STATIC_JS / "main.js").read_text(encoding="utf-8")
check("T6b shared fusion UI helpers in main.js",
      all(h in main_src for h in ("nirBuildFusionOfferHtml", "nirFusionPreview",
                                  "nirFusionExecute")))
check("T6c fusion UI user-decision buttons",
      "Nein, nicht" in main_src and "nirFusionExecute" in main_src)

report_src = (TEMPLATES / "project_report.html").read_text(encoding="utf-8")
check("T6d project report renders fusion panel",
      "fusionOfferBox" in report_src and "Analyse-Zweig" in report_src)
check("T6e project report keeps user decision",
      "nirFusionPreview" in report_src)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
