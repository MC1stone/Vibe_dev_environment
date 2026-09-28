"""OP43 verification: build_ventoy_stick.sh creates the complete stick payload.

One command should assemble the ventoy stick content: playbook,
bootstrap script, .deb (preferred method), tar.gz (archive method,
OP26/OP27 layout) and the guide - optionally copied directly onto the
mounted stick. This matrix builds the real artifacts and verifies the
staged structure. Offline (no stick required).
"""

import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS = 0
FAIL = 0
FAILED = []

def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'[PASS] {name}')
    else:
        FAIL += 1
        FAILED.append(name)
        print(f'[FAIL] {name} {detail}')


PROJECT = Path(__file__).resolve().parent.parent
SCRIPT = PROJECT / 'packaging' / 'build_ventoy_stick.sh'
DIST = PROJECT / 'dist'
STAGE = DIST / 'ventoy_stick' / 'ansible'

# ---------------------------------------------------------------------------
# T1: script exists, valid bash, executable
# ---------------------------------------------------------------------------
check('T1a build script exists', SCRIPT.exists())
proc = subprocess.run(['bash', '-n', str(SCRIPT)], capture_output=True, text=True)
check('T1b script passes bash -n', proc.returncode == 0, proc.stderr[:120])
mode = SCRIPT.stat().st_mode
check('T1c script is executable (755)',
      bool(mode & stat.S_IXUSR) and bool(mode & stat.S_IXGRP) and bool(mode & stat.S_IXOTH))

src = SCRIPT.read_text(encoding='utf-8')

# ---------------------------------------------------------------------------
# T2: script structure
# ---------------------------------------------------------------------------
check('T2a strict mode (set -euo pipefail)', 'set -euo pipefail' in src)
check('T2b shebang bash', src.startswith('#!/bin/bash'))
check('T2c builds the .deb via build_deb.sh',
      'build_deb.sh' in src)
check('T2d skips deb-build gracefully without dpkg-deb',
      'dpkg-deb nicht verfuegbar' in src)
check('T2e builds tar.gz with nir_intelligence root (OP26/OP27 layout)',
      'nir_intelligence' in src and 'tar -czf' in src)
check('T2f archive strips caches and the dev database',
      '__pycache__' in src and 'db.sqlite3' in src)
check('T2g stages playbook + bootstrap + guide',
      'install_nir_intelligence.yml' in src
      and 'bootstrap_install.sh' in src
      and 'INSTALL_NIR_INTELLIGENCE.md' in src)
check('T2h optional target dir copies onto the stick',
      'TARGET_DIR' in src and '"${TARGET_DIR}/ansible/"' in src)
check('T2i staging verified before copy (test -f/-x)',
      src.count('test -f') >= 3 and 'test -x' in src)
check('T2j bootstrap hint printed after copy',
      'sudo bash ${TARGET_DIR}/ansible/bootstrap_install.sh' in src)

# ---------------------------------------------------------------------------
# T3: real build - staged stick structure
# ---------------------------------------------------------------------------
if STAGE.exists():
    import shutil
    shutil.rmtree(STAGE)

r = subprocess.run(['bash', str(SCRIPT)], capture_output=True, text=True)
check('T3a script runs cleanly', r.returncode == 0, r.stderr[-200:])
check('T3b staged ansible dir exists', STAGE.is_dir())

expected = {
    'T3c playbook staged': 'install_nir_intelligence.yml',
    'T3d bootstrap staged': 'bootstrap_install.sh',
    'T3e guide staged': 'INSTALL_NIR_INTELLIGENCE.md',
    'T3f tar.gz staged': 'nir_intelligence_main.tar.gz',
}
for name, fname in expected.items():
    check(name, (STAGE / fname).exists())

check('T3g .deb staged (dpkg-deb available)',
      (STAGE / 'nir_intelligence_main.deb').exists()
      if subprocess.run(['which', 'dpkg-deb'],
                        capture_output=True).returncode == 0 else True)

check('T3h bootstrap stays executable on the stick',
      bool(STAGE.joinpath('bootstrap_install.sh').stat().st_mode & stat.S_IXUSR))

# ---------------------------------------------------------------------------
# T4: tar.gz fulfils the OP26 expectation
# ---------------------------------------------------------------------------
tarball = STAGE / 'nir_intelligence_main.tar.gz'
if tarball.exists():
    listing = subprocess.run(['tar', '-tzf', str(tarball)],
                             capture_output=True, text=True).stdout
    check('T4a archive root is nir_intelligence/',
          'nir_intelligence/' in listing)
    check('T4b install.sh at nir_intelligence/install.sh (OP26 expectation)',
          'nir_intelligence/install.sh' in listing)
    check('T4c packaging/install.sh inside the archive',
          'nir_intelligence/packaging/install.sh' in listing)
    check('T4d manage.py inside the archive',
          'nir_intelligence/django_project/manage.py' in listing)
    check('T4e no dev database inside the archive',
          'db.sqlite3' not in listing)
    check('T4f no pycache inside the archive',
          '__pycache__' not in listing)

# ---------------------------------------------------------------------------
# T5: copy onto a simulated stick (target dir argument)
# ---------------------------------------------------------------------------
import tempfile
with tempfile.TemporaryDirectory() as stick:
    r = subprocess.run(['bash', str(SCRIPT), stick],
                        capture_output=True, text=True)
    check('T5a script with target dir runs cleanly',
          r.returncode == 0, r.stderr[-200:])
    stick_ansible = Path(stick) / 'ansible'
    ok = all((stick_ansible / f).exists()
             for f in ('install_nir_intelligence.yml',
                       'bootstrap_install.sh',
                       'INSTALL_NIR_INTELLIGENCE.md',
                       'nir_intelligence_main.tar.gz'))
    check('T5b full payload copied onto the stick', ok,
          f'files={[p.name for p in stick_ansible.iterdir()] if stick_ansible.is_dir() else "missing"}')
    check('T5c output prints the bootstrap one-liner',
          'bootstrap_install.sh' in r.stdout)

with tempfile.TemporaryDirectory() as nodir:
    r = subprocess.run(['bash', str(SCRIPT), str(Path(nodir) / 'not_a_dir')],
                       capture_output=True, text=True)
    check('T5d invalid target dir fails clearly',
          r.returncode != 0 and 'Stick gemountet' in r.stdout + r.stderr)

# ---------------------------------------------------------------------------
# T6: CI wiring + task doc
# ---------------------------------------------------------------------------
ci = (PROJECT.parent / '.github' / 'workflows' / 'ci.yml').read_text(encoding='utf-8')
check('T6a CI runs the OP43 matrix',
      'python tests/test_op43_ventoy_stick.py' in ci)
task_md = (PROJECT / 'TASK.md').read_text(encoding='utf-8')
check('T6b TASK.md documents OP43', 'OP43' in task_md)
guide = (PROJECT / 'ansible' / 'INSTALL_NIR_INTELLIGENCE.md').read_text(encoding='utf-8')
check('T6c guide documents the stick-build command',
      'build_ventoy_stick.sh' in guide)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f'OP43 ventoy stick matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', ', '.join(FAILED))
    sys.exit(1)
