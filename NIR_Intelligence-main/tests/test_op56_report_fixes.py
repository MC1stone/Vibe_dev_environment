# OP56 test matrix: release-blocking report fixes
# Four user-observed defects after OP54/OP55:
#   1. Report-embedded chatbot showed "Offline" although Ollama was up:
#      the widget POSTed /api/chatbot/message/ without an X-CSRFToken
#      header -> DRF SessionAuthentication answered 403 -> the JS catch
#      branch fell into the offline knowledge base.
#   2. Metadata changes were not saved: the metadata editor POSTed with a
#      token from the csrftoken cookie, but the detail view never set the
#      cookie (ensure_csrf_cookie) and the form carried no hidden token.
#   3. Sensor reference data (e.g. SparkFun Triad) was not offered to fill
#      missing metadata fields.
#   4. Endless-looking preparation: no elapsed time / dataset count.
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "django_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")

PASS = 0
FAIL = 0


def check(name, cond, info=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {info}" if info else f"[FAIL] {name}")


import django

django.setup()

from django.test import Client
from django.test.runner import DiscoverRunner
from django.test.utils import setup_test_environment

setup_test_environment()

from django.conf import settings as dj_settings

if "testserver" not in dj_settings.ALLOWED_HOSTS:
    dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]

# T1: report chatbot widget sends the CSRF token and session credentials
widget_src = (Path(__file__).resolve().parent.parent
              / "services" / "report_chatbot.py").read_text(encoding="utf-8")
check("T1a report chatbot sends X-CSRFToken header",
      "'X-CSRFToken'" in widget_src)
check("T1b report chatbot reads the csrftoken cookie",
      "csrftoken=" in widget_src)
check("T1c report chatbot sends session credentials",
      "credentials: 'same-origin'" in widget_src)

# T2: project detail view sets the CSRF cookie; editor form carries a token
views_src = (Path(__file__).resolve().parent.parent
             / "django_project" / "api" / "project_views.py").read_text(
                 encoding="utf-8")
check("T2a ProjectDetailView uses ensure_csrf_cookie",
      "ensure_csrf_cookie" in views_src
      and "class ProjectDetailView" in views_src)
template_src = (Path(__file__).resolve().parent.parent
                / "django_project" / "templates"
                / "project_report.html").read_text(encoding="utf-8")
check("T2b metadata editor form embeds {% csrf_token %}",
      "{% csrf_token %}" in template_src)
check("T2c editor JS prefers the hidden csrfmiddlewaretoken input",
      'csrfmiddlewaretoken' in template_src)

# T3: suggested settings service exists and is wired into the reference check
sd_src = (Path(__file__).resolve().parent.parent
          / "services" / "sensor_documents.py").read_text(encoding="utf-8")
check("T3a _suggested_settings helper exists",
      "def _suggested_settings" in sd_src)
check("T3b reference check attaches suggested_settings",
      'entry["suggested_settings"] = _suggested_settings(name)' in sd_src)
check("T3c database-recorded settings win over catalogue defaults",
      "_usage_from_database" in sd_src and "recorded_settings" in sd_src)
check("T3d template renders one-click suggestion buttons",
      "js-suggest-setting" in template_src)
check("T3e suggestion buttons only fill empty inputs",
      "input && !input.value" in template_src)

# T4: preparation banner shows elapsed time and dataset count
check("T4a banner shows elapsed-time element",
      'id="prepare-elapsed"' in template_src)
check("T4b banner shows dataset-count element",
      'id="prepare-count"' in template_src)
check("T4c polling updates the dataset count",
      "prepare-count" in template_src.split("tickClock")[0]
      or "dataset_count" in template_src)

# T5: live behaviour of the detail view (CSRF cookie + suggestions)
runner = DiscoverRunner(verbosity=0)
old_config = runner.setup_databases()
try:
    from core.models import User, AnalysisProject, GenericFile
    from django.core.files.uploadedfile import SimpleUploadedFile

    user, _ = User.objects.get_or_create(username="op56user")
    if not user.check_password("pw12345!"):
        user.set_password("pw12345!")
        user.save()
    f = GenericFile.objects.create(
        user=user, name="op56.txt", original_filename="op56.txt",
        file=SimpleUploadedFile("op56.txt", b"x\ty\n1\t2\n"),
        file_size=len(b"x\ty\n1\t2\n"))
    project = AnalysisProject.objects.create(
        user=user, name="op56-proj",
        preparation_report={"datasets": [
            {"file_name": "op56.txt", "file_id": str(f.id), "usable": True,
             "metadata": {"instrument_type": "sparkfun_triad"}}]})
    client = Client()
    client.login(username="op56user", password="pw12345!")
    resp = client.get(f"/projects/{project.id}/")
    check("T5a detail view answers for logged-in owner",
          resp.status_code == 200, f"got {resp.status_code}")
    check("T5b detail response sets the csrftoken cookie",
          "csrftoken" in (resp.cookies or {}))
    # T5c: _suggested_settings for an unknown sensor returns None (honest)
    from services.sensor_documents import _suggested_settings
    check("T5c no suggestions for an unknown sensor",
          _suggested_settings("definitely-not-a-sensor") is None)
    # T5d: matched adapter (sparkfun_triad) yields at least the recorded /
    #      catalogue settings dict or None - never raises
    try:
        result = _suggested_settings("sparkfun_triad")
        check("T5d known sensor never raises",
              result is None or isinstance(result, dict))
    except Exception as exc:
        check("T5d known sensor never raises", False, str(exc))
finally:
    runner.teardown_databases(old_config)

print(f"\nOP56: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
