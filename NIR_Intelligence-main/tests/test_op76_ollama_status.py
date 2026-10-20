#!/usr/bin/env python3
# OP76 test matrix: Ollama-Statuszeile + Aktivierungs-Button.
# Nutzer-Befund (2026-10-20): 'Ollama funktioniert wieder nicht - das ist
# ein entscheidender Faktor.' Anforderungen: Test, der ZUALLERERST die
# Verfuegbarkeit klaert + Button zum Aktivieren wenn offline.
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
# T1: Service-Layer
# ---------------------------------------------------------------------------
from services.ollama_status import ollama_status  # noqa: E402

st = ollama_status()
check("T1a ollama_status liefert alle Felder",
      all(k in st for k in ('state', 'base_url', 'model',
                            'server_reachable', 'model_available',
                            'in_docker_stack')), str(st))
check("T1b Zustandsmenge korrekt",
      st['state'] in ('ok', 'model_missing', 'offline'), st['state'])
# Sandbox: kein Ollama -> ehrlich offline
check("T1c ohne Ollama ehrlich 'offline'",
      st['state'] == 'offline', str(st))

src = (REPO_ROOT / "services" / "ollama_status.py").read_text("utf-8")
check("T1d Start-Logik: docker compose restart ollama",
      "docker compose restart ollama" in src.replace("'", '"')
      or "'restart', 'ollama'" in src or '"restart", "ollama"' in src)
check("T1e Modell-Sicherung beim Start (nur wenn fehlt)",
      "model_available" in src and "pull" in src)
check("T1f ehrliche Anleitung wenn nicht im Docker-Stack",
      "not_in_docker_stack" in src and "systemctl start ollama" in src)

# ---------------------------------------------------------------------------
# T2: Endpoints (Runtime)
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op76user").first()
if user is None:
    user = User.objects.create_user("op76user", password="pw",
                                    email="u76@example.com")
staff = User.objects.filter(username="op76staff").first()
if staff is None:
    staff = User.objects.create_user("op76staff", password="pw",
                                     email="s76@example.com", is_staff=True)

client = Client(HTTP_HOST='testserver')
client.force_login(user)
r = client.get('/api/ollama/status/')
check("T2a GET /api/ollama/status/ 200 (angemeldet)",
      r.status_code == 200, f"status {r.status_code}")
body = r.json()
check("T2b Status-Body mit state/model/base_url",
      all(k in body for k in ('state', 'model', 'base_url')))

r2 = client.post('/api/ollama/start/')
check("T2c POST start: non-staff -> 403 staff_required",
      r2.status_code == 403 and r2.json().get('reason') == 'staff_required',
      f"{r2.status_code} {str(r2.json())[:80]}")

client.force_login(staff)
r3 = client.post('/api/ollama/start/')
body3 = r3.json()
check("T2d POST start (staff): ehrliches Protokoll, kein Fake-Erfolg",
      'protocol' in body3 and body3.get('success') is False
      and body3.get('reason') == 'not_in_docker_stack',
      str(body3)[:150])
check("T2e Protokoll enthaelt Start-Anleitung (Host-Pfad)",
      any('systemctl start ollama' in str(p)
          for p in body3.get('protocol', [])))

anon = Client(HTTP_HOST='testserver')
r4 = anon.get('/api/ollama/status/')
check("T2f anonym -> 401/403", r4.status_code in (401, 403),
      str(r4.status_code))

# ---------------------------------------------------------------------------
# T3: UI - Statuszeile auf jeder Seite (base.html), Start-Button Staff-only
# ---------------------------------------------------------------------------
tpl = (REPO_ROOT / "django_project" / "templates"
       / "base.html").read_text("utf-8")
check("T3a Statuszeile im Base-Template (jede Seite)",
      'ollamaStatusBar' in tpl)
check("T3b drei Zustaende gerendert (ok/model_missing/offline)",
      all(k in tpl for k in ("model_missing", "offline", "'ok'")))
check("T3c Start-Button vorhanden (ollamaStartBtn)",
      'ollamaStartBtn' in tpl and 'Ollama starten' in tpl)
check("T3d Staff-Gate im UI (data-user-staff)",
      'data-user-staff' in tpl)
check("T3e Start-Protokoll sichtbar (ollamaStartProtocol)",
      'ollamaStartProtocol' in tpl)
check("T3f Auto-Refresh (60s Polling)", 'setInterval(refresh, 60000)' in tpl)

# ---------------------------------------------------------------------------
# T4: Vorrang-Verkabelung - Statuscheck vor KI-abhaengigen Passen
# ---------------------------------------------------------------------------
ingest_src = (REPO_ROOT / "services" / "project_ingest.py").read_text("utf-8")
check("T4a Ingest nutzt weiterhin den OP50-Probe (ollama_health)",
      "ollama_health" in ingest_src or "ollama_reachable" in ingest_src)
health_src = (REPO_ROOT / "services" / "ollama_health.py").read_text("utf-8")
check("T4b Probe bleibt robust (Wiederholungen + Cache)",
      "attempts" in health_src and "_cache" in health_src)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
