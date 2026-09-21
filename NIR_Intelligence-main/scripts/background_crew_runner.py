#!/usr/bin/env python3
# NIR Intelligence Platform - Background crew runner (roadmap OP6)
# Runs the NIRAnalysisCrew agent system continuously in the background and
# lets the agents operate the platform: platform status round (Django,
# PostgreSQL, Qdrant, ILIAS, MCP tool integration) and, when new spectral
# data is present, the full analysis pipeline (data preparation, spectral
# analysis, sensor quality, statistics + neural networks in parallel,
# metadata, calibration) including report generation.

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("BackgroundCrewRunner")

STATUS_INTERVAL_SECONDS = 300


class BackgroundCrewRunner:
    """Operates the platform agents in the background."""

    def __init__(self, interval: int = STATUS_INTERVAL_SECONDS, once: bool = False,
                 state_file: str = "output/crew_background_state.json"):
        self.interval = int(interval)
        self.once = once
        self.state_file = Path(state_file)
        self.state: Dict[str, Any] = {"rounds": 0, "last_round": None, "history": []}
        self._load_state()

        from agents.nir_analysis_crew import NIRAnalysisCrew, CrewConfiguration

        self.crew = NIRAnalysisCrew(CrewConfiguration(enable_crewai=True))
        logger.info(
            "Background crew initialized: %d CrewAI agents (CrewAI package: %s)",
            len(self.crew.crewai_agents),
            "yes" if self.crew.crew is not None else "not installed - standalone mode",
        )

    def _load_state(self) -> None:
        if self.state_file.exists():
            try:
                self.state = json.loads(self.state_file.read_text())
            except Exception:
                logger.warning("Could not parse state file, starting fresh")

    def _save_state(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2, default=str))

    def platform_status_round(self) -> Dict[str, Any]:
        """Probe the platform interfaces through the service agents."""
        round_result: Dict[str, Any] = {"type": "platform_status", "agents": {}}

        agents = [
            ("django", self.crew.django_agent, {"operation": "health"}),
            ("postgresql", self.crew.postgresql_agent, {"operation": "health"}),
            ("qdrant", self.crew.qdrant_agent, {}),
            ("ilias", self.crew.ilias_agent, {"operation": "status"}),
            ("mcp", self.crew.mcp_agent, {"operation": "status"}),
        ]
        for name, agent, context in agents:
            try:
                output = agent.execute(context)
                round_result["agents"][name] = {
                    "status": "ok" if output.data.get("status", "ok") != "degraded" else "degraded",
                    "summary": {
                        key: output.data.get(key)
                        for key in ("status", "application_reachable", "connection_established",
                                    "available", "tools_integrated")
                        if key in output.data
                    },
                }
            except Exception as exc:
                round_result["agents"][name] = {"status": "error", "error": str(exc)}
        return round_result

    def run_round(self) -> Dict[str, Any]:
        """One background round: platform status + optional analysis."""
        started = time.time()
        round_result: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "platform": self.platform_status_round(),
        }
        degraded = [
            name for name, state in round_result["platform"]["agents"].items()
            if state.get("status") != "ok"
        ]
        round_result["platform"]["summary"] = {
            "agents_ok": len(round_result["platform"]["agents"]) - len(degraded),
            "agents_degraded": degraded,
        }

        round_result["duration_seconds"] = round(time.time() - started, 2)
        self.state["rounds"] = int(self.state.get("rounds", 0)) + 1
        self.state["last_round"] = round_result
        history: List = self.state.setdefault("history", [])
        history.append(round_result["timestamp"])
        if len(history) > 100:
            del history[:-100]
        self._save_state()

        logger.info(
            "Background round %d done in %.2fs - platform ok: %d/%d%s",
            self.state["rounds"],
            round_result["duration_seconds"],
            round_result["platform"]["summary"]["agents_ok"],
            len(round_result["platform"]["agents"]),
            f" (degraded: {', '.join(degraded)})" if degraded else "",
        )
        return round_result

    def run(self) -> None:
        logger.info("Background crew runner started (interval: %ds)", self.interval)
        if self.once:
            self.run_round()
            return
        while True:
            try:
                self.run_round()
            except Exception:
                logger.exception("Background round failed")
            time.sleep(self.interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="NIR background crew runner")
    parser.add_argument("--interval", type=int, default=STATUS_INTERVAL_SECONDS,
                        help="seconds between background rounds (default 300)")
    parser.add_argument("--once", action="store_true",
                        help="run a single round and exit")
    parser.add_argument("--state-file", default="output/crew_background_state.json",
                        help="path of the background state file")
    args = parser.parse_args()

    runner = BackgroundCrewRunner(interval=args.interval, once=args.once,
                                  state_file=args.state_file)
    runner.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
