# OP57 test matrix: asynchronous crew analysis (release -> background -> polling)
# Problem (Feldtest): "Die Analyse der neuen Daten fuer das Projekt laeuft
# SEEEEHR lange" - ProjectReleaseView ran run_project_crew SYNCHRON im
# Request: 15 Agenten mit je bis zu 120s LLM-Timeout pro Datensatz hingen
# den Request minutenlang ohne jedes Feedback (identisch zum OP55-Problem
# der Aufbereitung).
# Fix: Release setzt nur die Phase, persistiert die Spektren und startet
# den Crew-Lauf in einem Background-Thread; die Projektseite zeigt ein
# Fortschritts-Banner (verstrichene Zeit + Agenten-Berichte bisher) und
# pollt den neuen Status-Endpoint bis die Phase auf completed wechselt
# oder ein Fehler aufgezeichnet wurde.
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "django_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")

PASS = 0
FAIL = 0


def check(name, cond, info=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {info}" if info else f"[FAIL] {name}")


import django

django.setup()

from django.test import Client
from django.test.runner import DiscoverRunner
from django.test.utils import setup_test_environment

setup_test_environment()

from django.conf import settings as dj_settings

if "testserver" not in dj_settings.ALLOWED_HOSTS:
    dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]

PROJECT = Path(__file__).resolve().parent.parent

# T1: release view no longer runs the crew synchronously
views_src = (PROJECT / "django_project" / "api" / "project_views.py").read_text(
    encoding="utf-8")
check("T1a release view starts a background thread",
      "Thread(target=_run_crew" in views_src)
check("T1b release view no longer runs the crew in-request",
      "crew_results = run_project_crew(project)" not in views_src)
check("T1c release response carries analyzing flag",
      "'analyzing': True" in views_src)
check("T1d background crew failure resets phase and records crew_error",
      "crew_error" in views_src and "proj.phase = 'drafted'" in views_src)

# T2: crew status route registered
from django.urls import reverse

try:
    url = reverse("project-crew-status",
                  kwargs={"project_id": "00000000-0000-0000-0000-000000000000"})
    check("T2a crew status route registered",
          url.endswith("/00000000-0000-0000-0000-000000000000/crew-status/"),
          url)
except Exception as exc:
    check("T2a crew status route registered", False, str(exc))

# T3: template banner + polling
template_src = (PROJECT / "django_project" / "templates"
                / "project_report.html").read_text(encoding="utf-8")
check("T3a analyzing banner exists",
      'id="analyzingCard"' in template_src)
check("T3b banner shows for released projects without results",
      "project.phase == 'released' and not crew_analysis.overall_quality_score"
      in template_src)
check("T3c banner shows elapsed time",
      'id="analyze-elapsed"' in template_src)
check("T3d banner shows agent-section count",
      'id="analyze-count"' in template_src)
analyze_js = template_src.split("getElementById('analyzingCard')")[-1][:4000]
check("T3e polling reloads on completed",
      "data.completed" in analyze_js and "window.location.reload()" in analyze_js)

# T4: intermediate progress persisted per dataset
crew_src = (PROJECT / "services" / "project_crew.py").read_text(encoding="utf-8")
check("T4a intermediate crew_results persisted per dataset",
      "intermediate progress is persisted per dataset" in crew_src
      and "project.save(update_fields=['crew_results'" in crew_src)

# T5: live behaviour with the test client
runner = DiscoverRunner(verbosity=0)
old_config = runner.setup_databases()
try:
    from core.models import User, AnalysisProject, GenericFile
    from django.core.files.uploadedfile import SimpleUploadedFile

    user, _ = User.objects.get_or_create(username="op57user")
    if not user.check_password("pw12345!"):
        user.set_password("pw12345!")
        user.save()
    f = GenericFile.objects.create(
        user=user, name="op57.txt", original_filename="op57.txt",
        file=SimpleUploadedFile("op57.txt", b"x\ty\n1\t2\n"),
        file_size=len(b"x\ty\n1\t2\n"))
    released = AnalysisProject.objects.create(
        user=user, name="op57-running", phase="released",
        preparation_report={"datasets": [
            {"file_name": "op57.txt", "file_id": str(f.id), "usable": True}],
            "usable_dataset_count": 1})
    done = AnalysisProject.objects.create(
        user=user, name="op57-done", phase="completed",
        crew_results={"per_agent_reports": [{"agent": "x"}, {"agent": "y"}]},
        preparation_report={"datasets": [
            {"file_name": "op57.txt", "file_id": str(f.id), "usable": True}],
            "usable_dataset_count": 1})

    client = Client()
    client.login(username="op57user", password="pw12345!")

    resp = client.get(f"/api/projects/{released.id}/crew-status/")
    body = resp.json()
    check("T5a crew status answers 200 for running project",
          resp.status_code == 200 and body.get("success") is True
          and body.get("completed") is False, str(body)[:150])
    check("T5b running project reports zero agent sections",
          body.get("agent_sections") == 0, str(body)[:150])

    resp = client.get(f"/api/projects/{done.id}/crew-status/")
    body = resp.json()
    check("T5c completed project reports completed + section count",
          body.get("completed") is True and body.get("agent_sections") == 2,
          str(body)[:150])

    anon = Client()
    resp = anon.get(f"/api/projects/{released.id}/crew-status/")
    check("T5d anonymous crew status rejected",
          resp.status_code in (401, 403, 301, 302), f"got {resp.status_code}")

    # T5e: release of a prepared project answers immediately (thread path)
    import json as _json
    resp = client.post(f"/projects/{released.id}/release/",
                       data=_json.dumps({}),
                       content_type="application/json")
    body = resp.json()
    check("T5e release responds immediately with analyzing flag",
          resp.status_code == 200 and body.get("success")
          and body.get("analyzing") is True, str(body)[:150])
finally:
    runner.teardown_databases(old_config)

print(f"\nOP57: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
