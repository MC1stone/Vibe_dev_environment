#!/usr/bin/env python3
# OP88 test matrix: Review & Optimierung der uebrigen Framework-Agenten.
# Nutzer-Auftrag (2026-10-22): 'Bitte ueberpruefe die anderen Agenten ebenso
# und verbessere/optimiere wo moeglich.' Sechs Befunde aus dem Review des
# dev_framework (tester, quality, validator, generator, docs, server, cli)
# + agents-Registry, jeweils mit kleinste-korrektem Fix.
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


def run_cli(args, timeout=300):
    return subprocess.run(
        [sys.executable, "-m", "dev_framework"] + args,
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=timeout,
    )


# ---------------------------------------------------------------------------
# T1: Geaenderte Dateien kompilieren
# ---------------------------------------------------------------------------
for rel in ("agents/__init__.py",
            "dev_framework/tester.py",
            "dev_framework/validator.py",
            "dev_framework/quality.py",
            "dev_framework/docs.py",
            "dev_framework/cli.py"):
    p = PROJECT_ROOT / rel
    try:
        py_compile.compile(str(p), doraise=True)
        check(f"T1 compiles: {rel}", True)
    except Exception as exc:
        check(f"T1 compiles: {rel}", False, str(exc))

# ---------------------------------------------------------------------------
# T2: Registry vollstaendig (Fix 1)
# ---------------------------------------------------------------------------
from agents import AGENT_REGISTRY  # noqa: E402

agent_files = {p.stem for p in (PROJECT_ROOT / "agents").glob("*_agent.py")}
agent_files.discard("base_agent")
registry_keys = set(AGENT_REGISTRY.keys())

missing = agent_files - registry_keys
check("T2a keine Agent-Datei fehlt in der Registry", not missing,
      f"missing: {sorted(missing)}")
# nir_analysis_crew ist eine Crew, kein *_agent.py — erwartete Zusatz-Quelle
check("T2b Registry enthaelt genau die Dateien + nir_analysis_crew",
      registry_keys - agent_files == {"nir_analysis_crew"},
      f"extra: {sorted(registry_keys - agent_files)}")
check("T2c chatbot_agent in Registry", "chatbot_agent" in registry_keys)
check("T2d ilias_course_agent in Registry", "ilias_course_agent" in registry_keys)
check("T2e sensor_agent in Registry", "sensor_agent" in registry_keys)
check("T2f Registry-Klassen sind importierbar",
      all(callable(c) for c in AGENT_REGISTRY.values()))
check("T2g Registry-Count stimmt (34)", len(registry_keys) == 34,
      f"got {len(registry_keys)}")

# ---------------------------------------------------------------------------
# T3: Tester — ehrlicher Flat-Matrix-Fallback (Fix 2)
# ---------------------------------------------------------------------------
from dev_framework.tester import AgentTester  # noqa: E402

tester = AgentTester(verbose=False)
flat = sorted(tester.tests_dir.glob("test_*.py"))
check("T3a flache Matrix wird erkannt (>100 Matrizen)", len(flat) > 100,
      f"got {len(flat)}")

# Strukturelle Pruefung ohne Volllauf: run_all_tests muss den flat-Pfad waehlen
tester_src = (PROJECT_ROOT / "dev_framework" / "tester.py").read_text(encoding="utf-8")
check("T3b Tester kennt flat-matrix Fallback", "_run_flat_matrix" in tester_src)
check("T3c Tester prueft structured dirs vor flat", "structured" in tester_src)
check("T3d Tester-Imports oben (PEP 8, kein Import am Dateiende)",
      "import time" in tester_src.split("\n")[11]
      and not tester_src.rstrip().endswith("import re"))
check("T3e Tester meldet matrices_failed bei Fehler",
      "matrices_failed" in tester_src)

# Mini-Lauf: eine einzelne kleine Matrix ueber den Fallback-Mechanismus.
# test_calibration_metrics.py nutzt pytest-Style ('All 3 tests passed.') —
# der Parser erkennt 'N passed' in beiden Repo-Konventionen.
mini = PROJECT_ROOT / "tests" / "test_calibration_metrics.py"
if mini.exists():
    res = tester._run_flat_matrix([mini])
    check("T3f Fallback laeuft eine Matrix ehrlich (rc 0, kein Fake-Fehler)",
          res["mode"] == "flat-matrix" and res["matrices_total"] == 1
          and res["success"] is True and res["matrices_failed"] == [],
          f"res={ {k: res[k] for k in ('mode','matrices_total','success','matrices_failed')} }")
    # Negativ-Test: kaputte Matrix muss ehrlich fehlschlagen
    with tempfile.TemporaryDirectory() as td:
        broken = Path(td) / "test_broken.py"
        broken.write_text("import sys; print('RESULT: 0 passed, 1 failed'); "
                          "sys.exit(1)\n", encoding="utf-8")
        res2 = tester._run_flat_matrix([broken])
    check("T3g Fallback meldet Fehler ehrlich (kein silent success)",
          res2["success"] is False and res2["matrices_failed"] == ["test_broken.py"],
          f"res={ {k: res2[k] for k in ('success','matrices_failed')} }")
    # Parser-Robustheit: verschachtelte Fremd-Ausgabe ('692 info(s)') darf
    # nicht als 'failed' fehlgezaehlt werden (Regression aus dem Live-Lauf)
    with tempfile.TemporaryDirectory() as td:
        nested = Path(td) / "test_nested.py"
        nested.write_text(
            "print('inner tool: 692 info(s)')\n"
            "print('RESULT: 45 passed, 0 failed')\n"
            "import sys; sys.exit(0)\n", encoding="utf-8")
        res3 = tester._run_flat_matrix([nested])
    check("T3h verschachtelte Ausgabe wird nicht als failed fehlgezaehlt",
          res3["passed"] == 45 and res3["failed"] == 0 and res3["success"] is True,
          f"res={ {k: res3[k] for k in ('passed','failed','success')} }")
else:
    check("T3f Fallback laeuft eine Matrix ehrlich (rc 0, kein Fake-Fehler)",
          False, "test_calibration_metrics.py missing")
    check("T3g Fallback meldet Fehler ehrlich (kein silent success)",
          False, "test_calibration_metrics.py missing")
    check("T3h verschachtelte Ausgabe wird nicht als failed fehlgezaehlt",
          False, "test_calibration_metrics.py missing")

# OP88: --agent filtert per echtem Import (nicht Klassenname allein).
# Auswahl separat testen (ohne Lauf — sonst Rekursion, da diese Matrix
# selbst 'CalibrationAgent' im Source nennt).
agent_files = [p.name for p in tester._select_agent_matrices("CalibrationAgent")]
check("T3i --agent filtert auf echte Importe (nur 4 Matrizen)",
      len(agent_files) == 4
      and "test_calibration_metrics.py" in agent_files
      and "test_agenten_journal.py" in agent_files,
      f"got {agent_files}")
check("T3j --agent ohne Treffer ist ehrlich (keine 48-Matrix-Flut)",
      "test_op49_sensor_diy.py" not in agent_files)

# ---------------------------------------------------------------------------
# T4: Validator — keine False-Positives mehr (Fix 3)
# ---------------------------------------------------------------------------
from dev_framework.validator import AgentValidator  # noqa: E402

v = AgentValidator(strict=False)
r_all = v.validate_all()
py007 = [i for i in r_all.warnings if i.code == "PY_007"]
check("T4a keine PY_007 false positives mehr (BaseAgent-Vererbung)",
      len(py007) == 0, f"got {len(py007)}")

mand_warn = [i for i in r_all.warnings if i.code == "AGENT_003"]
mand_info = [i for i in r_all.info if i.code == "AGENT_003"]
check("T4b Mandatory-File-Check liefert keine 99x Warning-Spam",
      len(mand_warn) == 0, f"got {len(mand_warn)} warnings")
check("T4c Mandatory-File-Hinweis ist info (Session-Ebene erklaert)",
      len(mand_info) > 0 and all("Session-Ebene" in i.message for i in mand_info))

# Einzel-Validator: korrekter Pfad (mit _agent suffix)
r_one = v.validate_agent("CalibrationAgent")
check("T4d validate_agent findet Datei (kein toter Pfad)",
      r_one.valid or not any(i.code == "AGENT_001" for i in r_one.errors))
check("T4e validate_all bleibt valid (nur warnings)", r_all.valid)

# ---------------------------------------------------------------------------
# T5: Quality — skipped statt 692 Errors, Exit-Code ehrlich (Fix 4)
# ---------------------------------------------------------------------------
from dev_framework.quality import QualityEnforcer, count_by_severity  # noqa: E402

qe = QualityEnforcer()
# Einzelne Datei pruefen (schnell, keine Vollmatrix)
sample = PROJECT_ROOT / "agents" / "base_agent.py"
qr = qe._check_file(sample)
skipped = qr.skipped_tools
counts = count_by_severity(qr)
check("T5a fehlende Tools als skipped gemeldet",
      len(skipped) > 0, f"skipped={skipped}")
check("T5b skipped Tools erzeugen keine error-Issues",
      counts["error"] == 0, f"errors={counts['error']}")
check("T5c skipped Tools erzeugen info-Issues (degraded ehrlich)",
      counts["info"] > 0 and any("skipped" in i.message for i in qr.issues))
check("T5d Datei-Check success bei nur skipped (kein Fake-Fehler)",
      qr.success is True)

# CLI: quality --all --check exit-Code ehrlich
r = run_cli(["quality", "--all", "--check"], timeout=600)
check("T5e quality --all --check exit 0 bei nur skipped",
      r.returncode == 0, f"rc={r.returncode} err={r.stderr[-200:]}")
check("T5f CLI meldet skipped ehrlich",
      "Skipped tools" in r.stdout + r.stderr)
check("T5g CLI meldet passed (nicht 692 failed)",
      "Quality check passed" in r.stdout + r.stderr)

# ---------------------------------------------------------------------------
# T6: Docs — relative_to-Crash fix + CLI docs-Alias (Fix 5)
# ---------------------------------------------------------------------------
from dev_framework.docs import DocsGenerator, _rel_path  # noqa: E402

with tempfile.TemporaryDirectory() as td:
    outside = Path(td) / "sub" / "file.md"
    outside.parent.mkdir(parents=True)
    outside.write_text("x", encoding="utf-8")
    res = _rel_path(outside, PROJECT_ROOT)
    check("T6a _rel_path faellt auf absoluten Pfad zurueck (kein Crash)",
          res == str(outside), f"got {res}")
    inside = PROJECT_ROOT / "docs" / "x.md"
    res2 = _rel_path(inside, PROJECT_ROOT)
    check("T6b _rel_path liefert relativ wenn moeglich",
          res2 == "docs/x.md", f"got {res2}")

# DocsGenerator mit docs_dir ausserhalb project_root — vor OP88: ValueError
with tempfile.TemporaryDirectory() as td:
    g = DocsGenerator()
    g.docs_dir = Path(td)
    r = g.generate_agent_docs("ChatbotAgent")
    check("T6c docs generation mit externem docs_dir ohne Crash",
          r.success is True, f"error={r.error}")

# CLI: docs als eigener Subcommand
r = run_cli(["docs", "--agent", "ChatbotAgent"], timeout=120)
check("T6d `dev_framework docs --agent X` laeuft (Alias)",
      r.returncode == 0 and "Documentation generated" in r.stdout + r.stderr,
      f"rc={r.returncode} out={r.stdout[-200:]} err={r.stderr[-200:]}")
# cleanup generated doc
for f in (PROJECT_ROOT / "docs" / "agents").glob("chatbot_agent.md"):
    f.unlink()

# generate docs weiterhin OK (kein Alias-Regression)
r = run_cli(["generate", "docs", "--agent", "ChatbotAgent"], timeout=120)
check("T6e `generate docs --agent X` weiterhin OK",
      r.returncode == 0, f"rc={r.returncode}")
for f in (PROJECT_ROOT / "docs" / "agents").glob("chatbot_agent.md"):
    f.unlink()

# ---------------------------------------------------------------------------
# T7: CLI insgesamt — validate/test/info laufen ohne Crash
# ---------------------------------------------------------------------------
r = run_cli(["validate"], timeout=300)
check("T7a validate exit 0 (nur warnings)",
      r.returncode == 0 and "Validation passed" in r.stdout + r.stderr,
      f"rc={r.returncode}")

r = run_cli(["info"], timeout=60)
check("T7b info exit 0", r.returncode == 0, f"rc={r.returncode}")

# ---------------------------------------------------------------------------
# T8: Doc-Drift — PRODUCTION_READINESS Nachtrag (Fix 6)
# ---------------------------------------------------------------------------
pr = (PROJECT_ROOT / "PRODUCTION_READINESS.md").read_text(encoding="utf-8")
check("T8a PRODUCTION_READINESS traegt OP88-Nachtrag (34 agents)",
      "34 agents total" in pr and "OP88" in pr)
check("T8b Nachtrag nennt die 3 nachgetragenen Agenten",
      "chatbot_agent" in pr and "ilias_course_agent" in pr
      and "sensor_agent" in pr)

# ---------------------------------------------------------------------------
# T9: Steuerdateien — OP88 eingetragen
# ---------------------------------------------------------------------------
task_src = (PROJECT_ROOT / "TASK.md").read_text(encoding="utf-8")
check("T9a TASK.md traegt OP88 als Current Task",
      "Current Task: OP88" in task_src)
roadmap_src = (PROJECT_ROOT.parent / "REPOSITORY_ALIGNMENT_AND_ROADMAP.md") \
    .read_text(encoding="utf-8")
check("T9b Roadmap traegt OP88", "### OP88" in roadmap_src)

# ---------------------------------------------------------------------------
# T10: CI-Registrierung
# ---------------------------------------------------------------------------
ci_src = (PROJECT_ROOT.parent / ".github" / "workflows" / "ci.yml") \
    .read_text(encoding="utf-8")
check("T10a OP88-Matrix in CI registriert",
      "test_op88_dev_framework_review.py" in ci_src)

# ---------------------------------------------------------------------------
# T11: Anti-Code-Creep — keine produktiven Agent-Dateien veraendert
# ---------------------------------------------------------------------------
r = subprocess.run(
    ["git", "diff", "--name-only", "HEAD", "--", "agents/"],
    capture_output=True, text=True, cwd=str(PROJECT_ROOT.parent), timeout=60)
changed = [l for l in r.stdout.splitlines() if l.strip()]
allowed = {"NIR_Intelligence-main/agents/__init__.py"}
unexpected = [f for f in changed if f not in allowed]
check("T11a nur agents/__init__.py geaendert (keine Agent-Implementierung)",
      not unexpected, f"unexpected: {unexpected}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f"OP88 dev-framework review matrix: {PASS} passed, {FAIL} failed")
if FAILED:
    print("FAILED checks:", FAILED)
sys.exit(1 if FAIL else 0)
