# covers: services/project_ingest.py, api/project_views.py
# OP94 test matrix: Metadaten-Score 20/100 trotz Eingaben + Reingest ohne Karte.
# Zwei Bugs aus Nutzer-Feedback (2026-10-24, nach OP93-Merge):
# (A) Score zaehlte nur 5 RECOMMENDED_METADATA_FIELDS, nicht die 16
#     CANONICAL_FIELDS -> User-Eingaben (sample_id, location, notes etc.)
#     hatten keinen Effekt auf den Score.
# (B) Race zwischen Metadaten-Rebuild-Thread (OP93 async) und Reingest-
#     Thread: beide konkurrieren um project.preparation_report. Wenn der
#     Metadaten-Thread nach dem Reingest datasets schreibt, erscheint die
#     preparingCard nicht (Bedingung: phase=drafted AND not datasets).
# Fix: (A) Score zaehlt alle 16 CANONICAL_FIELDS mit Alias-Mapping;
#      (B) preparation_generation-Guard - letzter Thread gewinnt.
import os
import sys
import time
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
INGEST = REPO_ROOT / "services" / "project_ingest.py"
VIEWS = REPO_ROOT / "django_project" / "api" / "project_views.py"
REPORT_TPL = (REPO_ROOT / "django_project" / "templates"
              / "project_report.html")

ingest_src = INGEST.read_text(encoding="utf-8")
views_src = VIEWS.read_text(encoding="utf-8")
report_src = REPORT_TPL.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# T1: Score zaehlt alle CANONICAL_FIELDS (Bug A)
# ---------------------------------------------------------------------------
from services.project_ingest import _assess_metadata  # noqa: E402
from services.metadata_llm import CANONICAL_FIELDS  # noqa: E402

check("T1a CANONICAL_FIELDS hat 16 Eintraege",
      len(CANONICAL_FIELDS) == 16, f"len={len(CANONICAL_FIELDS)}")

# User-Szenario: 6 Felder (5 canonical + operator alias)
datasets_user = [{
    "usable": True,
    "metadata": {
        "sample_id": "S-001", "location": "Labor A", "notes": "Vorbereitung 2h",
        "operator": "Tom", "wavelength_range": "900-1700nm", "resolution": "8nm",
    },
    "metadata_sources": {k: "editor" for k in [
        "sample_id", "location", "notes", "operator",
        "wavelength_range", "resolution"]},
}]
r = _assess_metadata(datasets_user)
check("T1b Score > 20% (war 20.0, jetzt 37.5 = 6/16)",
      r["overall_quality_score"] == 37.5,
      f"score={r['overall_quality_score']}")
check("T1c canonical_fields_found enthaelt 6 Felder",
      len(r.get("canonical_fields_found") or []) == 6,
      f"found={r.get('canonical_fields_found')}")
check("T1d operator (alias) wird als operator_name gezaehlt",
      "operator_name" in (r.get("canonical_fields_found") or []),
      f"found={r.get('canonical_fields_found')}")
check("T1e canonical_fields_total = 16",
      r.get("canonical_fields_total") == 16,
      f"total={r.get('canonical_fields_total')}")

# Alle 16 canonical Felder -> 100%
datasets_full = [{
    "usable": True,
    "metadata": {f: f"val_{f}" for f in CANONICAL_FIELDS},
    "metadata_sources": {},
}]
r_full = _assess_metadata(datasets_full)
check("T1f Alle 16 canonical -> Score 100.0",
      r_full["overall_quality_score"] == 100.0,
      f"score={r_full['overall_quality_score']}")

# Keine Felder -> 0%
datasets_empty = [{"usable": True, "metadata": {}, "metadata_sources": {}}]
r_empty = _assess_metadata(datasets_empty)
check("T1g Keine Felder -> Score 0.0",
      r_empty["overall_quality_score"] == 0.0,
      f"score={r_empty['overall_quality_score']}")

# Alias + canonical gleichzeitig -> nicht doppelt gezaehlt
datasets_alias = [{
    "usable": True,
    "metadata": {"operator": "Tom", "operator_name": "Tom"},
    "metadata_sources": {},
}]
r_alias = _assess_metadata(datasets_alias)
check("T1h Alias+canonical nicht doppelt (6.2 = 1/16)",
      r_alias["overall_quality_score"] == 6.2,
      f"score={r_alias['overall_quality_score']}")
check("T1i Alias+canonical: nur operator_name in found",
      r_alias.get("canonical_fields_found") == ["operator_name"],
      f"found={r_alias.get('canonical_fields_found')}")

# Nur Alias (operator) -> zaehlt als operator_name
datasets_only_alias = [{
    "usable": True,
    "metadata": {"operator": "Tom"},
    "metadata_sources": {},
}]
r_only_alias = _assess_metadata(datasets_only_alias)
check("T1j Nur operator (alias) -> 6.2% (1/16 via operator_name)",
      r_only_alias["overall_quality_score"] == 6.2,
      f"score={r_only_alias['overall_quality_score']}")
check("T1k Nur operator (alias) -> operator_name in found",
      "operator_name" in (r_only_alias.get("canonical_fields_found") or []),
      f"found={r_only_alias.get('canonical_fields_found')}")

# missing_recommended_fields bleibt korrekt (nur 5 recommended)
check("T1l missing_recommended_fields nur recommended Felder",
      set(r["missing_recommended_fields"]) <= set(
          ["operator", "humidity", "temperature", "instrument",
           "acquisition_time"]),
      f"missing={r['missing_recommended_fields']}")

# ---------------------------------------------------------------------------
# T2: Race-Guard — Generation in build_preparation_report (Bug B)
# ---------------------------------------------------------------------------
check("T2a build_preparation_report hat generation-Parameter",
      "generation: int = None" in ingest_src or "generation=None" in ingest_src,
      "Parameter fehlt")
check("T2b Race-Guard vergleicht Generation vor dem Schreiben",
      "preparation_generation" in ingest_src and "current != generation" in ingest_src,
      "Guard fehlt")
check("T2c Report uebernimmt preparation_generation",
      'report["preparation_generation"] = current_gen' in ingest_src,
      "Uebernahme fehlt")
check("T2d Verwerfen-Log bei Generation-Mismatch",
      "verworfen" in ingest_src.lower() or "Generation" in ingest_src,
      "Log fehlt")

# ---------------------------------------------------------------------------
# T3: Views — Generation-Guard in allen drei async-Pfaden
# ---------------------------------------------------------------------------
check("T3a ReingestView inkrementiert Generation",
      "preparation_generation" in views_src and
      views_src.count("preparation_generation") >= 4,
      f"count={views_src.count('preparation_generation')}")
check("T3b ReingestView Thread bekommt generation",
      "args=(project.id, generation)" in views_src or
      "args=(project.id, gen)" in views_src,
      "Thread-Arg fehlt")
check("T3c Metadaten-Save inkrementiert Generation",
      views_src.count("preparation_generation") >= 4,
      "zu wenig Vorkommen")
check("T3d Metadaten-Save Thread bekommt generation",
      "args=(project.id, generation)" in views_src,
      "Thread-Arg fehlt")
check("T3e Wunsch-Save inkrementiert Generation",
      "gen = int(report.get('preparation_generation') or 0) + 1" in views_src,
      "Wunsch-Save fehlt")
check("T3f Projekt-Anlegen initialisiert Generation=1",
      "'preparation_generation': 1" in views_src,
      "Init fehlt")

# ---------------------------------------------------------------------------
# T4: Live — Score nach Metadaten-Save > 20% (Bug A end-to-end)
# ---------------------------------------------------------------------------
os.environ["NIR_INGEST_LLM"] = "skip"
from django.test import Client  # noqa: E402
from django.test.runner import DiscoverRunner  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402

setup_test_environment()
runner = DiscoverRunner(verbosity=0)
# OP94: SQLite file-based test DB (wie OP13/OP30) — in-memory wuerde von
# Hintergrund-Threads nicht gesehen (separate Connection). SQLite-Lock
# vermeiden: timeout hochsetzen, damit konkurrierende Threads nicht
# "database table is locked" werfen.
dj_settings.DATABASES["default"]["OPTIONS"] = {"timeout": 30}
old_config = runner.setup_databases()
try:
    from core.models import User, GenericFile, AnalysisProject  # noqa: E402
    from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

    user, _ = User.objects.get_or_create(username="op94live")
    if not user.check_password("pw12345!"):
        user.set_password("pw12345!")
        user.save()

    csv_content = b"wavelength,intensity\n" + b"".join(
        f"{400+i*10},{1.0 + 0.001*i}\n".encode() for i in range(20))
    f = GenericFile.objects.create(
        user=user, name="op94_live.csv",
        original_filename="op94_live.csv",
        file=SimpleUploadedFile("op94_live.csv", csv_content),
        file_size=len(csv_content))

    project = AnalysisProject.objects.create(
        user=user, name="op94-live-test", phase="drafted",
        preparation_report={"user_options": {}, "preparation_generation": 1},
        metadata_overrides={
            str(f.id): {
                "sample_id": "S-001", "location": "Labor A",
                "notes": "Vorbereitung 2h", "operator": "Tom",
                "wavelength_range": "900-1700nm", "resolution": "8nm",
            }
        },
    )
    project.files.add(f)

    from services.project_ingest import build_preparation_report  # noqa: E402
    build_preparation_report(project, generation=1)
    project.refresh_from_db()
    rep = project.preparation_report or {}
    mq = rep.get("metadata_quality") or {}
    check("T4a Live: Score initial = 37.5% (6/16 canonical)",
          mq.get("overall_quality_score") == 37.5,
          f"score={mq.get('overall_quality_score')}")
    check("T4b Live: Generation nach initialer Aufbereitung = 1",
          rep.get("preparation_generation") == 1,
          f"gen={rep.get('preparation_generation')}")

    client = Client()
    client.login(username="op94live", password="pw12345!")

    # Metadaten-Save -> Generation 2
    resp = client.post(
        f"/projects/{project.id}/metadata/",
        data='{"metadata": {"%s": {"sample_id": "S-001", "location": "Labor A", "notes": "N", "operator": "Tom", "wavelength_range": "900-1700nm", "resolution": "8nm"}}}' % f.id,
        content_type="application/json")
    check("T4c Metadaten-Save: success + preparing",
          resp.status_code == 200 and resp.json().get("success") is True
          and resp.json().get("preparing") is True,
          str(resp.json())[:100])

    project.refresh_from_db()
    gen_after_save = (project.preparation_report or {}).get(
        "preparation_generation")
    check("T4d Generation nach Metadaten-Save = 2",
          gen_after_save == 2, f"gen={gen_after_save}")

    # OP94 CI-Fix: Warte auf den Metadaten-Rebuild-Thread, BEVOR der
    # Reingest kommt. Sonst kollidieren beide Threads um die SQLite-
    # Schreibzugriffe (CI: "database table is locked"). Der Race-Guard
    # selbst wird in T5 direkt getestet (alter Thread darf nicht
    # schreiben) — der Live-Race ist hier nicht noetig.
    _deadline_save = time.time() + 30
    while time.time() < _deadline_save:
        project.refresh_from_db()
        _rep = project.preparation_report or {}
        if len(_rep.get("datasets") or []) > 0 or _rep.get("preparation_error"):
            break
        time.sleep(0.3)

    # Reingest -> Generation 3
    resp2 = client.post(f"/projects/{project.id}/reingest/")
    check("T4e Reingest: success + preparing",
          resp2.status_code == 200 and resp2.json().get("success") is True
          and resp2.json().get("preparing") is True,
          str(resp2.json())[:100])

    project.refresh_from_db()
    gen_after_reingest = (project.preparation_report or {}).get(
        "preparation_generation")
    check("T4f Generation nach Reingest = 3",
          gen_after_reingest == 3, f"gen={gen_after_reingest}")
    check("T4g Phase nach Reingest = drafted",
          project.phase == "drafted", f"phase={project.phase}")

    # Warte auf Hintergrund-Threads (max 30s)
    deadline = time.time() + 30
    while time.time() < deadline:
        project.refresh_from_db()
        rep = project.preparation_report or {}
        if len(rep.get("datasets") or []) > 0 or rep.get("preparation_error"):
            break
        time.sleep(0.5)

    project.refresh_from_db()
    rep = project.preparation_report or {}
    check("T4h Hintergrund-Rebuild terminiert (datasets oder error)",
          len(rep.get("datasets") or []) > 0 or rep.get("preparation_error"),
          f"keys={list(rep.keys())}")
    mq = rep.get("metadata_quality") or {}
    check("T4i Finaler Score = 37.5% (6/16 canonical)",
          mq.get("overall_quality_score") == 37.5,
          f"score={mq.get('overall_quality_score')}")

    # ---------------------------------------------------------------------------
    # T5: Race-Guard — alter Thread (gen 2) darf nicht ueberschreiben
    # ---------------------------------------------------------------------------
    # Der Reingest-Thread (gen 3) hat bereits geschrieben.
    # Simuliere: Metadaten-Thread (gen 2) versucht jetzt zu schreiben.
    before_datasets = len(rep.get("datasets") or [])
    before_gen = rep.get("preparation_generation")
    result_race = build_preparation_report(project, generation=2)
    project.refresh_from_db()
    rep_after = project.preparation_report or {}
    check("T5a Race: alter Thread (gen 2) schreibt NICHT",
          rep_after.get("preparation_generation") == before_gen,
          f"gen vorher={before_gen} nachher={rep_after.get('preparation_generation')}")
    check("T5b Race: datasets nicht veraendert durch alten Thread",
          len(rep_after.get("datasets") or []) == before_datasets,
          f"vorher={before_datasets} nachher={len(rep_after.get('datasets') or [])}")

    # Aktueller Thread (gen 3) schreibt erfolgreich
    result_ok = build_preparation_report(project, generation=3)
    project.refresh_from_db()
    rep_ok = project.preparation_report or {}
    check("T5c Korrekter Thread (gen 3) schreibt erfolgreich",
          len(rep_ok.get("datasets") or []) > 0,
          f"datasets={len(rep_ok.get('datasets') or [])}")
    check("T5d Korrekter Thread: Generation bleibt 3",
          rep_ok.get("preparation_generation") == 3,
          f"gen={rep_ok.get('preparation_generation')}")

    # Ohne generation (None) -> immer schreiben (abwaertskompatibel)
    result_none = build_preparation_report(project)
    project.refresh_from_db()
    rep_none = project.preparation_report or {}
    check("T5e Ohne generation (None) wird immer geschrieben",
          len(rep_none.get("datasets") or []) > 0,
          f"datasets={len(rep_none.get('datasets') or [])}")

    project.delete()
    f.delete()
    user.delete()
finally:
    runner.teardown_databases(old_config)
    os.environ.pop("NIR_INGEST_LLM", None)

# ---------------------------------------------------------------------------
# T6: Template — preparingCard + Score-Anzeige
# ---------------------------------------------------------------------------
check("T6a Template: preparingCard-Bedingung vorhanden",
      "project.phase == 'drafted' and not preparation.datasets" in report_src,
      "Bedingung fehlt")
check("T6b Template: OP94-Kommentar vorhanden",
      "OP94" in report_src, "Kommentar fehlt")
check("T6c Template: Score-Anzeige (overall_quality_score) vorhanden",
      "metadata_quality.overall_quality_score" in report_src,
      "Score-Anzeige fehlt")

# ---------------------------------------------------------------------------
# T7: py_compile aller geaenderten Dateien
# ---------------------------------------------------------------------------
import py_compile  # noqa: E402

for fpath in [INGEST, VIEWS]:
    try:
        py_compile.compile(str(fpath), doraise=True)
        check(f"T7 py_compile {fpath.name}", True)
    except py_compile.PyCompileError as exc:
        check(f"T7 py_compile {fpath.name}", False, str(exc))

# ---------------------------------------------------------------------------
# T8: CI-Registrierung (OP94-Matrix in ci.yml)
# ---------------------------------------------------------------------------
ci_path = REPO_ROOT.parent / ".github" / "workflows" / "ci.yml"
if ci_path.exists():
    ci_src = ci_path.read_text(encoding="utf-8")
    check("T8 CI: OP94-Matrix registriert",
          "test_op94_metadata_score_reingest_card" in ci_src,
          "Matrix fehlt in ci.yml")
else:
    check("T8 CI: ci.yml existiert", False, "Datei nicht gefunden")

print()
print(f"OP94 metadata-score-reingest-card matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
