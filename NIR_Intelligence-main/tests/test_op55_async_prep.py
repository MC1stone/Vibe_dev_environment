# OP55 test matrix: asynchronous project preparation
# Problem: ProjectCreateView ran build_preparation_report synchronously -
# with KI metadata extraction (up to 120s per file x2 attempts) the request
# hung for minutes with no feedback whether it would ever succeed.
# Fix: project is created immediately, preparation runs in a background
# thread, the detail page shows a progress banner and polls a status
# endpoint until the report is ready.
import os
import sys
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

# T1: create view runs preparation in a background thread
from api.project_views import ProjectCreateView, ProjectPrepareStatusView
src = (Path(__file__).resolve().parent.parent
       / "django_project" / "api" / "project_views.py").read_text(encoding="utf-8")
check("T1a create view no longer calls build_preparation_report synchronously",
      "        build_preparation_report(project)\n        return Response" not in src)
check("T1b create view starts a background thread",
      "Thread(target=_prepare" in src)
check("T1c background failure is recorded in preparation_report",
      "preparation_error" in src)
check("T1d create response carries preparing flag",
      "'preparing': True" in src)

# T2: status route registered
from django.urls import reverse, resolve
try:
    url = reverse("project-prepare-status",
                  kwargs={"project_id": "00000000-0000-0000-0000-000000000000"})
    check("T2a status route registered",
          url.endswith("/create/00000000-0000-0000-0000-000000000000/status/"),
          url)
except Exception as exc:
    check("T2a status route registered", False, str(exc))

# T3: status view behaviour
from django.conf import settings as dj_settings
from django.test import Client
from django.test.runner import DiscoverRunner
from django.test.utils import setup_test_environment

setup_test_environment()
if "testserver" not in dj_settings.ALLOWED_HOSTS:
    dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]

runner = DiscoverRunner(verbosity=0)
old_config = runner.setup_databases()
try:
    from core.models import User, GenericFile, AnalysisProject
    from django.core.files.uploadedfile import SimpleUploadedFile
    user, _ = User.objects.get_or_create(username="op55user")
    if not user.check_password("pw12345!"):
        user.set_password("pw12345!")
        user.save()

    f = GenericFile.objects.create(
        user=user, name="op55.txt",
        original_filename="op55.txt",
        file=SimpleUploadedFile("op55.txt", b"x\ty\n1\t2\n"),
        file_size=len(b"x\ty\n1\t2\n"))
    empty_project = AnalysisProject.objects.create(user=user, name="prep-empty")
    ready_project = AnalysisProject.objects.create(
        user=user, name="prep-ready",
        preparation_report={"datasets": [{"file_name": "a.txt"}]})

    client = Client()
    client.login(username="op55user", password="pw12345!")

    resp = client.get(f"/api/projects/create/{empty_project.id}/status/")
    body = resp.json()
    check("T3a status endpoint answers for unprepared project",
          resp.status_code == 200 and body.get("ready") is False
          and body.get("success") is True, str(body)[:150])
    resp = client.get(f"/api/projects/create/{ready_project.id}/status/")
    body = resp.json()
    check("T3b status endpoint reports ready after preparation",
          body.get("ready") is True and body.get("dataset_count") == 1,
          str(body)[:150])

    anon = Client()
    resp = anon.get(f"/api/projects/create/{empty_project.id}/status/")
    check("T3c anonymous status request rejected",
          resp.status_code in (401, 403, 301, 302), f"got {resp.status_code}")

    # T4: create view returns immediately with preparing flag
    import time
    import json as _json
    resp = client.post("/api/projects/create/",
                       data=_json.dumps({"file_ids": [str(f.id)],
                                         "name": "op55-proj"}),
                       content_type="application/json")
    body = resp.json()
    check("T4a create responds immediately with preparing flag",
          resp.status_code == 200 and body.get("success")
          and body.get("preparing") is True, str(body)[:150])
    pid = body.get("project_id")
    check("T4b project exists right away", bool(pid))

    # wait for the background thread to finish (real ingest incl. LLM
    # fallback when Ollama is unavailable offline)
    deadline = time.time() + 60
    ready = False
    while time.time() < deadline:
        r = client.get(f"/api/projects/create/{pid}/status/").json()
        if r.get("ready") or r.get("error"):
            ready = r.get("ready")
            break
        time.sleep(1)
    check("T4c background preparation completes and status flips to ready",
          ready is True, "not ready after 60s")
finally:
    runner.teardown_databases(old_config)

# T5: templates
tpl_dir = (Path(__file__).resolve().parent.parent
           / "django_project" / "templates")
report = (tpl_dir / "project_report.html").read_text(encoding="utf-8")
check("T5a report shows preparing banner when no datasets yet",
      "preparingCard" in report and "Datenaufbereitung laeuft" in report)
check("T5b report polls the status endpoint",
      'url "project-prepare-status"' in report)
projects_tpl = (tpl_dir / "projects.html").read_text(encoding="utf-8")
check("T5c create form communicates background preparation",
      "Aufbereitung läuft dort sichtbar im Hintergrund" in projects_tpl)

print(f"\nOP55 async preparation matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
