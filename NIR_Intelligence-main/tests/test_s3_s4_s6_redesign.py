"""S3/S4/S6 verification: quick-check result panel, next-step hint, chatbot panel.

S3: the spectra page renders the analysis result inline (no redirect to the
    orphaned /analysis/ page); spectra.js contains the result panel renderer.
S4: the workflow stepper shows a plain-text next-step hint derived in
    workflow_context.project_workflow_context (no dead ends).
S6: a reusable contextual chatbot panel is embedded in the analysis results
    page and the project report; the existing /chatbot/ solo page remains.
"""
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TEMPLATES = os.path.join(REPO_ROOT, 'django_project', 'templates')
STATIC_JS = os.path.join(REPO_ROOT, 'django_project', 'static', 'js')

results = []


def check(name, condition):
    results.append((name, bool(condition)))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def test_s3_result_panel():
    spectra_tpl = read(os.path.join(TEMPLATES, 'spectra.html'))
    spectra_js = read(os.path.join(STATIC_JS, 'spectra.js'))
    check("T1a spectra page contains the quick-check result section (S3)",
          'quickCheckResultSection' in spectra_tpl)
    check("T1b result section starts hidden and is revealed by JS (S3)",
          'id="quickCheckResultSection" hidden' in spectra_tpl)
    check("T1c spectra.js renders the crew response inline instead of redirecting (S3)",
          'showQuickCheckResult' in spectra_js)
    check("T1d no hard redirect to /analysis/ remains in single-spectrum analysis (S3)",
          "window.location.href = '/analysis/'" not in spectra_js)
    check("T1e result panel shows metadata quality and data quality (S3)",
          'metadata_quality' in spectra_js and 'spectral_analysis' in spectra_js)


def test_s4_next_step_hint():
    stepper = read(os.path.join(TEMPLATES, 'workflow_stepper.html'))
    ctx = read(os.path.join(REPO_ROOT, 'django_project', 'api', 'workflow_context.py'))
    check("T2a stepper renders the plain-text next-step hint (S4)",
          'workflow_context.next_hint' in stepper)
    check("T2b workflow_context derives next_hint for the first pending station (S4)",
          "'next_hint': _next_step_hint(project, stations)" in ctx)
    check("T2c hints exist for all six stations (S4)",
          all(str(n) in ctx for n in range(1, 7)) and 'NEXT_STEP_HINTS' in ctx)
    check("T2d completed projects get a completion hint (S4)",
          'Alle Schritte abgeschlossen' in ctx)


def test_s6_chatbot_panel():
    panel = read(os.path.join(TEMPLATES, 'chatbot_panel.html'))
    panel_js = read(os.path.join(STATIC_JS, 'chatbot_panel.js'))
    analysis_tpl = read(os.path.join(TEMPLATES, 'analysis.html'))
    report_tpl = read(os.path.join(TEMPLATES, 'project_report.html'))
    check("T3a reusable chatbot panel template exists (S6)",
          os.path.exists(os.path.join(TEMPLATES, 'chatbot_panel.html')))
    check("T3b panel posts to the existing /api/chatbot/message/ endpoint (S6)",
          '/api/chatbot/message/' in panel_js)
    check("T3c panel sends the contextual analysis results (S6)",
          'nirChatbotContext' in panel_js)
    check("T3d analysis results page embeds the panel (S6)",
          "include 'chatbot_panel.html'" in analysis_tpl)
    check("T3e project report embeds the panel for released projects (S6)",
          "include 'chatbot_panel.html'" in report_tpl)
    check("T3f project report passes crew results as context via json_script (S6)",
          "json_script:'crewAnalysisJson'" in report_tpl)
    check("T3g analysis.js provides the latest result as chatbot context (S6)",
          'nirChatbotContext' in read(os.path.join(STATIC_JS, 'analysis.js')))
    check("T3h solo /chatbot/ page remains as fallback (S6)",
          os.path.exists(os.path.join(TEMPLATES, 'chatbot.html')))


def test_op60_fixes():
    report_tpl = read(os.path.join(TEMPLATES, 'project_report.html'))
    check("T4a KI-Vorschlags-Verdrahtung laeuft beim Seitenladen, nicht im Decision-Handler (OP60-Fix)",
          'OP60-Fix' in report_tpl and
          report_tpl.index('OP60-Fix') < report_tpl.index("document.addEventListener('click'"))
    check("T4b Verdrahtung sendet an ki-accept-Endpoint mit sichtbarem Feedback (OP60-Fix)",
          "ki-accept" in report_tpl and 'ki-feedback' in report_tpl)
    check("T4c Charts haben ein zugeordnetes Erklaerungs-Dropdown (OP60)",
          'Was zeigt dieses Diagramm?' in report_tpl)
    check("T4d Erklaerungs-Dropdown nutzt den chart_explanation-Filter (OP60)",
          'chart_explanation' in report_tpl)
    expl = read(os.path.join(REPO_ROOT, 'django_project', 'core', 'templatetags',
                             'chart_explanations.py'))
    check("T4e Erklaerungen decken PCA-, Similarity-, Kalibrations- und XAI-Keys ab (OP60)",
          all(k in expl for k in ('score_plot', 'similarity_top3', 'rmse_cv', 'feature_importance')))
    check("T4f unbekannte Chart-Keys erhalten einen generischen Hinweis (OP60)",
          'GENERIC_EXPLANATION' in expl)


def test_s7_s8_redesign():
    base = read(os.path.join(TEMPLATES, 'base.html'))
    check("T5a /files/ removed from the Diagnose submenu (S7)",
          'href="/files/"' not in base)
    check("T5b files page itself remains reachable (S7, OP8)",
          os.path.exists(os.path.join(TEMPLATES, 'files.html')))
    check("T5c dead workflow display layer removed: views/urls/templates (S7)",
          not os.path.exists(os.path.join(REPO_ROOT, 'django_project', 'api', 'workflow_display_views.py')) and
          not os.path.exists(os.path.join(REPO_ROOT, 'django_project', 'api', 'workflow_display_urls.py')) and
          not os.path.exists(os.path.join(REPO_ROOT, 'django_project', 'api', 'workflow_views.py')) and
          not os.path.exists(os.path.join(REPO_ROOT, 'django_project', 'api', 'workflow_urls.py')) and
          not os.path.exists(os.path.join(TEMPLATES, 'workflow_list.html')) and
          not os.path.exists(os.path.join(TEMPLATES, 'workflow_results.html')))
    cv = read(os.path.join(REPO_ROOT, 'django_project', 'api', 'crewai_views.py'))
    check("T5d start_analysis supports async payload flag (S8)",
          "payload.get('async')" in cv and 'HTTP_202_ACCEPTED' in cv)
    check("T5e quick-check job registry + thread run in background (S8)",
          'QUICK_JOBS' in cv and 'threading.Thread' in cv)
    check("T5f quick-status endpoint registered (S8)",
          'quick-status' in read(os.path.join(REPO_ROOT, 'django_project', 'api', 'crewai_urls.py')))
    check("T5g shared response builder keeps sync+async shape identical (S8)",
          'def _build_analysis_response' in cv)
    sj = read(os.path.join(STATIC_JS, 'spectra.js'))
    check("T5h spectra quick check runs async with progress panel (S8)",
          'showQuickCheckProgress' in sj and "analysisRequest.async = true" in sj)
    check("T5i spectra polls quick-status and renders into the S3 panel (S8)",
          "pollQuickCheck" in sj and '/api/crewai/analysis/quick-status/' in sj)


def main():
    test_s3_result_panel()
    test_s4_next_step_hint()
    test_s6_chatbot_panel()
    test_op60_fixes()
    test_s7_s8_redesign()
    failed = [name for name, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        for name in failed:
            print(f"FAILED: {name}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == '__main__':
    main()
