#!/usr/bin/env python3
"""NIR Intelligence Platform - Flower SuperNode entry point (FL1 deployment).

Connects one federated learning client (SuperNode) to the SuperLink.
The ClientApp uses the SAME code as the verified simulation runtime
(services/flower_apps.make_client_fn): local training is the S9 ridge
update; only parameter updates leave the client (privacy contract).

Environment:
  FLOWER_SUPERLINK_ADDRESS (default flower_server:9092 - the fleet API)
  FLOWER_CLIENT_GROUP (spectrometer group / non-IID shard of this client)
  FLOWER_CLIENT_DATA (path to a .npz with x/y arrays; synthetic demo data
                      is generated when absent - honest log message, the
                      privacy contract is unchanged)
"""

import logging
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FlowerSuperNodeEntry")


def load_or_make_dataset(group: str):
    """Load the client's local dataset - never transmit it."""
    import numpy as np

    data_path = os.getenv("FLOWER_CLIENT_DATA")
    if data_path and Path(data_path).exists():
        blob = np.load(data_path)
        logger.info("loaded local dataset %s (x %s, y %s)",
                    data_path, blob["x"].shape, blob["y"].shape)
        return np.asarray(blob["x"], dtype=np.float64), \
            np.asarray(blob["y"], dtype=np.float64)

    # honest fallback: synthetic placeholder data for wiring verification;
    # real deployments mount FLOWER_CLIENT_DATA with the group's spectra
    rng = np.random.default_rng(abs(hash(group)) % (2 ** 32))
    x = rng.normal(0, 1, size=(30, int(os.getenv("FLOWER_MODEL_DIM", "18"))))
    y = x @ rng.normal(0, 1, size=x.shape[1]) + rng.normal(0, 0.05, size=30)
    logger.warning("FLOWER_CLIENT_DATA not set - using synthetic placeholder "
                   "data (wiring verification only, never real spectra)")
    return x, y


def main() -> int:
    superlink = os.getenv("FLOWER_SUPERLINK_ADDRESS", "flower_server:9092")
    group = os.getenv("FLOWER_CLIENT_GROUP", "sparkfun_triad")

    import numpy as np
    from flwr.client import ClientApp
    from flwr.supernode.cli import flwr_clientapp

    from services.flower_apps import NirFlwrClient
    from services.federated_learning_service import LocalDataset

    x, y = load_or_make_dataset(group)
    dataset = LocalDataset(x=x, y=y, group=group)

    def client_fn(cid: str):
        return NirFlwrClient(client_id=group, dataset=dataset).to_client()

    # make the ClientApp discoverable for the flwr runtime via a module
    import types
    module = types.ModuleType("nir_flwr_client_app")
    module.app = ClientApp(client_fn=client_fn)
    sys.modules["nir_flwr_client_app"] = module

    sys.argv = ["flower-supernode", "--insecure",
                "--superlink", superlink,
                "--node-config", f"app-path={PROJECT_ROOT}",
                ]
    logger.info("starting SuperNode for group %s against %s", group, superlink)
    try:
        flwr_clientapp()
    except KeyboardInterrupt:
        logger.info("shutting down")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
