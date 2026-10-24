#!/usr/bin/env python3
# OP95 test matrix: software split into open (community/public-sector) and
# pro (proprietary startup) editions.
#
# Covers:
#   T1  edition defaults (open -> F1/F2/F3 off, pro -> on)
#   T2  selective per-feature overrides (both directions)
#   T3  fail-closed behaviour for unknown features
#   T4  startup URL is a placeholder by default
#   T5  service-level guards (F1/F2/F3 factories raise in open edition)
#   T6  sensor document access is empty in open edition
#   T7  navigation template renders teaser links in open edition
#   T8  page guards render the teaser page in open edition
#   T9  API guards answer 403 in open edition (federated + ilias)
#   T10 settings couple FLOWERAI_ENABLED/ILIAS_ENABLED to the feature flags
#   T11 pro edition: guards pass (services constructible, pages reachable)
#   T12 docker-compose: ilias/flower services carry the "pro" profile
#
# Offline-safe: no network access required. Edition is switched via env vars
# and core.edition is reloaded per scenario.
import importlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "django_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nir_web.settings")

PASS = 0
FAIL = 0

FEATURE_ENV_VARS = [
    "NIR_IP_EDITION",
    "NIR_IP_STARTUP_URL",
    "NIR_IP_FEATURE_LEARNING",
    "NIR_IP_FEATURE_SENSORS",
    "NIR_IP_FEATURE_FEDERATED",
]


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {detail}")


def clear_edition_env():
    for var in FEATURE_ENV_VARS:
        os.environ.pop(var, None)


def reload_edition():
    from core import edition
    return importlib.reload(edition)


# ---------------------------------------------------------------- T1: defaults
clear_edition_env()
edition = reload_edition()
check("T1a default edition is 'open'", edition.get_edition() == "open")
check("T1b open: learning off", not edition.feature_enabled(edition.FEATURE_LEARNING))
check("T1c open: sensors off", not edition.feature_enabled(edition.FEATURE_SENSORS))
check("T1d open: federated off", not edition.feature_enabled(edition.FEATURE_FEDERATED))
check("T1e is_pro False in open", not edition.is_pro())

os.environ["NIR_IP_EDITION"] = "pro"
edition = reload_edition()
check("T1f pro: learning on", edition.feature_enabled(edition.FEATURE_LEARNING))
check("T1g pro: sensors on", edition.feature_enabled(edition.FEATURE_SENSORS))
check("T1h pro: federated on", edition.feature_enabled(edition.FEATURE_FEDERATED))
check("T1i is_pro True in pro", edition.is_pro())

os.environ["NIR_IP_EDITION"] = "bogus"
edition = reload_edition()
check("T1j unknown edition falls back to open", edition.get_edition() == "open")

# ------------------------------------------------- T2: selective overrides
clear_edition_env()
os.environ["NIR_IP_FEATURE_SENSORS"] = "true"
edition = reload_edition()
check("T2a open + SENSORS=true -> sensors on",
      edition.feature_enabled(edition.FEATURE_SENSORS))
check("T2b open + SENSORS=true -> learning still off",
      not edition.feature_enabled(edition.FEATURE_LEARNING))
check("T2c open + SENSORS=true -> federated still off",
      not edition.feature_enabled(edition.FEATURE_FEDERATED))

os.environ["NIR_IP_EDITION"] = "pro"
os.environ["NIR_IP_FEATURE_SENSORS"] = "false"
edition = reload_edition()
check("T2d pro + SENSORS=false -> sensors off (override wins)",
      not edition.feature_enabled(edition.FEATURE_SENSORS))
check("T2e pro + SENSORS=false -> federated still on",
      edition.feature_enabled(edition.FEATURE_FEDERATED))

# ------------------------------------------------------- T3: fail-closed
check("T3a unknown feature name -> disabled",
      not edition.feature_enabled("does_not_exist"))

# ------------------------------------------------------------ T4: startup URL
clear_edition_env()
edition = reload_edition()
check("T4a startup URL is a placeholder by default",
      edition.startup_url() == edition.DEFAULT_STARTUP_URL
      and "example.invalid" in edition.startup_url())
os.environ["NIR_IP_STARTUP_URL"] = "https://startup.example.com/info"
edition = reload_edition()
check("T4b startup URL configurable via env",
      edition.startup_url() == "https://startup.example.com/info")

# ------------------------------------------- T5: service-level guards (open)
clear_edition_env()
edition = reload_edition()

import django  # noqa: E402
django.setup()

try:
    from services.federated_learning_service import FederatedLearningService
    try:
        FederatedLearningService()
        check("T5a open: FederatedLearningService raises", False, "no exception")
    except RuntimeError as exc:
        check("T5a open: FederatedLearningService raises",
              "not available in edition" in str(exc))
except Exception as exc:
    check("T5a open: FederatedLearningService raises", False, str(exc))

try:
    from services.federated_calibration import FederatedCalibrationService
    try:
        FederatedCalibrationService()
        check("T5b open: FederatedCalibrationService raises", False, "no exception")
    except RuntimeError as exc:
        check("T5b open: FederatedCalibrationService raises",
              "not available in edition" in str(exc))
except Exception as exc:
    check("T5b open: FederatedCalibrationService raises", False, str(exc))

try:
    from services.ilias_learning_service import create_ilias_learning_service
    try:
        create_ilias_learning_service()
        check("T5c open: create_ilias_learning_service raises", False, "no exception")
    except RuntimeError as exc:
        check("T5c open: create_ilias_learning_service raises",
              "not available in edition" in str(exc))
except Exception as exc:
    check("T5c open: create_ilias_learning_service raises", False, str(exc))

try:
    from services.ilias_api_service import create_ilias_api_client
    try:
        create_ilias_api_client()
        check("T5d open: create_ilias_api_client raises", False, "no exception")
    except RuntimeError as exc:
        check("T5d open: create_ilias_api_client raises",
              "not available in edition" in str(exc))
except Exception as exc:
    check("T5d open: create_ilias_api_client raises", False, str(exc))

try:
    from services.sensor_catalog import get_sensor_profiles
    try:
        get_sensor_profiles()
        check("T5e open: get_sensor_profiles raises", False, "no exception")
    except RuntimeError as exc:
        check("T5e open: get_sensor_profiles raises",
              "not available in edition" in str(exc))
except Exception as exc:
    check("T5e open: get_sensor_profiles raises", False, str(exc))

# ------------------------------------------- T6: sensor documents empty (open)
try:
    from services.sensor_documents import sensor_documents
    docs = sensor_documents("sparkfun_triad")
    check("T6a open: sensor_documents returns empty queryset",
          hasattr(docs, "count") and docs.count() == 0)
except Exception as exc:
    check("T6a open: sensor_documents returns empty queryset", False, str(exc))

# ------------------------------------- T7: navigation teaser (open edition)
try:
    from django.template.loader import render_to_string
    from core.context_processors import edition_features

    class _Req:
        pass

    ctx = edition_features(_Req())
    html = render_to_string("base.html", ctx)
    check("T7a open: nav sensors -> startup link",
          ctx["startup_url"] in html and "/projects/sensors/" not in html)
    check("T7b open: nav lernen -> startup link",
          "/ilias/" not in html)
    check("T7c open: nav federated -> startup link",
          "/federated/" not in html)
except Exception as exc:
    check("T7a open: nav sensors -> startup link", False, str(exc))
    check("T7b open: nav lernen -> startup link", False, str(exc))
    check("T7c open: nav federated -> startup link", False, str(exc))

# --------------------------------------------- T8: page guards (open edition)
try:
    from django.test import RequestFactory
    from core.feature_guard import render_teaser
    from core import edition as ed

    rf = RequestFactory()
    request = rf.get("/ilias/")
    request.user = None
    response = render_teaser(request, ed.FEATURE_LEARNING)
    body = response.content.decode("utf-8")
    check("T8a open: ilias teaser page renders with startup link",
          response.status_code == 200 and ed.startup_url() in body)
    check("T8b open: teaser names the feature",
          "Lernplattform" in body)
except Exception as exc:
    check("T8a open: ilias teaser page renders with startup link", False, str(exc))
    check("T8b open: teaser names the feature", False, str(exc))

# --------------------------------------------- T9: API guards (open edition)
try:
    from rest_framework.test import APIRequestFactory
    from api.federated_views import federated_status, federated_consent
    from api.ilias_views import ilias_status

    arf = APIRequestFactory()
    resp = federated_status(arf.get("/api/federated/status/"))
    check("T9a open: GET /api/federated/status/ -> 403",
          resp.status_code == 403 and resp.data.get("available") is False)
    resp = federated_consent(arf.post("/api/federated/consent/",
                                     {"consent": True}, format="json"))
    check("T9b open: POST /api/federated/consent/ -> 403",
          resp.status_code == 403)
    resp = ilias_status(arf.get("/api/ilias/status/"))
    check("T9c open: GET /api/ilias/status/ -> 403",
          resp.status_code == 403 and resp.data.get("available") is False)
except Exception as exc:
    check("T9a open: GET /api/federated/status/ -> 403", False, str(exc))
    check("T9b open: POST /api/federated/consent/ -> 403", False, str(exc))
    check("T9c open: GET /api/ilias/status/ -> 403", False, str(exc))

# ------------------------------- T10: settings couple flags to feature flags
try:
    from django.conf import settings
    check("T10a open: FLOWERAI_ENABLED is False",
          settings.FLOWERAI_ENABLED is False)
    check("T10b open: FEDERATED_LEARNING_ENABLED is False",
          settings.FEDERATED_LEARNING_ENABLED is False)
    check("T10c open: ILIAS_ENABLED is False",
          settings.ILIAS_ENABLED is False)
except Exception as exc:
    check("T10a open: FLOWERAI_ENABLED is False", False, str(exc))
    check("T10b open: FEDERATED_LEARNING_ENABLED is False", False, str(exc))
    check("T10c open: ILIAS_ENABLED is False", False, str(exc))

# --------------------------------------------- T11: pro edition guards pass
clear_edition_env()
os.environ["NIR_IP_EDITION"] = "pro"
edition = reload_edition()
try:
    from services.federated_learning_service import FederatedLearningService
    svc = FederatedLearningService()
    check("T11a pro: FederatedLearningService constructible",
          svc is not None)
except Exception as exc:
    check("T11a pro: FederatedLearningService constructible", False, str(exc))

try:
    from services.ilias_learning_service import create_ilias_learning_service
    svc = create_ilias_learning_service()
    check("T11b pro: create_ilias_learning_service works",
          svc is not None)
except Exception as exc:
    check("T11b pro: create_ilias_learning_service works", False, str(exc))

try:
    from services.sensor_catalog import get_sensor_profiles
    profiles = get_sensor_profiles()
    check("T11c pro: get_sensor_profiles returns catalog",
          "registered_sensors" in profiles and "usage" in profiles)
except Exception as exc:
    check("T11c pro: get_sensor_profiles returns catalog", False, str(exc))

try:
    from services.sensor_documents import sensor_documents
    docs = sensor_documents("sparkfun_triad")
    check("T11d pro: sensor_documents returns queryset",
          hasattr(docs, "count"))
except Exception as exc:
    check("T11d pro: sensor_documents returns queryset", False, str(exc))

try:
    from rest_framework.test import APIRequestFactory
    from api.federated_views import federated_status
    arf = APIRequestFactory()
    resp = federated_status(arf.get("/api/federated/status/"))
    check("T11e pro: GET /api/federated/status/ -> 200",
          resp.status_code == 200)
except Exception as exc:
    check("T11e pro: GET /api/federated/status/ -> 200", False, str(exc))

# --------------------------------------------- T12: docker-compose profiles
try:
    import yaml
    compose = yaml.safe_load(
        (Path(__file__).resolve().parent.parent / "docker-compose.yml")
        .read_text(encoding="utf-8"))
    services = compose["services"]
    profiled = {"ilias", "ilias_db", "flower_server", "flower_client",
                "ilias_course_agent"}
    missing = [s for s in profiled if "pro" not in services[s].get("profiles", [])]
    check("T12a ilias/flower services carry the 'pro' profile",
          not missing, f"missing: {missing}")
    env = services["django_app"]["environment"]
    env_str = " ".join(str(e) for e in env)
    check("T12b django_app passes NIR_IP_EDITION + feature flags",
          "NIR_IP_EDITION" in env_str and "NIR_IP_FEATURE_SENSORS" in env_str
          and "NIR_IP_STARTUP_URL" in env_str)
except Exception as exc:
    check("T12a ilias/flower services carry the 'pro' profile", False, str(exc))
    check("T12b django_app passes NIR_IP_EDITION + feature flags", False, str(exc))

# restore default environment for other test runs
clear_edition_env()
reload_edition()

print(f"\nOP95 edition split matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
