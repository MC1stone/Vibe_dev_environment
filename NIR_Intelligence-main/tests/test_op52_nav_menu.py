#!/usr/bin/env python3
# OP52 test matrix: navigation menu restructure + calibration overview page
# Offline-safe: no network access required.
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

# T1: navigation order in base.html (Projekte -> Sensoren -> Kalibrieren ->
# Lernen mit Kursen -> Workflow last)
tpl_src = (Path(__file__).resolve().parent.parent
           / "django_project" / "templates" / "base.html").read_text(encoding="utf-8")
try:
    nav = tpl_src[tpl_src.index('c-nav-main__list'):tpl_src.index('</nav>')]
    check("T1a nav block extractable", True)
except ValueError as exc:
    nav = ""
    check("T1a nav block extractable", False, str(exc))

positions = []
for label in ("Projekte", "Sensoren", "Kalibrieren",
              "Lernen mit Kursen", "Workflow"):
    pos = nav.find('trans "%s"' % label)
    positions.append((label, pos))
    check(f"T1b nav contains '{label}'", pos != -1)

order_ok = (all(p != -1 for _, p in positions)
            and [p for _, p in positions] == sorted(p for _, p in positions))
check("T1c nav order: Projekte < Sensoren < Kalibrieren < Lernen < Workflow",
      order_ok, f"positions: {positions}")

check("T1d 'Projekte' links to /projects/",
      'href="/projects/"' in nav)
check("T1e 'Kalibrieren' links to /calibration/",
      'href="/calibration/"' in nav)
check("T1f 'Lernen mit Kursen' links to /ilias/",
      'href="/ilias/"' in nav)
check("T1g 'Workflow' links to / (start page)",
      'href="/"' in nav)

# T2: Sensoren sub-items (Sensoren + DIY-Spektrometer)
sens_pos = nav.find('trans "Sensoren"')
diy_pos = nav.find('trans "DIY-Spektrometer"')
check("T2a Sensoren has sub-menu", 'c-nav-sub' in nav)
check("T2b DIY-Spektrometer sub-item after Sensoren",
      -1 < sens_pos < diy_pos, f"sens={sens_pos} diy={diy_pos}")
check("T2c DIY sub-item links to /api/projects/sensors/diy/",
      'href="/api/projects/sensors/diy/"' in nav)

# T3: Spektren-Datenbank as sub-item under Projekte
db_pos = nav.find('trans "Spektren-Datenbank"')
check("T3a Spektren-Datenbank is sub-item under Projekte",
      -1 < nav.find('trans "Projekte"') < db_pos,
      f"db_pos={db_pos}")
check("T3b Spektren-Datenbank links to /projects/database/",
      'href="/projects/database/"' in nav)

# T4: calibration page route + view
from django.urls import reverse, resolve
try:
    url = reverse("calibration-page")
    check("T4a /calibration/ route registered", url == "/calibration/", url)
except Exception as exc:
    check("T4a /calibration/ route registered", False, str(exc))

try:
    match = resolve("/calibration/")
    check("T4b /calibration/ resolves to CalibrationOverviewView",
          match.view_name == "calibration-page", match.view_name)
except Exception as exc:
    check("T4b /calibration/ resolves", False, str(exc))

try:
    from api.project_views import CalibrationOverviewView
    check("T4c CalibrationOverviewView importable", True)
except Exception as exc:
    check("T4c CalibrationOverviewView importable", False, str(exc))

# T5: anonymous request redirects to login
from django.test import Client
from django.conf import settings as dj_settings
if "testserver" not in dj_settings.ALLOWED_HOSTS:
    dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]
client = Client()
try:
    resp = client.get("/calibration/")
    check("T5a anonymous /calibration/ redirects to login",
          resp.status_code in (301, 302)
          and "login" in (resp.get("Location") or ""))
except Exception as exc:
    check("T5a anonymous /calibration/ redirects", False, str(exc))

# T6: calibration template parses and extends base
try:
    from django.template.loader import get_template
    get_template("calibration_overview.html")
    check("T6a calibration_overview.html template parses", True)
except Exception as exc:
    check("T6a calibration_overview.html template parses", False, str(exc))

cal_src = (Path(__file__).resolve().parent.parent
           / "django_project" / "templates"
           / "calibration_overview.html").read_text(encoding="utf-8")
check("T6b calibration_overview.html extends base.html",
      'extends "base.html"' in cal_src)
check("T6c template shows empty-state hint",
      "Noch keine Kalibrationen" in cal_src)
check("T6d template links to projects",
      'href="/projects/"' in cal_src)

# T7: catalogs contain the OP52 msgids (via .po source, msgfmt runs in CI)
locale_base = Path(__file__).resolve().parent.parent / "django_project/locale"


def po_has(lang, msgid):
    po = (locale_base / lang / "LC_MESSAGES" / "django.po").read_text(encoding="utf-8")
    return f'msgid "{msgid}"' in po


de_msgids = ["Kalibrieren", "Kalibrierung - \u00dcbersicht", "Lernen mit Kursen",
             "ILIAS-Kurse", "Spektren-Datenbank", "Bestes Modell", "CV-Folds",
             "R\u00b2 (Cross-Validation)", "Zielwert"]
for msgid in de_msgids:
    check(f"T7a de catalog contains '{msgid}'", po_has("de", msgid))

en_expected = {
    "Kalibrieren": "Calibration",
    "Lernen mit Kursen": "Learning with courses",
    "ILIAS-Kurse": "ILIAS courses",
    "Spektren-Datenbank": "Spectrum database",
    "Bestes Modell": "Best model",
}
for msgid, expected in en_expected.items():
    po = (locale_base / "en" / "LC_MESSAGES" / "django.po").read_text(encoding="utf-8")
    ok = f'msgid "{msgid}"' in po and f'msgstr "{expected}"' in po
    check(f"T7b en catalog translates '{msgid}' -> '{expected}'", ok)

# T8: secondary route under /api/projects/ also resolves
try:
    url = reverse("calibration-overview")
    check("T8a /api/projects/calibration/overview/ route registered",
          url == "/api/projects/calibration/overview/", url)
except Exception as exc:
    check("T8a calibration-overview route registered", False, str(exc))

print(f"\nOP52 nav menu + calibration matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
