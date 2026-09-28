#!/usr/bin/env python3
"""NIR Intelligence Platform - ILIAS course agent container runner.

Runs the IliasCourseAgent continuously in its own container: it keeps
developing the NIR curriculum catalog from the platform capabilities
and syncing the courses to the ILIAS container (docker-compose service
`ilias_course_agent`). ILIAS outages degrade honestly - the runner
keeps iterating and reports the degraded state instead of crashing or
simulating syncs.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("IliasCourseAgentRunner")

STATE_FILE = Path("output/ilias_course_agent_state.json")
DEFAULT_INTERVAL = 300


def load_state(state_file: Path) -> Dict[str, Any]:
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("state file unreadable, starting fresh")
    return {"rounds": 0, "last_round": None, "history": []}


def save_state(state_file: Path, state: Dict[str, Any]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2, default=str),
                          encoding="utf-8")


def run_once(agent) -> Dict[str, Any]:
    outcome = agent.develop_and_sync()
    catalog = agent.catalog_status()
    return {"round": outcome, "catalog": catalog,
            "status": outcome.get("status")}


def main() -> int:
    parser = argparse.ArgumentParser(description="ILIAS course agent runner")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help="seconds between sync rounds (default 300)")
    parser.add_argument("--once", action="store_true",
                        help="run one round and exit")
    parser.add_argument("--ilias-url", default="http://ilias:80")
    parser.add_argument("--client-id", default="")
    parser.add_argument("--client-secret", default="")
    parser.add_argument("--state-file", default=str(STATE_FILE))
    args = parser.parse_args()

    from agents.ilias_course_agent import IliasCourseAgent

    agent = IliasCourseAgent(
        ilias_url=args.ilias_url,
        client_id=args.client_id,
        client_secret=args.client_secret,
        poll_interval=args.interval,
    )
    state_file = Path(args.state_file)
    state = load_state(state_file)
    logger.info("ILIAS course agent started (interval %ss, ILIAS %s)",
                args.interval, args.ilias_url)

    while True:
        try:
            summary = run_once(agent)
            state["rounds"] += 1
            state["last_round"] = summary
            state["history"].append(summary)
            state["history"] = state["history"][-50:]
            save_state(state_file, state)
            logger.info("round %s: %s curricula, %s synced, status=%s",
                        state["rounds"],
                        summary["catalog"]["curricula"],
                        summary["round"]["synced"],
                        summary["status"])
        except KeyboardInterrupt:
            logger.info("shutting down")
            return 0
        except Exception as exc:
            logger.error("round failed (continuing): %s", exc)
        if args.once:
            return 0
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    sys.exit(main())
