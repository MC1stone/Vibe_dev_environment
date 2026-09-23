"""OP26 verification: Ansible install playbook for NIR Intelligence Main.

The platform should be installable on a blank Debian 13 machine from a
Ventoy stick with one command. The playbook `ansible/install_nir_intelligence.yml`
supports two methods (.deb preferred, tar.gz + install.sh fallback), installs
dependencies, enables the service, verifies the result and stays idempotent.
This matrix verifies the playbook structurally (offline; no target machine).
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
# T1: playbook file exists and is valid YAML
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
raw_tasks = play.get('tasks', [])
src = PLAYBOOK.read_text(encoding='utf-8')


def _flatten(items):
    flat = []
    for item in items or []:
        flat.append(item)
        for nested in ('block', 'rescue', 'always'):
            flat.extend(_flatten(item.get(nested)))
    return flat


tasks = _flatten(raw_tasks)


def _task(name):
    return next((t for t in tasks if t.get('name') == name), None)


def _module(modules):
    return [t for t in tasks
            if any(t.get(m) is not None for m in modules)]


# ---------------------------------------------------------------------------
# T2: play-level requirements
# ---------------------------------------------------------------------------
check('T2a hosts localhost', play.get('hosts') == 'localhost')
check('T2b become enabled (root)', play.get('become') is True)
check('T2c connection local', play.get('connection') == 'local')

VARS = play.get('vars', {})
check('T2d ventoy mount variable', VARS.get('ventoy_mount') == '/mnt/ventoy')
check('T2e deb path variable (resolves to the ventoy ansible dir)',
      VARS.get('deb_path')
      == '{{ ventoy_ansible_dir }}/nir_intelligence_main.deb'
      and VARS.get('ventoy_ansible_dir') == '{{ ventoy_mount }}/ansible'
      and VARS.get('ventoy_mount') == '/mnt/ventoy')
check('T2f archive path variable (resolves to the ventoy ansible dir)',
      VARS.get('archive_path')
      == '{{ ventoy_ansible_dir }}/nir_intelligence_main.tar.gz')
check('T2g opt install dir variable',
      VARS.get('opt_install_dir') == '/opt/nir_intelligence')
check('T2h required packages variable (python3, wget, git, unzip)',
      set(VARS.get('required_packages', []))
      == {'python3', 'wget', 'git', 'unzip'})
check('T2i service name variable', VARS.get('service_name') == 'nir_intelligence')

# ---------------------------------------------------------------------------
# T3: required tasks present
# ---------------------------------------------------------------------------
check('T3a apt update task',
      any(t.get('ansible.builtin.apt', {}).get('update_cache')
          for t in tasks))
check('T3b dependency install task',
      any((t.get('ansible.builtin.apt') or {}).get('name') == '{{ required_packages }}'
          for t in tasks))
check('T3c deb copy task (stick -> /tmp)',
      _task('Kopiere das .deb-Paket nach /tmp') is not None)
check('T3d deb install task via apt',
      any(t.get('ansible.builtin.apt', {}).get('deb')
          for t in tasks))
check('T3e archive copy task (stick -> /opt)',
      _task('Kopiere das Archiv nach /opt') is not None)
check('T3f unarchive task (-> /opt, creates /opt/nir_intelligence/install.sh)',
      any((t.get('ansible.builtin.unarchive') or {}).get('dest')
          == '{{ opt_install_dir | dirname }}'
          and (t.get('ansible.builtin.unarchive') or {}).get('creates')
          == '{{ opt_install_dir }}/install.sh'
          for t in tasks))
check('T3g install.sh executed',
      'install.sh' in src and _module(['ansible.builtin.command'])
      and any('install.sh' in str(t.get('ansible.builtin.command', {}).get('cmd', ''))
              for t in tasks))
check('T3h systemd service enabled and started',
      any((t.get('ansible.builtin.systemd') or {}).get('enabled') is True
          and (t.get('ansible.builtin.systemd') or {}).get('state') == 'started'
          for t in tasks))
check('T3i daemon reload present',
      any((t.get('ansible.builtin.systemd') or {}).get('daemon_reload')
          for t in tasks))
check('T3j verification task present',
      _task('Pruefe, ob der Dienst aktiv ist (Verifikation)') is not None)

# ---------------------------------------------------------------------------
# T4: error handling
# ---------------------------------------------------------------------------
fail_tasks = _module(['ansible.builtin.fail'])
check('T4a fail module used', len(fail_tasks) >= 3,
      f'count={len(fail_tasks)}')
check('T4b ventoy mount check fails cleanly',
      _task('Breche ab, wenn der Ventoy-Stick nicht eingehaengt ist') is not None)
check('T4c missing source check (neither deb nor archive)',
      _task('Breche ab, wenn weder .deb-Paket noch Archiv gefunden wurden')
      is not None)
check('T4d missing install.sh check',
      _task('Breche ab, wenn install.sh fehlt') is not None)
check('T4e rescue blocks for both methods',
      src.count('rescue:') >= 2)
check('T4f stat checks before copying',
      len(_module(['ansible.builtin.stat'])) >= 4,
      f'count={len(_module(["ansible.builtin.stat"]))}')

# ---------------------------------------------------------------------------
# T5: idempotency
# ---------------------------------------------------------------------------
check('T5a unarchive guarded with creates:',
      any((t.get('ansible.builtin.unarchive') or {}).get('creates')
          for t in tasks))
check('T5b install.sh guarded with creates:',
      any((t.get('ansible.builtin.command') or {}).get('creates')
          for t in tasks))
check('T5c verification task marked changed_when: false',
      any((t.get('changed_when') is False)
          for t in tasks if 'ansible.builtin.command' in t))
check('T5d apt uses state: present (install tasks)',
      all((t.get('ansible.builtin.apt') or {}).get('state') == 'present'
          for t in tasks if 'ansible.builtin.apt' in t
          and (t.get('ansible.builtin.apt') or {}).get('name')))
check('T5e method selection based on file existence (not run-always)',
      _task('Festlegung der Installationsmethode') is not None
      and "deb_file_state.stat.exists" in src)

# ---------------------------------------------------------------------------
# T6: guide documentation
# ---------------------------------------------------------------------------
guide = GUIDE.read_text(encoding='utf-8')
check('T6a guide mentions the ansible-playbook command',
      'ansible-playbook -i localhost, -c local install_nir_intelligence.yml'
      in guide)
check('T6b guide documents the ventoy mount step', '/mnt/ventoy' in guide
      and 'mount' in guide)
check('T6c guide documents both install methods',
      'deb' in guide and 'tar.gz' in guide and 'install.sh' in guide)
check('T6d guide documents the variables table',
      '| Variable |' in guide)
check('T6e guide documents error handling', 'Fehlerbehandlung' in guide)

# ---------------------------------------------------------------------------
# T7: CI wiring + task doc
# ---------------------------------------------------------------------------
ci = (PROJECT.parent / '.github' / 'workflows' / 'ci.yml').read_text(encoding='utf-8')
check('T7a CI runs the OP26 matrix',
      'python tests/test_op26_ansible_install.py' in ci)

task_md = (PROJECT / 'TASK.md').read_text(encoding='utf-8')
check('T7b TASK.md documents OP26',
      'OP26' in task_md)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f'OP26 ansible install matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', ', '.join(FAILED))
    sys.exit(1)
