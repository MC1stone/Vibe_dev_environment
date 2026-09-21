#!/usr/bin/env python3
# NIR Intelligence Platform - OP6 test matrix: CrewAI agent implementation
# Verifies that all mission-statement agents are implemented for real (no
# simulated values), wired as CrewAI agents with tools, and that the
# background crew runner operates the platform interfaces. All tests run
# offline (degraded states are expected without containers).

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0
FAILED = []


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        FAILED.append(name)
        print(f"[FAIL] {name} {detail}")


def sample_data():
    np.random.seed(42)
    X = np.array([list(1000 + 20 * i + np.random.normal(0, 3, 30)) for i in range(15)])
    y = np.linspace(0.5, 9.5, 15)
    return X, y


# T1: no simulated values remain in the previously stubbed agents
for agent_file in [
    "sensor_quality_agent.py",
    "statistical_analysis_agent.py",
    "neural_network_agent.py",
    "calibration_agent.py",
    "metadata_agent.py",
    "postgresql_agent.py",
    "django_agent.py",
    "mcp_agent.py",
    "ilias_agent.py",
]:
    src = open(os.path.join(os.path.dirname(__file__), "..", "agents", agent_file)).read()
    check(f"T1a {agent_file}: no 'Simulate' placeholder left",
          "Simulate" not in src and "Placeholder implementation" not in src)
    check(f"T1b {agent_file}: degraded/error handling present",
          "degraded" in src or "no_data" in src or "no_reference" in src
          or "_handle_error" in src)

# T2: Sensor Quality Agent - real computation
from agents.sensor_quality_agent import SensorQualityAgent

X, y = sample_data()
out = SensorQualityAgent().execute({"spectra": X})
check("T2a sensor quality completes", out.status.name == "COMPLETED")
check("T2b sensor quality score computed from data",
      0.0 <= out.data["overall_quality_score"] <= 1.0)
noisy = X + np.random.normal(0, 500, X.shape)
out_noisy = SensorQualityAgent().execute({"spectra": noisy, "noise_threshold": 0.01})
check("T2c noise detection fires on noisy spectra",
      out_noisy.data["noise_detected"] is True)
check("T2d noisy spectra score lower than clean",
      out_noisy.data["overall_quality_score"] < out.data["overall_quality_score"])

# T3: Statistical Analysis Agent - real methods
from agents.statistical_analysis_agent import StatisticalAnalysisAgent

out = StatisticalAnalysisAgent().execute({"spectra": X, "reference_values": y})
check("T3a all default methods applied",
      set(out.data["methods_applied"]) == {"PCA", "PLS", "PCR", "ANOVA", "ClusterAnalysis"})
check("T3b PCA variance from real data",
      0.0 < out.data["method_results"]["PCA"]["cumulative_variance_explained"] <= 1.0)
check("T3c PLS mean_r2 computed",
      "mean_r2" in out.data["method_results"]["PLS"])
out_no_y = StatisticalAnalysisAgent().execute({"spectra": X})
check("T3d PLS/PCR skipped without reference values",
      any(s["method"] == "PLS" for s in out_no_y.data["methods_skipped"]))

# T4: Neural Network Agent - real training, CNN deferred without TF
from agents.neural_network_agent import NeuralNetworkAgent

out = NeuralNetworkAgent().execute(
    {"spectra": X, "reference_values": y, "models": ["MLP", "Autoencoder", "CNN"]})
check("T4a MLP and Autoencoder trained",
      {"MLP", "Autoencoder"} <= set(out.data["models_trained"]))
check("T4b CNN reported (trained or deferred), never simulated",
      "CNN" in out.data["models_trained"]
      or any(d["model"] == "CNN" for d in out.data["models_deferred"]))
check("T4c autoencoder anomaly metrics present",
      "reconstruction_mse" in out.data["model_results"].get("Autoencoder", {}))

# T5: Calibration Agent - real cross-validated calibrations
from agents.calibration_agent import CalibrationAgent

out = CalibrationAgent().execute({"spectra": X, "reference_values": y})
check("T5a real calibration methods tested",
      len(out.data["methods_tested"]) >= 4, detail=str(out.data["methods_tested"]))
check("T5b best method with r2 from cross-validation",
      "best_method" in out.data and "best_r2_score" in out.data)
out_no_ref = CalibrationAgent().execute({"spectra": X})
check("T5c calibration without reference values reported, not simulated",
      out_no_ref.data["status"] == "no_reference")

# T6: Metadata Agent delegates to real quality assessment
from agents.metadata_agent import MetadataAgent

out = MetadataAgent().execute({
    "metadata": {"instrument_type": "DIY", "measurement_date": "2026-01-01"},
    "sample_id": "s1",
})
check("T6a metadata quality score from assessment",
      out.data["metadata_quality_score"] > 0)
check("T6b missing required fields listed",
      len(out.data["missing_required_fields"]) > 0)

# T7: PostgreSQL Agent - degraded without database
from agents.postgresql_agent import PostgreSQLAgent

out = PostgreSQLAgent().execute({"operation": "health", "connect_timeout": 1})
check("T7a postgres degraded without db",
      out.data["status"] == "degraded" and out.data["connection_established"] is False)

# T8: Django Agent - degraded without application
from agents.django_agent import DjangoAgent

out = DjangoAgent().execute({"operation": "health", "base_url": "http://localhost:59998"})
check("T8a django degraded without app",
      out.data["status"] == "degraded" and out.data["application_reachable"] is False)

# T9: MCP Agent - real tool probing
from agents.mcp_agent import MCPAgent

out = MCPAgent().execute({"operation": "status",
                          "tools": [{"name": "t", "url": "http://localhost:59997", "health_path": "/"}]})
check("T9a mcp reports unreachable tools, not simulated integration",
      out.data["tools_integrated"] == 0 and out.data["status"] == "degraded")

# T10: ILIAS Agent - real status via learning service
from agents.ilias_agent import ILIASAgent

out = ILIASAgent().execute({"operation": "status", "ilias_url": "http://localhost:59996"})
check("T10a ilias degraded without container",
      out.data["status"] == "degraded" and out.data["available"] is False)

# T11: Crew wiring - all mission statement agents in the crew
from agents.nir_analysis_crew import NIRAnalysisCrew, CrewConfiguration

crew = NIRAnalysisCrew(CrewConfiguration(enable_crewai=True))
expected = [
    "data_preparation_agent", "spectral_agent", "sensor_quality_agent",
    "statistical_analysis_agent", "neural_network_agent", "metadata_agent",
    "calibration_agent", "qdrant_agent", "faiss_agent", "postgresql_agent",
    "django_agent", "mcp_agent", "ilias_agent", "reporting_agent",
    "quarto_agent", "flower_agent",
]
check("T11a all mission agents instantiated on the crew",
      all(hasattr(crew, name) for name in expected),
      detail=str([n for n in expected if not hasattr(crew, n)]))
check("T11b tool factory wraps agents with JSON contract",
      callable(crew._agent_tool(crew.mcp_agent, "d")))

# T12: CrewAI integration - 16 agents with tools when the package is present
import types

mock = types.ModuleType("crewai")


class _Agent:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _Crew:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _Task:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _Process:
    sequential = "sequential"


mock.Agent = _Agent
mock.Crew = _Crew
mock.Task = _Task
mock.Process = _Process
tools_mod = types.ModuleType("crewai.tools")
tools_mod.tool = lambda fn: fn
mock.tools = tools_mod
for name, mod in [("crewai", mock), ("crewai.tools", tools_mod)]:
    sys.modules[name] = mod

import agents.nir_analysis_crew as crew_module
import importlib

crew_module = importlib.reload(crew_module)
check("T12a mocked CrewAI import flips availability",
      crew_module.CREWAI_AVAILABLE is True)

full_crew = crew_module.NIRAnalysisCrew(crew_module.CrewConfiguration(enable_crewai=True))
check("T12b 16 CrewAI agents created", len(full_crew.crewai_agents) == 16,
      detail=str(len(full_crew.crewai_agents)))
check("T12c every CrewAI agent has a bound tool",
      all(getattr(a, "tools", None) for a in full_crew.crewai_agents))
check("T12d crew object created", full_crew.crew is not None)
tool_fn = full_crew.crewai_agents[0].tools[0]
result = tool_fn("{}")
import json as _json

parsed = _json.loads(result)
check("T12e tool executes the real agent and returns JSON",
      "agent" in parsed and "status" in parsed and "data" in parsed)

for name in ["crewai", "crewai.tools"]:
    del sys.modules[name]

# T13: background crew runner
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import background_crew_runner

runner = background_crew_runner.BackgroundCrewRunner(once=True, state_file="/tmp/op6_state.json")
round_result = runner.run_round()
check("T13a background round reports all platform agents",
      set(round_result["platform"]["agents"]) == {"django", "postgresql", "qdrant", "ilias", "mcp"})
check("T13b background state persisted",
      runner.state["rounds"] == 1)
check("T13c degraded agents reported (offline run)",
      len(round_result["platform"]["summary"]["agents_degraded"]) > 0)

# T14: docker-compose background_crew service
import yaml

compose = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "docker-compose.yml")))
services = compose["services"]
check("T14a background_crew service defined",
      "background_crew" in services)
check("T14b background_crew runs the runner script",
      "background_crew_runner.py" in services["background_crew"]["command"])
check("T14c background_crew joins nir_network and depends on postgres",
      "nir_network" in services["background_crew"]["networks"]
      and "postgresql" in services["background_crew"]["depends_on"])

print(f"\n{PASS}/{PASS + FAIL} tests passed")
sys.exit(1 if FAILED else 0)
