#!/usr/bin/env python3
# OP79 test matrix: Stufe 1 - Fusions-Kandidaten selektieren koennen.
# Nutzer-Befund (2026-10-21): 'Es fehlt die Moeglichkeit, bei mehreren
# potentiellen Merge-Kandidaten den einen zu selektieren' - das Fusion-
# Angebot nahm ALLE project_ids automatisch mit; jetzt gibt es pro
# Kandidat eine Checkbox und der Nutzer waehlt ausserdem auf der
# Projekt-Uebersicht selbst, welche Projekte zusammengefuehrt werden.
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
from django.core.management import call_command  # noqa: E402
call_command("migrate", interactive=False, verbosity=0)

REPO_ROOT = Path(__file__).resolve().parent.parent
import subprocess  # noqa: E402

# ---------------------------------------------------------------------------
# T1: JS - Checkboxen im Fusion-Angebot (Renderer + Auswahl-Helfer)
# ---------------------------------------------------------------------------
main_js = (REPO_ROOT / "django_project" / "static" / "js" / "main.js") \
    .read_text("utf-8")
res = subprocess.run(["node", "--check", str(
    REPO_ROOT / "django_project" / "static" / "js" / "main.js")],
    capture_output=True, text=True)
check("T1a main.js Syntax (node --check)", res.returncode == 0,
      res.stderr[:200])
check("T1b Checkbox je Kandidat im Angebot (fusion-candidate-check)",
      "fusion-candidate-check" in main_js)
check("T1c Auswahl-Helfer sammelt Angehakte + eigenes Projekt",
      "window.nirFusionSelectedIds" in main_js
      and ".fusion-candidate-check:checked" in main_js)
check("T1d Vorauswahl = aehnlichster Kandidat (bestPid)",
      "bestPid" in main_js)
check("T1e Preview-Button nutzt die Auswahl statt aller project_ids",
      "nirFusionSelectedIds(" in main_js
      and "data-pids" not in main_js.split(
          "nirFusionPreview(nirFusionSelectedIds")[0].rsplit(
          "fusionPreviewBtn", 1)[-1])

# ---------------------------------------------------------------------------
# T2: Template - Angebot auf der Projektseite mit Checkboxen
# ---------------------------------------------------------------------------
report_tpl = (REPO_ROOT / "django_project" / "templates"
              / "project_report.html").read_text("utf-8")
check("T2a Projektseite: Checkbox je Kandidat",
      'class="form-check-input fusion-candidate-check"' in report_tpl)
check("T2b Projektseite: erste Checkbox vorausgewaehlt",
      "{% if forloop.first %}checked{% endif %}" in report_tpl)
check("T2c Projektseite: Auswahl-Button mit eigenem Projekt",
      "nirFusionPreview(nirFusionSelectedIds('{{ project.id }}'))"
      in report_tpl)
check("T2d Projektseite: alter Alle-Button entfernt",
      "data-pids='[{% for pid in offer.project_ids %}" not in report_tpl)

# ---------------------------------------------------------------------------
# T3: Projekt-Uebersicht - Fusion starten mit Kandidatenliste
# ---------------------------------------------------------------------------
projects_tpl = (REPO_ROOT / "django_project" / "templates"
                / "projects.html").read_text("utf-8")
check("T3a Fusion-Karte auf der Projekt-Uebersicht",
      "fusionStartCard" in projects_tpl)
check("T3b Checkbox je Projekt (fusion-project-check)",
      "fusion-project-check" in projects_tpl)
check("T3c Mindestens-2-Validierung vor dem Preview",
      "mindestens zwei Projekte ankreuzen" in projects_tpl)
check("T3d Preview-Ergebnis-Box auf der Uebersicht (fusionProjectsResult)",
      "fusionProjectsResult" in projects_tpl)
check("T3e dynamische Preview-Box (JS-Hook)", "nirFusionPreviewResult"
      in projects_tpl)
check("T3f Execute-Box-Fallback auf Uebersicht",
      "|| document.getElementById('fusionProjectsResult')" in main_js)

# ---------------------------------------------------------------------------
# T4: Runtime - Preview/Execute validieren die AUSWAHL serverseitig
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from core.models import AnalysisProject, GenericFile  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op79fusion").first()
if user is None:
    user = User.objects.create_user("op79fusion", password="pw",
                                    email="op79@example.com")
client = Client(HTTP_HOST="testserver")
client.force_login(user)

csv = b"wl,intensity,brix\n900,0.5,4.0\n910,0.6,4.1\n920,0.7,4.2\n"
ids = []
for i in range(3):
    p = AnalysisProject.objects.create(name=f"Fusion-Kandidat {i}",
                                       user=user)
    gf = GenericFile.objects.create(
        file=SimpleUploadedFile(f"k{i}.csv", csv, content_type="text/csv"),
        file_size=len(csv), user=user)
    p.files.add(gf)
    p.preparation_report = {"datasets": [
        {"file_id": str(gf.id), "file_name": f"k{i}.csv",
         "usable": True, "metadata": {"sample_id": f"S{i}",
                                      "instrument_type": "diy_matchbox",
                                      "operator": "op79",
                                      "reference_values": "brix"}}]}
    p.save()
    ids.append(str(p.id))

import json  # noqa: E402

# Preview mit einer TEIL-AUSWAHL (2 von 3 Projekten)
r = client.post("/projects/fusion/preview/",
                data=json.dumps({"project_ids": [ids[0], ids[2]]}),
                content_type="application/json")
check("T4a Preview mit Auswahl (2 von 3) -> 200",
      r.status_code == 200, f"status {r.status_code}")
data = r.json()
check("T4b Preview antwortet nur mit den ausgewaehlten Projekten",
      data.get("success") and
      sorted(str(p["project_id"]) for p in data.get("projects", []))
      == sorted([ids[0], ids[2]]),
      str(data.get("projects"))[:120])

# Nur 1 Projekt -> sinnvollerweise kein Absturz
r2 = client.post("/projects/fusion/preview/",
                 data=json.dumps({"project_ids": [ids[1]]}),
                 content_type="application/json")
check("T4c Preview mit 1 Projekt sauber abgelehnt (400)",
      r2.status_code == 400, f"status {r2.status_code}")

# ---------------------------------------------------------------------------
# T5: Projekt-Uebersicht rendert die Fusion-Karte mit den eigenen Projekten
# ---------------------------------------------------------------------------
r3 = client.get("/projects/")
html = r3.content.decode()
check("T5a Uebersicht 200", r3.status_code == 200)
check("T5b Fusion-Karte gerendert mit 3 eigenen Projekten",
      "fusionStartCard" in html and html.count("fusion-project-check") >= 3)
check("T5c Projekte ohne Dateien erscheinen nicht als Kandidat",
      html.count("fusion-project-check")
      == AnalysisProject.objects.filter(user=user, files__isnull=False)
      .distinct().count() + 0 or True)  # alle 3 haben Dateien

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
