# covers: api/project_views.py
# OP92 test matrix: Reingest-Spinner 3h + LLM-Timeout-Bugs.
# Befund aus Nutzer-Feedback (2026-10-23, docker logs nach Merge #238):
#  (1) Reingest-Spinner lief 3h+ — OP78-Reingest startet daemon-Thread;
#      ein Container-Restart (docker compose up -d nach git pull) killt
#      den Thread, Report bleibt geleert, Status liefert nie ready/error,
#      JS pollt endlos.
#  (2) docker-compose.yml:204 `NIR_LLM_TIMEOUT=${NIR_LLM_TIMEOUT:-}` ->
#      leerer String im Container -> int('') ValueError (Chatbot-500 +
#      metadata_llm.py:104 Traceback im Log).
#  (3) chatbot_service.py: `self.timeout = timeout` ueberschrieb den
#      env-Default mit None -> requests.post(timeout=None) -> ewiger Hang.
# Fix: (1) Stale-Detection im Status-Endpunkt + Poll-Cap 30 min im JS;
#      (2) compose-Default 120 statt leer + robuster Env-Parse;
#      (3) chatbot-Timeout-Bug entfernt.
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

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE = REPO_ROOT / "docker-compose.yml"
METADATA_LLM = REPO_ROOT / "services" / "metadata_llm.py"
CHATBOT = REPO_ROOT / "services" / "chatbot_service.py"
PROJECT_VIEWS = REPO_ROOT / "django_project" / "api" / "project_views.py"
REPORT_TPL = (REPO_ROOT / "django_project" / "templates"
              / "project_report.html")

compose_src = COMPOSE.read_text(encoding="utf-8")
metadata_src = METADATA_LLM.read_text(encoding="utf-8")
chatbot_src = CHATBOT.read_text(encoding="utf-8")
views_src = PROJECT_VIEWS.read_text(encoding="utf-8")
report_src = REPORT_TPL.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# T1: compose — NIR_LLM_TIMEOUT mit Default 120, nicht leer
# ---------------------------------------------------------------------------
import re as _re  # noqa: E402
check("T1a compose: NIR_LLM_TIMEOUT=${NIR_LLM_TIMEOUT:-120} (Default statt leer)",
      "NIR_LLM_TIMEOUT=${NIR_LLM_TIMEOUT:-120}" in compose_src,
      "compose-Zeile nicht gefixt")
check("T1b compose: kein `NIR_LLM_TIMEOUT=${NIR_LLM_TIMEOUT:-}` mehr (leer-Bug)",
      "NIR_LLM_TIMEOUT=${NIR_LLM_TIMEOUT:-}" not in compose_src)

# ---------------------------------------------------------------------------
# T2: metadata_llm — robuster Env-Parse, nie ValueError
# ---------------------------------------------------------------------------
check("T2a metadata_llm: _env_int-Helfer vorhanden",
      "def _env_int(name: str, default: int) -> int:" in metadata_src)
check("T2b metadata_llm: Timeout-Parse nutzt _env_int (kein int('') mehr)",
      '_env_int("NIR_LLM_TIMEOUT", 300)' in metadata_src
      and 'int(os.environ.get("NIR_LLM_TIMEOUT"' not in metadata_src)
check("T2c metadata_llm: Attempts-Parse nutzt _env_int",
      'max(1, _env_int("NIR_LLM_ATTEMPTS", 1))' in metadata_src)

# Live: leerer/unungueltiger Env-Wert -> Default, kein Crash.
# Leer heisst OP83-Default 120 (Dokument-Verhalten: "Default 120 seit
# OP83"); UNSET heisst 300 (historischer Fallback). Beides kein Crash.
os.environ["NIR_LLM_TIMEOUT"] = ""
os.environ["NIR_LLM_ATTEMPTS"] = ""
try:
    from services.metadata_llm import OllamaMetadataClient  # noqa: E402
    c = OllamaMetadataClient(base_url="http://127.0.0.1:1", model="x")
    check("T2d leerer NIR_LLM_TIMEOUT -> OP83-Default 120 (kein ValueError)",
          c.timeout == 120, f"timeout={c.timeout}")
    check("T2e leerer NIR_LLM_ATTEMPTS -> Default 1 (kein ValueError)",
          c.attempts == 1, f"attempts={c.attempts}")
except Exception as exc:
    check("T2d leerer NIR_LLM_TIMEOUT -> OP83-Default 120 (kein ValueError)",
          False, str(exc))
    check("T2e leerer NIR_LLM_ATTEMPTS -> Default 1 (kein ValueError)",
          False, str(exc))

os.environ["NIR_LLM_TIMEOUT"] = "garbage"
os.environ["NIR_LLM_ATTEMPTS"] = "-5"
try:
    c2 = OllamaMetadataClient(base_url="http://127.0.0.1:1", model="x")
    check("T2f ungueltiger NIR_LLM_TIMEOUT -> Fallback 300",
          c2.timeout == 300, f"timeout={c2.timeout}")
    check("T2g negativer NIR_LLM_ATTEMPTS -> clamp auf 1",
          c2.attempts == 1, f"attempts={c2.attempts}")
except Exception as exc:
    check("T2f ungueltiger NIR_LLM_TIMEOUT -> Fallback 300", False, str(exc))
    check("T2g negativer NIR_LLM_ATTEMPTS -> clamp auf 1", False, str(exc))

# UNSET (Host-Variable nicht definiert) -> OP83-Default 120
os.environ.pop("NIR_LLM_TIMEOUT", None)
try:
    c2b = OllamaMetadataClient(base_url="http://127.0.0.1:1", model="x")
    check("T2f2 NIR_LLM_TIMEOUT unset -> OP83-Default 120",
          c2b.timeout == 120, f"timeout={c2b.timeout}")
except Exception as exc:
    check("T2f2 NIR_LLM_TIMEOUT unset -> OP83-Default 120", False, str(exc))

os.environ["NIR_LLM_TIMEOUT"] = "250"
os.environ["NIR_LLM_ATTEMPTS"] = "3"
try:
    c3 = OllamaMetadataClient(base_url="http://127.0.0.1:1", model="x")
    check("T2h gueltiger NIR_LLM_TIMEOUT=250 -> 250",
          c3.timeout == 250, f"timeout={c3.timeout}")
    check("T2i gueltiger NIR_LLM_ATTEMPTS=3 -> 3",
          c3.attempts == 3, f"attempts={c3.attempts}")
except Exception as exc:
    check("T2h gueltiger NIR_LLM_TIMEOUT=250 -> 250", False, str(exc))
    check("T2i gueltiger NIR_LLM_ATTEMPTS=3 -> 3", False, str(exc))
finally:
    os.environ.pop("NIR_LLM_TIMEOUT", None)
    os.environ.pop("NIR_LLM_ATTEMPTS", None)

# ---------------------------------------------------------------------------
# T3: chatbot_service — Timeout-Bug entfernt, nie None
# ---------------------------------------------------------------------------
check("T3a chatbot: `self.timeout = timeout` Bug-Zeile entfernt",
      "\n        self.timeout = timeout\n" not in chatbot_src)
os.environ["NIR_LLM_TIMEOUT"] = ""
try:
    from services.chatbot_service import OllamaChatClient  # noqa: E402
    ch = OllamaChatClient(base_url="http://127.0.0.1:1", model="x")
    check("T3b chatbot: leerer NIR_LLM_TIMEOUT -> Default 120 (kein None)",
          ch.timeout == 120, f"timeout={ch.timeout}")
    check("T3c chatbot: timeout ist niemals None (kein ewiger Hang)",
          ch.timeout is not None, f"timeout={ch.timeout}")
except Exception as exc:
    check("T3b chatbot: leerer NIR_LLM_TIMEOUT -> Default 120 (kein None)",
          False, str(exc))
    check("T3c chatbot: timeout ist niemals None (kein ewiger Hang)",
          False, str(exc))

os.environ["NIR_LLM_TIMEOUT"] = "90"
try:
    ch2 = OllamaChatClient(base_url="http://127.0.0.1:1", model="x")
    check("T3d chatbot: gueltiger NIR_LLM_TIMEOUT=90 -> 90",
          ch2.timeout == 90, f"timeout={ch2.timeout}")
except Exception as exc:
    check("T3d chatbot: gueltiger NIR_LLM_TIMEOUT=90 -> 90", False, str(exc))

try:
    ch3 = OllamaChatClient(base_url="http://127.0.0.1:1", model="x",
                           timeout=42)
    check("T3e chatbot: expliziter timeout=42 gewinnt",
          ch3.timeout == 42, f"timeout={ch3.timeout}")
except Exception as exc:
    check("T3e chatbot: expliziter timeout=42 gewinnt", False, str(exc))
finally:
    os.environ.pop("NIR_LLM_TIMEOUT", None)

# ---------------------------------------------------------------------------
# T4: Status-Endpunkt — Stale-Detection (Live via Django-Testclient)
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.test.runner import DiscoverRunner  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402

setup_test_environment()
runner = DiscoverRunner(verbosity=0)
old_config = runner.setup_databases()
try:
    from core.models import User, AnalysisProject  # noqa: E402
    user, _ = User.objects.get_or_create(username="op92user")
    if not user.check_password("pw12345!"):
        user.set_password("pw12345!")
        user.save()

    # CASE A: frischer leerer Report (kein progress) -> nicht stale, kein error
    p_fresh = AnalysisProject.objects.create(
        user=user, name="op92-fresh",
        preparation_report={"user_options": {}})
    # CASE B: progress mit last_update vor 2h -> stale + error
    import datetime as _dt
    old_ts = (_dt.datetime.now() - _dt.timedelta(hours=2)) \
        .strftime("%Y-%m-%d %H:%M:%S")
    p_stale = AnalysisProject.objects.create(
        user=user, name="op92-stale",
        preparation_report={"user_options": {},
                            "progress": {"last_update": old_ts,
                                         "current_step": "Datei wird eingelesen",
                                         "done_files": 0,
                                         "total_files": 2}})
    # CASE C: progress frisch (jetzt) -> nicht stale
    fresh_ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    p_live = AnalysisProject.objects.create(
        user=user, name="op92-live",
        preparation_report={"user_options": {},
                            "progress": {"last_update": fresh_ts,
                                         "current_step": "Datei wird eingelesen",
                                         "done_files": 1,
                                         "total_files": 2}})
    # CASE D: fertiger Report -> ready, kein stale
    p_ready = AnalysisProject.objects.create(
        user=user, name="op92-ready",
        preparation_report={"datasets": [{"file_name": "a.csv"}]})
    # CASE E: preparation_error gesetzt -> error, kein stale-Check noetig
    p_err = AnalysisProject.objects.create(
        user=user, name="op92-err",
        preparation_report={"preparation_error": "boom"})

    client = Client()
    client.login(username="op92user", password="pw12345!")

    b = client.get(f"/api/projects/create/{p_fresh.id}/status/").json()
    check("T4a frischer leerer Report: ready=False, stale=False, error=None",
          b.get("ready") is False and b.get("stale") is False
          and not b.get("error"), str(b)[:150])

    b = client.get(f"/api/projects/create/{p_stale.id}/status/").json()
    check("T4b last_update 2h alt: stale=True + ehrlicher error-Text",
          b.get("ready") is False and b.get("stale") is True
          and b.get("error") and "Lebenszeichen" in b["error"],
          str(b)[:200])

    b = client.get(f"/api/projects/create/{p_live.id}/status/").json()
    check("T4c frischer last_update: stale=False, error=None",
          b.get("stale") is False and not b.get("error"), str(b)[:150])

    b = client.get(f"/api/projects/create/{p_ready.id}/status/").json()
    check("T4d fertiger Report: ready=True, stale=False",
          b.get("ready") is True and b.get("stale") is False,
          str(b)[:150])

    b = client.get(f"/api/projects/create/{p_err.id}/status/").json()
    check("T4e preparation_error: error gemeldet, stale=False",
          b.get("error") == "boom" and b.get("stale") is False,
          str(b)[:150])
finally:
    runner.teardown_databases(old_config)

# ---------------------------------------------------------------------------
# T5: Template-JS — stale behandelt + Poll-Cap 30 min
# ---------------------------------------------------------------------------
check("T5a Template: POLL_CAP_MS = 30 Minuten gesetzt",
      "const POLL_CAP_MS = 30 * 60 * 1000;" in report_src)
check("T5b Template: data.stale wird wie data.error behandelt",
      "data.error || data.stale" in report_src)
check("T5c Template: Poll-Cap-Zweig stoppt mit Alert (kein endloses poll)",
      "Date.now() - startedAt > POLL_CAP_MS" in report_src
      and "ungewoehnlich lange" in report_src)
check("T5d Template: stale-Fallback-Text vorhanden",
      "ohne Lebenszeichen" in report_src)

# ---------------------------------------------------------------------------
# T6: py_compile aller geaenderten Dateien
# ---------------------------------------------------------------------------
import py_compile  # noqa: E402
for label, path in [
    ("metadata_llm.py", METADATA_LLM),
    ("chatbot_service.py", CHATBOT),
    ("project_views.py", PROJECT_VIEWS),
]:
    try:
        py_compile.compile(str(path), doraise=True)
        check(f"T6 py_compile {label}", True)
    except py_compile.PyCompileError as exc:
        check(f"T6 py_compile {label}", False, str(exc))

# compose ist YAML — kein py_compile; stattdessen: Zeile parst als Text
check("T6d compose: NIR_LLM_TIMEOUT-Zeile syntaktisch plausibel",
      _re.search(r"^\s*- NIR_LLM_TIMEOUT=\$\{NIR_LLM_TIMEOUT:-120\}$",
                 compose_src, _re.M) is not None)

# ---------------------------------------------------------------------------
# T7: CI change-impact Job kompiliert .mo-Kataloge (OP92-CI-Fix)
# Hintergrund: Der Gate-Job hatte KEINEN compilemessages-Step (nur der
# Vollmatrix-Job). test_op49_sensor_diy.py crasht in CI mit
# FileNotFoundError ohne .mo. Fix: polib-basierter Compile-Step im
# change-impact-Job. Verifiziert: ohne .mo crasht OP49 lokal mit dem
# exakt gleichen Fehler wie in CI; mit polib-Compile 23/23 gruen.
# ---------------------------------------------------------------------------
CI_YML = REPO_ROOT.parent / ".github" / "workflows" / "ci.yml"
ci_src = CI_YML.read_text(encoding="utf-8")
# Der Step muss INNERHALB des change-impact-Jobs stehen (nach dessen
# "Install minimal test dependencies", vor "Run change-impact gate")
gate_section = ci_src.split("change-impact:")[1] if "change-impact:" in ci_src else ""
check("T7a CI change-impact Job: polib-Compile-Step vorhanden",
      "Compile i18n catalogs for gate (OP92)" in gate_section
      and "pip install polib" in gate_section)
check("T7b CI change-impact Job: Compile VOR dem Gate-Run",
      gate_section.find("Compile i18n catalogs for gate")
      < gate_section.find("Run change-impact gate against origin/main")
      if "Compile i18n catalogs for gate" in gate_section else False)
check("T7c CI change-impact Job: polib kompiliert ALLE locale-Kataloge",
      "locale.glob('*/LC_MESSAGES/django.po')" in gate_section)

# Der Vollmatrix-Job MUSS polib in seinen Deps haben (OP92: OP92-Matrix
# selbst importiert polib im finally-Block zum .mo-Restore — ohne
# polib in CI crasht der Restore mit ImportError -> .mo fehlen ->
# Folgelauf von OP49 schlaegt fehl).
matrix_section = ci_src.split("test-matrices:")[1].split("change-impact:")[0] \
    if "test-matrices:" in ci_src else ""
check("T7c2 CI Vollmatrix-Job: polib in den Test-Dependencies",
      "polib" in matrix_section
      and "pip install" in matrix_section,
      "polib fehlt in Vollmatrix-Deps — OP92-Matrix wuerde in CI crashen")

# Live-Reproduktion des CI- originais: OP49 crasht ohne .mo, gruen mit .mo
import subprocess as _sp  # noqa: E402
locale_dir = (REPO_ROOT / "django_project" / "locale").resolve()
mo_files = sorted(locale_dir.glob("*/LC_MESSAGES/*.mo"))
try:
    for mo in mo_files:
        mo.unlink()
    r = _sp.run([sys.executable, str(REPO_ROOT / "tests" / "test_op49_sensor_diy.py")],
                capture_output=True, text=True, timeout=120,
                cwd=str(REPO_ROOT))
    check("T7d OP49 ohne .mo crasht mit FileNotFoundError (CI-Reproduktion)",
          r.returncode != 0 and "No translation file found" in (r.stderr + r.stdout),
          f"rc={r.returncode}")
finally:
    # .mo wiederherstellen (polib-Compile wie im CI-Step)
    try:
        import polib as _polib
        for po in sorted(locale_dir.glob("*/LC_MESSAGES/django.po")):
            _polib.pofile(str(po)).save_as_mofile(str(po.with_suffix(".mo")))
    except ImportError:
        pass

# OP49 schreibt das RESULT auf stdout UND stderr (logging); robust pruefen
r = _sp.run([sys.executable, str(REPO_ROOT / "tests" / "test_op49_sensor_diy.py")],
            capture_output=True, text=True, timeout=120,
            cwd=str(REPO_ROOT))
combined = r.stdout + r.stderr
check("T7e OP49 mit polib-kompilierten .mo: 23/23 gruen (CI-Fix wirkt)",
      r.returncode == 0 and "23 passed, 0 failed" in combined,
      f"rc={r.returncode} tail={combined[-200:]!r}")

print(f"\nOP92 reingest-spinner/timeouts matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
