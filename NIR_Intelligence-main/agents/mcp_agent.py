# NIR Intelligence Platform - MCP Agent
# Handles tool integration and communication with platform interfaces (MO 2).
# Real implementation: probes the platform tool endpoints (Qdrant, FAISS,
# Ollama, ILIAS, Django) over HTTP and reports their actual state plus the
# integrated tool registry. Unreachable services are reported per tool
# instead of simulated values.

from typing import Any, Dict, List, Optional

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity

DEFAULT_TOOLS = [
    {"name": "qdrant", "url": "http://qdrant:6333", "health_path": "/healthz"},
    {"name": "faiss", "url": "http://faiss:8081", "health_path": "/"},
    {"name": "ollama", "url": "http://ollama:11434", "health_path": "/api/tags"},
    {"name": "ilias", "url": "http://ilias:80", "health_path": "/"},
    {"name": "django_app", "url": "http://django_app:8000", "health_path": "/api/health/"},
]


class MCPAgent(BaseAgent):
    """Agent for managing MCP server and tool integration.

    context keys:
    - operation: 'status' (default) - probe all integrated tools
    - tools: tool list override ([{name, url, health_path}])
    - host/port: MCP server endpoint (informational in this implementation)
    """

    def __init__(self, **kwargs):
        super().__init__(name="MCPAgent", version="2.0.0", **kwargs)
        self.dependencies = ["requests", "websockets"]
        self.host = kwargs.get("host", "mcp_server")
        self.port = int(kwargs.get("port", 8082))
        self.protocols = kwargs.get("protocols", ["http", "websocket"])
        self.tools = kwargs.get("tools", DEFAULT_TOOLS)

    def _probe_tool(self, tool: Dict[str, Any], timeout: int = 5) -> Dict[str, Any]:
        name = tool.get("name", "unknown")
        url = tool.get("url", "").rstrip("/")
        health_path = tool.get("health_path", "/")
        try:
            import requests

            response = requests.get(f"{url}{health_path}", timeout=timeout)
            return {
                "name": name,
                "url": url,
                "reachable": True,
                "http_status": int(response.status_code),
                "integrated": int(response.status_code) < 500,
            }
        except Exception as exc:
            return {
                "name": name,
                "url": url,
                "reachable": False,
                "http_status": None,
                "integrated": False,
                "error": str(exc),
            }

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute MCP operations."""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting MCP agent execution")

            context = context or {}
            operation = str(context.get("operation", "status"))

            if operation == "status":
                tools = context.get("tools", self.tools)
                tools_integrated = 0
                tool_states: List[Dict[str, Any]] = []
                for tool in tools:
                    state = self._probe_tool(tool)
                    tool_states.append(state)
                    tools_integrated += 1 if state["integrated"] else 0
                mcp_results = {
                    "operation": operation,
                    "mcp_endpoint": f"{self.host}:{self.port}",
                    "protocols_enabled": list(self.protocols),
                    "tools_registered": len(tools),
                    "tools_integrated": tools_integrated,
                    "tool_states": tool_states,
                    "status": "ok" if tools_integrated > 0 else "degraded",
                    "message": (
                        f"{tools_integrated}/{len(tools)} platform tools integrated"
                        if tools_integrated
                        else "no platform tool reachable"
                    ),
                }
            else:
                return self._handle_error(ValueError(f"unknown operation '{operation}'"))

            self.status = AgentStatus.COMPLETED
            return self._create_success_output(mcp_results)
        except Exception as e:
            return self._handle_error(e)
