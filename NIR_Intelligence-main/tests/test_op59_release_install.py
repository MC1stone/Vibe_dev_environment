"""OP59 verification: Release-Installation mit perfekter Ansible-Routine.

Der Release muss auf einem frischen Debian 13 mit einem Befehl vom
Ventoy-Stick installierbar sein - inklusive Docker (Pflicht, nicht
optional), Backend-Stack und Ende-zu-Ende-Verifikation. OP5 (MQTT-Worker
und kommerzielle Spektrometer-Adapter) ist vom Release ausgeschlossen;
die Packaging-Skripte muessen das beim Bauen erzwingen.

Diese Matrix prueft Playbook, Packaging-Skripte und Anleitung
strukturell (offline; keine Zielmaschine noetig).
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
BUILD_DEB = PROJECT / 'packaging' / 'build_deb.sh'
BUILD_STICK = PROJECT / 'packaging' / 'build_ventoy_stick.sh'

# ---------------------------------------------------------------------------
# T1: Dateien vorhanden und validiert
# ---------------------------------------------------------------------------
check('T1a playbook file exists', PLAYBOOK.exists())
check('T1b guide file exists', GUIDE.exists())
check('T1c build_deb.sh exists', BUILD_DEB.exists())
check('T1d build_ventoy_stick.sh exists', BUILD_STICK.exists())

import yaml  # noqa: E402

try:
    docs = yaml.safe_load(PLAYBOOK.read_text(encoding='utf-8'))
    check('T1e playbook is valid YAML', isinstance(docs, list) and len(docs) == 1)
except Exception as exc:
    check('T1e playbook is valid YAML', False, str(exc)[:120])
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


all_tasks = _flatten(raw_tasks)
all_names = ' '.join((t.get('name') or '') for t in all_tasks)
all_src = ' '.join(
    str(t) for t in all_tasks
)

# ---------------------------------------------------------------------------
# T2: OP59a - Docker-Installation ist Pflicht, nicht optional
# ---------------------------------------------------------------------------
vars_block = play.get('vars', {})
check(
    'T2a docker_packages enthalten docker.io und docker-compose-v2',
    'docker.io' in str(vars_block.get('docker_packages', '')) and
    'docker-compose-v2' in str(vars_block.get('docker_packages', '')),
)

docker_install_tasks = [
    t for t in all_tasks
    if 'Installiere Docker und Docker Compose' in (t.get('name') or '')
]
check('T2b Docker-Installation via ansible.builtin.apt', len(docker_install_tasks) == 1)
check(
    'T2c Docker-Installation nur wenn fehlend (when docker_version_result.rc != 0)',
    len(docker_install_tasks) == 1 and
    'docker_version_result.rc != 0' in str(docker_install_tasks[0].get('when', '')),
)

check(
    'T2d Fail, wenn Docker nach Installation immer noch fehlt',
    'Breche ab, wenn Docker auch nach der Installation fehlt' in all_names,
)
def _sysd(t):
    return t.get('ansible.builtin.systemd') or t.get('systemd') or {}


check(
    'T2e Docker-Daemon wird state=started/enabled gesichert',
    any(
        _sysd(t).get('name') == 'docker' and
        _sysd(t).get('state') == 'started' and
        _sysd(t).get('enabled') is True
        for t in all_tasks
    ),
)
check(
    'T2f Fail, wenn Docker-Daemon nicht antwortet (docker info)',
    'Breche ab, wenn der Docker-Daemon nicht erreichbar ist' in all_names and
    'docker info' in all_src,
)
check(
    'T2g kein Hinweis-Debug auf manuelle Docker-Installation mehr (degraded verhindern)',
    'Hinweis - Docker/Compose fehlt' not in all_names,
)
check(
    'T2h Fail, wenn Backend-Stack-Skript fehlt (statt nur Hinweis)',
    'Breche ab, wenn das Backend-Stack-Skript fehlt' in all_names and
    'Hinweis - Backend-Stack-Skript fehlt im Payload' not in all_names,
)
check(
    'T2i Fail, wenn der Backend-Stack nicht startet',
    'Breche ab, wenn der Backend-Stack nicht startet' in all_names,
)

# ---------------------------------------------------------------------------
# T3: OP59b - Ende-zu-Ende-Verifikation
# ---------------------------------------------------------------------------
check(
    'T3a Django HTTP-Check gegen http://127.0.0.1:8000',
    "url: \"http://127.0.0.1:8000/\"" in src,
)
def _uri(t):
    return t.get('ansible.builtin.uri') or t.get('uri') or {}


check(
    'T3b Django-HTTP-Check mit until/retries (app_wait_timeout)',
    any(
        _uri(t).get('url', '').startswith('http://127.0.0.1:8000') and
        'until' in t and 'retries' in t
        for t in all_tasks
    ),
)
check(
    'T3c Ollama-Check gegen /api/tags',
    any(
        _uri(t).get('url', '') == 'http://127.0.0.1:11434/api/tags'
        for t in all_tasks
    ),
)
check(
    'T3d LLM-Modell-Check vorhanden (Verifikation schlaegt fehl, wenn Modell fehlt)',
    'Breche ab, wenn das LLM-Modell fehlt' in all_names and
    'llm_model' in str(vars_block),
)
check(
    'T3e Qdrant-Check gegen /healthz',
    any(
        _uri(t).get('url', '') == 'http://127.0.0.1:6333/healthz'
        for t in all_tasks
    ),
)
check(
    'T3f Redis-PING via docker exec nir_redis',
    'docker exec nir_redis redis-cli ping' in all_src,
)
check(
    'T3g Verifikationsergebnisse werden gesammelt (verify_checks)',
    'Sammle Verifikationsergebnisse' in all_names and
    'verify_checks' in all_src,
)
check(
    'T3h Verifikationsbericht wird ausgegeben',
    'Zeige Verifikationsbericht' in all_names,
)
check(
    'T3i Abbruch, wenn ein Check false ist',
    'Breche bei verfehltem Verifikationsziel ab' in all_names and
    "equalto', false" in src.replace('"', "'"),
)
check(
    'T3j Erfolgs-Meldung nennt alle verifizierten Komponenten',
    'Installation erfolgreich verifiziert (OP59b)' in all_names and
    'Qdrant und Redis sind aktiv' in src,
)
check(
    'T3k verify_command nur noch Dienst-Check, HTTP-Check separat',
    vars_block.get('verify_command') == 'systemctl is-active {{ service_name }}' and
    vars_block.get('app_wait_timeout') is not None,
)

# ---------------------------------------------------------------------------
# T4: OP59c - OP5/MQTT-Ausschluss erzwungen
# ---------------------------------------------------------------------------
deb_src = BUILD_DEB.read_text(encoding='utf-8')
stick_src = BUILD_STICK.read_text(encoding='utf-8')
check(
    'T4a build_deb.sh prueft Payload auf MQTT-Leck und bricht ab',
    'OP59c' in deb_src and 'grep -rli "mqtt"' in deb_src and 'exit 1' in deb_src,
)
check(
    'T4b build_ventoy_stick.sh prueft Archiv auf MQTT-Leck und bricht ab',
    'OP59c' in stick_src and 'grep -rli "mqtt"' in stick_src and 'exit 1' in stick_src,
)
check(
    'T4c Leak-Scan ignoriert napari_server (nur Env-Vars, kein OP5)',
    'napari_server' in deb_src and 'napari_server' in stick_src,
)
# Der Repositoriums-Payload (was ins .deb wandert) ist OP5-frei:
import subprocess  # noqa: E402
payload_dirs = ['django_project', 'agents', 'services', 'config', 'templates',
                'tasks', 'skills', 'scripts']
leak = subprocess.run(
    ['grep', '-rli', 'mqtt'] +
    [str(PROJECT / d) for d in payload_dirs if (PROJECT / d).exists()] +
    ['--include=*.py', '--include=*.yml', '--include=*.sh'],
    capture_output=True, text=True,
)
leak_files = [f for f in leak.stdout.splitlines() if 'napari_server' not in f]
check('T4d Release-Payload (Repo) ist OP5/MQTT-frei', len(leak_files) == 0,
      str(leak_files))

# ---------------------------------------------------------------------------
# T5: OP59d - kanonische Anleitung
# ---------------------------------------------------------------------------
guide = GUIDE.read_text(encoding='utf-8')
check(
    'T5a Guide ist kanonische Release-Anleitung (kennzeichnet alte Docs)',
    'kanonische Release-Installationsanleitung' in guide,
)
check(
    'T5b Guide dokumentiert automatische Docker-Installation (Pflicht)',
    'Docker ist Pflicht' in guide and 'docker.io' in guide,
)
check(
    'T5c Guide dokumentiert die Ende-zu-Ende-Verifikation mit allen Checks',
    all(k in guide for k in ['django_service', 'django_http', 'ollama',
                             'qdrant', 'redis']),
)
check(
    'T5d Guide dokumentiert OP5-Ausschluss',
    'OP5' in guide and 'MQTT-Worker' in guide,
)
check(
    'T5e Guide nennt bootstrap_install.sh als Ein-Befehl-Installation',
    'bootstrap_install.sh' in guide,
)
check(
    'T5f Variablen-Tabelle enthaelt docker_packages und llm_model',
    'docker_packages' in guide and 'llm_model' in guide,
)
check(
    'T5g Fehlerbehandlung deckt Docker- und Modell-Fehler ab',
    'journalctl -u docker' in guide and 'ollama pull' in guide,
)
check(
    'T5h Guide dokumentiert Reboot-Verhalten',
    'Nach einem Reboot' in guide,
)

# ---------------------------------------------------------------------------
# T6: CI und Dokumentation
# ---------------------------------------------------------------------------
ci = (PROJECT.parent / '.github' / 'workflows' / 'ci.yml').read_text(encoding='utf-8')
check('T6a CI runs the OP59 matrix',
      'tests/test_op59_release_install.py' in ci)
task_md = (PROJECT / 'TASK.md').read_text(encoding='utf-8')
check('T6b TASK.md documents OP59', 'OP59' in task_md)
roadmap = (PROJECT.parent / 'REPOSITORY_ALIGNMENT_AND_ROADMAP.md').read_text(encoding='utf-8')
check('T6c roadmap documents OP59', 'OP59' in roadmap)

# ---------------------------------------------------------------------------
# Ergebnis
# ---------------------------------------------------------------------------
print()

# ---------------------------------------------------------------------------
# T7: OP59-Nachtrag - KI-Metadaten-Rettungsstufe (Pflicht, nicht optional)
# ---------------------------------------------------------------------------
INGEST = PROJECT / 'services' / 'project_ingest.py'
ingest_src = INGEST.read_text(encoding='utf-8')

check('T7a KI-Rettungsstufe _ki_rescue_entry existiert',
      'def _ki_rescue_entry' in ingest_src)
# Struktur-Klaerungsdialog (2026-10-08): der unparseable-Pfad bietet jetzt
# zusaetzlich den KI-Struktur-Dialog an; die Reihenfolge bleibt
# Rettungsstufe -> usable=False (mit structure_dialog-Angebot).
check('T7b Rettungsstufe ist in den unparseable-Pfad eingebaut (vor usable=False)',
      '_ki_rescue_entry(entry, file_path, loader)' in ingest_src and
      ingest_src.index('_ki_rescue_entry(entry, file_path, loader)') <
      ingest_src.index('Not parseable as spectral data'),
      'order check with structure dialog fallback')
check('T7c Rettungsstufe dokumentiert Pflicht-Charakter (Metadaten-Untersuchung)',
      'Metadaten-Untersuchung ist Pflicht' in ingest_src)
check('T7d Rettungsstufe nutzt Anti-Halluzinations-Belegpruefung (MetadataLLMService)',
      'from services.metadata_llm import MetadataLLMService' in ingest_src)
check('T7e Rettungseintrag ist usable=True, dataset_type metadata',
      '"dataset_type": "metadata"' in ingest_src and
      '"metadata_sources": {field: "ki" for field in fields}' in ingest_src)
check('T7f KI-Fragen werden eskaliert (open_questions)',
      '"open_questions": [f"KI-Frage zu' in ingest_src)
check('T7g Never-raises-Garantie (except mit logger.exception, return None)',
      'KI rescue pass failed (non-fatal)' in ingest_src)
check('T7h LLM nicht verfuegbar -> None -> ehrlicher usable=False-Marker bleibt',
      'if not service.client.is_available():' in ingest_src)

# Funktionspruefung mit gefaktem LLM-Client (Offline, kein Ollama noetig)
import os  # noqa: E402
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.nir_web.settings')
sys.path.insert(0, str(PROJECT))
import tempfile  # noqa: E402
import services.project_ingest as pi  # noqa: E402
import services.metadata_llm as mlm  # noqa: E402

with tempfile.NamedTemporaryFile(suffix='.dat', delete=False) as f:
    f.write(b'binary-ish content Operator Dr. Meier')
    rescue_path = f.name
entry = {'file_id': '1', 'file_name': 'x.dat', 'file_extension': '.dat',
         'file_category': 'unknown'}


class _FakeClient:
    def is_available(self):
        return True


class _FakeLLM:
    def __init__(self, client=None):
        self.client = _FakeClient()

    def extract(self, text, file_name=''):
        return {'fields': {'operator': {'value': 'Dr. Meier', 'evidence': 'x'}},
                'questions': ['Welches Geraet?'], 'rejected': []}


mlm.MetadataLLMService = _FakeLLM
res = pi._ki_rescue_entry(entry, rescue_path, object())
check('T7i Rettung liefert verwertbaren Eintrag (Feld, Quelle ki, Frage)',
      bool(res) and res['usable'] is True and
      res['metadata'] == {'operator': 'Dr. Meier'} and
      res['metadata_sources'] == {'operator': 'ki'} and
      any('Welches Geraet' in q for q in res['open_questions']),
      str(res))


class _FakeEmpty(_FakeLLM):
    def extract(self, text, file_name=''):
        return None


mlm.MetadataLLMService = _FakeEmpty
check('T7j KI findet nichts -> None (usable=False bleibt ehrlich)',
      pi._ki_rescue_entry(entry, rescue_path, object()) is None)


class _FakeBoom(_FakeLLM):
    def extract(self, text, file_name=''):
        raise RuntimeError('boom')


mlm.MetadataLLMService = _FakeBoom
check('T7k LLM-Ausnahme -> None (never raises)',
      pi._ki_rescue_entry(entry, rescue_path, object()) is None)
os.unlink(rescue_path)

print(f'OP59 release install matrix: {PASS} passed, {FAIL} failed')
if FAILED:
    print('failed checks:', ', '.join(FAILED))
sys.exit(1 if FAIL else 0)
