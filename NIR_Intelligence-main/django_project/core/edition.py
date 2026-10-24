"""OP95: Edition & feature flags for the software split.

Two editions of the same code base:

- ``open`` (default) - the open-source community / public-sector edition.
  It contains the full core functionality. The three extended functions
  (learning platform F1, sensor database F2, federated learning F3) are
  replaced by a teaser linking to the startup page, unless explicitly
  enabled per feature flag.
- ``pro`` - the proprietary startup edition. It contains everything the
  open edition contains plus F1-F3 fully enabled.

Selection is environment-driven so the same image serves both editions:

- ``NIR_IP_EDITION`` = ``open`` (default) | ``pro``
- ``NIR_IP_STARTUP_URL`` - URL of the startup page the teasers link to
  (placeholder by default; configurable per deployment).
- Per-feature overrides (selective activation, e.g. a customer who only
  licenses the sensor database):
  ``NIR_IP_FEATURE_LEARNING``, ``NIR_IP_FEATURE_SENSORS``,
  ``NIR_IP_FEATURE_FEDERATED`` = ``true`` | ``false``

Defaults: edition ``open`` -> all three features OFF (teaser links only);
edition ``pro`` -> all three features ON. A single feature flag always
wins over the edition default.
"""

import os

EDITION_OPEN = 'open'
EDITION_PRO = 'pro'

FEATURE_LEARNING = 'learning_platform'
FEATURE_SENSORS = 'sensor_database'
FEATURE_FEDERATED = 'federated_learning'

ALL_FEATURES = (FEATURE_LEARNING, FEATURE_SENSORS, FEATURE_FEDERATED)

# Placeholder only - the real startup URL is configured per deployment
# via NIR_IP_STARTUP_URL. Never a hard-coded production URL.
DEFAULT_STARTUP_URL = 'https://example.invalid/startup'

_ENV_FLAG_MAP = {
    FEATURE_LEARNING: 'NIR_IP_FEATURE_LEARNING',
    FEATURE_SENSORS: 'NIR_IP_FEATURE_SENSORS',
    FEATURE_FEDERATED: 'NIR_IP_FEATURE_FEDERATED',
}


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def get_edition():
    """Return the active edition: ``open`` (default) or ``pro``."""
    edition = os.getenv('NIR_IP_EDITION', EDITION_OPEN).strip().lower()
    return edition if edition in (EDITION_OPEN, EDITION_PRO) else EDITION_OPEN


def is_pro():
    """True when the proprietary startup edition is active."""
    return get_edition() == EDITION_PRO


def feature_enabled(feature):
    """Return True when the given feature is enabled in this deployment.

    A per-feature environment flag wins over the edition default.
    Unknown feature names are reported as disabled (fail-closed).
    """
    if feature not in ALL_FEATURES:
        return False
    env_name = _ENV_FLAG_MAP[feature]
    if env_name in os.environ:
        return _env_bool(env_name)
    return is_pro()


def startup_url():
    """Return the startup page URL used by the open-edition teasers."""
    return os.getenv('NIR_IP_STARTUP_URL', DEFAULT_STARTUP_URL)


def feature_status():
    """Return a dict with edition, startup URL and per-feature state."""
    return {
        'edition': get_edition(),
        'startup_url': startup_url(),
        'features': {name: feature_enabled(name) for name in ALL_FEATURES},
    }
