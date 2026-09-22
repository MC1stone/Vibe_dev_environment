# NIR Intelligence Platform - MCP Agent
# Handles tool integration and communication with platform interfaces (MO 2).
# Real implementation: probes the platform tool endpoints (Qdrant, FAISS,
# Ollama, ILIAS, Django) over HTTP and reports their actual state plus the
# integrated tool registry. Unreachable services are reported per tool
# instead of simulated values.

import math
import os
import tempfile
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
    - operation 'interfaces': registry of platform data/API interfaces the
      MCP server exposes to external clients (Django REST endpoints, upload,
      crew analysis, report pages)
    - operation 'ingest': cooperate with the data-preparation agent to load
      any spectral file format, extract metadata + spectral data and prepare
      the dataset for statistical analysis. context keys: file_path, formats.
    """

    def __init__(self, **kwargs):
        super().__init__(name="MCPAgent", version="3.0.0", **kwargs)
        self.dependencies = ["requests", "websockets"]
        self.host = kwargs.get("host", "mcp_server")
        self.port = int(kwargs.get("port", 8082))
        self.protocols = kwargs.get("protocols", ["http", "websocket", "stdio"])
        self.tools = kwargs.get("tools", DEFAULT_TOOLS)

    PLATFORM_INTERFACES = [
        {
            "name": "upload_file",
            "kind": "http",
            "endpoint": "/api/files/upload/",
            "method": "POST",
            "description": "Upload a spectral data file in any supported format",
        },
        {
            "name": "crew_analysis",
            "kind": "http",
            "endpoint": "/api/files/<file_id>/crew-analysis/",
            "method": "POST",
            "description": "Run the full NIRAnalysisCrew pipeline on an uploaded file",
        },
        {
            "name": "analysis_report",
            "kind": "http",
            "endpoint": "/analysis/report/<file_id>/",
            "method": "GET",
            "description": "Fetch the comprehensive analysis report page",
        },
        {
            "name": "ingest_dataset",
            "kind": "mcp-tool",
            "description": (
                "Load a spectral file in any format, extract metadata and "
                "spectral data, and prepare the dataset for statistical analysis"
            ),
        },
    ]

    def _interfaces(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "operation": "interfaces",
            "mcp_endpoint": f"{self.host}:{self.port}",
            "protocols_enabled": list(self.protocols),
            "interfaces": [dict(i) for i in self.PLATFORM_INTERFACES],
            "count": len(self.PLATFORM_INTERFACES),
            "status": "ok",
        }

    def _ingest(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Cooperate with the data-preparation agent to prepare a dataset.

        Reuses the S3 format-agnostic loader (all file formats, all
        spectrometers): loads the file, extracts metadata and the unified
        spectral schema, and emits the clean wavelengths/intensities pairs
        the statistical analysis agents consume.
        """
        file_path = str(context.get("file_path", "")).strip()
        if not file_path:
            raise ValueError("ingest requires 'file_path'")
        if not os.path.isfile(file_path):
            return {
                "operation": "ingest",
                "file_path": file_path,
                "status": "error",
                "error": "file not found",
            }

        from .data_preparation_agent import EnhancedDataPreparationAgent

        loader = EnhancedDataPreparationAgent(
            input_directory=os.path.dirname(file_path) or ".",
            output_directory=tempfile.mkdtemp(prefix="mcp_ingest_"),
        )
        spectral = loader._load_spectral_data(file_path)
        if not spectral or spectral.get("data") is None:
            return {
                "operation": "ingest",
                "file_path": file_path,
                "status": "error",
                "error": "not a parseable spectral file",
            }

        df = spectral["data"]
        wavelength_col = spectral.get("wavelength_column")
        intensity_col = spectral.get("intensity_column")
        if wavelength_col not in df.columns or intensity_col not in df.columns:
            return {
                "operation": "ingest",
                "file_path": file_path,
                "status": "error",
                "error": "wavelength/intensity columns not found",
            }

        wavelengths, intensities = [], []
        for wl_raw, it_raw in zip(df[wavelength_col].tolist(),
                                  df[intensity_col].tolist()):
            wl = EnhancedDataPreparationAgent._normalise_decimal_string(wl_raw)
            it = EnhancedDataPreparationAgent._normalise_decimal_string(it_raw)
            try:
                wl_f, it_f = float(wl), float(it)
            except (TypeError, ValueError):
                continue
            if math.isfinite(wl_f) and math.isfinite(it_f):
                wavelengths.append(wl_f)
                intensities.append(it_f)

        if not wavelengths:
            return {
                "operation": "ingest",
                "file_path": file_path,
                "status": "error",
                "error": "no finite spectral values",
            }

        return {
            "operation": "ingest",
            "file_path": file_path,
            "format": spectral.get("format"),
            "source_file": os.path.basename(file_path),
            "status": "ok",
            "metadata": spectral.get("metadata") or {},
            "wavelength_column": wavelength_col,
            "intensity_column": intensity_col,
            "prepared_dataset": {
                "wavelengths": wavelengths,
                "intensities": intensities,
                "num_points": len(wavelengths),
                "wavelength_unit": "nm",
                "ready_for": "statistical_analysis",
            },
        }

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
            elif operation == "interfaces":
                mcp_results = self._interfaces(context)
            elif operation == "ingest":
                mcp_results = self._ingest(context)
            else:
                return self._handle_error(ValueError(f"unknown operation '{operation}'"))

            self.status = AgentStatus.COMPLETED
            return self._create_success_output(mcp_results)
        except Exception as e:
            return self._handle_error(e)
