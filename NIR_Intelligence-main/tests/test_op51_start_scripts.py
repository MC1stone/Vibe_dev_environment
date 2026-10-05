#!/usr/bin/env python3
# OP51 test matrix: single start path (Docker stack only).
# The legacy host-Django starters created parallel server instances
# (analysis on 8001, upload on 8000) and killed unrelated manage.py
# processes. All starters now delegate to docker compose.
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
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


# T1: the three delegating starter scripts exist and delegate to compose
starters = {
    "start.sh": ("docker compose up -d", "start"),
    "stop_server.sh": ("docker compose down", "stop"),
    "check_server.sh": ("docker compose ps", "status"),
}
for name, (expected_cmd, purpose) in starters.items():
    path = PROJECT / "django_project" / name
    src = path.read_text(encoding="utf-8") if path.exists() else ""
    check(f"T1 {name} delegates to docker compose ({purpose})",
          expected_cmd in src, "missing" if not path.exists() else "")
    code = "\n".join(line for line in src.splitlines()
                      if not line.strip().startswith("#"))
    check(f"T2 {name} never kills host processes / starts runserver",
          "kill -9" not in code and "runserver" not in code
          and "fuser -k" not in code)

# T3: removed parallel-host starters are gone
removed = ["start_server.sh", "start_clean.sh", "dev_server.sh",
           "start_server_venv.sh"]
for name in removed:
    check(f"T3 legacy starter removed: {name}",
          not (PROJECT / "django_project" / name).exists())

# T4: no hard-coded private path remains in any starter
for sh in (PROJECT / "django_project").glob("*.sh"):
    src = sh.read_text(encoding="utf-8")
    check(f"T4 {sh.name} free of hard-coded private paths",
          "/home/martin" not in src)

# T5: start.sh ignores port args but documents the behaviour (no second port)
start_src = (PROJECT / "django_project" / "start.sh").read_text(encoding="utf-8")
check("T5 start.sh documents that port args are ignored (single port 8000)",
      "Port-Argument wird ignoriert" in start_src)

# T6: START_SERVER.md documents the single Docker path
doc = (PROJECT / "django_project" / "START_SERVER.md").read_text(encoding="utf-8")
check("T6 START_SERVER.md documents Docker-only single path",
      "docker compose up -d" in doc and "8001" in doc)
check("T7 START_SERVER.md no longer instructs removed scripts",
      "./start_server_venv.sh" not in doc and "./start_clean.sh" not in doc
      and "./start.sh 8001" not in doc and "./dev_server.sh" not in doc)

# T8: shell syntax of the delegating starters
import subprocess
for name in starters:
    r = subprocess.run(["sh", "-n", str(PROJECT / "django_project" / name)],
                        capture_output=True, text=True)
    check(f"T8 {name} valid shell syntax", r.returncode == 0, r.stderr[-100:])

print(f"\nOP51 start script consolidation matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
