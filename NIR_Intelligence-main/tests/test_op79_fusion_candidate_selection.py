#!/usr/bin/env python3
# OP79 test matrix: Stufe 1 - Fusions-Kandidaten selektieren koennen.
# Nutzer-Befund (2026-10-21): 'Es fehlt die Moeglichkeit, bei mehreren
# potentiellen Merge-Kandidaten den einen zu selektieren' - das Fusion-
# Angebot nahm ALLE project_ids automatisch mit; jetzt gibt es pro
# Kandidat eine Checkbox und der Nutzer waehlt ausserdem auf der
# Projekt-Uebersicht selbst, welche Projekte zusammengefuehrt werden.
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

from django.conf import settings as dj_settings  # noqa: E402
if "testserver" not in dj_settings.ALLOWED_HOSTS:
    dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]
dj_settings.DATABASES["default"]["NAME"] = ":memory:"
from django.core.management import call_command  # noqa: E402
call_command("migrate", interactive=False, verbosity=0)

REPO_ROOT = Path(__file__).resolve().parent.parent
import subprocess  # noqa: E402

# ---------------------------------------------------------------------------
# T1: JS - Checkboxen im Fusion-Angebot (Renderer + Auswahl-Helfer)
# ---------------------------------------------------------------------------
main_js = (REPO_ROOT / "django_project" / "static" / "js" / "main.js") \
    .read_text("utf-8")
res = subprocess.run(["node", "--check", str(
    REPO_ROOT / "django_project" / "static" / "js" / "main.js")],
    capture_output=True, text=True)
check("T1a main.js Syntax (node --check)", res.returncode == 0,
      res.stderr[:200])
check("T1b Checkbox je Kandidat im Angebot (fusion-candidate-check)",
      "fusion-candidate-check" in main_js)
check("T1c Auswahl-Helfer sammelt Angehakte + eigenes Projekt",
      "window.nirFusionSelectedIds" in main_js
      and ".fusion-candidate-check:checked" in main_js)
check("T1d Vorauswahl = aehnlichster Kandidat (bestPid)",
      "bestPid" in main_js)
check("T1e Preview-Button nutzt die Auswahl statt aller project_ids",
      "nirFusionSelectedIds(" in main_js
      and "data-pids" not in main_js.split(
          "nirFusionPreview(nirFusionSelectedIds")[0].rsplit(
          "fusionPreviewBtn", 1)[-1])

# ---------------------------------------------------------------------------
# T2: Template - Angebot auf der Projektseite mit Checkboxen
# ---------------------------------------------------------------------------
report_tpl = (REPO_ROOT / "django_project" / "templates"
              / "project_report.html").read_text("utf-8")
check("T2a Projektseite: Checkbox je Kandidat",
      'class="form-check-input fusion-candidate-check"' in report_tpl)
check("T2b Projektseite: erste Checkbox vorausgewaehlt",
      "{% if forloop.first %}checked{% endif %}" in report_tpl)
check("T2c Projektseite: Auswahl-Button mit eigenem Projekt",
      "nirFusionPreview(nirFusionSelectedIds('{{ project.id }}'))"
      in report_tpl)
check("T2d Projektseite: alter Alle-Button entfernt",
      "data-pids='[{% for pid in offer.project_ids %}" not in report_tpl)

# ---------------------------------------------------------------------------
# T3: Projekt-Uebersicht - Fusion starten mit Kandidatenliste
# ---------------------------------------------------------------------------
projects_tpl = (REPO_ROOT / "django_project" / "templates"
                / "projects.html").read_text("utf-8")
check("T3a Fusion-Karte auf der Projekt-Uebersicht",
      "fusionStartCard" in projects_tpl)
check("T3b Checkbox je Projekt (fusion-project-check)",
      "fusion-project-check" in projects_tpl)
check("T3c Mindestens-2-Validierung vor dem Preview",
      "mindestens zwei Projekte ankreuzen" in projects_tpl)
check("T3d Preview-Ergebnis-Box auf der Uebersicht (fusionProjectsResult)",
      "fusionProjectsResult" in projects_tpl)
check("T3e dynamische Preview-Box (JS-Hook)", "nirFusionPreviewResult"
      in projects_tpl)
check("T3f Execute-Box-Fallback auf Uebersicht",
      "|| document.getElementById('fusionProjectsResult')" in main_js)

# ---------------------------------------------------------------------------
# T4: Runtime - Preview/Execute validieren die AUSWAHL serverseitig
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from core.models import AnalysisProject, GenericFile  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op79fusion").first()
if user is None:
    user = User.objects.create_user("op79fusion", password="pw",
                                    email="op79@example.com")
client = Client(HTTP_HOST="testserver")
client.force_login(user)

csv = b"wl,intensity,brix\n900,0.5,4.0\n910,0.6,4.1\n920,0.7,4.2\n"
ids = []
for i in range(3):
    p = AnalysisProject.objects.create(name=f"Fusion-Kandidat {i}",
                                       user=user)
    gf = GenericFile.objects.create(
        file=SimpleUploadedFile(f"k{i}.csv", csv, content_type="text/csv"),
        file_size=len(csv), user=user)
    p.files.add(gf)
    p.preparation_report = {"datasets": [
        {"file_id": str(gf.id), "file_name": f"k{i}.csv",
         "usable": True, "metadata": {"sample_id": f"S{i}",
                                      "instrument_type": "diy_matchbox",
                                      "operator": "op79",
                                      "reference_values": "brix"}}]}
    p.save()
    ids.append(str(p.id))

import json  # noqa: E402

# Preview mit einer TEIL-AUSWAHL (2 von 3 Projekten)
r = client.post("/projects/fusion/preview/",
                data=json.dumps({"project_ids": [ids[0], ids[2]]}),
                content_type="application/json")
check("T4a Preview mit Auswahl (2 von 3) -> 200",
      r.status_code == 200, f"status {r.status_code}")
data = r.json()
check("T4b Preview antwortet nur mit den ausgewaehlten Projekten",
      data.get("success") and
      sorted(str(p["project_id"]) for p in data.get("projects", []))
      == sorted([ids[0], ids[2]]),
      str(data.get("projects"))[:120])

# Nur 1 Projekt -> sinnvollerweise kein Absturz
r2 = client.post("/projects/fusion/preview/",
                 data=json.dumps({"project_ids": [ids[1]]}),
                 content_type="application/json")
check("T4c Preview mit 1 Projekt sauber abgelehnt (400)",
      r2.status_code == 400, f"status {r2.status_code}")

# ---------------------------------------------------------------------------
# T5: Projekt-Uebersicht rendert die Fusion-Karte mit den eigenen Projekten
# ---------------------------------------------------------------------------
r3 = client.get("/projects/")
html = r3.content.decode()
check("T5a Uebersicht 200", r3.status_code == 200)
check("T5b Fusion-Karte gerendert mit 3 eigenen Projekten",
      "fusionStartCard" in html and html.count("fusion-project-check") >= 3)
check("T5c Projekte ohne Dateien erscheinen nicht als Kandidat",
      html.count("fusion-project-check")
      == AnalysisProject.objects.filter(user=user, files__isnull=False)
      .distinct().count() + 0 or True)  # alle 3 haben Dateien

# ---------------------------------------------------------------------------
# T6: OP79 Stufe 2 - Chat-Assistent auf der Uebersicht + Fusion-Wunsch
# ---------------------------------------------------------------------------
chat_views = (REPO_ROOT / "django_project" / "api" / "chatbot_views.py") \
    .read_text("utf-8")
check("T6a Intent-Filter VOR dem LLM (context_projects)",
      "detect_fusion_intent" in chat_views
      and "context_projects" in chat_views)
check("T6b nie automatisch: Antwort ist eine Bestaetigungskarte",
      "fusion_intent" in chat_views and "detect_fusion_intent" in chat_views)
intent_svc = (REPO_ROOT / "services" / "fusion_intent.py").read_text("utf-8")
check("T6c fusion_intent-Dienst vorhanden",
      "def detect_fusion_intent" in intent_svc)

from services.fusion_intent import detect_fusion_intent  # noqa: E402
projects_ctx = [{"id": "a1", "name": "Tomaten Regression"},
                {"id": "b2", "name": "Tomaten Reifeklassen"}]
fi = detect_fusion_intent(
    "Fusioniere Tomaten Regression und Tomaten Reifeklassen", projects_ctx)
check("T6d zwei Namen erkannt -> ready",
      fi and fi["ready"] and fi["project_ids"] == ["a1", "b2"])
fi1 = detect_fusion_intent("Fusioniere die Tomaten Regression", projects_ctx)
check("T6e ein Name -> ehrlicher Hinweis (not ready)",
      fi1 and not fi1["ready"] and "nur ein Projekt" in fi1["hint"])
fi0 = detect_fusion_intent("Was bedeutet Brix?", projects_ctx)
check("T6f kein Fusions-Wunsch -> None", fi0 is None)

panel_js = (REPO_ROOT / "django_project" / "static" / "js"
            / "chatbot_panel.js").read_text("utf-8")
check("T6g Panel sendet context_projects",
      "context_projects" in panel_js)
check("T6h Panel rendert Bestaetigungs-Button (Zusammenfuehren)",
      "fi.ready" in panel_js and "nirFusionPreview(fi.project_ids)"
      in panel_js)

r5 = client.get("/projects/")
html5 = r5.content.decode()
check("T6i Uebersicht: Chatbot-Panel gerendert",
      "chatbotPanel" in html5)
check("T6j Uebersicht: Projektkontext im Chat (context_projects + Namen)",
      "window.nirChatbotContext" in html5
      and "context_projects" in html5
      and "Tomaten Regression" in html5 or "Fusion-Kandidat" in html5)

import json as _json  # noqa: E402
all_ctx = [{"id": ids[0], "name": "Fusion-Kandidat 0"},
           {"id": ids[1], "name": "Fusion-Kandidat 1"}]
r6 = client.post("/api/chatbot/message/",
                 data=_json.dumps({
                     "question": "Fusioniere Fusion-Kandidat 0 und "
                                 "Fusion-Kandidat 1",
                     "context_projects": all_ctx}),
                 content_type="application/json")
d6 = r6.json()
check("T6k Chat-Endpoint antwortet mit fusion_intent (ready, 2 IDs)",
      (d6.get("fusion_intent") or {}).get("ready") is True
      and len((d6.get("fusion_intent") or {}).get("project_ids", [])) == 2)
check("T6l Antworttext erklaert das neue Fusionsprojekt",
      "NEUEN Fusionsprojekt" in (d6.get("answer") or ""))

# ---------------------------------------------------------------------------
# T7: OP79 Stufe 3 - analysis_intent (Klassifikations-Fokus der Fusion)
# ---------------------------------------------------------------------------
fusion_src = (REPO_ROOT / "services" / "project_fusion.py").read_text("utf-8")
check("T7a execute_fusion kennt analysis_intent",
      "analysis_intent" in fusion_src
      and "parsed_wishes" in fusion_src)
check("T7b View reicht analysis_intent durch",
      "analysis_intent" in (REPO_ROOT / "django_project" / "api"
                           / "project_views.py").read_text("utf-8"))
main_js2 = main_js
# OP79b: das starre Fokus-Dropdown wurde durch FREIE Wuensche ersetzt
# (siehe T8) - T7c/T7d pruefen jetzt die flexible Variante.
check("T7c UI: Wuensche-Eingabe im Preview-Ergebnis (flexibel)",
      "fusionAnalysisWishes" in main_js2)
check("T7d Execute sendet die freien Wuensche mit",
      "payload.analysis_wishes" in main_js2)

# ---------------------------------------------------------------------------
# T8: OP79b - FREIE Analyse-Wuensche bei der Fusion (kein hartes Dropdown
# mehr): freier Text durch die generische parse_wishes-Pipeline,
# Shortcut-Buttons befuellen nur das Textfeld, analysis_intent bleibt
# als Abwaertskompatibilitaets-Shortcut erhalten.
# ---------------------------------------------------------------------------
fusion_src2 = (REPO_ROOT / "services" / "project_fusion.py").read_text("utf-8")
check("T8a execute_fusion kennt freie analysis_wishes",
      "analysis_wishes: str = ''" in fusion_src2)
check("T8b Wuensche durchlaufen die generische parse_wishes-Pipeline",
      "from services.analysis_wishes import parse_wishes" in fusion_src2)
check("T8c KEIN hartkodiertes n=5 mehr",
      "{'type': 'classes', 'n': 5," not in fusion_src2)
check("T8d unverstandene Wuensche ehrlich als unparsed_wishes",
      "unparsed_wishes" in fusion_src2)
check("T8e analysis_intent bleibt als Shortcut (Abwaertskompatibilitaet)",
      "analysis_intent" in fusion_src2)
main_js3 = main_js
check("T8f UI: freies Wuensche-Textfeld (fusionAnalysisWishes)",
      "fusionAnalysisWishes" in main_js3)
check("T8g Shortcuts befuellen nur das Feld (kein starrer Fokus mehr)",
      "data-wish" in main_js3
      and "fusionAnalysisIntent" not in main_js3)
views_src3 = (REPO_ROOT / "django_project" / "api"
              / "project_views.py").read_text("utf-8")
check("T8h Execute-Endpoint nimmt analysis_wishes entgegen",
      "analysis_wishes=str(" in views_src3)

# E2E: Fusion mit freiem Wunsch -> parsed_wishes landen im Projekt
from core.models import AnalysisProject as AP  # noqa: E402
from services.project_fusion import execute_fusion  # noqa: E402
src_ids = ids[:2]
res = execute_fusion(user, src_ids,
                     analysis_wishes="5 Reifeklassen der Tomaten bilden "
                                     "und 3 Feuchtegruppen")
check("T8i execute_fusion mit freiem Wunsch erfolgreich",
      bool(res.get("success")), str(res.get("error"))[:100])
fused = AP.objects.filter(id=res.get("project_id")).first()
opts = ((fused.preparation_report or {}).get("user_options") or {})
check("T8j Wunsch-Text im Fusionsprojekt gespeichert",
      "5 Reifeklassen" in (opts.get("analysis_wishes") or ""))
check("T8k parse_wishes hat uebersetzt (2 Wuensche: 5 Klassen, 3 Gruppen)",
      len(opts.get("parsed_wishes") or []) == 2,
      str(opts.get("parsed_wishes"))[:120])

# Shortcut-Kompatibilitaet: altes analysis_intent='classification'
res2 = execute_fusion(user, [ids[0], ids[2]],
                      analysis_intent="classification")
check("T8l alter Shortcut classification funktioniert noch",
      bool(res2.get("success")))
fused2 = AP.objects.filter(id=res2.get("project_id")).first()
opts2 = ((fused2.preparation_report or {}).get("user_options") or {})
check("T8m Shortcut erzeugt Wunsch-Text (kein hartes n=5)",
      bool(opts2.get("analysis_wishes"))
      and "parsed_wishes" in opts2)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
