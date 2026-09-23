# OP17: delete button and file-add (edit) button on the project list.
#
# The projects list had no way to remove a project or to add further
# files to a drafted project. OP17 adds both:
# - a delete button with a confirmation dialog per project row. Safety
#   contract: only the owner can delete (404 for others); uploaded files
#   stay (they may be shared by other projects); persisted
#   SpectrumRecords stay (SET_NULL on the project link), the spectral
#   database is not damaged by a deletion.
# - an edit button (drafted phase only) that uploads further files and
#   attaches them to the project; the preparation report is rebuilt so
#   the report page reflects the new files immediately. Released
#   projects are frozen (400).
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "django_project"))

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


import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")
import django

django.setup()

from core.models import AnalysisProject, SpectrumRecord  # noqa: E402

models_src = (PROJECT / "django_project" / "core" / "models.py").read_text(encoding="utf-8")
check("T1a SpectrumRecord.project is SET_NULL (delete keeps spectra)",
      models_src.split("class SpectrumRecord")[1].count("models.SET_NULL") >= 1)

# ---------------------------------------------------------------------------
# T2: wiring
# ---------------------------------------------------------------------------
views_src = (PROJECT / "django_project" / "api" / "project_views.py").read_text(encoding="utf-8")
check("T2a ProjectDeleteView exists", "class ProjectDeleteView" in views_src)
check("T2b delete view enforces ownership via _get_project",
      "_get_project(project_id, request.user)" in views_src.split("class ProjectDeleteView")[1].split("class ")[0]
      if "class ProjectDeleteView" in views_src else False)
check("T2c delete view actually deletes",
      "project.delete()" in views_src)
urls_src = (PROJECT / "django_project" / "api" / "project_urls.py").read_text(encoding="utf-8")
check("T2d delete route wired",
      "path('<uuid:project_id>/delete/'" in urls_src
      and "ProjectDeleteView" in urls_src)
projects_tpl = (PROJECT / "django_project" / "templates" / "projects.html").read_text(encoding="utf-8")
check("T2e delete button in the project list",
      "btn-delete-project" in projects_tpl
      and "data-project-id" in projects_tpl)
check("T2f delete confirmation modal present",
      "projectDeleteModal" in projects_tpl and "btnConfirmDelete" in projects_tpl)
check("T2g modal posts to the delete route",
      "/delete/'" in projects_tpl and "X-CSRFToken" in projects_tpl)

# template compiles
from django.template.loader import get_template  # noqa: E402

get_template("projects.html")
check("T2h projects template compiles", True)

# ---------------------------------------------------------------------------
# T3: live API contract (real ORM, test client)
# ---------------------------------------------------------------------------
from django.test.utils import setup_test_environment  # noqa: E402

setup_test_environment()
from django.test.runner import DiscoverRunner  # noqa: E402

runner = DiscoverRunner(verbosity=0, interactive=False)
old_config = runner.setup_databases()

from django.contrib.auth import get_user_model  # noqa: E402
from django.test import Client  # noqa: E402

User = get_user_model()
alice = User.objects.create_user(username="op17_alice", password="x",
                                 email="op17_alice@example.com")
mallory = User.objects.create_user(username="op17_mallory", password="x",
                                   email="op17_mallory@example.com")

project = AnalysisProject.objects.create(
    user=alice, name="OP17 Delete Me",
    preparation_report={"datasets": []},
)
record = SpectrumRecord.objects.create(
    user=alice, project=project, file_name="keep_me.txt",
    visibility="private",
    wavelengths=[410.0, 435.0], intensities=[1.0, 2.0],
    wavelength_grid="410.0,435.0",
)
project_id = str(project.id)

c = Client()
c.force_login(alice)
check("T3a unauthenticated delete rejected",
      Client().post(f"/projects/{project_id}/delete/").status_code in (301, 302, 401, 403))

m = Client()
m.force_login(mallory)
resp = m.post(f"/projects/{project_id}/delete/")
check("T3b foreign user gets 404 (ownership enforced)", resp.status_code == 404,
      str(resp.status_code))
check("T3c project still there after foreign attempt",
      AnalysisProject.objects.filter(id=project_id).exists())

resp = c.post(f"/projects/{project_id}/delete/")
check("T3d owner delete returns success JSON",
      resp.status_code == 200 and resp.json().get("success") is True,
      str(resp.status_code))
check("T3e project removed from the database",
      not AnalysisProject.objects.filter(id=project_id).exists())
check("T3f SpectrumRecord survives, project link nulled",
      SpectrumRecord.objects.filter(id=record.id).exists()
      and SpectrumRecord.objects.get(id=record.id).project_id is None)

resp = c.post(f"/projects/{project_id}/delete/")
check("T3g deleting a deleted project -> 404, no crash",
      resp.status_code == 404, str(resp.status_code))

list_resp = c.get("/projects/")
check("T3h project list renders without the deleted project",
      list_resp.status_code == 200
      and b"OP17 Delete Me" not in list_resp.content)

# ---------------------------------------------------------------------------
# T4: edit button - add further files to a drafted project
# ---------------------------------------------------------------------------
check("T4a ProjectFilesAddView exists", "class ProjectFilesAddView" in views_src)
check("T4b files/add route wired",
      "path('<uuid:project_id>/files/add/'" in urls_src
      and "ProjectFilesAddView" in urls_src)
check("T4c edit button in the list (drafted only)",
      "btn-edit-project" in projects_tpl
      and "{% if p.phase == 'drafted' %}" in projects_tpl)
check("T4d edit modal posts to files/add route",
      "projectFilesAddModal" in projects_tpl
      and "/files/add/'" in projects_tpl)

from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402


def _upload(client, name, content):
    resp = client.post("/api/files/upload/",
                       {'files': [SimpleUploadedFile(name, content)]})
    data = resp.json()
    ids = (data.get('file_ids') or data.get('uploaded_files')
           or [f['id'] for f in data.get('files', [])])
    return resp.status_code, ids


edit_project = AnalysisProject.objects.create(
    user=alice, name="OP17 Edit Me",
    preparation_report={"datasets": []},
)
status, file_ids = _upload(c, "op17_a.csv", b"wavelength,intensity\n410,100\n435,200\n")
check("T4e file upload works", status in (200, 201) and len(file_ids) == 1,
      str(status))
resp = c.post(f"/projects/{edit_project.id}/files/add/",
              data=json.dumps({'file_ids': file_ids}),
              content_type='application/json')
check("T4f files attached to the project",
      resp.status_code == 200 and resp.json().get('success') is True
      and resp.json().get('added_file_count') == 1, str(resp.status_code))
check("T4g preparation report rebuilt",
      (AnalysisProject.objects.get(id=edit_project.id).preparation_report
       or {}).get('total_dataset_count') == 1,
      str((AnalysisProject.objects.get(id=edit_project.id).preparation_report
           or {}).get('total_dataset_count')))
check("T4h project file count reflected", edit_project.files.count() == 1)

resp = c.post(f"/projects/{edit_project.id}/files/add/",
              data=json.dumps({'file_ids': file_ids}),
              content_type='application/json')
check("T4i duplicate file skipped, no rebuild error",
      resp.status_code == 200
      and resp.json().get('added_file_count') == 0
      and resp.json().get('already_present_count') == 1, str(resp.status_code))

resp = c.post(f"/projects/{edit_project.id}/files/add/",
              data=json.dumps({'file_ids': []}),
              content_type='application/json')
check("T4j empty file_ids rejected (400)", resp.status_code == 400)

resp = m.post(f"/projects/{edit_project.id}/files/add/",
              data=json.dumps({'file_ids': file_ids}),
              content_type='application/json')
check("T4k foreign user cannot add files (404)", resp.status_code == 404)

released_project = AnalysisProject.objects.create(
    user=alice, name="OP17 Released", phase='released',
    preparation_report={"datasets": []},
)
resp = c.post(f"/projects/{released_project.id}/files/add/",
              data=json.dumps({'file_ids': file_ids}),
              content_type='application/json')
check("T4l released project frozen (400)", resp.status_code == 400)

runner.teardown_databases(old_config)

print(f"OP17 project delete + edit matrix: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
