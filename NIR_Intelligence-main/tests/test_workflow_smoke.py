#!/usr/bin/env python3
"""OP89: Gesamtworkflow-Smoke (interagierende Teile, ein Durchlauf).

Nutzer-Anforderung (2026-10-22): Der Tester Agent soll jeden Code-Change
vollstaendig testen — Funktionen, GESAMTER Workflow und interagierende
Teile. Diese Matrix ist der Workflow-Teil des Change-Impact-Gates und
laeuft bei jedem Change (siehe scripts/run_change_tests.py).

Durchlauf (Django-Testclient, loopback, keine externen Dienste noetig):
  Projekt anlegen -> Datei-Upload -> Ingest/Aufbereitung -> Release ->
  Crew-Status (Analyse) -> Abschlussbericht -> Chatbot -> Cleanup.

Ehrlichkeitsregel (OP14-Vertrag): Fehlende externe Dienste (Ollama, Qdrant)
sind DEGRADED, nie Fake-Erfolg. Der Chatbot darf ohne Ollama ehrlich 503 +
degraded=true melden — das ist der bestandene Vertrag, nicht der Fehler.
Umgekehrt darf ein Crew-Fehler offline als error gemeldet werden; der
Test akzeptiert nur ehrliche Zustände (completed mit Bericht ODER error
mit begruendeter Meldung), nie einen hängenden oder widerspruechlichen.

Offline, kein CrewAI-Paket noetig (Standalone-Crew), kein Netzwerk.
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "django_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")

PASS = 0
FAIL = 0
FAILED = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        FAILED.append(name)
        print(f"[FAIL] {name} {detail}")


PROJECT_ROOT = Path(__file__).resolve().parent.parent

import django  # noqa: E402

django.setup()

from django.test import Client  # noqa: E402
from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.core.management import call_command  # noqa: E402

if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")

# ---------------------------------------------------------------------------
# T0: Setup — eigene DB-Migration (Repo-Standard wie OP12), eigener User
# ---------------------------------------------------------------------------
User = get_user_model()
try:
    User.objects.filter(username="op89smoke").first()
except Exception:
    call_command("migrate", interactive=False, verbosity=0)
user = User.objects.filter(username="op89smoke").first()
if user is None:
    user = User(username="op89smoke", email="op89smoke@test.local")
user.set_password("op89smoke")
user.is_staff = True
user.save()

c = Client()
check("T0a login works", c.login(username="op89smoke", password="op89smoke"))

# ---------------------------------------------------------------------------
# T1: Datei-Upload (Station 2 — Ingest & Datengrundlage)
# ---------------------------------------------------------------------------
csv_bytes = (b"wavelength,intensity\n"
             + b"".join(
                 f"{wl},{0.10 + 0.01 * i:.2f}\n".encode()
                 for i, wl in enumerate(range(700, 1160, 10))
             ))
r = c.post("/api/files/upload/", {
    "files": SimpleUploadedFile("op89_smoke.csv", csv_bytes,
                                content_type="text/csv")
}, format="multipart")
body = r.json() if r.status_code == 200 else {}
check("T1a upload endpoint 200 + success",
      r.status_code == 200 and body.get("success") is True,
      f"status={r.status_code} body={str(body)[:200]}")
file_ids = body.get("uploaded_files", [])
check("T1b uploaded_files ids returned", len(file_ids) == 1,
      f"ids={file_ids}")

# ---------------------------------------------------------------------------
# T2: Projekt anlegen + Aufbereitung abwarten (Station 1 -> 2)
# ---------------------------------------------------------------------------
project_name = f"OP89 Smoke {int(time.time())}"
r = c.post("/api/projects/create/",
           data={"file_ids": file_ids, "name": project_name},
           content_type="application/json")
body = r.json() if r.status_code in (200, 201) else {}
check("T2a project create 200 + project_id",
      r.status_code in (200, 201) and body.get("success") is True
      and body.get("project_id"),
      f"status={r.status_code} body={str(body)[:200]}")
pid = body.get("project_id")

from core.models import AnalysisProject  # noqa: E402

prepared = False
if pid:
    deadline = time.time() + 60
    while time.time() < deadline:
        project = AnalysisProject.objects.get(id=pid)
        prep = project.preparation_report or {}
        if project.phase == "drafted" and prep.get("datasets"):
            prepared = True
            break
        time.sleep(1)
check("T2b preparation report built (drafted + datasets)", prepared)
check("T2c preparation honest: usable_dataset_count reported",
      prepared and isinstance(
          (AnalysisProject.objects.get(id=pid).preparation_report or {})
          .get("usable_dataset_count"), int))

r = c.get(f"/projects/{pid}/")
check("T2d project detail page renders", r.status_code == 200,
      f"status={r.status_code}")

# ---------------------------------------------------------------------------
# T3: Release -> Crew-Analyse (Station 5) — Status ehrlich pollen
# ---------------------------------------------------------------------------
crew_completed = False
crew_error = ""
if pid:
    r = c.post(f"/api/projects/{pid}/release/", data={},
               content_type="application/json")
    body = r.json() if r.status_code in (200, 202) else {}
    check("T3a release accepted",
          r.status_code in (200, 202) and body.get("success") is True,
          f"status={r.status_code} body={str(body)[:200]}")

    deadline = time.time() + 120
    while time.time() < deadline:
        r = c.get(f"/api/projects/{pid}/crew-status/")
        body = r.json() if r.status_code == 200 else {}
        if body.get("success") is True and (
                body.get("completed") or body.get("error")):
            crew_completed = bool(body.get("completed"))
            crew_error = body.get("error") or ""
            break
        time.sleep(2)
    check("T3b crew-status endpoint answers with honest terminal state",
          crew_completed or bool(crew_error),
          "weder completed noch error gemeldet (haengender Zustand?)")

    # Ehrlichkeit: completed ohne Bericht ist widerspruechlich
    r = c.get(f"/api/projects/{pid}/final-report/markdown/")
    if crew_completed:
        check("T3c completed crew -> markdown report served (200)",
              r.status_code == 200, f"status={r.status_code}")
    else:
        check("T3c degraded crew -> report 404 + error ehrlich gemeldet",
              r.status_code == 404 and bool(crew_error),
              f"status={r.status_code} error={crew_error[:80]}")

# ---------------------------------------------------------------------------
# T4: Chatbot (Station 5/6 — Ergebnisdiskussion, MO 10)
# ---------------------------------------------------------------------------
r = c.get("/api/chatbot/status/")
body = r.json() if r.status_code == 200 else {}
check("T4a chatbot status endpoint answers (ollama_available ehrlich)",
      r.status_code == 200 and "ollama_available" in body
      and isinstance(body.get("ollama_available"), bool),
      f"status={r.status_code} body={str(body)[:200]}")

r = c.post("/api/chatbot/message/",
           data={"question": "Wie ist die Datenqualitaet des Projekts?"},
           content_type="application/json")
if r.status_code == 200:
    body = r.json()
    check("T4b chatbot answered (LLM erreichbar)",
          body.get("degraded") is False and bool(body.get("answer")),
          f"body={str(body)[:200]}")
elif r.status_code == 503:
    body = r.json()
    check("T4b chatbot ehrlich degraded (kein Ollama, kein Fake)",
          body.get("degraded") is True and bool(body.get("error")),
          f"body={str(body)[:200]}")
else:
    check("T4b chatbot ehrlich degraded (kein Ollama, kein Fake)", False,
          f"unerwarteter status={r.status_code}")

# ---------------------------------------------------------------------------
# T5: Health + Cleanup (keine Dead Ends, keine Datenleichen)
# ---------------------------------------------------------------------------
r = c.get("/api/health/")
check("T5a health endpoint 200", r.status_code == 200,
      f"status={r.status_code}")

if pid:
    r = c.post(f"/api/projects/{pid}/delete/", data={},
               content_type="application/json")
    check("T5b cleanup: project deleted",
          r.status_code == 200 and r.json().get("success") is True,
          f"status={r.status_code}")
    r = c.get(f"/projects/{pid}/")
    check("T5c deleted project detail 404 (kein Dead End)",
          r.status_code == 404, f"status={r.status_code}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f"OP89 workflow smoke: {PASS} passed, {FAIL} failed")
if FAILED:
    print("FAILED checks:", FAILED)
sys.exit(1 if FAIL else 0)
