# NIR Intelligence Platform - ILIAS learning path service (roadmap S8)
# Models NIR laboratory learning paths as ILIAS course structures and
# synchronizes them to the ILIAS instance running in its own container
# (docker-compose service 'ilias', srsolutions/ilias image).
# The HTTP transport is stubbed in tests; the service never performs
# network calls at import time and reports sync failures gracefully.

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.ILIASLearning")

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

ILIAS_DEFAULT_URL = "http://ilias:80"


@dataclass
class LearningObjective:
    """One learning objective of the NIR laboratory learning path"""

    title: str
    description: str = ""
    target_level: str = "apply"  # remember, understand, apply, analyze, evaluate, create

    def to_dict(self) -> Dict[str, Any]:
        return {"title": self.title, "description": self.description,
                "target_level": self.target_level}


@dataclass
class LearningModule:
    """One learning module (ILIAS learning objective/lesson)"""

    title: str
    objectives: List[LearningObjective] = field(default_factory=list)
    content_ref: Optional[str] = None  # reference to Quarto report/course material

    def to_dict(self) -> Dict[str, Any]:
        return {"title": self.title,
                "objectives": [o.to_dict() for o in self.objectives],
                "content_ref": self.content_ref}


@dataclass
class LearningPath:
    """A NIR laboratory learning path, mapped to one ILIAS course"""

    title: str
    description: str = ""
    target_group: str = "students"
    modules: List[LearningModule] = field(default_factory=list)
    ilias_ref_id: Optional[str] = None  # set after successful sync

    def to_dict(self) -> Dict[str, Any]:
        return {"title": self.title, "description": self.description,
                "target_group": self.target_group,
                "modules": [m.to_dict() for m in self.modules],
                "ilias_ref_id": self.ilias_ref_id}

    def total_objectives(self) -> int:
        return sum(len(m.objectives) for m in self.modules)


class ILIASCourseBuilder:
    """Builds ILIAS course payloads (REST API v1 style) from learning paths"""

    @staticmethod
    def build_course_payload(path: LearningPath) -> Dict[str, Any]:
        return {
            "type": "crs",  # ILIAS course object type
            "title": path.title,
            "description": path.description,
            "additional": {
                "target_group": path.target_group,
                "objective_count": path.total_objectives(),
                "module_count": len(path.modules),
            },
        }

    @staticmethod
    def build_module_payloads(path: LearningPath) -> List[Dict[str, Any]]:
        payloads: List[Dict[str, Any]] = []
        for module in path.modules:
            payload = {
                "type": "lobj",  # ILIAS learning objective
                "title": module.title,
                "description": "; ".join(o.title for o in module.objectives),
                "objectives": [o.to_dict() for o in module.objectives],
            }
            if module.content_ref:
                payload["content_ref"] = module.content_ref
            payloads.append(payload)
        return payloads


@dataclass
class SyncOutcome:
    """Result of a learning path synchronization to ILIAS"""

    success: bool
    course_title: str
    course_ref_id: Optional[str] = None
    modules_synced: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"success": self.success, "course_title": self.course_title,
                "course_ref_id": self.course_ref_id,
                "modules_synced": self.modules_synced, "errors": self.errors}


class ILIASLearningService:
    """Synchronizes NIR learning paths to the ILIAS container (S8)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.ilias_url = self.config.get("ilias_url", ILIAS_DEFAULT_URL)
        self.client_id = self.config.get("client_id", "nir_ip")
        self.api_token: Optional[str] = None
        self.session = requests.Session() if REQUESTS_AVAILABLE else None

    def is_available(self) -> bool:
        """Cheap availability probe against the ILIAS container."""
        if not REQUESTS_AVAILABLE or self.session is None:
            return False
        try:
            response = self.session.get(self.ilias_url, timeout=5)
            return response.status_code < 500
        except Exception:
            return False

    def sync_learning_path(self, path: LearningPath,
                           transport: Optional[Any] = None,
                           course_ref_id: Optional[Any] = None) -> SyncOutcome:
        """Create course + learning objectives in ILIAS.

        transport: optional callable(method, url, **kwargs) -> response-like
        object with .status_code/.json(); injected by tests. Defaults to the
        requests session against the configured ILIAS URL.
        course_ref_id: optional real ILIAS course ref_id (OP2). When given,
        no new course is created; the modules are synced into the existing
        course identified by this ref_id (e.g. resolved beforehand via
        IliasApiClient.find_course_ref_id_by_title).
        """
        outcome = SyncOutcome(success=False, course_title=path.title)
        if not path.modules:
            outcome.errors.append("learning path has no modules")
            return outcome

        caller = transport or self._default_transport

        try:
            if course_ref_id is None:
                course_payload = ILIASCourseBuilder.build_course_payload(path)
                response = caller("POST", f"{self.ilias_url}/api/v1/courses", json=course_payload)
                if getattr(response, "status_code", 500) not in (200, 201):
                    outcome.errors.append(
                        f"course creation failed (status {getattr(response, 'status_code', '?')})")
                    return outcome
                course_ref_id = response.json().get("ref_id")
            else:
                course_ref_id = course_ref_id
            path.ilias_ref_id = str(course_ref_id) if course_ref_id is not None else None
            outcome.course_ref_id = path.ilias_ref_id

            for module_payload in ILIASCourseBuilder.build_module_payloads(path):
                response = caller("POST", f"{self.ilias_url}/api/v1/courses/{course_ref_id}/objectives",
                                  json=module_payload)
                if getattr(response, "status_code", 500) in (200, 201):
                    outcome.modules_synced += 1
                else:
                    outcome.errors.append(
                        f"module '{module_payload['title']}' failed "
                        f"(status {getattr(response, 'status_code', '?')})")
        except Exception as exc:
            outcome.errors.append(f"ILIAS unreachable: {exc}")
            return outcome

        outcome.success = len(outcome.errors) == 0
        return outcome

    def _default_transport(self, method: str, url: str, **kwargs):
        if self.session is None:
            raise RuntimeError("requests package not available")
        return self.session.request(method, url, timeout=30, **kwargs)

    def status(self) -> Dict[str, Any]:
        return {
            "service": "ilias_learning",
            "ilias_url": self.ilias_url,
            "client_id": self.client_id,
            "available": self.is_available(),
        }


def create_ilias_learning_service(config: Optional[Dict[str, Any]] = None) -> ILIASLearningService:
    """Factory used by the ILIAS agent / Django layer"""
    return ILIASLearningService(config=config)


def create_authenticated_ilias_service(config: Optional[Dict[str, Any]] = None) -> ILIASLearningService:
    """ILIAS learning service wired to an authenticated API transport (OP2).

    Builds an IliasApiClient (OAuth2 token flow via services/ilias_api_service.py)
    and exposes it as the sync transport, so learning path syncs carry a
    Bearer Authorization header. The token client config comes from the same
    config dict (ilias_url, client_id, client_secret, grant_type, ...).
    """
    from services.ilias_api_service import create_ilias_api_client

    service = ILIASLearningService(config=config)
    api_client = create_ilias_api_client(config=config)
    service.api_client = api_client
    service.session = None
    service._default_transport = api_client.request
    return service
