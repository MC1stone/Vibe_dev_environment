#!/usr/bin/env python3
"""OP87: Build the static test impact map for the change-impact test gate.

Scans the project sources and discovers, for every test matrix in
tests/test_*.py, which source modules it covers. The result is written to
tests/.impact_map.json (generated, gitignored) and consumed by
scripts/run_change_tests.py.

Assignment strategy (deterministic, no third-party deps):
1. Explicit tag: a line ``# covers: services/fusion_calibration.py, ...``
   in the first 15 lines of the test file wins.
2. Name heuristic: tests/test_op63_fusion_branch.py -> modules matching
   the distinctive token (``fusion``) in agents/, services/, django_project/.
3. Import scan: ``import services.x`` / ``from services.x import ...`` /
   ``from agents.x`` / ``from api.x`` inside the test source.

The map also contains the reverse dependency graph: which source modules
import which other source modules (one level deep, intra-project). A change
to module M therefore selects every matrix covering M or any module that
imports M (transitive closure is computed by the runner, one level here is
enough because services/* rarely import each other two levels deep - the
runner expands transitively anyway).

Usage:
    python scripts/build_test_impact_map.py [--project-root DIR] [--quiet]
Exit code 0 on success, 1 on failure.
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

SOURCE_ROOTS = ("agents", "services", "scripts", "dev_framework")
DJANGO_ROOTS = ("api", "core", "nir_web", "port_manager", "middleware")
JS_ROOT = ("django_project", "static", "js")

COVERS_TAG = re.compile(r"^#\s*covers:\s*(.+)$", re.MULTILINE)
IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+"
    r"(agents|services|scripts|dev_framework|api|core|nir_web|port_manager|middleware)"
    r"[.\s]",
    re.MULTILINE,
)


def project_root_from_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=None,
                        help="NIR_Intelligence-main directory (default: auto)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    if args.project_root:
        return Path(args.project_root).resolve(), args.quiet
    # scripts/ lives directly under the project root
    return Path(__file__).resolve().parent.parent, args.quiet


def iter_python_files(root, subdirs):
    for sub in subdirs:
        base = root / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            yield path


def module_key(root, path):
    """Repo-relative module path without .py, e.g. services/fusion_calibration."""
    rel = path.relative_to(root).with_suffix("")
    return str(rel).replace("/", ".")


def imports_of(root, path):
    """Intra-project modules imported by one python file (module keys)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                found.add(node.module)
    keys = set()
    for mod in found:
        top = mod.split(".")[0]
        if top in SOURCE_ROOTS or top in DJANGO_ROOTS:
            keys.add(mod)
    return sorted(keys)


def token_from_test_name(test_path):
    """tests/test_op63_fusion_branch.py -> 'fusion' (longest word >= 4 chars)."""
    stem = test_path.stem
    words = re.split(r"[^a-z]+", stem.lower())
    words = [w for w in words if len(w) >= 4 and w not in {
        "test", "op63", "with", "from", "into", "page", "data", "file", "html",
    }]
    # drop pure op-numbers
    words = [w for w in words if not re.fullmatch(r"op\d+[a-z]?", w)]
    return max(words, key=len) if words else None


def modules_matching_token(root, token):
    """All intra-project module keys whose path contains the token."""
    hits = []
    for path in iter_python_files(root, SOURCE_ROOTS + DJANGO_ROOTS):
        key = module_key(root, path)
        if token in key:
            hits.append(key)
    return hits


def covers_for_test(root, test_path):
    """Explicit covers-tag first, then name heuristic, then import scan."""
    try:
        head = "".join(
            test_path.read_text(encoding="utf-8").splitlines(keepends=True)[:15]
        )
    except UnicodeDecodeError:
        head = ""
    m = COVERS_TAG.search(head)
    if m:
        mods = []
        for part in m.group(1).split(","):
            part = part.strip().rstrip(".py").replace("/", ".").strip()
            if part:
                mods.append(part)
        if mods:
            return mods, "tag"

    token = token_from_test_name(test_path)
    if token:
        hits = modules_matching_token(root, token)
        if hits:
            return hits, f"name:{token}"

    return imports_of(root, test_path), "imports"


def build_map(root):
    tests_dir = root / "tests"
    test_files = sorted(tests_dir.glob("test_*.py"))

    # Workflow-Smoke ist kein Impact-Ziel: Er laeuft bei jedem Change und
    # deckt den Gesamtworkflow ab — eine Modul-Zuordnung wuerde ihn doppelt
    # auswaehlen und falsche "betroffene Module" suggerieren.
    ALWAYS_RUN = {"test_workflow_smoke.py"}

    # forward: module -> set of test files covering it
    module_to_tests = {}
    test_assignment = {}
    for tf in test_files:
        if tf.name in ALWAYS_RUN:
            test_assignment[tf.name] = {"covers": [], "strategy": "always-run"}
            continue
        mods, strategy = covers_for_test(root, tf)
        test_assignment[tf.name] = {"covers": mods, "strategy": strategy}
        for mod in mods:
            module_to_tests.setdefault(mod, set()).add(tf.name)

    # reverse: module -> modules it imports (one level)
    imports = {}
    for path in iter_python_files(root, SOURCE_ROOTS + DJANGO_ROOTS):
        imports[module_key(root, path)] = imports_of(root, path)

    # JS files (checked with node --check by the runner)
    js_files = []
    js_base = root / "django_project" / "static" / "js"
    if js_base.is_dir():
        js_files = sorted(
            str(p.relative_to(root)) for p in js_base.glob("*.js")
        )

    return {
        "version": 1,
        "module_to_tests": {k: sorted(v) for k, v in sorted(module_to_tests.items())},
        "test_assignment": test_assignment,
        "imports": imports,
        "js_files": js_files,
        "source_roots": list(SOURCE_ROOTS),
        "django_roots": list(DJANGO_ROOTS),
    }


def main(argv=None):
    root, quiet = project_root_from_args(argv if argv is not None else sys.argv[1:])
    if not (root / "tests").is_dir():
        print(f"ERROR: {root} does not look like NIR_Intelligence-main "
              "(tests/ missing)", file=sys.stderr)
        return 1
    impact_map = build_map(root)
    out = root / "tests" / ".impact_map.json"
    out.write_text(json.dumps(impact_map, indent=2) + "\n", encoding="utf-8")
    if not quiet:
        n_tests = len(impact_map["test_assignment"])
        n_mods = len(impact_map["module_to_tests"])
        print(f"impact map written: {out}")
        print(f"  test matrices: {n_tests}")
        print(f"  covered modules: {n_mods}")
        print(f"  js files: {len(impact_map['js_files'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
