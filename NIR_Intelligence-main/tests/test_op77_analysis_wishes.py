#!/usr/bin/env python3
# OP77 test matrix: Freie Analyse-Wuensche beim Upload (generisch).
# Nutzer-Wunsch: 'z. B. 5 Reifeklassen der Tomaten' + Nutzer-Korrektur:
# 'Der Nutzer koennte auch andere Wuensche eingeben - keine Hardcodierung
# der Loesung, nur die Funktion!'
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

# ---------------------------------------------------------------------------
# T1: parse_wishes - generisch, verschiedene Formulierungen
# ---------------------------------------------------------------------------
from services.analysis_wishes import (  # noqa: E402
    apply_wishes_to_dataset, build_target_classes, parse_wishes,
)

cases = [
    ("5 Reifeklassen der Tomaten bilden", [('classes', 5)], 0),
    ("3 Feuchtegruppen", [('classes', 3)], 0),
    ("erstelle die Auswertung und bilde dazu 5 Reifeklassen",
     [('classes', 5)], 1),
    ("fuenf Stufen aus dem Brix", [('classes', 5)], 0),
    ("bild 4 Kategorien", [('classes', 4)], 0),
    ("zeige mir den besten Sensor", [], 1),
    ("", [], 0),
]
for text, expected, exp_unparsed in cases:
    r = parse_wishes(text)
    got = [(w['type'], w['n']) for w in r['wishes']]
    check(f"T1 parse: {text[:40]!r}", got == expected
          and len(r['unparsed']) == exp_unparsed,
          f"got={got} unparsed={r['unparsed']}")

# T2: unbekannter Wunsch -> ehrlich gemeldet, nie still ignoriert
r = parse_wishes("5 Reifeklassen und zeig die Top-Wellenlaengen")
check("T2a gemischter Text: bekannter Wunsch erkannt",
      ('classes', 5) in [(w['type'], w['n']) for w in r['wishes']])
check("T2b unbekannter Teil ehrlich in unparsed",
      len(r['unparsed']) == 1 and 'Top-Wellenlaengen' in r['unparsed'][0])

# ---------------------------------------------------------------------------
# T3: build_target_classes - zielagnostisch (nicht 'Reife'-hardcodiert)
# ---------------------------------------------------------------------------
import numpy as np  # noqa: E402
rng = np.random.default_rng(42)
brix = list(4.0 + rng.beta(2, 3, 500) * 4.0)
cls = build_target_classes(brix, 5, 'Brix')
check("T3a 5 Klassen aus Brix", cls.get('n_classes') == 5)
check("T3b Klassenlabels nennen das ZIEL (nicht 'Reife')",
      all('Brix' in l for l in cls['labels']), str(cls['labels'][:2]))
feuchte = list(10.0 + rng.normal(0, 2, 500))
cls2 = build_target_classes(feuchte, 3, 'Feuchte')
check("T3c gleiches Funktion fuer Feuchte (kein Ziel-Hardcoding)",
      cls2.get('n_classes') == 3
      and all('Feuchte' in l for l in cls2['labels']))
check("T3d zu duenne Daten -> ehrlich leer",
      build_target_classes([1.0, 2.0], 5) == {})
check("T3e konstanter Wert -> ehrlich leer",
      build_target_classes([5.0] * 100, 5) == {})

# ---------------------------------------------------------------------------
# T4: apply_wishes_to_dataset - zeilensynchrone Klassen je Datensatz
# ---------------------------------------------------------------------------
dataset = {'calibration_samples': [[float(i), float(i + 1)]
                                   for i in range(100)],
           'reference_values': brix[:100],
           'metadata': {'target_name': 'Brix'}}
wishes = parse_wishes('5 Reifeklassen bilden')['wishes']
applied = apply_wishes_to_dataset(dataset, wishes)
check("T4a Wunsch am Datensatz angewandt", len(applied) == 1)
check("T4b derived_classes dokumentiert (Wish, Kanten, Verteilung)",
      'derived_classes' in dataset and dataset['derived_classes'].get('n_classes') == 5
      and 'distribution' in dataset['derived_classes'])
check("T4c classification_samples/labels zeilensynchron",
      len(dataset['classification_samples'])
      == len(dataset['classification_labels']) == 100)
check("T4d class_labels = unique Klassenliste",
      len(dataset['class_labels']) == 5)

# ohne Referenzwerte: ehrlich nichts angewandt
d2 = {'calibration_samples': [[1.0, 2.0]] * 20}
check("T4e ohne Referenzwerte kein Fake",
      apply_wishes_to_dataset(d2, wishes) == [])

# ---------------------------------------------------------------------------
# T5: Struktur - kein 'ripeness'-Hardcoding mehr im Pfad
# ---------------------------------------------------------------------------
ingest_src = (REPO_ROOT / "services" / "project_ingest.py").read_text("utf-8")
views_src = (REPO_ROOT / "django_project" / "api"
             / "project_views.py").read_text("utf-8")
agent_src = (REPO_ROOT / "agents"
             / "statistical_analysis_agent.py").read_text("utf-8")
crew_src = (REPO_ROOT / "services" / "project_crew.py").read_text("utf-8")
check("T5a services/analysis_wishes.py existiert (generisches Modul)",
      (REPO_ROOT / "services" / "analysis_wishes.py").exists())
check("T5b kein ripeness_classes-Modul mehr",
      not (REPO_ROOT / "services" / "ripeness_classes.py").exists())
check("T5c View nimmt freies Textfeld analysis_wishes",
      "analysis_wishes" in views_src
      and "parse_wishes" in views_src)
check("T5d Ingest: parsed_wishes + unparsed-Warnungen",
      "parsed_wishes" in ingest_src and "unparsed_wishes" in ingest_src)
check("T5e Agent: derived_classification (generic), keine Reife-Refs",
      "derived_classification" in agent_src
      and "ripeness" not in agent_src)
check("T5f Crew: derived_classes-Flag (generic)",
      "derived_classes" in crew_src)
check("T5g unbekannte Wuensche als offene Fragen (Ehrlichkeit)",
      "noch nicht" in ingest_src and "unterstuetzt" in ingest_src)

# ---------------------------------------------------------------------------
# T6: Runtime - Upload-Modal + Create-Endpoint
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op77wish").first()
if user is None:
    user = User.objects.create_user("op77wish", password="pw",
                                    email="w77@example.com")
client = Client(HTTP_HOST='testserver')
client.force_login(user)
r = client.get('/projects/')
html = r.content.decode()
check("T6a Upload-Modal hat freies Wuensche-Feld (analysisWishes)",
      'analysisWishes' in html and 'Analyse-W' in html)
check("T6b JS sendet analysis_wishes",
      "payload.analysis_wishes = wishesVal" in html)

# Template vom Statistik-Agenten: Zusatz-Klassifikation im Result
check("T6c Agent-Ergebnis-Schluessel derived_class_analysis",
      "derived_class_analysis" in agent_src)

# OP77-Fix: der Bericht muss die Zusatz-Konfusionsmatrix auch im
# regression-Modus rendern (derived_class_analysis), nicht nur im
# classification-Zweig
report_src = (REPO_ROOT / "services" / "project_report.py").read_text("utf-8")
check("T6d Bericht rendert derived_class_analysis (HTML)",
      "data_dict.get('derived_class_analysis')" in report_src)
check("T6e Bericht rendert derived_class_analysis (Markdown)",
      "data.get('derived_class_analysis')" in report_src)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
