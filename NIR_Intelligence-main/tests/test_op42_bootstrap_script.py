"""OP42 verification: bootstrap script installs Ansible and starts the playbook.

One command on the target machine should be enough: `bootstrap_install.sh`
installs Ansible if missing (apt, pipx fallback) and then runs the OP26
install playbook directly. This matrix verifies the script structurally
(offline; no package installation performed).
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
SCRIPT = PROJECT / 'ansible' / 'bootstrap_install.sh'
PLAYBOOK = PROJECT / 'ansible' / 'install_nir_intelligence.yml'
GUIDE = PROJECT / 'ansible' / 'INSTALL_NIR_INTELLIGENCE.md'

# ---------------------------------------------------------------------------
# T1: files exist, script is valid bash and executable
# ---------------------------------------------------------------------------
check('T1a bootstrap script exists', SCRIPT.exists())
check('T1b playbook exists', PLAYBOOK.exists())

proc = subprocess.run(['bash', '-n', str(SCRIPT)], capture_output=True, text=True)
check('T1c script passes bash -n', proc.returncode == 0, proc.stderr[:120])

mode = SCRIPT.stat().st_mode
check('T1d script is executable (755)',
      bool(mode & stat.S_IXUSR) and bool(mode & stat.S_IXGRP) and bool(mode & stat.S_IXOTH))

src = SCRIPT.read_text(encoding='utf-8')

# ---------------------------------------------------------------------------
# T2: robustness
# ---------------------------------------------------------------------------
check('T2a strict mode (set -euo pipefail)', 'set -euo pipefail' in src)
check('T2b shebang bash', src.startswith('#!/bin/bash'))
check('T2c resolves its own directory (playbook dir)',
      'dirname "$0"' in src)
check('T2d fails clearly if the playbook is missing',
      'Playbook nicht gefunden' in src)

# ---------------------------------------------------------------------------
# T3: Ansible installation logic
# ---------------------------------------------------------------------------
check('T3a checks ansible-playbook presence via command -v',
      'command -v ansible-playbook' in src)
check('T3b installs via apt-get (full ansible package)',
      'apt-get install -y ansible' in src)
check('T3c apt update before install', 'apt-get update' in src)
check('T3d pipx fallback with --include-deps',
      'pipx install --include-deps ansible' in src)
check('T3e pipx path handling (ensurepath/PATH)',
      'pipx ensurepath' in src and '.local/bin' in src)
check('T3f hard error if installation failed',
      'konnte nicht installiert werden' in src)
check('T3g sudo only when not root',
      '"$(id -u)" -eq 0' in src)
check('T3h idempotent: install only when ansible-playbook is missing',
      src.index('command -v ansible-playbook')
      < src.index('apt-get install'))

# ---------------------------------------------------------------------------
# T4: playbook invocation
# ---------------------------------------------------------------------------
check('T4a runs the OP26 playbook by absolute path',
      'install_nir_intelligence.yml' in src)
check('T4b localhost inventory + local connection',
      '-i localhost, -c local' in src)
check('T4c exec (no subshell leaking)',
      'exec ansible-playbook' in src)
check('T4d become-pass asked only when needed (sudo -n probe)',
      'sudo -n true' in src and '--ask-become-pass' in src)
check('T4e arguments passed through to the playbook ("$@")',
      '"$@"' in src)

# ---------------------------------------------------------------------------
# T5: guide documentation
# ---------------------------------------------------------------------------
guide = GUIDE.read_text(encoding='utf-8')
check('T5a guide documents the bootstrap command',
      'bootstrap_install.sh' in guide)
check('T5b guide documents ansible-full vs core rationale',
      'ansible-core' in guide and 'community.general' in guide)
check('T5c guide documents argument pass-through',
      '--extra-vars' in guide)

# ---------------------------------------------------------------------------
# T6: CI wiring + task doc + regressions
# ---------------------------------------------------------------------------
ci = (PROJECT.parent / '.github' / 'workflows' / 'ci.yml').read_text(encoding='utf-8')
check('T6a CI runs the OP42 matrix',
      'python tests/test_op42_bootstrap_script.py' in ci)
task_md = (PROJECT / 'TASK.md').read_text(encoding='utf-8')
check('T6b TASK.md documents OP42', 'OP42' in task_md)
check('T6c OP41 regression - playbook timeout intact',
      'preflight_timeout' in PLAYBOOK.read_text(encoding='utf-8'))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f'OP42 bootstrap script matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', ', '.join(FAILED))
    sys.exit(1)
