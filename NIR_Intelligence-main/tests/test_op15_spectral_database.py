# OP15: persistent spectral database.
#
# The FAISS similarity section compared a project only against its own
# sibling datasets - spectra from earlier projects were lost after the run.
# OP15 persists released datasets as SpectrumRecords (visibility: private
# default, lab_shared opt-in - FL ground rule: raw spectra stay local) and
# compares new projects against the visible database records on the same
# wavelength grid (no cross-grid interpolation, by design). Provenance fields
# double as non-IID sharding dimensions for federated learning (S9).
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"[PASS] {name}")
    else:
        failed += 1
        print(f"[FAIL] {name} {detail}")


# ---------------------------------------------------------------------------
# T1: model, migration and grid key
# ---------------------------------------------------------------------------
import os  # noqa: E402
import django  # noqa: E402

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nir_web.settings')
sys.path.insert(0, str(PROJECT / 'django_project'))
django.setup()

from core.models import AnalysisProject, SpectrumRecord  # noqa: E402

models_src = (PROJECT / 'django_project' / 'core' / 'models.py').read_text(encoding='utf-8')
check("T1a SpectrumRecord model exists", 'class SpectrumRecord' in models_src)
check("T1b visibility choices private/lab_shared",
      "'private'" in models_src and "'lab_shared'" in models_src
      and 'SpectrumRecord' in models_src)
migration = PROJECT / 'django_project' / 'core' / 'migrations' / '0006_spectrumrecord.py'
check("T1c migration 0006 exists", migration.exists(), str(migration))
migration_src = migration.read_text(encoding='utf-8') if migration.exists() else ''
check("T1d migration creates the table",
      'CreateModel' in migration_src and 'SpectrumRecord' in migration_src)
check("T1e FL sharding provenance fields",
      'instrument_type' in models_src.split('class SpectrumRecord')[1]
      and 'sample_type' in models_src.split('class SpectrumRecord')[1])
grid_a = SpectrumRecord.grid_key([410.0, 435.5, 940.0])
grid_b = SpectrumRecord.grid_key([410.01, 435.52, 939.99])
grid_c = SpectrumRecord.grid_key([700.0, 750.0, 800.0])
check("T1f grid key canonical (float noise tolerant)", grid_a == grid_b, f"{grid_a} vs {grid_b}")
check("T1g grid key discriminates different grids", grid_a != grid_c)

# ---------------------------------------------------------------------------
# T2: persistence service (real ORM, test database)
# ---------------------------------------------------------------------------
from django.test.utils import setup_test_environment  # noqa: E402

setup_test_environment()
from django.test.runner import DiscoverRunner  # noqa: E402

runner = DiscoverRunner(verbosity=0, interactive=False)
old_config = runner.setup_databases()

from services.spectrum_database import (  # noqa: E402
    persist_project_spectra, visible_records, references_for_dataset,
)

from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()
alice = User.objects.create_user(username='op15_alice', password='x',
                                  email='op15_alice@example.com')
bob = User.objects.create_user(username='op15_bob', password='x',
                                email='op15_bob@example.com')

triad_wavelengths = [410.0, 435.0, 460.0, 485.0, 510.0, 535.0, 560.0, 585.0,
                     610.0, 645.0, 680.0, 705.0, 730.0, 760.0, 810.0, 860.0,
                     900.0, 940.0]
triad_intensities = [1359.7, 2409.2, 4560.2, 1793.6, 3746.6, 6713.5, 1277.5, 1975.4,
                     16146.2, 2417.1, 3749.2, 1037.0, 2144.7, 1232.2, 2871.0, 4367.3,
                     1997.6, 1083.4]


project = AnalysisProject.objects.create(
    user=alice, name='OP15 Triad',
    preparation_report={'datasets': [{
        'usable': True,
        'file_id': 'f1',
        'file_name': 'triad.txt',
        'preview': {'wavelengths': triad_wavelengths,
                    'intensities': triad_intensities},
        'metadata': {'instrument_type': 'Dpark fun NIR Triad',
                     'sample_type': 'Tomate'},
    }]},
)
summary = persist_project_spectra(project)
check("T2a persist created one record", summary.get('created') == 1, str(summary))
record = SpectrumRecord.objects.filter(project=project).first()
check("T2b record persisted with grid key",
      record is not None and record.wavelength_grid == SpectrumRecord.grid_key(triad_wavelengths))
check("T2c provenance stored (instrument, sample)",
      record.instrument_type == 'Dpark fun NIR Triad' and record.sample_type == 'Tomate')
check("T2d default visibility private", record.visibility == 'private')

summary2 = persist_project_spectra(project)
check("T2e re-release idempotent (update, no duplicate)",
      summary2.get('created') == 0 and summary2.get('updated') == 1
      and SpectrumRecord.objects.filter(project=project).count() == 1, str(summary2))

# a different project from another user, lab-shared
shared_project = AnalysisProject.objects.create(
    user=bob, name='OP15 Shared',
    preparation_report={'datasets': [{
        'usable': True,
        'file_id': 'f2',
        'file_name': 'shared_triad.txt',
        'preview': {'wavelengths': triad_wavelengths,
                    'intensities': [v * 0.5 for v in triad_intensities]},
        'metadata': {},
    }]},
)
persist_project_spectra(shared_project, visibility='lab_shared')
shared = SpectrumRecord.objects.filter(project=shared_project).first()
check("T2f lab_shared visibility stored", shared.visibility == 'lab_shared')

# a different wavelength grid must not be compared against the triad grid
other_project = AnalysisProject.objects.create(
    user=alice, name='OP15 Other Grid',
    preparation_report={'datasets': [{
        'usable': True,
        'file_id': 'f3',
        'file_name': 'other.txt',
        'preview': {'wavelengths': [700.0, 750.0, 800.0, 850.0, 900.0, 950.0,
                                     1000.0, 1050.0, 1100.0, 1150.0],
                    'intensities': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0,
                                    9.0, 10.0]},
        'metadata': {},
    }]},
)
persist_project_spectra(other_project)

# ---------------------------------------------------------------------------
# T3: visibility and grid filtering
# ---------------------------------------------------------------------------
check("T3a owner sees own private records",
      visible_records(alice).filter(id=record.id).exists())
check("T3b other user does NOT see private records",
      not visible_records(bob).filter(id=record.id).exists())
check("T3c lab-shared record visible to other user",
      visible_records(bob).filter(id=shared.id).exists())
dataset = project.preparation_report['datasets'][0]
check("T3d dataset grid key matches record",
      SpectrumRecord.grid_key(dataset['preview']['wavelengths']) == record.wavelength_grid)

# ---------------------------------------------------------------------------
# T4: FAISS reference set for the similarity section
# ---------------------------------------------------------------------------
bob_dataset = shared_project.preparation_report['datasets'][0]
refs_bob = references_for_dataset(bob.id, bob_dataset)
check("T4a shared spectrum found as reference for the other user",
      len(refs_bob['references']) == 1, str(len(refs_bob['references'])))
check("T4b reference ids carry the source file name",
      refs_bob['ids'] == ['shared_triad.txt'], str(refs_bob['ids']))

# a lab-shared triad-grid spectrum is visible to alice (other user) too
refs_alice_shared = references_for_dataset(alice.id, dataset,
                                          exclude_project_id=project.id)
check("T4b2 lab-shared spectrum visible across users",
      refs_alice_shared['ids'] == ['shared_triad.txt'], str(refs_alice_shared['ids']))

refs_alice = references_for_dataset(alice.id, dataset, exclude_project_id=project.id)
check("T4c own project excluded, other grid excluded",
      all('other.txt' not in i for i in refs_alice['ids'])
      and all('triad.txt' != i for i in refs_alice['ids']), str(refs_alice['ids']))

other_dataset = other_project.preparation_report['datasets'][0]
refs_other = references_for_dataset(bob.id, other_dataset)
check("T4d cross-grid references empty (no interpolation by design)",
      refs_other['references'] == [], str(refs_other['references']))

# ---------------------------------------------------------------------------
# T5: wiring - release persists, crew compares, UI routes exist
# ---------------------------------------------------------------------------
views_src = (PROJECT / 'django_project' / 'api' / 'project_views.py').read_text(encoding='utf-8')
check("T5a release persists spectra",
      'persist_project_spectra' in views_src.split('class ProjectReleaseView')[1]
      if 'class ProjectReleaseView' in views_src else False)
check("T5b visibility request option validated",
      "spectrum_visibility" in views_src and "'lab_shared'" in views_src)
check("T5c SpectrumDatabaseView exists", 'class SpectrumDatabaseView' in views_src)
check("T5d SpectrumDatabaseDetailView with FAISS matches",
      'class SpectrumDatabaseDetailView' in views_src and 'FaissAgent' in views_src)
urls_src = (PROJECT / 'django_project' / 'api' / 'project_urls.py').read_text(encoding='utf-8')
check("T5e database route wired", "path('database/'" in urls_src)
check("T5f detail route wired", "path('database/<uuid:spectrum_id>/'" in urls_src)
db_template = PROJECT / 'django_project' / 'templates' / 'spectrum_database.html'
detail_template = PROJECT / 'django_project' / 'templates' / 'spectrum_detail.html'
check("T5g database template exists", db_template.exists())
check("T5h detail template exists", detail_template.exists())
db_template_src = db_template.read_text(encoding='utf-8') if db_template.exists() else ''
check("T5i database template links projects page",
      '/projects/' in db_template_src)
crew_src = (PROJECT / 'services' / 'project_crew.py').read_text(encoding='utf-8')
check("T5j similarity section uses the database",
      'references_for_dataset' in crew_src
      and 'database_references' in crew_src)
projects_src = (PROJECT / 'django_project' / 'templates' / 'projects.html').read_text(encoding='utf-8')
check("T5k projects page links the database", '/projects/database/' in projects_src)
report_src = (PROJECT / 'django_project' / 'templates' / 'project_report.html').read_text(encoding='utf-8')
check("T5l release offers lab-sharing opt-in",
      'spectrum-visibility' in report_src and 'lab_shared' in report_src)

# templates compile
from django.template.loader import get_template  # noqa: E402

for name in ('spectrum_database.html', 'spectrum_detail.html'):
    get_template(name)
check("T5m templates compile", True)

# ---------------------------------------------------------------------------
# T6: live API contract (Django test client, real ORM)
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402

client = Client()
client.force_login(alice)
db_response = client.get('/projects/database/')
check("T6a database page renders (200)",
      db_response.status_code == 200, str(db_response.status_code))
check("T6b database page shows the own spectrum",
      b'triad.txt' in db_response.content)
check("T6c database page shows the shared spectrum",
      b'shared_triad.txt' in db_response.content)
detail_response = client.get(f'/projects/database/{record.id}/')
check("T6d detail page renders (200)",
      detail_response.status_code == 200, str(detail_response.status_code))
check("T6e detail page shows the series",
      b'16146.2' in detail_response.content)
foreign = Client()
foreign.force_login(bob)
check("T6f detail of a private spectrum hidden for others (404)",
      foreign.get(f'/projects/database/{record.id}/').status_code == 404)

runner.teardown_databases(old_config)

print()
print(f"OP15 spectral database matrix: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
