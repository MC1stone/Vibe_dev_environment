# OP54 test matrix: DIY project detail pages (same pattern as sensor pages)
# - one page per curated DIY project with prepared link info
# - document upload/delete per DIY project (sensor_key diy_<slug>)
# - asynchronous KI overview via sensor-summary route
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "django_project"))

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


def main():
    django.setup()
    from django.conf import settings as dj_settings

    # T1: curated projects carry slugs + descriptions
    from api.project_views import DiySpectrometerView, DiyDetailView
    projects = DiySpectrometerView.DIY_PROJECTS
    check("T1a five projects with unique slugs",
          len(projects) == 5
          and len({p.get("slug") for p in projects}) == 5,
          str([p.get("slug") for p in projects]))
    check("T1b all projects carry a prepared description (>=150 chars)",
          all(len(p.get("description") or "") >= 150 for p in projects),
          str([len(p.get("description") or "") for p in projects]))
    check("T1c get_project resolves slug",
          DiyDetailView.get_project("open-spectrometer")["name"]
          == "OpenSpectrometer")
    check("T1d get_project returns None for unknown slug",
          DiyDetailView.get_project("does-not-exist") is None)
    check("T1e sensor_key prefix diy_",
          DiyDetailView._sensor_key("open-spectrometer")
          == "diy_open-spectrometer")

    # T2: routes
    from django.urls import reverse, resolve
    url = reverse("sensor-diy-detail", kwargs={"slug": "open-spectrometer"})
    check("T2a diy detail route registered",
          url == "/api/projects/sensors/diy/open-spectrometer/", url)
    match = resolve("/api/projects/sensors/diy/open-spectrometer/")
    check("T2b route resolves to DiyDetailView",
          match.func is not None)

    # T3: view behaviour with DB
    from django.test import Client
    from django.test.runner import DiscoverRunner
    from django.test.utils import setup_test_environment

    setup_test_environment()
    if "testserver" not in dj_settings.ALLOWED_HOSTS:
        dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]

    runner = DiscoverRunner(verbosity=0)
    old_config = runner.setup_databases()
    try:
        from core.models import User, SensorDocument
        from django.core.files.uploadedfile import SimpleUploadedFile
        user, _ = User.objects.get_or_create(username="op54user")
        if not user.has_usable_password() or not user.check_password("pw12345!"):
            user.set_password("pw12345!")
            user.save()

        anon = Client()
        resp = anon.get("/projects/sensors/diy/open-spectrometer/")
        check("T3a anonymous diy detail redirects to login",
              resp.status_code in (301, 302))

        client = Client()
        client.login(username="op54user", password="pw12345!")
        resp = client.get("/projects/sensors/diy/open-spectrometer/")
        check("T3b diy detail page renders (200)",
              resp.status_code == 200, f"got {resp.status_code}")
        html = resp.content.decode()
        check("T3c page shows KI-Ueberblick async box",
              "kiSummaryBox" in html)
        check("T3d page shows prepared description",
              "Open-Source-Spektrometer" in html)
        check("T3e page renders csrfmiddlewaretoken input",
              'name="csrfmiddlewaretoken"' in html)
        check("T3f page wires summary URL for diy sensor_key",
              "diy_open-spectrometer/summary/" in html)

        resp = client.get("/projects/sensors/diy/unknown-slug/")
        check("T3g unknown slug returns 404",
              resp.status_code == 404, f"got {resp.status_code}")

        # T4: upload + delete per DIY project
        upload_url = ("/api/projects/sensors/diy_open-spectrometer/"
                      "documents/upload/")
        f = SimpleUploadedFile("op54_manual.pdf", b"%PDF-1.4 manual",
                               content_type="application/pdf")
        resp = client.post(upload_url, {"files": f, "doc_type": "manual"})
        body = resp.json()
        check("T4a upload stores document under diy sensor_key",
              resp.status_code == 200 and body.get("success")
              and body["documents"][0]["sensor_key"] == "diy_open-spectrometer",
              str(body)[:200])
        new_id = body["documents"][0]["id"]
        resp = client.post(f"/api/projects/sensors/documents/{new_id}/delete/")
        check("T4b delete removes diy document",
              resp.status_code == 200 and resp.json().get("success"))

        # T5: SensorSummaryService carries the DIY description
        from services.sensor_summary import SensorSummaryService

        class FakeClient:
            def chat(self, prompt):
                self.prompt = prompt
                return "Zusammenfassung."

        fake = FakeClient()
        svc = SensorSummaryService(client=fake)
        desc = DiyDetailView.get_project("public-lab-desktop")["description"]
        result = svc.summarize("diy_public-lab-desktop",
                               {"description": desc})
        check("T5a summary returned for diy facts", result == "Zusammenfassung.")
        check("T5b diy description reaches the LLM prompt",
              "beschreibung" in fake.prompt and "Public Lab" in fake.prompt)

        # T6: summary view handles diy keys
        from django.test import Client as C2
        c2 = C2()
        c2.login(username="op54user", password="pw12345!")
        resp = c2.get("/api/projects/sensors/diy_open-spectrometer/summary/")
        check("T6a summary endpoint answers for diy key",
              resp.status_code == 200 and resp.json().get("success") is True,
              f"got {resp.status_code}")
    finally:
        runner.teardown_databases(old_config)

    # T7: templates
    tpl_dir = (Path(__file__).resolve().parent.parent
               / "django_project" / "templates")
    detail = (tpl_dir / "sensor_diy_detail.html").read_text(encoding="utf-8")
    check("T7a diy detail template exists with async KI block",
          "kiSummaryBox" in detail and 'url "sensor-summary"' in detail)
    check("T7b diy detail template wires upload + delete",
          'url "sensor-document-upload"' in detail
          and 'url "sensor-document-delete"' in detail)
    check("T7c diy detail template uses getCsrfToken helper",
          "getCsrfToken" in detail)
    overview = (tpl_dir / "sensor_diy.html").read_text(encoding="utf-8")
    check("T7d overview links to detail pages",
          "/projects/sensors/diy/{{ project.slug }}/" in overview)

    print(f"\nOP54 diy detail pages matrix: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")
    main()
