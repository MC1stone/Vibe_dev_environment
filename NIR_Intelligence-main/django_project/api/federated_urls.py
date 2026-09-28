# NIR Intelligence Platform - Federated learning API URLs (FL4)
from django.urls import include, path

from .federated_views import (
    federated_consent,
    federated_privacy,
    federated_round,
    federated_status,
)

urlpatterns = [
    path("consent/", federated_consent, name="federated_consent"),
    path("status/", federated_status, name="federated_status"),
    path("rounds/", federated_round, name="federated_round"),
    path("privacy/", federated_privacy, name="federated_privacy"),
]

federated_api_urls = [path("api/federated/", include(urlpatterns))]
federated_urls = urlpatterns
