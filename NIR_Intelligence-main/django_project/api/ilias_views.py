# NIR Intelligence Platform - ILIAS learning path API views (roadmap S8)
# Django REST endpoints for NIR learning path synchronization to the
# ILIAS container (services/ilias_learning_service.py).

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger("API.ILIASLearning")


def _get_service():
    from django.conf import settings

    from services.ilias_learning_service import create_ilias_learning_service

    return create_ilias_learning_service(config={
        "ilias_url": getattr(settings, "ILIAS_URL", "http://ilias:80"),
        "client_id": getattr(settings, "ILIAS_CLIENT_ID", "nir_ip"),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def learning_path_sync(request):
    """POST /api/ilias/learning-paths/sync/

    Body: a learning path dict (title, description, target_group, modules
    with objectives and content_ref).
    """
    payload = request.data
    if not isinstance(payload, dict) or not payload.get("title"):
        return Response({"error": "title is required"},
                        status=status.HTTP_400_BAD_REQUEST)

    from services.ilias_learning_service import (
        LearningModule,
        LearningObjective,
        LearningPath,
    )

    modules = []
    for module_data in payload.get("modules", []):
        objectives = [LearningObjective(
            title=o.get("title", ""),
            description=o.get("description", ""),
            target_level=o.get("target_level", "apply"),
        ) for o in module_data.get("objectives", [])]
        modules.append(LearningModule(
            title=module_data.get("title", ""),
            objectives=objectives,
            content_ref=module_data.get("content_ref"),
        ))

    path = LearningPath(
        title=payload["title"],
        description=payload.get("description", ""),
        target_group=payload.get("target_group", "students"),
        modules=modules,
    )

    if not modules:
        return Response({"error": "learning path has no modules"},
                        status=status.HTTP_400_BAD_REQUEST)

    service = _get_service()
    outcome = service.sync_learning_path(path)
    response_code = status.HTTP_201_CREATED if outcome.success else status.HTTP_502_BAD_GATEWAY
    return Response(outcome.to_dict(), status=response_code)


@api_view(["GET"])
@permission_classes([AllowAny])
def ilias_status(request):
    """GET /api/ilias/status/ - ILIAS container availability"""
    service = _get_service()
    return Response(service.status())
