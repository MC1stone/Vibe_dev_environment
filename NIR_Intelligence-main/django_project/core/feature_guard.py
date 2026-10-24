"""OP95: shared guard helpers for edition-gated features.

Used by views and services so the three enforcement layers (navigation,
views/URLs, services/agents) behave identically: when a feature is
disabled in this deployment, the caller gets an honest "not available in
this edition" response - never a silent fallback and never a simulated
result.
"""

from functools import wraps

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from core import edition

# Map feature -> (teaser route name, translated feature name key, description key)
FEATURE_TEASER = {
    edition.FEATURE_LEARNING: {
        'feature_name': 'Lernplattform',
        'feature_desc': ('ILIAS-Kurse, Einf\u00fchrungsseite "Richtig messen" und '
                         'die Lernpfad-Synchronisation.'),
    },
    edition.FEATURE_SENSORS: {
        'feature_name': 'Sensor-Datenbank',
        'feature_desc': ('Sensor-Katalog mit Adapter-Profilen, Nutzungsstatistiken, '
                         'Dokumentenverwaltung und KI-Zusammenfassung pro Ger\u00e4t.'),
    },
    edition.FEATURE_FEDERATED: {
        'feature_name': 'Federated Learning',
        'feature_desc': ('F\u00f6derierte Kalibrationsmodelle \u00fcber Flower: Consent-Gate, '
                         'parameter-only Transport, Differential Privacy, FedAvg.'),
    },
}


def render_teaser(request, feature):
    """Render the honest teaser page for a disabled feature."""
    info = FEATURE_TEASER.get(feature, {
        'feature_name': feature,
        'feature_desc': '',
    })
    return render(request, 'feature_teaser.html', {
        'feature_name': info['feature_name'],
        'feature_desc': info['feature_desc'],
        'startup_url': edition.startup_url(),
        'edition': edition.get_edition(),
    })


def teaser_redirect(feature):
    """Return a redirect to the feature's teaser route (for URL-level guards)."""
    return HttpResponseRedirect(reverse('feature-teaser', kwargs={'feature': feature}))


def require_feature(feature):
    """Class-based-view decorator: disabled feature -> teaser page (HTTP 200).

    Enabled feature -> the view runs unchanged.
    """
    def decorator(view_class):
        original_get = view_class.get

        def guarded_get(self, request, *args, **kwargs):
            if not edition.feature_enabled(feature):
                return render_teaser(request, feature)
            return original_get(self, request, *args, **kwargs)

        view_class.get = guarded_get
        return view_class
    return decorator


def guarded(feature):
    """Function-based-view decorator: disabled feature -> teaser page."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not edition.feature_enabled(feature):
                return render_teaser(request, feature)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class FeatureUnavailable(Exception):
    """Raised by services/agents when a feature is disabled in this edition."""

    def __init__(self, feature):
        self.feature = feature
        super().__init__(
            f"Feature '{feature}' is not available in edition "
            f"'{edition.get_edition()}'")


def check_feature(feature):
    """Service/agent-level guard (fail-closed, honest message)."""
    if not edition.feature_enabled(feature):
        raise FeatureUnavailable(feature)
    return True
