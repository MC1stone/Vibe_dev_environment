#!/usr/bin/env python3
# OP83 test matrix: LLM-Wartezeit der Aufbereitung begrenzen.
# Nutzer-Befund (2026-10-22): CPU-only Ollama (mistral:latest, 4.4 GB) -
# Fahrplan-Karte zeigte Datei 1/2 im KI-Schritt seit 5:34 (>300 s);
# 2 Versuche x 300 s Timeout = bis 10 min PRO DATEI blockierten die
# Aufbereitung (30+ min Gesamtlauf). OP83:
#   1) Default entschaeerft: 1 Versuch, 120 s (vorher 2 x 300 s)
#   2) NIR_LLM_ATTEMPTS / NIR_LLM_TIMEOUT konfigurierbar
#   3) NIR_INGEST_LLM=skip deaktiviert den KI-Pass der Aufbereitung
#      komplett (ehrlicher Vermerk im Report statt stiller Verweigerung)
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

REPO_ROOT = Path(__file__).resolve().parent.parent
import py_compile  # noqa: E402
for f in ("services/metadata_llm.py", "services/project_ingest.py"):
    try:
        py_compile.compile(str(REPO_ROOT / f), doraise=True)
        check(f"T1 kompiliert: {f}", True)
    except Exception as exc:
        check(f"T1 kompiliert: {f}", False, str(exc))

# ---------------------------------------------------------------------------
# T2: Client-Defaults entschaeerft + konfigurierbar
# ---------------------------------------------------------------------------
llm_src = (REPO_ROOT / "services" / "metadata_llm.py").read_text("utf-8")
check("T2a attempts konfigurierbar (NIR_LLM_ATTEMPTS)",
      "NIR_LLM_ATTEMPTS" in llm_src)
check("T2b chat() nutzt self.attempts (kein hartes 2-if)",
      "attempts = self.attempts" in llm_src)
check("T2c Default-Timeout ohne ENV auf 120 s gesenkt",
      'self.timeout = 120' in llm_src)

import importlib  # noqa: E402
for var in ("NIR_LLM_TIMEOUT", "NIR_LLM_ATTEMPTS", "NIR_INGEST_LLM"):
    os.environ.pop(var, None)
import services.metadata_llm as mllm  # noqa: E402
importlib.reload(mllm)
client = mllm.OllamaMetadataClient()
check("T2d Default: 1 Versuch", client.attempts == 1,
      f"attempts={client.attempts}")
check("T2e Default: Timeout 120 s", client.timeout == 120,
      f"timeout={client.timeout}")
os.environ["NIR_LLM_ATTEMPTS"] = "2"
os.environ["NIR_LLM_TIMEOUT"] = "300"
importlib.reload(mllm)
client2 = mllm.OllamaMetadataClient()
check("T2f ENV ueberschreibt (2 Versuche, 300 s)",
      client2.attempts == 2 and client2.timeout == 300)
os.environ.pop("NIR_LLM_ATTEMPTS", None)
os.environ.pop("NIR_LLM_TIMEOUT", None)

# ---------------------------------------------------------------------------
# T3: NIR_INGEST_LLM=skip -> kein LLM-Call, ehrlicher Vermerk
# ---------------------------------------------------------------------------
os.environ.pop("NIR_INGEST_LLM", None)
import services.project_ingest as ping  # noqa: E402
importlib.reload(ping)

entry = {}
ping._ki_metadata_pass(entry, "/nonexistent.csv", None)
check("T3a ohne skip: kein deaktiviert-Vermerk",
      "deaktiviert" not in str((entry.get("metadata_sources") or {})
                               .get("llm", "")))

os.environ["NIR_INGEST_LLM"] = "skip"
importlib.reload(ping)
entry2 = {}
ping._ki_metadata_pass(entry2, "/nonexistent.csv", None)
check("T3b skip: KI-Pass fuehrt KEINEN LLM-Call aus",
      "deaktiviert" in str((entry2.get("metadata_sources") or {})
                           .get("llm", "")))
check("T3c skip: ehrlicher Vermerk erklaert das Verhalten",
      "deterministische Aufbereitung" in str(
          (entry2.get("metadata_sources") or {}).get("llm", "")))

# skip=off/no/0/false equally accepted
for alias in ("off", "no", "0", "false"):
    os.environ["NIR_INGEST_LLM"] = alias
    importlib.reload(ping)
    e = {}
    ping._ki_metadata_pass(e, "/x.csv", None)
    if "deaktiviert" in str((e.get("metadata_sources") or {}).get("llm", "")):
        check(f"T3d Alias '{alias}' akzeptiert", True)
    else:
        check(f"T3d Alias '{alias}' akzeptiert", False)
os.environ.pop("NIR_INGEST_LLM", None)
importlib.reload(ping)

# ---------------------------------------------------------------------------
# T4: compose exposes the variables
# ---------------------------------------------------------------------------
compose_src = (REPO_ROOT / "docker-compose.yml").read_text("utf-8")
check("T4a compose: NIR_INGEST_LLM durchreichbar",
      "NIR_INGEST_LLM=${NIR_INGEST_LLM" in compose_src)
check("T4b compose: NIR_LLM_ATTEMPTS durchreichbar",
      "NIR_LLM_ATTEMPTS=${NIR_LLM_ATTEMPTS" in compose_src)
check("T4c compose: NIR_LLM_TIMEOUT durchreichbar",
      "NIR_LLM_TIMEOUT=${NIR_LLM_TIMEOUT" in compose_src)

# ---------------------------------------------------------------------------
# T5: E2E - Reingest mit skip laeuft deterministisch durch
# (KI-Pass ist der einzige LLM-Kontakt der Aufbereitung)
# ---------------------------------------------------------------------------
from django.conf import settings as dj_settings  # noqa: E402
if "testserver" not in dj_settings.ALLOWED_HOSTS:
    dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]
dj_settings.DATABASES["default"]["NAME"] = ":memory:"
from django.core.management import call_command  # noqa: E402
call_command("migrate", interactive=False, verbosity=0)
from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from core.models import AnalysisProject, GenericFile  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
import json  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op83llm").first()
if user is None:
    user = User.objects.create_user("op83llm", password="pw",
                                   email="op83@example.com")
client = Client(HTTP_HOST="testserver")
client.force_login(user)


def _wide_csv(prefix, base, step, n, brix_lo):
    hdr = ",".join([f"{prefix}_{base+i*step}" for i in range(n)] + ["brix"])
    lines = [hdr]
    for r_ in range(16):
        chans = ",".join(f"{0.4+0.01*((i+r_+1)%(n))}" for i in range(n))
        lines.append(chans + f",{brix_lo+0.05*r_}")
    return ("\n".join(lines) + "\n").encode()


os.environ["NIR_INGEST_LLM"] = "skip"
importlib.reload(ping)
p = AnalysisProject.objects.create(name="OP83-Skip", phase="drafted",
                                   user=user)
gf = GenericFile.objects.create(
    file=SimpleUploadedFile("s.csv", _wide_csv("A", 900, 10, 12, 4.0),
                            content_type="text/csv"),
    file_size=10, user=user)
p.files.add(gf)
report = ping.build_preparation_report(p)
datasets = report.get("datasets") or []
check("T5a Reingest mit skip: Datensaetze deterministisch gebaut",
      len(datasets) >= 1)
llm_note = str(((datasets[0].get("metadata_sources") or {})
                .get("llm", "")))
check("T5b Datensatz traegt den ehrlichen skip-Vermerk",
      "deaktiviert" in llm_note, llm_note[:80])
os.environ.pop("NIR_INGEST_LLM", None)
importlib.reload(ping)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
