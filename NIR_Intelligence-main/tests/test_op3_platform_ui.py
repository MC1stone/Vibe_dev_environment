#!/usr/bin/env python3
# NIR Intelligence Platform - OP3 test matrix: platform UI
# Verifies the file upload wiring, the chatbot UI and the ILIAS UI:
# Django template syntax checks (offline, via django.template.Engine),
# URL routing contracts and the fetch endpoints/payloads used by the
# templates. No network, no running containers.

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0
FAILED = []

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "django_project", "templates")


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        FAILED.append(name)
        print(f"[FAIL] {name} {detail}")


def check_template_syntax(template_name):
    """Compile a template with the Django engine; True when valid."""
    try:
        import django
        from django.template import Engine

        if not django.conf.settings.configured:
            django.conf.settings.configure(
                TEMPLATES=[{
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [TEMPLATES_DIR],
                    "APP_DIRS": False,
                    "OPTIONS": {},
                }],
                INSTALLED_APPS=[],
                USE_TZ=True,
            )
        engine = Engine(
            dirs=[TEMPLATES_DIR],
            libraries={
                "static": "django.templatetags.static",
            },
        )
        template = engine.get_template(template_name)
        return template is not None
    except Exception as exc:
        print(f"      template error in {template_name}: {exc}")
        return False


def main():
    # ---------- T1: template syntax ----------
    check("T1a base.html template syntax", check_template_syntax("base.html"))
    check("T1b files.html template syntax", check_template_syntax("files.html"))
    check("T1c chatbot.html template syntax", check_template_syntax("chatbot.html"))
    check("T1d ilias.html template syntax", check_template_syntax("ilias.html"))
    check("T1e upload_files.html removed (broken template)",
          not os.path.exists(os.path.join(TEMPLATES_DIR, "upload_files.html")))

    # ---------- T2: routing ----------
    urls_path = os.path.join(os.path.dirname(__file__), "..", "django_project", "nir_web", "urls.py")
    with open(urls_path, encoding="utf-8") as f:
        urls_src = f.read()
    check("T2a /chatbot/ route present", "chatbot/" in urls_src and "chatbot.html" in urls_src)
    check("T2b /ilias/ route present", "ilias/" in urls_src and "ilias.html" in urls_src)

    # ---------- T3: files.html upload wiring ----------
    with open(os.path.join(TEMPLATES_DIR, "files.html"), encoding="utf-8") as f:
        files_src = f.read()
    check("T3a uploadFiles posts to /api/files/upload/",
          "fetch('/api/files/upload/'" in files_src)
    check("T3b loadFiles fetches /api/files/",
          "fetch('/api/files/'" in files_src)
    check("T3c CSRF token helper present", "getCsrfToken" in files_src and "csrftoken" in files_src)
    check("T3d FormData carries files", "formData.append('files'" in files_src)
    check("T3e auto_analyze flag sent", "auto_analyze" in files_src)
    check("T3f single-file analyze wired",
          "fetch('/api/files/' + fileId + '/analyze/'" in files_src)
    check("T3g multi-file analyze wired", "'/api/files/analyze-multiple/'" in files_src)
    check("T3h delete-multiple wired", "'/api/files/delete-multiple/'" in files_src)
    check("T3i no remaining upload stub", "console.log('Uploading files" not in files_src)
    check("T3j no remaining load stub", "console.log('Loading files" not in files_src)
    check("T3k stats ids wired", "totalFiles" in files_src and "validFiles" in files_src)

    # ---------- T4: chatbot UI contract ----------
    with open(os.path.join(TEMPLATES_DIR, "chatbot.html"), encoding="utf-8") as f:
        chat_src = f.read()
    check("T4a chatbot posts to /api/chatbot/message/",
          "fetch('/api/chatbot/message/'" in chat_src)
    check("T4b payload uses question field", "question: question" in chat_src)
    check("T4c degraded handling present", "degraded" in chat_src)
    check("T4d rag sources rendered", "rag_sources" in chat_src and "qdrant_rag" in chat_src)
    check("T4e status endpoint wired", "fetch('/api/chatbot/status/'" in chat_src)
    check("T4f CSRF token helper present", "getCsrfToken" in chat_src)

    # ---------- T5: ilias UI contract ----------
    with open(os.path.join(TEMPLATES_DIR, "ilias.html"), encoding="utf-8") as f:
        ilias_src = f.read()
    check("T5a ilias sync posts to /api/ilias/learning-paths/sync/",
          "fetch('/api/ilias/learning-paths/sync/'" in ilias_src)
    check("T5b payload uses title and modules",
          "title:" in ilias_src and "modules:" in ilias_src)
    check("T5c objectives mapped", "objectives" in ilias_src)
    check("T5d status endpoint wired", "fetch('/api/ilias/status/'" in ilias_src)
    check("T5e CSRF token helper present", "getCsrfToken" in ilias_src)

    # ---------- T6: navigation ----------
    with open(os.path.join(TEMPLATES_DIR, "base.html"), encoding="utf-8") as f:
        base_src = f.read()
    check("T6a chatbot nav entry", "/chatbot/" in base_src and "Chatbot" in base_src)
    check("T6b ilias nav entry", "/ilias/" in base_src and "ILIAS" in base_src)

    # ---------- T7: upload view redirect ----------
    wf_path = os.path.join(os.path.dirname(__file__), "..", "django_project", "api", "workflow_display_views.py")
    with open(wf_path, encoding="utf-8") as f:
        wf_src = f.read()
    check("T7a upload_view redirects to files page", "HttpResponseRedirect('/files/')" in wf_src)

    # ---------- T8: backend view contracts unchanged ----------
    fv_path = os.path.join(os.path.dirname(__file__), "..", "django_project", "api", "file_views.py")
    with open(fv_path, encoding="utf-8") as f:
        fv_src = f.read()
    check("T8a FileUploadView requires files field", "getlist('files')" in fv_src)
    check("T8b analyze-multiple uses file_ids", "file_ids" in fv_src)
    check("T8c delete-multiple uses file_ids", fv_src.count("file_ids") >= 2)
    cv_path = os.path.join(os.path.dirname(__file__), "..", "django_project", "api", "chatbot_views.py")
    with open(cv_path, encoding="utf-8") as f:
        cv_src = f.read()
    check("T8d chatbot view expects question", "question" in cv_src and "question is required" in cv_src)
    iv_path = os.path.join(os.path.dirname(__file__), "..", "django_project", "api", "ilias_views.py")
    with open(iv_path, encoding="utf-8") as f:
        iv_src = f.read()
    check("T8e ilias sync view expects title", "title" in iv_src)
    rs_path = os.path.join(os.path.dirname(__file__), "..", "django_project", "port_manager",
                           "management", "commands", "runserver_free.py")
    check("T8f runserver_free command exists (port manager start)", os.path.exists(rs_path))
    if os.path.exists(rs_path):
        with open(rs_path, encoding="utf-8") as f:
            rs_src = f.read()
        check("T8g runserver_free uses the port management agent",
              "PortManagementAgentCrewAI" in rs_src and "find_free_port" in rs_src)
        check("T8h runserver_free falls back when the preferred port is taken",
              "already in use" in rs_src)
        check("T8i runserver_free binds loopback only by default",
              "127.0.0.1" in rs_src)

    # ---------- T9: regression spot checks ----------
    ok_op1 = os.path.exists(os.path.join(os.path.dirname(__file__), "test_op1_embedding_pipeline.py"))
    check("T9a OP1 test matrix present", ok_op1)
    ok_op2 = os.path.exists(os.path.join(os.path.dirname(__file__), "test_op2_ilias_token_flow.py"))
    check("T9b OP2 test matrix present", ok_op2)
    ok_s6 = os.path.exists(os.path.join(os.path.dirname(__file__), "test_s6_chatbot.py"))
    check("T9c S6 test matrix present", ok_s6)

    print()
    if FAIL:
        print(f"{FAILED}")
        print(f"{FAIL} tests FAILED")
        return 1
    print(f"{PASS}/{PASS + FAIL} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
