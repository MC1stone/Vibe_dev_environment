#!/usr/bin/env python3
# OP53 test matrix: one KI page per sensor, sensor document database,
# sensor reference check at project creation.
# Offline-safe: no network access required (LLM client is faked).
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "django_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {detail}")


try:
    import django
    django.setup()
    check("T0a django setup", True)
except Exception as exc:
    check("T0a django setup", False, str(exc))
    sys.exit(1)

# T1: SensorDocument model + migration
from core.models import SensorDocument
check("T1a SensorDocument model importable", True)
mig = (Path(__file__).resolve().parent.parent / "django_project/core/migrations"
       / "0007_sensordocument.py")
check("T1b migration 0007_sensordocument exists", mig.exists())
check("T1c upload_to under sensor_docs/",
      "sensor_docs/" in SensorDocument._meta.get_field("file").upload_to)
check("T1d visibility choices private/lab_shared",
      {c[0] for c in SensorDocument.VISIBILITY} == {"private", "lab_shared"})
check("T1e sensor_key indexed",
      SensorDocument._meta.get_field("sensor_key").db_index)

# T2: sensor_documents service (visibility filter, stats)
from services.sensor_documents import (DOC_TYPES, check_sensor_reference,
                                        document_stats, sensor_documents,
                                        sensors_with_documents)
check("T2a seven document types offered", len(DOC_TYPES) == 7,
      f"got {len(DOC_TYPES)}")
check("T2b check_sensor_reference classifies known vs unknown",
      set(check_sensor_reference(["x", "y"], user=None)) ==
      {"checked", "unknown"})
ref = check_sensor_reference(["x"], user=None)
check("T2c unknown sensor lands in unknown with sensor_url",
      ref["unknown"] and ref["unknown"][0]["sensor_url"].endswith("/projects/sensors/x/"))
stats = document_stats([type("D", (), {"doc_type": "datasheet"}),
                        type("D", (), {"doc_type": "datasheet"}),
                        type("D", (), {"doc_type": "photo"})])
check("T2d document_stats counts by type",
      stats == {"count": 3, "by_type": {"datasheet": 2, "photo": 1}})

# T2e: DB-backed visibility filter (needs a user)
from django.test.utils import setup_test_environment
from django.test.runner import DiscoverRunner
runner = DiscoverRunner(verbosity=0)
old_config = runner.setup_databases()
from core.models import User
try:
    user = User.objects.create_user("op53user", password="pw12345!")
    from django.core.files.uploadedfile import SimpleUploadedFile
    doc_shared = SensorDocument.objects.create(
        user=user, sensor_key="TestSensor",
        file=SimpleUploadedFile("a.txt", b"data"), original_name="a.txt",
        doc_type="datasheet", visibility="lab_shared")
    doc_private = SensorDocument.objects.create(
        user=user, sensor_key="TestSensor",
        file=SimpleUploadedFile("b.txt", b"data"), original_name="b.txt",
        doc_type="manual", visibility="private")
    anon_docs = list(sensor_documents("TestSensor", None))
    check("T2e anonymous sees only lab_shared docs", len(anon_docs) == 1
          and anon_docs[0].visibility == "lab_shared")
    user_docs = list(sensor_documents("TestSensor", user))
    check("T2f owner sees shared + private docs", len(user_docs) == 2)
    check("T2g sensors_with_documents lists lab_shared keys",
          "TestSensor" in sensors_with_documents())
    ref = check_sensor_reference(["TestSensor"], user=user)
    check("T2h known sensor lands in checked with document_count",
          ref["checked"] and ref["checked"][0]["document_count"] == 2)
    check("T2i get_summary exposes url and doc_type",
          doc_shared.get_summary()["doc_type"] == "datasheet"
          and doc_shared.get_summary()["url"])
    # T3: upload/delete views
    from django.test import Client
    if "testserver" not in __import__("django.conf", fromlist=["settings"]).settings.ALLOWED_HOSTS:
        __import__("django.conf", fromlist=["settings"]).settings.ALLOWED_HOSTS.append("testserver")
    client = Client()
    client.login(username="op53user", password="pw12345!")
    upload_url = "/api/projects/sensors/TestSensor/documents/upload/"
    upload = SimpleUploadedFile("op53_test.txt", b"test content")
    resp = client.post(upload_url, {"files": upload, "doc_type": "other",
                                    "visibility": "lab_shared"})
    body = resp.json()
    check("T3a upload view stores the document",
          resp.status_code == 200 and body.get("success")
          and body.get("uploaded") == 1, str(body)[:200])
    new_id = body["documents"][0]["id"]
    resp = client.post(f"/api/projects/sensors/documents/{new_id}/delete/")
    check("T3b delete view removes own document",
          resp.status_code == 200 and resp.json().get("success"))
    resp = client.post(f"/api/projects/sensors/documents/{doc_shared.id}/delete/")
    check("T3c delete removes the shared document",
          resp.status_code == 200 and resp.json().get("success"))
    resp2 = client.post(f"/api/projects/sensors/documents/{doc_shared.id}/delete/")
    check("T3c2 double delete returns not found",
          resp2.status_code == 404)
    anon = Client()
    resp = anon.get("/projects/sensors/TestSensor/")
    check("T3d anonymous sensor page redirects to login",
          resp.status_code in (301, 302))
    resp = anon.post(upload_url, {"files": SimpleUploadedFile("x.txt", b"x")})
    check("T3e anonymous upload rejected (401/redirect/CSRF-403)",
          resp.status_code in (401, 301, 302, 403), f"got {resp.status_code}")
finally:
    runner.teardown_databases(old_config)

# T4: SensorSummaryService (fake LLM client)
from services.sensor_summary import SensorSummaryService


class FakeClient:
    def __init__(self, answer=None, raise_exc=None):
        self.answer = answer
        self.raise_exc = raise_exc

    def chat(self, prompt):
        if self.raise_exc:
            raise self.raise_exc
        return self.answer


svc = SensorSummaryService(client=FakeClient("Der Sensor ist ein NIR-Geraet."))
check("T4a summary returned for plain text",
      svc.summarize("X", {"usage": {"spectrum_count": 3}}) ==
      "Der Sensor ist ein NIR-Geraet.")
svc = SensorSummaryService(client=FakeClient('{"summary": "Kurz."}'))
check("T4b json answer unwrapped",
      svc.summarize("X", {"documents": [{"file_name": "d.pdf"}]}) == "Kurz.")
svc = SensorSummaryService(client=FakeClient(None))
check("T4c empty LLM answer -> None (honest fallback)",
      svc.summarize("X", {"usage": {"spectrum_count": 1}}) is None)
svc = SensorSummaryService(client=FakeClient(None, RuntimeError("ollama down")))
check("T4d LLM unreachable -> None, never raises",
      svc.summarize("X", {"usage": {"spectrum_count": 1}}) is None)
check("T4e no facts at all -> None (nothing to summarize)",
      SensorSummaryService(client=FakeClient("x")).summarize("X", {}) is None)

# T5: routes registered
from django.urls import reverse
try:
    url = reverse("sensor-document-upload", kwargs={"sensor_key": "FooBar"})
    check("T5a upload route registered",
          url == "/api/projects/sensors/FooBar/documents/upload/", url)
except Exception as exc:
    check("T5a upload route registered", False, str(exc))
try:
    url = reverse("sensor-document-delete",
                  kwargs={"document_id": "00000000-0000-0000-0000-000000000000"})
    check("T5b delete route registered",
          url == "/api/projects/sensors/documents/"
          "00000000-0000-0000-0000-000000000000/delete/", url)
except Exception as exc:
    check("T5b delete route registered", False, str(exc))

# T6: templates render the new sections
tpl_dir = Path(__file__).resolve().parent.parent / "django_project/templates"
detail = (tpl_dir / "sensor_detail.html").read_text(encoding="utf-8")
check("T6a sensor page shows KI-Ueberblick block",
      "KI-Ueberblick" in detail and "ki_summary_available" in detail)
check("T6b sensor page honest fallback text present",
      "nicht erreichbar" in detail)
check("T6c sensor page shows documents section",
      "Sensor-Datenbank: Dokumente" in detail and "docUploadResult" in detail)
check("T6d sensor page wires upload URL via {% url %}",
      'url "sensor-document-upload"' in detail)
check("T6e sensor page offers all doc types",
      "for value, label in doc_types" in detail
      and detail.count('<option value="{{ value }}"') == 1)
report = (tpl_dir / "project_report.html").read_text(encoding="utf-8")
check("T6f project report shows sensor reference section",
      "Sensor-Datenbank-Referenz" in report and "sensor_reference.checked" in report)
check("T6g project report links to sensor page for unknown sensors",
      'sensor_url }}#documents' in report)

# T7: preparation report carries the sensor reference check
ingest_src = (Path(__file__).resolve().parent.parent
              / "services" / "project_ingest.py").read_text(encoding="utf-8")
check("T7a build_preparation_report runs check_sensor_reference",
      "check_sensor_reference" in ingest_src)
check("T7b sensor check is degraded-safe (try/except)",
      "Sensor reference check failed" in ingest_src)

print(f"\nOP53 sensor pages matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
