"""S8 verification: ILIAS container integration + learning path sync.

Tests the learning path model (objectives/modules/courses), the ILIAS course
payload builder, the synchronization against a stubbed transport (no network
required), graceful degradation when ILIAS is unreachable, the Django API
wiring, and the docker-compose ILIAS container topology (own container,
dedicated MariaDB, volumes, networks).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from services.ilias_learning_service import (
    ILIASCourseBuilder,
    LearningModule,
    LearningObjective,
    LearningPath,
    SyncOutcome,
    create_ilias_learning_service,
)

results = []


def check(name, ok, detail=''):
    results.append((name, ok))
    print(f'[{"PASS" if ok else "FAIL"}] {name} {detail}')


PROJECT = Path(__file__).resolve().parent.parent


def make_learning_path():
    return LearningPath(
        title='NIR-Spektroskopie im Labor',
        description='Lernpfad: NIR-Messung, Datenauswertung, Kalibration',
        target_group='students',
        modules=[
            LearningModule(title='Messung mit dem SparkFun Triad', objectives=[
                LearningObjective(title='18-Kanal-Spektrum aufnehmen'),
                LearningObjective(title='Wellenlängenbereiche benennen', target_level='remember'),
            ], content_ref='reports/nir_intro.qmd'),
            LearningModule(title='Kalibration und Validierung', objectives=[
                LearningObjective(title='PLS-Modell erstellen', target_level='apply'),
            ]),
        ],
    )


# T1: learning path model
path = make_learning_path()
check('T1a learning path has modules and objectives',
      len(path.modules) == 2 and path.total_objectives() == 3)
as_dict = path.to_dict()
check('T1b learning path serializes to dict',
      as_dict['title'] == 'NIR-Spektroskopie im Labor'
      and len(as_dict['modules']) == 2
      and as_dict['modules'][0]['objectives'][0]['target_level'] == 'apply')

# T2: ILIAS course payload builder
course_payload = ILIASCourseBuilder.build_course_payload(path)
check('T2a course payload maps to ILIAS course object',
      course_payload['type'] == 'crs' and course_payload['title'] == path.title
      and course_payload['additional']['objective_count'] == 3)
module_payloads = ILIASCourseBuilder.build_module_payloads(path)
check('T2b module payloads are ILIAS learning objectives',
      len(module_payloads) == 2 and module_payloads[0]['type'] == 'lobj'
      and 'content_ref' in module_payloads[0] and 'content_ref' not in module_payloads[1])

# T3: successful sync via stubbed transport
calls = []


class StubResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def stub_transport(method, url, json=None):
    calls.append((method, url, json))
    if url.endswith('/courses'):
        return StubResponse(201, {'ref_id': 42})
    return StubResponse(201, {'ref_id': 100})


service = create_ilias_learning_service()
path2 = make_learning_path()
outcome = service.sync_learning_path(path2, transport=stub_transport)
check('T3a sync success reports modules synced',
      outcome.success is True and outcome.modules_synced == 2
      and outcome.course_ref_id == '42' and path2.ilias_ref_id == '42')
check('T3b course created first, then objectives under course ref',
      len(calls) == 3 and calls[0][1].endswith('/api/v1/courses')
      and calls[1][1].endswith('/api/v1/courses/42/objectives'))

# T4: course creation failure surfaces as error
def failing_course_transport(method, url, json=None):
    if url.endswith('/courses'):
        return StubResponse(403, {})
    return StubResponse(201, {})


outcome4 = service.sync_learning_path(make_learning_path(), transport=failing_course_transport)
check('T4 course creation failure -> unsuccessful outcome with error',
      outcome4.success is False and outcome4.modules_synced == 0
      and any('course creation failed' in e for e in outcome4.errors))

# T5: module sync failure is recorded per module
def partial_transport(method, url, json=None):
    if url.endswith('/courses'):
        return StubResponse(201, {'ref_id': 7})
    if json and json.get('title') == 'Kalibration und Validierung':
        return StubResponse(500, {})
    return StubResponse(201, {})


outcome5 = service.sync_learning_path(make_learning_path(), transport=partial_transport)
check('T5 partial module failure recorded, one module synced',
      outcome5.success is False and outcome5.modules_synced == 1
      and len(outcome5.errors) == 1)

# T6: unreachable ILIAS -> graceful error, no crash
def unreachable_transport(method, url, json=None):
    raise ConnectionError('ilias container not running')


outcome6 = service.sync_learning_path(make_learning_path(), transport=unreachable_transport)
check('T6 unreachable ILIAS -> error in outcome, no crash',
      outcome6.success is False and any('unreachable' in e for e in outcome6.errors))

# T7: empty learning path rejected
outcome7 = service.sync_learning_path(LearningPath(title='empty'), transport=stub_transport)
check('T7 empty learning path -> error, no sync call',
      outcome7.success is False and len(calls) == 3
      and any('no modules' in e for e in outcome7.errors))

# T8: SyncOutcome serialization
outcome_dict = outcome.to_dict()
check('T8 SyncOutcome serializable',
      outcome_dict['success'] is True and outcome_dict['modules_synced'] == 2)

# T9: service status without running ILIAS (no crash)
status = service.status()
check('T9 service status reports ilias url and availability flag',
      status['ilias_url'] == 'http://ilias:80' and 'available' in status)

# T10: Django API wiring
api_dir = PROJECT / 'django_project' / 'api'
check('T10a ilias views/urls files exist',
      (api_dir / 'ilias_views.py').exists() and (api_dir / 'ilias_urls.py').exists())
main_urls = (PROJECT / 'django_project' / 'nir_web' / 'urls.py').read_text()
check('T10b ilias route registered', "api/ilias/" in main_urls and "api.ilias_urls" in main_urls)
views_src = (api_dir / 'ilias_views.py').read_text()
check('T10c view status codes: 400 validation, 201 created, 502 bad gateway',
      'HTTP_400_BAD_REQUEST' in views_src and 'HTTP_201_CREATED' in views_src
      and 'HTTP_502_BAD_GATEWAY' in views_src)

# T11: docker-compose ILIAS container (dev + prod)
compose = yaml.safe_load((PROJECT / 'docker-compose.yml').read_text())
services = compose['services']
check('T11a ilias container in dev compose',
      'ilias' in services and services['ilias']['image'].startswith('srsolutions/ilias:')
      and services['ilias']['ports'] == ['8080:80'])
check('T11b ilias uses dedicated mariadb (ilias_db) and depends on it',
      'ilias_db' in services and services['ilias_db']['image'].startswith('mariadb:')
      and 'ilias_db' in services['ilias']['depends_on'])
check('T11c ilias environment configures auto setup + database',
      any('ILIAS_AUTO_SETUP' in e for e in services['ilias']['environment'])
      and any('ILIAS_DB_HOST=ilias_db' in e for e in services['ilias']['environment']))
check('T11d ilias volumes registered (data, extradata, db)',
      {'ilias_data', 'ilias_extradata', 'ilias_db_data'} <= set(compose['volumes']))
check('T11e ilias joins nir_network',
      'nir_network' in services['ilias']['networks'])
prod = yaml.safe_load((PROJECT / 'docker-compose.prod.yml').read_text())
check('T11f ilias container in prod compose with healthchecks',
      'ilias' in prod['services'] and 'healthcheck' in prod['services']['ilias']
      and 'healthcheck' in prod['services']['ilias_db'])
check('T11g ilias image pinned (no latest tag)',
      not services['ilias']['image'].endswith('latest')
      and not prod['services']['ilias']['image'].endswith('latest'))

# T12: agent config references the container URL scheme
agent_config = (PROJECT / 'config' / 'agent_config.yaml').read_text()
check('T12 agent config keeps ilias integration block',
      'ilias_agent:' in agent_config and 'synchronization:' in agent_config)

# T13: regression spot checks
from services.ilias_learning_service import ILIASLearningService
check('T13a factory returns service', isinstance(service, ILIASLearningService))
import py_compile
py_compile.compile(str(api_dir / 'ilias_views.py'), doraise=True)
py_compile.compile(str(api_dir / 'ilias_urls.py'), doraise=True)
check('T13b Django views/urls compile', True)
from services.chatbot_service import ChatbotService
svc = ChatbotService()
msgs, rag = svc.build_messages('Q?')
check('T13c S6 chatbot regression spot check', len(msgs) == 2 and rag['sources'] == [])

failed = [r for r in results if not r[1]]
print(f'\n{len(results) - len(failed)}/{len(results)} tests passed')
sys.exit(1 if failed else 0)
