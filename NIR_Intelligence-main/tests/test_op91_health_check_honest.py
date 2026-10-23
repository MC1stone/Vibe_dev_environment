# covers: api/views.py
# OP91 test matrix: Health-Check ehrlich — flower-URL-Bug + agents_loaded.
# Befund aus lokalem Systemtest (2026-10-23, nach Merge #231/#234/#237):
# GET /health/ meldete status=healthy, aber:
#  (1) flower: 'Failed to parse: flower_server:5556Flower is not a valid
#      host or port' — health_path 'Flower' ohne fuehrendes '/' wurde an
#      die URL angehaengt. Der Dev-Compose startet den flwr-SuperLink
#      (scripts/flower_superlink_entry.py, Runtime-API Port 9091), der
#      keinen HTTP-Health-Endpunkt hat.
#  (2) agents_loaded: 0 — zaehlte die Legacy-DB-Tabelle core_agent, die
#      niemand befuellt. Echte Agenten: agents/AGENT_REGISTRY (34 seit OP88).
# Fix: (1) TCP-Connect auf flower_server:9091; (2) len(AGENT_REGISTRY).
import os
import socket
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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

REPO_ROOT = Path(__file__).resolve().parent.parent
VIEWS = REPO_ROOT / "django_project" / "api" / "views.py"
views_src = VIEWS.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# T1: flower-Check — kein kaputter URL-String mehr im Source
# ---------------------------------------------------------------------------
import re as _re  # noqa: E402
# Der alte Bug war ein _check_service_health-Aufruf mit health_path='Flower'
# (ohne führendes /). Er darf nicht mehr als Funktionsaufruf existieren —
# Erwähnungen im Kommentar (Doku des Fixes) sind OK.
old_bug_call = _re.findall(
    r"_check_service_health\([^)]*['\"]Flower['\"]", views_src)
check("T1a kein _check_service_health-Aufruf mit health_path='Flower' (alter Bug)",
      not old_bug_call, f"alter Bug-Aufruf noch vorhanden: {old_bug_call}")
check("T1b flower-Check nutzt TCP-Connect auf Port 9091 (SuperLink Runtime-API)",
      "_check_tcp_port('flower_server', 9091)" in views_src,
      "TCP-Connect-Aufruf fehlt")
check("T1c _check_tcp_port Helfer existiert",
      "def _check_tcp_port(self, host, port, timeout=2)" in views_src)
check("T1d socket-Import vorhanden (stdlib, keine neue Dependency)",
      "\nimport socket\n" in views_src)

# ---------------------------------------------------------------------------
# T2: agents_loaded — Registry statt toter DB-Tabelle
# ---------------------------------------------------------------------------
check("T2a agents_loaded zaehlt AGENT_REGISTRY (nicht Agent.objects.count)",
      "len(AGENT_REGISTRY)" in views_src)
check("T2b Health-Block nutzt nicht mehr Agent.objects.count()",
      "agents_loaded = Agent.objects.count()" not in views_src)
check("T2c Import-Fallback: agents_loaded = 0 bei Importfehler (nie Crash)",
      "except Exception:\n            agents_loaded = 0" in views_src)

# ---------------------------------------------------------------------------
# T3: _check_tcp_port — Verhalten gegen echten loopback-Listener
# ---------------------------------------------------------------------------
from api.views import HealthCheckView  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), _Handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

view = HealthCheckView()
check("T3a TCP-Connect auf offenen Port -> healthy",
      view._check_tcp_port("127.0.0.1", port) == "healthy")
srv.shutdown()
srv.server_close()

# geschlossener Port -> unhealthy mit Grund (kein 'Failed to parse')
res = view._check_tcp_port("127.0.0.1", 1, timeout=1)
check("T3b TCP-Connect auf geschlossenen Port -> unhealthy mit Grund",
      res.startswith("unhealthy:") and "Failed to parse" not in res,
      f"got {res[:80]}")

# unaufloesbarer Host -> unhealthy mit Grund (kein Crash, kein Parse-Fehler)
res2 = view._check_tcp_port("flower_server.invalid", 9091, timeout=1)
check("T3c unaufloesbarer Host -> unhealthy mit Grund (kein Crash)",
      res2.startswith("unhealthy:") and "Failed to parse" not in res2,
      f"got {res2[:80]}")

# ---------------------------------------------------------------------------
# T4: Live-Health via Django-Testclient — agents_loaded spiegelt Registry
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402

client = Client()
resp = client.get("/health/")
check("T4a /health/ antwortet 200", resp.status_code == 200,
      f"status {resp.status_code}")
body = resp.json()

from agents import AGENT_REGISTRY  # noqa: E402
check("T4b agents_loaded == len(AGENT_REGISTRY) (34 seit OP88)",
      body.get("agents_loaded") == len(AGENT_REGISTRY),
      f"got {body.get('agents_loaded')}, registry={len(AGENT_REGISTRY)}")
check("T4c agents_loaded ist int und > 0",
      isinstance(body.get("agents_loaded"), int)
      and body.get("agents_loaded", 0) > 0)

flower_status = (body.get("docker_services") or {}).get("flower", "")
check("T4d flower-Status ohne 'Failed to parse' (ehrlich statt kaputt)",
      "Failed to parse" not in flower_status,
      f"got {flower_status[:100]}")
check("T4e flower-Status ist 'healthy' oder 'unhealthy: <grund>'",
      flower_status == "healthy" or flower_status.startswith("unhealthy:"),
      f"got {flower_status[:100]}")

# ---------------------------------------------------------------------------
# T5: Health-Vertrag — Pflichtfelder vorhanden (OP89-Smoke nutzt /health/)
# ---------------------------------------------------------------------------
for field in ("status", "version", "timestamp", "agents_loaded",
              "database_status", "storage_status", "framework_status",
              "docker_services", "system_info"):
    check(f"T5 {field} vorhanden", field in body)

# ---------------------------------------------------------------------------
# T6: py_compile + keine neue Dependency
# ---------------------------------------------------------------------------
import py_compile  # noqa: E402
try:
    py_compile.compile(str(VIEWS), doraise=True)
    check("T6a views.py kompiliert", True)
except Exception as exc:
    check("T6a views.py kompiliert", False, str(exc))

check("T6b keine neuen Imports ausser stdlib socket",
      "import socket" in views_src and "import flwr" not in views_src)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
