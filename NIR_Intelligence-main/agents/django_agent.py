# NIR Intelligence Platform - Django Agent
# Handles web interface and API operations (MO 1).
# Real implementation: probes and drives the running Django application
# over HTTP (health, endpoints, migrations status via /api/health/).
# Unreachable application or missing requests are reported as degraded
# instead of simulated results.

from typing import Any, Dict, List, Optional

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class DjangoAgent(BaseAgent):
    """Agent for managing the Django web application.

    context keys:
    - operation: 'health' (default) | 'endpoints'
    - base_url: Django base URL (default http://django_app:8000 or localhost:8000)
    """

    def __init__(self, **kwargs):
        super().__init__(name="DjangoAgent", version="2.0.0", **kwargs)
        self.dependencies = ["django", "djangorestframework", "requests"]
        self.project_name = kwargs.get("project_name", "nir_web")
        self.apps = kwargs.get("apps", ["core", "api", "visualization"])
        self.port = int(kwargs.get("port", 8000))
        self.debug = kwargs.get("debug", True)
        self.base_url = kwargs.get("base_url") or f"http://localhost:{self.port}"

    def _request(self, url: str, timeout: int = 10):
        import requests

        return requests.get(url, timeout=timeout)

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute Django operations."""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting Django agent execution")

            context = context or {}
            operation = str(context.get("operation", "health"))
            base_url = str(context.get("base_url", self.base_url)).rstrip("/")

            try:
                import requests  # noqa: F401
            except ImportError:
                return self._create_success_output({
                    "operation": operation,
                    "status": "degraded",
                    "message": "requests package not available",
                })

            if operation == "health":
                try:
                    response = self._request(f"{base_url}/api/health/")
                    django_results = {
                        "operation": operation,
                        "base_url": base_url,
                        "http_status": int(response.status_code),
                        "application_reachable": True,
                        "response": self._safe_json(response),
                        "status": "ok" if response.status_code < 500 else "degraded",
                    }
                except Exception as exc:
                    django_results = {
                        "operation": operation,
                        "base_url": base_url,
                        "application_reachable": False,
                        "status": "degraded",
                        "message": f"Django application not reachable: {exc}",
                    }
            elif operation == "endpoints":
                endpoints = [
                    "/api/health/",
                    "/api/agents/",
                    "/api/spectra/",
                    "/api/jobs/",
                    "/api/chatbot/status/",
                    "/api/ilias/status/",
                ]
                probe_results: List[Dict[str, Any]] = []
                reachable = 0
                for endpoint in endpoints:
                    try:
                        response = self._request(f"{base_url}{endpoint}", timeout=5)
                        ok = response.status_code < 500
                        probe_results.append({
                            "endpoint": endpoint,
                            "http_status": int(response.status_code),
                            "ok": ok,
                        })
                        reachable += 1 if ok else 0
                    except Exception:
                        probe_results.append({
                            "endpoint": endpoint,
                            "http_status": None,
                            "ok": False,
                        })
                django_results = {
                    "operation": operation,
                    "base_url": base_url,
                    "endpoints_probed": len(endpoints),
                    "endpoints_reachable": reachable,
                    "probe_results": probe_results,
                    "status": "ok" if reachable > 0 else "degraded",
                }
            else:
                return self._handle_error(ValueError(f"unknown operation '{operation}'"))

            self.status = AgentStatus.COMPLETED
            return self._create_success_output(django_results)
        except Exception as e:
            return self._handle_error(e)

    @staticmethod
    def _safe_json(response) -> Any:
        try:
            return response.json()
        except Exception:
            return {"text": response.text[:200]}
