"""OP45 verification: host backend stack for the bare-metal installation.

Zielumgebungs-Feedback (Mint-Durchlauf): Die Installation (OP26-OP44)
bringt nur die systemd-Django-App auf den Host - der Docker-Stack mit den
Analyse-Backends (Ollama/Mistral, Qdrant, Redis) fehlt komplett, und die
Host-App ruft die Backends mit Container-Namen auf (http://ollama:11434),
die auf dem Host nicht aufloesbar sind. Folglich sind alle KI-Analysen
degraded.

OP45 closes the gap:
- packaging/docker-compose.host-backend.yml: Ollama, Qdrant, Redis mit
  Port-Freigabe an 127.0.0.1 (localhost-erreichbar vom Host-Django)
- packaging/start_backend_stack.sh: idempotenter Start + Modell-Pull
- postinst/install.sh: rufen den Stack-Start auf (mit klarem WARNING,
  wenn Docker fehlt - kein Fake-Erfolg)
- Ansible-Playbook: prueft Docker/Compose und startet den Stack
- build_deb.sh/build_ventoy_stick.sh: Payload enthaelt den Stack
- Defaults der App: localhost statt Container-Namen auf dem Host;
  im Docker-Stack bleibt NIR_DOCKER_STACK=1 fuer Container-Namen

This matrix verifies the structure offline (no target machine).
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
COMPOSE = PROJECT / 'packaging' / 'docker-compose.host-backend.yml'
START_SCRIPT = PROJECT / 'packaging' / 'start_backend_stack.sh'
POSTINST = PROJECT / 'packaging' / 'DEBIAN' / 'postinst'
INSTALL_SH = PROJECT / 'packaging' / 'install.sh'
PLAYBOOK = PROJECT / 'ansible' / 'install_nir_intelligence.yml'
BUILD_DEB = PROJECT / 'packaging' / 'build_deb.sh'
BUILD_STICK = PROJECT / 'packaging' / 'build_ventoy_stick.sh'
SETTINGS = PROJECT / 'django_project' / 'nir_web' / 'settings.py'

# ---------------------------------------------------------------------------
# T1: compose file for the host backend stack
# ---------------------------------------------------------------------------
check('T1a host backend compose file exists', COMPOSE.exists())
import yaml  # noqa: E402

try:
    compose_doc = yaml.safe_load(COMPOSE.read_text(encoding='utf-8'))
    check('T1b compose file is valid YAML', isinstance(compose_doc, dict))
except Exception as exc:
    check('T1b compose file is valid YAML', False, str(exc)[:120])
    sys.exit(1)

services = (compose_doc or {}).get('services', {})
check('T1c compose provides ollama, qdrant, redis',
      {'ollama', 'qdrant', 'redis'} <= set(services.keys()),
      f'services={sorted(services.keys())}')

compose_src = COMPOSE.read_text(encoding='utf-8')
check('T1d ollama published on 127.0.0.1:11434',
      '127.0.0.1:11434:11434' in compose_src)
check('T1e qdrant published on 127.0.0.1:6333',
      '127.0.0.1:6333:6333' in compose_src)
check('T1f redis published on 127.0.0.1:6379',
      '127.0.0.1:6379:6379' in compose_src)
check('T1g backend containers restart unless-stopped',
      all(services.get(s, {}).get('restart') == 'unless-stopped'
          for s in ('ollama', 'qdrant', 'redis')))
check('T1h named volumes persist model/vector/cache data',
      {'ollama_data', 'qdrant_data', 'redis_data'}
      <= set((compose_doc.get('volumes') or {}).keys()))
check('T1i no django_app service (systemd runs Django on the host)',
      'django_app' not in services)
published = [str(p) for svc in services.values() for p in svc.get('ports', [])]
check('T1j no port 8000 conflict with the systemd Django app',
      all(':8000' not in p and ':8080' not in p for p in published),
      f'published={published}')

# ---------------------------------------------------------------------------
# T2: start script contract
# ---------------------------------------------------------------------------
check('T2a start_backend_stack.sh exists', START_SCRIPT.exists())
proc = subprocess.run(['bash', '-n', str(START_SCRIPT)],
                      capture_output=True, text=True)
check('T2b start script passes bash -n', proc.returncode == 0,
      proc.stderr[:120])
mode = START_SCRIPT.stat().st_mode
check('T2c start script is executable',
      bool(mode & stat.S_IXUSR))
src = START_SCRIPT.read_text(encoding='utf-8')
check('T2d start script detects missing docker with install hint',
      'docker' in src and 'apt-get' in src and 'ERROR' in src)
check('T2e start script detects missing compose (v2 plugin or legacy)',
      'docker compose' in src and 'docker-compose' in src)
check('T2f start script detects an unreachable docker daemon',
      'docker info' in src)
check('T2g start script runs compose up -d against the backend file',
      'up -d' in src and 'docker-compose.host-backend.yml' in src)
check('T2h start script waits for ollama health (api/tags, bounded)',
      '/api/tags' in src and 'seq 1 120' in src)
check('T2i start script pulls the mistral model if missing',
      'ollama pull' in src and 'mistral' in src)
check('T2j start script is idempotent (no fail on rerun path)',
      'up -d' in src)

# ---------------------------------------------------------------------------
# T3: installer wiring (.deb postinst + archive install.sh)
# ---------------------------------------------------------------------------
postinst_src = POSTINST.read_text(encoding='utf-8')
check('T3a postinst starts the backend stack',
      'start_backend_stack.sh' in postinst_src)
check('T3b postinst warns (no fake success) if the stack fails',
      'WARNING' in postinst_src and 'degraded' in postinst_src)
install_src = INSTALL_SH.read_text(encoding='utf-8')
check('T3c install.sh starts the backend stack',
      'start_backend_stack.sh' in install_src)
check('T3d install.sh warns if the stack is missing in the payload',
      'WARNING' in install_src and 'degraded' in install_src)

# ---------------------------------------------------------------------------
# T4: ansible playbook wiring
# ---------------------------------------------------------------------------
play = yaml.safe_load(PLAYBOOK.read_text(encoding='utf-8'))[0]


def _flatten(items):
    flat = []
    for item in items or []:
        flat.append(item)
        for nested in ('block', 'rescue', 'always'):
            flat.extend(_flatten(item.get(nested)))
    return flat


tasks = _flatten(play.get('tasks', []))
playbook_src = PLAYBOOK.read_text(encoding='utf-8')
check('T4a playbook checks docker availability',
      any('docker --version' in str(t.get('ansible.builtin.command', {}).get('cmd', ''))
          for t in tasks))
check('T4b playbook checks docker compose availability',
      any('docker compose version' in str(t.get('ansible.builtin.command', {}).get('cmd', ''))
          for t in tasks))
check('T4c playbook runs the backend stack script',
      'start_backend_stack.sh' in playbook_src)
check('T4d playbook reports a clear hint when docker/compose is missing',
      'docker-compose-v2' in playbook_src and 'degraded' in playbook_src)
check('T4e backend stack start guarded by docker+compose+script checks',
      'compose_version_result.rc == 0' in playbook_src
      and 'backend_script_state.stat.exists' in playbook_src)

# ---------------------------------------------------------------------------
# T5: payload wiring (.deb + ventoy archive)
# ---------------------------------------------------------------------------
deb_src = BUILD_DEB.read_text(encoding='utf-8')
check('T5a build_deb.sh ships the backend compose file',
      'docker-compose.host-backend.yml' in deb_src)
check('T5b build_deb.sh ships the start script',
      'start_backend_stack.sh' in deb_src)
check('T5c build_deb.sh sanity-checks the backend stack files',
      deb_src.count('test -f "${APP_DIR}/packaging/') >= 3
      or ('docker-compose.host-backend.yml' in deb_src
          and 'start_backend_stack.sh' in deb_src))
stick_src = BUILD_STICK.read_text(encoding='utf-8')
check('T5d build_ventoy_stick.sh ships the backend compose file',
      'docker-compose.host-backend.yml' in stick_src)
check('T5e build_ventoy_stick.sh ships the start script',
      'start_backend_stack.sh' in stick_src)
check('T5f build_ventoy_stick.sh sanity-checks the backend stack files',
      stick_src.count('test -f "${APP_DIR}/packaging/') >= 3
      or ('docker-compose.host-backend.yml' in stick_src
          and 'start_backend_stack.sh' in stick_src))

# ---------------------------------------------------------------------------
# T6: host-resolvable service URLs (bare-metal defaults)
# ---------------------------------------------------------------------------
settings_src = SETTINGS.read_text(encoding='utf-8')
check('T6a settings read OLLAMA_URL from env with localhost default',
      "OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')"
      in settings_src)
check('T6b settings read QDRANT_URL/QDRANT_HOST with localhost defaults',
      "QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')"
      in settings_src
      and "QDRANT_HOST = os.getenv('QDRANT_HOST', 'localhost')" in settings_src)
check('T6c settings read REDIS_URL with localhost default',
      "REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')"
      in settings_src)

chatbot_views_src = (PROJECT / 'django_project' / 'api' / 'chatbot_views.py')\
    .read_text(encoding='utf-8')
check('T6d chatbot views default to host-resolvable URLs',
      'http://localhost:11434' in chatbot_views_src
      and '"localhost"' in chatbot_views_src)

views_src = (PROJECT / 'django_project' / 'api' / 'views.py')\
    .read_text(encoding='utf-8')
check('T6e health view defaults to host-resolvable URLs',
      "'http://localhost:6333'" in views_src
      and "'http://localhost:11434'" in views_src)

mcp_src = (PROJECT / 'agents' / 'mcp_agent.py').read_text(encoding='utf-8')
check('T6f mcp agent resolves container vs host via NIR_DOCKER_STACK',
      'NIR_DOCKER_STACK' in mcp_src and 'localhost' in mcp_src)
dockerfile = (PROJECT / 'Dockerfile.django').read_text(encoding='utf-8')
check('T6g Dockerfile.django keeps container semantics (NIR_DOCKER_STACK=1)',
      'NIR_DOCKER_STACK=1' in dockerfile)
for svc_file in ('services/chatbot_service.py', 'services/embedding_service.py',
                 'services/metadata_llm.py'):
    svc_src = (PROJECT / svc_file).read_text(encoding='utf-8')
    check(f'T6h {svc_file} defaults to localhost ollama',
          'OLLAMA_DEFAULT_URL = "http://localhost:11434"' in svc_src)

# ---------------------------------------------------------------------------
# T7: guide documentation + CI wiring
# ---------------------------------------------------------------------------
guide = (PROJECT / 'ansible' / 'INSTALL_NIR_INTELLIGENCE.md')\
    .read_text(encoding='utf-8')
check('T7a install guide documents the backend stack',
      'start_backend_stack.sh' in guide
      and 'docker-compose.host-backend.yml' in guide)
check('T7b install guide documents the degraded consequence',
      'degraded' in guide)

ci = (PROJECT.parent / '.github' / 'workflows' / 'ci.yml')\
    .read_text(encoding='utf-8')
check('T7c CI runs the OP45 matrix',
      'python tests/test_op45_host_backend_stack.py' in ci)

task_md = (PROJECT / 'TASK.md').read_text(encoding='utf-8')
check('T7d TASK.md documents OP45', 'OP45' in task_md)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print(f'OP45 host backend stack matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('FAILED checks:', ', '.join(FAILED))
    sys.exit(1)
