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

# Workflow-UI-Redesign (S1, PO-freigegeben): 7-Punkte-Navigation entlang
# des NIR-Fachprozesses (Start/Projekte/Kalibration/Schnell-Check/Sensoren/Lernen).
positions = []
for label in ("Start", "Projekte", "Kalibration", "Schnell-Check",
              "Sensoren", "Lernen"):
    pos = nav.find(label)
    positions.append((label, pos))
    check(f"T1b nav contains '{label}'", pos != -1)

order_ok = (all(p != -1 for _, p in positions)
            and [p for _, p in positions] == sorted(p for _, p in positions))
check("T1c nav order: Start < Projekte < Kalibration < Schnell-Check < Sensoren < Lernen",
      order_ok, f"positions: {positions}")

# OP52b: 'Workflow' nav tab removed (release feedback); the start page
# stays reachable via the logo link.
check("T1c2 'Workflow' nav tab removed",
      'trans "Workflow"' not in nav)
logo_pos = tpl_src.find('c-header__logo')
check("T1c3 logo links to start page /",
      -1 < logo_pos < tpl_src.find('href="/"', logo_pos),
      "logo block does not link to /")

check("T1d 'Projekte' links to /projects/",
      'href="/projects/"' in nav)
check("T1e 'Kalibrieren' links to /calibration/",
      'href="/calibration/"' in nav)
check("T1f 'Lernen mit Kursen' links to /ilias/",
      'href="/ilias/"' in nav)

# T2: Sensoren sub-items (Sensoren + DIY-Spektrometer)
sens_pos = nav.find('trans "Sensoren"')
diy_pos = nav.find('trans "DIY-Spektrometer"')
check("T2a Sensoren has sub-menu", 'c-nav-sub' in nav)
check("T2b DIY-Spektrometer sub-item after Sensoren",
      -1 < sens_pos < diy_pos, f"sens={sens_pos} diy={diy_pos}")
check("T2c DIY sub-item links to /api/projects/sensors/diy/",
      'href="/api/projects/sensors/diy/"' in nav)

# Workflow-UI-Redesign (S1, PO-freigegeben): Die Datenbank ist Unterpunkt
# von "Kalibration & Datenbank" (Fachprozess-Phase 4-5), nicht mehr doppelt.
db_pos = nav.find('Referenzspektren')
check("T3a Referenzspektren sub-item under Kalibration",
      -1 < nav.find('Kalibration') < db_pos,
      f"db_pos={db_pos}")
check("T3b Spektren-Datenbank links to /projects/database/",
      'href="/projects/database/"' in nav)
db_count = nav.count('Referenzspektren')
check("T3d exactly one Datenbank nav link (under Kalibration)",
      db_count == 1, f"count={db_count}")

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

# T9: ILIAS wiring (OP52b: 'Open ILIAS' must work via Lernen mit Kursen)
settings_src = (Path(__file__).resolve().parent.parent
                / "django_project" / "nir_web" / "settings.py").read_text(encoding="utf-8")
check("T9a settings define ILIAS_URL (default http://ilias:80)",
      "ILIAS_URL = os.getenv('ILIAS_URL', 'http://ilias:80')" in settings_src)
check("T9b ILIAS_API_URL default points to the container (not hswt.de)",
      "https://ilias.hswt.de" not in settings_src)

compose_src = (Path(__file__).resolve().parent.parent
                / "docker-compose.yml").read_text(encoding="utf-8")
django_block = compose_src[compose_src.index('  django_app:'):]
django_block = django_block[:django_block.index('background_crew')]
check("T9c django_app env passes ILIAS_URL=http://ilias:80",
      'ILIAS_URL=http://ilias:80' in django_block)
check("T9d django_app env passes ILIAS_API_URL=http://ilias:80",
      'ILIAS_API_URL=http://ilias:80' in django_block)

ilias_block = compose_src[compose_src.index('  ilias:'):]
ilias_block = ilias_block[:ilias_block.index('\n  ilias_db:')]
check("T9e ilias service has a healthcheck",
      'healthcheck:' in ilias_block)
check("T9f django_app waits for ilias service_healthy",
      django_block.count('ilias:') >= 1
      and 'condition: service_healthy' in django_block,
      "django_app does not depend on ilias healthy")

# T10: ILIAS external URL (browser-reachable link, OP52b field test)
check("T10a settings define ILIAS_EXTERNAL_URL (default localhost:8080)",
      "ILIAS_EXTERNAL_URL = os.getenv('ILIAS_EXTERNAL_URL', 'http://localhost:8080')"
      in settings_src)
check("T10b django_app env passes ILIAS_EXTERNAL_URL",
      'ILIAS_EXTERNAL_URL' in django_block)

ilias_tpl = (Path(__file__).resolve().parent.parent
             / "django_project" / "templates" / "ilias.html").read_text(encoding="utf-8")
check("T10c ilias.html status box shows clickable external_url link",
      "data.external_url" in ilias_tpl and 'target="_blank"' in ilias_tpl)
check("T10d 'Open ILIAS' button is wired to external_url",
      'id="openIliasBtn"' in ilias_tpl)
check("T10e no hardcoded ilias:80 link left in the template",
      'href="http://ilias:' not in ilias_tpl)

views_src = (Path(__file__).resolve().parent.parent
             / "django_project" / "api" / "ilias_views.py").read_text(encoding="utf-8")
check("T10f ilias_status view passes external_url to the service",
      "ILIAS_EXTERNAL_URL" in views_src)
service_src = (Path(__file__).resolve().parent.parent
                / "services" / "ilias_learning_service.py").read_text(encoding="utf-8")
check("T10g service status() reports external_url",
      '"external_url": self.external_url' in service_src)

print(f"\nOP52 nav menu + calibration matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
