# NIR Intelligence Platform - Flower app pair for real federated learning (FL1)
# Bridges the S9 framework-independent core (federated_learning_service) to
# the actual Flower transport: the ServerApp runs FedAvg/FedProx via flwr
# strategies, the ClientApp performs local training with the same ridge-update
# semantics as FederatedLearningService.client_update. Raw spectra never
# leave the client - only parameter updates are transmitted (privacy
# contract verified by the S9 PrivacyAuditor).
#
# Runtime modes (all use the SAME ServerApp/ClientApp code):
# - simulation: flwr.simulation backend (verification / CI)
# - deployment: flower-superlink + flower-supernode via docker-compose
#   (services/flower_server.py starts the SuperLink; clients connect as
#   SuperNodes over the internal nir_network only)

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("Service.FlowerApps")

try:
    import flwr as fl
    from flwr.client import NumPyClient
    from flwr.common import ndarrays_to_parameters, parameters_to_ndarrays
    from flwr.server import ServerApp, ServerConfig
    from flwr.server.strategy import FedAvg, FedProx

    FLWR_AVAILABLE = True
except ImportError:
    FLWR_AVAILABLE = False

from .federated_learning_service import (
    FederatedLearningService,
    LocalDataset,
    NonIIDSharder,
)


def make_strategy(strategy: str = "fedavg", proximal_mu: float = 0.1,
                  min_clients: int = 2, initial_params: Optional[np.ndarray] = None):
    """Build the flwr strategy matching the S9 core configuration."""
    if not FLWR_AVAILABLE:
        raise RuntimeError("flwr is not installed - deployment runtime unavailable")
    common = dict(
        min_available_clients=min_clients,
        min_fit_clients=min_clients,
        min_evaluate_clients=min_clients,
        on_fit_config_fn=lambda server_round: {"learning_rate": 0.1},
    )
    initial = None
    if initial_params is not None:
        initial = ndarrays_to_parameters([initial_params])
    if strategy == "fedprox":
        return FedProx(proximal_mu=proximal_mu, initial_parameters=initial, **common)
    if strategy == "fedavg":
        return FedAvg(initial_parameters=initial, **common)
    raise ValueError(f"unknown strategy: {strategy}")


def make_server_app(dim: int, num_rounds: int = 3, strategy: str = "fedavg",
                    proximal_mu: float = 0.1, min_clients: int = 2,
                    seed: int = 42) -> "ServerApp":
    """ServerApp over the flwr transport with S9 core semantics."""
    rng = np.random.default_rng(seed)
    initial = [rng.normal(0, 0.01, size=dim)]
    return ServerApp(
        config=ServerConfig(num_rounds=num_rounds),
        strategy=make_strategy(strategy, proximal_mu, min_clients,
                               initial_params=initial[0]),
    )


class NirFlwrClient(NumPyClient):
    """Flower client whose local training IS the S9 ridge update.

    fit() computes the closed-form local optimum (same as
    FederatedLearningService.client_update with learning_rate=1.0) and
    transmits only the parameter vector - the local spectra stay on the
    client (privacy contract).
    """

    def __init__(self, client_id: str, dataset: LocalDataset,
                 learning_rate: float = 0.1,
                 core: Optional[FederatedLearningService] = None):
        self.client_id = client_id
        self.dataset = dataset
        self.learning_rate = float(learning_rate)
        self.core = core or FederatedLearningService()

    def get_parameters(self, config):
        if self.core.global_params is None:
            return [np.zeros(self.dataset.x.shape[1])]
        return [self.core.global_params]

    def fit(self, parameters, config):
        global_params = np.asarray(parameters[0], dtype=np.float64)
        if self.core.global_params is None or \
                self.core.global_params.shape != global_params.shape:
            self.core.global_params = global_params
        update = self.core.client_update(
            self.client_id, self.dataset,
            learning_rate=float(config.get("learning_rate", self.learning_rate)),
        )
        # aggregate into this client's view so subsequent rounds blend
        # (the server aggregates across clients; this keeps core state honest)
        self.core.global_params = update.params
        return [update.params], self.dataset.size(), {
            "group": self.dataset.group,
            "local_rmse": update.metrics.get("local_rmse", 0.0),
        }

    def evaluate(self, parameters, config):
        w = np.asarray(parameters[0], dtype=np.float64)
        x = self.dataset.x.astype(np.float64)
        y = self.dataset.y.astype(np.float64)
        if x.shape[0] == 0:
            return 0.0, 0, {}
        mse = float(np.mean((x @ w - y) ** 2))
        return mse, x.shape[0], {"group": self.dataset.group}


def make_client_fn(datasets: Dict[str, LocalDataset],
                   learning_rate: float = 0.1):
    """Client factory over non-IID shards (one SuperNode per spectrometer
    group, mirroring the S9 NonIIDSharder assignment)."""
    if not FLWR_AVAILABLE:
        raise RuntimeError("flwr is not installed - deployment runtime unavailable")
    client_ids = list(datasets.keys())
    cores: Dict[str, FederatedLearningService] = {
        cid: FederatedLearningService() for cid in client_ids
    }

    def client_fn(cid: str):
        client_id = client_ids[int(cid) % len(client_ids)]
        client = NirFlwrClient(client_id=client_id,
                               dataset=datasets[client_id],
                               learning_rate=learning_rate,
                               core=cores[client_id])
        return client.to_client()

    return fl.client.ClientApp(client_fn=client_fn)


def run_federated_training(x: np.ndarray, y: np.ndarray,
                           groups: List[str],
                           num_rounds: int = 3,
                           strategy: str = "fedavg",
                           proximal_mu: float = 0.1,
                           backend_name: str = "io") -> Dict[str, Any]:
    """Run real federated training over the flwr simulation runtime.

    Uses the same ServerApp/ClientApp code as the deployment mode
    (superlink/supernode); the simulation engine just executes them
    in-process instead of over gRPC.
    """
    if not FLWR_AVAILABLE:
        return {"status": "deferred", "reason": "flwr not installed"}
    sharder = NonIIDSharder()
    shards = sharder.shard(x, y, groups)
    datasets = {group: shard for group, shard in shards.items()}
    dim = x.shape[1]

    server_app = make_server_app(dim=dim, num_rounds=num_rounds,
                                 strategy=strategy, proximal_mu=proximal_mu,
                                 min_clients=len(datasets))
    client_app = make_client_fn(datasets)

    fl.simulation.run_simulation(
        server_app=server_app,
        client_app=client_app,
        num_supernodes=len(datasets),
        backend_name=backend_name,
    )
    return {
        "status": "completed",
        "rounds": num_rounds,
        "strategy": strategy,
        "groups": sorted(datasets.keys()),
        "privacy_note": "only parameter updates shared - raw data stays local",
    }
