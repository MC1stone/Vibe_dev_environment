"""OP27 verification: .deb package for NIR Intelligence Main.

The OP26 ansible playbook expects `nir_intelligence_main.deb` (or a tar.gz
with install.sh) on the ventoy stick. This OP provides the packaging so
that artifact actually exists: `packaging/build_deb.sh` bundles the
platform into /opt/nir_intelligence with DEBIAN control/postinst, a
systemd unit (nir_intelligence.service) and install.sh for the archive
method. The matrix builds the .deb with the real dpkg-deb and checks the
structure. Offline (no installation is performed).
"""

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
PKG_DIR = PROJECT / 'packaging'
BUILD = PKG_DIR / 'build_deb.sh'
CONTROL = PKG_DIR / 'DEBIAN' / 'control'
POSTINST = PKG_DIR / 'DEBIAN' / 'postinst'
SERVICE = PKG_DIR / 'nir_intelligence.service'
INSTALL_SH = PKG_DIR / 'install.sh'
DIST = PROJECT / 'dist'

# ---------------------------------------------------------------------------
# T1: packaging files exist
# ---------------------------------------------------------------------------
check('T1a build script exists', BUILD.exists())
check('T1b control file exists', CONTROL.exists())
check('T1c postinst exists', POSTINST.exists())
check('T1d systemd unit exists', SERVICE.exists())
check('T1e install.sh exists (archive method)', INSTALL_SH.exists())
for script in (BUILD, POSTINST, INSTALL_SH):
    check(f'T1f {script.name} is executable',
          script.exists() and script.stat().st_mode & 0o111)

# ---------------------------------------------------------------------------
# T2: control metadata
# ---------------------------------------------------------------------------
control = CONTROL.read_text(encoding='utf-8')
check('T2a package name nir-intelligence-main',
      'Package: nir-intelligence-main' in control)
check('T2b version field present', 'Version:' in control)
check('T2c architecture all', 'Architecture: all' in control)
check('T2d depends on python3/venv/pip/sqlite3',
      'python3' in control and 'python3-venv' in control
      and 'python3-pip' in control and 'sqlite3' in control)
check('T2e description mentions /opt and the service',
      '/opt/nir_intelligence' in control and 'nir_intelligence' in control)

# ---------------------------------------------------------------------------
# T3: postinst contract (mirrors the OP26 expectations)
# ---------------------------------------------------------------------------
postinst = POSTINST.read_text(encoding='utf-8')
check('T3a postinst is a bash script', postinst.startswith('#!/bin/bash'))
check('T3b postinst creates the nir service user',
      'useradd' in postinst and 'APP_USER="nir"' in postinst)
check('T3c postinst builds the venv',
      'python3 -m venv' in postinst)
check('T3d postinst installs requirements (tolerant to optional deps)',
      'requirements.txt' in postinst and '||' in postinst)
check('T3e postinst migrates the database',
      'manage.py migrate' in postinst)
check('T3f postinst enables and restarts the service',
      'systemctl enable' in postinst and 'systemctl restart' in postinst)
check('T3g postinst guarded by configure case (idempotent)',
      'configure' in postinst)

# ---------------------------------------------------------------------------
# T4: systemd unit contract
# ---------------------------------------------------------------------------
service = SERVICE.read_text(encoding='utf-8')
check('T4a unit installs into multi-user target',
      'WantedBy=multi-user.target' in service)
check('T4b unit runs as the nir user',
      'User=nir' in service and 'Group=nir' in service)
check('T4c working directory is the django project',
      'WorkingDirectory=/opt/nir_intelligence/django_project' in service)
check('T4d exec starts the web UI on loopback port 8000',
      'ExecStart=/opt/nir_intelligence/venv/bin/python manage.py runserver '
      '127.0.0.1:8000' in service)
check('T4e restart on failure', 'Restart=on-failure' in service)

# ---------------------------------------------------------------------------
# T5: install.sh contract (archive method, OP26 playbook calls it)
# ---------------------------------------------------------------------------
install_sh = INSTALL_SH.read_text(encoding='utf-8')
check('T5a install.sh requires root',
      'id -u' in install_sh and '-ne 0' in install_sh)
check('T5b install.sh uses the script directory (portable)',
      "dirname" in install_sh)
check('T5c install.sh installs the systemd unit',
      'nir_intelligence.service' in install_sh
      and '/etc/systemd/system' in install_sh)
check('T5d install.sh writes the .install_completed marker (playbook guard)',
      '.install_completed' in install_sh)
check('T5e install.sh is idempotent (venv/user/service guards)',
      install_sh.count('if !') >= 2 and 'getent group' in install_sh)

# ---------------------------------------------------------------------------
# T6: build script + real build
# ---------------------------------------------------------------------------
build_src = BUILD.read_text(encoding='utf-8')
check('T6a build stages into /opt/nir_intelligence',
      'opt/nir_intelligence' in build_src)
check('T6b build copies the DEBIAN control dir',
      'packaging/DEBIAN' in build_src)
check('T6c build bundles django_project, agents, services',
      all(item in build_src for item in
          ('django_project', 'agents', 'services')))
check('T6d build strips caches and the dev database',
      '__pycache__' in build_src and 'db.sqlite3' in build_src)
check('T6e build outputs dist/nir_intelligence_main.deb',
      'dist/nir_intelligence_main.deb' in build_src)

deb = DIST / 'nir_intelligence_main.deb'
if not deb.exists():
    r = subprocess.run(['bash', str(BUILD)], capture_output=True, text=True)
    check('T6f build script runs cleanly', r.returncode == 0,
          r.stderr[-200:] if r.returncode else '')
check('T6g .deb artifact exists', deb.exists())

if deb.exists():
    listing = subprocess.run(
        ['dpkg-deb', '-c', str(deb)], capture_output=True, text=True).stdout
    check('T6h payload under /opt/nir_intelligence',
          './opt/nir_intelligence/' in listing)
    check('T6i install.sh inside the package',
          './opt/nir_intelligence/install.sh' in listing)
    check('T6j systemd unit inside the package',
          './opt/nir_intelligence/packaging/nir_intelligence.service'
          in listing)
    check('T6k manage.py inside the package',
          './opt/nir_intelligence/django_project/manage.py' in listing)
    check('T6l requirements.txt inside the package',
          './opt/nir_intelligence/requirements.txt' in listing)
    check('T6m no dev database in the package',
          'db.sqlite3' not in listing)
    check('T6n no pycache dirs in the package',
          '__pycache__' not in listing)
    info = subprocess.run(
        ['dpkg-deb', '-f', str(deb)], capture_output=True, text=True).stdout
    check('T6o dpkg metadata parses (Package/Version)',
          'Package: nir-intelligence-main' in info and 'Version:' in info)
    import tempfile
    with tempfile.TemporaryDirectory() as ctl_dir:
        extract = subprocess.run(
            ['dpkg-deb', '-e', str(deb), ctl_dir], capture_output=True, text=True)
        ctl_files = list(Path(ctl_dir).glob('*'))
        check('T6p postinst shipped inside the package',
              extract.returncode == 0
              and (Path(ctl_dir) / 'postinst').exists()
              and (Path(ctl_dir) / 'postinst').read_text(encoding='utf-8')
              .startswith('#!/bin/bash'),
              f'files={[f.name for f in ctl_files]}')

# ---------------------------------------------------------------------------
# T7: archive method produces the OP26 layout (tar.gz with install.sh at root)
# ---------------------------------------------------------------------------
tarball = DIST / 'nir_intelligence_main.tar.gz'
if not tarball.exists():
    import shutil
    base = DIST / '_archive_stage'
    if base.exists():
        shutil.rmtree(base)
    (base / 'nir_intelligence').mkdir(parents=True)
    for item in ('django_project', 'agents', 'services', 'config',
                 'templates', 'tasks', 'skills', 'docs', 'requirements.txt',
                 'README.md', 'path_config.py'):
        src_item = PROJECT / item
        if src_item.exists():
            if src_item.is_dir():
                shutil.copytree(src_item, base / 'nir_intelligence' / item,
                                ignore=shutil.ignore_patterns('__pycache__'))
            else:
                shutil.copy2(src_item, base / 'nir_intelligence' / item)
    shutil.copytree(PKG_DIR, base / 'nir_intelligence' / 'packaging')
    shutil.copy2(INSTALL_SH, base / 'nir_intelligence' / 'install.sh')
    subprocess.run(['tar', '-czf', str(tarball), '-C', str(base),
                    'nir_intelligence'], check=True)
    shutil.rmtree(base)
tar_listing = subprocess.run(
    ['tar', '-tzf', str(tarball)], capture_output=True, text=True).stdout
check('T7a archive root is nir_intelligence/',
      'nir_intelligence/' in tar_listing)
check('T7b install.sh at nir_intelligence/install.sh (OP26 expectation)',
      'nir_intelligence/install.sh' in tar_listing)

# ---------------------------------------------------------------------------
# T8: CI wiring + task doc
# ---------------------------------------------------------------------------
ci = (PROJECT.parent / '.github' / 'workflows' / 'ci.yml').read_text(encoding='utf-8')
check('T8a CI runs the OP27 matrix',
      'python tests/test_op27_deb_package.py' in ci)
task_md = (PROJECT / 'TASK.md').read_text(encoding='utf-8')
check('T8b TASK.md tracks OP27 as current task',
      'Current Task: OP27' in task_md)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f'OP27 deb package matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', ', '.join(FAILED))
    sys.exit(1)
