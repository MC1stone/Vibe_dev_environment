#!/usr/bin/env python3
# OP49 test matrix: DIY spectrometer overview page + opt-in sensor websearch
# Offline-safe: no network access required (websearch is opt-in and mocked).
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


# T1: sensor_websearch service contract
try:
    import django
    django.setup()
    from services import sensor_websearch
    check("T1a sensor_websearch service importable", True)
except Exception as exc:
    check("T1a sensor_websearch service importable", False, str(exc))
    sys.exit(1)

# T1b: websearch disabled by default (opt-in)
os.environ.pop("NIR_SENSOR_WEBSEARCH", None)
check("T1b websearch disabled by default (opt-in)",
      not sensor_websearch.websearch_enabled())

# T1c: opt-in via env var
os.environ["NIR_SENSOR_WEBSEARCH"] = "1"
check("T1c websearch enabled via NIR_SENSOR_WEBSEARCH=1",
      sensor_websearch.websearch_enabled())
os.environ.pop("NIR_SENSOR_WEBSEARCH", None)

# T1d: search_sensor never raises without ollama, reports honestly
result = sensor_websearch.search_sensor("TriadSensor")
check("T1d search_sensor honest without ollama (enabled=False, no crash)",
      result.get("enabled") is False and "summary" in result)

# T2: SensorAgent exposes websearch section (offline default)
from agents.sensor_agent import SensorAgent
out = SensorAgent().execute({"operation": "collect"})
data = out.data or {}
check("T2a SensorAgent collect exposes websearch section",
      "websearch" in data)
ws = data.get("websearch") or {}
check("T2b websearch disabled offline by default",
      ws.get("enabled") is False)
check("T2c websearch results marked external/unverified",
      ws.get("external_unverified") is True)

# T3: DIY view + URL wiring
from django.urls import reverse, resolve
try:
    url = reverse("sensor-diy")
    check("T3a /api/projects/sensors/diy/ route registered", url == "/api/projects/sensors/diy/", url)
except Exception as exc:
    check("T3a /sensors/diy/ route registered", False, str(exc))
    url = None
if url:
    match = resolve("/api/projects/sensors/diy/")
    check("T3b route resolves to DiySpectrometerView",
          match.view_name == "sensor-diy")

# T3c: DIY route takes precedence over sensor-detail parameter route
try:
    from api.project_views import DiySpectrometerView
    match = resolve("/api/projects/sensors/diy/")
    check("T3c /sensors/diy/ is not swallowed by sensor-detail",
          match.func is not None and "diy" not in match.kwargs)
except Exception as exc:
    check("T3c /sensors/diy/ is not swallowed by sensor-detail", False, str(exc))

# T4: curated project list content
from api.project_views import DiySpectrometerView
projects = DiySpectrometerView.DIY_PROJECTS
check("T4a five curated DIY projects", len(projects) == 5,
      f"got {len(projects)}")
names = [p["name"] for p in projects]
expected = ["OpenSpectrometer", "DIY Spectroscope (Thingiverse)",
            "Public Lab Desktop Spectrometer", "Smartphone-CD-Spektrometer",
            "SpecPhone / DualSpec"]
check("T4b project names match curated list", names == expected,
      f"got {names}")
all_urls = [u for p in projects for _, u in p["urls"]]
check("T4c all project links are https", all(u.startswith("https://") for u in all_urls))
check("T4d all project links unique", len(all_urls) == len(set(all_urls)))
tutorials = DiySpectrometerView.TUTORIAL_LINKS
check("T4e seven tutorial links provided", len(tutorials) == 7,
      f"got {len(tutorials)}")
check("T4f tutorial links are https", all(u.startswith("https://") for _, u in tutorials))

# T5: template renders (login redirect expected for anonymous)
from django.test import Client
from django.conf import settings as dj_settings
if "testserver" not in dj_settings.ALLOWED_HOSTS:
    dj_settings.ALLOWED_HOSTS = [*dj_settings.ALLOWED_HOSTS, "testserver"]
client = Client()
try:
    resp = client.get("/api/projects/sensors/diy/")
    check("T5a anonymous request redirects to login",
          resp.status_code in (301, 302)
          and "login" in (resp.get("Location") or ""))
except Exception as exc:
    check("T5a anonymous request redirects to login", False, str(exc))

# T5b: template parses (direct render check with empty context)
try:
    from django.template.loader import get_template
    get_template("sensor_diy.html")
    check("T5b sensor_diy.html template parses", True)
except Exception as exc:
    check("T5b sensor_diy.html template parses", False, str(exc))

# T6: sensor_list links to DIY page
try:
    tpl_src = (Path(__file__).resolve().parent.parent
              / "django_project" / "templates" / "sensor_list.html"
              ).read_text(encoding="utf-8")
    check("T6a sensor_list.html links to /projects/sensors/diy/",
          '/api/projects/sensors/diy/' in tpl_src)
except Exception as exc:
    check("T6a sensor_list.html links to /sensors/diy/", False, str(exc))

# T7: catalogs contain the new msgids
import gettext as gettext_mod
locale_base = Path(__file__).resolve().parent.parent / "django_project/locale"
t_de = gettext_mod.translation("django", localedir=str(locale_base), languages=["de"])
t_en = gettext_mod.translation("django", localedir=str(locale_base), languages=["en"])
check("T7a de catalog translates 'Sensor-Suche (Ollama, Opt-in)'",
      t_de.gettext("Sensor-Suche (Ollama, Opt-in)") == "Sensor-Suche (Ollama, Opt-in)")
check("T7b en catalog translates 'Sensor-Suche (Ollama, Opt-in)'",
      t_en.gettext("Sensor-Suche (Ollama, Opt-in)") == "Sensor search (Ollama, opt-in)")
check("T7c de catalog translates 'Zur Sensor-Übersicht'",
      t_de.gettext("Zur Sensor-Übersicht") == "Zur Sensor-Übersicht")
check("T7d en catalog translates 'Zur Sensor-Übersicht'",
      t_en.gettext("Zur Sensor-Übersicht") == "To the sensor overview")

print(f"\nOP49 sensor websearch + DIY matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
