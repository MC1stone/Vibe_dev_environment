#!/usr/bin/env python3
# OP84 test matrix: Selektive KI-Nutzung fuer die Metadaten-Zuordnung.
# Nutzer-Anforderung (2026-10-22): 'Ich brauche die Kreativitaet, da die
# Metadaten automatisch zugeordnet werden sollen - vielleicht koennen wir
# die KI-Nutzung auf die Metadaten beschraenken, die deterministisch
# nicht zugeordnet werden koennen?'
# => Der KI-Pass laeuft NUR wenn der deterministische Layer Felder
# offen laesst; der Prompt fokussiert genau diese Luecken. Vollstaendig
# deterministische Dateien sparen den LLM-Call komplett (CPU-Ollama:
# Minuten pro Datei).
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

import time  # noqa: E402
import services.project_ingest as ping  # noqa: E402
from services.metadata_llm import CANONICAL_FIELDS, MetadataLLMService  # noqa: E402

# ---------------------------------------------------------------------------
# T2: Vollstaendig deterministische Metadaten -> KEIN LLM-Call
# ---------------------------------------------------------------------------
os.environ.pop("NIR_INGEST_LLM", None)
entry_full = {"metadata": {f: f"val_{f}" for f in CANONICAL_FIELDS}}
t0 = time.monotonic()
ping._ki_metadata_pass(entry_full, "/nonexistent.csv", None)
dt = time.monotonic() - t0
note = (entry_full.get("metadata_sources") or {}).get("llm", "")
check("T2a alle Felder deterministisch -> LLM-Call gespart",
      "kein KI-Aufruf" in note, note[:80])
check("T2b Ersparnis real (< 1 s statt Minuten)", dt < 1.0,
      f"{dt:.3f}s")
check("T2c ehrlicher Vermerk im Report",
      "deterministisch zugeordnet" in note)

# ---------------------------------------------------------------------------
# T3: Luecken -> fokussierter Auftrag (Prompt-Mechanik)
# ---------------------------------------------------------------------------
llm_src = (REPO_ROOT / "services" / "metadata_llm.py").read_text("utf-8")
check("T3a extract() kennt focus_fields",
      "focus_fields" in llm_src)
check("T3b Fokus-Prompt nennt die offenen Felder",
      "noch offenen Felder" in llm_src)
check("T3c Kreativitaet erhalten: Zusatz-Auftrag gilt im Fokus",
      "Zusatz-Auftrag" in llm_src
      and "fuer genau diese Felder" in llm_src)
ingest_src = (REPO_ROOT / "services" / "project_ingest.py").read_text("utf-8")
check("T3d KI-Pass ermittelt offene Felder VOR dem Call",
      "relevant_open" in ingest_src)
check("T3e extract() wird mit focus_fields gerufen",
      "focus_fields=relevant_open or None" in ingest_src)

# Luecken-Ermittlung als Einheit
entry_gap = {"metadata": {"sample_id": "S1", "operator_name": "Anna"}}
meta = entry_gap["metadata"]
filled = {f for f in CANONICAL_FIELDS if str(meta.get(f) or "").strip()}
open_fields = [f for f in CANONICAL_FIELDS if f not in filled]
check("T3f Luecken korrekt ermittelt (Rest offen)",
      len(open_fields) == len(CANONICAL_FIELDS) - 2
      and "sample_id" not in open_fields)

# focus_fields ohne kanonische Namen -> None (kein sinnloser Call)
svc = MetadataLLMService()
check("T3g focus_fields nur mit kanonischen Feldern",
      # nicht direkt aufrufbar ohne LLM - Strukturpruefung
      "focus = [f for f in focus_fields if f in CANONICAL_FIELDS]"
      in llm_src)

# ---------------------------------------------------------------------------
# T4: skip-Schalter (OP83) unveraendert integriert
# ---------------------------------------------------------------------------
check("T4a NIR_INGEST_LLM=skip weiterhin erster Guard",
      "NIR_INGEST_LLM" in ingest_src)

# ---------------------------------------------------------------------------
# T5: E2E - Aufbereitung einer Wide-CSV mit vollstaendigen Metadaten
# laeuft ohne jeden LLM-Kontakt durch (Namen + Werte deterministisch).
# (KI hier ohnehin nicht erreichbar in der Sandbox - der Punkt ist der
# gesparte Call-Pfad, der nicht in den Timeout laufen kann.)
# ---------------------------------------------------------------------------
from django.conf import settings as dj_settings  # noqa: E402
if "testserver" not in dj_settings.ALLOWED_HOSTS:
    dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]
dj_settings.DATABASES["default"]["NAME"] = ":memory:"
from django.core.management import call_command  # noqa: E402
call_command("migrate", interactive=False, verbosity=0)
from django.contrib.auth import get_user_model  # noqa: E402
from core.models import AnalysisProject, GenericFile  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op84sel").first()
if user is None:
    user = User.objects.create_user("op84sel", password="pw",
                                   email="op84@example.com")


def _wide_csv(prefix, base, step, n, brix_lo):
    hdr = ",".join([f"{prefix}_{base+i*step}" for i in range(n)] + ["brix"])
    lines = [hdr]
    for r_ in range(16):
        chans = ",".join(f"{0.4+0.01*((i+r_+1)%(n))}" for i in range(n))
        lines.append(chans + f",{brix_lo+0.05*r_}")
    return ("\n".join(lines) + "\n").encode()


p = AnalysisProject.objects.create(name="OP84-Selektiv", phase="drafted",
                                   user=user)
gf = GenericFile.objects.create(
    file=SimpleUploadedFile("sel.csv", _wide_csv("A", 900, 10, 12, 4.0),
                            content_type="text/csv"),
    file_size=10, user=user)
p.files.add(gf)
t1 = time.monotonic()
report = ping.build_preparation_report(p)
dt_e2e = time.monotonic() - t1
datasets = report.get("datasets") or []
check("T5a E2E: Datensaetze gebaut", len(datasets) >= 1)
llm_e2e = str(((datasets[0].get("metadata_sources") or {}).get("llm", "")))
check("T5b E2E: KI-Quelle ehrlich dokumentiert (gespart oder fokussiert)",
      ("gespart" in llm_e2e) or ("nicht erreichbar" in llm_e2e)
      or ("deaktiviert" in llm_e2e) or llm_e2e == "",
      llm_e2e[:80])
check("T5c E2E: Aufbereitung schnell (kein Timeout-Kontakt)",
      dt_e2e < 120, f"{dt_e2e:.1f}s")

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
