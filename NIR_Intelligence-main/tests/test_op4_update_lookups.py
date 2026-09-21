"""OP4 verification: online update lookups (PyPI/Docker Hub) and CI wiring.

Tests the UpdateLookupService with stub transports (offline), the
repository normalization for Docker Hub URLs, offline graceful degradation,
the CLI --online flag contract, and the GitHub Actions workflow files.
No network access required.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.update_lookup import (PYPI_JSON_URL, DOCKER_HUB_TAGS_URL,
                                    UpdateLookupService, create_update_lookup)
from services.update_monitor import ComponentEntry, create_update_monitor

results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')


PROJECT = Path(__file__).resolve().parent.parent


class StubResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


# T1: PyPI lookup with stub transport
pypi_payload = {
    'info': {'version': '0.0.1'},
    'releases': {
        '1.0.0': [{'yanked': False}],
        '1.5.0': [{'yanked': False}],
        '1.5.9': [{'yanked': False}],
        '2.0.0rc1': [{'yanked': False}],
        '9.9.9': [{'yanked': True}],
        'empty-release': [],
    },
}
svc = UpdateLookupService(transport=lambda m, u, **k: StubResponse(pypi_payload))
check('T1a latest stable pypi version detected',
      svc.latest_pypi_version('numpy') == '1.5.9',
      f'latest={svc.latest_pypi_version("numpy")}')
check('T1b yanked releases skipped', svc.latest_pypi_version('numpy') != '9.9.9')
check('T1c pypi url format', 'pypi.org/pypi/numpy/json' in PYPI_JSON_URL.format(name='numpy'))

# T2: HTTP error statuses degrade to None
for status in (404, 500):
    svc_err = UpdateLookupService(
        transport=lambda m, u, s=None, **k: StubResponse({}, status=s))
    broken = StubResponse({}, status)
    svc_err = UpdateLookupService(transport=lambda m, u, **k: broken)
    check(f'T2a pypi http {status} -> None', svc_err.latest_pypi_version('numpy') is None)

# T3: transport exceptions degrade to None (offline guarantee)
def raise_offline(method, url, **kwargs):
    raise RuntimeError('network unreachable')

svc_offline = UpdateLookupService(transport=raise_offline)
check('T3a offline pypi lookup returns None', svc_offline.latest_pypi_version('numpy') is None)
check('T3b offline docker lookup returns None', svc_offline.latest_docker_tag('postgres') is None)
check('T3c offline enrich_report returns 0',
      svc_offline.enrich_report([ComponentEntry(name='numpy', kind='pip', declared='>=1.0')]) == 0)
check('T3d online=False skips lookups entirely',
      create_update_lookup().enrich_report([], online=False) == 0)

# T4: Docker Hub tag lookup with stub transport
hub_payload = {'results': [
    {'name': 'latest'},
    {'name': '1.5.2'},
    {'name': '1.6.0'},
    {'name': '1.6.0-alpine'},
    {'name': 'edge'},
]}
svc_hub = UpdateLookupService(transport=lambda m, u, **k: StubResponse(hub_payload))
check('T4a latest stable docker tag detected',
      svc_hub.latest_docker_tag('qdrant/qdrant') == '1.6.0',
      f'latest={svc_hub.latest_docker_tag("qdrant/qdrant")}')
check('T4b non-semver tags skipped',
      svc_hub.latest_docker_tag('qdrant/qdrant') not in ('latest', 'edge', '1.6.0-alpine'))

# T5: repository normalization
norm = UpdateLookupService._normalize_repository
check('T5a library images get namespace', norm('postgres') == 'library/postgres')
check('T5b tag stripped before normalization', norm('postgres:15-alpine') == 'library/postgres')
check('T5c namespaced images unchanged', norm('qdrant/qdrant') == 'qdrant/qdrant')
check('T5d private registries stripped',
      norm('registry.example.com:5000/foo/bar') == 'foo/bar')
check('T5e localhost registry stripped', norm('localhost:5000/foo') == 'foo')
check('T5f vendor images keep namespace', norm('srsolutions/ilias') == 'srsolutions/ilias')

# T6: enrich_report flags updates correctly
entry_old = ComponentEntry(name='numpy', kind='pip', declared='>=1.0.0', installed='1.2.0')
entry_current = ComponentEntry(name='pandas', kind='pip', declared='>=2.0.0', installed='2.2.0')
entry_docker = ComponentEntry(name='qdrant/qdrant', kind='docker', declared='latest')

lookup = UpdateLookupService(transport=lambda m, u, **k: StubResponse(pypi_payload))
enriched = lookup.enrich_report([entry_old])
check('T6a outdated component flagged',
      enriched == 1 and entry_old.update_available is True
      and entry_old.available == '1.5.9'
      and 'newer' in (entry_old.note or ''),
      f'note={entry_old.note}')

lookup_cur = UpdateLookupService(transport=lambda m, u, **k: StubResponse(
    {'releases': {'2.2.0': [{'yanked': False}]}}))
lookup_cur.enrich_report([entry_current])
check('T6b current component not flagged',
      entry_current.update_available is False and entry_current.available == '2.2.0')

lookup_docker = UpdateLookupService(transport=lambda m, u, **k: StubResponse(hub_payload))
lookup_docker.enrich_report([entry_docker])
check('T6c latest-tag docker entry gets upstream info',
      entry_docker.available == '1.6.0' and entry_docker.update_available is None
      and 'compare manually' in (entry_docker.note or ''),
      f'note={entry_docker.note}')

# T7: monitor report entries serialize with the new available field
monitor = create_update_monitor(config={'project_root': str(PROJECT),
                                        'compose_files': ['docker-compose.yml']})
report = monitor.scan()
entry_dict = report.to_dict()['components'][0]
check('T7a ComponentEntry.to_dict includes available', 'available' in entry_dict)
try:
    json.dumps(report.to_dict())
    check('T7b enriched report stays JSON-serializable', True)
except Exception as exc:
    check('T7b enriched report stays JSON-serializable', False, str(exc)[:120])
text = monitor._quarto_markdown(report)
check('T7c Quarto report has upstream column',
      'Upstream latest' in text
      and '| Package | Declared | Installed | Update flagged | Upstream latest |' in text)

# T8: CLI --online flag contract
cli = subprocess.run(
    [sys.executable, str(PROJECT / 'scripts' / 'check_updates.py'),
     '--project-root', str(PROJECT), '--online', '--no-report', '--json'],
    capture_output=True, text=True, timeout=180,
)
check('T8a CLI --online exits 0 (offline-tolerant)', cli.returncode == 0,
      f'stderr={cli.stderr[:200] if cli.returncode else ""}')
try:
    parsed = json.loads(cli.stdout)
    check('T8b CLI --online --json produces valid report',
          'summary' in parsed and 'components' in parsed)
except Exception as exc:
    check('T8b CLI --online --json produces valid report', False, str(exc)[:200])

# T9: GitHub Actions workflow files
workflow_dir = PROJECT.parent / '.github' / 'workflows'
ci_path = workflow_dir / 'ci.yml'
check('T9a CI workflow file exists', ci_path.exists(), str(ci_path))
if ci_path.exists():
    ci_text = ci_path.read_text()
    import yaml
    ci_yaml = yaml.safe_load(ci_text)
    job = ci_yaml.get('jobs', {}).get('test-matrices', {})
    step_run = ''.join(s.get('run', '') for s in job.get('steps', []))
    check('T9b workflow runs all test matrices',
          all(name in step_run for name in [
              'test_s3_format_loaders', 'test_s4_spectrometer_adapters',
              'test_s5_spectrum_similarity', 'test_s6_chatbot',
              'test_s7_update_monitoring', 'test_s8_ilias_integration',
              'test_s9_federated_learning', 'test_op1_embedding_pipeline',
              'test_op2_ilias_token_flow', 'test_op3_platform_ui',
              'test_op6_crewai_agents']),
          'missing some test matrices')
    check('T9c workflow installs the documented minimal deps',
          'pyyaml' in step_run and 'scikit-learn' in step_run and 'pillow' in step_run)
    check('T9d workflow is valid YAML with a real job',
          bool(job) and 'runs-on' in job)

update_path = workflow_dir / 'update-monitor.yml'
check('T9e update-monitor workflow file exists', update_path.exists())
if update_path.exists():
    upd_yaml = yaml.safe_load(update_path.read_text())
    upd_job = list(upd_yaml.get('jobs', {}).values())
    upd_run = ''.join(s.get('run', '') for s in upd_job[0].get('steps', [])) if upd_job else ''
    check('T9f update-monitor workflow uses --online flag', '--online' in upd_run)
    check('T9g update-monitor workflow is scheduled', 'schedule' in upd_yaml.get(True, upd_yaml.get('on', {})) or 'schedule' in str(upd_yaml.get('on', upd_yaml.get(True, {}))))

# T10: S7 regression spot check (offline monitor unchanged)
from services.update_monitor import UpdateMonitorService
check('T10a S7 specifier semantics unchanged',
      UpdateMonitorService._specifier_allows_update('<=1.0.0', '2.5.3') is True
      and UpdateMonitorService._specifier_allows_update('>=1.0.0', '2.5.3') is False)
check('T10b S7 compose image extraction unchanged',
      UpdateMonitorService.parse_compose_images(PROJECT / 'docker-compose.yml') != [])

print(f'\n{sum(1 for _, ok in results if ok)}/{len(results)} tests passed')
sys.exit(1 if any(not ok for _, ok in results) else 0)
