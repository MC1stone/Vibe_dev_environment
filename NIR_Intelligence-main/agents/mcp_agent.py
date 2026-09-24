# NIR Intelligence Platform - MCP Agent
# Handles tool integration and communication with platform interfaces (MO 2).
# Real implementation: probes the platform tool endpoints (Qdrant, FAISS,
# Ollama, ILIAS, Django) over HTTP and reports their actual state plus the
# integrated tool registry. Unreachable services are reported per tool
# instead of simulated values.

import math
import os
import re
import tempfile

import pandas as pd
from typing import Any, Dict, List, Optional, Tuple

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
        the statistical analysis agents consume. When the file contains no
        single wavelength/intensity pair but a wide measurement table
        (one row per measurement, one column per channel), the measurement
        matrix is extracted instead, so every file with measurable values
        is ingestable (MO 1).
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
        metadata = dict(spectral.get("metadata") or {})

        # Multi-channel (wide-format) exports first, same detection rule as
        # the ingest service (services/project_ingest.py): channel columns
        # named '<prefix>_<wavelength>' (A_410, B_435, ch_410nm, 680nm).
        # Such a file has one row per measurement and no single spectral
        # axis, so the pair extraction below must not run.
        channel_re = re.compile(r"^(?:[A-Za-z]{1,3}_)?(\d{2,5})\s*n?m?$",
                                re.IGNORECASE)
        channel_cols = [c for c in df.columns
                        if channel_re.match(str(c).strip())]
        if len(channel_cols) >= 3:
            numeric_cols = [c for c in df.columns
                            if pd.api.types.is_numeric_dtype(df[c])]
            matrix = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
            usable = matrix.dropna(how="all")
            measurements = []
            for row in usable.to_numpy(dtype=float, na_value=float("nan")):
                values = [float(v) for v in row
                          if not (isinstance(v, float) and math.isnan(v))
                          and math.isfinite(v)]
                if values:
                    measurements.append(values)
            if measurements:
                metadata["dataset_layout"] = "wide_measurement_matrix"
                return {
                    "operation": "ingest",
                    "file_path": file_path,
                    "format": spectral.get("format"),
                    "source_file": os.path.basename(file_path),
                    "status": "ok",
                    "metadata": metadata,
                    "wavelength_column": None,
                    "intensity_column": None,
                    "prepared_dataset": {
                        "channels": [str(c) for c in numeric_cols],
                        "num_channels": len(numeric_cols),
                        "num_measurements": len(measurements),
                        "measurements": measurements,
                        "wavelength_unit": "channel_index",
                        "ready_for": "statistical_analysis",
                    },
                }

        def _finite_pairs(wl_col: Any, it_col: Any) -> List[Tuple[float, float]]:
            pairs: List[Tuple[float, float]] = []
            for wl_raw, it_raw in zip(df[wl_col].tolist(), df[it_col].tolist()):
                wl = EnhancedDataPreparationAgent._normalise_decimal_string(wl_raw)
                it = EnhancedDataPreparationAgent._normalise_decimal_string(it_raw)
                try:
                    wl_f, it_f = float(wl), float(it)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(wl_f) and math.isfinite(it_f):
                    pairs.append((wl_f, it_f))
            return pairs

        wavelength_col = spectral.get("wavelength_column")
        intensity_col = spectral.get("intensity_column")
        pairs: List[Tuple[float, float]] = []

        def _is_spectral_axis(values: List[float]) -> bool:
            """A real spectral axis ascends and spans at least 10 nm (or
            the equivalent in um / cm-1 scaled exports). Reference-value
            columns (Brix, sugar) and channel runs fail this check and
            route the file to the measurement-matrix extraction."""
            if len(values) < 2:
                return False
            if not all(b > a for a, b in zip(values, values[1:])):
                return False
            return (values[-1] - values[0]) > 10.0

        if wavelength_col in df.columns and intensity_col in df.columns:
            candidates = _finite_pairs(wavelength_col, intensity_col)
            if candidates and _is_spectral_axis([p[0] for p in candidates]):
                pairs = candidates

        # The loader picks columns by name patterns and heuristics; exotic
        # exports can defeat that guess. Scan ALL column pairs and keep
        # the most plausible spectral pair.
        if not pairs and len(df.columns) >= 2:
            for wl_col in df.columns:
                for it_col in df.columns:
                    if wl_col == it_col:
                        continue
                    candidate = _finite_pairs(wl_col, it_col)
                    if not candidate:
                        continue
                    wls = [p[0] for p in candidate]
                    if not _is_spectral_axis(wls):
                        continue
                    its = [p[1] for p in candidate]
                    if its == sorted(its) and all(
                            abs(b - a) <= 1e-9 for a, b in zip(its, its[1:])):
                        continue
                    if len(candidate) > len(pairs):
                        pairs = candidate
                        wavelength_col, intensity_col = wl_col, it_col

        if pairs:
            wavelengths = [p[0] for p in pairs]
            intensities = [p[1] for p in pairs]
            return {
                "operation": "ingest",
                "file_path": file_path,
                "format": spectral.get("format"),
                "source_file": os.path.basename(file_path),
                "status": "ok",
                "metadata": metadata,
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

        # No wavelength/intensity pair anywhere: search the file for a
        # wide measurement matrix (one row per measurement, one column
        # per channel) so multi-channel exports are ingestable too.
        numeric_cols = [c for c in df.columns
                        if pd.api.types.is_numeric_dtype(df[c])]
        if len(numeric_cols) >= 2:
            matrix = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
            usable = matrix.dropna(how="all")
            measurements = []
            for row in usable.to_numpy(dtype=float, na_value=float("nan")):
                values = [float(v) for v in row
                          if not (isinstance(v, float) and math.isnan(v))
                          and math.isfinite(v)]
                if values:
                    measurements.append(values)
            if measurements:
                metadata["dataset_layout"] = "wide_measurement_matrix"
                return {
                    "operation": "ingest",
                    "file_path": file_path,
                    "format": spectral.get("format"),
                    "source_file": os.path.basename(file_path),
                    "status": "ok",
                    "metadata": metadata,
                    "wavelength_column": None,
                    "intensity_column": None,
                    "prepared_dataset": {
                        "channels": [str(c) for c in numeric_cols],
                        "num_channels": len(numeric_cols),
                        "num_measurements": len(measurements),
                        "measurements": measurements,
                        "wavelength_unit": "channel_index",
                        "ready_for": "statistical_analysis",
                    },
                }

        return {
            "operation": "ingest",
            "file_path": file_path,
            "status": "error",
            "error": "no finite spectral values",
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
