#!/usr/bin/env python3
# OP87 test matrix: Change-Impact Test Gate (Tester Agent 2.0).
# Nutzer-Anforderung (2026-10-22): 'Ich moechte den Test-Agenten so
# weiterentwickeln, dass er JEDEN Code-Change, der zum Merge
# vorgeschlagen werden soll, so vollstaendig testet, dass die
# Funktionen, der gesamte Workflow sowie die interagierenden Teile der
# Software getestet sind — ich habe den Eindruck, dass ich hier viel
# zu viel Zeit fuer die einfachsten Tests verschwende.'
#
# Das Gate besteht aus drei Teilen:
#   scripts/build_test_impact_map.py  — statische Impact-Map + Zuordnung
#   tests/test_workflow_smoke.py      — Gesamtworkflow (interagierende Teile)
#   scripts/run_change_tests.py       — Diff -> betroffene Matrizen + Gate
# Plus CLI-Wiring (dev_framework test --impact) und CI-Registrierung.
#
# Diese Matrix prueft das Gate selbst — offline, ohne echten git-Diff.
import importlib.util
import json
import os
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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


def load_module(name, rel_path):
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# T1: Artefakte vorhanden + kompilieren
# ---------------------------------------------------------------------------
for rel in ("scripts/build_test_impact_map.py",
            "scripts/run_change_tests.py",
            "tests/test_workflow_smoke.py"):
    p = PROJECT_ROOT / rel
    check(f"T1a exists: {rel}", p.exists())
    if p.exists():
        try:
            py_compile.compile(str(p), doraise=True)
            check(f"T1b compiles: {rel}", True)
        except Exception as exc:
            check(f"T1b compiles: {rel}", False, str(exc))

# ---------------------------------------------------------------------------
# T2: Impact-Map — Bau + Struktur
# ---------------------------------------------------------------------------
bim = load_module("op87_bim", "scripts/build_test_impact_map.py")
impact_map = bim.build_map(PROJECT_ROOT)
check("T2a map has module_to_tests", bool(impact_map.get("module_to_tests")))
check("T2b map has test_assignment", bool(impact_map.get("test_assignment")))
check("T2c map has imports graph", bool(impact_map.get("imports")))
check("T2d map lists js files", len(impact_map.get("js_files", [])) >= 5)

m2t = impact_map["module_to_tests"]
check("T2e services.fusion_calibration hat Matrizen",
      "test_op63_fusion_branch.py" in m2t.get("services.fusion_calibration", []))
check("T2f services.project_ingest hat Matrizen",
      "test_op12_project_upload_ui.py" in m2t.get("services.project_ingest", []))
check("T2g workflow smoke ist NICHT selbst zugeordnet (laeuft immer)",
      "test_workflow_smoke.py" not in
      {t for tests in m2t.values() for t in tests})

# covers-Tag gewinnt vor Heuristik
with tempfile.TemporaryDirectory() as td:
    tdir = Path(td)
    (tdir / "tests").mkdir()
    tf = tdir / "tests" / "test_op99_tagged.py"
    tf.write_text("# covers: services.fusion_calibration\nimport os\n",
                  encoding="utf-8")
    mods, strategy = bim.covers_for_test(PROJECT_ROOT, tf)
    check("T2h covers-Tag gewinnt", strategy == "tag"
          and mods == ["services.fusion_calibration"],
          f"strategy={strategy} mods={mods}")

# ---------------------------------------------------------------------------
# T3: Runner — Diff-Parsing + Matrix-Auswahl (ohne echten git-Aufruf)
# ---------------------------------------------------------------------------
rct = load_module("op87_rct", "scripts/run_change_tests.py")

# file_to_module mapping
check("T3a django_project/api/project_views.py -> api.project_views",
      rct.file_to_module("django_project/api/project_views.py")
      == "api.project_views")
check("T3b services/x.py -> services.x",
      rct.file_to_module("services/fusion_calibration.py")
      == "services.fusion_calibration")
check("T3c .js -> None (kein Modul)",
      rct.file_to_module("django_project/static/js/main.js") is None)

# Auswahl: direkter Treffer
matrices, reasons, js, mods = rct.select_matrices(
    impact_map, ["services/fusion_calibration.py"])
check("T3d direkter Change waehlt fusion-Matrizen",
      "test_op63_fusion_branch.py" in matrices
      and "test_op63_st3_calibration.py" in matrices,
      f"got {matrices[:5]}")
check("T3e nicht betroffene Matrix NICHT gewaehlt",
      "test_op48_i18n.py" not in matrices)

# Auswahl: transitiv — Modul, das fusion_calibration importiert, sodass
# dessen eigene Matrizen (z. B. test_op63_st3_calibration) mit auswaehlt.
importers = [m for m, imps in impact_map["imports"].items()
             if "services.fusion_calibration" in imps]
if importers:
    imp = importers[0].replace(".", "/") + ".py"
    m2, _, _, _ = rct.select_matrices(impact_map, [imp])
    expected = set(m2t.get(importers[0], []))
    check("T3f transitiv: Importeur-Change waehlt dessen Matrizen",
          expected and expected.issubset(set(m2)),
          f"importer={imp} expected={sorted(expected)[:3]} got={m2[:5]}")
else:
    check("T3f transitiv: Importeur-Change waehlt dessen Matrizen",
          True, "kein Importeur gefunden (Map zu duenn?)")

# JS-Change -> kein Modul, aber js-Liste
m3, _, js3, mods3 = rct.select_matrices(
    impact_map, ["django_project/static/js/main.js"])
check("T3g JS-Change -> node --check Liste, keine falschen Matrizen",
      js3 == ["django_project/static/js/main.js"] and mods3 == [])

# Test-Datei geaendert -> laeuft selbst
m4, _, _, _ = rct.select_matrices(
    impact_map, ["tests/test_op63_fusion_branch.py"])
check("T3h geaenderte Testmatrix laeuft direkt",
      "test_op63_fusion_branch.py" in m4)

# leere Auswahl -> nur Smoke (wird vom Runner angehaengt, hier nackt leer)
m5, _, _, _ = rct.select_matrices(impact_map, ["README.md"])
check("T3i Doku-Only-Change -> keine Matrix (Smoke haengt der Runner an)",
      m5 == [], f"got {m5}")

# ---------------------------------------------------------------------------
# T4: Runner — echten Diff gegen HEAD (intakes Repo, uncommitted changes)
# ---------------------------------------------------------------------------
r = subprocess.run(
    [sys.executable, str(PROJECT_ROOT / "scripts" / "run_change_tests.py"),
     "--base", "HEAD"],
    capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=900)
check("T4a gate laeuft gegen HEAD (Exit 0 bei gruenem Tree)",
      r.returncode == 0,
      f"rc={r.returncode} out={r.stdout[-300:]} err={r.stderr[-300:]}")
check("T4b gate meldet GREEN",
      "gate result: GREEN" in r.stdout, r.stdout[-200:])
check("T4c workflow smoke ist im Gate enthalten",
      "test_workflow_smoke.py" in r.stdout)

# ---------------------------------------------------------------------------
# T5: Workflow-Smoke — Vertrag (Ehrlichkeit, kein Fake)
# ---------------------------------------------------------------------------
smoke_src = (PROJECT_ROOT / "tests" / "test_workflow_smoke.py") \
    .read_text(encoding="utf-8")
check("T5a smoke deckt Upload ab", "/api/files/upload/" in smoke_src)
check("T5b smoke deckt Projekt-Anlage ab", "/api/projects/create/" in smoke_src)
check("T5c smoke deckt Release/Crew ab", "/release/" in smoke_src
      and "crew-status" in smoke_src)
check("T5d smoke deckt Chatbot ab (degraded ehrlich akzeptiert)",
      "/api/chatbot/message/" in smoke_src and "degraded" in smoke_src)
check("T5e smoke hat Cleanup (kein Dead End)", "/delete/" in smoke_src)
check("T5f smoke nutzt Django-Testclient (loopback, kein externer Dienst)",
      "django.test" in smoke_src and "Client" in smoke_src)

# ---------------------------------------------------------------------------
# T6: CLI-Wiring — dev_framework test --impact
# ---------------------------------------------------------------------------
cli_src = (PROJECT_ROOT / "dev_framework" / "cli.py").read_text(encoding="utf-8")
check("T6a CLI kennt --impact", "'--impact'" in cli_src)
check("T6b CLI kennt --base", "'--base'" in cli_src)
check("T6c CLI delegiert an run_change_tests.py",
      "run_change_tests.py" in cli_src)

r = subprocess.run(
    [sys.executable, "-m", "dev_framework", "test", "--impact",
     "--base", "HEAD"],
    capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=900)
check("T6d `dev_framework test --impact` laeuft gruen",
      r.returncode == 0 and "gate result: GREEN" in r.stdout,
      f"rc={r.returncode} out={r.stdout[-300:]} err={r.stderr[-300:]}")

# ---------------------------------------------------------------------------
# T7: CI-Registrierung + Roadmap/TASK
# ---------------------------------------------------------------------------
ci_path = PROJECT_ROOT.parent / ".github" / "workflows" / "ci.yml"
ci_src = ci_path.read_text(encoding="utf-8") if ci_path.exists() else ""
check("T7a CI-Job change-impact registriert", "change-impact:" in ci_src)
check("T7b CI-Job laeuft das Gate gegen origin/main",
      "run_change_tests.py --base origin/main" in ci_src)
check("T7c CI-Job ist PR-only (if pull_request)",
      "if: github.event_name == 'pull_request'" in ci_src)
check("T7d CI-Vollmatrix bleibt als Backstop erhalten",
      "test-matrices:" in ci_src)
check("T7e OP87-Matrix selbst in CI (change-impact Job)",
      "test_op87_change_impact_gate.py" in ci_src)

try:
    import yaml
    yaml.safe_load(ci_src)
    check("T7f ci.yml ist valides YAML", True)
except Exception as exc:
    check("T7f ci.yml ist valides YAML", False, str(exc))

task_src = (PROJECT_ROOT / "TASK.md").read_text(encoding="utf-8")
check("T7g TASK.md traegt OP87 als Current Task",
      "Current Task: OP87" in task_src)
roadmap_src = (PROJECT_ROOT.parent / "REPOSITORY_ALIGNMENT_AND_ROADMAP.md") \
    .read_text(encoding="utf-8")
check("T7h Roadmap traegt OP87", "### OP87" in roadmap_src)

# ---------------------------------------------------------------------------
# T8: Impact-Map ist gitignored (generiert, kein Check-in-Noise)
# ---------------------------------------------------------------------------
gitignore_src = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
check("T8a tests/.impact_map.json gitignored",
      "tests/.impact_map.json" in gitignore_src)

# ---------------------------------------------------------------------------
# T9: Anti-Code-Creep — bestehende Matrizen unberuehrt
# ---------------------------------------------------------------------------
r = subprocess.run(
    ["git", "diff", "--name-only", "HEAD", "--", "tests/"],
    capture_output=True, text=True,
    cwd=str(PROJECT_ROOT.parent), timeout=60)
changed_tests = [l for l in r.stdout.splitlines() if l.strip()]
allowed_new = {"NIR_Intelligence-main/tests/test_workflow_smoke.py",
               "NIR_Intelligence-main/tests/test_op87_change_impact_gate.py"}
unexpected = [f for f in changed_tests
              if f not in allowed_new
              and not f.endswith(".impact_map.json")]
check("T9a keine bestehende Testmatrix veraendert",
      not unexpected, f"unexpected: {unexpected}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f"OP87 change-impact gate matrix: {PASS} passed, {FAIL} failed")
if FAILED:
    print("FAILED checks:", FAILED)
sys.exit(1 if FAIL else 0)
