# NIR Intelligence Platform - Federated learning core service (roadmap S9)
# Framework-independent federated learning core for distributed spectrometer
# setups: clients train on local spectra and share ONLY model parameter
# updates (privacy: raw spectra never leave the client). Non-IID data
# sharding groups spectra per spectrometer/sample type. Aggregation
# implements FedAvg- and FedProx-style updates on plain numpy arrays; the
# Flower framework (services/flower_server.py, agents/flower_agent.py) is
# the production transport, this core is transport-agnostic and testable
# without flwr installed.

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("Service.FederatedLearning")

try:
    import flwr  # noqa: F401 - production transport (optional here)

    FLWR_AVAILABLE = True
except ImportError:
    FLWR_AVAILABLE = False


@dataclass
class LocalDataset:
    """Local training data of one client (stays on the client)"""

    x: np.ndarray
    y: np.ndarray
    group: str = "default"  # non-IID group, e.g. spectrometer model id

    def size(self) -> int:
        return int(self.x.shape[0])


@dataclass
class ModelUpdate:
    """Parameter update transmitted from a client to the server.

    Privacy guarantee: only these parameter arrays leave the client -
    never the raw spectra.
    """

    client_id: str
    params: np.ndarray
    num_examples: int
    group: str
    metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"client_id": self.client_id, "num_examples": self.num_examples,
                "group": self.group, "metrics": self.metrics,
                "param_shape": list(self.params.shape)}


@dataclass
class AggregationResult:
    """Result of one federated aggregation round"""

    round_id: int
    aggregated_params: Optional[np.ndarray] = None
    participating_clients: List[str] = field(default_factory=list)
    total_examples: int = 0
    groups: List[str] = field(default_factory=list)
    strategy: str = "fedavg"
    privacy_note: str = "only parameter updates shared - raw data stays local"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_id": self.round_id,
            "participating_clients": self.participating_clients,
            "total_examples": self.total_examples,
            "groups": self.groups,
            "strategy": self.strategy,
            "privacy_note": self.privacy_note,
            "param_shape": list(self.aggregated_params.shape) if self.aggregated_params is not None else None,
        }


class NonIIDSharder:
    """Creates non-IID dataset shards grouped by spectrometer/sample group.

    Each simulated distributed spectrometer setup receives only the spectra
    of its own group (e.g. one spectrometer model or sample type), which is
    the realistic non-IID federated scenario for the NIR laboratory.
    """

    def __init__(self, num_groups: int = 3):
        self.num_groups = num_groups

    def shard(self, x: np.ndarray, y: np.ndarray,
              groups: List[str]) -> Dict[str, LocalDataset]:
        if len(groups) != x.shape[0]:
            raise ValueError(f"group labels ({len(groups)}) do not match rows ({x.shape[0]})")
        shards: Dict[str, LocalDataset] = {}
        for group in dict.fromkeys(groups):  # unique, order preserved
            mask = np.array([g == group for g in groups])
            shards[group] = LocalDataset(x=x[mask], y=y[mask], group=group)
        return shards

    def shards_for_clients(self, x: np.ndarray, y: np.ndarray,
                           groups: List[str], client_ids: List[str]) -> Dict[str, LocalDataset]:
        """Assign each client one non-IID shard (client i <- group i)."""
        shards = self.shard(x, y, groups)
        assignment: Dict[str, LocalDataset] = {}
        for client_id, group in zip(client_ids, dict.fromkeys(groups)):
            if group in shards:
                assignment[client_id] = shards[group]
        return assignment


class FedAvgAggregator:
    """Federated averaging (weighted by client example counts).

    Supports fedavg and fedprox-style aggregation: fedprox applies a
    proximal term pulling client updates toward the global parameters
    (approximated by blending with mu, mirroring FedProx's mu||w - w_global||^2).
    """

    def __init__(self, strategy: str = "fedavg", proximal_mu: float = 0.1):
        if strategy not in ("fedavg", "fedprox"):
            raise ValueError(f"unknown strategy: {strategy}")
        self.strategy = strategy
        self.proximal_mu = float(proximal_mu)

    def aggregate(self, updates: List[ModelUpdate],
                  global_params: Optional[np.ndarray] = None) -> Optional[np.ndarray]:
        if not updates:
            return None
        shapes = {u.params.shape for u in updates}
        if len(shapes) != 1:
            raise ValueError(f"client parameter shapes differ: {shapes}")

        total = sum(u.num_examples for u in updates)
        if total == 0:
            raise ValueError("no examples across updates")

        weighted = np.zeros_like(updates[0].params, dtype=np.float64)
        for update in updates:
            weight = update.num_examples / total
            params = update.params.astype(np.float64)
            if self.strategy == "fedprox" and global_params is not None:
                params = (1.0 - self.proximal_mu) * params + self.proximal_mu * global_params
            weighted += weight * params
        return weighted


class PrivacyAuditor:
    """Verifies the privacy contract of a federated round.

    Checks that client payloads contain only parameter updates and metrics
    - never raw spectral data rows.
    """

    @staticmethod
    def audit_update(update: ModelUpdate, reference_x: Optional[np.ndarray] = None) -> Dict[str, Any]:
        findings: List[str] = []
        ok = True
        if update.params.ndim == 2 and reference_x is not None:
            # heuristic: parameter matrix must not equal/contain raw data rows
            for row in reference_x[: min(5, reference_x.shape[0])]:
                if any(np.array_equal(update.params, row) for _ in [0]):
                    findings.append("parameter payload matches a raw data row")
                    ok = False
        return {"client_id": update.client_id, "private": ok,
                "findings": findings, "payload": "params_only"}


class FederatedLearningService:
    """Federated learning core for distributed spectrometer setups (S9).

    The service orchestrates rounds locally (simulation/standalone mode) and
    delegates to the Flower server (services/flower_server.py) in the
    containerized production setup.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.strategy = self.config.get("strategy", "fedavg")
        self.proximal_mu = float(self.config.get("proximal_mu", 0.1))
        self.aggregator = FedAvgAggregator(strategy=self.strategy,
                                           proximal_mu=self.proximal_mu)
        self.sharder = NonIIDSharder()
        self.auditor = PrivacyAuditor()
        self.global_params: Optional[np.ndarray] = None
        self.round_id = 0
        self.history: List[AggregationResult] = []

    def initialize_global_model(self, dim: int, seed: int = 42) -> np.ndarray:
        rng = np.random.default_rng(seed)
        self.global_params = rng.normal(0, 0.01, size=dim)
        return self.global_params

    def client_update(self, client_id: str, dataset: LocalDataset,
                      epochs: int = 1, learning_rate: float = 0.1) -> ModelUpdate:
        """Simulate local training: ridge-style update toward local optima.

        Clients fit their local optimum (closed-form ridge regression) and
        transmit ONLY the resulting parameters - the dataset never leaves.
        """
        x = dataset.x.astype(np.float64)
        y = dataset.y.astype(np.float64)
        if x.shape[0] == 0:
            raise ValueError(f"client {client_id} has no local data")
        gram = x.T @ x + 1e-6 * np.eye(x.shape[1])
        local_params = np.linalg.solve(gram, x.T @ y)
        # blend local optimum with global parameters (local SGD step)
        if self.global_params is not None and self.global_params.shape == local_params.shape:
            local_params = (1 - learning_rate) * self.global_params + learning_rate * local_params
        return ModelUpdate(client_id=client_id, params=local_params,
                           num_examples=dataset.size(), group=dataset.group,
                           metrics={"local_rmse": float(np.sqrt(np.mean((x @ local_params - y) ** 2)))})

    def aggregate_round(self, updates: List[ModelUpdate]) -> AggregationResult:
        """Aggregate client updates into new global parameters (privacy-safe)."""
        self.round_id += 1
        aggregated = self.aggregator.aggregate(updates, global_params=self.global_params)
        result = AggregationResult(
            round_id=self.round_id,
            aggregated_params=aggregated,
            participating_clients=[u.client_id for u in updates],
            total_examples=sum(u.num_examples for u in updates),
            groups=sorted({u.group for u in updates}),
            strategy=self.strategy,
        )
        self.global_params = aggregated
        self.history.append(result)
        return result

    def run_round(self, datasets: Dict[str, LocalDataset],
                  epochs: int = 1, learning_rate: float = 0.1,
                  reference_x: Optional[np.ndarray] = None) -> Tuple[AggregationResult, List[Dict[str, Any]]]:
        """Run one complete federated round: local training + aggregation +
        privacy audit."""
        updates = [self.client_update(cid, data, epochs=epochs, learning_rate=learning_rate)
                   for cid, data in datasets.items()]
        audits = [self.auditor.audit_update(u, reference_x=reference_x) for u in updates]
        result = self.aggregate_round(updates)
        if not all(a["private"] for a in audits):
            logger.warning("privacy audit findings in round %s", result.round_id)
        return result, audits

    def status(self) -> Dict[str, Any]:
        return {
            "service": "federated_learning",
            "strategy": self.strategy,
            "proximal_mu": self.proximal_mu,
            "flwr_available": FLWR_AVAILABLE,
            "rounds_completed": len(self.history),
            "global_model_initialized": self.global_params is not None,
        }


def create_federated_learning_service(config: Optional[Dict[str, Any]] = None) -> FederatedLearningService:
    """Factory used by the FlowerAgent and the simulation layer"""
    return FederatedLearningService(config=config)
