"""OP95: expose edition feature flags to all templates.

Makes ``feature_learning``, ``feature_sensors``, ``feature_federated``,
``edition`` and ``startup_url`` available in every template so the
navigation (base.html) can render either the real menu entry or the
startup teaser link per feature.
"""

from core import edition


def edition_features(request):
    return {
        'edition': edition.get_edition(),
        'is_pro': edition.is_pro(),
        'startup_url': edition.startup_url(),
        'feature_learning': edition.feature_enabled(edition.FEATURE_LEARNING),
        'feature_sensors': edition.feature_enabled(edition.FEATURE_SENSORS),
        'feature_federated': edition.feature_enabled(edition.FEATURE_FEDERATED),
    }
