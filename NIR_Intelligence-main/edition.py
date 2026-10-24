"""OP95: edition & feature flags for the software split (top-level mirror).

The canonical implementation lives in ``django_project/core/edition.py``
inside the Django project. The agents and services under ``agents/`` and
``services/`` are also executed standalone (scripts, Flower containers,
test matrices) where ``django_project`` is not on ``sys.path`` - this
top-level module re-exports the same API so the guards work in every
runtime context.

Two editions of the same code base:

- ``open`` (default) - open-source community / public-sector edition with
  the full core functionality; the three extended functions (learning
  platform F1, sensor database F2, federated learning F3) are gated.
- ``pro`` - proprietary startup edition with F1-F3 fully enabled.

Environment:
- ``NIR_IP_EDITION`` = ``open`` (default) | ``pro``
- ``NIR_IP_STARTUP_URL`` - startup page URL for the open-edition teasers
  (placeholder by default).
- ``NIR_IP_FEATURE_LEARNING`` / ``NIR_IP_FEATURE_SENSORS`` /
  ``NIR_IP_FEATURE_FEDERATED`` - selective per-feature overrides.
"""

import os
import sys
from pathlib import Path

_DJANGO_PROJECT = Path(__file__).resolve().parent / 'django_project'
if str(_DJANGO_PROJECT) not in sys.path:
    sys.path.insert(0, str(_DJANGO_PROJECT))

from core.edition import (  # noqa: E402,F401
    ALL_FEATURES,
    DEFAULT_STARTUP_URL,
    EDITION_OPEN,
    EDITION_PRO,
    FEATURE_FEDERATED,
    FEATURE_LEARNING,
    FEATURE_SENSORS,
    feature_enabled,
    feature_status,
    get_edition,
    is_pro,
    startup_url,
)
