# NIR Intelligence Platform - ILIAS Agent
# Handles e-learning platform integration (MO 14, roadmap S8/OP2).
# Real implementation: uses the OAuth2 token flow and authenticated REST
# client from services/ilias_api_service.py and the learning path sync from
# services/ilias_learning_service.py. Unreachable ILIAS instances are
# reported as degraded instead of simulated sync results.

from typing import Any, Dict, List, Optional

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class ILIASAgent(BaseAgent):
    """Agent for managing ILIAS e-learning integration.

    context keys:
    - operation: 'status' (default) | 'list_courses' | 'sync_learning_path'
    - learning_path: learning path payload for 'sync_learning_path'
      ({title, description, target_group, modules: [{title, objectives,
      content_ref}]})
    - ilias_url / client_id / client_secret: connection overrides
    """

    def __init__(self, **kwargs):
        super().__init__(name="ILIASAgent", version="2.0.0", **kwargs)
        self.dependencies = ["requests"]
        self.ilias_url = kwargs.get("ilias_url", "http://ilias:80")
        self.api_version = kwargs.get("api_version", "v1")
        self.client_id = kwargs.get("client_id", "nir_ip")
        self.client_secret = kwargs.get("client_secret", "")
        self.synchronization = kwargs.get("synchronization", {})

    def _service_config(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ilias_url": context.get("ilias_url", self.ilias_url),
            "client_id": context.get("client_id", self.client_id),
            "client_secret": context.get("client_secret", self.client_secret),
        }

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute ILIAS integration operations."""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting ILIAS agent execution")

            context = context or {}
            operation = str(context.get("operation", "status"))
            config = self._service_config(context)

            from services.ilias_learning_service import (
                ILIASLearningService,
                LearningModule,
                LearningObjective,
                LearningPath,
                create_ilias_learning_service,
            )

            service = create_ilias_learning_service(config=config)

            if operation == "status":
                status = service.status()
                ilias_results = {
                    "operation": operation,
                    "ilias_url": status["ilias_url"],
                    "available": status["available"],
                    "status": "ok" if status["available"] else "degraded",
                    "message": (
                        "ILIAS reachable"
                        if status["available"]
                        else "ILIAS container not reachable"
                    ),
                }
            elif operation == "list_courses":
                from services.ilias_api_service import create_ilias_api_client

                api_client = create_ilias_api_client(config=config)
                try:
                    response = api_client.list_courses()
                    status_code = getattr(response, "status_code", 0)
                    if status_code == 200:
                        body = response.json()
                        courses = body.get("courses", body) if isinstance(body, dict) else body
                        ilias_results = {
                            "operation": operation,
                            "authenticated": True,
                            "courses": courses if isinstance(courses, list) else [],
                            "course_count": len(courses) if isinstance(courses, list) else 0,
                            "status": "ok",
                        }
                    else:
                        ilias_results = {
                            "operation": operation,
                            "authenticated": False,
                            "http_status": int(status_code),
                            "status": "degraded",
                            "message": f"ILIAS API returned {status_code}",
                        }
                except Exception as exc:
                    ilias_results = {
                        "operation": operation,
                        "authenticated": False,
                        "status": "degraded",
                        "message": f"ILIAS API unreachable: {exc}",
                    }
            elif operation == "sync_learning_path":
                payload = context.get("learning_path")
                if not isinstance(payload, dict) or not payload.get("title"):
                    return self._handle_error(ValueError(
                        "operation 'sync_learning_path' requires a learning_path with a title"))
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
                outcome = service.sync_learning_path(path)
                ilias_results = {
                    "operation": operation,
                    "success": outcome.success,
                    "course_title": outcome.course_title,
                    "course_ref_id": outcome.course_ref_id,
                    "modules_synced": outcome.modules_synced,
                    "errors": outcome.errors,
                    "status": "ok" if outcome.success else "degraded",
                }
            else:
                return self._handle_error(ValueError(f"unknown operation '{operation}'"))

            self.status = AgentStatus.COMPLETED
            return self._create_success_output(ilias_results)
        except Exception as e:
            return self._handle_error(e)
