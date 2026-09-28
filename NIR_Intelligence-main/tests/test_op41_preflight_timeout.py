"""OP41 verification: Pre-flight timeout against hanging mounts (OP26 playbook).

On the target machine the OP26 install playbook hung silently at the
'Pruefe, ob das .deb-Paket auf dem Stick liegt' stat task: a mount hanging
in the kernel (removed/defective USB media still registered as mounted)
blocks every file access - stat never returns. This matrix verifies that
the pre-flight stat checks run with an async/poll timeout, that a block/
rescue converts a timeout into a clean abort with a diagnosis message,
and that the happy path (healthy mount) stays unchanged.
"""

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
PLAYBOOK = PROJECT / 'ansible' / 'install_nir_intelligence.yml'
GUIDE = PROJECT / 'ansible' / 'INSTALL_NIR_INTELLIGENCE.md'

# ---------------------------------------------------------------------------
# T1: files exist and playbook is valid YAML
# ---------------------------------------------------------------------------
check('T1a playbook file exists', PLAYBOOK.exists())
check('T1b guide file exists', GUIDE.exists())

import yaml  # noqa: E402

try:
    docs = yaml.safe_load(PLAYBOOK.read_text(encoding='utf-8'))
    check('T1c playbook is valid YAML', isinstance(docs, list) and len(docs) == 1)
except Exception as exc:
    check('T1c playbook is valid YAML', False, str(exc)[:120])
    sys.exit(1)

play = docs[0]
src = PLAYBOOK.read_text(encoding='utf-8')


def _flatten(items):
    flat = []
    for item in items or []:
        flat.append(item)
        for nested in ('block', 'rescue', 'always'):
            flat.extend(_flatten(item.get(nested)))
    return flat


tasks = _flatten(play.get('tasks', []))

def _task(name):
    return next((t for t in tasks if t.get('name') == name), None)


# ---------------------------------------------------------------------------
# T2: preflight_timeout variable
# ---------------------------------------------------------------------------
VARS = play.get('vars', {})
check('T2a preflight_timeout variable defined',
      VARS.get('preflight_timeout') == 10,
      f"got {VARS.get('preflight_timeout')!r}")

# existing variables untouched
check('T2b ventoy_mount unchanged', VARS.get('ventoy_mount') == '/mnt/ventoy')
check('T2c deb_path unchanged',
      VARS.get('deb_path')
      == '{{ ventoy_ansible_dir }}/nir_intelligence_main.deb')
check('T2d archive_path unchanged',
      VARS.get('archive_path')
      == '{{ ventoy_ansible_dir }}/nir_intelligence_main.tar.gz')
check('T2e service_name unchanged',
      VARS.get('service_name') == 'nir_intelligence')


# ---------------------------------------------------------------------------
# T3: pre-flight stat checks run with async/poll timeout
# ---------------------------------------------------------------------------
stat_names = [
    'Pruefe, ob der Ventoy-Stick eingehaengt ist',
    'Pruefe, ob das .deb-Paket auf dem Stick liegt',
    'Pruefe, ob das Archiv auf dem Stick liegt',
]
for stat_name in stat_names:
    task = _task(stat_name)
    check(f'T3a stat task present: {stat_name[:20]}...', task is not None)
    if task:
        check(f'T3b async timeout on: {stat_name[:20]}...',
              task.get('async') == '{{ preflight_timeout }}',
              f"got {task.get('async')!r}")
        check(f'T3c poll enabled on: {stat_name[:20]}...',
              task.get('poll') == 1,
              f"got {task.get('poll')!r}")

# no other stat task gained an async wrapper (only the pre-flight checks)
async_stats = [t for t in tasks
               if t.get('ansible.builtin.stat') is not None and 'async' in t]
check('T3d exactly the three pre-flight stats carry async',
      len(async_stats) == 3, f'count={len(async_stats)}')


# ---------------------------------------------------------------------------
# T4: block/rescue converts timeout into clean abort
# ---------------------------------------------------------------------------
block_task = next((t for t in play.get('tasks', [])
                   if 'block' in t and 'rescue' in t), None)
check('T4a pre-flight block with rescue present', block_task is not None)

if block_task:
    rescue_tasks = block_task.get('rescue', [])
    check('T4b rescue has the abort task',
          any('Pre-Flight' in (t.get('name') or '') for t in rescue_tasks),
          f"names={[t.get('name') for t in rescue_tasks]}")
    rescue_fail = [t for t in rescue_tasks if 'ansible.builtin.fail' in t]
    check('T4c rescue aborts with fail module', len(rescue_fail) >= 1)
    if rescue_fail:
        msg = rescue_fail[0].get('ansible.builtin.fail', {}).get('msg', '')
        check('T4d rescue message names the timeout',
              'preflight_timeout' in str(msg))
        check('T4e rescue message contains mount diagnosis hints',
              'mount | grep -i ventoy' in str(msg)
              and 'lsblk -f' in str(msg))

# pre-flight fail guards still inside the block (unchanged semantics)
block_names = [t.get('name') for t in _flatten(block_task.get('block') or [])] \
    if block_task else []
check('T4f missing-stick fail guard inside the block',
      'Breche ab, wenn der Ventoy-Stick nicht eingehaengt ist' in block_names)
check('T4g missing-source fail guard inside the block',
      'Breche ab, wenn weder .deb-Paket noch Archiv gefunden wurden'
      in block_names)
check('T4h method selection inside the block',
      'Festlegung der Installationsmethode' in block_names)

# install method debug stays outside the block (runs after successful pre-flight)
top_names = [t.get('name') for t in play.get('tasks', [])]
check('T4i method debug outside the block',
      'Installationsmethode bekanntgeben' in top_names)

# when-guards still reference the registered stat results
check('T4j when-guards unchanged (stat.exists)',
      'ventoy_mount_state.stat.exists' in src
      and 'deb_file_state.stat.exists' in src
      and 'archive_file_state.stat.exists' in src)

# install method selection still driven by the stat results
check('T4k install_method selection unchanged',
      "install_method: \"{{ 'deb' if deb_file_state.stat.exists else 'archive' }}\"" in src)


# ---------------------------------------------------------------------------
# T5: guide documentation
# ---------------------------------------------------------------------------
guide = GUIDE.read_text(encoding='utf-8')
check('T5a guide documents preflight_timeout variable',
      '`preflight_timeout`' in guide)
check('T5b guide documents the timeout behaviour in error handling',
      'Timeout' in guide and 'Fehlerbehandlung' in guide)
check('T5c guide documents diagnosis commands',
      'lsblk -f' in guide and 'mount | grep -i ventoy' in guide)


# ---------------------------------------------------------------------------
# T6: CI wiring + task doc
# ---------------------------------------------------------------------------
ci = (PROJECT.parent / '.github' / 'workflows' / 'ci.yml').read_text(encoding='utf-8')
check('T6a CI runs the OP41 matrix',
      'python tests/test_op41_preflight_timeout.py' in ci)
task_md = (PROJECT / 'TASK.md').read_text(encoding='utf-8')
check('T6b TASK.md documents OP41', 'OP41' in task_md)
check('T6c OP26 regression - playbook still has all core pieces',
      'Kopiere das .deb-Paket nach /tmp' in src
      and 'Kopiere das Archiv nach /opt' in src
      and 'daemon_reload' in src)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f'OP41 pre-flight timeout matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', ', '.join(FAILED))
    sys.exit(1)
