#!/usr/bin/env python3
"""OP89: Change-Impact Test Gate — testet jeden Code-Change vollstaendig.

Nutzer-Anforderung (2026-10-22): Der Tester Agent soll jeden zum Merge
vorgeschlagenen Code-Change testen — Funktionen, Gesamtworkflow und
interagierende Teile — ohne manuelle Testauswahl und ohne 85 einzelne
Python-Prozesse.

Ablauf:
  1. git diff --name-only <base>...HEAD  -> geaenderte Dateien
  2. Impact-Map (tests/.impact_map.json, rebuild falls älter/fehlend)
     -> betroffene Testmatrizen (direkt + transitiv via Import-Graph)
  3. immer dazu: tests/test_workflow_smoke.py (Gesamtworkflow),
     manage.py check (Django-Systemcheck)
  4. geaenderte JS-Dateien: node --check
  5. geaenderte Python-Dateien: py_compile (schneller Syntax-Smoke)
  6. Alle Matrizen in EINEM Prozess (subprocess je Matrix, aber ein
     Runner, eine Zusammenfassung, ein Exit-Code).

CI-Modus: --base origin/main (Merge-Base via `git merge-base`).
Lokal:    --base main oder --base HEAD~1.
--full:   komplette Matrix (Backstop, entspricht der CI-Vollmatrix).

Exit-Code: 0 = alle Schritte gruen, 1 = mindestens ein Fehler.
Keine neuen Abhaengigkeiten (stdlib + git + node fuer JS).
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMPACT_MAP = PROJECT_ROOT / "tests" / ".impact_map.json"
SMOKE_TEST = "test_workflow_smoke.py"


def run(cmd, cwd=PROJECT_ROOT, timeout=600):
    """Run a command, return (returncode, stdout+stderr)."""
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT after {timeout}s: {' '.join(map(str, cmd))}"
    except FileNotFoundError as exc:
        return 127, f"command not found: {exc}"


def changed_files(base):
    """git diff --name-only base...HEAD (merge-base), repo-relative paths."""
    rc, out = run(["git", "merge-base", base, "HEAD"])
    if rc != 0:
        # fallback: direct diff without merge-base (e.g. base == HEAD~1)
        rc, out = run(["git", "diff", "--name-only", base])
        if rc != 0:
            return None, out
        base_ref = base
    else:
        base_ref = out.strip()
        rc, out = run(["git", "diff", "--name-only", f"{base_ref}...HEAD"])
        if rc != 0:
            return None, out
    files = [line.strip() for line in out.splitlines() if line.strip()]
    # diff is run from repo root? PROJECT_ROOT is NIR_Intelligence-main,
    # the git repo root is one level up — normalize to project-relative.
    repo_root_rc, repo_root_out = run(["git", "rev-parse", "--show-toplevel"])
    if repo_root_rc == 0:
        repo_root = Path(repo_root_out.strip()).resolve()
        rel = []
        for f in files:
            p = (repo_root / f).resolve()
            try:
                rel.append(str(p.relative_to(PROJECT_ROOT)))
            except ValueError:
                rel.append(f)  # outside project root — keep as-is
        return rel, ""
    return files, ""


def load_impact_map():
    if not IMPACT_MAP.exists():
        rc, out = run([sys.executable,
                       str(PROJECT_ROOT / "scripts" / "build_test_impact_map.py"),
                       "--quiet"])
        if rc != 0:
            return None, f"impact map build failed: {out[-500:]}"
    try:
        return json.loads(IMPACT_MAP.read_text(encoding="utf-8")), ""
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, f"impact map unreadable: {exc}"


def file_to_module(rel_path):
    """django_project/api/project_views.py -> api.project_views (or None)."""
    p = Path(rel_path)
    if p.suffix != ".py":
        return None
    parts = list(p.with_suffix("").parts)
    if parts and parts[0] == "django_project":
        parts = parts[1:]
    if not parts:
        return None
    return ".".join(parts)


def select_matrices(impact_map, changed):
    """Betroffene Testmatrizen: direkte Abdeckung + transitiv (Importe)."""
    module_to_tests = impact_map.get("module_to_tests", {})
    imports = impact_map.get("imports", {})

    changed_modules = set()
    changed_js = []
    for rel in changed:
        mod = file_to_module(rel)
        if mod:
            changed_modules.add(mod)
        elif rel.endswith(".js"):
            changed_js.append(rel)

    # transitive closure: a change to M also affects modules importing M
    affected = set(changed_modules)
    grew = True
    while grew:
        grew = False
        for mod, imps in imports.items():
            if mod in affected:
                continue
            if any(imp in affected for imp in imps):
                affected.add(mod)
                grew = True

    selected = set()
    reasons = {}
    for mod in sorted(affected):
        for test in module_to_tests.get(mod, []):
            selected.add(test)
            reasons.setdefault(test, []).append(mod)

    # test files themselves changed -> run them directly. Deleted files
    # (e.g. renamed test matrices) only qualify when they still exist.
    tests_dir = PROJECT_ROOT / "tests"
    for rel in changed:
        name = Path(rel).name
        if rel.startswith("tests/") and name.startswith("test_") \
                and name.endswith(".py") and (tests_dir / name).exists():
            selected.add(name)
            reasons.setdefault(name, []).append("(test file changed)")

    return sorted(selected), reasons, sorted(changed_js), sorted(changed_modules)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=None,
                        help="git ref to diff against (default: auto "
                             "origin/main...HEAD, fallback main...HEAD)")
    parser.add_argument("--full", action="store_true",
                        help="run the complete test matrix (backstop mode)")
    parser.add_argument("--skip-smoke", action="store_true",
                        help="do not run the workflow smoke test")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    def log(msg):
        if not args.quiet:
            print(msg, flush=True)

    overall_rc = 0
    started = time.time()

    # ------------------------------------------------------------------
    # 1. Determine changed files
    # ------------------------------------------------------------------
    if args.full:
        changed = None  # signal: full matrix
        log("== OP89 change-impact gate: FULL matrix ==")
    else:
        base = args.base
        if base is None:
            rc, _ = run(["git", "rev-parse", "--verify", "--quiet",
                         "origin/main"])
            base = "origin/main" if rc == 0 else "main"
        changed, err = changed_files(base)
        if changed is None:
            print(f"ERROR: git diff against {base} failed: {err[-300:]}",
                  file=sys.stderr)
            return 1
        log(f"== OP89 change-impact gate: base={base}, "
            f"{len(changed)} changed files ==")

    # ------------------------------------------------------------------
    # 2. Impact map + matrix selection
    # ------------------------------------------------------------------
    impact_map, err = load_impact_map()
    if impact_map is None:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    if args.full:
        tests_dir = PROJECT_ROOT / "tests"
        matrices = sorted(p.name for p in tests_dir.glob("test_*.py"))
        reasons = {m: ["(full matrix)"] for m in matrices}
        changed_js = [f for f in impact_map.get("js_files", [])]
        changed_modules = []
    else:
        matrices, reasons, changed_js, changed_modules = \
            select_matrices(impact_map, changed)

    if not args.skip_smoke and SMOKE_TEST not in matrices:
        matrices.append(SMOKE_TEST)
        reasons.setdefault(SMOKE_TEST, []).append("(workflow smoke, immer)")

    log(f"-- selected matrices: {len(matrices)}")
    for m in matrices:
        log(f"   {m}  <- {', '.join(reasons.get(m, [])[:3])}")

    # ------------------------------------------------------------------
    # 3. Per-file quick checks: py_compile + node --check
    # ------------------------------------------------------------------
    if changed is not None:
        py_files = [f for f in changed if f.endswith(".py")
                    and not f.startswith("tests/")]
        if py_files:
            rc, out = run([sys.executable, "-m", "py_compile"] + py_files)
            if rc == 0:
                log(f"-- py_compile OK ({len(py_files)} files)")
            else:
                overall_rc = 1
                log(f"-- py_compile FAILED:\n{out[-2000:]}")
        if changed_js:
            for js in changed_js:
                rc, out = run(["node", "--check", str(PROJECT_ROOT / js)])
                if rc == 0:
                    log(f"-- node --check OK: {js}")
                else:
                    overall_rc = 1
                    log(f"-- node --check FAILED: {js}\n{out[-1000:]}")

    # ------------------------------------------------------------------
    # 4. Django system check
    # ------------------------------------------------------------------
    rc, out = run([sys.executable, "django_project/manage.py", "check"])
    if rc == 0:
        log("-- manage.py check OK")
    else:
        overall_rc = 1
        log(f"-- manage.py check FAILED:\n{out[-2000:]}")

    # ------------------------------------------------------------------
    # 5. Run matrices (one runner, sequential, clear per-matrix result)
    # ------------------------------------------------------------------
    failed = []
    for matrix in matrices:
        path = PROJECT_ROOT / "tests" / matrix
        if not path.exists():
            log(f"[SKIP] {matrix} (file missing on this branch)")
            continue
        t0 = time.time()
        rc, out = run([sys.executable, str(path)], timeout=900)
        dt = time.time() - t0
        tail = [l for l in out.splitlines() if l.strip()][-1:] 
        if rc == 0:
            log(f"[PASS] {matrix} ({dt:.1f}s) {tail[0] if tail else ''}")
        else:
            failed.append(matrix)
            overall_rc = 1
            log(f"[FAIL] {matrix} ({dt:.1f}s)")
            log("\n".join(out.splitlines()[-25:]))

    # ------------------------------------------------------------------
    # 6. Summary
    # ------------------------------------------------------------------
    dt = time.time() - started
    log("")
    log(f"== gate result: {'GREEN' if overall_rc == 0 else 'RED'} "
        f"({len(matrices)} matrices, {dt:.1f}s) ==")
    if failed:
        log("failed matrices: " + ", ".join(failed))
    return overall_rc


if __name__ == "__main__":
    sys.exit(main())
