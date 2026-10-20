#!/usr/bin/env python3
# OP72 test matrix: Einfuehrungs-Seite 'Richtig messen' unter Start.
# Nutzer-Anforderung (2026-10-20): INTRO-Seite unter Start, die erklaert,
# wie Spektroskopie-Messungen durchgefuehrt werden, was zu beachten ist
# (Licht!) und welche Metadaten festzuhalten sind; Beruecksichtigung der
# Sensor-Datenbank; einsteiger-verstaendlich; illustrative Bilder;
# Schwarz/Weiss-Abgleich erklärt (inkl. Referenz-Vertrag OP68).
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
dj_settings.DATABASES["default"].setdefault("ATOMIC_REQUESTS", False)
from django.core.management import call_command  # noqa: E402
call_command("migrate", interactive=False, verbosity=0)

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# T1: Struktur - View, URL, Template, Start-Link
# ---------------------------------------------------------------------------
import py_compile  # noqa: E402

views_path = REPO_ROOT / "django_project" / "api" / "dashboard_views.py"
urls_path = REPO_ROOT / "django_project" / "nir_web" / "urls.py"
tpl_path = (REPO_ROOT / "django_project" / "templates"
            / "intro_spectroscopy.html")
start_tpl = (REPO_ROOT / "django_project" / "templates"
             / "dashboard_start.html")

check("T1a IntroSpectroscopyView vorhanden", views_path.exists()
      and "class IntroSpectroscopyView" in views_path.read_text("utf-8"))
for p in (views_path, urls_path):
    try:
        py_compile.compile(str(p), doraise=True)
        check(f"T1b {p.name} kompiliert", True)
    except Exception as exc:
        check(f"T1b {p.name} kompiliert", False, str(exc))
urls_src = urls_path.read_text("utf-8")
check("T1c URL /intro/spectroscopy/ registriert (de + i18n, 2x)",
      urls_src.count("intro/spectroscopy/") == 2
      and "IntroSpectroscopyView" in urls_src)
check("T1d Template existiert", tpl_path.exists())
start_src = start_tpl.read_text("utf-8")
check("T1e Startseite verlinkt die Einfuehrung",
      "/intro/spectroscopy/" in start_src
      and "Zur Einführung" in start_src)

# T2: Template-Inhalt (fachliche Anforderung)
tpl_src = tpl_path.read_text("utf-8")
check("T2a Grundprinzip erklaert", "Grundprinzip" in tpl_src
      and "reflektiert" in tpl_src)
check("T2b Lichtverhältnisse (richtig/haeufige Fehler)",
      "Licht und Lichtverhältnisse" in tpl_src
      and "So geht's richtig" in tpl_src and "Häufige Fehler" in tpl_src)
check("T2c Schwarz/Weiss-Abgleich mit Formel + >=50 Vertrag",
      "Schwarz/Weiß-Abgleich" in tpl_src
      and "( Messung − Schwarz ) / ( Weiß − Schwarz )" in tpl_src
      and "50 Wiederholungen" in tpl_src)
check("T2d Metadaten-Deklaration (reference_type/n_repeats)",
      "reference_type" in tpl_src and "n_repeats" in tpl_src
      and "reference_artifact" in tpl_src)
check("T2e Metadaten-Pflichtfelder (Proben-ID, Referenzwert, Operator)",
      all(k in tpl_src for k in ("Proben-ID", "Referenzwert", "Operator")))
check("T2f Setting-Optionen aus der Sensor-DB (Template-Loop)",
      "setting_options" in tpl_src and "{% for opt in setting_options %}"
      in tpl_src)
check("T2g Sensor-Loop aus der Sensor-DB", "{% for s in sensors %}"
      in tpl_src and "Zur Sensor-Datenbank" in tpl_src)
check("T2h Illustrationen vorhanden (SVG, offline-faehig)",
      tpl_src.count("<svg") >= 2 and "http" not in tpl_src[:2000])
check("T2i Checkliste fuer die erste Messung", "Checkliste" in tpl_src
      and "{% for step in checklist %}" in tpl_src)

# ---------------------------------------------------------------------------
# T3: Runtime - Seite rendert mit echten Sensor-Daten
# ---------------------------------------------------------------------------
from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.urls import reverse  # noqa: E402

User = get_user_model()
user = User.objects.filter(username="op72intro").first()
if user is None:
    user = User.objects.create_user("op72intro", password="pw",
                                    email="op72@example.com")
client = Client(HTTP_HOST='testserver')
client.force_login(user)
url = reverse('intro-spectroscopy')
r = client.get(url)
check("T3a intro page 200", r.status_code == 200, f"status {r.status_code}")
html = r.content.decode()
check("T3b alle Abschnitte gerendert",
      all(k in html for k in ("Grundprinzip", "Licht und Lichtverhältnisse",
                              "Schwarz/Weiß-Abgleich", "Metadaten",
                              "Checkliste")))
check("T3c Sensor-Daten aus der DB sichtbar (SparkFun Triad)",
      "Sparkfun Triad" in html)
check("T3d Setting-Erklaerungen aus der DB (Integrationszeit)",
      "Integrationszeit" in html)
check("T3e SVG-Illustrationen gerendert", html.count("<svg") >= 2)
r2 = client.get('/')
check("T3f Startseite rendert mit Einfuehrungs-Kachel",
      r2.status_code == 200 and "/intro/spectroscopy/" in
      r2.content.decode())
anon = Client(HTTP_HOST='testserver')
r3 = anon.get(url)
check("T3g anonym -> Login-Redirect", r3.status_code in (301, 302))
# i18n-Pfad verfuegbar (englisches Praefix)
r4 = client.get('/en/intro/spectroscopy/')
check("T3h i18n-Pfad /en/intro/spectroscopy/ erreichbar",
      r4.status_code == 200, f"status {r4.status_code}")

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
