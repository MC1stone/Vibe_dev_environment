#!/usr/bin/env python3
# NIR Intelligence Platform - FL6 test matrix: real flwr deployment wiring
# (superlink/supernode) + ILIAS course development agent in its own container.
# Verifies: (A) the compose services and entry scripts for the SuperLink
# transport (FL1 deployment), (B) the IliasCourseAgent - curriculum catalog
# from real platform capabilities, honest degradation, ILIAS sync via the
# OP2 services with stub transport, and the agent container + runner wiring.
# No network, no running containers.

import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0
FAILED = []

PROJECT = os.path.join(os.path.dirname(__file__), "..")


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        FAILED.append(name)
        print(f"[FAIL] {name} {detail}")


# --- A: superlink/supernode deployment wiring (FL1) ----------------------

dev = open(os.path.join(PROJECT, "docker-compose.yml"), encoding="utf-8").read()
prod = open(os.path.join(PROJECT, "docker-compose.prod.yml"), encoding="utf-8").read()

check("A1a dev compose: flower_server starts the superlink entry script",
      "flower_superlink_entry.py" in dev)
check("A1b dev compose: flower_client supernode service with group env",
      "flower_client:" in dev and "FLOWER_CLIENT_GROUP" in dev
      and "flower_supernode_entry.py" in dev)
check("A1c dev compose: client connects to the superlink fleet API",
      "FLOWER_SUPERLINK_ADDRESS=flower_server:9092" in dev)
check("A1d prod compose: same superlink wiring",
      "flower_superlink_entry.py" in prod and "flower_client:" in prod)
check("A1e both composes pin flwr in the entry commands",
      dev.count("flwr>=1.4.0") >= 2 and prod.count("flwr>=1.4.0") >= 2)

import yaml

for name, text in (("dev", dev), ("prod", prod)):
    try:
        services = yaml.safe_load(text)["services"]
        ok = "flower_server" in services and "flower_client" in services
    except Exception as exc:
        ok = False
        print("      yaml error:", exc)
    check(f"A1f {name} compose parses with flower services", ok)

superlink_src = open(os.path.join(PROJECT, "scripts", "flower_superlink_entry.py"),
                     encoding="utf-8").read()
check("A2a superlink entry starts flower_superlink CLI",
      "flower_superlink" in superlink_src and "--fleet-api-address" in superlink_src)
check("A2b superlink entry launches the ServerApp from services/flower_apps",
      "make_server_app" in superlink_src)
check("A2c superlink entry honours FLOWER_STRATEGY/FLOWER_NUM_ROUNDS env",
      "FLOWER_STRATEGY" in superlink_src and "FLOWER_NUM_ROUNDS" in superlink_src)

supernode_src = open(os.path.join(PROJECT, "scripts", "flower_supernode_entry.py"),
                     encoding="utf-8").read()
check("A3a supernode entry uses the FL1 NirFlwrClient (S9 semantics)",
      "NirFlwrClient" in supernode_src and "LocalDataset" in supernode_src)
check("A3b supernode entry connects to FLOWER_SUPERLINK_ADDRESS",
      "FLOWER_SUPERLINK_ADDRESS" in supernode_src)
check("A3c supernode data loading is honest (synthetic only as warning)",
      "FLOWER_CLIENT_DATA" in supernode_src and "placeholder" in supernode_src)
check("A3d supernode never transmits raw data (privacy contract note)",
      "never transmit it" in supernode_src)

# --- B: ILIAS course development agent ------------------------------------

from agents.ilias_course_agent import (
    CURRICULUM_SEQUENCE,
    PLATFORM_TOPICS,
    CurriculumCatalogEntry,
    IliasCourseAgent,
)

agent = IliasCourseAgent()
catalog = agent.build_curriculum_catalog()
check("B1a catalog covers the platform capability topics",
      [e.topic_key for e in catalog] == CURRICULUM_SEQUENCE
      and len(catalog) >= 5)
check("B1b every curriculum has objectives with Bloom levels",
      all(len(e.objectives) >= 2 for e in catalog)
      and all(o["target_level"] in
              ("remember", "understand", "apply", "analyze", "evaluate", "create")
              for e in catalog for o in e.objectives))
check("B1c federated learning is part of the curriculum",
      any(e.topic_key == "federated" for e in catalog))
check("B1d catalog status reports counts honestly",
      agent.catalog_status()["curricula"] == len(catalog)
      and agent.catalog_status()["objectives"] ==
      sum(len(e.objectives) for e in catalog))

# catalog derives ONLY from the real inventory - unknown keys are dropped
PLATFORM_TOPICS["phantom"] = {"title": "Phantom", "description": "", "objectives": []}
check("B1e catalog never invents capabilities outside the sequence",
      all(e.topic_key in CURRICULUM_SEQUENCE for e in catalog))
del PLATFORM_TOPICS["phantom"]

payload = catalog[0].to_learning_path_payload()
check("B1f learning path payload matches the S8 sync contract",
      payload["title"] and payload["modules"]
      and payload["target_group"] == "students")


# ILIAS sync via stub transport (OP2 pattern) - honest degradation
class StubResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body or {}

    def json(self):
        return self._body


class StubTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers=None, **kwargs):
        self.calls.append({"method": method, "url": url})
        if self.responses:
            return self.responses.pop(0)
        raise ConnectionError("ILIAS container not running")


agent2 = IliasCourseAgent()


def with_stub_transport(agent, transport):
    """Wire the stub into the services used by the agent."""
    import services.ilias_learning_service as ils
    import services.ilias_api_service as ias
    original_sync = ils.ILIASLearningService.sync_learning_path

    def sync_stub(path, course_ref_id=None, transport=None, **kw):
        return original_sync(agent, path, transport=transport, **kw)

    return sync_stub


# sync path via the real learning service with injected transport
from services.ilias_learning_service import ILIASLearningService, LearningPath

entry = catalog[0]
service = ILIASLearningService(config={"ilias_url": "http://ilias:80"})


class _FakeResp:
    status_code = 201

    def json(self):
        return {"ref_id": "55"}


good_transport = StubTransport([_FakeResp(), _FakeResp()])
lp = LearningPath(title=entry.title, description=entry.description,
                  modules=[])
lp2 = LearningPath(title=entry.title, description=entry.description,
                   modules=[])
# modules must be non-empty for the sync contract
from services.ilias_learning_service import LearningModule, LearningObjective

lp_mod = LearningModule(
    title=entry.title,
    objectives=[LearningObjective(**o) for o in entry.objectives])
lp2.modules = [lp_mod]
outcome = service.sync_learning_path(lp2, transport=good_transport)
check("B2a curriculum syncs as learning path via the S8 service (stub)",
      outcome.success and outcome.course_ref_id == "55",
      str(outcome.errors))

# honest degradation: ILIAS unreachable
bad_transport = StubTransport([])
agent3 = IliasCourseAgent()
agent3.config["ilias_url"] = "http://ilias:80"


class UnreachableTransport:
    def __call__(self, method, url, **kwargs):
        raise ConnectionError("ILIAS container not running")


outcome2 = service.sync_learning_path(
    LearningPath(title="X", modules=[lp_mod]),
    transport=UnreachableTransport())
check("B2b unreachable ILIAS degrades honestly (no crash, no fake success)",
      not outcome2.success and outcome2.errors)

# agent execute contract
result = agent.execute({"operation": "develop"})
check("B3a execute(develop) returns the catalog payload",
      result.data["operation"] == "develop"
      and result.data["catalog"]["curricula"] >= 5)
result = agent.execute({"operation": "status"})
check("B3b execute(status) reports agent config and catalog",
      result.data["agent"] == "ilias_course_agent"
      and "ilias_url" in result.data["config"])
result = agent.execute({"operation": "sync"})
check("B3c execute(sync) reports honest degraded status without ILIAS",
      result.data["operation"] == "sync"
      and result.data["status"] in ("completed", "degraded"))
check("B3d sync result details every curriculum",
      len(result.data["results"]) >= 5
      and all("success" in r and "topic" in r for r in result.data["results"]))

# --- C: agent container + runner wiring ----------------------------------

check("C1a dev compose defines ilias_course_agent service",
      "ilias_course_agent:" in dev)
check("C1b prod compose defines ilias_course_agent service",
      "ilias_course_agent:" in prod)
check("C1c agent container depends on the ILIAS container",
      "depends_on" in dev.split("ilias_course_agent:")[1].split("networks")[0])
check("C1d agent runs the container runner",
      "ilias_course_agent_runner.py" in dev
      and "ilias_course_agent_runner.py" in prod)

runner_src = open(os.path.join(PROJECT, "scripts", "ilias_course_agent_runner.py"),
                  encoding="utf-8").read()
check("C2a runner keeps iterating with honest degraded handling",
      "--once" in runner_src and "round failed (continuing)" in runner_src)
check("C2b runner persists round state",
      "state_file" in runner_src and "save_state" in runner_src)
check("C2c runner imports the IliasCourseAgent",
      "IliasCourseAgent" in runner_src)

# runner smoke: one round with unreachable ILIAS must complete degraded
import subprocess

if os.path.exists("/tmp/fl6_state.json"):
    os.remove("/tmp/fl6_state.json")
r = subprocess.run([sys.executable,
                    os.path.join(PROJECT, "scripts", "ilias_course_agent_runner.py"),
                    "--once", "--ilias-url", "http://ilias:80",
                    "--state-file", "/tmp/fl6_state.json"],
                   capture_output=True, text=True, timeout=120)
check("C2d runner completes one round against unreachable ILIAS (exit 0)",
      r.returncode == 0, r.stderr[-200:] if r.returncode else "")
import json

state = json.load(open("/tmp/fl6_state.json"))
check("C2e runner state records the degraded round honestly",
      state["rounds"] == 1 and state["last_round"]["status"] in
      ("completed", "degraded"))

print(f"\n{PASS}/{PASS + FAIL} checks passed")
if FAILED:
    print("FAILED:", FAILED)
    sys.exit(1)
