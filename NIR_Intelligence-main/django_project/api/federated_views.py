# NIR Intelligence Platform - Federated learning API views (FL4)
# Django REST endpoints for federated sessions: consent-gated start
# (explicit opt-in per WORKFLOW_INTEGRATION.md - default is local_only),
# round history from the S9 core contract, privacy status (FL3 accountant
# + SecAgg availability) and the FL2 federated calibration.

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger("API.FederatedLearning")

from services.federated_calibration import (
    FederatedCalibrationService,
    SKLEARN_AVAILABLE,
)
from services.federated_learning_service import (
    FederatedLearningService,
    FLWR_AVAILABLE,
)
from services.federated_privacy import secure_aggregation_available
from django.utils.translation import gettext_lazy as gettext

_consent_given = False


def _session_status() -> dict:
    return {
        "federated_learning": True,
        "consent_given": _consent_given,
        "privacy_level": "federated" if _consent_given else "local_only",
        "flwr_available": FLWR_AVAILABLE,
        "sklearn_available": SKLEARN_AVAILABLE,
        "secure_aggregation": secure_aggregation_available(),
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def federated_consent(request):
    """POST /api/federated/consent/

    Explicit opt-in for federated learning (WORKFLOW_INTEGRATION.md:
    users must explicitly enable federated sharing). Body:
    {"consent": true/false}.
    """
    global _consent_given
    payload = request.data
    if not isinstance(payload, dict) or not isinstance(payload.get("consent"), bool):
        return Response({"error": gettext("consent (bool) is required")},
                        status=status.HTTP_400_BAD_REQUEST)
    _consent_given = bool(payload["consent"])
    logger.info("federated learning consent set to %s", _consent_given)
    return Response(_session_status(), status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def federated_status(request):
    """GET /api/federated/status/ - session, runtime and privacy status."""
    return Response(_session_status(), status=status.HTTP_200_OK)


def run_federated_round(payload):
    """Core round logic, decoupled from DRF for testability.

    Returns (body_dict, http_status). Consent gate first (403), honest
    deferral without scikit-learn (503), payload validation (400).
    """
    if not _consent_given:
        return {"error": gettext("federated learning requires explicit consent (POST /api/federated/consent/)")}, status.HTTP_403_FORBIDDEN
    if not SKLEARN_AVAILABLE:
        return {"error": gettext("scikit-learn is not available - federated calibration deferred")}, status.HTTP_503_SERVICE_UNAVAILABLE
    shards_payload = payload.get("shards") if isinstance(payload, dict) else None
    if not shards_payload or not isinstance(shards_payload, list):
        return {"error": gettext("shards (list) is required")}, status.HTTP_400_BAD_REQUEST
    import numpy as np

    from services.federated_calibration import CalibrationShard

    shards = []
    for shard_data in shards_payload:
        x = shard_data.get("x")
        y = shard_data.get("y")
        if x is None or y is None:
            return {"error": gettext("each shard needs x and y")}, status.HTTP_400_BAD_REQUEST
        shards.append(CalibrationShard(
            x=np.asarray(x, dtype=np.float64),
            y=np.asarray(y, dtype=np.float64),
            instrument_type=str(shard_data.get("instrument_type", "unknown")),
            sample_type=str(shard_data.get("sample_type", "unknown")),
        ))
    service = FederatedCalibrationService(
        n_components=int(payload.get("n_components", 2)))
    try:
        result = service.run_round(shards)
    except (ValueError, RuntimeError) as exc:
        return {"error": str(exc)}, status.HTTP_400_BAD_REQUEST
    return result.to_dict(), status.HTTP_201_CREATED


@api_view(["POST"])
@permission_classes([AllowAny])
def federated_round(request):
    """POST /api/federated/rounds/

    Runs one federated calibration round (S9 core semantics via the FL2
    calibration service). Requires explicit consent (403 otherwise).
    """
    body, code = run_federated_round(request.data)
    return Response(body, status=code)


@api_view(["GET"])
@permission_classes([AllowAny])
def federated_privacy(request):
    """GET /api/federated/privacy/ - privacy mechanisms status (FL3)."""
    from services.federated_privacy import DPConfig, PrivacyAccountant

    accountant = PrivacyAccountant(DPConfig())
    return Response({
        "differential_privacy": accountant.status(),
        "secure_aggregation": secure_aggregation_available(),
        "privacy_contract": "only parameter updates shared - raw data stays local",
    }, status=status.HTTP_200_OK)
