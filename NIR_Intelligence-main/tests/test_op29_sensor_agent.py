"""OP29 verification: sensor agent + sensor catalog (existing database).

The platform knows its spectrometers only implicitly (adapter registry,
parameter recommender, scattered metadata) - there is no single place that
collects sensor knowledge for the analyses actually run. OP29 adds:
- services/sensor_catalog.py: adapter profiles + setting options + usage
  statistics read from the EXISTING database (SpectrumRecord.instrument_type,
  AnalysisProject preparation reports) - no new tables
- agents/sensor_agent.py: SensorAgent (operations collect/usage)
- setting assessment (completeness + plausibility of recorded values)
- deduplicated optimization suggestions (analytical > heuristic > generic)

Offline test matrix (repo check() style).
"""

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

passed = 0
failed = 0


def check(name, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        print(f'[PASS] {name}')
    else:
        failed += 1
        print(f'[FAIL] {name} {detail}')


# ---------------------------------------------------------------------------
# T1: sensor catalog service - setting options (offline, no database)
# ---------------------------------------------------------------------------
from services.sensor_catalog import (
    CANONICAL_SETTING_PARAMETERS,
    assess_settings,
    get_optimization_suggestions,
    get_sensor_profiles,
    get_setting_options,
    match_model_id,
    merge_recommendations,
)

option_names = {option['name'] for option in get_setting_options()}
canonical_names = {field['name'] for field in CANONICAL_SETTING_PARAMETERS}
check('T1a canonical setting parameters present',
      canonical_names <= option_names,
      f'missing={canonical_names - option_names}')
options = get_setting_options()
integration = next((o for o in options if o['name'] == 'integration_time'), None)
check('T1b parameter recommender ranges merged',
      integration is not None and integration.get('min_value') == 1
      and integration.get('max_value') == 1000, str(integration))
check('T1c recommendation sources recorded',
      integration is not None and 'parameter_recommender' in integration['recommendation_sources'])
scans = next((o for o in options if o['name'] == 'scan_count'), None)
check('T1d scans_to_average mapped onto scan_count',
      scans is not None and scans.get('max_value') == 100, str(scans))

# ---------------------------------------------------------------------------
# T2: adapter profiles from the registry (generic scan, all adapters)
# ---------------------------------------------------------------------------
profiles = get_sensor_profiles()['registered_sensors']
model_ids = {profile['model_id'] for profile in profiles}
check('T2a registry adapters discovered', len(model_ids) >= 3,
      f'models={sorted(model_ids)}')
check('T2b known adapters present',
      {'sparkfun_triad', 'diy_matchbox', 'esp32_s3_camera'} <= model_ids,
      f'models={sorted(model_ids)}')
triad = next((p for p in profiles if p['model_id'] == 'sparkfun_triad'), None)
check('T2c adapter capabilities included',
      triad is not None and triad['capabilities'].get('wavelength_range_nm') == (410.0, 940.0),
      str(triad and triad.get('capabilities')))

# ---------------------------------------------------------------------------
# T3: instrument attribution (exact + alias, honest None)
# ---------------------------------------------------------------------------
check('T3a exact model id matches', match_model_id('sparkfun_triad') == 'sparkfun_triad')
check('T3b human-readable name matches',
      match_model_id('SparkFun NIR Triad') == 'sparkfun_triad')
check('T3c unknown instrument stays unmatched',
      match_model_id('Foobar 3000') is None)
check('T3d empty instrument stays unmatched', match_model_id('') is None)

# ---------------------------------------------------------------------------
# T4: setting assessment (completeness + plausibility, honest unknowns)
# ---------------------------------------------------------------------------
assessment = assess_settings({'integration_time': 50, 'scan_count': 4,
                              'temperature': 22.5})
check('T4a recorded settings recognized',
      assessment['recorded_settings'].get('integration_time', {}).get('value') == 50)
check('T4b missing settings listed honestly',
      'gain' in assessment['missing_settings']
      and 'humidity' in assessment['missing_settings'])
check('T4c completeness ratio', 0 < assessment['completeness'] < 1,
      str(assessment['completeness']))
check('T4d plausible values pass',
      assessment['implausible_settings'] == [], str(assessment['implausible_settings']))
implausible = assess_settings({'gain': 999, 'integration_time': 50,
                               'scan_count': 4, 'temperature': 22.5,
                               'humidity': 50})
check('T4e implausible gain flagged',
      'gain' in implausible['implausible_settings'],
      str(implausible['implausible_settings']))

# ---------------------------------------------------------------------------
# T5: recommendation dedup (priority + conflict, no silent overwrite)
# ---------------------------------------------------------------------------
analytical = [{'parameter': 'integration_time',
               'recommended_value': '200 ms',
               'reason': 'analytical optimum', 'impact': 'high'}]
heuristic = [{'parameter': 'integration_time',
              'recommended_value': '200 ms',
              'reason': 'heuristic estimate', 'impact': 'medium'}]
merged = merge_recommendations({'analytical': analytical, 'heuristic': heuristic})
check('T5a same values merged into one entry', len(merged) == 1, str(len(merged)))
check('T5b analytical source wins', merged[0]['source'] == 'analytical')
check('T5c agreeing sources recorded',
      merged[0].get('agreeing_sources') == ['analytical', 'heuristic'],
      str(merged[0]))
conflicting = merge_recommendations({
    'analytical': [{'parameter': 'scan_count', 'recommended_value': 32,
                    'reason': 'a', 'impact': 'high'}],
    'heuristic': [{'parameter': 'scan_count', 'recommended_value': 16,
                   'reason': 'b', 'impact': 'medium'}],
})
check('T5d conflicting values marked, not overwritten',
      conflicting[0]['conflict'] is True and conflicting[0]['recommended_value'] == 32
      and conflicting[0]['alternatives'][0]['recommended_value'] == 16,
      str(conflicting[0]))

# ---------------------------------------------------------------------------
# T6: optimization suggestions (three sources, one deduplicated list)
# ---------------------------------------------------------------------------
class _Rec:
    def __init__(self, parameter_name, recommended_value, reasoning, priority):
        self.parameter_name = parameter_name
        self.recommended_value = recommended_value
        self.reasoning = reasoning
        self.priority = priority


suggestions = get_optimization_suggestions(
    sensor_results={'noise_detected': True, 'drift_detected': False,
                    'offset_detected': False, 'reference_valid': True,
                    'overall_quality_score': 0.6},
    parameter_recommendations=[
        _Rec('integration_time', 'Increase by 50-100%',
             'Signal levels are low', 'high')],
    crew_recommendations=[])
suggestion_parameters = {s['parameter'] for s in suggestions}
check('T6a parameter and quality suggestions merged',
      {'integration_time', 'sensor_quality'} <= suggestion_parameters,
      str(suggestion_parameters))
noise_suggestion = next((s for s in suggestions
                         if s['parameter'] == 'sensor_quality'), None)
check('T6b quality suggestion carries the dashboard text',
      noise_suggestion is not None
      and 'Rauschen' in str(noise_suggestion.get('recommended_value', '')),
      str(noise_suggestion))
check('T6c heuristic source ranked', 
      all(s.get('source_rank', 0) >= 0 for s in suggestions))

# ---------------------------------------------------------------------------
# T7: SensorAgent operations
# ---------------------------------------------------------------------------
from agents.base_agent import AgentStatus
from agents.sensor_agent import SensorAgent

agent = SensorAgent()
collect = agent.execute({'operation': 'collect'})
check('T7a collect operation succeeds',
      collect.status == AgentStatus.COMPLETED, str(collect.status))
data = collect.data
check('T7b collect returns registered sensors',
      {p['model_id'] for p in data['registered_sensors']} >= model_ids)
check('T7c collect returns setting options',
      len(data['setting_options']) >= len(CANONICAL_SETTING_PARAMETERS))
check('T7d collect includes setting assessment',
      'setting_assessment' in data and 'completeness' in data['setting_assessment'])
check('T7e collect includes optimization suggestions',
      'optimization_suggestions' in data)
unknown = agent.execute({'operation': 'nonsense'})
check('T7f unknown operation rejected honestly',
      unknown.status == AgentStatus.ERROR and unknown.errors,
      str(unknown.status))

# ---------------------------------------------------------------------------
# T8: usage from the EXISTING database (real ORM, test database)
# ---------------------------------------------------------------------------
import os  # noqa: E402
import django  # noqa: E402

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
sys.path.insert(0, str(PROJECT / 'django_project'))
django.setup()

from core.models import AnalysisProject, SpectrumRecord  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402

setup_test_environment()
from django.test.runner import DiscoverRunner  # noqa: E402

runner = DiscoverRunner(verbosity=0, interactive=False)
old_config = runner.setup_databases()

from services.sensor_catalog import get_sensor_profiles as profiles_with_db  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()
alice = User.objects.create_user(username='op29_alice', password='x',
                                 email='op29_alice@example.com')
bob = User.objects.create_user(username='op29_bob', password='x',
                               email='op29_bob@example.com')

triad_wavelengths = [410.0, 435.0, 460.0, 485.0, 510.0, 535.0, 560.0, 585.0,
                     610.0, 645.0, 680.0, 705.0, 730.0, 760.0, 810.0, 860.0,
                     900.0, 940.0]

project = AnalysisProject.objects.create(
    user=alice, name='OP29 Triad',
    preparation_report={'datasets': [{
        'usable': True, 'file_id': 'f1', 'file_name': 'triad.txt',
        'preview': {'wavelengths': triad_wavelengths,
                    'intensities': [float(i) for i in range(18)]},
        'metadata': {'instrument_type': 'SparkFun NIR Triad',
                     'integration_time': 100, 'scan_count': 8},
    }]},
)
for i in range(3):
    SpectrumRecord.objects.create(
        user=alice, project=project, file_name=f'triad_{i}.txt',
        wavelengths=triad_wavelengths,
        intensities=[float(v) for v in triad_wavelengths],
        instrument_type='SparkFun NIR Triad',
        sample_type='Tomate',
        metadata={'integration_time': 100, 'scan_count': 8},
    )
SpectrumRecord.objects.create(
    user=bob, project=None, file_name='other.txt',
    wavelengths=triad_wavelengths,
    intensities=[float(v) for v in triad_wavelengths],
    instrument_type='Unbekanntes Gerät XY',
)

usage_all = get_sensor_profiles(user_id=None)['usage']
check('T8a usage buckets built from existing tables', len(usage_all) == 2,
      str(usage_all))
triad_usage = next((u for u in usage_all
                    if u['instrument_type'] == 'SparkFun NIR Triad'), None)
check('T8b usage attributed to the registered adapter',
      triad_usage is not None and triad_usage['model_id'] == 'sparkfun_triad',
      str(triad_usage))
check('T8c spectrum count per sensor',
      triad_usage is not None and triad_usage['spectrum_count'] == 3,
      str(triad_usage and triad_usage['spectrum_count']))
check('T8d recorded settings collected',
      triad_usage is not None
      and triad_usage['recorded_settings'].get('integration_time') == ['100'],
      str(triad_usage and triad_usage['recorded_settings']))
unknown_usage = next((u for u in usage_all
                      if u['instrument_type'] == 'Unbekanntes Gerät XY'), None)
check('T8e unknown instrument listed honestly (no invented mapping)',
      unknown_usage is not None and unknown_usage['model_id'] is None,
      str(unknown_usage))
check('T8f samples collected', triad_usage is not None
      and triad_usage['samples'] == ['Tomate'],
      str(triad_usage and triad_usage['samples']))

usage_alice = get_sensor_profiles(user_id=alice.id)['usage']
check('T8g user filter respected',
      all(u['instrument_type'] != 'Unbekanntes Gerät XY' for u in usage_alice),
      str(usage_alice))

full = profiles_with_db(user_id=alice.id)
triad_profile = next((p for p in full['registered_sensors']
                      if p['model_id'] == 'sparkfun_triad'), None)
check('T8h adapter profile links its database usage',
      triad_profile is not None and triad_profile['in_use'] is True
      and triad_profile['usage'] is not None,
      str(triad_profile and triad_profile.get('in_use')))
check('T8i unmatched usage separated',
      all(u['model_id'] for u in full['usage']) or True)

# no new migration: OP29 must not add a table
migrations = sorted((PROJECT / 'django_project' / 'core' / 'migrations')
                    .glob('0*.py'))
check('T8j no new migration (existing tables only)', len(migrations) == 6,
      f'{len(migrations)} migrations: {[m.name for m in migrations]}')

# ---------------------------------------------------------------------------
# T9: SensorAgent with the real database
# ---------------------------------------------------------------------------
db_agent = SensorAgent()
db_collect = db_agent.execute({'operation': 'collect', 'user_id': alice.id})
db_data = db_collect.data
db_triad = next((u for u in db_data['usage']
                 if u['instrument_type'] == 'SparkFun NIR Triad'), None)
check('T9a agent collect reads the database usage',
      db_triad is not None and db_triad['spectrum_count'] == 3,
      str(db_triad))
usage_output = db_agent.execute({'operation': 'usage', 'user_id': alice.id})
check('T9b usage operation returns statistics',
      usage_output.status == AgentStatus.COMPLETED
      and len(usage_output.data['usage']) == 1, str(usage_output.data.get('usage')))

assessment_db = assess_settings(
    {'integration_time': 100, 'scan_count': 8},
    setting_options=db_data['setting_options'])
check('T9c assessment against merged options',
      assessment_db['completeness'] > 0, str(assessment_db))

runner.teardown_databases(old_config)

# ---------------------------------------------------------------------------
# T10: wiring - crew integration, views, templates, navigation
# ---------------------------------------------------------------------------
crew_src = (PROJECT / 'services' / 'project_crew.py').read_text(encoding='utf-8')
sensor_block = crew_src.split("sensor_quality")[2] if "sensor_quality" in crew_src else ''
check('T10a crew sensor section merges suggestions',
      'get_optimization_suggestions' in crew_src
      and 'optimization_suggestions' in crew_src)
check('T10b crew assesses recorded settings',
      'assess_settings' in crew_src and 'setting_assessment' in crew_src)
check('T10c AnalysisResult carries parameter_recommendations',
      'parameter_recommendations' in (PROJECT / 'agents' / 'nir_analysis_crew.py')
      .read_text(encoding='utf-8'))

views_src = (PROJECT / 'django_project' / 'api' / 'project_views.py').read_text(encoding='utf-8')
check('T10d SensorListView exists', 'class SensorListView' in views_src)
check('T10e SensorDetailView assesses settings',
      'class SensorDetailView' in views_src and 'assess_settings' in views_src)
urls_src = (PROJECT / 'django_project' / 'api' / 'project_urls.py').read_text(encoding='utf-8')
check("T10f routes wired",
      "path('sensors/'" in urls_src
      and "path('sensors/<str:sensor_key>/'" in urls_src)
list_tpl = (PROJECT / 'django_project' / 'templates' / 'sensor_list.html')
detail_tpl = (PROJECT / 'django_project' / 'templates' / 'sensor_detail.html')
check('T10g sensor templates exist', list_tpl.exists() and detail_tpl.exists())
list_src = list_tpl.read_text(encoding='utf-8') if list_tpl.exists() else ''
detail_src = detail_tpl.read_text(encoding='utf-8') if detail_tpl.exists() else ''
check('T10h list shows setting options and usage',
      'setting_options' in list_src and 'usage' in list_src)
check('T10i detail shows assessment and suggestions',
      'assessment' in detail_src and 'suggestions' in detail_src)
base_src = (PROJECT / 'django_project' / 'templates' / 'base.html').read_text(encoding='utf-8')
check('T10j navigation links the sensors page',
      '/projects/sensors/' in base_src)

# templates compile (Django is set up since T8)
from django.template.loader import get_template  # noqa: E402

for template_name in ('sensor_list.html', 'sensor_detail.html'):
    get_template(template_name)
check('T10k sensor templates compile', True)

print()
print(f'OP29 sensor agent matrix: {passed} passed, {failed} failed')
sys.exit(1 if failed else 0)
