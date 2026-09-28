#!/usr/bin/env python3
"""NIR Intelligence Platform - Flower SuperLink entry point (FL1 deployment).

Starts the flwr SuperLink (federation coordinator) inside the
flower_server container. The ServerApp with the S9 core semantics is
launched alongside via flwr-serverapp against the SuperLink runtime API
so a federated run (started e.g. via `flwr run` from a client or the
simulation runner) executes FedAvg/FedProx over the connected
SuperNodes. Binds only inside the container network (nir_network) -
no public exposure.

Environment:
  FLOWER_SERVER_HOST (default 0.0.0.0 - container-internal)
  FLOWER_SUPERLINK_PORT (default 9091, runtime HTTP API)
  FLOWER_FLEET_API_PORT (default 9092, gRPC SuperNode fleet)
  FLOWER_NUM_ROUNDS (default 3)
  FLOWER_STRATEGY (fedavg | fedprox)
  FLOWER_PROXIMAL_MU (default 0.1)
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def start_superlink() -> subprocess.Popen:
    host = os.getenv("FLOWER_SERVER_HOST", "0.0.0.0")
    port = os.getenv("FLOWER_SUPERLINK_PORT", "9091")
    fleet_port = os.getenv("FLOWER_FLEET_API_PORT", "9092")
    cmd = [
        sys.executable, "-m", "flwr.superlink.cli", "flower_superlink",
        "--insecure",
        "--host", host,
        "--port", port,
        "--fleet-api-address", f"{host}:{fleet_port}",
    ]
    print("[flower_superlink_entry] starting:", " ".join(cmd), flush=True)
    return subprocess.Popen(cmd)


def start_server_app(superlink_address: str) -> subprocess.Popen:
    """Launch the ServerApp with the S9 core semantics (services/flower_apps).

    The ServerApp connects to the SuperLink runtime API; the strategy and
    rounds come from the environment. Flwr requires the app importable in
    the working directory - PROJECT_ROOT/services is on the path.
    """
    num_rounds = os.getenv("FLOWER_NUM_ROUNDS", "3")
    strategy = os.getenv("FLOWER_STRATEGY", "fedavg")
    proximal_mu = os.getenv("FLOWER_PROXIMAL_MU", "0.1")
    bootstrap = (
        "import sys; sys.path.insert(0, %r); "
        "import numpy as np; "
        "from services.flower_apps import make_server_app; "
        "from flwr.server import ServerConfig; "
        "app = make_server_app(dim=int(%s), num_rounds=int(%s), strategy=%r, "
        "proximal_mu=float(%s)); "
        "setattr(app, '_config', ServerConfig(num_rounds=int(%s)))"
    ) % (str(PROJECT_ROOT), os.getenv("FLOWER_MODEL_DIM", "18"), num_rounds,
         strategy, float(proximal_mu), num_rounds)
    cmd = [
        sys.executable, "-c",
        bootstrap + "; from flwr.superlink.cli import flwr_serverapp; "
        "import sys as _s; _s.argv = ['flwr-serverapp', '--insecure', "
        "'--runtime-api-address', %r, '--token', 'nir-fl1']; flwr_serverapp()",
        superlink_address,
    ]
    print("[flower_superlink_entry] starting ServerApp against", superlink_address,
          flush=True)
    return subprocess.Popen(cmd)


def main() -> int:
    superlink = start_superlink()
    time.sleep(5)  # let the runtime API come up
    server_app = None
    if os.getenv("FLOWER_START_SERVERAPP", "1") == "1":
        host = os.getenv("FLOWER_SERVER_HOST", "0.0.0.0")
        port = os.getenv("FLOWER_SUPERLINK_PORT", "9091")
        server_app = start_server_app(f"{host}:{port}")
    try:
        while True:
            if superlink.poll() is not None:
                print("[flower_superlink_entry] SuperLink exited - stopping",
                      flush=True)
                return superlink.returncode or 1
            if server_app is not None and server_app.poll() is not None:
                print("[flower_superlink_entry] ServerApp exited - "
                      "restarting (SuperLink stays up)", flush=True)
                time.sleep(5)
                host = os.getenv("FLOWER_SERVER_HOST", "0.0.0.0")
                port = os.getenv("FLOWER_SUPERLINK_PORT", "9091")
                server_app = start_server_app(f"{host}:{port}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("[flower_superlink_entry] shutting down", flush=True)
        return 0
    finally:
        for proc in (server_app, superlink):
            if proc is not None and proc.poll() is None:
                proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
