# covers: api/project_views.py
# OP93 test matrix: Metadaten-Speichern hängt endlos ("Speichern..." stoppt nie).
# Befund aus Nutzer-Feedback (2026-10-23, nach OP92-Merge): Metadaten im
# Editor ergänzt + "Speichern" gedrückt -> Button bleibt auf "Speichern...".
# Root-Cause (lokal reproduziert): ProjectMetadataView.post rief
# build_preparation_report SYNCHRON im Request. KI-Pässe blocken bei
# hängendem Ollama: _ki_forward_questions (2 Topics x 120s) +
# _ki_relevance_pass (120s) + _ki_metadata_pass (Nx120s) = ~18 min.
# NIR_INGEST_LLM=skip schützte nur _ki_metadata_pass.
# Fix: (1) Metadaten-Save wird async (Thread + preparing: True, OP78-Muster);
#      (2) NIR_INGEST_LLM=skip-Guard in _ki_forward_questions +
#      _ki_relevance_pass; (3) JS: Client-Timeout + Reload nach Erfolg.
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
PROJECT_VIEWS = REPO_ROOT / "django_project" / "api" / "project_views.py"
INGEST = REPO_ROOT / "services" / "project_ingest.py"
REPORT_TPL = (REPO_ROOT / "django_project" / "templates"
              / "project_report.html")

views_src = PROJECT_VIEWS.read_text(encoding="utf-8")
ingest_src = INGEST.read_text(encoding="utf-8")
report_src = REPORT_TPL.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# T1: ProjectMetadataView.post — async (kein sync build_preparation_report)
# ---------------------------------------------------------------------------
import re as _re  # noqa: E402

# Extrahiere den Metadaten-Pfad (nach metadata_overrides save, vor Response)
meta_view = _re.search(
    r"class ProjectMetadataView.*?(?=\nclass )", views_src, _re.DOTALL)
check("T1a ProjectMetadataView class found", meta_view is not None)
if meta_view:
    mv = meta_view.group(0)
    # Der Metadaten-Pfad (nach 'metadata_overrides') darf KEINEN sync call haben
    meta_path = mv[mv.find("metadata_overrides = overrides"):]
    check("T1b Metadaten-Pfad: kein sync 'report = build_preparation_report(project)'",
          "report = build_preparation_report(project)" not in meta_path,
          "sync call noch vorhanden — Request blockt bei hängendem Ollama")
    check("T1c Metadaten-Pfad: Thread(target=_prepare) gestartet",
          "Thread(target=_prepare" in meta_path)
    check("T1d Metadaten-Pfad: Antwort enthält 'preparing': True",
          "'preparing': True" in meta_path)
    check("T1e Metadaten-Pfad: Report wird geleert (datasets entfernt)",
          "preserved = {'user_options': user_options}" in meta_path)
    check("T1f Metadaten-Pfad: fusion-Sektion erhalten (OP82)",
          "if report.get('fusion'):" in meta_path)
    check("T1g Metadaten-Pfad: _prepare fängt Exception + setzt preparation_error",
          "rep['preparation_error'] = str(exc)" in meta_path)

# ---------------------------------------------------------------------------
# T2: NIR_INGEST_LLM=skip-Guard in _ki_forward_questions + _ki_relevance_pass
# ---------------------------------------------------------------------------
fwd_fn = _re.search(
    r"def _ki_forward_questions\(.*?(?=\ndef )", ingest_src, _re.DOTALL)
check("T2a _ki_forward_questions: NIR_INGEST_LLM=skip-Guard vorhanden",
      fwd_fn is not None and "NIR_INGEST_LLM" in fwd_fn.group(0)
      and "skip" in fwd_fn.group(0),
      "Guard fehlt — Pass blockt auch mit skip")

rel_fn = _re.search(
    r"def _ki_relevance_pass\(.*?(?=\ndef )", ingest_src, _re.DOTALL)
check("T2b _ki_relevance_pass: NIR_INGEST_LLM=skip-Guard vorhanden",
      rel_fn is not None and "NIR_INGEST_LLM" in rel_fn.group(0)
      and "skip" in rel_fn.group(0),
      "Guard fehlt — Pass blockt auch mit skip")

# Guard muss VOR dem try/except stehen (früher Return). try_pos = erste
# 'try:' NACH dem Docstring (sonst matcht 'try:' im Docstring-Text).
def _guard_before_try(fn_text):
    doc_end = fn_text.find('"""', fn_text.find('"""') + 3)
    body = fn_text[doc_end:] if doc_end > 0 else fn_text
    guard_pos = body.find("NIR_INGEST_LLM")
    try_pos = body.find("\n    try:")
    return 0 < guard_pos < try_pos, guard_pos, try_pos

if fwd_fn:
    ok, gp, tp = _guard_before_try(fwd_fn.group(0))
    check("T2c _ki_forward_questions: Guard VOR try (früher Return)",
          ok, f"guard_pos={gp}, try_pos={tp}")
if rel_fn:
    ok, gp, tp = _guard_before_try(rel_fn.group(0))
    check("T2d _ki_relevance_pass: Guard VOR try (früher Return)",
          ok, f"guard_pos={gp}, try_pos={tp}")

# ---------------------------------------------------------------------------
# T3: Live — _ki_forward_questions + _ki_relevance_pass mit skip = sofort
# ---------------------------------------------------------------------------
os.environ["NIR_INGEST_LLM"] = "skip"
os.environ["OLLAMA_URL"] = "http://127.0.0.1:1"  # nicht erreichbar
try:
    from services.project_ingest import (_ki_forward_questions,  # noqa: E402
                                        _ki_relevance_pass)
    entry = {"file_name": "t.csv", "metadata": {"instrument_type": "NIR"},
             "open_questions": []}
    standards = {"ISO 12099": ["integration_time", "serial_number"]}
    t0 = time.time()
    _ki_forward_questions(entry, standards)
    t1 = time.time()
    check("T3a _ki_forward_questions mit skip: < 1s (kein LLM-Call)",
          t1 - t0 < 1.0, f"{t1-t0:.2f}s")
    check("T3b _ki_forward_questions mit skip: keine KI-Frage hinzugefuegt",
          not any("KI-Frage zum Thema" in q
                  for q in entry.get("open_questions", [])
                  if "KI-Frage zum Thema" in q and "deterministisch" not in q),
          str(entry.get("open_questions", []))[:100])

    assessment = {"metadata_fields": ["instrument_type"],
                  "missing_recommended_fields": ["integration_time"]}
    t0 = time.time()
    result = _ki_relevance_pass(assessment, [entry])
    t1 = time.time()
    check("T3c _ki_relevance_pass mit skip: < 1s (kein LLM-Call)",
          t1 - t0 < 1.0, f"{t1-t0:.2f}s")
    check("T3d _ki_relevance_pass mit skip: None + ehrlicher Status",
          result is None
          and "skip" in assessment.get("ki_relevance_status", ""),
          str(assessment.get("ki_relevance_status"))[:80])
finally:
    os.environ.pop("NIR_INGEST_LLM", None)

# ---------------------------------------------------------------------------
# T4: Live — Metadaten-POST antwortet sofort (auch wenn Ollama hängt)
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.test.runner import DiscoverRunner  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402

setup_test_environment()
runner = DiscoverRunner(verbosity=0)
old_config = runner.setup_databases()
try:
    from core.models import User, GenericFile, AnalysisProject  # noqa: E402
    from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
    user, _ = User.objects.get_or_create(username="op93user")
    if not user.check_password("pw12345!"):
        user.set_password("pw12345!")
        user.save()

    f = GenericFile.objects.create(
        user=user, name="op93.csv",
        original_filename="op93.csv",
        file=SimpleUploadedFile("op93.csv", b"wl\tint\n400\t1.0\n500\t2.0\n"),
        file_size=20)
    project = AnalysisProject.objects.create(user=user, name="op93-proj")
    project.files.add(f)
    project.preparation_report = {
        "datasets": [{"file_name": "op93.csv", "file_id": str(f.id)}],
        "user_options": {"analysis_wishes": "test"},
        "fusion": {"source_projects": ["a", "b"]},
    }
    project.save(update_fields=["preparation_report"])

    client = Client()
    client.login(username="op93user", password="pw12345!")

    # Metadaten-POST: muss sofort antworten (< 5s), auch ohne Ollama
    os.environ["OLLAMA_URL"] = "http://127.0.0.1:1"  # nicht erreichbar
    os.environ.pop("NIR_INGEST_LLM", None)  # KI aktiv (schlimmster Fall)
    t0 = time.time()
    resp = client.post(
        f"/projects/{project.id}/metadata/",
        data='{"metadata": {"%s": {"operator_name": "Martin"}}}' % f.id,
        content_type="application/json")
    t1 = time.time()
    body = resp.json()
    check("T4a Metadaten-POST antwortet < 5s (async, kein sync-Hang)",
          t1 - t0 < 5.0, f"{t1-t0:.2f}s")
    check("T4b Metadaten-POST: success=True + preparing=True",
          resp.status_code == 200 and body.get("success") is True
          and body.get("preparing") is True, str(body)[:150])
    check("T4c Metadaten-POST: report_url vorhanden",
          body.get("report_url") == f"/projects/{project.id}/", str(body)[:100])

    # Report geleert: datasets entfernt, user_options + fusion erhalten
    project.refresh_from_db()
    rep = project.preparation_report or {}
    check("T4d Report geleert: datasets entfernt",
          "datasets" not in rep, f"keys={list(rep.keys())}")
    check("T4e Report: user_options erhalten (OP77b)",
          rep.get("user_options", {}).get("analysis_wishes") == "test",
          str(rep.get("user_options"))[:80])
    check("T4f Report: fusion erhalten (OP82)",
          rep.get("fusion", {}).get("source_projects") == ["a", "b"],
          str(rep.get("fusion"))[:80])

    # metadata_overrides gespeichert
    project.refresh_from_db()
    check("T4g metadata_overrides gespeichert",
          project.metadata_overrides.get(str(f.id), {}).get("operator_name")
          == "Martin", str(project.metadata_overrides)[:100])

    # Hintergrund-Thread läuft — warte bis ready oder error (max 30s)
    deadline = time.time() + 30
    ready = False
    last_body = {}
    while time.time() < deadline:
        r = client.get(f"/api/projects/create/{project.id}/status/").json()
        last_body = r
        if r.get("ready") or r.get("error"):
            ready = r.get("ready")
            break
        time.sleep(0.5)
    check("T4h Hintergrund-Rebuild terminiert (ready oder error)",
          ready is True or last_body.get("error"),
          f"ready={ready} body={str(last_body)[:150]}")
finally:
    os.environ.pop("OLLAMA_URL", None)
    runner.teardown_databases(old_config)

# ---------------------------------------------------------------------------
# T5: Template-JS — kein endloses "Speichern..."
# ---------------------------------------------------------------------------
check("T5a Template: AbortController + 120s Client-Timeout",
      "AbortController" in report_src
      and "120000" in report_src)
check("T5b Template: d.preparing-Zweig (async-Antwort) behandelt",
      "d.preparing" in report_src
      and "Aufbereitung läuft im Hintergrund" in report_src)
check("T5c Template: Button wird bei Fehler reaktiviert",
      "saveBtn.disabled = false" in report_src)
check("T5d Template: Reload nach Erfolg (900ms)",
      "setTimeout(function(){ location.reload(); }, 900)" in report_src)

# ---------------------------------------------------------------------------
# T6: py_compile aller geaenderten Dateien
# ---------------------------------------------------------------------------
import py_compile  # noqa: E402
for label, path in [
    ("project_views.py", PROJECT_VIEWS),
    ("project_ingest.py", INGEST),
]:
    try:
        py_compile.compile(str(path), doraise=True)
        check(f"T6 py_compile {label}", True)
    except py_compile.PyCompileError as exc:
        check(f"T6 py_compile {label}", False, str(exc))

print(f"\nOP93 metadata-save-hang matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
