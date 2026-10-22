#!/usr/bin/env python3
# OP78 test matrix: Schrittweiser Fortschritts-Trace der Aufbereitung
# statt Black Box. Nutzer-Befund (2026-10-21): grosse Aufbereitung lief
# 30+ min ohne jede Rueckmeldung - der Nutzer konnte nicht sehen, welche
# Datei gerade dran ist und welcher Schritt laeuft.
# Stufe 1: _PrepTrace schreibt incrementell progress-Daten ins Projekt,
# der Status-Endpoint liefert sie, die Fortschrittskarte rendert sie.
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

# ---------------------------------------------------------------------------
# T1: Struktur - _PrepTrace + Hooks in build_preparation_report
# ---------------------------------------------------------------------------
ingest_path = REPO_ROOT / "services" / "project_ingest.py"
ingest_src = ingest_path.read_text("utf-8")

import py_compile  # noqa: E402
try:
    py_compile.compile(str(ingest_path), doraise=True)
    check("T1a project_ingest.py kompiliert", True)
except Exception as exc:
    check("T1a project_ingest.py kompiliert", False, str(exc))

check("T1b _PrepTrace-Klasse vorhanden", "class _PrepTrace:" in ingest_src)
check("T1c Trace schreibt vor jedem Schritt (progress-Dict)",
      "'progress'" in ingest_src and "current_step" in ingest_src
      and "current_file" in ingest_src)
check("T1d Datei-Loop verdrahtet (file_started/file_done)",
      "trace.file_started(" in ingest_src
      and "trace.file_done()" in ingest_src)
check("T1e Zeitschätzung pro Datei (avg_file_seconds)",
      "avg_file_seconds" in ingest_src
      and "file_durations" in ingest_src)
check("T1f Trace speichert nur Statusfelder (kleine writes)",
      "update_fields=[\"preparation_report\"," in ingest_src)

# ---------------------------------------------------------------------------
# T2: Status-Endpoint liefert den Trace
# ---------------------------------------------------------------------------
views_path = REPO_ROOT / "django_project" / "api" / "project_views.py"
views_src = views_path.read_text("utf-8")
try:
    py_compile.compile(str(views_path), doraise=True)
    check("T2a project_views.py kompiliert", True)
except Exception as exc:
    check("T2a project_views.py kompiliert", False, str(exc))

check("T2b ProjectPrepareStatusView liefert progress",
      "'progress': progress" in views_src)

# ---------------------------------------------------------------------------
# T3: Fahrplan-Karte im Template
# ---------------------------------------------------------------------------
tpl_path = (REPO_ROOT / "django_project" / "templates"
            / "project_report.html")
tpl_src = tpl_path.read_text("utf-8")

check("T3a Datei-Zähler (prepare-file-counter)", "prepare-file-counter" in tpl_src)
check("T3b aktueller Schritt + Datei (prepare-current)",
      "prepare-current" in tpl_src
      and "current_step" in tpl_src and "current_file" in tpl_src)
check("T3c Fortschrittsbalken (prepare-bar, Prozent aus done/total)",
      "prepare-bar" in tpl_src and "pr.total_files" in tpl_src)
check("T3d Zeitschätzung (prepare-eta, avg_file_seconds)",
      "prepare-eta" in tpl_src and "avg_file_seconds" in tpl_src)
check("T3e abgeschlossene Schritte als Liste (prepare-steps)",
      "prepare-steps" in tpl_src and "steps_done" in tpl_src)
check("T3f letzte Aktualisierung sichtbar (last_update)",
      "last_update" in tpl_src)

# ---------------------------------------------------------------------------
# T4: Runtime - Trace waechst incrementell, Endpoint liefert ihn
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from core.models import AnalysisProject, GenericFile  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from services.project_ingest import _PrepTrace  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op78trace").first()
if user is None:
    user = User.objects.create_user("op78trace", password="pw",
                                    email="op78@example.com")

csv_a = b"wl,intensity,brix\n900,0.5,4.0\n910,0.6,4.1\n920,0.7,4.2\n"
csv_b = b"wl,intensity,brix\n900,0.4,5.0\n910,0.5,5.1\n920,0.6,5.2\n"
p = AnalysisProject.objects.create(name="OP78-Trace", phase="drafted",
                                   user=user)
for name, content in (("a.csv", csv_a), ("b.csv", csv_b)):
    gf = GenericFile.objects.create(
        file=SimpleUploadedFile(name, content, content_type="text/csv"),
        file_size=len(content), user=user)
    p.files.add(gf)
p.preparation_report = {"user_options": {}}
p.save()

trace = _PrepTrace(p, total_files=2)
trace.step("Analyse-Wünsche geprüft")
check("T4a step() schreibt progress",
      bool((p.preparation_report or {}).get("progress")))
trace.file_started("a.csv")
prog = (p.preparation_report or {}).get("progress") or {}
check("T4b file_started setzt current_file",
      prog.get("current_file") == "a.csv")
trace.file_done()
trace.file_started("b.csv")
prog = (p.preparation_report or {}).get("progress") or {}
check("T4c Zähler inkrementell (done_files=1)",
      prog.get("done_files") == 1)
check("T4d steps_done waechst mit",
      len(prog.get("steps_done") or []) >= 1)
trace.file_done()
trace.step("Aufbereitung abgeschlossen")
prog = (p.preparation_report or {}).get("progress") or {}
check("T4e avg_file_seconds nach 2 Dateien",
      isinstance(prog.get("avg_file_seconds"), (int, float)))
check("T4f last_update gesetzt (HH:MM:SS-Format)",
      bool(prog.get("last_update")) and ":" in prog["last_update"])

client = Client(HTTP_HOST="testserver")
client.force_login(user)
from django.urls import reverse  # noqa: E402
status_url = reverse("project-prepare-status", args=[p.id])
r = client.get(status_url)
check("T4g Status-Endpoint 200", r.status_code == 200,
      f"status {r.status_code}")
data = r.json()
check("T4h Endpoint liefert progress-Felder",
      bool(data.get("progress"))
      and data["progress"].get("total_files") == 2
      and data["progress"].get("current_step"))

# T5: E2E - kompletter build_preparation_report-Trace (KI deterministisch,
# da in der Testumgebung kein Ollama laeuft)
p2 = AnalysisProject.objects.create(name="OP78-E2E", phase="drafted",
                                    user=user)
for name, content in (("a.csv", csv_a), ("b.csv", csv_b)):
    gf = GenericFile.objects.create(
        file=SimpleUploadedFile(name, content, content_type="text/csv"),
        file_size=len(content), user=user)
    p2.files.add(gf)
p2.preparation_report = {"user_options": {
    "analysis_wishes": "5 Reifeklassen bilden",
    "parsed_wishes": [{"type": "classes", "n": 5, "name": "test"}]}}
p2.save()

from services.project_ingest import build_preparation_report  # noqa: E402
report = build_preparation_report(p2)
rep2 = p2.preparation_report or {}
check("T5a E2E: Bericht gebaut mit Datensätzen",
      len(report.get("datasets") or []) >= 1)
check("T5b E2E: Trace hat jede Datei gezählt (done=total)",
      (rep2.get("progress") or {}).get("done_files")
      == (rep2.get("progress") or {}).get("total_files"))
check("T5c E2E: letzter Schritt 'Aufbereitung abgeschlossen'",
      "Aufbereitung abgeschlossen" in
      (rep2.get("progress") or {}).get("steps_done", []))
check("T5d E2E: Wünsche im Report erhalten (user_options)",
      (rep2.get("user_options") or {}).get("analysis_wishes")
      == "5 Reifeklassen bilden")

# T6: Fahrplan-Karte rendert (drafted + keine datasets)
p3 = AnalysisProject.objects.create(name="OP78-Page", phase="drafted",
                                    user=user)
gf = GenericFile.objects.create(
    file=SimpleUploadedFile("a.csv", csv_a, content_type="text/csv"),
    file_size=len(csv_a), user=user)
p3.files.add(gf)
p3.save()
r = client.get(f"/projects/{p3.id}/")
html = r.content.decode()
check("T6a Projektseite 200", r.status_code == 200)
check("T6b preparingCard gerendert", "preparingCard" in html)
check("T6c Fortschrittsbalken + Zähler + ETA + Schritte im HTML",
      all(k in html for k in ("prepare-bar", "prepare-file-counter",
                              "prepare-eta", "prepare-steps")))

# ---------------------------------------------------------------------------
# T7: OP78-Fix - Reingest asynchron (die Fahrplan-Karte muss auch beim
# 'Aufbereitung erneut ausfuehren'-Button erscheinen, nicht nur beim
# Projekt-Anlegen/Wunsch-Save)
# ---------------------------------------------------------------------------
views_src2 = (REPO_ROOT / "django_project" / "api" / "project_views.py").read_text("utf-8")
check("T7a Reingest asynchron (Thread + preparing: True)",
      "Background reingest failed" in views_src2
      and "'preparing': True" in views_src2)
# OP82: das Leeren passiert jetzt ueber die preserved-Variable, die
# user_options UND (bei Fusionsprojekten) die fusion-Sektion erhaelt -
# datasets werden in beiden Faellen weggeleert -> Karte erscheint.
check("T7b Reingest leert den alten Report (Karte wird sichtbar)",
      "preserved = {'user_options': user_options}" in views_src2)
check("T7c Reingest erhaelt user_options (Wuensche ueberleben)",
      "user_options = report.get('user_options') or {}" in views_src2)
tpl2 = tpl_src
check("T7d Buttons kommunizieren Hintergrund-Start + Reload",
      tpl2.count("wird im Hintergrund neu ausgeführt") >= 2)
check("T7e Buttons erwarten keine syncen Counts mehr",
      "d.usable_dataset_count + ' verwertbare" not in tpl2)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
